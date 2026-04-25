---
description: Phase 1 - Read the blueprint and generate topic-plan.yaml + empty lab folders
argument-hint: (no args - reads blueprint/<exam-code>/blueprint.md)
---

You are running Phase 1 of the three-phase lab workflow: **exam planning**.

Advisory prerequisite checks (warn, do not block):
1. Locate `blueprint/` at the repo root. If it is missing, warn that bootstrap is incomplete and stop.
2. Find the exam-code subdirectory under `blueprint/` (e.g., `blueprint/300-410/`). If there is more than one, ask which to use.
3. Check that `blueprint/<exam-code>/blueprint.md` exists and is non-empty. If missing or empty, warn that the blueprint has not been uploaded yet and ask whether to proceed anyway.
4. If `specs/topic-plan.yaml` already exists, warn that re-running will overwrite or conflict with it and confirm before continuing.

Then read `.agent/skills/exam-planner/SKILL.md` and execute it end-to-end. The skill is responsible for:
- Parsing the full blueprint
- Writing `specs/topic-plan.yaml`
- Creating empty `labs/<topic>/` folders per the plan

When the topic plan is approved, **fill the Suggested Practice Order in `README.md`**:
1. Read the `build_order`, topic names, `dependencies`, and `scope_notes` from `specs/topic-plan.yaml`.
2. Find the `<!-- practice-order-start -->` / `<!-- practice-order-end -->` markers in `README.md`. If absent, the README is from before this convention — warn the user and skip this step (they should re-render from the template).
3. Replace **only** the lines between the markers (preserving the marker lines themselves) with a numbered list, one entry per topic in `build_order`:

```
1. **<topic-slug>** — <one-line summary distilled from scope_notes> · *needs <comma-separated dependencies>*
2. ...
```

The `· *needs ...*` suffix is omitted for topics with no dependencies. Keep each summary under ~12 words.

4. Do **not** modify `README.md` outside the markers. Do **not** modify `STATUS.md` — that is `/project-status`'s job.
5. Write the updated `README.md` and commit it alongside `specs/topic-plan.yaml` and the empty `labs/` folders.

Finish by summarising the generated topic list and pointing the user at `/create-spec <topic-slug>` for Phase 2.
