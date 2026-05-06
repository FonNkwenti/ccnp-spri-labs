# BGP Dual-CE Multihoming — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - 1.5.d: Multihoming
  - 1.5.a: Route advertisement

## Supplemental Topic Note

This topic is a targeted extension of the `bgp` topic (labs 00–08). All nine `bgp` labs
model a **single CE** with two uplinks to the **same SP** (AS 65100). That is a different
architectural pattern from a customer who deploys **two CE routers in the same AS**, each
connecting to a **different upstream ISP**. The dual-CE model introduces distinct requirements:

- CE-to-CE iBGP is mandatory — without it each CE has a partial routing view
- Transit prevention is a policy obligation, not just good practice — the customer AS sits
  between two providers and becomes a free transit path without explicit filtering
- MED is useless for cross-provider inbound TE — AS-path prepend is the only lever
- Selective prefix advertisement (splitting the /24 into /25s toward different ISPs) is a
  load-distribution technique not possible with a single CE

Blueprint bullet 1.5.d ("Multihoming") covers both patterns. This series drills the
dual-CE, dual-provider variant exclusively.

## Topology Summary

Four core routers span two customer CEs and two ISP PEs. **R1** (CE1, AS 65001) and
**R2** (CE2, AS 65001) are in the same customer AS and run iBGP between themselves across
link L3. R1 peers eBGP with **R3** (ISP-A PE, AS 65100); R2 peers eBGP with **R4**
(ISP-B PE, AS 65200). Two optional routers — **R5** (ISP-A internal peer) and **R6**
(ISP-B internal peer) — are activated from lab-02 to provide additional ISP prefixes for
inbound TE verification and selective advertisement scenarios.

Customer prefix: `192.168.1.0/24` (PI space advertised from both CEs).
ISP-A representative prefix: `10.100.1.0/24` (Lo1 on R3).
ISP-B representative prefix: `10.200.1.0/24` (Lo1 on R4).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-dual-ce-ibgp-baseline | Dual-CE iBGP Architecture and Baseline | Foundation | 60m | progressive | 1.5.d | R1, R2, R3, R4 |
| 01 | lab-01-transit-prevention | Transit Prevention Policy | Intermediate | 75m | progressive | 1.5.d | R1, R2, R3, R4 |
| 02 | lab-02-inbound-traffic-engineering | Inbound Traffic Engineering Across Two ISPs | Intermediate | 75m | progressive | 1.5.d | R1, R2, R3, R4, R5, R6 |
| 03 | lab-03-selective-advertisement | Outbound Policy and Selective Prefix Advertisement | Intermediate | 90m | progressive | 1.5.d, 1.5.a | R1, R2, R3, R4, R5, R6 |
| 04 | lab-04-capstone-config | BGP Dual-CE Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, R5, R6 |
| 05 | lab-05-capstone-troubleshooting | BGP Dual-CE Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, R5, R6 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In | XR Exercised? |
|-----------------|-------------|------------|---------------|
| 1.5.d | Multihoming | lab-00, lab-01, lab-02, lab-03, lab-04, lab-05 | yes — capstone |
| 1.5.a | Route advertisement | lab-03, lab-04, lab-05 | yes — capstone |

## Design Decisions

- **XR Coverage Posture: `XR-mixed`** (per `memory/xr-coverage-policy.md`).
  Foundation/intermediate labs run on IOSv as today; the capstones (lab-04,
  lab-05) flip the **CE pair** (R1 and R2) to IOS XRv via Phase 3 #6 of the
  [`2026-05-06 XR Coverage Retrofit`](../../tasks/2026-05-06-xr-coverage-retrofit.md).
  Driven by §1.5.d and §1.5.a — XR-side dual-CE iBGP, AS-path prepend for
  inbound TE, and selective prefix advertisement use the `router bgp`
  neighbor-group / address-family hierarchy and RPL `as-path-set` matching
  rather than IOS route-maps. CCIE SP candidates routinely encounter
  XR-on-CE in real SP-MPLS handoffs, which makes this retrofit
  high-value despite the topic's CE-only focus. Capstone peak ≈ 9 GB
  (4×IOSv + 2×XRv); see RAM table in `memory/xr-coverage-policy.md` §5.

- **Two distinct provider ASes (65100 and 65200) instead of two PEs in the same SP:** The
  existing `bgp` series already covers single-SP dual-PE. Using separate ISP ASes forces
  all multi-provider-specific behaviors to surface: MED irrelevance across ASes, AS-path
  prepend as the only inbound TE mechanism, and the transit problem that arises when two
  unrelated providers peer with the same customer AS.

- **CE-to-CE iBGP link present from lab-00:** Link L3 is IP-addressed and the iBGP session
  is established in lab-00 and retained throughout the progressive chain. This is the
  structural prerequisite for all subsequent labs — without it the transit prevention and
  inbound TE scenarios are incoherent.

- **Optional R5/R6 introduced at lab-02:** Labs 00 and 01 only need 4 routers — the transit
  problem and CE-CE iBGP requirement are fully demonstrable with a minimal 4-node topology.
  R5 and R6 (simulating the broader ISP networks) are activated from lab-02 to provide
  more realistic prefix diversity for inbound TE and selective advertisement verification.

- **Customer prefix 192.168.1.0/24 (PI space):** Deliberately different from the `bgp`
  topic's 172.16.1.0/24 to avoid confusion if a student runs both topic sets simultaneously.
  The /24 is split into two /25s in lab-03 for selective advertisement.

- **No inter-domain security (GTSM/MD5) in this series:** Those features are fully covered
  in `bgp/lab-03-interdomain-security`. Repeating them here would duplicate existing content
  without adding dual-CE-specific pedagogical value.

- **Lab-03 scope is LOCAL_PREF + selective advertisement only:** Backup-only ISP
  (default-route-only acceptance) was assessed as low priority relative to the four high/
  medium scenarios and would push the lab past 90 minutes. It can be added as a task
  extension if time permits during a study session.

- **Capstone II faults are dual-CE-specific:** Five faults are planted, all distinct to the
  dual-CE architecture. Inter-domain security faults (covered in `bgp/lab-03`) are excluded
  to keep the fault set focused on patterns unique to this topic.
