# Model Comparison Report — OSPF Lab-01 Multiarea OSPFv2

**Scope:** Three-model build comparison of identical spec (`lab-01-multiarea-ospfv2`)
executed by Haiku 4.5, Sonnet 4.6, and Opus 4.7 under the same `lab-assembler`
skill. Focus: **topology.drawio**, **workbook.md**, **setup_lab.py**, plus
self-reported telemetry.

**Date:** 2026-04-24
**Evaluator:** Synthesis of parallel file analysis across all three variants.

---

## 1. Structural Compliance (File Placement)

The `lab-assembler` skill prescribes a specific directory layout. Two of the
three builds are fully compliant.

| Path expected | Haiku | Sonnet | Opus |
|---|:---:|:---:|:---:|
| `workbook.md` (root) | ✓ | ✓ | ✓ |
| `README.md` (root) | ✓ | ✓ | ✓ |
| `meta.yaml` (root) | ✓ | ✓ | ✓ |
| `setup_lab.py` (root) | ✓ | ✓ | ✓ |
| `decisions.md` (root, optional) | — | — | ✓ (only Opus) |
| `initial-configs/R{1..5}.cfg` | ✓ | ✓ | ✓ |
| `solutions/R{1..5}.cfg` | ✓ | ✓ | ✓ |
| `topology/topology.drawio` | **✗ at lab root** | ✓ | ✓ |
| `topology/README.md` | ✓ | ✓ | ✓ |
| `scripts/fault-injection/*` | ✓ | ✓ | ✓ |
| `<model>-telemetry.md` | ✓ | ✓ | ✓ |

**Defects:**
- **Haiku:** `topology.drawio` landed at `lab-01-multiarea-ospfv2-haiku/topology.drawio`
  instead of `topology/topology.drawio`. Telemetry does not self-identify this
  defect. A student following `topology/README.md`'s "open topology.drawio"
  instruction will hit a missing file.
- **All three:** Left `__pycache__/` byproducts under `scripts/fault-injection/`
  (and in Sonnet/Opus root) from the subagent's `py_compile` check. Trivial
  cleanup gap, not a correctness defect.

---

## 2. topology.drawio — Quality Comparison

All three use the correct `mxgraph.cisco19.rect;prIcon=router` Cisco19 shape
library and the dark navy `#1a1a2e` background. Where they differ:

| Dimension | Haiku (189 lines) | Sonnet (169 lines) | Opus (151 lines) |
|---|---|---|---|
| Shape library | Cisco19 ✓ | Cisco19 ✓ | Cisco19 ✓ |
| Canvas | `#1a1a2e` ✓ | `#1a1a2e` ✓ | `#1a1a2e` ✓ |
| Area visualization | 4 colored zones, but **Area 0 & Areas 1/2/3 use only two colors** (blue + green repeated) | 4 zones in **4 distinct colors** (blue/green/orange/purple) with dashed borders and "Normal/Backbone" subtitles | 4 zones, 4 distinct colors |
| Area 3 geometry | Awkward — zone only partially encloses R3 | Correct enclosure around R3 branch point | Correct enclosure |
| Edge styling | White, 2px, no arrow | White, 2px, no arrow | White, 2px, no arrow |
| Per-interface IP labels | Last-octet floating labels | 8 last-octet floating labels | Last-octet floating labels |
| Legend | Present (bottom-right, black) | Present (bottom-right, black, most complete — includes ABR/IR abbreviations) | Present |
| Layout | Modified Y / T-shape (R1–R2–R3 linear, R5 below R3) | Y-topology (R1–R2–R3 spine, R4 upper-right, R5 lower-right) | Y-topology (same as Sonnet) |
| Placement | **Wrong folder** | Correct | Correct |
| Line count | 189 (most verbose) | 169 | 151 (most compact) |

**Winner:** **Sonnet** — four distinct area colors, clean Y-layout, most
complete legend, correct placement.
**Runner-up:** **Opus** — equivalent structural quality, slightly more compact.
**Weakest:** **Haiku** — only two repeated colors for four areas (visually
ambiguous for students learning which interface belongs to which area), wrong
folder placement.

