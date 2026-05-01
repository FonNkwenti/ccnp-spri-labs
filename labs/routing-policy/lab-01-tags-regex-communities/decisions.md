# Lab 01 — Decisions and Build Provenance

## Model gate — 2026-04-28

- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Lab type and structure

Progressive, extending lab-00. `initial-configs/` = verbatim copy of lab-00 `solutions/`. Students start with OSPF/IS-IS/BGP fully converged and FILTER_R4_IN applied; all lab-01 objectives are additions.

R4 solution is unchanged from lab-00 — all new policy lives on the AS 65100 side.

## Redistribution design — asymmetric roles

R2 and R3 both redistribute bidirectionally, but with different roles:

- **R2**: pure tagger — `set tag 100` (OSPF→IS-IS) and `set tag 200` (IS-IS→OSPF) with no deny sequences. This lets students verify tagging works correctly in isolation before adding the loop-prevention logic.
- **R3**: tagger + filter — same tag assignments PLUS deny sequences at the top of each route-map. The deny on R3 breaks the redistribution loop: routes that came from IS-IS (tagged 200) are denied when going back into IS-IS via R3's OSPF→IS-IS map; routes that came from OSPF (tagged 100) are denied when going back into OSPF via R3's IS-IS→OSPF map.

The asymmetric design makes troubleshooting systematic: if tags are missing, the problem is on R2; if loops form, the problem is on R3's deny sequences.

## Route-type coverage — three sequences required

The baseline objective explicitly calls out `match route-type external type-1`. A common student mistake is writing only `external type-2` (the IOS default when redistributing into OSPF). Lab-01 forces all three sequences (type-1, type-2, internal) so students see that each is a separate match clause — not a single wildcard.

Both R2 and R3 carry all three sequences in their OSPF_TO_ISIS maps. The IS-IS→OSPF direction does not need route-type matching because IS-IS has no internal/external distinction — all redistributed IS-IS routes enter OSPF as E2 by default.

## AS-path regex topology limitation

In this 4-router topology, `_65200$` and `_65200_` produce identical results: R4 is a leaf AS so 65200 is always the last AS-hop, and `_` matches end-of-string. The distinction only matters in production when AS 65200 appears as a transit AS in a longer path.

Resolution: the workbook documents this limitation explicitly in the Verification & Analysis section and in Ticket 3. Ticket 3's inject fault (`_65200_` instead of `_65200$`) is intended as a mechanical/syntax teaching moment, not a behavioral difference demonstration. The `show ip bgp regexp` commands in the ticket guide students to test both patterns and articulate why `_65200$` is the production-correct form.

## Community propagation — `send-community both` scoping

`send-community both` applies to the IBGP peer group (not individual neighbors). This is the correct SP practice: adding it per-neighbor is error-prone when the peer group grows. The lab requires students to add it to the peer group before setting any communities, so the verification step for community propagation naturally catches any student who applied it to the wrong scope.

## Fault-injection design

Three injects, all reversible by `apply_solution.py`:

| # | Fault | Target | Class | Observable symptom |
|---|-------|--------|-------|-------------------|
| 1 | `set community 65100:200` in R1's FILTER_R4_IN permit 20 | R1 | Wrong value | R2 sees 65100:200 for routes that should carry 65100:100 |
| 2 | `redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF` removed from R2's OSPF | R2 | Missing config | IS-IS routes disappear from OSPF table on R1 |
| 3 | `ip as-path access-list 1 permit _65200_` (trailing `_` instead of `$`) | R3 | Regex error | Behaviorally equivalent in this topology; teaches production distinction |

Faults are single-router, single-command changes to minimize blast radius and make symptoms unambiguous.

## Community-lists defined but not applied

`COMM_65100_100`, `COMM_65100_1XX`, and `COMM_65100_2XX` are defined on all three SP routers but not wired into any active route-map. They are verification objects for this lab and policy hooks for lab-02, which will use `match community COMM_65100_2XX` to steer traffic. Applying them prematurely here would add state churn that lab-02 should introduce in a controlled way.

## DEMO_WELL_KNOWN route-map

Carried in R1's solution config as a defined-but-not-applied map. The workbook Task 7 asks students to temporarily apply it and observe `no-export` behavior on R2. It is not part of the fault-injection matrix — temporary application and removal is entirely student-driven.
