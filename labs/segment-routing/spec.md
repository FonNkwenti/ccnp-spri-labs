# Segment Routing and SR-TE — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **4.2** Implement segment routing
    - **4.2.a** Routing protocol extensions (BGP, OSPF, IS-IS)
    - **4.2.b** SRGB and SRLB
    - **4.2.c** Topology-Independent Loop-Free Alternate (TI-LFA)
    - **4.2.d** Migration procedures (SR prefer and mapping server)
  - **4.3** Implement segment routing traffic engineering
    - **4.3.a** Automated steering and coloring
    - **4.3.b** Policies (constraints, metrics, and attributes)
    - **4.3.c** PCE-based path calculation
    - **4.3.d** SRLG
    - **4.3.e** Tree SID

> This topic depends on `mpls` (for LDP/MPLS fundamentals used by
> migration) and `routing-policy` (for route-policy/RPL syntax used by
> SR-TE color matching). IS-IS L2 is the IGP, consistent with the
> `fast-convergence` and `mpls` topics.

## Topology Summary

Four-router IOS-XRv 9000 core (R1-R2-R3-R4) meshed identically to the
`fast-convergence` topology — full ring (L1 R1↔R2, L2 R2↔R3, L3 R3↔R4,
L4 R1↔R4) with a diagonal (L5 R1↔R3) that unlocks TI-LFA and multi-path
SR-TE. A dedicated PCE controller (also XRv9k) joins at lab-04 via a
BGP-LS peering to R2. Two IOSv customer edges (CE1, CE2) join at
lab-03 in their own ASes to exercise SR-TE end-to-end customer steering.

```
                   AS 65100 (SP core, IS-IS L2 + SR-MPLS)

            ┌────┐                         ┌────┐
            │ R1 ├──────── L1 ─────────────┤ R2 │
            └─┬──┘                         └──┬─┘
              │ ╲                             │
              │  ╲                           (L6 to PCE, lab-04+)
             L4   L5 (diagonal, TI-LFA)       │
              │    ╲                          │
              │     ╲                         L2
            ┌─┴──┐   ╲                      ┌─┴──┐
            │ R4 ├────╲─────── L3 ──────────┤ R3 │
            └────┘     ╲                    └─┬──┘
                        ╲                      │
                         ╲                     │
                          ╲ (L7 R1↔CE1, lab-03+; L8 R3↔CE2, lab-03+)

         ┌─────┐                          ┌─────┐
         │ CE1 │  AS 65101 (lab-03+)      │ CE2 │  AS 65102 (lab-03+)
         └─────┘  iosv, eBGP to R1 via L7 └─────┘  iosv, eBGP to R3 via L8

                                             ┌─────┐
                                             │ PCE │  AS 65100 (lab-04+)
                                             └─────┘  BGP-LS peer of R2 via L6
```

Link summary: L1 R1↔R2, L2 R2↔R3, L3 R3↔R4, L4 R1↔R4, L5 R1↔R3
(diagonal, IS-IS+SR, TI-LFA alternate), L6 R2↔PCE (BGP-LS only,
lab-04+), L7 R1↔CE1 (eBGP, lab-03+), L8 R3↔CE2 (eBGP, lab-03+).

**Key relationships**

- **Full-mesh core + diagonal**. Every R1↔R3, R2↔R4 pair has at least
  two link-disjoint IGP paths. TI-LFA (4.2.c) needs this; SR-TE (4.3)
  benefits from it because explicit paths have multiple real choices
  instead of a single obvious route.
- **PCE is a peer, not a core router**. The PCE runs BGP-LS with R2
  only — it does not participate in IS-IS, does not carry IP traffic,
  and has no data-plane role. R2 acts as the BGP-LS producer for the
  IGP topology. This cleanly isolates the controller plane (PCE ↔ R2)
  from the forwarding plane (core routers).
- **CE1 (AS 65101) and CE2 (AS 65102) source the customer prefixes**
  that SR-TE policies steer. They activate at lab-03 when the topic
  shifts from "build SR labels" to "use SR labels to move customer
  traffic on specific paths." 192.0.2.0/24 is announced by CE1, and
  198.51.100.0/24 by CE2.
- **Platform = IOS-XRv 9000 throughout the core**. IOSv 15.9 has no SR
  support; CSR1000v 17.3 supports SR-MPLS but not Tree SID. IOS-XR is
  the SP-native platform and covers every 4.2/4.3 bullet. The boot
  penalty (~10 min per XRv node) is the cost of admission for SR.
