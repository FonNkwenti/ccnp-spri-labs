---
description: Refresh STATUS.md with the current phase and lab build state, and report the next command
argument-hint: (no args)
model: claude-haiku-4-5-20251001
---

Refresh `STATUS.md` at the repo root with a current snapshot of where this exam repo sits in the three-phase workflow, then report a short summary in chat.

`STATUS.md` is the live build dashboard. `README.md` stays stable — do not modify it.

## Step 1 — Gather data

1. **Blueprint**: does `blueprint/<exam-code>/blueprint.md` exist and is it non-empty? Capture the objective count if listed in the file header (e.g. "94 objectives").
2. **Phase 1 (plan)**: does `specs/topic-plan.yaml` exist? If yes, parse the topic slugs in `build_order` and the `summary` block (`total_topics`, `total_estimated_labs`).
3. **Phase 2 (specs)**: for each topic slug, check whether `labs/<topic>/spec.md` and `labs/<topic>/baseline.yaml` exist.
4. **Phase 3 (builds)**: for each topic, list lab folders under `labs/<topic>/` and check whether each contains `workbook.md`. A lab counts as "built" only if `workbook.md` exists.
5. **Progress memo**: if `memory/progress.md` or `.agent/skills/memory/progress.md` exists, capture the most recent dated entries as recent activity (1-3 lines).
6. **Skills pin**: run `git submodule status .agent/skills` and capture the short commit hash + branch.

## Step 2 — Compute marker body content

Build the text that will go inside each `<!-- *-start --> ... <!-- *-end -->` block in STATUS.md.

### `<!-- status-meta-start -->` body
```
**Last updated:** YYYY-MM-DD
**Skills pin:** `<short-sha>` (heads/main)
**Blueprint:** [`blueprint/<exam-code>/blueprint.md`](blueprint/<exam-code>/blueprint.md) (<N> objectives)
```

### `<!-- phase-summary-start -->` body
A 3-row markdown table with one of these states per phase: `— not started`, `⧗ in progress`, `✓ complete`, `⚠ needs review`.

- Phase 1 = `✓ complete` if `specs/topic-plan.yaml` exists and is non-empty
- Phase 2 = `✓ complete` if every topic has both `spec.md` and `baseline.yaml`; `⧗ in progress` if some do; `— not started` if none
- Phase 3 = `✓ complete` only if every planned lab has `workbook.md`; `⧗ in progress` if any do; `— not started` otherwise

### `<!-- topic-matrix-start -->` body
The two header rows of the matrix (`| Topic | Spec | Labs Built / Planned | Notes |` and the separator) followed by one row per topic in `build_order`:

```
| <topic> | ✓ or — | <built>/<planned> | <one-line note from spec_notes or empty> |
```

`<built>` = count of lab folders with `workbook.md`. `<planned>` = `estimated_labs` from topic-plan.

### `<!-- recent-activity-start -->` body
The two or three most recent dated entries from `memory/progress.md` as a bullet list. If none exist, write `_no recent activity logged_`.

### `<!-- next-step-start -->` body
A single line recommending the next command, pointing at the earliest incomplete step:

- No blueprint → ``Upload blueprint to `blueprint/<exam-code>/blueprint.md`, then run `/plan-exam`.``
- No `topic-plan.yaml` → `` Run `/plan-exam`. ``
- A topic missing `spec.md` → `` Run `/create-spec <topic>`. ``
- A topic with spec but unbuilt labs → `` Run `/build-lab <topic>/<lab-id>` (next lab in build_order). ``
- All built → `` All labs built. Consider `/build-capstone` or review/tag passes. ``

## Step 3 — Write `STATUS.md`

**If `STATUS.md` does not exist:**
1. Read `.agent/skills/scaffolding/STATUS_template.md`.
2. Substitute the title-area variables that bootstrap normally fills:
   - `{{EXAM_SHORT}}` → from `CLAUDE.md` (the certification short name)
   - `{{EXAM_CODE}}` → from `CLAUDE.md` or `topic-plan.yaml`
3. Replace each `{{VAR}}` inside the markers with the bodies computed in Step 2.
4. Write the result to `STATUS.md`.

**If `STATUS.md` already exists:**
1. Read the current `STATUS.md`.
2. For each marker pair (`status-meta`, `phase-summary`, `topic-matrix`, `recent-activity`, `next-step`), replace only the lines between `<!-- <name>-start -->` and `<!-- <name>-end -->` with the new body. Keep the marker lines themselves intact.
3. Do not touch any content outside the markers — that is hand-curated and must be preserved.
4. Write the updated content back to `STATUS.md`.

Use Edit (one Edit call per marker block, with the marker lines as the unique anchors) for idempotent updates.

## Step 4 — Report to chat

Print a brief summary the user can read at a glance:

1. The 3-row phase summary (with state icons).
2. The topic matrix table.
3. The single-line "Next" recommendation.
4. One line: `Wrote STATUS.md` (or `Updated STATUS.md`).

Do not modify `README.md`, `topic-plan.yaml`, or any spec/baseline file.
