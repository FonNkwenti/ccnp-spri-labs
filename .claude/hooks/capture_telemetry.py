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


PRICING_DATE = "2026-05-06"

# $/MTok input, $/MTok output. Prefix-matched against the model ID.
# Cache multipliers applied to the input price: read=0.10, write_5m=1.25, write_1h=2.0.
MODEL_PRICING = {
    "claude-opus-4":   {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input":  3.0, "output": 15.0},
    "claude-haiku-4":  {"input":  1.0, "output":  5.0},
}
CACHE_READ_MULT = 0.10
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.0


def _price_for(model: str | None):
    if not model:
        return None
    for prefix, prices in MODEL_PRICING.items():
        if model.startswith(prefix):
            return prices
    return None


def parse_transcript(path: str) -> dict:
    """
    Defensively parse the session transcript JSONL.
    The schema is undocumented — every access uses .get() with safe defaults.
    Aggregates model, tool_calls, duration, and per-turn usage blocks.
    """
    model = None
    tool_calls = 0
    timestamps = []
    tokens = {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_creation_5m": 0,
        "cache_creation_1h": 0,
    }

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

                msg = entry.get("message") if isinstance(entry.get("message"), dict) else {}

                if model is None:
                    model = entry.get("model") or msg.get("model")

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

                # Token usage lives on assistant turns under message.usage
                usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else None
                if usage:
                    tokens["input"]      += int(usage.get("input_tokens") or 0)
                    tokens["output"]     += int(usage.get("output_tokens") or 0)
                    tokens["cache_read"] += int(usage.get("cache_read_input_tokens") or 0)
                    cc = usage.get("cache_creation")
                    if isinstance(cc, dict):
                        tokens["cache_creation_5m"] += int(cc.get("ephemeral_5m_input_tokens") or 0)
                        tokens["cache_creation_1h"] += int(cc.get("ephemeral_1h_input_tokens") or 0)
                    else:
                        # Fallback: only the flat field present
                        tokens["cache_creation_5m"] += int(usage.get("cache_creation_input_tokens") or 0)

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

    return {
        "model": model,
        "tool_calls": tool_calls,
        "duration_seconds": duration,
        "tokens": tokens,
    }


def estimate_cost_usd(model: str | None, tokens: dict) -> float | None:
    prices = _price_for(model)
    if not prices:
        return None
    p_in, p_out = prices["input"], prices["output"]
    cost = (
        tokens["input"]              * p_in                       +
        tokens["output"]             * p_out                      +
        tokens["cache_read"]         * p_in * CACHE_READ_MULT     +
        tokens["cache_creation_5m"]  * p_in * CACHE_WRITE_5M_MULT +
        tokens["cache_creation_1h"]  * p_in * CACHE_WRITE_1H_MULT
    ) / 1_000_000.0
    return round(cost, 4)


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

    project_root = (
        hook_data.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )

    stats = parse_transcript(transcript_path) if transcript_path else {}
    tokens = stats.get("tokens") or {
        "input": 0, "output": 0, "cache_read": 0,
        "cache_creation_5m": 0, "cache_creation_1h": 0,
    }
    cost = estimate_cost_usd(stats.get("model"), tokens)

    telemetry = {
        "session_id": session_id,
        "model": stats.get("model"),
        "tool_calls": stats.get("tool_calls", 0),
        "duration_seconds": stats.get("duration_seconds"),
        "tokens": tokens,
        "cost_usd_estimate": cost,
        "pricing_date": PRICING_DATE,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "source": "stop-hook",
    }

    out_dir = Path(project_root) / ".claude"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "last_run.json"

    try:
        out_path.write_text(json.dumps(telemetry, indent=2), encoding="utf-8")
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
