# Pi vs Claude: Capstone Lab Build Comparison

**Comparison Date:** 2026-05-01  
**Exam:** CCNP SPRI 300-510  
**Labs Compared:**
- `mpls/lab-04-capstone-config` (Claude) vs `mpls/lab-04-capstone-config-pi` (Pi)
- `bgp/lab-07-capstone-config` (Claude) vs `bgp/lab-07-capstone-config-pi` (Pi)

---

## Executive Summary

Both agents produced complete, structurally valid lab packages following the lab-assembler contract. Claude's workbooks are consistently larger (18–22% for MPLS, but Pi's BGP workbook is 17% larger — an inversion driven by Claude's radically different "Scenario" format). Claude's topology diagrams include richer visual elements. Solution configs are functionally identical across both agents. Pi produces workbooks that adhere more strictly to the "Task N" contract format, while Claude's BGP workbook innovates beyond the contract with a scenario-based format.

---

## 1. Overall Package Comparison

### 1.1 File Structure

| Criterion | Claude (MPLS) | Pi (MPLS) | Claude (BGP) | Pi (BGP) |
|-----------|--------------|-----------|-------------|----------|
| File count | 24 | 24 | 26 | 26 |
| All required directories | ✓ | ✓ | ✓ | ✓ |
| `meta.yaml` complete | ✓ | ✓ | ✓ | ✓ |
| `decisions.md` present | ✓ | ✓ | ✓ | ✓ |
| All scripts syntax-valid | ✓ | ✓ | ✓ | ✓ |

**Verdict:** Tie — both agents produce identical file structures.

---

### 1.2 Solution Configs

| Metric | Claude (MPLS) | Pi (MPLS) | Claude (BGP) | Pi (BGP) |
|--------|--------------|-----------|-------------|----------|
| PE1/R1 lines | 78 | 82 | 64 | 64 |
| P1/R2 lines | 55 | 55 | 74 | 75 |
| P2/R3 lines | 55 | 55 | 61 | 58 |
| PE2/R4 lines | 64 | 64 | 57 | 57 |
| CE1/R5 lines | 28 | 28 | 76 | 75 |
| CE2/R6 lines | 28 | 28 | 42 | 41 |
| R7 lines | — | — | 49 | 44 |

**Verdict:** Tie — solutions are functionally identical. Minor line-count differences come from whitespace and comment formatting, not configuration divergence.

---

## 2. Workbook Deep Dive

### 2.1 Size & Depth

| Metric | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|--------|------------|---------|-----------|--------|
| Lines | 1,189 | 1,051 | 1,168 | 974 |
| Bytes | 55,561 | 45,405 | 37,394 | 43,812 |
| Concepts subsections (Section 1) | 5 | 5 | 0 (single overview) | 7 |
| Tasks/Scenarios (Section 5) | 7 Tasks | 7 Tasks | 9 Scenarios | 8 Tasks |
| Troubleshooting tickets | 3 | 3 | 3 | 3 |

**Analysis:** Pi's MPLS workbook is 12% shorter than Claude's. However, Pi's BGP workbook is 17% **larger** than Claude's BGP workbook. This inversion is driven by Claude's BGP workbook using a radically different format — it replaces the traditional "Task N" structure with 9 "Scenario A–I" blocks, each containing Situation/Constraints/Acceptance criteria. While more engineering-fluent, this format is more compact (fewer bullet explanations per scenario). Pi's BGP workbook uses the traditional Task 1–8 format with detailed bullet steps, verification commands, and richer Section 1 theory subsections, resulting in a larger file despite having one fewer "task."

### 2.2 Section 1: Concepts & Skills Covered

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| Number of theory subsections | 5 | 5 | 0 | 7 |
| Layer dependency diagram (ASCII) | ✓ (5-layer stack) | ✗ | ✗ | ✗ |
| Skills table | ✓ | ✓ | ✗ | ✓ |
| Exam objective citation | ✓ | ✓ | ✗ | ✓ |
| Insight callout box | ✗ | ✓ | ✗ | ✓ |
| IOS syntax inline blocks | ✓ | ✓ | ✗ | ✓ (per subsection) |

