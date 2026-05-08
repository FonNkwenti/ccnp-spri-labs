# Lab Build Decisions — mpls/lab-04-capstone-config

## Model gate — 2026-05-01

- Difficulty: Advanced
- Running model: claude-opus-4-7
- Allowed models: claude-opus-4-7
- Outcome: PASS

## Workbook gate — 2026-05-01

- Outcome: PASS-AFTER-FIXES
- Items fixed: 3
- Notes:
  - Section 4 "IS pre-loaded" listed `no ip domain-lookup` in backticks — rewrote to "DNS lookup disabled" (no raw IOS in non-code prose).
  - Section 4 "IS NOT pre-loaded" enumerated config tokens in backticks (`send-label`, `next-hop-self`, `router bgp`, `PE1-via-P2`) — rewrote as plain-English requirements (e.g. "iBGP between PE1 and PE2 (loopback-sourced) with BGP labeled-unicast").
  - Section 5 task bodies (Tasks 1–7) contained raw IOS syntax in backticks — rewrote all seven as concept-level requirements describing WHAT to configure, not HOW. Verification footers retained verbatim (show commands are explicitly permitted by the contract).
  - Re-validated the rewritten workbook against the full Step 3b checklist; no remaining FAILs.

## Capstone tunnel design — 2026-05-01

- Single Tunnel10 on PE1 destined for PE2 (10.0.0.4) with two path-options:
  - `path-option 10 dynamic` — primary; CSPF picks PE1→P1→PE2 via lower-router-id tie-break.
  - `path-option 20 explicit name PE1-via-P2` — secondary; loose-hop list (10.0.0.3, 10.0.0.4) forces transit via P2 (PE1→P2→PE2).
- Lab-03's separate Tunnel20 (PE1-via-P2 explicit) was consolidated into Tunnel10 path-option 20 to demonstrate the more pragmatic single-tunnel-with-failover pattern that the spec describes.
- Bandwidth chosen at 10 Mbps requested with 100 Mbps reservable per link — leaves headroom and matches lab-03 RSVP pool sizing.

## BGP-free core enforcement — 2026-05-01

- P1 and P2 solutions contain zero `router bgp` configuration.
- Workbook Section 5 Task 3 explicitly calls this out as an invariant; Section 6 Task 7 verifies via `show ip bgp summary` returning `% BGP not active` and customer prefixes absent from P routers' RIBs.
- Fault-injection ticket 1 deliberately tests TE behaviour on a P router (the right test for a BGP-free P) rather than fabricating a BGP fault on a P that should not have BGP.

## Build completed — 2026-05-01

- All nine lab-assembler steps complete: workbook, contract gate, initial-configs, solutions, topology.drawio (drawio subagent), topology/README.md, setup_lab.py, lab README, fault-injection scripts (fault-injector subagent), meta.yaml.
- Skills submodule HEAD: `f840ce03` (workbook contract gate Step 3b).
- Status updated to "Review Needed" in `memory/progress.md` (mpls topic, lab-04 row).
- Next lab in topic: `lab-05-capstone-troubleshooting` (capstone II — troubleshooting-only).
