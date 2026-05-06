# Segment Routing v6 (SRv6) — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **4.4** Implement segment routing v6 (SRv6)
    - **4.4.a** Control plane operations
    - **4.4.b** Data plane operations
    - **4.4.c** Flexible algorithm
    - **4.4.d** Locator, micro-segment, encapsulation, and interworking gateway

> This topic depends on `segment-routing` (for SR-MPLS concepts used in the
> interworking gateway lab) and `mpls` (for label-forwarding context). IS-IS L2
> is the IGP, consistent with the segment-routing and mpls topics.
>
> SRv6 requires IOS-XRv 9000 7.1.1 — the only installed platform that supports
> SRv6 locators, SID functions, and Flex-Algo. IOSv and CSR1000v do not have
> SRv6 capability.

## Topology Summary

Six-router IOS-XRv 9000 core: a four-node P ring (P1-P2-P3-P4) with a diagonal
(P1↔P3) that creates three distinct paths between the two PE attachment points.
PE1 hangs off P1 and PE2 hangs off P3. All six XRv9k nodes run IS-IS L2
dual-stack with SRv6 locators under the fc00:0::/32 block. Two IOSv customer
edges (CE1, CE2) join at lab-02 for BGP SRv6 L3VPN (End.DT4). The ring plus
diagonal gives Flex-Algo a meaningful choice: shortest-IGP path uses the
diagonal P1→P3 directly (L5, cost 10), while TE-metric steering can force the
longer P1→P2→P3 path (L1+L2) when asymmetric TE metrics are applied.

```
         ┌───────────┐                        ┌───────────┐
         │    PE1    │                        │    PE2    │
         │ 10.0.0.11 │                        │ 10.0.0.12 │
         └─────┬─────┘                        └─────┬─────┘
               │ L6  10.10.6.0/30    10.10.7.0/30   │ L7
         ┌─────┴─────┐     L1              ┌─────┴─────┐
         │    P1     ├─────────────────────┤    P2     │
         │ 10.0.0.1  │  10.10.1.0/30       │ 10.0.0.2  │
         │fc00:0:1:: ├──╲                  └─────┬─────┘
         └─────┬─────┘   ╲ L5 (diagonal)         │ L2
               │ L4       ╲  10.10.5.0/30    10.10.2.0/30
         10.10.4.0/30       ╲                     │
         ┌─────┴─────┐       ╲             ┌─────┴─────┐
         │    P4     ├────────╲──── L3 ────┤    P3     │
         │ 10.0.0.4  │    10.10.3.0/30      │ 10.0.0.3  │
         │fc00:0:4:: │                      │fc00:0:3:: │
         └───────────┘                      └───────────┘
```

Link summary: L1 P1↔P2 (10.10.1.0/30), L2 P2↔P3 (10.10.2.0/30),
L3 P3↔P4 (10.10.3.0/30), L4 P4↔P1 (10.10.4.0/30),
L5 P1↔P3 diagonal (10.10.5.0/30), L6 PE1↔P1 (10.10.6.0/30),
L7 PE2↔P3 (10.10.7.0/30), L8 CE1↔PE1 (192.0.2.0/30, lab-02+),
L9 CE2↔PE2 (198.51.100.0/30, lab-02+)

