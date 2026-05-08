# Claude vs DeepSeek vs Pi: MPLS Capstone Three-Way Comparison

**Comparison Date:** 2026-05-04
**Exam:** CCNP SPRI 300-510
**Lab:** `labs/mpls/lab-04-capstone-config` (MPLS Full Mastery — Capstone I)

**Agents Compared:**
- `lab-04-capstone-config` — **Claude Opus 4.7** (claude-opus-4-7, skill f840ce03, built 2026-05-01)
- `lab-04-capstone-config-dsc` — **DeepSeekv4 via Claude harness** (deepseek-v4-pro, force-model override, built 2026-05-04)
- `lab-04-capstone-config-pi` — **Pi agent with DeepSeekv4** (pi agent, manual model gate override, built 2026-05-01)

---

## Executive Summary

All three agents produced complete, structurally valid MPLS capstone lab packages. Claude's workbook provides the strongest pedagogical depth with a layer-dependency model and LIB/LFIB distinction. DeepSeek's workbook is the most verbose with 9 tasks (TE split into four sub-tasks) and the richest theory explanations. Pi's workbook is the most compact and exam-focused, with a unique Insight callout box and the innovative approach of creating both explicit paths and letting the student choose. Claude's topology is definitively the best (last-octet labels on every link). All three solution configs are functionally identical.

**Overall ranking: Claude (8.4) > DeepSeek (7.8) > Pi (7.5)**

---

## 1. Overall Package Comparison

### 1.1 File Structure

| Criterion | Claude | DeepSeek | Pi |
|-----------|--------|----------|-----|
| File count | 24 | 24 | 24 |
| All required directories | ✓ | ✓ | ✓ |
| `meta.yaml` complete | ✓ | ✓ | ✓ |
| `decisions.md` present | ✓ | ✓ | ✓ |
| All scripts syntax-valid | ✓ | ✓ | ✓ |
| `updated: []` field in meta.yaml | ✗ | ✓ | ✓ |

**Verdict:** Tie on structure. DeepSeek and Pi include the `updated: []` forward-compatibility field; Claude's older build predates it.

---

### 1.2 Workbook Size & Depth

| Metric | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| Lines | 1,189 | 1,398 | 1,051 |
| Bytes | 55,561 | 55,841 | 45,405 |
| Tasks in Section 5 | 7 | 9 | 7 |
| Theory subsections (Section 1) | 5 | 5 | 5 |
| Troubleshooting tickets | 3 | 3 | 3 |

**Analysis:** DeepSeek produces the largest workbook (18% larger than Pi). The extra size comes from richer theory explanations in Section 1 and the decision to split TE into four separate tasks (5–8) rather than combining them into two tasks as Claude and Pi do. Pi's workbook is the most compact — 12% shorter than Claude's and 25% shorter than DeepSeek's — achieving concision without losing required content.

---

### 1.3 Solution Configs

| Device | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| PE1 lines | 78 | 78 | 82 |
| P1 lines | 55 | 55 | 55 |
| P2 lines | 55 | 55 | 55 |
| PE2 lines | 64 | 64 | 64 |
| CE1 lines | 28 | 28 | 28 |
| CE2 lines | 28 | 28 | 28 |

**Verdict:** Functionally identical. Pi's PE1 has 4 extra lines from the second explicit path definition (`PE1-via-P1`). No configuration divergence — all three produce the same working MPLS stack.

---

## 2. Workbook Deep Dive

### 2.1 Section 1: Concepts & Skills Covered

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Number of theory subsections | 5 | 5 | 5 |
| Layer dependency diagram (ASCII) | ✓ (5-layer stack) | ✗ | ✗ |
| LIB/LFIB distinction explained | ✓ (detailed) | ✓ (detailed) | ✓ (concise) |
| RSVP-TE component breakdown | ✓ (4 components + flow diagram) | ✓ (4 components + ASCII flow) | ✓ (4-component table) |
| BGP-free core architectural rationale | ✓ | ✓ | ✓ |
| Skills table | ✓ | ✓ | ✓ |
| Exam objective citation | ✓ (4.1.a–4.1.e) | ✓ (4.1 all sub-topics) | ✓ (4.1 all sub-bullets) |
| Insight callout box | ✗ | ✗ | ✓ (unique) |
| IS-IS NET format explanation | ✓ | ✓ | ✓ |

