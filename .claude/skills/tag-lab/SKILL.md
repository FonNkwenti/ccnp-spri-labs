---
name: tag-lab
description: Stamps a lab's meta.yaml with the agent and skill that generated or modified it. Use after running an external agent (Gemini, Kimi, etc.) on a lab directory. Invoked as /tag-lab <chapter/lab-slug> <agent-name> <skill-name>.
model: claude-haiku-4-5-20251001
---

# Tag Lab Skill

Records provenance for labs generated or modified by external agents (Gemini, Kimi K2.5, etc.) by appending an entry to `meta.yaml`. Keeps provenance tracking accurate when Claude is not the generating agent.

-# Instructions

--# Step 0: Read telemetry sidecar (if present)

Before parsing arguments, check for telemetry from the previous session.

Source: `.claude/last_run.json` — written by the Stop hook when the previous session ended.

If it exists, read it and store the contents as `telemetry`. If it does not exist, set `telemetry = null`. Do not delete it — it is a rolling session record overwritten on every Stop.

Expected fields (all nullable — handle missing gracefully):
```json
{
  "model": "claude-sonnet-4-6",
  "tool_calls": 42,
  "duration_seconds": 847,
  "session_id": "abc123",
  "tokens": {
    "input": 1240,
    "output": 18560,
    "cache_read": 245100,
    "cache_creation_5m": 32400,
    "cache_creation_1h": 18676
  },
  "cost_usd_estimate": 0.8421,
  "pricing_date": "2026-05-06",
  "written_at": "2026-05-06T14:30:00+00:00",
  "source": "stop-hook"
}
```

--# Step 1: Parse Arguments

Arguments format: `<chapter/lab-slug> <agent-name> <skill-name>`

Examples:
- `/tag-lab eigrp/lab-07 gemini-2.0-flash create-lab`
- `/tag-lab eigrp/lab-07-filtering-route-maps kimi-k2.5 inject-faults`

Resolution rules:
- `chapter` = first path segment (e.g., `eigrp`)
- `lab-slug` = second path segment — match by prefix glob if partial (e.g., `lab-07` matches `lab-07-filtering-route-maps`)
- Full lab path: `labs/<topic>/lab-NN-<slug>/`
- `agent-name` = second argument as-is (e.g., `gemini-2.0-flash`, `kimi-k2.5`, `claude-sonnet-4-6`)
- `skill-name` = third argument as-is (e.g., `create-lab`, `inject-faults`, `chapter-topics`)

If the lab directory cannot be resolved, stop and report the available lab directories for that chapter.

--# Step 2: Get skill_version

Run: `git -C .agent/skills log --format="%ci" -1`

Take the date portion only (YYYY-MM-DD).

--# Step 3: List lab files

Glob all files in the lab directory recursively. Produce a sorted list of relative paths (relative to the lab dir root). Exclude `meta.yaml` itself.

Example output:
```
initial-configs/R1.cfg
initial-configs/R2.cfg
scripts/fault-injection/apply_solution.py
scripts/fault-injection/inject_scenario_01.py
scripts/fault-injection/README.md
setup_lab.py
solutions/R1.cfg
solutions/R2.cfg
topology.drawio
workbook.md
```

--# Step 4: Update meta.yaml

**If `meta.yaml` exists:**

Read it, then append to the `updated` list:

```yaml
updated:
  - date: "[YYYY-MM-DD today]"
    agent: [agent-name]
    skill: [skill-name]
    skill_version: "[YYYY-MM-DD from Step 2]"
    telemetry:                            # omit this entire key if telemetry is null
      model: "[telemetry.model]"
      tool_calls: [telemetry.tool_calls]
      duration_seconds: [telemetry.duration_seconds]
      session_id: "[telemetry.session_id]"
      tokens:
        input: [telemetry.tokens.input]
        output: [telemetry.tokens.output]
        cache_read: [telemetry.tokens.cache_read]
        cache_creation_5m: [telemetry.tokens.cache_creation_5m]
        cache_creation_1h: [telemetry.tokens.cache_creation_1h]
      cost_usd_estimate: [telemetry.cost_usd_estimate]
      pricing_date: "[telemetry.pricing_date]"
    files:
      - [all files from Step 3]
```

If `telemetry` is `null` (no sidecar was found in Step 0), omit the `telemetry:` key entirely — do not write null values.

Write the updated file back.

**If `meta.yaml` does not exist:**

Create it with `created.agent: unknown` to flag that original provenance was not captured, then record this run as the first `updated` entry:

```yaml
# Auto-generated — do not edit manually. Use /tag-lab to stamp external agent runs.
lab: [lab-dir-name]
chapter: [chapter]
created:
  date: "unknown"
  agent: unknown
  skill: unknown
  skill_version: unknown
  files: []
updated:
  - date: "[YYYY-MM-DD today]"
    agent: [agent-name]
    skill: [skill-name]
    skill_version: "[YYYY-MM-DD from Step 2]"
    telemetry:                            # omit this entire key if telemetry is null
      model: "[telemetry.model]"
      tool_calls: [telemetry.tool_calls]
      duration_seconds: [telemetry.duration_seconds]
      session_id: "[telemetry.session_id]"
      tokens:
        input: [telemetry.tokens.input]
        output: [telemetry.tokens.output]
        cache_read: [telemetry.tokens.cache_read]
        cache_creation_5m: [telemetry.tokens.cache_creation_5m]
        cache_creation_1h: [telemetry.tokens.cache_creation_1h]
      cost_usd_estimate: [telemetry.cost_usd_estimate]
      pricing_date: "[telemetry.pricing_date]"
    files:
      - [all files from Step 3]
```

If `telemetry` is `null` (no sidecar was found in Step 0), omit the `telemetry:` key entirely.

--# Step 5: Confirm

Report to the user:
- Lab path stamped
- Agent and skill recorded
- Number of files listed
- Whether this was a new `meta.yaml` or an append to an existing one
- Telemetry source: `last_run.json` / none (omitted)
- If `cost_usd_estimate` was non-null, surface the figure (e.g., `est. cost: $0.84`)

-# Examples

User: `/tag-lab eigrp/lab-07 gemini-2.0-flash create-lab`

Actions:
1. Resolve lab dir → `labs/eigrp/lab-07-filtering-route-maps/`
2. Run git command → `skill_version: "2026-02-27"`
3. Glob lab dir → list of 14 files
4. `meta.yaml` exists → append entry to `updated[]`
5. Report: "Stamped labs/eigrp/lab-07-filtering-route-maps/meta.yaml — gemini-2.0-flash / create-lab / 14 files recorded."

User: `/tag-lab eigrp/lab-03 kimi-k2.5 create-lab`

Actions:
1. Resolve → `labs/eigrp/lab-03-metrics-k-values/`
2. Get skill_version
3. Glob files
4. Append to existing `updated[]`
5. Confirm
