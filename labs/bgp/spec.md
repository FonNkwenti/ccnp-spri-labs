# BGP Scalability and Troubleshooting — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **1.4** Describe the BGP scalability and performance
    - **1.4.a** BGP confederations
    - **1.4.b** Route reflectors
  - **1.5** Troubleshoot BGP
    - **1.5.a** Route advertisement
    - **1.5.b** Route reflectors
    - **1.5.c** Confederations
    - **1.5.d** Multihoming
    - **1.5.e** TTL security and inter-domain security
    - **1.5.f** Maximum prefix
    - **1.5.g** Route dampening
    - **1.5.h** Dynamic neighbors
    - **1.5.i** Communities
    - **1.5.j** FlowSpec

> BGP PIC and additional/backup paths (1.7.e, 1.7.g) live under the
> `fast-convergence` topic to keep this one focused on scalability and
> troubleshooting rather than convergence tuning.

## Topology Summary

Six-router three-AS provider topology with one optional external peer. AS 65100
is the service-provider core running an internal OSPF IGP; R2, R3 are East PEs
and R5 is the West PE. R4 is the P / Route Reflector. Customer A (AS 65001) is
dual-homed via R2 and R3; external SP peer AS 65002 terminates on R5 via R6.

```
  AS 65001                  AS 65100 (SP core, OSPF area 0)              AS 65002
                           ╔══════════════════════════════════╗
   ┌────┐    ┌────┐        ║  ┌────┐          ┌────┐  ┌────┐  ║    ┌────┐
   │ R1 ├─L1─┤ R2 │════════╬══┤ R4 │══════════┤ R5 │══╬══L7══┤ R6 │
   └────┘    └────┘        ║  └────┘          └────┘  ║    └────┘
       │    (PE East-1)    ║  (P / RR)       (PE West)║
       │                   ║    iBGP / OSPF core      ║
       │    ┌────┐         ║                          ║
       └─L2─┤ R3 │═════════╝                          ║
            └────┘                                    ║
           (PE East-2)                                ║
                                                      ║
     [Optional — introduced in lab-05]                ║
                  ┌────┐                              ║
                  │ R7 │══L8═══════════════════════════  (eBGP AS 65100↔65003)
                  └────┘
                 (flowspec / multihop external peer)
```

**Key relationships**

- R1 is dual-homed to R2 (L1) and R3 (L2). Both eBGP sessions are configured
  from lab-00, but lab-02 is where traffic engineering via LOCAL_PREF / MED /
  AS-path prepending makes the two paths diverge.
- R2, R3, R4, R5 all participate in an internal OSPF area 0. iBGP peers on
  loopback0 addresses.
- R4 becomes the Route Reflector in lab-01. R2, R3, R5 become RR clients.
  The direct R2↔R5 iBGP session from lab-00 persists (additive continuity)
  but becomes redundant; a design note discusses production cleanup.
- R5 is a **CSR1000v (IOS-XE)** rather than IOSv. IOS-XE is needed for BGP
  FlowSpec NLRI support in lab-05 and matches real-world SP PEs.
- R7 is optional, activated in lab-05 as a second external peer running
  IOS-XE. It originates flowspec rules and demonstrates eBGP multihop and
  community-tagged prefix exchange.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-ebgp-ibgp-foundations | eBGP and iBGP Foundations | Foundation | 60m | progressive | 1.4, 1.5, 1.5.a | R1, R2, R3, R4, R5, R6 |