- **SRGB = 16000-23999** (Cisco default); per-node prefix SIDs are
  16001 (R1), 16002 (R2), 16003 (R3), 16004 (R4), 16099 (PCE). SRLB
  uses the default 15000-15999 range.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-sr-foundations-and-srgb | SR-MPLS Foundations, SRGB, and Prefix SIDs | Foundation | 90m | progressive | 4.2, 4.2.a, 4.2.b | R1, R2, R3, R4 |
| 01 | lab-01-ti-lfa | Topology-Independent Loop-Free Alternate (TI-LFA) | Intermediate | 75m | progressive | 4.2.c | R1, R2, R3, R4 |
| 02 | lab-02-sr-migration-ldp-coexistence | SR Migration — LDP Coexistence, Mapping Server, SR-Prefer | Intermediate | 90m | progressive | 4.2.d | R1, R2, R3, R4 |
| 03 | lab-03-sr-te-policies-and-steering | SR-TE Policies, Constraints, and Automated Steering | Intermediate | 105m | progressive | 4.3.a, 4.3.b | R1, R2, R3, R4, CE1, CE2 |
| 04 | lab-04-pce-srlg-tree-sid | PCE Path Computation, SRLG, and Tree SID | Advanced | 105m | progressive | 4.3.c, 4.3.d, 4.3.e | R1, R2, R3, R4, CE1, CE2, PCE |
| 05 | lab-05-ospf-sr-standalone | OSPF Segment Routing Extensions (standalone) | Intermediate | 60m | standalone | 4.2.a (OSPF) | R1, R2, R3, R4 |
| 06 | lab-06-capstone-config | SR Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 07 | lab-07-capstone-troubleshooting | SR Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|--------|-------------|------------|---------------|
| 4.2 | Implement segment routing (umbrella) | lab-00 through lab-07 | yes — primary |
| 4.2.a | SR extensions — IS-IS (lab-00), OSPF (lab-05 standalone), BGP-LS (lab-04) | lab-00 (IS-IS primary), lab-04 (BGP-LS), lab-05 (OSPF primary), lab-06, lab-07 | yes — primary |
| 4.2.b | SRGB and SRLB (Global and Local Block allocation) | lab-00 (primary), lab-05, lab-06, lab-07 | yes — primary |
| 4.2.c | TI-LFA (microloop-free post-convergence FRR) | lab-01 (primary), lab-06, lab-07 | yes — primary |
| 4.2.d | Migration — SR mapping server + `sr-prefer` over LDP | lab-02 (primary), lab-06, lab-07 | yes — primary |
| 4.3.a | Automated steering (color-based PE steering, on-demand next-hop) | lab-03 (primary), lab-06, lab-07 | yes — primary |
| 4.3.b | SR-TE policies (constraints, metrics, attributes) | lab-03 (primary), lab-04, lab-06, lab-07 | yes — primary |
| 4.3.c | PCE-based path calculation (PCEP, BGP-LS topology feed) | lab-04 (primary), lab-06, lab-07 | yes — primary |
| 4.3.d | SRLG (Shared Risk Link Groups) | lab-04 (primary), lab-06, lab-07 | yes — primary |
| 4.3.e | Tree SID (SR-MPLS P2MP, configuration + caveat) | lab-04 (primary), lab-06, lab-07 | yes — primary |

Every blueprint bullet has a dedicated primary lab; capstones exercise
every bullet again end-to-end.

## Design Decisions

- **XR Coverage Posture: `XR-native`** (per `memory/xr-coverage-policy.md`).
  All core nodes run IOS-XRv 9000; IOSv appears only as customer edges
  (CE1, CE2). This is correct as designed — segment routing in §4.2 / §4.3
  has features (Tree SID §4.3.e, full PCE §4.3.c, on-demand next-hop
  §4.3.a) that are XR-only or only fully implemented on XR. No retrofit
  required. The XRv 9000 platform is justified rather than gratuitous: SR
  policies, PCEP server, and Tree SID all need the heavier image. RAM
  budget (~80 GB peak with 5×XRv 9000) approaches the 64 GB host ceiling
  and is documented in lab-00's prereq notes.

- **Eight labs (+1 over the topic-plan estimate of 7).** 4.2 and 4.3
  between them have 9 sub-bullets. The progressive chain collapses
  cleanly to 5 content labs (00-04) + 2 capstones by combining
  adjacent bullets (4.3.a + 4.3.b for SR-TE policies and steering;
  4.3.c + 4.3.d + 4.3.e for PCE-driven advanced TE). The extra lab
  (lab-05) is a **standalone OSPF-SR lab** — it cannot flow from the
  IS-IS progressive chain without routing churn, so it sits after the
  last progressive lab and before the capstones. Total 8 labs is
  within the skill's ±2 tolerance of the topic-plan estimate.
