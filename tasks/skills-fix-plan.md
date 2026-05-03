# Skills Contradiction Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate two confirmed contradictions in `lab-assembler/SKILL.md` Step 5 that cause non-deterministic topology diagram output, tighten Section 5 task-heading enforcement, and identify labs built before the workbook contract gate existed.

**Architecture:** Three targeted edits to `.agent/skills/lab-assembler/SKILL.md`, one bash audit sweep, then a submodule commit. No new files created; no skill structure changed.

**Tech Stack:** Markdown skill files, bash, git submodule.

---

### Task 1: Fix drawio dispatch Pre-Write checklist

Two items in the Step 5 dispatch prompt directly contradict `drawio/SKILL.md`. The subagent reads drawio/SKILL.md first, then receives a checklist that overrides it with wrong instructions. This produces non-compliant diagrams (old `cisco.routers.router` shapes, separate label cells).

**Files:**
- Modify: `.agent/skills/lab-assembler/SKILL.md` lines 703–717 (Pre-Write Checklist inside Step 5 subagent prompt)

- [ ] **Step 1: Confirm the contradictions are present**

```bash
grep -n "cisco.routers.router\|separate text cells\|NOT embedded" .agent/skills/lab-assembler/SKILL.md
```

Expected output includes lines referencing `mxgraph.cisco.routers.router` and `separate text cells`.

- [ ] **Step 2: Replace the Pre-Write Checklist**

Locate the `## Pre-Write Checklist` block (around line 703) and replace it with:

```markdown
## Pre-Write Checklist
- [ ] drawio/SKILL.md §4.2–§4.7 read; §4.7 XML snippets in context
- [ ] Router shape: mxgraph.cisco19.rect;prIcon=router (NOT mxgraph.cisco.routers.router — deprecated library)
- [ ] Device labels: embedded in device cell value= as HTML (NOT separate text cells)
- [ ] Connection lines: strokeColor=#FFFFFF, strokeWidth=2 — NOT default black
- [ ] IP last-octet labels: standalone mxCell with edgeLabel style, parent="1"
- [ ] Legend box: fillColor=#000000, fontColor=#FFFFFF, bottom-right
- [ ] Canvas background: #1a1a2e set in <mxGraphModel background="#1a1a2e">
- [ ] Zone shapes (OSPF areas, BGP AS): rounded=1;arcSize=5 — NOT ellipse
```

- [ ] **Step 3: Verify old contradictions are gone**

```bash
grep -n "cisco.routers.router\|separate text cells\|NOT embedded" .agent/skills/lab-assembler/SKILL.md
```

Expected: no output. If any lines still match, re-edit.

---

### Task 2: Fix drawio dispatch Post-Write checklist

The Post-Write Checklist (inside the same subagent dispatch block) repeats the same two wrong instructions, now as validation criteria. An agent compliant with the correct drawio skill would fail its own post-write check.

**Files:**
- Modify: `.agent/skills/lab-assembler/SKILL.md` lines 711–717 (Post-Write Checklist inside Step 5 subagent prompt)

- [ ] **Step 1: Confirm post-write checklist contains contradictions**

```bash
grep -n "separate label cell\|mxgraph.cisco.routers.router" .agent/skills/lab-assembler/SKILL.md
```

Expected: lines inside the Post-Write Checklist block.

- [ ] **Step 2: Replace the Post-Write Checklist**

Locate the `## Post-Write Checklist (fix before confirming done)` block and replace it with:

```markdown
## Post-Write Checklist (fix before confirming done)
- [ ] File written to `labs/<topic>/lab-NN-<slug>/topology/topology.drawio` — NOT to the lab root
- [ ] Every router cell uses mxgraph.cisco19.rect;prIcon=router (or prIcon=l3_switch / workgroup_switch / cloud / workstation)
- [ ] Every device label is embedded in the cell value= as HTML — no separate label mxCells exist
- [ ] Every edge has strokeColor=#FFFFFF, strokeWidth=2
- [ ] Every interface endpoint has a standalone .N octet cell (edgeLabel style, parent="1")
- [ ] Legend present at bottom-right with fillColor=#000000, fontColor=#FFFFFF
```