---

## 3. workbook.md — Quality Comparison

All three produce the required 11 sections with matching titles. They diverge
sharply on **visual depth**, **theory coverage**, and **correctness**.

| Dimension | Haiku (688 lines) | Sonnet (716 lines) | Opus (908 lines) |
|---|---|---|---|
| Section count | 11 ✓ | 11 ✓ | 11 ✓ |
| Table of Contents | — | — | ✓ (only Opus has ToC) |
| ASCII topology diagram | Box-drawing chars, **inline area labels** (not bounded) — linear R1→R2→R3→R4 with R5 dropped below | Box-drawing chars, no bounded area zones in ASCII | Box-drawing chars, **bounded area rectangles** (each area enclosed as its own box) — richest ASCII of the three |
| Section 1 theory | Baseline: LSA types 1–3 narrative, 4-bullet design principles, IS-IS comparison paragraph. No Type-4/Type-5, no stub discussion | Extended: **LSA types 1–5 table**, 5-row adjacency mismatch table, ABR best-practice note (Lo0 in Area 0), ABR auto-promotion explained, Type-3 re-generation behavior | Deepest: "Why Multiarea?" motivation prose, ABR section, LSA types, explicit **backbone-rule subsection**, OSPF-vs-IS-IS contrast, design note on ABR loopback placement |
| Callouts (notes/tips) | Exam-tip blockquotes only | `> Note:` + `> Exam tip:` blockquotes | `> Design note:` + narrative framing throughout |
| Tables | 7 tables | 7+ tables (3 in Section 1 alone) | Multiple tables + ToC |
| `<details>` collapse blocks | Solutions + 3 ticket fixes | Per-task + per-ticket | Per-task + per-ticket |
| Troubleshooting tickets | 3 (2× area mismatch + 1× ABR filter) — **Ticket 3 diagnosis thin** (one show command, no narrative) | 3 distinct classes (area ID + missing network stmt + wrong wildcard) — all uniform depth | 3 distinct classes (area ID + missing network stmt + **hello/dead timer mismatch**) — unique fault class, but **Ticket 2 narrative had correctness bug** caught by advisor and fixed |
| Correctness issues | Ticket 2 fix originally wrong (`clear ip ospf process` vs ABR filter removal); corrected in commit 983d805 | None reported | Ticket 2 narrative contradicted injected fault (claimed R2 stops being ABR; Lo0 keeps it ABR); caught by advisor, rewritten pre-ship |
| Pedagogical gaps | Ticket 3 under-developed; no stub/NSSA; Task 5 optional and unlabeled | Minor; console ports left as `(see EVE-NG UI)` placeholders | Longest by ~28% — potential verbosity risk |
| Verbosity | Tight | Moderate-high but purposeful | Highest — some readers will find it too dense |

