---
description: Phase 3 - Build every lab for a topic with a review gate between each
argument-hint: <topic-slug> [--force-model]
---

You are running Phase 3 of the three-phase lab workflow at the **topic level** for `$ARGUMENTS`. This uses the `lab-builder` orchestrator, which iterates every lab in `baseline.yaml labs[]` and pauses for user approval between each one.

## Argument parsing

1. If `$ARGUMENTS` is empty, ask the user which topic slug to build (offer the list from `specs/topic-plan.yaml` if available) and STOP.
2. Detect the `--force-model` flag anywhere in `$ARGUMENTS`. Set `force_model = true` if present. Strip the flag before using `$ARGUMENTS` as a topic slug.

## HARD PRE-FLIGHT GATE — model enforcement (per lab, BLOCKING)

This gate runs **once per lab** inside the topic loop, not once for the topic — because
different labs in the same topic can have different difficulty tiers.

Before invoking `lab-assembler` for each lab:
1. Read `.agent/skills/model-policy.yaml` (once, cache for the whole topic run).
2. From `labs/<topic>/baseline.yaml`, read this lab's `difficulty`.
3. Self-identify your exact model ID from the system prompt ("The exact model ID is …").
4. If your model ID is NOT in `tiers[difficulty].allowed_models`:
   - If `force_model == true`: log `[GATE OVERRIDDEN] <lab-id> on <model> for <tier>`,
     append an entry to that lab's `decisions.md`, and continue.
   - Otherwise: **STOP the whole topic build**. Output:

     ```
     [TOPIC BUILD HALTED] Lab <lab-id> requires one of <allowed_models> for <difficulty> tier.
     Your model: <your exact model ID>. Remaining labs in topic will not be built.
     Re-run with /build-topic <topic> --force-model to override, or switch models.
     ```

     Do NOT proceed to the next lab in the topic loop.
5. If the gate passes, append to this lab's `decisions.md`:

   ```markdown
   ## Model gate — <YYYY-MM-DD>
   - Difficulty: <difficulty>
   - Running model: <your exact model ID>
   - Allowed models: <list>
   - Outcome: <PASS | OVERRIDDEN via --force-model>
   ```

   Then continue with the build for that lab.

The topic build halts at the first gate failure rather than skip-and-continue because
a mismatch usually means the user picked the wrong model for the whole session, not
that only one lab is wrong.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/spec.md` or `labs/$ARGUMENTS/baseline.yaml` is missing, warn that Phase 2 has not run for this topic and suggest `/create-spec $ARGUMENTS`. Ask whether to proceed anyway.
2. If any lab folder under `labs/$ARGUMENTS/` already contains a `workbook.md`, warn that those labs will be re-built (overwritten) and confirm before continuing.

Then read `.agent/skills/lab-builder/SKILL.md` and execute it for topic `$ARGUMENTS`. The orchestrator is responsible for:
- Parsing `labs[]` from `baseline.yaml`
- Invoking `lab-assembler` for each lab in order
- Enforcing the pause-for-review gate after each lab (do not skip these pauses, even if the user seems eager)
- Running the Step 3 validation checklist after all labs are approved

After **each individual lab** is approved during the topic build, update `README.md` immediately:
- In the `### $ARGUMENTS` section between the `<!-- lab-index-start -->` / `<!-- lab-index-end -->` markers, find the line `- [ ] \`<lab-id>\`` for the just-approved lab and change `[ ]` to `[x]`.
- Write the updated `README.md` before pausing for the next lab.

To build a single lab without the topic loop, use `/build-lab <topic>/<lab-id>` instead (that calls `lab-assembler` directly).
