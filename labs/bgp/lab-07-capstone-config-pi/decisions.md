# Build Decisions — BGP Lab 07 Capstone I (Pi Build)

## Model gate — 2026-05-01
- Difficulty: Advanced
- Running model: pi (coding agent harness)
- Allowed models: claude-opus-4-7
- Outcome: MANUAL OVERRIDE — Building as Pi agent per user request for comparison purposes.

## Workbook gate — 2026-05-01
- Outcome: PASS-CLEAN
- Items fixed: none
- Notes: All 11 sections comply with lab-assembler contract on first write.

## Compatibility notes — 2026-05-01
- Mixed platform lab: R1–R4, R6 are IOSv (ios-classic); R5, R7 are CSR1000v (ios-xe).
  CSR1000v is required for BGP FlowSpec SAFI 133 support — IOSv rejects
  `address-family ipv4 flowspec`.
- OSPF, BGP, route-map, prefix-list, community, and security commands are all `pass`
  on ios-classic. FlowSpec commands are `pass` on ios-xe.
- CSR1000v uses GigabitEthernet<N> (not GigabitEthernet<N>/<M>) interface naming.
  R5: Gi2, Gi3, Gi4; R7: Gi1. IOSv uses Gi0/N. Verified against lab-05 solutions.
- `no ip domain lookup` used instead of `no ip domain-lookup` in lab-05 solutions
  — both forms are accepted by IOS; the dash form is canonical per initial-configs
  from lab-00. Solutions use `no ip domain-lookup` for consistency.

## Design decisions — 2026-05-01
- **Capstone I (clean_slate: true).** Initial configs are IP-only. No OSPF, no BGP
  pre-loaded — student builds the full production topology from scratch.
- **No legacy R2↔R5 iBGP.** Unlike lab-01 which preserves the lab-00 direct session
  for additive continuity, the capstone starts clean. Only RR-based iBGP is present.
- **R4 as sole Route Reflector** with cluster-id 10.0.0.4. Three clients: R2, R3, R5.
- **R5 and R7 as CSR1000v** for BGP FlowSpec. The rest are IOSv for resource
  efficiency (~10.5 GB total RAM, within Dell Latitude 5540 envelope).
- **Dynamic-neighbor interface** (10.99.0.0/30) between R1 Gi0/2 and R2 Gi0/3
  included in initial-configs and solutions — added to baseline spec by lab-04.
- **Three troubleshooting tickets** mapped to 1.5.b (missing RR client), 1.5.d
  (missing route-map / LOCAL_PREF), and 1.5.i (missing send-community).
- **Fault injection scripts use find_open_lab()** for auto-discovery. Two of three
  tickets use non-matching UUID fault markers due to "absence" fault patterns.