| 01 | lab-01-route-reflectors | iBGP Route Reflectors and Cluster IDs | Intermediate | 75m | progressive | 1.4.b, 1.5.b | R1, R2, R3, R4, R5, R6 |
| 02 | lab-02-ebgp-multihoming | eBGP Multihoming and Traffic Engineering | Intermediate | 90m | progressive | 1.5.d | R1, R2, R3, R4, R5, R6 |
| 03 | lab-03-interdomain-security | Inter-Domain Security and Maximum-Prefix | Intermediate | 75m | progressive | 1.5.e, 1.5.f | R1, R2, R3, R4, R5, R6 |
| 04 | lab-04-dampening-dynamic | Route Dampening and Dynamic Neighbors | Intermediate | 75m | progressive | 1.5.g, 1.5.h | R1, R2, R3, R4, R5, R6 |
| 05 | lab-05-communities-flowspec | BGP Communities and FlowSpec | Advanced | 90m | progressive | 1.5.i, 1.5.j | R1, R2, R3, R4, R5, R6, R7 |
| 06 | lab-06-confederations | BGP Confederations | Advanced | 90m | standalone | 1.4.a, 1.5.c | R1, R2, R3, R4, R5, R6 |
| 07 | lab-07-capstone-config | BGP Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, R5, R6, R7 |
| 08 | lab-08-capstone-troubleshooting | BGP Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, R5, R6, R7 |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In |
|--------|-------------|------------|
| 1.4 | Describe BGP scalability and performance | lab-00 (full-mesh scaling problem stated), lab-01 (RR solution), lab-06 (confederation solution), lab-07 |
| 1.4.a | BGP confederations | lab-06 (standalone), lab-07 |
| 1.4.b | Route reflectors | lab-01, lab-07, lab-08 |
| 1.5 | Troubleshoot BGP | every lab (focus varies); lab-08 concentrates 5+ concurrent faults |
| 1.5.a | Route advertisement | lab-00, lab-01, lab-02, lab-08 |
| 1.5.b | Route reflectors | lab-01, lab-08 |
| 1.5.c | Confederations | lab-06, lab-08 |
| 1.5.d | Multihoming | lab-02, lab-07, lab-08 |
| 1.5.e | TTL security and inter-domain security | lab-03, lab-07, lab-08 |
| 1.5.f | Maximum prefix | lab-03, lab-07, lab-08 |
| 1.5.g | Route dampening | lab-04, lab-07, lab-08 |
| 1.5.h | Dynamic neighbors | lab-04, lab-07, lab-08 |
| 1.5.i | Communities | lab-05, lab-07, lab-08 |
| 1.5.j | FlowSpec | lab-05, lab-07 (via R5/R7 CSR1000v nodes) |

## Design Decisions

- **Mixed platform: IOSv + CSR1000v.** R1–R4, R6 are IOSv (IOS 15.9) for
  resource efficiency. R5 (and optional R7) are CSR1000v (IOS-XE) because
  IOSv does not implement the BGP FlowSpec NLRI (SAFI 133); IOS-XE does.
  This mirrors a real upgrade path where SP West PE is refreshed to XE while
  East PEs still run classic IOS.
- **Single confederation lab, tagged `standalone`.** Converting AS 65100 from
  a plain-RR design to a confederation requires re-numbering AS-IDs on every
  SP router — fundamentally a rebuild, not an additive step. Per the
  continuity rules, that work is isolated in lab-06 with a clean-slate
  starting point, slotted just before the capstones.
- **Route-Reflector in lab-01 keeps the legacy R2↔R5 iBGP session.** To honor
  the "only add, never remove" progressive rule, the direct R2↔R5 iBGP peer
  configured in lab-00 persists after R4 becomes the RR. Design notes in the
  workbook will call this out as "legacy / production would remove this after
  RR stabilizes" and the capstone configs start from a clean slate so the
  final design is clean.
- **Single external AS (65002) for most labs; optional AS 65003 for flowspec.**
  Minimizing external-AS count keeps lab-02 through lab-04 focused on intra-AS
  mechanisms. Flowspec needs a second IOS-XE peer to show BGP NLRI exchange
  convincingly, which justifies activating R7 in lab-05.
- **IPv4 only, unicast AFI.** BGP IPv6 / multiprotocol extensions are covered
  by the `ipv6-transition` topic (6PE in 1.6.c) and the `multicast` topic
  (MBGP in 2.2.b). Keeping this topic IPv4-unicast keeps lab time on the
  blueprint bullets that actually belong here.
- **IGP: OSPF area 0.** Any IGP would work for iBGP next-hop reachability;
  OSPF reuses what students configured in the `ospf` topic (same
  interfaces, same subnets on the SP-core links L3/L4/L5/L6).
- **R7 is optional, used only in lab-05 and lab-07.** Keeps foundation and
  intermediate labs on a 6-node footprint, activating the seventh node only
  where flowspec propagation must be observed across two IOS-XE speakers.

## Resource Note

- 5 × IOSv @ 512 MB + 1 × CSR1000v @ 4 GB (+1 × CSR1000v @ 4 GB when R7 is
  active) ≈ 6.5 GB RAM base / 10.5 GB with R7. Within the Dell Latitude 5540
  EVE-NG envelope. If R7's CSR1000v image is unavailable, flowspec can be
  demonstrated with pre-captured outputs in lab-05 — the rest of the lab
  (communities) runs on IOSv alone.
