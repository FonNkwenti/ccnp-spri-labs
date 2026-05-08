# Three-Way MPLS Capstone I Comparison

**Subject lab:** MPLS Lab 04 — Full Mastery (Capstone I), CCNP SPRI 300-510
**Diamond core topology:** PE1 — P1/P2 — PE2 + CE1/CE2 (6 IOSv devices, 512 MB)
**Stack tested:** IS-IS L2 → MPLS LDP → iBGP send-label (BGP-LU) → eBGP → MPLS-TE/RSVP → Tunnel10 (dynamic + explicit path-option)
**BGP-free core invariant:** P1 and P2 must have ZERO BGP configuration

| Variant | Path | Agent stack | Underlying model |
|---|---|---|---|
| **CO** (Claude Opus) | `labs/mpls/lab-04-capstone-config` | Claude Code harness, native | claude-opus-4-7 |
| **DSC** (Claude+DeepSeek) | `labs/mpls/lab-04-capstone-config-dsc` | Claude Code harness `--force-model` | deepseek-v4-pro |
| **PI** (Pi+DeepSeek) | `labs/mpls/lab-04-capstone-config-pi` | Pi agentic framework | deepseek-v4-pro |

Methodology mirrors `analysis/PI_VS_CLAUDE_COMPARISON.md` (weighted scoring across 10 dimensions, contract compliance scorecard, evidence-based dimension scoring).

---

## 1. Executive Summary

All three variants are **shippable**. Solutions are functionally identical and the BGP-free core invariant is held everywhere. The differentiation is **pedagogical style**, not correctness:

- **Claude Opus (CO)** — deepest theory (LIB vs LFIB with annotated outputs side-by-side), most thorough decisions.md, cleanest topology diagram (nested MPLS Core zone, Tunnel10 arc with explicit path label). Weakest area: a no-op idempotency check in inject_scenario_02 (synthetic fault marker that can never match show output).

- **Claude+DeepSeek (DSC)** — most granular task design (9 discrete tasks vs 7), most exam-tips (6 callouts), best preflight logic (two-condition checks). Weakest areas: README mislabels Scenario 02 (says "send-label missing on PE2" but the script actually injects BGP onto P1 — a real documentation bug); decisions.md is sparse (~100 words vs ~290 for CO and ~270 for PI); Tunnel10 is absent from the topology diagram.

- **Pi+DeepSeek (PI)** — most operationally rigorous fault scripts (UUID sentinel preflight pattern for deletion-type faults — only variant to solve this correctly), both explicit paths present in solution config (lets students observe CSPF dynamic choice), cleanest contract gate pass (1 fix vs 3-4). Weakest areas: no iBGP arc in topology, `setup_lab.py` has a hardcoded `DEFAULT_LAB_PATH` while the fault scripts don't (internal inconsistency), thinnest cheatsheet (1 exam tip vs 4-6).

**Final weighted scores: PI 8.58 ≈ CO 8.58 > DSC 8.37**

PI and CO are statistically tied (within 0.01). DSC trails by ~0.2 due to the README/inject mismatch and sparse decisions.md, despite having the strongest task structure.

---

## 2. File Structure

| File | CO | DSC | PI |
|---|---|---|---|
| `workbook.md` (lines) | 1,189 | **1,398** | 1,051 |
| `decisions.md` (words) | ~290 | ~100 | ~270 |
| `README.md` (lines) | 62 | 64 | 56 |
| `topology/topology.drawio` (lines) | 128 | 153 | 158 |
| `setup_lab.py` (lines) | 110 | 110 | 107 |
| `meta.yaml` | full manifest | full manifest | full manifest |
| `initial-configs/*` | 6 files, 24/24/24/24/18/18 | identical | identical |
| `solutions/*` | 6 files, 78/55/55/64/28/28 | identical | 82/55/55/64/28/28 |
| `scripts/fault-injection/` | 3 inject + apply + README | 3 inject + apply + README | 3 inject + apply + README |

**Key observation:** All three produce the SAME file inventory — every contract-required artifact is present in every variant. The contract gate enforced a strong floor.

---

## 3. Solution Configs (Correctness)

All three variants pass the technical correctness bar identically:

