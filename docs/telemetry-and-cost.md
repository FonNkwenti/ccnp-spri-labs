# Lab Build Telemetry & Cost Tracking

Every lab build records who built it, with which model, how long it took, how many tokens it consumed, and an estimated USD cost. This data lives inside the lab's own `meta.yaml`, so the lab carries its provenance + cost record with it forever.

## What gets recorded

Each build appends an entry to the `updated[]` array in `labs/<topic>/<lab>/meta.yaml`:

```yaml
updated:
  - date: "2026-05-06"
    agent: claude-opus-4-7
    skill: build-lab
    skill_version: "2026-05-01"
    telemetry:
      model: "claude-opus-4-7"
      tool_calls: 31
      duration_seconds: 5073
      session_id: "abc123..."
      tokens:
        input: 86
        output: 36848
        cache_read: 2727515
        cache_creation_5m: 80520
        cache_creation_1h: 37352
      cost_usd_estimate: 9.4865
      pricing_date: "2026-05-06"
    files:
      - workbook.md
      - solutions/R1.cfg
      - ...
```

### Field reference

| Field | Meaning | Notes |
|---|---|---|
| `model` | Exact Anthropic model ID | Sourced from the transcript, not user-supplied |
| `tool_calls` | Total `tool_use` blocks across the session | Includes reads, edits, bash, subagent dispatches |
| `duration_seconds` | First-to-last timestamp in the transcript | Includes user think-time — overstates compute time |
| `tokens.input` | Fresh input tokens (not cached) | Charged at full input rate |
| `tokens.output` | Generated tokens | Charged at full output rate (5x input) |
| `tokens.cache_read` | Tokens served from prompt cache | Charged at 10% of input rate — cheap |
| `tokens.cache_creation_5m` | Tokens written to 5-minute cache | Charged at 125% of input rate |
| `tokens.cache_creation_1h` | Tokens written to 1-hour cache | Charged at 200% of input rate |
| `cost_usd_estimate` | Computed at write time | `null` if model not in pricing table |
| `pricing_date` | Date the rates in the pricing table were verified | Use this to detect stale estimates |

## The two telemetry sources

The build flow uses **only the Stop hook**. Inline telemetry stamping was removed to ensure every build records full token + cost data.

```
session start
  /build-lab <topic>/<lab>
    -> builds workbook, configs, topology, scripts
    -> tells you: "end session and run /tag-lab in a fresh session"
session ends
  Stop hook fires:
    .claude/hooks/capture_telemetry.py reads transcript JSONL
    aggregates per-turn usage blocks
    writes .claude/last_run.json with tokens + cost_usd_estimate

new session
  /tag-lab <topic>/<lab> <model-id> build-lab
    reads .claude/last_run.json
    appends an entry to labs/<topic>/<lab>/meta.yaml
```

`last_run.json` is a rolling record overwritten on every session end. Tag a build before starting a new significant session, otherwise the data gets clobbered.

## Cost model

Computed inside the Stop hook at `.claude/hooks/capture_telemetry.py`:

```
cost_usd =
    input_tokens             * input_price / 1M
  + output_tokens            * output_price / 1M
  + cache_read_tokens        * input_price * 0.10 / 1M
  + cache_creation_5m_tokens * input_price * 1.25 / 1M
  + cache_creation_1h_tokens * input_price * 2.00 / 1M
```

Pricing table (verified `pricing_date: 2026-05-06`):

| Model prefix | $/MTok input | $/MTok output |
|---|---|---|
| `claude-opus-4` | 15.00 | 75.00 |
| `claude-sonnet-4` | 3.00 | 15.00 |
| `claude-haiku-4` | 1.00 | 5.00 |

Models outside the prefix list (e.g., a future 5.x) record token counts but leave `cost_usd_estimate: null`. To update prices: edit the `MODEL_PRICING` dict at `.claude/hooks/capture_telemetry.py:21` and bump `PRICING_DATE`.

## Building the same lab with multiple models

Labs are built independently. Whether you build the same lab twice in parallel sessions or revisit an old lab months later with a different model, each run appends a fresh entry to `updated[]`. No special tooling required.

### Example: Opus vs Haiku on the same lab

```yaml
updated:
  - date: "2026-05-06"
    agent: claude-opus-4-7
    telemetry:
      model: "claude-opus-4-7"
      tool_calls: 31
      cost_usd_estimate: 9.4865
      ...
  - date: "2026-05-12"
    agent: claude-haiku-4-5-20251001
    telemetry:
      model: "claude-haiku-4-5-20251001"
      tool_calls: 142
      cost_usd_estimate: 0.6231
      ...
```

The Haiku build used 4.5x more tool calls but cost 15x less. Whether that's a good trade depends on output quality — which is what comparative analysis answers.

## Comparative analysis

When you want to compare builds, prompt Claude with the lab paths. Example:

> Compare these two builds of the same lab:
> - `labs/bgp/lab-05-communities-flowspec/` (built with Opus 4.7)
> - `labs/bgp-haiku/lab-05-communities-flowspec/` (built with Haiku 4.5)
>
> Look at meta.yaml telemetry for cost/effort, and diff workbook.md +
> solutions/*.cfg for output quality. Which model gave better value?

Claude has everything it needs:
- `meta.yaml` telemetry blocks for cost / token / duration deltas
- File diffs for output quality
- `decisions.md` for any model-gate overrides

If `pricing_date` is older than today, ask Claude to recompute USD estimates from the raw token counts using current prices.

## Stale estimates

Anthropic prices change. If you see `pricing_date: "2026-05-06"` on a build from a year ago and current prices differ:

1. The raw `tokens.{input,output,cache_read,cache_creation_5m,cache_creation_1h}` fields are still authoritative — they're the actual usage Anthropic billed.
2. Update `MODEL_PRICING` and `PRICING_DATE` in `.claude/hooks/capture_telemetry.py`.
3. New builds use the new prices automatically. Old `cost_usd_estimate` values stay at the old rate (with their `pricing_date` flagging them as stale).
4. To recompute an old estimate, pass the tokens block to Claude with current prices — no script needed.

## Related files

| Path | Role |
|---|---|
| `.claude/hooks/capture_telemetry.py` | Stop hook — parses transcript, writes `last_run.json` |
| `.claude/last_run.json` | Rolling per-session record |
| `.claude/skills/tag-lab/SKILL.md` | Reads `last_run.json`, stamps `meta.yaml` |
| `.claude/commands/build-lab.md` | Build command — no longer writes telemetry inline |
| `labs/<topic>/<lab>/meta.yaml` | Permanent provenance + telemetry record per lab |