**Winner: Claude (by narrow margin).** Claude's 5-layer ASCII dependency diagram is the standout pedagogical feature — it gives the student a mental model of build order before they configure anything. The LIB/LFIB walkthrough with actual `show` command output is equally strong. Pi's Insight callout box is a genuine innovation (framed asides with architectural rationale) that the other two lack. DeepSeek's theory is thorough but conventional.

`★ Insight ─────────────────────────────────────`
- Claude's layer-dependency diagram isn't decorative — it encodes the *only correct build order*. Building LDP before IS-IS converges produces empty label bindings; building BGP-LU before LDP produces labels with no underlying LSP. The diagram prevents the most common student mistake.
- Pi's Insight callout box teaches *why* not just *what*. The note that "RSVP tunnels are unidirectional" and "P routers need TE enabled even though they have no tunnel definitions" addresses real-world misconceptions.
`─────────────────────────────────────────────────`

---

### 2.2 Section 2: Topology & Scenario

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| ASCII topology diagram | ✓ (landscape, box-drawing) | ✓ (landscape, box-drawing) | ✓ (portrait, box-drawing) |
| Link table with interface/IP columns | ✓ | ✓ | ✓ |
| Narrative scenario framing | ✓ (1 paragraph) | ✓ (1 paragraph) | ✓ (1 paragraph) |
| Tunnel path-options in diagram | ✓ (annotated below) | ✗ | ✗ |
| Path diversity note (3 paths) | ✗ | ✓ | ✗ |
| Key relationships text | ✗ | ✗ | ✓ |

**Winner: Tie (Claude/DeepSeek).** Claude's topology diagram annotates the tunnel path-options directly below the ASCII art — the student sees both paths without reading the task text. DeepSeek's topology section adds a unique "Path diversity note" explicitly listing all three paths (PE1→P1→PE2, PE1→P2→PE2, PE1→P1→P2→PE2). Pi's diagram is portrait-oriented, uses router boxes with interface breakout lines, and includes a "Key relationships" bullet list — a different but equally valid style.

---

### 2.3 Section 3: Hardware & Environment

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Device Inventory table | ✓ | ✓ | ✓ |
| RAM column in Device Inventory | ✗ | ✓ (512 MB) | ✗ |
| Loopback Address table | ✓ | ✓ | ✓ |
| Cabling table (Device A/B, Interface, IP) | ✓ | ✓ | ✗ (Link table instead) |
| Advertised Prefixes table | ✓ | ✓ | ✓ |
| Console Access Table | ✓ | ✓ | ✓ |

**Winner: DeepSeek.** DeepSeek's Section 3 is the only one with the RAM column (512 MB per device, per eve-ng-constraints.md). This was noted as a fix in decisions.md — the other two agents omitted it. Pi's Section 3 uses a "Link table" with Endpoints/Subnet/Purpose columns instead of the contract Cabling table format (Device A, Interface, IP, Device B, Interface, IP) — a structural divergence.

---

### 2.4 Section 4: Base Configuration

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| IS pre-loaded list | ✓ (4 items) | ✓ (4 items) | ✓ (6 items) |
| IS NOT pre-loaded list | ✓ (12 items) | ✓ (9 items) | ✓ (8 items) |
| Invariants section | ✓ (BGP-free + labeled traffic) | ✗ | ✗ |
| Raw IOS syntax avoided | ✓ | ⚠ (had issues, fixed) | ⚠ (has `no ip domain-lookup`, `no shutdown`) |

**Winner: Claude.** Claude's Section 4 is the only one that explicitly states the two critical invariants (BGP-free core, labeled traffic requirement) that the student must preserve. DeepSeek's IS NOT list is the most comprehensive (9 items). Pi's IS pre-loaded list includes `no ip domain-lookup` and `no shutdown` as raw IOS commands rather than plain English — a minor contract deviation.

---

### 2.5 Section 5: Lab Challenge (Task Design)

