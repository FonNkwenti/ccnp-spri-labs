---
description: Refactor a built lab workbook to match the current lab-assembler template — full pass by default, or scoped with a flag
argument-hint: <topic-slug>/<lab-id> [--concepts | --section N | --all]
---

You are refactoring an already-built lab workbook so it conforms to the **current** lab-assembler template. Older labs were built before later improvements to the template; this command closes those gaps.

Target arguments: `$ARGUMENTS`

## Argument parsing

1. **First positional argument** is the lab path in the form `<topic-slug>/<lab-id>` (e.g. `segment-routing/lab-03-sr-te-policies-and-steering`). If missing, ask the user and stop until they answer.
2. **Flags** (mutually exclusive — accept whichever appears, default to `--all` if none given):
   - `--concepts` — refactor Section 1 (Concepts & Skills Covered) only. See "Section 1 — Concepts framing" below.
   - `--section N` — refactor Section N only (N ∈ 1..11). Use the Section N spec + checklist in `lab-assembler/SKILL.md` as the contract.
   - `--all` (default) — full workbook refactor. Diff every section against the lab-assembler template, identify gaps, and fix them section by section.

If you see an unrecognized flag, stop and tell the user which flags are supported.

## Advisory prerequisite checks (warn, do not block)

1. If `labs/$1/workbook.md` does not exist, warn and stop — there is nothing to refactor.
2. If the lab has no `initial-configs/` or `solutions/` directory, warn that the lab does not look fully built but allow the refactor to proceed.

## What "refactor" means

You are aligning an existing workbook with the **current** `.agent/skills/lab-assembler/SKILL.md` spec. The skill file is the single source of truth — read it fresh every invocation, because it evolves.

**Do NOT:**
- Rewrite lab pedagogy, change Section 5 tasks, or invent content that isn't already implied by the existing workbook + spec
- Re-derive the topology, cabling, addressing, or Console Access Table from anything other than the existing workbook (those reflect already-built configs and EVE-NG state)
- Change scenario narratives, ticket wording, or solution configs unless the template explicitly mandates a format change
- Touch sections outside the requested scope (`--section N` and `--concepts` are surgical)
- Commit. The user reviews and commits separately.

**Do:**
- Treat the lab-assembler spec as authoritative for format, ordering, required tables, required subsections, and checklists
- Preserve all existing pedagogical content — only its packaging is being adjusted
- Be conservative: if a gap is ambiguous (the spec is unclear, or fixing it would require inventing technical content), flag it in the summary instead of guessing

## Procedure

### Step 1 — Load the template

Read `.agent/skills/lab-assembler/SKILL.md` end to end. The Section specs (`Section 1 — ...`, `Section 4 — IS/NOT pre-loaded format`, `Section 5 — Tasks format`, etc.) and the per-section checklists near the end of that file together define the current template.

### Step 2 — Read the target workbook

Read `labs/$1/workbook.md` in full.

### Step 3 — Scope the diff

- If `--concepts` → only check Section 1 against the Section 1 spec + checklist.
- If `--section N` → only check Section N.
- If `--all` (default) → check every section (1 through 11) plus the Table of Contents and document-level checklist items.

For each section in scope, produce an internal list of concrete gaps: missing required subsections, missing tables, headings that don't match the required form, checklists items that fail. Be specific — "Section 3 is missing the Loopback Address table required immediately after Device Inventory" beats "Section 3 doesn't match the template."

### Step 4 — Apply fixes

Apply the fixes in section order (lowest section number first). For each section:

1. State to the user (one short line): "Section N: <fix summary>." If there are no gaps in that section, say "Section N: no changes."
2. Edit the workbook with the smallest change that closes the gap. Preserve surrounding content verbatim.
3. If a gap requires content you cannot derive from the existing workbook + spec (e.g. the spec mandates a roles table for Section 1 but the framing analogy isn't obvious), STOP that section's fix and add the gap to a "Deferred — needs author input" list to report at the end.

### Step 5 — Verify

After all edits, re-read the affected sections and walk the relevant per-section checklist(s) from `lab-assembler/SKILL.md`. Confirm every checklist item passes for in-scope sections.

### Step 6 — Report

Print a summary to the user containing:
- The flag used and the sections in scope
- One bullet per section: "Section N: <one-line description of what changed>" or "Section N: no changes"
- The "Deferred — needs author input" list, if any, with one bullet per deferred gap and what input is needed

Do NOT commit. The user reviews and commits separately.

## Section 1 — Concepts framing (used by `--concepts` and by `--all`)

When refactoring Section 1, apply the framing pattern defined in `lab-assembler/SKILL.md` (Section 1 spec, parts c and d). The pattern has two halves — both must land in the same pass:

**Half 1 — Insert the framing subsection.** Immediately after the intro paragraph that follows the `**Exam Objective:**` line, and BEFORE the first `### <feature>` subsection, insert (or revise in place if present) a `### The Problem This Lab Solves` block with three parts:
- Problem statement (1-2 paragraphs) ending with a single bolded sentence naming the mechanism that closes the gap
- `| Piece | Role in the overall goal |` table — one row per feature subsection that follows, in subsection order
- `**Analogy — <name>.**` block with a bulleted list mapping each Piece to its real-world counterpart, closing with a one-line bridge to the subsections below

**Half 2 — Add tie-back sentences.** For every `### <feature>` subsection inside Section 1, insert a single italicized tie-back sentence as the first body line. It must reference the framing's roles table or analogy and phrase it naturally — no fixed prefix like "Where this fits the goal:". Examples: `*The intent container from the analogy — <what this subsection covers>.*` / `*The fallback ladder from the analogy — <what this subsection covers>.*`.

If Section 1 already has a `### The Problem This Lab Solves` block and tie-back sentences on every feature subsection, report "Section 1: no changes" and do nothing.

If the existing intro lacks enough material to build the analogy (e.g. only one or two features in scope, or the lab's goal isn't clear from the intro), defer the analogy and report it in the "needs author input" list rather than inventing one.
