# Hard Model Enforcement — Paste-Ready

Adds a hard pre-flight gate to `/build-lab` and `/build-topic` that aborts if
the running model doesn't match the lab's difficulty tier. Uses the existing
`difficulty` field already in every `baseline.yaml` (`Foundation` |
`Intermediate` | `Advanced`) — no spec changes needed.

## How enforcement works

1. **Policy file** (`.agent/skills/model-policy.yaml`, new) — maps each
   difficulty tier to its allowed model IDs.
2. **Slash commands** (`build-lab.md`, `build-topic.md`) — before invoking
   the skill, read the lab's `difficulty`, look up allowed models, compare
   against the agent's own `exact model ID` (self-reported in the system
   prompt). Abort with an explicit message on mismatch.
3. **Escape hatch** — `/build-lab <path> --force-model` skips the gate for
   intentional overrides (drafts with cheaper model, experiments, etc.). The
   override is logged in `decisions.md` so reviewers see it.
4. **Logged outcome** — every gate check (pass, fail, override) goes into
   the lab's `decisions.md` so the provenance is auditable.

The gate can't physically swap the model — Claude Code routes tool calls to
whatever model the user has active. What the gate CAN do is make the
standard workflow refuse to proceed, which covers 95% of real-world
"distracted operator" mistakes. For the remaining 5%, hooks at the
Claude Code settings level (pre-tool-use blocking) are the only true
enforcement — noted at the end as future work.

---

## File 1 (NEW) — `.agent/skills/model-policy.yaml`

Create this file at the root of the skills submodule.

```yaml
# Model policy for lab builds.
# Owned by the skills submodule — one edit here propagates to every exam repo.
#
# Difficulty tiers come from baseline.yaml labs[N].difficulty.
# Each tier lists the model IDs that are ALLOWED to run a build for that tier.
# A build is REFUSED unless the running agent's model ID is in the allowed list
# (or the user passed --force-model to the slash command).

version: 1
updated: "2026-04-24"

tiers:
  Foundation:
    # Foundation labs are low-stakes scaffolding; any model tier is acceptable.
    allowed_models:
      - claude-haiku-4-5-20251001
      - claude-sonnet-4-6
      - claude-opus-4-7
    recommended: claude-sonnet-4-6
    notes: "Sonnet is default; Haiku acceptable for drafts; Opus overkill."

  Intermediate:
    # Intermediate labs need Sonnet's pedagogical depth. Haiku is too thin.
    allowed_models:
      - claude-sonnet-4-6
      - claude-opus-4-7
    recommended: claude-sonnet-4-6
    notes: "Sonnet is the production default for student-facing labs."

  Advanced:
    # Advanced/capstone labs demand Opus-level reasoning and reference depth.
    allowed_models:
      - claude-opus-4-7
    recommended: claude-opus-4-7
    notes: "Opus only — the complexity justifies the cost."

# Effort-level guidance (advisory, not enforced — tracked in telemetry only)
effort_guidance:
  Foundation: medium
  Intermediate: high
  Advanced: high

# Deprecation / migration notes — when rotating model IDs:
# 1. Add the new model ID to allowed_models for each tier where it qualifies.
# 2. Keep the old ID for one release cycle so in-flight builds don't break.
# 3. After the cycle, remove the old ID and bump `version`.
```

---

## File 2 (EDIT) — `.claude/commands/build-lab.md`

**File:** `.claude/commands/build-lab.md`

**Find the current opening (first ~8 lines):**

```
---
description: Phase 3 - Build one lab (workbook, configs, topology, scripts) from its spec
argument-hint: <topic-slug>/<lab-id>
---

You are running Phase 3 of the three-phase lab workflow: **lab build** for `$ARGUMENTS`.

If `$ARGUMENTS` is empty or not of the form `<topic-slug>/<lab-id>`, ask the user for the full path and stop until they answer.

Advisory prerequisite checks (warn, do not block):
```

**Replace with:**