**Winner: Pi (by narrow margin).** Pi's BGP Section 1 is substantially richer — 7 named theory subsections (OSPF Underlay, iBGP RR, eBGP Multihoming, Inter-Domain Security, Dampening/Dynamic, Communities, FlowSpec) with IOS syntax blocks, reference tables, and an "Insight" callout. Claude's BGP Section 1 is a single "Lab Overview" paragraph without named subsections. For MPLS, both are comparable, but Claude's layer-dependency ASCII diagram is an excellent pedagogical addition Pi missed.

### 2.3 Section 2: Topology & Scenario

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| ASCII topology diagram | ✓ (landscape) | ✓ (portrait) | ✓ (elaborate landscape) | ✓ (compact) |
| Link table with interface/IP columns | ✓ (Device A/B, IPs) | ✓ (Endpoints, Subnet) | ✗ (inline in ASCII) | ✓ (cabling table in S3) |
| Narrative scenario framing | ✓ (1 paragraph) | ✓ (1 paragraph) | ✓ (inline) | ✓ (1 paragraph) |
| Role descriptions per device | ✓ (in ASCII label) | ✓ (in ASCII label) | ✓ (separate section) | ✓ (Key relationships) |

**Winner: Claude (BGP), Pi (MPLS).** Claude's BGP ASCII topology is exceptionally detailed — landscape layout with proper box-drawing characters, interface/IP labels on every link, per-device role descriptions, and color-coded AS boundaries. Pi's BGP topology is functional but less visually refined. For MPLS, Pi's diamond layout is cleaner and more readable.

### 2.4 Section 3: Hardware & Environment

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| Device Inventory table | ✓ | ✓ | ✗ | ✓ |
| Loopback Address table | ✓ | ✓ | ✗ | ✓ |
| Cabling table with interface/IPs | ✓ | ✓ | ✗ (Addressing Table) | ✓ |
| Console Access Table | ✓ | ✓ | ✗ | ✓ |
| Advertised Prefixes table | ✓ | ✓ | ✗ | ✓ |

**Winner: Pi.** Pi's Section 3 is contract-compliant across both labs with all 4–5 required tables. Claude's BGP workbook omits the Device Inventory and Console Access tables entirely, replacing Section 3 with an "Addressing Table" and moving prerequisites to Section 4. Claude's BGP addressing table is comprehensive (Device | Interface | Address | Role) but breaks the lab-assembler contract's table ordering requirements.

### 2.5 Section 5: Lab Challenge (Tasks vs Scenarios)

**This is the most significant design divergence.**

| Approach | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|----------|------------|---------|-----------|--------|
| Format | Task 1–7 | Task 1–7 | Scenario A–I | Task 1–8 |
| Task structure | Design Requirements intro + per-task objectives | Per-task bullet steps + Verification | Situation → Constraints → Acceptance | Per-task bullet steps + Verification |
| Explicit IOS commands avoided | ✓ | ✓ | ✓ | ✓ |
| "Capstone" heading | ✓ | ✓ | ✓ | ✓ |

**Winner: Claude (BGP), Tie (MPLS).** Claude's BGP "Scenario" format is a genuine innovation. Each scenario reads like an engineering work order: **Situation** (what is the business need), **Constraints** (what limits apply), **Acceptance criteria** (numbered checklist items). This maps more closely to real-world SP engineering than the traditional Task format. Example:

```
### Scenario A — Customer-A dual-homed with deterministic primary/backup
**Situation.** Customer A (R1, AS 65001) is dual-homed...
**Constraints.** AS 65100 must prefer R2 inbound (LOCAL_PREF 200)...
**Acceptance criteria.**
1. On R5, show ip bgp 172.16.1.0/24 lists best path with LOCAL_PREF 200...
```

This format encourages the student to think in terms of design requirements rather than configuration checklists. Pi's Task 1–8 format is contract-compliant but conventional. For MPLS, both agents use the same Task format and are functionally equivalent.

### 2.6 Section 7: Cheatsheet

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| Syntax skeleton code blocks | ✓ (5 groups) | ✓ (5 groups) | ✗ | ✓ (6 groups) |
| Command/Purpose tables | ✓ | ✓ | ✗ | ✓ |
| Verification Commands table | ✓ | ✓ | ✓ (verification matrix) | ✓ |
| Wildcard Mask Quick Reference | ✓ | ✓ | ✗ | ✓ |
| Common Failure Causes table | ✓ | ✓ | ✗ | ✓ |

