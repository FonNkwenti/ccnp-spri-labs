#!/usr/bin/env python3
"""
Stop hook — writes .claude/last_run.json with session telemetry.

Invoked by Claude Code when a session ends. Receives JSON on stdin:
  {"session_id": "...", "transcript_path": "...", "cwd": "...", ...}

Uses cwd from the hook payload (not os.getcwd()) so the output file
always lands in the project root regardless of where Claude Code runs.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_transcript(path: str) -> dict:
    """
    Defensively parse the session transcript JSONL.
    The schema is undocumented — every access uses .get() with safe defaults.
    Returns dict with model, tool_calls, duration_seconds (all may be None/0).
    """
    model = None
    tool_calls = 0
    timestamps = []

    try:
        with open(path, encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(entry, dict):
                    continue

                # Model: try several plausible locations in the entry
                if model is None:
                    model = (
                        entry.get("model")
                        or entry.get("message", {}).get("model")
                        or (entry.get("message", {}) or {}).get("model")
                    )

                # Tool calls: count tool_use blocks wherever they appear
                for content_key in ("content", "message"):
                    content = entry.get(content_key)
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_calls += 1
                    elif isinstance(content, dict):
                        inner = content.get("content", [])
                        if isinstance(inner, list):
                            for block in inner:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tool_calls += 1

                # Timestamps: collect all we find
                for ts_key in ("timestamp", "created_at", "time"):
                    ts = entry.get(ts_key)
                    if isinstance(ts, str) and ts:
                        timestamps.append(ts)
                        break

    except (OSError, IOError):
        pass

    duration = None
    if len(timestamps) >= 2:
        try:
            t0 = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration = max(0, int((t1 - t0).total_seconds()))
        except (ValueError, TypeError, AttributeError):
            pass

    return {"model": model, "tool_calls": tool_calls, "duration_seconds": duration}


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return 0

    try:
        hook_data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    session_id = hook_data.get("session_id")
    transcript_path = hook_data.get("transcript_path")

    # Resolve project root: prefer cwd from hook payload, fall back to env var
    project_root = (
        hook_data.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )

    stats = parse_transcript(transcript_path) if transcript_path else {}

    telemetry = {
        "session_id": session_id,
        "model": stats.get("model"),
        "tool_calls": stats.get("tool_calls", 0),
        "duration_seconds": stats.get("duration_seconds"),
        "written_at": datetime.now(timezone.utc).isoformat(),
        "source": "stop-hook",
    }

    out_dir = Path(project_root) / ".claude"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "last_run.json"

    try:
        out_path.write_text(json.dumps(telemetry, indent=2), encoding="utf-8")
    except OSError:
        pass  # Never crash — a hook failure blocks session exit

    return 0


if __name__ == "__main__":
    sys.exit(main())