- **Platform: IOS-XRv 9000 for the SR core, IOSv for customer edges.**
  IOSv 15.9 has no SR. CSR1000v 17.3 was evaluated as a lighter
  alternative and covers 4.2.a-d + 4.3.a-d cleanly (SR-MPLS, SR-TE
  policies, TI-LFA, mapping server, PCEP *client*) but cannot do
  **Tree SID** (4.3.e) — SR-MPLS P2MP is an IOS-XR feature and
  Tree SID requires the root and leaf PCCs to be XR. That forces XR
  on R1, R3, R4 (Tree SID participants) out of a 4-router core, so a
  mixed-platform core would leave only R2 as a CSR1000v, with little
  resource saving and the complication of two control-plane dialects.
  Full IOS-XR is cleaner and gives production parity. The boot latency
  (~10 min per XRv node) is documented in the lab-00 prereq section;
  students are warned to start nodes early. Five XRv nodes plus two
  IOSv nodes fit comfortably in the 64 GB host (22 GB RAM total).
- **Tree SID (4.3.e) configured with a behavioral-gap caveat.** IOS-XRv
  9000 7.1.1 has partial Tree SID support — the CLI accepts the policy
  and PCE computes the tree, but P2MP data-plane replication is an
  ASIC feature the QEMU-emulated XR cannot fully demonstrate. Lab-04
  configures Tree SID end-to-end (PCE policy, PCC delegation), verifies
  control-plane state (`show segment-routing traffic-eng p2mp policy`),
  and documents what a real ASR 9000 would do with the computed tree.
  This mirrors how `fast-convergence` handles the NSR gap — configure,
  verify state, document the hardware limitation honestly.
- **OSPF SR is a dedicated standalone lab (lab-05), not a sidebar.**
  4.2.a lists BGP, OSPF, and IS-IS as protocol extensions. Running
  OSPF alongside IS-IS on the same interfaces would thrash next-hops
  and produce administrative-distance fights for no pedagogical gain.
  The chosen approach: lab-05 is a **standalone** lab that starts
  from the clean-slate interfaces-only baseline, brings up OSPFv2 SR
  on R1-R4 (in place of IS-IS for that single lab), allocates the
  same prefix SIDs under OSPF, and verifies that SR forwarding works
  identically regardless of IGP. Because the lab is standalone, its
  end-state does not feed the capstones — the capstones restart from
  clean-slate anyway and re-use IS-IS. BGP participation in SR
  (4.2.a, BGP angle) is still covered in lab-04 via BGP-LS topology
  distribution to the PCE.
- **Migration lab (4.2.d) requires LDP + SR to coexist.** `sr-prefer`
  and the mapping server only have pedagogical value when there are
  two label sources in play. Lab-02 adds LDP in parallel with SR on
  the core (MPLS topic graduates taught LDP; we reuse that muscle
  memory), configures R1 as SR mapping server to advertise SIDs for
  the CE-learned customer prefix ranges (non-SR-native prefixes), then
  uses `sr-prefer` to flip label-source preference from LDP to SR.
  Before/after verification shows the LFIB swapping from LDP-learned
  labels to SR-learned labels for the same destination. This is the
  only place in the series where LDP is deliberately re-introduced.
- **PCE uses BGP-LS from R2, not IS-IS.** Production PCEs rarely join
  the IGP — they receive topology via BGP-LS and deliver paths via
  PCEP. Modeling this accurately keeps the PCE plane isolated from
  the forwarding plane and matches how the exam presents PCE
  architecture. R2 is the BGP-LS producer (chosen arbitrarily; could
  be any core router).
- **Progressive chain: strict.** SR from lab-00 stays on through
  lab-04. LDP from lab-02 stays on (coexists with SR as in production
  migrations). TI-LFA from lab-01 stays on. SR-TE policies from lab-03
  stay on. PCE from lab-04 stays on. By lab-04 the topology carries
  the full SR stack; capstones re-build it from a clean slate in 120
  minutes to prove the student can bootstrap without intermediate
  help.
- **CE1/CE2 optional, booting at lab-03.** Labs 00-02 are label-plane
  and control-plane exercises — prefix SID allocation, FRR behavior,
  migration — and don't need customer traffic. CEs join at lab-03
  when SR-TE "automated steering" requires real customer prefixes
  tagged with color communities. Deferring CE boot saves 1 GB RAM on
  early labs and shortens the boot phase.