**Winner: Pi.** Claude's BGP workbook omits the cheatsheet entirely — Section 7 is "Verification" with per-scenario show command outputs but no syntax skeleton blocks, command/purpose tables, or failure causes table. This is a significant pedagogical gap for a capstone lab. Pi's cheatsheets are consistently complete across both labs with all required subsections.

**Note:** Claude's BGP "7.0 Verification Matrix" (summary checklist table) is an excellent innovation — a single table mapping check # to device, command, and expected output. Pi doesn't include this summary matrix.

### 2.7 Section 8: Solutions

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| Spoiler warning | ✓ | ✓ | ✓ | ✓ |
| `<details>` blocks per task | ✓ (7 tasks) | ✓ (7 tasks) | ✓ (per scenario) | ✓ (3 tasks, then file ref) |
| Complete configs inline | ✓ | ✓ (partial for BGP) | ✓ | ✓ (Tasks 1–3 only) |
| Verification commands in spoilers | ✓ | ✓ | ✗ | ✓ |

**Winner: Claude (BGP), Tie (MPLS).** For MPLS, both include complete configs per task. For BGP, Claude includes full per-scenario solution configs in `<details>` blocks. Pi includes Task 1–3 configs inline and then refers to `solutions/` files for Tasks 4–7. While the solutions files are functionally identical, Claude's inline approach is more student-friendly — the student doesn't need to open separate files.

### 2.8 Section 9: Troubleshooting

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| Ticket count | 3 | 3 | 3 | 3 |
| Symptom-only headings | ✓ | ✓ | ✓ | ✓ |
| Inject command inline | ✓ | ✓ | ✓ | ✓ |
| Diagnosis steps | ✓ | ✓ | ✓ | ✓ |
| Fix in spoiler | ✓ | ✓ | ✓ | ✓ |
| Workflow code block | ✓ | ✓ | ✓ | ✓ |

**Verdict: Tie.** Both agents produce contract-compliant troubleshooting sections. Ticket quality is comparable — Claude's tickets tend to have slightly richer scenario context (e.g., "Tunnel10 Stays Down After a Routine Maintenance Window" with multi-paragraph narrative), while Pi's tickets are more focused on diagnostic command walkthroughs.

---

## 3. Topology Diagrams Deep Dive

### 3.1 Visual Feature Comparison