- [ ] **Step 3: Verify corrections**

```bash
grep -n "cisco19\|embedded in the cell value" .agent/skills/lab-assembler/SKILL.md | grep -A2 "Post-Write"
```

Expected: lines matching `cisco19` and `embedded in the cell value` in the Post-Write block.

- [ ] **Step 4: Commit Step 5 drawio dispatch fixes**

```bash
git -C .agent/skills add lab-assembler/SKILL.md
git -C .agent/skills commit -m "fix(lab-assembler): reconcile Step 5 drawio dispatch with canonical drawio skill

Pre/Post-Write checklists contradicted drawio/SKILL.md on two points:
- Shape library: cisco.routers.router -> cisco19.rect;prIcon=router
- Label style: separate text cells -> embedded HTML in cell value

An agent reading drawio/SKILL.md first and the checklist second got
conflicting instructions, producing non-compliant diagrams non-deterministically."
```

---

### Task 3: Tighten Section 5 task-heading gate enforcement

The current gate item specifies `### Task N: <Title>` format but doesn't explicitly FAIL headings like `### Scenario A` or `### Objective 1`. A loose reader can pass non-compliant Section 5 headings through the gate.

**Files:**
- Modify: `.agent/skills/lab-assembler/SKILL.md` line 556 (Section 5 gate checklist item)

- [ ] **Step 1: Confirm current gate item text**

```bash
grep -n "Task N" .agent/skills/lab-assembler/SKILL.md | grep -i "checklist\|block\|heading"
```

Expected: one line near line 556 reading `Each \`### Task N: <Title>\` block has bullet steps...`.

- [ ] **Step 2: Replace with explicit fail-pattern item**

Find the single line:
```
- [ ] Each `### Task N: <Title>` block has bullet steps plus a closing `**Verification:**` line with `show` command(s)
```

Replace with:
```markdown
- [ ] Every Section 5 H3 heading matches `### Task N:` (N = digit). Headings like `### Scenario A`, `### Objective N`, `### Step N` are a FAIL. Exception: capstone-ii troubleshooting tickets use `### Ticket N —` for their ticket list, but capstone-i implementation tasks still use `### Task N:`.
- [ ] Each `### Task N:` block has bullet steps plus a closing `**Verification:**` line with `show` command(s)
```

- [ ] **Step 3: Verify the new items appear**

```bash
grep -n "Scenario A\|Objective N\|FAIL\|Ticket N" .agent/skills/lab-assembler/SKILL.md
```

Expected: lines in the Step 3b checklist for "Scenario A" and "FAIL".

- [ ] **Step 4: Commit gate tightening**

```bash
git -C .agent/skills add lab-assembler/SKILL.md
git -C .agent/skills commit -m "fix(lab-assembler): make Section 5 task-heading gate explicit

Gate item now explicitly names failing patterns (Scenario A, Objective N)
so a loose reader cannot pass a non-compliant heading. Preserves the
capstone-ii exception for Ticket N headings."
```

---

### Task 4: Pre-gate audit — identify labs built before the contract gate

The workbook contract gate (Step 3b) was added on 2026-05-01 (commit f840ce0). Any lab with `created.date` before that date may have a non-compliant workbook. This task produces an explicit list so you can decide which ones to rebuild.

**Files:**
- Read: all `labs/*/lab-*/meta.yaml`
- Write: `tasks/pre-gate-labs.txt` (audit output)

- [ ] **Step 1: Run the audit sweep**

```bash
for f in /c/Users/Nkwenti/Documents/Labs/Cisco/ccnp-spri-labs/labs/*/lab-*/meta.yaml; do
  d=$(grep -E '^\s+date:' "$f" | head -1 | sed 's/.*date: *"//; s/".*//')
  [[ "$d" < "2026-05-01" ]] && echo "$d  $f"
