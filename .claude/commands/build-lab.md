---
description: Phase 3 - Build one lab (workbook, configs, topology, scripts) from its spec
argument-hint: <topic-slug>/<lab-id> [--force-model]
---

You are running Phase 3 of the three-phase lab workflow: **lab build** for `$ARGUMENTS`.

## Argument parsing

1. If `$ARGUMENTS` is empty, ask the user for the full path and STOP until they answer.
2. Strip the `--force-model` flag from `$ARGUMENTS` if present. Set `force_model = true`.
3. Normalize the path: strip any leading `labs/` or `labs\` prefix (with or without trailing
   separator) from the remaining token. The result must be of the form `<topic-slug>/<lab-id>`
   (forward or back slashes accepted — normalize to forward slashes internally).
   If it is not, ask the user for the correct path and STOP.
   Examples of equivalent inputs that all resolve to `routing-policy/lab-03-igp-route-manipulation`:
   - `routing-policy/lab-03-igp-route-manipulation`
   - `labs/routing-policy/lab-03-igp-route-manipulation`
   - `labs\routing-policy\lab-03-igp-route-manipulation`

## HARD PRE-FLIGHT GATE — model enforcement (BLOCKING)

This gate runs BEFORE any skill read, BEFORE any file write, BEFORE any subagent dispatch.
You MUST complete this gate before proceeding. Do not skip it.

1. **Read policy:** Read `.agent/skills/model-policy.yaml`.
2. **Read lab difficulty:** Read `labs/<topic-slug>/baseline.yaml` and find the entry
   under `labs:` whose `folder` matches `<lab-id>` (strip any `-haiku` / `-sonnet` / `-opus` /
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
     To use the recommended model, exit and restart Claude Code with the correct model,
     then re-run this command.
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

Use the normalized `<topic-slug>/<lab-id>` from argument parsing above. Let `TOPIC=<topic-slug>` and `LAB_PATH=labs/<topic-slug>/<lab-id>`.

1. If `LAB_PATH/` does not exist or is empty — **proceed silently**. This is the normal post-Phase 2 state: `/create-spec` scaffolds empty lab folders. No approval needed; `lab-assembler` will populate it.
2. If `labs/TOPIC/spec.md` does not exist, warn that Phase 2 has not run for this topic and suggest `/create-spec <topic-slug>`. Ask whether to proceed anyway.
3. If `labs/TOPIC/baseline.yaml` is missing, warn before proceeding.
4. If `LAB_PATH/workbook.md` already exists, warn that re-running will rewrite it and confirm.

Then read `.agent/skills/lab-assembler/SKILL.md` and execute it for `$ARGUMENTS`. Per `CLAUDE.md`, `lab-assembler` dispatches `drawio` and `fault-injector` as subagents at the appropriate steps - let it handle that; do not invoke those skills directly.

Note: this command builds **one** lab. To build every lab in a topic with a review gate between each, use `/build-topic <topic-slug>` instead (that routes to the `lab-builder` orchestrator).

When the lab is approved, **update `README.md`**:
1. Parse `$ARGUMENTS` as `<topic-slug>/<lab-id>`.
2. In the `### <topic-slug>` section between the `<!-- lab-index-start -->` / `<!-- lab-index-end -->` markers, find the line containing `- [ ] \`<lab-id>\`` and change `[ ]` to `[x]`.
3. Write the updated `README.md`.

Then suggest `/tag-lab $ARGUMENTS` and point the user at the next unbuilt lab in the same topic.