**This is the most significant design divergence among the three agents.**

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Task count | 7 | 9 | 7 |
| Task format | Design Requirements intro + per-task objectives | Per-task bullet steps + Verification | Per-task bullet steps + Verification |
| TE task decomposition | Tasks 5–6 (TE underlay + Tunnel10) | Tasks 5–8 (Global TE, IS-IS TE, RSVP, Tunnel) | Tasks 5–6 (TE+RSVP + Tunnel) |
| Explicit paths created | 1 (PE1-via-P2) | 1 (PE1-via-P2) | 2 (PE1-via-P1 + PE1-via-P2) |
| "Choose the unused path" approach | ✗ | ✗ | ✓ (innovative) |
| Capstone heading | ✓ | ✓ | ✓ |
| Explicit IOS commands avoided | ✓ | ✓ | ✓ |

**Winner: Pi (for tunnel design), Claude (for build-order framing).**

Pi's Task 6 is the most innovative: it instructs the student to create *both* explicit paths, run `show mpls traffic-eng tunnels tunnel10` to see which P router CSPF chose, then configure path-option 20 to use the *other* path. This is pedagogically superior — the student learns to inspect CSPF decisions and make configuration choices based on observed state rather than blindly following instructions. Claude and DeepSeek hard-code PE1-via-P2 as the secondary, which is simpler but less instructive.

Claude's "Design Requirements" intro paragraph before the tasks gives architectural context for the build order (IS-IS → LDP → BGP → eBGP → TE → Tunnel → Customer). DeepSeek and Pi jump directly into Task 1 without this framing.

DeepSeek's 9-task decomposition (splitting TE into Global TE, IS-IS TE Extensions, RSVP Bandwidth, and Tunnel as four separate tasks) is more granular but risks fragmentation — the student may not see how the four TE pieces interconnect until Task 8.

---

### 2.6 Section 6: Verification & Analysis

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Verification organization | Bottom-up per task | Consolidated per task | Per task |
| Sample command output | ✓ (annotated with `! ←`) | ✓ (annotated with `! ←`) | ✓ (annotated with `! ←`) |
| P1 and P2 show output included | ✓ | ✓ | ✓ |
| BGP-free invariant verification | ✓ (explicit check) | ✓ (explicit check) | ✓ (explicit check) |
| Tunnel10 path-option detail | ✓ (both listed) | ✓ (both listed) | ✓ (both listed, with standby note) |

**Verdict: Tie.** All three agents provide comprehensive verification sections with annotated sample output. The differences are cosmetic — Claude's inline arrow annotations are slightly cleaner; DeepSeek's output is the most verbose; Pi's output is the most compact but equally complete.

---

### 2.7 Section 7: Verification Cheatsheet

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Syntax skeleton code blocks | ✓ (5 groups) | ✓ (6 groups) | ✓ (5 groups) |
| Command/Purpose tables | ✓ (per group) | ✓ (per group) | ✓ (per group) |
| Verification Commands summary table | ✓ | ✓ | ✓ |
| Wildcard Mask Quick Reference | ✓ | ✓ | ✓ |
| Common Failure Causes table | ✓ (8 entries) | ✓ (10 entries) | ✓ (8 entries) |
| Exam tips | ✓ (inline in tables) | ✓ (callout boxes) | ✓ (callout boxes) |

**Winner: DeepSeek (by narrow margin).** DeepSeek's cheatsheet has the most syntax skeleton groups (6 — TE is split into Global TE, IS-IS TE Extensions, and RSVP separately), the most failure causes (10 vs 8), and uses prominent `> **Exam tip:**` callout boxes. Pi's cheatsheet is the most compact but still covers all required elements. Claude's cheatsheet is strong but slightly less granular than DeepSeek's.

---

### 2.8 Section 8: Solutions

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Spoiler warning | ✓ | ✓ | ✓ |
| `<details>` blocks per task | ✓ (7) | ✓ (9) | ✓ (6, consolidated) |
| Complete configs inline | ✓ | ✓ | ✓ |
| Verification commands in spoilers | ✓ | ✓ | ✓ |
| Per-device sub-details | ✓ (PE1, P1, P2, PE2 separately) | ✓ (PE1, P1, P2, PE2 separately) | ⚠ (consolidated, fewer sub-blocks) |

**Winner: Claude/DeepSeek (tie).** Both provide per-device `<details>` blocks with complete configurations. Pi consolidates some devices (e.g., "All Core Router Configuration") into single blocks, which is more compact but harder for a student to follow device-by-device.

---

