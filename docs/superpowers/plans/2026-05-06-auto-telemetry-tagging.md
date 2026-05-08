# Auto Telemetry Tagging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-stamp `meta.yaml` with model execution telemetry whenever a lab is built — zero user friction.

**Architecture:** build-lab writes `.claude/pending_telemetry.json` inline before calling tag-lab automatically. tag-lab reads that file and embeds a `telemetry:` block into meta.yaml. A separate Stop hook writes `.claude/last_run.json` after every session for use by manual `/tag-lab` invocations (external-agent workflow). Two telemetry sources, one schema, no user arguments.

**Tech Stack:** Python 3 (hook script), YAML (meta.yaml schema), Markdown (skill/command files), Claude Code hooks (`settings.local.json`)

---

## Timing Problem & Solution

The Stop hook fires **after** the session ends. If build-lab calls tag-lab inline (same session), `last_run.json` does not exist yet. The fix:

| Scenario | Telemetry source | Written by |
|---|---|---|
| `/build-lab` → tag-lab (inline) | `.claude/pending_telemetry.json` | build-lab at end of build |
| `/tag-lab` manually (external agent) | `.claude/last_run.json` | Stop hook from prior session |

tag-lab checks `pending_telemetry.json` first, then falls back to `last_run.json`, then omits the block gracefully.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `.claude/hooks/capture_telemetry.py` | **CREATE** | Stop hook: reads session transcript, writes `last_run.json` |
| `.claude/settings.local.json` | **MODIFY** | Register Stop hook |
| `.agent/skills/tag-lab/SKILL.md` | **MODIFY** (submodule) | New Step 0: read telemetry; updated meta.yaml schema |
| `.claude/commands/build-lab.md` | **MODIFY** | Capture start time; write `pending_telemetry.json`; auto-call tag-lab |

---

## Task 1: Create the Stop Hook Script

**Files:**
- Create: `.claude/hooks/capture_telemetry.py`

- [ ] **Step 1: Create hooks directory and write hook script**

Create `.claude/hooks/capture_telemetry.py` with this exact content:

```python
#!/usr/bin/env python3
"""
Stop hook: reads the session transcript and writes .claude/last_run.json
with model, tool_call_count, duration_seconds, and session_id.
Called automatically by Claude Code when a session ends.
"""
import json
import sys
import os
from datetime import datetime, timezone


def parse_transcript(path: str) -> dict:
    model = None
    tool_calls = 0
    timestamps = []

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Capture model from first assistant message
                if entry.get("type") == "assistant" and model is None:
                    model = entry.get("model")

                # Count tool_use blocks inside assistant content
                content = entry.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_calls += 1

                # Collect timestamps
                ts = entry.get("timestamp")
                if ts:
                    timestamps.append(ts)
    except (OSError, IOError):
        pass

    duration = None
    if len(timestamps) >= 2:
        try:
            t0 = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration = int((t1 - t0).total_seconds())
        except (ValueError, TypeError):
            pass

    return {
        "model": model,
        "tool_calls": tool_calls,
        "duration_seconds": duration,
    }


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_data = json.loads(raw)
    except json.JSONDecodeError:
        return

    session_id = hook_data.get("session_id")
    transcript_path = hook_data.get("transcript_path")

    stats = parse_transcript(transcript_path) if transcript_path else {}

    telemetry = {
        "session_id": session_id,
        "model": stats.get("model"),
        "tool_calls": stats.get("tool_calls", 0),
        "duration_seconds": stats.get("duration_seconds"),
        "written_at": datetime.now(timezone.utc).isoformat(),
        "source": "stop-hook",
    }

    # Write relative to CWD (project root when Claude Code invokes hooks)
    out_path = os.path.join(".claude", "last_run.json")
    os.makedirs(".claude", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the file was written**

```
ls .claude/hooks/capture_telemetry.py
```
Expected: file exists.

- [ ] **Step 3: Commit**

```bash
git add .claude/hooks/capture_telemetry.py
git commit -m "feat(telemetry): add Stop hook script to capture session stats"
```

---

## Task 2: Register the Stop Hook in settings.local.json

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Read the current file**

Read `.claude/settings.local.json`. It currently contains only `permissions.allow`.

- [ ] **Step 2: Add the hooks block**

Add a `hooks` key alongside the existing `permissions` key. The final file must be:

```json
{
  "permissions": {
    "allow": [
      "Bash(mkdir -p blueprint/300-510/references specs labs/ospf labs/isis labs/bgp labs/routing-policy labs/ipv6-transition labs/fast-convergence labs/mpls labs/multicast labs/segment-routing labs/srv6)",
      "Bash(mv \"blueprint/Implementing Cisco Service Provider Advanced Routing Solutions v1.1 \\(300-510\\).md\" blueprint/300-510/blueprint.md)",
      "Bash(rmdir blueprint/350-510/references blueprint/350-510)",
      "Bash(git -C C:/Users/Nkwenti/Documents/Labs/Cisco/ccnp-spri-labs rev-parse --show-toplevel)",
      "Bash(chmod +x .agent/skills/scripts/link-skills.sh)",
      "Bash(bash .agent/skills/scripts/link-skills.sh)",
      "Bash(bash -x .agent/skills/scripts/link-skills.sh)",
      "Bash(cmd *)",
      "Bash(powershell.exe *)",
      "Bash(git *)",
      "Bash(python -c ' *)",
      "Bash(python3 -)"
    ]
  },
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/capture_telemetry.py"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 3: Verify JSON is valid**

```bash
python -c "import json; json.load(open('.claude/settings.local.json'))" && echo "valid"
```
Expected: `valid`

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.local.json
git commit -m "feat(telemetry): register Stop hook in project settings"
```

---

## Task 3: Update tag-lab SKILL.md to Read Telemetry

**Files:**
- Modify: `.agent/skills/tag-lab/SKILL.md` (git submodule — commit inside submodule)

The change adds a **new Step 0** before the existing Step 1, and updates the `meta.yaml` schema in Step 4 to include a `telemetry:` block.

- [ ] **Step 1: Read the current SKILL.md**

Read `.agent/skills/tag-lab/SKILL.md` to confirm current content before editing.

- [ ] **Step 2: Insert Step 0 — Read telemetry sidecar**

Insert the following block immediately after the `--# Instructions` heading and before the existing `--# Step 1: Parse Arguments` heading:

```markdown
--# Step 0: Read telemetry sidecar (if present)

Before parsing arguments, check for telemetry data from the current or previous session.

Priority order:
1. `.claude/pending_telemetry.json` — written inline by `build-lab` at end of build (same session)
2. `.claude/last_run.json` — written by Stop hook after prior session ended (manual /tag-lab workflow)

Read whichever file exists (prefer `pending_telemetry.json`). If neither exists, set `telemetry = null` and continue.

Expected fields (all nullable):
```json
{
  "model": "claude-sonnet-4-6",
  "tool_calls": 42,
  "duration_seconds": 847,
  "session_id": "abc123",
  "written_at": "2026-05-06T14:30:00+00:00",
  "source": "build-lab-inline"
}
```

Store the telemetry object for use in Step 4. Do not fail if fields are missing — use `null` for absent values.

After reading, **delete `.claude/pending_telemetry.json`** if it exists (it is a one-shot sidecar; `last_run.json` is persistent and should not be deleted).
```

- [ ] **Step 3: Update Step 4 meta.yaml schema**

In the existing `--# Step 4: Update meta.yaml` section, update both YAML blocks (existing and new) to include the `telemetry:` block. 

Replace the `updated:` entry schema:

```yaml
updated:
  - date: "[YYYY-MM-DD today]"
    agent: [agent-name]
    skill: [skill-name]
    skill_version: "[YYYY-MM-DD from Step 2]"
    files:
      - [all files from Step 3]
```

With:

```yaml
updated:
  - date: "[YYYY-MM-DD today]"
    agent: [agent-name]
    skill: [skill-name]
    skill_version: "[YYYY-MM-DD from Step 2]"
    telemetry:
      model: "[telemetry.model or null]"
      tool_calls: [telemetry.tool_calls or null]
      duration_seconds: [telemetry.duration_seconds or null]
      session_id: "[telemetry.session_id or null]"
    files:
      - [all files from Step 3]
```

Apply the same schema update to the "If meta.yaml does not exist" block's first `updated` entry.

Note: if `telemetry` is `null` (no sidecar found), **omit the `telemetry:` key entirely** from the YAML entry rather than writing null values.

- [ ] **Step 4: Update Step 5 confirmation message**

In `--# Step 5: Confirm`, add one bullet:

```markdown
- Whether telemetry was stamped (source: pending_telemetry.json / last_run.json / none)
```

- [ ] **Step 5: Commit inside the submodule**

```bash
cd .agent/skills
git add tag-lab/SKILL.md
git commit -m "feat(tag-lab): add telemetry sidecar step and meta.yaml telemetry block"
cd ../..
git add .agent/skills
git commit -m "chore(skills): bump submodule — tag-lab telemetry stamping"
```

---

## Task 4: Update build-lab.md to Write Telemetry and Auto-Call tag-lab

**Files:**
- Modify: `.claude/commands/build-lab.md`

Two changes:
1. At the very top of the build steps (after argument parsing), capture the start timestamp.
2. At the end (where it currently says "suggest /tag-lab"), write `pending_telemetry.json` and auto-invoke tag-lab.

- [ ] **Step 1: Read the current file**

Read `.claude/commands/build-lab.md` to confirm current content.

- [ ] **Step 2: Add start-time capture after argument parsing**

After the `## Argument parsing` section and before `## HARD PRE-FLIGHT GATE`, insert:

```markdown
## Telemetry: record build start

Run the following Bash command and store the output as `BUILD_START_EPOCH`:

```bash
python -c "import time; print(int(time.time()))"
```

Store this value for use at the end of the build.
```

- [ ] **Step 3: Replace the final "suggest" block**

Find the last paragraph of `build-lab.md`:

```
Then suggest `/tag-lab $ARGUMENTS` and point the user at the next unbuilt lab in the same topic.
```

Replace it with:

```markdown
## Telemetry: write sidecar and auto-tag

1. Get the current epoch:

```bash
python -c "import time; print(int(time.time()))"
```

2. Compute `duration_seconds = current_epoch - BUILD_START_EPOCH`.

3. Write `.claude/pending_telemetry.json` with this exact structure (substitute real values):

```json
{
  "model": "<your exact model ID from system prompt>",
  "tool_calls": null,
  "duration_seconds": <duration_seconds>,
  "session_id": null,
  "written_at": "<ISO-8601 UTC timestamp>",
  "source": "build-lab-inline",
  "skill": "build-lab"
}
```

Use this Bash command to write it (substitute the computed values):

```bash
python -c "
import json, time, datetime, os
data = {
    'model': '<MODEL_ID>',
    'tool_calls': None,
    'duration_seconds': <DURATION>,
    'session_id': None,
    'written_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source': 'build-lab-inline',
    'skill': 'build-lab'
}
os.makedirs('.claude', exist_ok=True)
open('.claude/pending_telemetry.json', 'w').write(json.dumps(data, indent=2))
"
```

4. Run `/tag-lab $ARGUMENTS <your-model-id> build-lab` (do not suggest — execute it).

5. After tag-lab completes, point the user at the next unbuilt lab in the same topic.
```

- [ ] **Step 4: Verify no syntax errors in the command file**

Read `.claude/commands/build-lab.md` back and confirm the new sections are present and the file reads coherently end-to-end.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/build-lab.md
git commit -m "feat(build-lab): auto-invoke tag-lab with inline telemetry sidecar"
```

---

## Task 5: Smoke Test

- [ ] **Step 1: Verify hook registration is correct**

```bash
python -c "import json; d=json.load(open('.claude/settings.local.json')); print(d['hooks']['Stop'])"
```
Expected: list containing the `capture_telemetry.py` command entry.

- [ ] **Step 2: Test hook script directly**

```bash
python .claude/hooks/capture_telemetry.py <<'EOF'
{"session_id": "test-123", "transcript_path": "nonexistent_path.jsonl"}
EOF
cat .claude/last_run.json
```
Expected: `.claude/last_run.json` written with `session_id: "test-123"`, `tool_calls: 0`, `model: null`.

- [ ] **Step 3: Test pending_telemetry.json read path**

```bash
python -c "
import json, os, datetime
data = {
    'model': 'claude-sonnet-4-6',
    'tool_calls': None,
    'duration_seconds': 300,
    'session_id': None,
    'written_at': datetime.datetime.utcnow().isoformat(),
    'source': 'build-lab-inline',
    'skill': 'build-lab'
}
open('.claude/pending_telemetry.json', 'w').write(json.dumps(data, indent=2))
print('Written pending_telemetry.json')
"
```

Then manually run `/tag-lab <any-built-lab> claude-sonnet-4-6 build-lab` and verify:
- `meta.yaml` includes a `telemetry:` block with `model: claude-sonnet-4-6` and `duration_seconds: 300`
- `.claude/pending_telemetry.json` is deleted after tag-lab runs

- [ ] **Step 4: Final commit (if any fixups needed)**

```bash
git add -p
git commit -m "fix(telemetry): smoke test fixups"
```

---

## Self-Review

**Spec coverage:**
- [x] Zero user friction for build-lab runs — build-lab auto-invokes tag-lab + writes telemetry
- [x] Manual /tag-lab still works — reads last_run.json from Stop hook
- [x] Timing problem solved — pending_telemetry.json is inline; last_run.json is post-session
- [x] Graceful degradation — telemetry block omitted if no sidecar found
- [x] Submodule commit path documented

**Placeholder scan:** No TBD, no TODO, no "add validation" stubs. All code blocks are complete.

**Type consistency:** `pending_telemetry.json` and `last_run.json` share the same schema so tag-lab's read logic is identical for both files.
