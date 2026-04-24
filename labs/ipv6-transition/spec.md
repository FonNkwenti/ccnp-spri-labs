# IPv6 Tunneling and Transition — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **1.6** Describe IPv6 tunneling mechanisms
    - **1.6.a** Static IPv6-in-IPv4 tunnels
    - **1.6.b** Dynamic 6to4 tunnels
    - **1.6.c** IPv6 provider edge (6PE)
    - **1.6.d** IPv6 policy enforcement
    - **1.6.e** NAT64 and MAP-T

> This topic depends on `bgp` for MP-BGP fundamentals used by 6PE.

## Topology Summary

Four-router IOSv core with an IPv4-only middle (R2, R3 as P routers) and
dual-stack edges (R1, R4 as CE/PE). Same three-link IPv4 backbone carries
every transition mechanism in turn: manual GRE-style tunnels in lab-00,
MPLS labels in lab-01, policy-enforced forwarding in lab-02. A CSR1000v
NAT64/MAP-T gateway (R5) plus an IPv6-only VPC client join at lab-03 to
introduce header translation.

```
     [IPv6 site]       [IPv4 core]        [IPv4 core]      [IPv6 site]
     ┌────┐             ┌────┐             ┌────┐            ┌────┐
     │ R1 ├──── L1 ─────┤ R2 ├──── L2 ─────┤ R3 ├──── L3 ────┤ R4 │
     └────┘             └────┘             └────┘            └────┘
     CE/PE              P (v4-only)        P (v4-only)       CE/PE

     [Optional, from lab-03 — NAT64/MAP-T gateway]
                                            │
                                            L4 (IPv4)
                                            │
                                          ┌────┐
                                          │ R5 │ CSR1000v
                                          └─┬──┘
                                            L5 (IPv6-only)
                                            │
                                         ┌──────┐
                                         │ VPC1 │  IPv6 client
                                         └──────┘
```

**Key relationships**

- R2 and R3 are **deliberately IPv4-only** for the life of this topic. That
  constraint is the whole point of 1.6.c (6PE): IPv6 reachability across
  a core that knows nothing about IPv6. It also lets tunnels in lab-00
  encapsulate IPv6 into IPv4 naturally — the core never sees an IPv6
  header until the tunnel terminates.
- R1 and R4 play three roles over the topic: (1) tunnel endpoints in
  lab-00, (2) 6PE PE routers in lab-01, (3) IPv6 policy enforcement
  points in lab-02. Each lab adds configuration; none of it is removed.
- R5 (CSR1000v) is the only IOS-XE node. IOSv 15.9 has no usable
  stateful NAT64 or MAP-T support — both features are CSR1000v-exclusive
  on this EVE-NG installation. R5 dual-homes: L4 into the IPv4 core and
  L5 into an IPv6-only client segment (VPC1).
- VPC1 is a single IPv6 endpoint — it exists solely so NAT64
  demonstrations have a real end-to-end source without pretending a
  router loopback is a client.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-manual-and-6to4-tunnels | Static IPv6-in-IPv4 and 6to4 Tunnels | Foundation | 60m | progressive | 1.6, 1.6.a, 1.6.b | R1, R2, R3, R4 |
| 01 | lab-01-6pe-over-mpls | IPv6 Provider Edge (6PE) over MPLS | Intermediate | 90m | progressive | 1.6.c | R1, R2, R3, R4 |
| 02 | lab-02-ipv6-policy-enforcement | IPv6 Policy Enforcement with ACLs and PBR | Intermediate | 75m | progressive | 1.6.d | R1, R2, R3, R4 |
| 03 | lab-03-nat64-and-mapt | NAT64 and MAP-T Translation | Intermediate | 90m | progressive | 1.6.e | R1, R2, R3, R4, R5, VPC1 |
| 04 | lab-04-capstone-config | IPv6 Transition Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 05 | lab-05-capstone-troubleshooting | IPv6 Transition Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In |
|--------|-------------|------------|
| 1.6 | Describe IPv6 tunneling mechanisms | lab-00 (umbrella), lab-04, lab-05 |
| 1.6.a | Static IPv6-in-IPv4 tunnels | lab-00 (primary), lab-04, lab-05 |
| 1.6.b | Dynamic 6to4 tunnels | lab-00 (primary), lab-04, lab-05 |
| 1.6.c | IPv6 provider edge (6PE) | lab-01 (primary), lab-04, lab-05 |
| 1.6.d | IPv6 policy enforcement | lab-02 (primary), lab-04, lab-05 |
| 1.6.e | NAT64 and MAP-T | lab-03 (primary), lab-04, lab-05 |

Every blueprint bullet has a dedicated primary lab; capstones exercise
every bullet again end-to-end.

## Design Decisions

- **Lab count: 6 (+1 over the topic-plan estimate of 5).** The estimate
  assigned one lab per bullet, but the project convention (see ospf,
  bgp) treats the last two labs as always-capstones. Giving each
  transition mechanism its own primary lab plus two capstones lands at
  6. This is within the ±2 tolerance and matches the instructional
  density of the other topics.
- **IOSv core + CSR1000v only for NAT64/MAP-T.** IOSv 15.9 supports
  tunnels, 6to4, MPLS LDP, MP-BGP with send-label (6PE), and IPv6 ACLs
  / PBR — covering 1.6.a through 1.6.d with ~2 GB RAM across 4 nodes.
  NAT64 and MAP-T both require IOS-XE, so R5 (CSR1000v, 3 GB RAM) is
  introduced as an optional device in lab-03. Early labs stay cheap
  and fast; only one lab pays the IOS-XE boot cost.
- **R2 and R3 stay IPv4-only for the whole topic.** This preserves the
  pedagogical payload of 1.6.c — the student sees IPv6 reachability
  established across a core that never configures an IPv6 address.
  Tunnels work over this core, MPLS labels work over this core, but
  the core's RIB is pure IPv4 throughout. If R2/R3 were dual-stack,
  the student could "cheat" and route IPv6 natively, defeating the
  point.
- **6PE chosen over 6VPE.** The blueprint says "IPv6 provider edge" —
  ambiguous between 6PE (global IPv6 over MPLS) and 6VPE (VPNv6 per-VRF).
  6PE is simpler, uses one BGP address-family, and matches the
  SPRI-era exam question pool. Left 6VPE for future expansion.
- **NAT64 and MAP-T paired in one lab.** They share the same gateway
  device (R5), the same mental model (header translation, not
  tunneling), and both exercise the same IPv6-to-IPv4 flow. Splitting
  them would duplicate setup without adding pedagogical value.
- **VPC1 as IPv6 client, not a router loopback.** NAT64 is about
  end-to-end client-to-server behavior; using a real client endpoint
  (VPC1) means the student sees the DNS64/AAAA-synthesis path, pings
  `64:ff9b::a00:0001`, and observes the packet on the IPv4 wire —
  exactly how the exam frames the topic. A router loopback would still
  work mechanically but obscures the intent.
- **Progressive chain is strict: only add config between labs.** Every
  lab's solution is the next lab's starting point. Tunnels from lab-00
  persist into lab-01 (ignored by 6PE but present). 6PE BGP sessions
  from lab-01 persist into lab-02. Etc. The capstones start from a
  clean_slate interface-only baseline so students rebuild the whole
  transition stack in 2 hours.