```
---
description: Phase 3 - Build one lab (workbook, configs, topology, scripts) from its spec
argument-hint: <topic-slug>/<lab-id> [--force-model]
---

You are running Phase 3 of the three-phase lab workflow: **lab build** for `$ARGUMENTS`.

## Argument parsing

1. If `$ARGUMENTS` is empty, ask the user for the full path and STOP until they answer.
2. Parse `$ARGUMENTS`. The first token must be of the form `<topic-slug>/<lab-id>`.
   If it is not, ask the user for the full path and STOP.
3. Detect the `--force-model` flag anywhere in `$ARGUMENTS`. Set `force_model = true` if present.

## HARD PRE-FLIGHT GATE — model enforcement (BLOCKING)

This gate runs BEFORE any skill read, BEFORE any file write, BEFORE any subagent dispatch.
You MUST complete this gate before proceeding. Do not skip it.

1. **Read policy:** Read `.agent/skills/model-policy.yaml`.
2. **Read lab difficulty:** Read `labs/<topic-slug>/baseline.yaml` and find the entry
   under `labs:` whose `id` matches `<lab-id>` (strip any `-haiku` / `-sonnet` / `-opus` /
   `-medium` / `-force` model-variant suffix for the lookup — variant suffixes are
   build-tags, not distinct labs). Extract `difficulty` from that entry.
   - If `baseline.yaml` is missing OR the lab entry is not found OR `difficulty` is
     unset: WARN and ask whether to proceed as `Intermediate` (fallback default).
3. **Look up allowed models:** From `model-policy.yaml`, find `tiers[<difficulty>].allowed_models`.
4. **Self-identify:** Your own exact model ID is declared in your system prompt under
   "The exact model ID is …". Extract that value literally — do not guess or substitute.
5. **Compare:**
   - If your model ID IS in `allowed_models` → gate PASSES. Proceed.
   - If your model ID is NOT in `allowed_models` AND `force_model == false` → gate FAILS.
     You MUST STOP now. Output exactly this message and then stop without invoking any tool:

     ```
     [GATE FAILED] Model mismatch for <topic-slug>/<lab-id>
       Lab difficulty : <difficulty>
       Allowed models : <comma-separated list from policy>
       Your model     : <your exact model ID>
       Recommended    : <tiers[difficulty].recommended>

     To proceed anyway, re-run: /build-lab <topic-slug>/<lab-id> --force-model
     To use the recommended model, exit and restart Claude Code with /model claude-opus-4-7
     (or whichever the recommendation specifies), then re-run this command.
     ```

   - If your model ID is NOT in `allowed_models` AND `force_model == true` → gate OVERRIDDEN.
     Log this prominently: "[GATE OVERRIDDEN] Building <lab-id> on <your model> for <difficulty>
     tier (allowed: <list>) via --force-model. Provenance will be stamped in decisions.md."
     Proceed.

6. **Record the gate outcome** — after the build completes, append to `labs/<topic-slug>/<lab-id>/decisions.md`:

   ```markdown
   ## Model gate — <YYYY-MM-DD>
   - Difficulty: <difficulty>
   - Running model: <your exact model ID>
   - Allowed models: <list>
   - Outcome: <PASS | OVERRIDDEN via --force-model>
   ```

   If `decisions.md` does not exist, create it with this entry as Section 1.

## Advisory prerequisite checks (warn, do not block):
```

(Keep the existing numbered advisory checks and everything below unchanged.)

---

## File 3 (EDIT) — `.claude/commands/build-topic.md`

**File:** `.claude/commands/build-topic.md`

This command builds every lab in a topic. The gate must run **once per lab**,
not once for the topic — because different labs in the same topic can have
different difficulty tiers.

**Find** the section that invokes `lab-builder` or iterates labs, and **insert**
the following block immediately before each per-lab build:

```
## HARD PRE-FLIGHT GATE — model enforcement (per lab, BLOCKING)

Before invoking `lab-assembler` for this lab:
1. Read `.agent/skills/model-policy.yaml`.
2. From `labs/<topic>/baseline.yaml`, read this lab's `difficulty`.
3. Self-identify your model ID from the system prompt.
4. If your model is NOT in `tiers[difficulty].allowed_models`:
   - If user passed `--force-model` at the /build-topic invocation: log `[GATE OVERRIDDEN]`
     and continue.
   - Otherwise: STOP the whole topic build. Output:

     ```
     [TOPIC BUILD HALTED] Lab <lab-id> requires one of <allowed_models> for <difficulty> tier.
     Your model: <your ID>. Remaining labs in topic will not be built.
     Re-run with /build-topic <topic> --force-model to override, or switch models.
     ```

   Do NOT proceed to the next lab in the topic loop after a gate failure.

If the gate passes, log the outcome to this lab's `decisions.md` and continue with the build.
```

The topic build should **halt at the first gate failure** rather than skip-and-continue,
because a mismatch usually means the user picked the wrong model for the whole session,
not that only one lab is wrong.

---

## File 4 (EDIT) — `spec-creator/SKILL.md`

Make the `difficulty` field in `baseline.yaml` non-optional so the gate always
has something to read.

**File:** `.agent/skills/spec-creator/SKILL.md`

**Find** the section that documents the `labs:` array schema in `baseline.yaml`
(search for `difficulty` — should appear in the schema description).

**Ensure** the schema description contains the following requirement (add if
missing, or tighten if already present):