| Feature | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------|------------|---------|-----------|--------|
| cisco19 router shapes | ✓ | ✓ | ✓ | ✓ |
| Embedded HTML device labels | ✓ | ✓ | ✓ | ✓ |
| Dark canvas (#1a1a2e) | ✓ | ✓ | ✓ | ✓ |
| White connection lines (#FFFFFF) | ✓ | ✓ | ✓ | ✓ |
| **Last-octet IP labels** | ✓ (on EVERY link) | ✗ | ✓ (on EVERY link) | ✗ |
| **Security badges on links** | ✗ | ✗ | ✓ (🔒GTSM, 🔑MD5) | ✗ |
| AS/domain zone overlays | ✓ (4 zones) | ✓ (3 zones) | ✓ (4 zones) | ✓ (4 zones) |
| Tunnel overlay (dashed) | ✓ (orange, curved) | ✓ (orange, arc) | N/A | N/A |
| Dynamic-neighbor link (dashed green) | N/A | N/A | ✓ | ✗ |
| Legend box (black fill, white text) | ✓ | ✓ | ✓ | ✓ |
| Title banner | ✓ | ✓ | ✓ | ✓ |
| Diagram file size (bytes) | 15,434 | 13,102 | 19,173 | 14,473 |

### 3.2 Critical Missing Feature: Last-Octet Labels

Both Claude diagrams include per-interface endpoint last-octet labels as separate `edgeLabel` cells:

```xml
<!-- Claude's MPLS drawio -->
<mxCell id="oct_L1_CE1" value=".11" style="edgeLabel;...fontColor=#FFFFFF;"
        vertex="1" connectable="0">
    <mxGeometry x="93" y="418" as="geometry"/>
</mxCell>
<mxCell id="oct_L1_PE1" value=".1" style="edgeLabel;...fontColor=#FFFFFF;"
        vertex="1" connectable="0">
    <mxGeometry x="243" y="418" as="geometry"/>
</mxCell>
```

Every link endpoint has a `.N` octet label positioned near the router icon. This is a **contract requirement** from the lab-assembler checklist: "Every interface endpoint has a standalone .N octet cell." Pi's diagrams embed subnet information in edge labels but omit the per-interface octet labels. **This is the single biggest topology gap.**

### 3.3 Claude's BGP Diagram — Security Badges

Claude's BGP topology includes visual security badges on eBGP links:

```
🔒 GTSM  — on L1 (R1↔R2) and L2 (R1↔R3)
🔑 MD5   — on L7 (R5↔R6) and L8a (R5↔R7)
```

These are rendered as small rounded text boxes with gold/orange borders, providing immediate visual indication of which links carry which security mechanisms. Pi's diagram omits these entirely — a missed opportunity for visual pedagogy.

### 3.4 Claude's Dynamic-Neighbor Link

Claude's BGP diagram renders the dynamic-neighbor link (10.99.0.0/30) as a **dashed green line** (`strokeColor=#AAFFAA`) with green octet labels, visually distinguishing it from the solid white physical links. Pi's diagram doesn't show this link at all — a topology completeness gap.

---

## 4. Unique Innovations Per Agent

### 4.1 Claude's Unique Contributions

| Innovation | Lab | Description |
|-----------|-----|-------------|
| **Scenario-based tasks** | BGP | Section 5 as "Scenario A–I" with Situation/Constraints/Acceptance — engineering work-order format |
| **Blueprint Coverage matrix** | BGP | Section 6 maps every scenario to a blueprint bullet |
| **Verification Summary Matrix** | BGP | Single table (check # → device → command → expected) — quick reference |
| **Layer dependency diagram** | MPLS | ASCII art 5-layer stack showing build order dependency |
| **Security badges on topology** | BGP | 🔒GTSM and 🔑MD5 visual indicators on link overlays |
| **Last-octet labels** | Both | Per-interface `.N` octet labels on every link endpoint in drawio |
| **Lab Teardown section** | BGP | Section 9 explains how to clean up after the lab |
| **Further Reading section** | BGP | Section 11 points to additional resources |
| **Dynamic-neighbor link in topology** | BGP | Green dashed line for the listen-range link |
| **Device-specific addressing table** | BGP | Full interface→address→role table |

### 4.2 Pi's Unique Contributions

| Innovation | Lab | Description |
|-----------|-----|-------------|
| **Insight callout boxes** | Both | `★ Insight` framed asides with architectural rationale |
| **Per-subsection IOS syntax blocks** | BGP | Every theory subsection has inline IOS config skeletons |
| **Richer Section 1 theory** | BGP | 7 named subsections vs Claude's single overview |
| **Full cheatsheet compliance** | BGP | Syntax skeletons, command/purpose tables, failure causes, wildcard mask reference |
| **Explicit "IS/NOT pre-loaded" format** | Both | Contract-compliant two-list format |
| **MPSL domain zone + AS zones** | MPLS | Both MPLS core and AS zones rendered as semi-transparent overlays |

---

## 5. Contract Compliance Scorecard

Each item scored: ✓ (pass), ⚠ (partial), ✗ (fail)

| Contract Requirement | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|---------------------|-------------|---------|-----------|--------|
| Title line + TOC (11 entries) | ✓ | ✓ | ⚠ (no TOC entries) | ✓ |
| Section 1: Exam objective + 3+ subsections + Skills table | ✓ | ✓ | ⚠ (no named subsections) | ✓ |
| Section 3: Device Inventory table | ✓ | ✓ | ✗ | ✓ |
| Section 3: Loopback Address table | ✓ | ✓ | ✗ | ✓ |
| Section 3: Cabling table | ✓ | ✓ | ✗ | ✓ |
| Section 3: Console Access Table | ✓ | ✓ | ✗ | ✓ |
| Section 3: Advertised Prefixes table | ✓ | ✓ | ✗ | ✓ |
| Section 4: IS/NOT pre-loaded lists (no IOS syntax) | ✓ | ✓ | ⚠ (different format) | ✓ |
| Section 5: Tasks with bullets + Verification (no IOS syntax) | ✓ | ✓ | ⚠ (Scenarios, not Tasks) | ✓ |
| Section 5: Capstone heading "Full Protocol Mastery" | ✓ | ✓ | ✓ | ✓ |
| Section 6: Inline `! ←` verification markers | ✓ | ✓ | ⚠ (separate 7.x subsections) | ✓ |
| Section 7: Cheatsheet with syntax skeletons + tables | ✓ | ✓ | ✗ (no syntax skeletons) | ✓ |
| Section 8: Solutions in `<details>` blocks | ✓ | ✓ | ✓ | ⚠ (partial — refs files) |
| Section 9: Ticket symptom-only headings + inject + spoilers | ✓ | ✓ | ✓ | ✓ |
| Section 10: Core + Troubleshooting checklist | ✓ | ✓ | ✓ | ✓ |
| Section 11: Exit codes table | ✓ | ✓ | ⚠ ("Further Reading") | ✓ |
| Drawio: Last-octet `.N` labels | ✓ | ✗ | ✓ | ✗ |
| Drawio: Legend box (black fill, bottom-right) | ✓ | ✓ | ✓ | ✓ |
| Drawio: White connection lines | ✓ | ✓ | ✓ | ✓ |

---

## 6. Scoring Summary

### 6.1 Weighted Scores

Each category scored 0–10. Weights reflect pedagogical importance for a certification capstone lab.

| Category | Weight | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|----------|--------|------------|---------|-----------|--------|
| **Workbook — Theory depth (S1)** | 15% | 8 | 8 | 4 | 9 |
| **Workbook — Task/scenario design (S5)** | 20% | 8 | 7 | 9 | 7 |
| **Workbook — Cheatsheet (S7)** | 10% | 8 | 8 | 3 | 9 |
| **Workbook — Solutions (S8)** | 10% | 8 | 8 | 9 | 7 |
| **Workbook — Troubleshooting (S9)** | 10% | 8 | 8 | 8 | 8 |
| **Workbook — Contract compliance** | 10% | 8 | 9 | 4 | 9 |
| **Topology — Visual quality** | 10% | 9 | 6 | 9 | 6 |
| **Topology — Completeness** | 5% | 9 | 6 | 9 | 6 |
| **Solutions — Config accuracy** | 5% | 9 | 9 | 9 | 9 |
| **Scripts — Fault injection quality** | 5% | 8 | 8 | 8 | 8 |
| **TOTAL (weighted)** | 100% | **8.2** | **7.8** | **7.1** | **7.9** |

### 6.2 Raw Average (unweighted)

| Metric | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|--------|------------|---------|-----------|--------|
| Simple average of all 10 categories | 8.3 | 7.7 | 7.2 | 7.8 |

### 6.3 Workbook-Specific Scores (Sections 1–11 only)

| Metric | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|--------|------------|---------|-----------|--------|
| Workbook average (7 categories) | 8.0 | 8.0 | 6.6 | 8.3 |

### 6.4 Topology-Specific Scores (drawio only)

| Metric | Claude MPLS | Pi MPLS | Claude BGP | Pi BGP |
|--------|------------|---------|-----------|--------|
| Visual quality | 9 | 6 | 9 | 6 |
| Completeness (octets, badges, overlay links) | 9 | 6 | 9 | 6 |

---

## 7. Key Findings

### 7.1 Where Claude Excels

1. **Topology diagrams are definitively better.** Last-octet labels on every link endpoint, security badges on relevant links, tunnel overlays with proper waypoint routing, and dynamic-neighbor links as visually distinct dashed lines. These are contract requirements Pi missed entirely.

2. **Scenario-based task format (BGP).** Claude's "Scenario A–I" with Situation/Constraints/Acceptance is a superior pedagogical approach for a capstone — it teaches design thinking rather than configuration execution. Pi's Task 1–8 format is contract-compliant but less innovative.

3. **Verification Summary Matrix.** Claude's single-table checklist (device → command → expected) is more student-friendly than Pi's per-task verification blocks.

4. **Topology ASCII art.** Claude's BGP landscape topology with box-drawing characters is more visually refined than Pi's compact version.

### 7.2 Where Pi Excels

1. **Contract compliance (BGP).** Pi's BGP workbook passes every contract checklist item with full marks. Claude's BGP workbook fails 6 of 10 Section 3 requirements (missing all tables), has no TOC entries, no Section 1 named subsections, and no Section 7 cheatsheet.

2. **Theory depth (BGP Section 1).** Pi's 7 named theory subsections with IOS syntax blocks, reference tables, and Insight callouts provide substantially more pedagogical value than Claude's single "Lab Overview" paragraph.

3. **Cheatsheet completeness.** Pi's cheatsheets are consistently complete with syntax skeletons, command/purpose tables, wildcard mask references, and failure causes tables. Claude's BGP workbook omits the cheatsheet entirely.

4. **Consistency across labs.** Pi's two labs are structurally identical — same format, same section structure, same level of detail. Claude's two labs diverge significantly: MPLS follows the Task format while BGP innovates with Scenarios, and BGP drops several standard sections.

### 7.3 Critical Gaps

| Gap | Agent | Impact |
|-----|-------|--------|
| Missing last-octet labels in drawio | Pi (both labs) | Students cannot identify interface IPs from the diagram alone — a key visual pedagogy loss |
| Missing Section 3 tables (BGP) | Claude | Students don't have a quick Device Inventory or Console Access reference |
| Missing cheatsheet (BGP) | Claude | No syntax skeletons or command/purpose reference for the capstone — significant pedagogy loss |
| Missing Section 1 subsections (BGP) | Claude | Theory coverage is a single paragraph vs Pi's 7 subsections |
| No TOC entries (BGP) | Claude | Navigation is harder without anchor links at the top |

---

## 8. Recommendations

### For Pi

1. **Add last-octet labels to drawio diagrams.** This is the single highest-impact improvement. Each link endpoint needs a `.N` edgeLabel cell positioned near the router icon.

2. **Consider the Scenario format for capstones.** Claude's BGP Scenario A–I format is a genuine pedagogical improvement. Pi could adopt a hybrid: keep the bullet-step verification format but frame each task as a Situation/Constraints/Acceptance block.

3. **Add a Verification Summary Matrix.** A one-table checklist at the top of Section 6 mapping check numbers to device/command/expected output is extremely student-friendly.

4. **Include security badges on topology diagrams.** Visual indicators for GTSM, MD5, and other security features make the diagram more informative.

### For Claude

1. **Restore Section 3 tables in BGP workbook.** Device Inventory, Loopback, Cabling, Console Access, and Advertised Prefixes tables are contract requirements.

2. **Add TOC entries and named Section 1 subsections.** The BGP workbook needs the standard 11-section structure with anchor-linked TOC.

3. **Add a cheatsheet (Section 7).** Syntax skeletons, command/purpose tables, and failure causes are essential for a capstone lab that covers 10+ blueprint bullets.

4. **Maintain format consistency across labs.** The MPLS lab follows the contract; the BGP lab innovates away from it. Either standardize on the Scenario format for all capstones or maintain the Task format consistently.

---

## 9. Final Comparative Scores

| Lab | Agent | Workbook Score | Topology Score | Overall | Verdict |
|-----|-------|---------------|---------------|---------|--------|
| MPLS Capstone | Claude | 8.0 | 9.0 | **8.2** | Winner |
| MPLS Capstone | Pi | 8.0 | 6.0 | **7.8** | — |
| BGP Capstone | Claude | 6.6 | 9.0 | **7.1** | — |
| BGP Capstone | Pi | 8.3 | 6.0 | **7.9** | Winner |

**Final result: 1–1 split.** Claude wins the MPLS comparison on topology diagram quality. Pi wins the BGP comparison on workbook completeness and contract compliance. The topology gap (last-octet labels) is Pi's most significant weakness across both labs; the contract compliance gap (missing sections/tables) is Claude's most significant weakness in the BGP lab.

**The ideal capstone lab would combine:** Pi's workbook structure (full compliance, rich theory, complete cheatsheet) + Claude's topology diagrams (last-octet labels, security badges, overlay links) + Claude's BGP Scenario task format.