Key relationships:
- P1 uses all four XRv9k interfaces: L1 (P2), L4 (P4), L5 diagonal (P3), L6 (PE1)
- P3 uses all four interfaces: L2 (P2), L3 (P4), L5 diagonal (P1), L7 (PE2)
- P2 and P4 each use only two interfaces — they are the "apex" nodes with no PE or diagonal connections
- Three distinct paths exist PE1→PE2: ① direct diagonal P1→P3 (L5, 2 hops), ② via P2 (L1+L2, 3 hops), ③ via P4 (L4+L3, 3 hops)
- Flex-Algo 128 (min IGP): uses direct diagonal; Flex-Algo 129 (min TE metric) can force via-P2 if TE metrics are set higher on L5
- BGP SRv6 L3VPN: PE1 and PE2 are iBGP peers (two-PE full-mesh, no RR needed)
- Interworking gateway: PE1 acts as the SRv6/SR-MPLS boundary node in lab-02

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|------------|------|------|----------------|---------|
| 00 | lab-00-srv6-control-plane | SRv6 IS-IS Control Plane | Foundation | 60m | progressive | 4.4, 4.4.a, 4.4.d | P1, P2, P3, P4, PE1, PE2 |
| 01 | lab-01-srv6-data-plane | SRv6 Data Plane and Encapsulation | Intermediate | 75m | progressive | 4.4.b, 4.4.d | P1, P2, P3, P4, PE1, PE2 |
| 02 | lab-02-flex-algo-and-l3vpn | Flex-Algo, BGP SRv6 L3VPN, and Interworking | Intermediate | 90m | progressive | 4.4.a, 4.4.c, 4.4.d | all |
| 03 | lab-03-capstone-config | SRv6 Full Deployment — Capstone I | Advanced | 120m | capstone_i | all | all |
| 04 | lab-04-capstone-troubleshooting | SRv6 Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In | XR Exercised? |
|-----------------|-------------|------------|---------------|
| 4.4 | Implement segment routing v6 (SRv6) | lab-00, lab-01, lab-02 | yes — primary |
| 4.4.a | Control plane operations | lab-00 (IS-IS SRv6 extensions, locator advertisements, SID manager), lab-02 (BGP SRv6 L3VPN signaling, End.DT4 allocation) | yes — primary |
| 4.4.b | Data plane operations | lab-01 (SRH, End/End.X/End.DT4, H.Encaps, PSP, transit behavior) | yes — primary |
| 4.4.c | Flexible algorithm | lab-02 (Flex-Algo 128/129 definition, per-algo SID allocation, asymmetric TE metric steering) | yes — primary |
| 4.4.d | Locator, micro-segment, encapsulation, and interworking gateway | lab-00 (locator config + verification), lab-01 (H.Encaps encapsulation source, SRH construction), lab-02 (uSID/micro-segment SID table, SRv6↔SR-MPLS binding-SID interworking) | yes — primary |

## Design Decisions

- **XR Coverage Posture: `XR-native`** (per `memory/xr-coverage-policy.md`).
  SRv6 is the one feature in the 300-510 blueprint that absolutely requires
  IOS-XRv 9000 — neither IOSv nor CSR1000v has any SRv6 capability. The
  XR-native posture is therefore not a choice but a hard platform constraint;
  every blueprint sub-bullet (4.4.a-d) is taught and verified on XR. No Phase 3
  capstone retrofit is required because there is no IOSv portion of the topic
  to retrofit *from*.

- **Platform: full XRv9k** — SRv6 is not supported on IOSv (IOS 15.9) or CSR1000v
  (IOS-XE 17.3.x). IOS-XRv 9000 7.1.1 is the only installed image with SRv6
  capability. Six nodes × 4096 MB = 24 GB — comfortably within the 64 GB host
  limit. (The reduced 4 GB allocation works because SRv6 control/data plane
  exercise less of the XRv 9000 feature surface than, e.g., the EVPN/Tree SID
  workloads in `segment-routing`.)

- **Four-node P ring + diagonal** — four P nodes in a ring (P1-P2-P3-P4) with a
  diagonal (P1↔P3) create three structurally distinct paths between PE1 and PE2
  (direct diagonal, via-P2, via-P4). This makes Flex-Algo steering concretely
  observable: Flex-Algo 128 (min IGP metric) follows the diagonal, while Flex-Algo
  129 (min TE metric) can be steered to the via-P2 path by setting a lower TE metric
  on L1+L2 vs L5. The three-node triangle in the original draft had only two paths —
  insufficient to demonstrate the full TE-metric steering use case.

- **Five labs (matches estimate)** — 4.4.d covers four sub-concepts (locator,
  micro-segment/uSID, encapsulation, interworking gateway) spread across labs 00-02;
  no standalone labs needed. All four concepts build naturally on the IS-IS →
  data-plane → services progression.

- **uSID caveat** — IOS-XR 7.1.1 SRv6 micro-segment (uSID) is a carrier-grade
  forwarding compression feature (RFC 9252). Control-plane state — compressed uSID
  locator format, SID table entries — is verifiable via `show segment-routing srv6
  sid` and `show segment-routing srv6 locator`. Hardware-level packet-capture
  showing actual SRH compression is an ASIC-accelerated data path not reliably
  emulated in QEMU. Lab-02 exercises uSID locator configuration and SID inspection,
  with a noted limitation that end-to-end captures show full 128-bit SIDs rather than
  compressed 16-bit uSIDs.

- **Interworking gateway in lab-02 (progressive, not standalone)** — PE1 acts as the
  SRv6↔SR-MPLS boundary using a binding-SID mapping entry, keeping the concept in
  the progressive chain. This references SR-MPLS prefix-SID concepts from the
  segment-routing topic but requires no separate MPLS domain in the topology.

- **BGP SRv6 L3VPN** — PE1 and PE2 run iBGP two-PE full-mesh with End.DT4 service
  SIDs from lab-02. Avoids route-reflector overhead; focus stays on SRv6 service-SID
  allocation and VPN prefix exchange.