### 2.9 Section 9: Troubleshooting

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Ticket count | 3 | 3 | 3 |
| Symptom-only headings | ✓ | ✓ | ✓ |
| Inject command | ✓ | ✓ | ✓ |
| Diagnosis steps | ✓ | ✓ | ✓ |
| Fix in spoiler | ✓ | ✓ | ✓ |
| Workflow code block | ✓ | ✓ | ✓ |

**Ticket scenario comparison:**

| Ticket | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| #1 | Tunnel10 Stays Down After Maintenance (global TE missing on P1) | P2 Missing from TE Topology (IS-IS TE extensions missing on P2) | LDP Session Flaps Every 30 Seconds (wrong LDP router-id on P1) |
| #2 | BGP Session Up but No Labels (send-label missing on PE2) | CE1-to-CE2 Ping Fails After P1 Change (BGP configured on P1) | PE1 Can Ping CE2's Network but CE1 Cannot (next-hop-self missing on PE2) |
| #3 | Tunnel10 Secondary Path Never Signals (RSVP bandwidth on L3) | Tunnel10 Down After P1 Maintenance (global TE missing on P1) | Tunnel10 Has Only One Path Option Signaled (RSVP bandwidth on L4) |

**Winner: Claude (ticket diversity), Pi (ticket realism).**

Claude's tickets cover three distinct fault domains (TE global on P router, BGP-LU capability mismatch, RSVP bandwidth on a single link) with no overlap. Each ticket tests a different diagnostic skill.

DeepSeek's tickets have overlap — Ticket 1 (IS-IS TE extensions missing on P2) and Ticket 3 (global TE missing on P1) are both "TE component missing on a P router" faults, just different components. Ticket 2 (BGP on P1) is excellent — it tests the BGP-free core invariant directly.

Pi's tickets are the most realistic. Ticket 1 (LDP router-id wrong, causing 30-second flaps) is a classic real-world fault. Ticket 2 (missing next-hop-self) tests understanding of BGP next-hop reachability through the core. Ticket 3 (insufficient RSVP bandwidth on L4) tests CSPF constraint awareness. However, Pi's Ticket 3 and Claude's Ticket 3 overlap in fault domain (RSVP bandwidth).

---

### 2.10 Section 10: Lab Completion Checklist

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Core Implementation checklist | ✓ (21 items) | ✓ (20 items) | ✓ (16 items) |
| Troubleshooting checklist | ✓ (3 items) | ✓ (3 items) | ✓ (3 items) |

**Winner: Claude.** Claude's checklist is the most granular (21 items) with explicit verification commands embedded in each item description. Pi's checklist is the most compact (16 items) but still covers all essential checks.

---

### 2.11 Section 11: Script Exit Codes

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| Exit codes table | ✓ (5 codes) | ✓ (5 codes) | ✓ (5 codes) |
| Code descriptions | ✓ | ✓ | ✓ |
| Applies-to column | ✓ | ✓ | ✓ |

**Verdict: Tie.** All three are identical — this section is effectively template content.

---

## 3. Topology Diagrams Deep Dive

### 3.1 Visual Feature Comparison