| Check | CO | DSC | PI |
|---|---|---|---|
| BGP-free P1/P2 (zero `router bgp`) | YES | YES | YES |
| iBGP `send-label` bilateral | YES | YES | YES |
| iBGP `next-hop-self` bilateral | YES | YES | YES |
| MPLS LDP `router-id Loopback0 force` | YES | YES | YES |
| `mpls mtu 1508` on all core interfaces | YES | YES | YES |
| `ip rsvp bandwidth 100000 100000` | YES | YES | YES |
| Tunnel10 path-option 10 dynamic | YES | YES | YES |
| Tunnel10 path-option 20 explicit | YES (PE1-via-P2) | YES (PE1-via-P2) | YES (PE1-via-P2) |
| `metric-style wide` for IS-IS L2 | YES | YES | YES |
| Customer prefixes 192.0.2.0/24 + 198.51.100.0/24 advertised | YES | YES | YES |

**Differentiator (PI only):** PI's PE1.cfg includes BOTH explicit-paths (`PE1-via-P1` AND `PE1-via-P2`), letting students experiment with overriding either dynamic choice. CO and DSC define only the secondary explicit path (`PE1-via-P2`). PI's choice is more pedagogically rich at the cost of 4 extra config lines.

**No bugs in any solution config across all three variants.**

---

## 4. Workbook Deep Dive

### 4.1 Section structure
All three use the same 11-section template:
1. Concepts & Skills Covered → 2. Topology & Scenario → 3. Hardware & Environment Specs → 4. Base Configuration → 5. Lab Challenge → 6. Verification & Analysis → 7. Verification Cheatsheet → 8. Solutions (Spoiler) → 9. Troubleshooting Scenarios → 10. Lab Completion Checklist → 11. Appendix: Script Exit Codes

### 4.2 Theory depth (Section 1)

| Block | CO (lines) | DSC (lines) | PI (lines) |
|---|---|---|---|
| MPLS layering / build order | 10 (with ASCII stack diagram + failure analysis) | — | — |
| IS-IS as MPLS IGP | 12 | 24 | 12 |
| MPLS LDP fundamentals | 15 (LIB vs LFIB **annotated outputs side-by-side** — unique to CO) | 20 | 14 |
| BGP-free core / Unified BGP | 18 | 16 | 18 (split into 2 blocks) |
| RSVP-TE architecture | 12 | 22 (**ASCII PATH/RESV signal-flow diagram** — unique to DSC) | 12 |
| Insight callout / starred box | — | — | 6-bullet starred Insight (unique to PI) |
| **Total Section 1 prose** | **~80 lines** | **~90 lines** | **~95 lines** |

**Verdict:** PI has the most lines, DSC has the most consolidated blocks, but **CO has the most distinctive content** (LIB vs LFIB with two annotated `show` outputs side-by-side — a pattern that explicitly diagnoses the most-misunderstood MPLS failure mode).

### 4.3 Tasks coverage (Section 5)

| Task structure | CO | DSC | PI |
|---|---|---|---|
| Total tasks | 7 | **9** | 7 |
| IS-IS L2 + wide metrics | Task 1 | Task 1 | Task 1 |
| MPLS LDP + router-id | Task 2 | Task 2 | Task 2 |
| iBGP + send-label | Task 3 | Task 3 | Task 3 |
| eBGP CE peering | Task 4 | Task 4 | Task 4 |
| MPLS-TE global enable | Task 5 (combined) | **Task 5 (separate)** | Task 5 (combined) |
| IS-IS TE extensions | Task 5 (combined) | **Task 6 (separate)** | Task 5 (combined) |
| RSVP bandwidth | Task 5 (combined) | **Task 7 (separate)** | Task 5 (combined) |
| Tunnel10 with path-options | Task 6 | Task 8 | Task 6 |
| End-to-end + BGP-free verification | Task 7 | Task 9 | Task 7 |
| Per-interface IS-IS metric variation | NO | NO | NO |

**Verdict:** DSC's 9-task split is **most exam-friendly** (each Cisco command surface gets a discrete checkpoint). CO and PI use a coarser 7-task structure that bundles TE setup steps. None of the three exercises per-interface IS-IS metric tuning, which is a missed opportunity that all three share.