done | sort > /c/Users/Nkwenti/Documents/Labs/Cisco/ccnp-spri-labs/tasks/pre-gate-labs.txt
cat /c/Users/Nkwenti/Documents/Labs/Cisco/ccnp-spri-labs/tasks/pre-gate-labs.txt
```

Expected: a list of `YYYY-MM-DD  labs/<topic>/lab-NN-<slug>/meta.yaml` lines. The BGP capstone (`lab-07-capstone-config`, 2026-04-28) will appear.

- [ ] **Step 2: Scan each pre-gate workbook for the most critical failure pattern**

```bash
while IFS= read -r line; do
  metafile="${line#*  }"
  workbook="${metafile/meta.yaml/workbook.md}"
  [[ -f "$workbook" ]] || { echo "MISSING workbook: $workbook"; continue; }
  # Check: does Section 1 heading match the contract?
  if ! grep -q "^## 1. Concepts & Skills Covered" "$workbook"; then
    echo "FAIL (wrong Section 1): $workbook"
  else
    echo "OK: $workbook"
  fi
done < /c/Users/Nkwenti/Documents/Labs/Cisco/ccnp-spri-labs/tasks/pre-gate-labs.txt
```

Expected: `FAIL` lines for labs that predate the current contract. `OK` lines for any that happen to be compliant already.

- [ ] **Step 3: Review audit output and decide on rebuilds**

Read `tasks/pre-gate-labs.txt`. For each FAIL:
- If it's a topic that's still actively being used (student-facing), queue it for rebuild using `/build-lab <topic>/<lab-id>`.
- If it's a deprecated or replaced lab (e.g., `lab-07-capstone-config` has a Pi replacement in `lab-07-capstone-config-pi`), note it for archival/removal instead.

This is a human decision step — do not auto-rebuild without user confirmation.

---

### Task 5: Update submodule reference in parent repo

After committing fixes to `.agent/skills`, the parent repo needs its submodule pointer updated and pushed, or the fixes won't be visible to other sessions.

**Files:**
- Modify: `.agent/skills` (git submodule reference in parent repo)

- [ ] **Step 1: Confirm the submodule has new commits**

```bash
git -C .agent/skills log --oneline -3
```

Expected: your two commits from Tasks 2 and 3 at the top.

- [ ] **Step 2: Stage the submodule update in the parent repo**

```bash
git add .agent/skills
git status
```

Expected: `modified: .agent/skills` shown as a staged change.

- [ ] **Step 3: Commit the submodule bump**

```bash
git commit -m "chore: bump skills submodule — fix drawio dispatch contradictions, tighten Section 5 gate

Picks up two commits from lab-assembler/SKILL.md:
- Reconcile Step 5 drawio dispatch with canonical drawio/SKILL.md
- Explicit fail-patterns for Section 5 H3 headings

Ref: pre-gate audit output in tasks/pre-gate-labs.txt"
```

- [ ] **Step 4: Verify**

```bash
git log --oneline -3
git submodule status .agent/skills
```

Expected: your commit at HEAD, submodule showing the new SHA without a leading `+` (clean).

---

## Self-Review

**Spec coverage:**
- [x] Fix drawio shape library contradiction — Task 1 + 2
- [x] Fix drawio label style contradiction — Task 1 + 2
- [x] Tighten Section 5 task-heading enforcement — Task 3
- [x] Pre-gate audit — Task 4
- [x] Commit submodule — Task 5
- [x] Recommendations #8 (programmatic validator) — deliberately deferred; out of scope for this plan

**Placeholder scan:** No TBD/TODO/similar. All edit strings are exact.

**Type consistency:** No types involved; skill text edits only. Terminology (`### Task N:`, `### Ticket N —`, `cisco19.rect;prIcon=router`) is consistent across all tasks.