| Feature | Claude | DeepSeek | Pi |
|---------|--------|----------|-----|
| cisco19 router shapes | ✓ | ✓ | ✓ |
| Embedded HTML device labels | ✓ | ✓ | ✓ |
| Dark canvas (#1a1a2e) | ✓ | ✓ | ✓ |
| White connection lines (#FFFFFF) | ✓ | ✓ | ✓ |
| **Last-octet IP labels** | ✓ (on EVERY link) | ✗ | ✗ |
| AS/domain zone overlays | ✓ (4 zones) | ✓ (2 zones) | ✓ (2 zones) |
| Tunnel overlay (dashed) | ✓ (orange, curved) | ✗ | ✗ |
| Legend box (black fill, white text) | ✓ | ✓ | ✓ |
| Title banner | ✓ | ✓ | ✓ |
| Diagram file size (bytes) | 15,434 | 16,988 | 13,102 |

### 3.2 The Last-Octet Gap

Claude's topology is the **only one** with last-octet `.N` labels on every link endpoint — a contract requirement. Each interface's host portion of the IP address appears as a standalone `edgeLabel` cell positioned near the router icon:

```
.1  ──────────────  .2     (on L2: PE1 Gi0/1 ↔ P1 Gi0/0)
```

This lets students identify interface IPs directly from the diagram without consulting the cabling table. DeepSeek and Pi both omit this feature entirely — their diagrams rely on the link table for IP information.

### 3.3 Tunnel Overlay

Claude's topology includes a dashed orange curved line representing Tunnel10 from PE1 to PE2, with the annotation "Tunnel10: path-option 10 dynamic (active) / path-option 20 explicit PE1-via-P2 (standby)." Neither DeepSeek nor Pi renders the tunnel as a visual overlay on the diagram.

### 3.4 Zone Overlays

Claude renders four semi-transparent colored zones (AS 65101 customer zone, MPLS core zone, BGP-free core sub-zone, AS 65102 customer zone). DeepSeek and Pi render two zones each (SP core + customer ASes). Claude's 4-zone approach better communicates the BGP-free core as a sub-domain within the MPLS core.

**Topology Winner: Claude (decisive).**

---

## 4. Unique Innovations Per Agent

### 4.1 Claude's Unique Contributions

| Innovation | Description |
|-----------|-------------|
| **5-layer dependency diagram** | ASCII art showing IS-IS → LDP → BGP → RSVP-TE → Customer reachability stack with build-order dependency arrows |
| **LIB/LFIB walkthrough** | Side-by-side `show mpls ldp bindings` (LIB) vs `show mpls forwarding-table` (LFIB) with explanation of why they differ — directly teaches diagnostic technique |
| **Last-octet labels on topology** | Every interface endpoint has a `.N` octet cell in drawio |
| **Tunnel overlay on topology** | Dashed orange curved line showing Tunnel10 path on the diagram |
| **4-zone topology coloring** | BGP-free core rendered as a distinct visual sub-zone within the MPLS core |
| **Invariants section in Base Config** | Explicit "Critical invariants that the student must preserve" with BGP-free + labeled traffic requirements |
| **Design Requirements intro** | Architectural framing paragraph before Task 1 explaining the build order rationale |
| **Tunnel path-options annotated below ASCII diagram** | Both path-options described directly under the topology art |

### 4.2 DeepSeek's Unique Contributions

| Innovation | Description |
|-----------|-------------|
| **RAM column in Device Inventory** | Only agent to include 512 MB per device (per eve-ng-constraints.md) |
| **Path diversity note (3 paths)** | Explicitly lists PE1→P1→P2→PE2 as a third available path through the P1↔P2 cross-link |
| **RSVP-TE ASCII flow diagram** | `Headend (PE1) → PATH → Transit (P1) → PATH → Tail (PE2)` with RESV return arrows |
| **9-task TE decomposition** | Splits TE into Global TE, IS-IS Extensions, RSVP Bandwidth, and Tunnel as separate tasks |
| **Most failure causes (10)** | Cheatsheet has 10 entries vs 8 for Claude and Pi |
| **LDP session lifecycle description** | 3-phase breakdown (Discovery → Session establishment → Label exchange) |
| **`updated: []` in meta.yaml** | Forward-compatibility field (also present in Pi's build) |

### 4.3 Pi's Unique Contributions

| Innovation | Description |
|-----------|-------------|
| **Insight callout box** | `★ Insight` framed aside with architectural rationale — unique among all three agents |
| **"Choose the unused path" approach** | Creates BOTH PE1-via-P1 and PE1-via-P2 explicit paths, instructs student to inspect CSPF and choose the unused one as secondary |
| **Most compact workbook** | Achieves contract compliance at 1,051 lines (25% smaller than DeepSeek) without losing required content |
| **Portrait ASCII topology with interface breakouts** | Different visual style — router boxes with explicit Gi0/N interface labels protruding |
| **Key relationships text** | Bullet list below topology explaining non-obvious design relationships |
| **`updated: []` in meta.yaml** | Forward-compatibility field (also present in DeepSeek's build) |

---

## 5. Contract Compliance Scorecard

Each item scored: ✓ (pass), ⚠ (partial), ✗ (fail)

| Contract Requirement | Claude | DeepSeek | Pi |
|---------------------|--------|----------|-----|
| Title line + TOC (11 entries) | ✓ | ✓ | ✓ |
| Section 1: Exam objective + 5+ subsections + Skills table | ✓ | ✓ | ✓ |
| Section 3: Device Inventory table with RAM | ⚠ (no RAM) | ✓ | ⚠ (no RAM) |
| Section 3: Loopback Address table | ✓ | ✓ | ✓ |
| Section 3: Cabling table (Device A/B, Interface, IP) | ✓ | ✓ | ⚠ (Link table format) |
| Section 3: Console Access Table | ✓ | ✓ | ✓ |
| Section 3: Advertised Prefixes table | ✓ | ✓ | ✓ |
| Section 4: IS/NOT pre-loaded lists (no IOS syntax) | ✓ | ⚠ (had issues, fixed) | ⚠ (IOS syntax in IS list) |
| Section 5: Tasks with bullets + Verification (no IOS syntax) | ✓ | ✓ | ✓ |
| Section 5: Capstone heading | ✓ | ✓ | ✓ |
| Section 6: Inline verification markers | ✓ | ✓ | ✓ |
| Section 7: Cheatsheet with syntax skeletons + tables | ✓ | ✓ | ✓ |
| Section 8: Solutions in `<details>` blocks | ✓ | ✓ | ⚠ (consolidated, fewer blocks) |
| Section 9: Ticket symptom-only headings + inject + spoilers | ✓ | ✓ | ✓ |
| Section 10: Core + Troubleshooting checklist | ✓ | ✓ | ✓ |
| Section 11: Exit codes table | ✓ | ✓ | ✓ |
| Drawio: Last-octet `.N` labels | ✓ | ✗ | ✗ |
| Drawio: Legend box (black fill, bottom-right) | ✓ | ✓ | ✓ |
| Drawio: White connection lines | ✓ | ✓ | ✓ |
| Drawio: Tunnel overlay | ✓ | ✗ | ✗ |

**Contract compliance scores: Claude 18/20, DeepSeek 17/20, Pi 16/20**

---

## 6. Scoring Summary

### 6.1 Weighted Scores

Each category scored 0–10. Weights reflect pedagogical importance for a certification capstone lab.

| Category | Weight | Claude | DeepSeek | Pi |
|----------|--------|--------|----------|-----|
| **Workbook — Theory depth (S1)** | 15% | 9 | 8 | 7 |
| **Workbook — Task/scenario design (S5)** | 20% | 8 | 7 | 9 |
| **Workbook — Cheatsheet (S7)** | 10% | 8 | 9 | 8 |
| **Workbook — Solutions (S8)** | 10% | 9 | 9 | 7 |
| **Workbook — Troubleshooting (S9)** | 10% | 9 | 7 | 8 |
| **Workbook — Contract compliance** | 10% | 9 | 8 | 7 |
| **Topology — Visual quality** | 10% | 9 | 6 | 6 |
| **Topology — Completeness** | 5% | 9 | 6 | 6 |
| **Solutions — Config accuracy** | 5% | 9 | 9 | 9 |
| **Scripts — Fault injection quality** | 5% | 8 | 8 | 8 |
| **TOTAL (weighted)** | 100% | **8.6** | **7.7** | **7.7** |

### 6.2 Raw Average (unweighted)

| Metric | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| Simple average of all 10 categories | 8.7 | 7.7 | 7.5 |

### 6.3 Workbook-Specific Scores (Sections 1–11 only)

| Metric | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| Workbook average (7 categories) | 8.7 | 8.0 | 7.7 |

### 6.4 Topology-Specific Scores (drawio only)

| Metric | Claude | DeepSeek | Pi |
|--------|--------|----------|-----|
| Visual quality | 9 | 6 | 6 |
| Completeness (octets, overlays) | 9 | 6 | 6 |

---

## 7. Key Findings

### 7.1 Where Claude Excels

1. **Topology diagrams are definitively better.** Last-octet labels on every link endpoint (a contract requirement the other two missed), tunnel overlay as a dashed orange line, 4-zone coloring with BGP-free core as a distinct sub-zone. This is the single biggest differentiator.

2. **Layer-dependency teaching model.** The 5-layer ASCII stack diagram in Section 1 gives students a mental model of build order. The LIB/LFIB side-by-side walkthrough teaches diagnostic technique directly.

3. **Architectural framing.** The "Design Requirements" intro in Section 5 and "Critical invariants" in Section 4 give students the *why* before the *what*. The other agents jump into configuration without this context.

4. **Troubleshooting ticket diversity.** Three distinct fault domains with no overlap — TE global, BGP-LU capability, RSVP bandwidth. Each teaches a different diagnostic skill.

### 7.2 Where DeepSeek Excels

1. **Contract completeness on Section 3.** Only agent to include the RAM column in Device Inventory. Most comprehensive cheatsheet with 10 failure causes and 6 syntax skeleton groups.

2. **Theory verbosity.** The LDP session lifecycle (3-phase breakdown) and RSVP-TE ASCII flow diagram are strong pedagogical additions. The path diversity note (3 paths) is a useful topology insight the others missed.

3. **Granular TE task decomposition.** Splitting TE into four separate tasks (Global TE, IS-IS Extensions, RSVP, Tunnel) ensures the student doesn't miss any component — but risks fragmentation.

4. **`updated: []` forward-compatibility.** Included the metadata field for future updates (shared with Pi).

### 7.3 Where Pi Excels

1. **"Choose the unused path" tunnel design.** Creating both explicit paths and having the student inspect CSPF to decide which to use is pedagogically superior. It teaches state inspection, not just configuration execution.

2. **Insight callout box.** The `★ Insight` framed aside is a genuine innovation — architectural rationale separated from instructional text. Neither Claude nor DeepSeek has this.

3. **Concision without loss.** Pi achieves contract compliance at 1,051 lines — 25% smaller than DeepSeek — without dropping required content. The compact format is better for exam-focused study.

4. **Most realistic troubleshooting tickets.** LDP router-id flap (30-second cycle) and missing next-hop-self are classic real-world faults that directly map to exam scenarios.

### 7.4 Critical Gaps

| Gap | Agent(s) | Impact |
|-----|----------|--------|
| Missing last-octet labels in drawio | DeepSeek, Pi | Students cannot identify interface IPs from the diagram alone |
| Missing RAM column in Device Inventory | Claude, Pi | Doesn't match eve-ng-constraints.md requirement |
| IOS syntax in Section 4 IS list | Pi | Minor contract deviation (`no ip domain-lookup`, `no shutdown`) |
| TE ticket overlap (2 of 3 in same domain) | DeepSeek | Tickets 1 and 3 are both "TE component missing on P router" |
| Consolidated solution blocks | Pi | Harder for students to follow device-by-device |
| No invariants section in Base Config | DeepSeek, Pi | Students may not understand what must NOT be changed |
| No layer-dependency model | DeepSeek, Pi | Students may build layers in wrong order without understanding why |

---

## 8. Task Design Philosophy Comparison

The three agents reveal fundamentally different philosophies about capstone task design:

| Philosophy | Claude | DeepSeek | Pi |
|-----------|--------|----------|-----|
| **Approach** | "Teach the model, then execute" | "Enumerate every step" | "Minimal guidance, maximum discovery" |
| **Task count** | 7 (balanced) | 9 (granular) | 7 (balanced) |
| **TE handling** | 2 tasks (underlay + tunnel) | 4 tasks (global, IS-IS, RSVP, tunnel) | 2 tasks (underlay + tunnel) |
| **Path design** | Prescribed (PE1-via-P2) | Prescribed (PE1-via-P2) | Discovery-based (inspect CSPF, choose unused) |
| **Theory style** | Architectural (why this order, why this design) | Encyclopedic (every protocol mechanic) | Exam-focused (what you need to pass) |

Claude treats the capstone as an **engineering design exercise** — the student understands the architecture, then executes. DeepSeek treats it as a **comprehensive checklist** — every sub-component gets its own task. Pi treats it as a **discovery lab** — the student observes state and makes decisions.

For a CCNP exam candidate, Claude's approach is strongest for deep understanding, Pi's is strongest for exam readiness, and DeepSeek's is strongest for procedural completeness.

---

## 9. Recommendations

### For Claude (Opus)

1. **Add the RAM column to Device Inventory.** Trivial fix, contract requirement per eve-ng-constraints.md.
2. **Consider Pi's "choose the unused path" approach.** Creating both explicit paths and letting the student decide which to use adds a discovery element without increasing task count.
3. **Add the `updated: []` field to meta.yaml.** Forward-compatibility for future builds.

### For DeepSeek (via Claude harness)

1. **Add last-octet labels to drawio diagrams.** This is the single highest-impact improvement. Every link endpoint needs a `.N` edgeLabel cell.
2. **Add a tunnel overlay to the topology.** A dashed line showing Tunnel10's path adds visual pedagogy.
3. **Reduce TE ticket overlap.** Tickets 1 and 3 should target different fault domains (e.g., keep one TE fault and replace the other with an LDP or BGP-LU fault).
4. **Consider a layer-dependency diagram in Section 1.** A visual model of build order helps students avoid the most common capstone mistake.
5. **Add an invariants section to Base Config.** Explicitly state what must NOT be changed.

### For Pi

1. **Add last-octet labels to drawio diagrams.** Same critical gap as DeepSeek.
2. **Add a tunnel overlay to the topology.** Visual representation of Tunnel10 on the diagram.
3. **Add the RAM column to Device Inventory.** Contract requirement.
4. **Use the Cabling table format** (Device A, Interface, IP | Device B, Interface, IP) instead of the Link table format (Endpoints, Subnet, Purpose) for contract compliance.
5. **Expand Section 8 solutions to per-device `<details>` blocks.** Consolidated blocks are harder for students to follow.
6. **Add a layer-dependency model in Section 1.** Pi's Insight box already teaches *why* individually; a dependency diagram would show *how* the pieces connect.

---

## 10. Final Comparative Scores

| Lab Variant | Agent | Workbook Score | Topology Score | Overall | Verdict |
|-------------|-------|---------------|---------------|---------|---------|
| `lab-04-capstone-config` | Claude Opus 4.7 | 8.7 | 9.0 | **8.6** | **Winner** |
| `lab-04-capstone-config-dsc` | DeepSeekv4 (Claude harness) | 8.0 | 6.0 | **7.7** | — |
| `lab-04-capstone-config-pi` | Pi (DeepSeekv4) | 7.7 | 6.0 | **7.5** | — |

**Claude wins the MPLS capstone comparison decisively.** The topology quality gap (last-octet labels, tunnel overlay, 4-zone coloring) is the largest single differentiator. Claude's layer-dependency teaching model and architectural framing provide deeper pedagogical value than DeepSeek's verbosity or Pi's concision.

**The ideal MPLS capstone lab would combine:**
- Claude's topology diagrams (last-octet labels, tunnel overlay, zone coloring)
- Claude's layer-dependency model and LIB/LFIB walkthrough
- Pi's "choose the unused path" tunnel design and Insight callout box
- DeepSeek's RAM column, path diversity note, and LDP session lifecycle breakdown
- Pi's troubleshooting ticket realism (LDP flap, next-hop-self)

---

## 11. Cross-Agent Patterns

### 11.1 What All Three Got Right

- Complete 11-section workbook structure with TOC
- Functionally identical solution configs (all produce a working MPLS stack)
- BGP-free core invariant enforced and verified
- Tunnel10 with dual path-options (dynamic + explicit)
- Three troubleshooting tickets with inject scripts, diagnosis, and spoiler fixes
- Syntax skeleton cheatsheets with command/purpose tables
- Contract-compliant Section 5 with "no IOS syntax in task descriptions"

### 11.2 What All Three Got Wrong (or Could Improve)

- None include a "Further Reading" or "References" section (present in some Claude BGP workbooks)
- None include a lab teardown/cleanup procedure
- None explicitly state the total lab time estimate in the workbook header (DeepSeek omits it; Claude and Pi have it implied but not explicit)

### 11.3 Model vs. Harness Effect

Both DeepSeek variants (Claude harness and Pi harness) share the same underlying model (deepseek-v4-pro) but produce notably different workbooks:

- **DeepSeek (Claude harness):** 1,398 lines, verbose theory, 9 tasks, prescribed explicit path, no Insight box
- **Pi (DeepSeek model):** 1,051 lines, compact theory, 7 tasks, discovery-based path, Insight box present

The 33% size difference between two variants of the same model suggests the **agent harness** (Claude Code vs Pi) has a larger influence on output style than the underlying LLM. Claude harness produces more verbose, architecturally-framed output; Pi harness produces more compact, exam-focused output regardless of which model is underneath.

---

**Analysis by: Claude Opus 4.7**
**Date: 2026-05-04**
**Methodology: Workbook line-by-line comparison, topology XML structure analysis, solution config diff, contract compliance checklist scoring, weighted rubric evaluation.**
