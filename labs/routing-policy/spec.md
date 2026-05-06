# Routing Policy and Manipulation — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **3.1** Compare routing policy language and route maps
  - **3.2** Describe conditional matching
    - **3.2.a** Operations
    - **3.2.b** Semantics of policy applications and statements
    - **3.2.c** Regular expressions
    - **3.2.d** Policy sets
    - **3.2.e** Tags
    - **3.2.f** ACLs
    - **3.2.g** Prefix lists and prefix sets
    - **3.2.h** Route types
    - **3.2.i** BGP attributes and communities
    - **3.2.j** Hierarchical and parameterized structures
  - **3.3** Troubleshoot route manipulation for IGPs
    - **3.3.a** IS-IS
    - **3.3.b** OSPF
  - **3.4** Troubleshoot route manipulation for BGP
    - **3.4.a** Route filtering
    - **3.4.b** Traffic steering

> This topic depends on `ospf`, `isis`, and `bgp` for protocol fundamentals.
> Students should have working knowledge of all three before starting these labs.

## Topology Summary

Four-router IOSv core running OSPF area 0, IS-IS L2, and BGP (AS 65100 internal,
AS 65200 external via R4). Two optional IOS-XRv 9000 routers (XR1, XR2) join
from lab-02 onward to carry the Routing Policy Language (RPL) comparison and
the hierarchical/parameterized policy work that RPL is designed for.

```
                       AS 65100 (SP core)
            ┌────┐                      ┌────┐
            │ R1 ├──────── L1 ──────────┤ R2 │
            └─┬──┘                      └──┬─┘
              │                            │
              L5                           L2
              │                            │
            ┌─┴──┐                      ┌──┴─┐
            │ R3 ├──────── L3 ──────────┤ R4 │  AS 65200 (external)
            └─┬──┘                      └────┘
              │                            │
              └────────── L4 ──────────────┘

  [Optional, from lab-02 — XRv9k, AS 65100]
            ┌────┐                      ┌────┐
            │XR1 ├──────── L8 ──────────┤XR2 │
            └─┬──┘                      └──┬─┘
              │                            │
              L6 ── R2:Gi0/2       R3:Gi0/3 ── L7
```

**Key relationships**

- R1, R2, R3 run OSPF area 0, IS-IS L2, and iBGP (AS 65100) in parallel from
  lab-00. Running both IGPs simultaneously is deliberate — 3.3 requires
  troubleshooting route manipulation on IS-IS and OSPF independently, and
  keeping both live avoids tearing down and rebuilding adjacencies between
  labs.
- R4 is in AS 65200 with eBGP sessions to R1 (L5 replaces R1↔R3 in later
  labs — see note below) and R3. This gives every BGP filtering/steering
  scenario a real inter-AS boundary instead of faking one with route-maps
  on iBGP.
- XR1 and XR2 join the SP core from lab-02 via IS-IS L2 and iBGP to R2/R3.
  They carry RPL examples and the hierarchical/parameterized policy work.
  Kept dark through labs 00-01 so foundation labs stay at ~2 GB RAM.
- **L5 clarification:** L5 is the R1↔R3 diagonal, not R1↔R4. R1↔R4 is L4
  (see baseline.yaml). The ASCII art above shows the physical topology;
  the OSPF/IS-IS/iBGP mesh uses L1, L2, L5.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-route-maps-foundations | Route-Maps, Prefix-Lists, and ACL Matching | Foundation | 60m | progressive | 3.2, 3.2.a, 3.2.b, 3.2.f, 3.2.g | R1, R2, R3, R4 |