```
## Required per-lab fields in baseline.yaml labs[]:

- `id` — directory name stem (e.g., lab-01-multiarea-ospfv2)
- `title` — human-readable title
- `difficulty` — REQUIRED. One of: Foundation | Intermediate | Advanced.
  This field drives the hard model-enforcement gate in /build-lab and /build-topic.
  A missing or invalid difficulty will cause the gate to fall back to "Intermediate"
  and warn the user. Pick the tier honestly — do not downgrade difficulty to enable
  a cheaper model. Difficulty reflects the lab's pedagogical rigor, not your budget.
- `blueprint_refs` — list of exam-blueprint bullet IDs this lab covers
- `devices` — active devices from core_topology.devices
- ... (remaining existing fields)

## Difficulty tier definitions (for spec authors):

- **Foundation** — first lab of a topic; single concept; minimal prior knowledge.
  Scaffolds into later labs. Example: lab-00-single-area-ospfv2.
- **Intermediate** — combines 2–3 concepts; exercises real troubleshooting.
  The meat of the certification. Example: lab-01-multiarea-ospfv2.
- **Advanced** — capstone-style; spans multiple areas; open-ended troubleshooting
  or design justification. Example: multi-topic capstones.
```

---

## File 5 (NEW) — docs entry in the submodule

**File:** `.agent/skills/MODEL-POLICY.md` (new, at submodule root)

```markdown
# Model Policy

The skills submodule ships a `model-policy.yaml` that defines which
Anthropic model IDs are allowed to build labs at each difficulty tier.

## Why this exists

1. **Cost discipline** — Foundation labs don't need Opus-level reasoning.
   Advanced labs shouldn't be built by Haiku.
2. **Quality floor** — the OSPF lab-01 three-model comparison showed that
   Haiku ships with structural defects (misplaced drawio, thin ticket
   narratives) that are unacceptable on exam-critical content.
3. **Single source of truth** — when Anthropic rotates model IDs, this
   one file updates and every exam repo picks it up on `git submodule update`.

## Editing the policy

1. Bump `version` at the top of `model-policy.yaml`.
2. Update `tiers[*].allowed_models` and `recommended` as needed.
3. Append an entry to this doc under "Change log".
4. Commit to the skills submodule; exam repos pick it up on next submodule pull.

## Enforcement

Enforcement lives in the slash commands (`build-lab.md`, `build-topic.md`)
in each exam repo's `.claude/commands/`. The skills submodule cannot enforce
directly — it has no runtime hook into Claude Code's model selection.

Override mechanism: `--force-model` flag on either command. Overrides are
logged to the lab's `decisions.md`.

## Change log

- 2026-04-24: Initial policy. Haiku for Foundation, Sonnet for
  Foundation/Intermediate, Opus required for Advanced. Derived from the
  OSPF lab-01 three-model comparison report.
```

---

## Future work — true runtime enforcement (not implemented here)

The gate above is a *prompt-level* gate: it relies on the agent reading the
command prompt and refusing to proceed. A determined operator can bypass it
by invoking `lab-assembler` directly instead of through `/build-lab`.

For true enforcement, the Claude Code settings would need a **PreToolUse
hook** that:
1. Reads the target lab's difficulty.
2. Checks the running model against `model-policy.yaml`.
3. Returns `"decision": "block"` in the hook response if mismatched.

This lives in `.claude/settings.json` (or `~/.claude/settings.json`) as:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "python3 .claude/hooks/model-gate.py" }
        ]
      }
    ]
  }
}
```

The hook script would inspect the tool's file path, map it back to a lab,
consult `model-policy.yaml`, and block if the model is wrong. This is the
only mechanism that cannot be bypassed by direct skill invocation.

Recommended to defer until the prompt-level gate proves insufficient. Most
"distracted operator" cases are caught by the prompt gate; the hook is
belt-and-braces.

---

## Summary — files touched

| Where | File | Action |
|---|---|---|
| Skills submodule | `model-policy.yaml` | **NEW** |
| Skills submodule | `spec-creator/SKILL.md` | Edit — tighten difficulty schema |
| Skills submodule | `MODEL-POLICY.md` | **NEW** |
| Parent exam repo | `.claude/commands/build-lab.md` | Edit — prepend gate |
| Parent exam repo | `.claude/commands/build-topic.md` | Edit — per-lab gate |
| **Total** | **5 files** | **2 new, 3 edits** |

## Application order

1. Submodule first: add `model-policy.yaml`, update `spec-creator/SKILL.md`,
   add `MODEL-POLICY.md`. Commit & push in the submodule.
2. Parent repo: bump submodule pointer (`git submodule update --remote`),
   then edit the two slash commands. Commit both together.
3. Verification: run `/build-lab ospf/lab-00-single-area-ospfv2` under Haiku
   (should PASS — Foundation tier allows Haiku), then under Haiku for a
   hypothetical Advanced lab (should FAIL with gate message).

## Verification test matrix

| Test | Running model | Lab difficulty | `--force-model`? | Expected |
|---|---|---|---|---|
| 1 | Sonnet | Intermediate | no | PASS |
| 2 | Haiku | Intermediate | no | **GATE FAILED** |
| 3 | Haiku | Intermediate | yes | OVERRIDDEN — proceeds, logs to decisions.md |
| 4 | Opus | Foundation | no | PASS (Opus allowed at all tiers) |
| 5 | Haiku | Advanced | no | **GATE FAILED** |
| 6 | baseline.yaml missing difficulty | any | no | WARN + fall back to Intermediate |