**ASCII diagram quality (the user's stated gap):**
- **Haiku:** `┌────┐──L1──┌────┐` with area labels as plain text between boxes.
  Functional but areas not visually delineated.
- **Sonnet:** Full box-drawing boxes for each router with interface labels as
  tree branches. No area bounding boxes in the ASCII.
- **Opus:** Each area rendered as its own bounded rectangle containing the
  router inside it. This is the closest ASCII analogue to the drawio diagram
  and best matches CLAUDE.md's "bordered boxes" guidance.

**Winner (theory + visual):** **Opus** for depth, **Sonnet** for density-per-line
ratio.
**Weakest:** **Haiku** — thin Ticket 3, weakest ASCII area visualization,
baseline-only theory.

---

## 4. setup_lab.py — Quality Comparison

This file is heavily templated. All three builds pass `py_compile` and use the
shared `eve_ng` helpers correctly.

| Dimension | Haiku (105) | Sonnet (105) | Opus (99) |
|---|---|---|---|
| Uses `from eve_ng import ...` | ✓ | ✓ | ✓ |
| `discover_ports` at runtime | ✓ (no hardcoded ports) | ✓ | ✓ |
| `require_host` guard | ✓ | ✓ | ✓ |
| `DEFAULT_LAB_PATH` | `ospf/lab-01-multiarea-ospfv2-haiku.unl` | `ospf/lab-01-multiarea-ospfv2-sonnet.unl` | `ospf/lab-01-multiarea-ospfv2-opus.unl` |
| `DEVICES` list | R1–R5 ✓ | R1–R5 ✓ | R1–R5 ✓ |
| Comment-stripping in push | ✓ | ✓ | ✓ |
| Exit code hygiene | 0 / 1 / 3 | 0 / 1 / 3 | 0 / 1 / 3 |
| Template adherence | High | High | High (most compact) |
| py_compile result | Pass | Pass | Pass |

**Winner:** Tie. No meaningful differentiation on this file — the template
leaves almost no room for creativity. Opus is 6 lines shorter; Sonnet and Haiku
are identical in structure.

---

## 5. Telemetry Comparison

Each model self-reported via a `<model>-telemetry.md` file.

| Dimension | Haiku | Sonnet | Opus |
|---|---|---|---|
| Phases documented | 9 + 3 corrections (3.R1–R3) | 11 | 12 + 3 corrections (3.R1–R3) |
| Post-build corrections reported | 2 (Ticket 2 fix + path fix) | 0 | 1 (Ticket 2 narrative) |
| Session compaction | Occurred | Not reported | Occurred mid-build |
| Parallel subagent dispatch | Sequential | Parallel (single message) | Parallel (single message) |
| meta.yaml subagent bleed | Yes | Yes | Not observed |
| Git commits for fixes | 2 | 0 (expected) | 1 (expected) |
| Self-detection of drawio folder bug | **No** | N/A | N/A |
| Advisor tool used | No | No | **Yes** (caught correctness bug) |
| Cross-model comparison table | Framework only (forward-looking) | Haiku-vs-Sonnet | Full 3-way including unique dimensions |
| Honesty about gaps | Good — flagged subagent opacity, context pressure | Good — flagged no live EVE-NG test | Best — flagged compaction + advisor dependency + not re-verifying meta.yaml post-rewrite |

**Winner:** **Opus** for telemetry completeness (3-way comparison table,
advisor-driven catch documented).
**Weakest:** **Haiku** — missed its own structural defect (misplaced drawio).

---

## 6. Summary Matrix — Strengths & Weaknesses

| Model | Strengths | Weaknesses |
|---|---|---|
| **Haiku 4.5** | Fast; single-session completion; accurate multiarea architecture; valid IOS syntax; self-corrected Ticket 2 when prompted; lowest cost per build | **Misplaced `topology.drawio`** (structural defect); drawio uses only 2 colors for 4 areas; thinnest Ticket 3; baseline-only Section 1 theory; Ticket 2 fix originally wrong; did not self-detect drawio folder bug; required 2 git fix commits |
| **Sonnet 4.6** | Zero post-build corrections; parallel subagent dispatch; best drawio (4 distinct colors + most complete legend); dense LSA/adjacency mismatch tables; ABR best-practice call-outs; one-shot completion (no compaction); strongest time-vs-quality trade-off | ASCII topology lacks bounded area zones; console port placeholders left as `(see EVE-NG UI)`; meta.yaml subagent bleed needed manual override; no decisions.md |
| **Opus 4.7** | Deepest workbook (908 lines with ToC); bounded-area ASCII (best of three); unique timer-mismatch fault class; only model to produce `decisions.md` documenting build-time trade-offs; advisor-driven correctness catch on Ticket 2; richest telemetry | Longest workbook risks verbosity; context compaction mid-build; Ticket 2 narrative had correctness bug that only advisor caught; marginally shorter drawio line count suggests fewer decorative elements than Sonnet; highest token cost |

---

## 7. Recommendations

### Which model is best overall?
**Opus 4.7** produces the highest-ceiling deliverable: deepest theory,
bounded-area ASCII that matches CLAUDE.md guidance, unique fault classes,
and the discipline to run an advisor review that catches its own correctness
bugs. If the goal is *canonical reference-quality material*, Opus wins.

### Which model strikes the best balance of quality, time, and cost?
**Sonnet 4.6.** It produced zero post-build corrections, ran subagents in
parallel, shipped the best drawio diagram, and did not trigger session
compaction. Its workbook is 80% of Opus's depth at roughly half the token
spend and without the advisor round-trip. For bulk lab production across the
remaining 60+ labs in the series, Sonnet is the default choice.

### When to use Haiku?
For **drafts, scaffolding, or low-stakes labs** where a human reviewer will
clean up behind it. Haiku's speed and cost make it appropriate for volume
work, but its structural defect (misplaced drawio) and thin Ticket 3 mean
every Haiku build needs a structural-compliance pass before ship.

### Suggested workflow
1. **Haiku** builds first-pass draft → human review.
2. **Sonnet** is the default production builder for all remaining labs.
3. **Opus** reserved for the 2–3 flagship capstone labs where reference-quality
   depth matters, and for advisor-reviewing other models' output.

### Model-agnostic gaps to close
- All three leave `__pycache__/` artifacts — add a post-build cleanup step.
- meta.yaml subagent bleed hit both Haiku and Sonnet — fix the
  `fault-injector` subagent to not write its own provenance.
- No live EVE-NG validation by any model — add a CI step that imports one
  build per model into EVE-NG and verifies adjacency.
- Haiku's structural defect (misplaced drawio) suggests the `lab-assembler`
  skill should add a post-build path verification checklist.

---

## 8. Scoreboard

Weighted 0–5 per dimension; total out of 35.

| Dimension | Weight | Haiku | Sonnet | Opus |
|---|:---:|:---:|:---:|:---:|
| Structural compliance | 1× | 3 | 5 | 5 |
| topology.drawio quality | 1× | 3 | 5 | 4 |
| workbook.md depth | 1× | 3 | 4 | 5 |
| workbook.md ASCII diagram | 1× | 2 | 3 | 5 |
| setup_lab.py | 1× | 5 | 5 | 5 |
| Correctness on first pass | 1× | 2 | 5 | 3 |
| Telemetry quality | 1× | 3 | 4 | 5 |
| **Total / 35** | | **21** | **31** | **32** |
| **Cost-adjusted winner** | | | **✓ best balance** | highest quality |

---

**Report authored:** 2026-04-24
**Source files read:** 9 (3 × topology.drawio + 3 × workbook.md + 3 × setup_lab.py) + 3 telemetry files
**Method:** Parallel sub-agent file analysis + main-agent synthesis

---

## Addendum — Sonnet 4.6 High-Effort vs Medium-Effort Comparison

A second Sonnet build was produced under `/effort medium` at
`labs/ospf/lab-01-multiarea-ospfv2-sonnet-medium/`. This addendum compares
the two Sonnet builds at identical model, identical spec, different effort
setting.

### Structural compliance

Both builds pass identically. Same directory layout (`topology/topology.drawio`,
`scripts/fault-injection/*`, 5 × initial + 5 × solution configs). Neither
produces a `decisions.md`. Both leave `__pycache__/` artifacts (the skill-level
bug documented elsewhere in this report — not a model defect).

### Head-to-head: Sonnet High vs Sonnet Medium

| Dimension | Sonnet 4.6 (High) | Sonnet 4.6 (Medium) | Delta |
|---|---|---|---|
| workbook.md line count | 716 | 504 | **−30%** |
| Section count | 11 ✓ | 11 ✓ | equal |
| Section 1 theory lines | ~130 | ~55 | **−58%** |
| LSA type table (5 rows) | ✓ | ✓ | equal |
| Adjacency mismatch/failure table (5 rows) | ✓ | **absent** | **cut** |
| ABR best-practice callout | ✓ | ✓ | equal |
| Exam tips (Sections 1, 7) | ✓ per subsection | **absent** | **cut** |
| Cheatsheet syntax skeletons (`router ospf <pid>` etc.) | ✓ | **absent** | **cut** |
| Verification output `!` annotations | 6–8 per block | 2–3 per block | **−66%** |
| Troubleshooting tickets | 3, all complete | 3, all complete | equal |
| Solution blocks | All 5 tasks | **Tasks 3/4 verification-only (correct)** | medium is more precise |
| IOS configs (initial + solutions) | byte-identical | byte-identical | equal |
| setup_lab.py | 105 lines | 93 lines | −12 lines (cosmetic whitespace) |
| topology.drawio | 169 lines, 4 distinct area colors, full legend | 160 lines, 4 distinct area colors, full legend | −9 lines (XML whitespace) |
| drawio structural completeness | all elements | all elements | equal |
| Fault injection scripts | all 3 distinct classes + apply_solution | all 3 distinct classes + apply_solution | equal |
| Python py_compile pass | ✓ | ✓ | equal |
| Post-build corrections | 0 | 1 (meta.yaml subagent bleed — same as High) | effort-independent |
| Parallel subagent dispatch | ✓ | ✓ | equal |
| Total LOC in package | ~1,900 | ~1,500 | **−21%** |

### What Medium preserves vs cuts

**Preserved (load-bearing):** All 11 sections, all 5 core tasks, all 3
troubleshooting tickets with full diagnosis chains, byte-identical IOS configs,
all drawio structural elements (shapes, zones, legend, IP labels), all Python
scripts with equivalent logic.

**Cut (pedagogical enrichment):**
1. **Adjacency failure cause table** — 5-row symptom→root-cause table
   (area mismatch / MTU / timers / auth / subnet mask) removed entirely.
   This is the single most exam-relevant table and its loss is the biggest gap.
2. **Exam tips** — gone from Section 1 subsections and the Section 7 cheatsheet.
3. **Syntax skeletons** in the cheatsheet — `router ospf <pid>` / `network`
   templates students copy from.
4. **Inline verification annotations** — `show ip ospf neighbor` blocks
   drop from ~7 explanatory `!` comments down to ~2.

### Interpretation

Medium-effort mode is a **pure prose-density reduction**. It does not trade
correctness, structural completeness, or fault-scenario design. Everything
that makes the lab *work* is preserved; what gets cut is everything that
makes the lab *teach*.

### Is the Medium build shippable?

- **As an instructor reference or lab skeleton:** Yes — it is technically
  complete and a human instructor could supplement the missing exam content.
- **As a primary student resource for 300-510 prep:** No — the missing
  adjacency failure table and absent exam tips are the two pieces students
  lean on most for the exam. Those would need to be manually backfilled.

### Cost/quality curve for Sonnet

| Config | Est. cost vs High | Quality ceiling | Recommended use |
|---|---|---|---|
| Sonnet 4.6 High | 1.0× | 31/35 (from main report) | Default for student-facing labs |
| Sonnet 4.6 Medium | ~0.7× | ~26/35 (estimate: −3 theory, −2 cheatsheet) | Drafts, skeletons, instructor-facing reference, non-exam labs |

### Updated model-selection guidance

The three-way (Haiku / Sonnet-Medium / Sonnet-High / Opus) picture:

| Use case | Best pick |
|---|---|
| Production student lab (default) | **Sonnet High** |
| Fast draft before human review | **Sonnet Medium** or **Haiku** |
| Flagship capstone / reference-quality depth | **Opus** |
| Bulk scaffolding where content will be rewritten | **Haiku** |

Sonnet Medium slots between Haiku and Sonnet High: **better structural
correctness than Haiku (no misplaced drawio, all tickets uniform depth),
less instructional content than Sonnet High**. It's a useful tier for first-draft
work before a human pass, but not a direct substitute for Sonnet High on
labs that ship to students.

---

**Addendum authored:** 2026-04-24
**Source files added:** 4 (sonnet-medium's workbook.md, setup_lab.py, topology.drawio, sonnet-medium-telemetry.md)