| 01 | lab-01-tags-regex-communities | Tags, Route Types, Regex, and BGP Communities | Foundation | 75m | progressive | 3.2.c, 3.2.e, 3.2.h, 3.2.i | R1, R2, R3, R4 |
| 02 | lab-02-rpl-vs-route-maps | RPL vs Route-Maps — Policy Sets and Hierarchy | Intermediate | 90m | progressive | 3.1, 3.2.d, 3.2.j | R1, R2, R3, R4, XR1, XR2 |
| 03 | lab-03-igp-route-manipulation | Route Manipulation for IS-IS and OSPF | Intermediate | 90m | progressive | 3.3, 3.3.a, 3.3.b | R1, R2, R3, R4, XR1, XR2 |
| 04 | lab-04-bgp-filtering-steering | BGP Route Filtering and Traffic Steering | Intermediate | 90m | progressive | 3.4, 3.4.a, 3.4.b | R1, R2, R3, R4, XR1, XR2 |
| 05 | lab-05-capstone-config | Routing Policy Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 06 | lab-06-capstone-troubleshooting | Routing Policy Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|--------|-------------|------------|---------------|
| 3.1 | Compare routing policy language and route maps | lab-02 (primary), lab-05, lab-06 | yes — primary |
| 3.2 | Describe conditional matching | lab-00, lab-01, lab-02 (umbrella across foundation labs) | yes — primary (lab-02+) |
| 3.2.a | Operations (match/set, permit/deny, sequencing) | lab-00 | no — IOSv foundation |
| 3.2.b | Semantics of policy applications and statements | lab-00 | no — IOSv foundation |
| 3.2.c | Regular expressions (AS-path regex, community regex) | lab-01 | no — IOSv foundation |
| 3.2.d | Policy sets (prefix-set, community-set, as-path-set) | lab-02 | yes — primary (RPL-only feature) |
| 3.2.e | Tags (route-tag for redistribution control) | lab-01 | no — IOSv foundation |
| 3.2.f | ACLs (standard, extended, named) | lab-00 | no — IOSv foundation |
| 3.2.g | Prefix lists and prefix sets | lab-00 (lists), lab-02 (sets) | yes — primary (sets on XR) |
| 3.2.h | Route types (internal/external/E1/E2, L1/L2) | lab-01 | no — IOSv foundation |
| 3.2.i | BGP attributes and communities | lab-01 | no — IOSv foundation |
| 3.2.j | Hierarchical and parameterized structures | lab-02 | yes — primary (RPL-only feature) |
| 3.3 | Troubleshoot route manipulation for IGPs | lab-03 (primary), lab-06 | yes — primary |
| 3.3.a | IS-IS route manipulation (L1/L2 leaking, filter/redistribute) | lab-03 | yes — primary |
| 3.3.b | OSPF route manipulation (distribute-list, filter-list, prefix suppression) | lab-03 | yes — primary |
| 3.4 | Troubleshoot route manipulation for BGP | lab-04 (primary), lab-06 | yes — primary |
| 3.4.a | Route filtering (prefix-list, as-path, community, RPL) | lab-04 | yes — primary |
| 3.4.b | Traffic steering (LOCAL_PREF, MED, AS-path prepend, conditional advertisement) | lab-04 | yes — primary |

Every blueprint bullet is covered by at least one dedicated lab. Capstones
exercise every bullet again, end-to-end.

## Design Decisions

- **XR Coverage Posture: `XR-mixed`** (per `memory/xr-coverage-policy.md`).
  This topic was XR-mixed from inception — XR1 and XR2 join the SP core
  from lab-02 onward to carry the RPL-vs-route-maps comparison (§3.1) and
  the RPL-native abstractions (policy sets §3.2.d, hierarchical /
  parameterized structures §3.2.j). No Phase 3 capstone retrofit is needed
  because XR is already integral to lab-02 through the capstones.
  *Platform note:* the existing baseline uses XRv 9000 for XR1/XR2; per the
  policy doc's platform-selection rule, plain IOS XRv would now be
  preferred (RPL works on XRv and the heavier image is unnecessary here).
  A future cleanup task may downgrade XRv 9000 → IOS XRv; not in scope for
  the 2026-05-06 retrofit.

- **Mixed IOSv + XRv9k platform.** Bullet 3.1 explicitly requires comparing
  Routing Policy Language (IOS-XR only) with route-maps (IOS/IOS-XE). Going
  IOSv-only would gut the signature SPRI objective; going XR-only would
  demand ~24 GB RAM for a 6-router topology with 10-minute boot times.
  Splitting the difference — IOSv core with 2 XRv9k introduced at lab-02 —
  keeps early labs lightweight (~2 GB) and reserves the XR boot penalty for
  labs where RPL is actually the subject.
- **Both IGPs run simultaneously on the IOSv core.** 3.3.a and 3.3.b require
  troubleshooting IS-IS and OSPF route manipulation. Running them in
  parallel (not serial across labs) means lab-03 can exercise both without
  reconverging the control plane mid-lab, and the capstones can plant
  faults across both IGPs concurrently.
- **Dedicated AS 65200 edge router (R4).** Every BGP filtering/steering
  scenario needs a real inter-AS peering. R4 in AS 65200 with dual eBGP
  sessions (to R1 and R3) models a small multi-homed edge — enough to
  demonstrate LOCAL_PREF, MED, AS-path prepend, outbound filtering, and
  conditional advertisement without a second transit AS.
- **Lab ordering by feature class, not by bullet order.** Bullets 3.2.a
  through 3.2.j are reordered so route-maps foundations (ACLs, prefix-lists,
  basic match/set) come first (lab-00), then the matching depth-first items
  (tags, regex, communities, route types — lab-01), then the RPL-native
  abstractions (policy-sets, hierarchical/parameterized — lab-02). This
  avoids teaching policy-sets before the student has seen a prefix-list.
- **XR routers carried through labs 03–04 even though the protocol work is
  primarily IOS.** Once XR1/XR2 join in lab-02, they participate in IS-IS
  and iBGP for the remaining labs — this lets 03 and 04 demonstrate the
  same manipulation on both RPL and route-maps where relevant (e.g., RPL
  `apply` vs IOS `redistribute route-map`).
- **Capstones use the full 6-device topology.** Both capstones load with
  all interfaces configured but no protocols running (clean_slate: true).
  Capstone I builds the entire policy framework — IGP filtering, BGP
  filtering, traffic steering, RPL hierarchy — from scratch. Capstone II
  plants 5+ concurrent faults spanning route-maps, RPL, IGP filtering,
  BGP attribute manipulation, and redistribution tagging.