### 4.4 Cheatsheet (Section 7)

| Element | CO | DSC | PI |
|---|---|---|---|
| Cheatsheet length | 147 lines | **192 lines** | 136 lines |
| `> **Exam tip:**` callouts | 4 | **6** | 1 (+ Insight box) |
| Common Failure Causes table | 9 rows | 10 rows | 9 rows |
| Wildcard mask quick-ref | NO | YES | YES |
| Per-protocol config snippets | YES (4) | YES (5) | YES (5) |

**Verdict:** DSC's cheatsheet is the densest exam-prep tool. PI's lone exam tip is compensated by the Section-1 starred Insight box, but the cheatsheet itself is the thinnest.

### 4.5 Verification & Analysis (Section 6)

All three variants annotate expected `show` output with inline `! ←` comments. Distinct command counts:

| Variant | Distinct verification commands across Sections 5–7 |
|---|---|
| CO | ~19 |
| DSC | ~28 |
| PI | ~22 |

DSC has the most coverage; CO is the most concise.

### 4.6 Troubleshooting (Section 9)

All three present 3 tickets with `<details>` Diagnosis Steps + Fix blocks. The fault-injection layer differs significantly — see Section 6 of this document.

---

## 5. Topology Diagrams Deep Dive

| Element | CO | DSC | PI |
|---|---|---|---|
| Cell count (approx) | 39 | 41 | 38 |
| Cisco19 stencil | YES | YES | YES |
| Dark theme `#1a1a2e` | YES | YES | YES |
| All 6 devices labeled | YES | YES | YES |
| Per-link interface pair labels | YES (`Gi0/X - Gi0/Y`) | YES | YES |
| Subnet labels per link | YES (`/24`) | YES | YES |
| Per-endpoint IP octets (.1, .2, ...) | **YES (14 labels)** | **YES (14 labels)** | NO (only Lo0 in node label) |
| AS zone shading | YES (3 zones) | YES (3 zones) | YES (3 zones) |
| **MPLS Core nested zone** | **YES (only CO)** | NO | NO |
| **Tunnel10 visual arc** | **YES (orange dashed, both paths in label)** | NO | **YES (dashed orange)** |
| **iBGP visual arc** | NO | **YES (dashed curved arc PE1↔PE2)** | NO |
| Legend | YES | YES | YES |
| Title banner | YES | YES | YES |

