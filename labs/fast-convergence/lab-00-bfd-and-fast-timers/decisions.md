## Model gate — 2026-05-05
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Workbook gate — 2026-05-05
- Outcome: PASS-AFTER-FIXES
- Items fixed: 1
- Notes: Task 9 body contained a show command reference and raw IOS syntax (`bfd interval 150 min_rx 150 multiplier 3`); rewritten to plain-language description per Section 5 contract

## Advisor review — 2026-05-05
- Outcome: FIXES APPLIED
- Items fixed: 4
- Notes:
  1. solutions/R1.cfg — `next-hop-self` moved from eBGP neighbor (10.0.0.5) to iBGP neighbors (10.0.0.2, 10.0.0.3, 10.0.0.4); applying it to the eBGP peer rewrites the next-hop in updates sent TO R5 (no effect) rather than inward to iBGP peers
  2. solutions/R3.cfg — same fix: `next-hop-self` moved from 10.0.0.5 to iBGP neighbors (10.0.0.1, 10.0.0.2, 10.0.0.4)
  3. workbook.md Task 2 body — rewritten to clarify that `next-hop-self` applies on iBGP neighbors, not the eBGP peer
  4. workbook.md Section 8 Task 2 R1 solution + Section 7 cheatsheet — updated `address-family ipv4` blocks to show `next-hop-self` on iBGP neighbors (10.0.0.2/3/4), not on 10.0.0.5

## Platform refactor — 2026-05-12
- Change: All devices switched from iosv to csr1000v (IOS-XE)
- Interface naming: Gi0/X → GigabitEthernet1/2/3/4 per CSR1000v convention
- Files updated: solutions/*.cfg, initial-configs/*.cfg, workbook.md (all sections),
  fault-injection scripts, topology/README.md, meta.yaml, README.md
- Topology, IP addressing, lab sequence unchanged
- Model gate: PASS (Foundation, claude-sonnet-4-6)

## Post-build review — 2026-05-09
- Outcome: FIXES APPLIED
- Items fixed: 4
- Notes:
  1. workbook.md Tasks 3/4/6 body + Section 6 Task 3/4 prose — convergence test source changed from R5→R2 loopback to R2→R3 loopback; R5 has no route to 10.0.0.2 and shutting L2 does not disrupt any R5→R2 path; alternate path corrected to R2→R1→R3 (L1+L5) or R2→R1→R4→R3 (L1+L4+L3)
  2. inject_scenario_01.py — extended to also fault R1 Gi0/0 (bfd interval 500 min_rx 500 multiplier 3) to match the spec-described asymmetric fault; script now connects to both R1 and R2; apply_solution.py already restored R1 (already in RESTORE_TARGETS)
  3. workbook.md Section 9 Ticket 1 Fix — updated to instruct student to correct both R1 and R2 to 150/150/3; previous version only mentioned R2
  4. workbook.md Section 6 Task 3/4 — R2 IS-IS neighbor table: R3 was shown on Gi0/0 but L2 is R2 Gi0/1; corrected to Gi0/1; also fixed "30-second multiplier" phrasing to "multiplier 3 — hold time = 30 seconds" in Task 3 Verification