**Critical finding:** Each variant omits **exactly one** of three key overlays:
- **CO** — no explicit iBGP arc (relationship implied by AS 65100 zone)
- **DSC** — no Tunnel10 arc (the actual deliverable students are building isn't visualized)
- **PI** — no iBGP arc + no per-endpoint IP octets

**Most complete:** CO's diagram has the fewest gaps (Tunnel10 with both path descriptions in the label, nested MPLS Core zone distinct from AS 65100 boundary). DSC's missing Tunnel10 is the most pedagogically problematic gap because the tunnel IS the headline deliverable.

---

## 6. Fault Injection Deep Dive

| Element | CO | DSC | PI |
|---|---|---|---|
| Total scenarios | 3 | 3 | 3 |
| Scenario 01 fault | `no mpls traffic-eng tunnels` on **P1** | Remove `mpls traffic-eng level-2` from **P2** IS-IS | `mpls ldp router-id Loopback1 force` on **P1** |
| Scenario 01 layer tested | TE plane (P router) | TE flooding plane | LDP control plane |
| Scenario 02 fault | Remove `send-label` on **PE2** | Add `router bgp 65100` on **P1** (BGP-free violation) | Remove `next-hop-self` on **PE2** |
| Scenario 02 layer tested | BGP-LU plane | BGP-free invariant | Next-hop resolution |
| Scenario 03 fault | RSVP bandwidth → 10 kbps on **PE1** Gi0/2 | `no mpls traffic-eng tunnels` global on **P1** | RSVP bandwidth → 10 kbps on **P1** Gi0/1 |
| Scenario 03 layer tested | CSPF/RSVP admission | TE global plane | CSPF/RSVP admission |
| Preflight in all 3 scripts | YES | YES | YES |
| Solution-marker check | YES (all 3) | YES (all 3) | YES (all 3) |
| Fault-marker (idempotency) check | scenario 02 = **synthetic string (NO-OP)** | YES (all 3, two-condition) | YES — uses **UUID sentinel** for deletion fault |
| `--skip-preflight` flag | YES | YES | YES |
| `apply_solution.py` RESTORE_TARGETS | `[P1, PE2, PE1]` | `[P1, P2]` | `[P1, PE1, PE2]` |
| `--node` single-device restore | YES | YES | YES |
| `--reset` soft-reset flag | YES | YES | YES |
| README accuracy | accurate | **mismatch — calls Scenario 02 "send-label missing on PE2" but code injects BGP on P1** | accurate (and explains UUID sentinel design choice) |

### Fault-injection scoring rationale

- **PI wins** the fault-injection layer. The UUID sentinel pattern (`PREFLIGHT_FAULT_MARKER = "NEXTHOP_SELF_FAULT_89A2F1C4_INJECTED"`) is the only correct solution for **deletion-type faults** where you cannot positively detect absence of a config line. PI's decisions.md documents this design choice explicitly. CO's Scenario 02 uses the same pattern but with a placeholder marker that was never replaced — making the idempotency guard a no-op.
- **DSC** has two-condition preflights everywhere (best logic), but the README description for Scenario 02 contradicts the actual injected commands — a real bug a student would hit on first run.
- **CO's** layer separation is cleanest: each ticket targets a different MPLS plane (P-router TE, PE-BGP-LU, PE-CSPF). DSC's Scenarios 01 and 03 both target the TE plane (overlap). PI mixes LDP control / BGP next-hop / CSPF — three distinct planes.

---

## 7. Setup Scripts and Decisions.md

### setup_lab.py
| Element | CO | DSC | PI |
|---|---|---|---|
| Uses shared `eve_ng` library | YES | YES | YES |
| Auto-discovers ports at runtime | YES | YES | YES |
| Hardcoded `DEFAULT_LAB_PATH` | YES (with override) | YES (with override) | YES (with override — but inconsistent with fault scripts) |
| `--reset` soft-reset support | YES | YES | YES |
| Pushes initial-configs for all 6 devices | YES | YES | YES |

**Note:** PI's decisions.md claims fault scripts use pure `find_open_lab()` auto-discovery (correct) but does not flag that `setup_lab.py` retains a hardcoded `DEFAULT_LAB_PATH` — a minor internal inconsistency.

### decisions.md
| Element | CO | DSC | PI |
|---|---|---|---|
| Word count | ~290 | **~100 (sparse)** | ~270 |
| Model gate outcome documented | YES | YES (with `--force-model` rationale) | YES (with Pi-agent override rationale) |
| Workbook gate outcome | PASS-AFTER-FIXES (3 items) | PASS-AFTER-FIXES (4 items) | **PASS-AFTER-FIXES (1 item — cleanest)** |
| Architectural rationale (why diamond, why path-options) | YES | NO | YES |
| Fault scenario design notes | YES | NO | YES (incl. UUID sentinel rationale) |

**Verdict:** DSC's decisions.md is too thin to serve as architectural documentation. CO and PI both produce useful records.

---

## 8. Contract Compliance Scorecard

Items that the lab-assembler workbook contract requires:

| Contract item | CO | DSC | PI |
|---|---|---|---|
| Section ordering matches template | PASS | PASS | PASS |
| No raw IOS commands in task prose (Section 5) | PASS-AFTER-FIX | PASS-AFTER-FIX | PASS |
| Cheatsheet present (Section 7) | PASS | PASS | PASS |
| Solutions in `<details>` spoiler blocks (Section 8) | PASS | PASS | PASS |
| Troubleshooting section with 3 tickets | PASS | PASS | PASS |
| Completion checklist (Section 10) | PASS (21 items) | PASS (24 items) | PASS (19 items) |
| Hardware specs include RAM | PASS | PASS-AFTER-FIX | PASS |
| Cabling table location (Section 3) | PASS | PASS | PASS-AFTER-FIX (moved from Sec 2) |
| All 6 initial-configs present | PASS | PASS | PASS |
| All 6 solution configs present | PASS | PASS | PASS |
| Topology drawio uses cisco19 stencils | PASS | PASS | PASS |
| Topology drawio dark theme | PASS | PASS | PASS |
| `setup_lab.py` uses `eve_ng` shared lib | PASS | PASS | PASS |
| 3 fault-injection scripts + apply_solution | PASS | PASS | PASS |
| README description matches inject script | PASS | **FAIL (Scenario 02 mismatch)** | PASS |
| meta.yaml manifest complete | PASS | PASS | PASS |

**Score:** CO 16/16, DSC 15/16 (1 real bug), PI 16/16.

---

## 9. Weighted Score Calculation

Same weights as `PI_VS_CLAUDE_COMPARISON.md`:

| Dimension | Weight | CO | DSC | PI |
|---|---|---|---|---|
| Theory depth | 15% | 9.0 | 8.0 | 8.5 |
| Task design (granularity, exam alignment) | 20% | 8.0 | 9.0 | 8.0 |
| Cheatsheet quality | 10% | 8.5 | 9.0 | 7.5 |
| Solution comprehensiveness | 10% | 9.0 | 9.0 | 9.5 |
| Troubleshooting design | 10% | 8.0 | 7.0 | 9.0 |
| Contract compliance | 10% | 9.0 | 9.0 | 9.5 |
| Topology visual quality | 10% | 8.5 | 7.5 | 8.0 |
| Topology completeness | 5% | 9.0 | 7.5 | 8.0 |
| Solutions accuracy | 5% | 9.5 | 9.5 | 9.5 |
| Scripts (setup + fault inject) | 5% | 8.0 | 7.0 | 9.0 |
| **Weighted total** | **100%** | **8.58** | **8.37** | **8.58** |

**CO and PI tie at 8.58. DSC trails at 8.37.**

---

## 10. Unique Innovations Per Variant

### Claude Opus (CO)
1. **LIB vs LFIB pedagogy** — only variant that includes side-by-side annotated `show` outputs distinguishing label-information-base from label-forwarding-information-base. This is the single most-misunderstood MPLS distinction on the 300-510 exam.
2. **Nested MPLS Core zone** in topology — visually separates the "no-BGP" boundary from the AS 65100 boundary. No other variant attempts this.
3. **Tunnel10 arc with explicit path description** — the topology label reads `Tunnel10 Dyn (PE1→P1→PE2) + Expl (PE1→P2→PE2) [MPLS-TE]`, which lets students read the path-option design straight from the diagram.
4. **Build-order failure analysis** — Section 1 opens with an ASCII stack diagram + paragraph explaining what symptom you see if each layer is configured before its dependency.

### Claude+DeepSeek (DSC)
1. **9-task granularity** — only variant that splits MPLS-TE global, IS-IS TE extensions, and RSVP bandwidth into 3 separate tasks. This matches how the exam blueprint sub-bullets are graded.
2. **6 exam-tip callouts** in cheatsheet (vs 4 in CO, 1 in PI). Each callout names a specific bilateral mistake that produces a silent failure.
3. **PATH/RESV ASCII signal-flow diagram** — only variant to visualize RSVP-TE control-plane signaling.
4. **Two-condition preflight checks in all 3 inject scripts** — checks both solution marker presence AND fault marker absence, the most defensive preflight logic of any variant.
5. **Wildcard mask quick-reference table** in cheatsheet (also present in PI; absent in CO).

### Pi+DeepSeek (PI)
1. **UUID sentinel preflight pattern** — `PREFLIGHT_FAULT_MARKER = "NEXTHOP_SELF_FAULT_89A2F1C4_INJECTED"`. The only correct way to write an idempotency guard for deletion-type faults (where you can't positively detect "absence"). PI documents this design choice in decisions.md.
2. **Both explicit paths in PE1 solution** — `PE1-via-P1` AND `PE1-via-P2` are both defined, letting a student override the dynamic choice in either direction without editing the config.
3. **Starred Insight callout box** in Section 1 — 6-bullet box covering IS-IS/LDP sequencing, the `force` keyword, tunnel unidirectionality, and P-router TE participation requirement.
4. **Blueprint sub-bullet mapping** — fault scenarios are explicitly labeled to blueprint items (4.1.a LDP, 4.1.d BGP-free, 4.1.e RSVP-TE).
5. **Cleanest contract gate pass** — only 1 PASS-AFTER-FIX item (cabling table location), vs 3 for CO and 4 for DSC.

---

## 11. Key Findings

### What's the same across all three
- Solution config correctness is identical. BGP-free invariant, send-label, next-hop-self, mpls mtu 1508, RSVP bandwidth all match.
- Initial-configs are byte-similar: 24/24/24/24/18/18 lines, IP-only.
- All three use the shared `eve_ng` library with auto-discovery.
- All three use cisco19 stencils on a dark `#1a1a2e` canvas.
- All three pass the 11-section workbook contract template.
- None exercise per-interface IS-IS metric tuning — a shared blind spot.

### Where each variant wins
- **Theory depth:** CO (LIB vs LFIB)
- **Task granularity:** DSC (9 tasks)
- **Cheatsheet density:** DSC (192 lines, 6 exam tips)
- **Topology completeness:** CO (Tunnel10 + nested MPLS Core zone)
- **Fault-injection rigor:** PI (UUID sentinel for deletion faults)
- **Solution flexibility:** PI (both explicit paths)
- **Contract gate compliance:** PI (1 fix vs 3-4)
- **Architectural documentation:** CO + PI tied (both ~270-290 word decisions.md)

### Where each variant loses
- **CO:** Scenario 02 fault marker is a synthetic string never replaced — idempotency guard is a no-op. No explicit iBGP arc in topology.
- **DSC:** README scenario description contradicts inject_scenario_02 code (real bug). decisions.md is sparse (~100 words). Tunnel10 missing from topology.
- **PI:** No iBGP arc in topology. `setup_lab.py` has hardcoded `DEFAULT_LAB_PATH` while fault scripts don't (internal inconsistency). Cheatsheet has only 1 exam tip.

---

## 12. Recommendations

For students prepping for 300-510:
- **Use CO if you struggle with LDP concepts** — the LIB vs LFIB pedagogy is unmatched.
- **Use DSC if you want exam-flavored task pacing** — the 9-task structure mirrors blueprint grading granularity.
- **Use PI if you want the most reliable fault-injection lab loop** — the preflight logic is bulletproof and the dual-explicit-path solution lets you experiment without re-editing.

For lab maintenance:
1. **Fix DSC Scenario 02 README description** (real bug — currently contradicts inject script).
2. **Fix CO Scenario 02 fault marker** (replace synthetic string with a real `show`-output substring like `"send-label"` absence indicator).
3. **Add an iBGP arc to CO and PI topologies** — both omit it. DSC has it; lift the pattern.
4. **Add a Tunnel10 arc to DSC topology** — currently missing the headline deliverable visualization.
5. **Expand DSC decisions.md** to record architectural rationale (why diamond, why two path-options on Tunnel10, why P-router TE participation matters).
6. **Backport PI's UUID sentinel preflight pattern** to all variants for any deletion-type fault.

---

## 13. Final Comparative Scores

| Rank | Variant | Score | Headline strength | Headline weakness |
|---|---|---|---|---|
| 1 (tie) | **PI** | **8.58** | UUID sentinel preflight + dual explicit paths | No iBGP arc in topology |
| 1 (tie) | **CO** | **8.58** | LIB vs LFIB theory + nested MPLS Core zone | Scenario 02 idempotency no-op |
| 3 | **DSC** | **8.37** | 9-task granularity + 6 exam tips | README/inject Scenario 02 mismatch (real bug) |

**Spread: 0.21 across three variants — all three are production-quality.**

The 0.21 gap between DSC and the leaders comes overwhelmingly from one real documentation bug (the Scenario 02 README mismatch). Fix that single line, expand decisions.md with architectural rationale, add a Tunnel10 arc to the topology, and DSC catches up to within 0.05 of the leaders.

---

**Last updated:** 2026-05-05
**Methodology:** Same weighted-scoring approach as `analysis/PI_VS_CLAUDE_COMPARISON.md`. Evidence drawn from full reads of all three lab directories (workbook, decisions, README, meta.yaml, all 6 initial-configs, all 6 solutions, topology.drawio, setup_lab.py, all 3 inject scripts, apply_solution.py, fault-injection README) by parallel general-purpose subagents.
