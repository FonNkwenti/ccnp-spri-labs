# Fast Convergence — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **1.7** Implement fast convergence
    - **1.7.a** Bidirectional forwarding detection (BFD)
    - **1.7.b** Nonstop Forwarding (NSF)
    - **1.7.c** NSR (Nonstop Routing)
    - **1.7.d** Timers
    - **1.7.e** BGP PIC (edge and core)
    - **1.7.f** LFA / IP-FRR
    - **1.7.g** BGP additional and backup path

> This topic depends on `ospf`, `isis`, and `bgp`. It does not re-teach the
> protocols — it adds convergence mechanisms on top of working IGP/BGP
> baselines.

## Topology Summary

Five-router IOSv domain: a four-router meshed core (R1-R2-R3-R4) giving
every node at least two loop-free paths to every other node (required for
LFA), plus an external eBGP peer R5 in AS 65200 dual-homed to the core
from lab-00 (both L6 R1↔R5 and L7 R3↔R5 up from day 1). IS-IS L2 is the
sole IGP — fast convergence in this SP-centric topic is built on IS-IS,
matching the production reality of most service-provider cores.

```
                 AS 65100 (SP core, IS-IS L2 + iBGP full mesh)

              ┌────┐                        ┌────┐
              │ R1 ├──────── L1 ────────────┤ R2 │
              └─┬──┘                        └──┬─┘
                │ ╲                            │
                │  ╲                           │
                L4  L5 (diagonal)              L2
                │    ╲                         │
                │     ╲                        │
              ┌─┴──┐   ╲                     ┌─┴──┐
              │ R4 ├────\─────── L3 ─────────┤ R3 │
              └────┘     ╲                   └─┬──┘
                          ╲                    │
                           ╲                   │
                            ╲                  L7
                             ╲                 │
                              ╲              ┌─┴──┐
                             L6 ─────────────┤ R5 │  AS 65200
                                             └────┘  external CE (dual-homed)
```

Link summary: L1 R1↔R2, L2 R2↔R3, L3 R3↔R4, L4 R1↔R4, L5 R1↔R3
(diagonal, provides LFA alternate), L6 R1↔R5 (eBGP), L7 R3↔R5 (second
eBGP — R5 dual-homed from lab-00).

**Key relationships**

- R1, R2, R3, R4 form a meshed core with **five physical links** (L1 R1↔R2,
  L2 R2↔R3, L3 R3↔R4, L4 R1↔R4, L5 R1↔R3). This gives every single-link
  failure at least one alternate path, which is what LFA needs to compute
  a loop-free alternate.
- **IS-IS L2 is the only IGP** configured on the core. Fast convergence
  mechanisms (BFD, GR, LFA) are all protocol-agnostic in principle, but
  running a single IGP eliminates cognitive overhead and lets the student
  focus on the convergence mechanism rather than mediating between
  OSPF and IS-IS. SP-centric exam, SP-typical choice.
- **iBGP full mesh across R1-R4** in AS 65100 carries the external
  prefix learned from R5. BGP PIC exercises the path to R5's prefix
  (192.0.2.0/24) across both eBGP sessions.
- **R5 is dual-homed from lab-00** via L6 R1↔R5 and L7 R3↔R5. Both
  eBGP sessions come up on day 1 and stay up for the whole topic. The
  multi-path topology is a physical fact from the start; what changes
  at lab-03 is the *control-plane behavior* — enabling add-paths and
  BGP PIC so iBGP speakers actually install both external paths and
  pre-compute the backup.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-bfd-and-fast-timers | BFD and Fast Timer Tuning | Foundation | 75m | progressive | 1.7, 1.7.a, 1.7.d | R1, R2, R3, R4, R5 |
| 01 | lab-01-nsf-and-nsr | Nonstop Forwarding (NSF) and Nonstop Routing (NSR) | Intermediate | 75m | progressive | 1.7.b, 1.7.c | R1, R2, R3, R4, R5 |
| 02 | lab-02-lfa-ip-fast-reroute | IS-IS LFA and IP Fast Reroute | Intermediate | 90m | progressive | 1.7.f | R1, R2, R3, R4, R5 |
| 03 | lab-03-bgp-pic-and-addpaths | BGP PIC Edge/Core and Additional Paths | Intermediate | 90m | progressive | 1.7.e, 1.7.g | R1, R2, R3, R4, R5 |
| 04 | lab-04-capstone-config | Fast Convergence Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 05 | lab-05-capstone-troubleshooting | Fast Convergence Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|--------|-------------|------------|---------------|
| 1.7 | Implement fast convergence (umbrella) | lab-00 through lab-05 | yes — capstone |
| 1.7.a | BFD (single-hop on IS-IS, multi-hop on iBGP/eBGP-loopback) | lab-00 (primary), lab-04, lab-05 | yes — capstone |
| 1.7.b | Nonstop Forwarding (graceful restart for IS-IS and BGP) | lab-01 (primary), lab-04, lab-05 | yes — capstone |
| 1.7.c | NSR (Nonstop Routing — configured, with behavioral-gap caveat) | lab-01 (primary), lab-04 | yes — capstone (XR makes NSR demonstrable) |
| 1.7.d | Timers (IS-IS hello/hold, SPF/PRC throttle, BGP keepalive/hold) | lab-00 (primary), lab-04, lab-05 | yes — capstone |
| 1.7.e | BGP PIC Edge and Core | lab-03 (primary), lab-04, lab-05 | yes — capstone |
| 1.7.f | LFA / IP-FRR (per-prefix LFA, Remote LFA) | lab-02 (primary), lab-04, lab-05 | yes — capstone |
| 1.7.g | BGP additional and backup paths (add-paths, backup path install) | lab-03 (primary), lab-04, lab-05 | yes — capstone |

Every blueprint bullet has a dedicated primary lab; capstones exercise
every bullet again end-to-end.

## Design Decisions

- **XR Coverage Posture: `XR-mixed`** (per `memory/xr-coverage-policy.md`).
  Foundation/intermediate labs (00–03) run on IOSv to keep RAM low and
  preserve fine-grained measurement of convergence times in a single image
  family; the capstones flip 2 of the 5 nodes to IOS XRv via Phase 3 #2 of
  the [`2026-05-06 XR Coverage Retrofit`](../../tasks/2026-05-06-xr-coverage-retrofit.md).
  Driven by §1.7.c NSR (only physically demonstrable on a multi-RP image —
  XR is the closest practical platform inside EVE-NG) and §1.7.e BGP PIC
  (XR's PIC edge/core CLI under `address-family ipv4 unicast` differs
  materially from IOS). The capstone retrofit is what closes the
  long-standing NSR behavioral gap — see the NSR caveat below for the
  pre-retrofit limitation. Capstone peak ≈ 10 GB (3×IOSv + 2×XRv); see
  RAM table in `memory/xr-coverage-policy.md` §5.

- **Single IGP (IS-IS L2) across the whole topic.** The scope note
  explicitly says the topic is "organized around the convergence
  mechanism, not the protocol carrying it." Running two IGPs (as
  routing-policy does) would force students to mentally switch contexts
  mid-lab. IS-IS is the SP-native choice — students have already
  configured it in the `isis` topic, so no protocol overhead.
- **Five-link meshed core is deliberate.** LFA needs alternates; a
  simple square (R1-R2-R3-R4 ring) gives alternates but Remote LFA
  requires PQ-node topologies which benefit from the diagonal. Adding
  L5 R1↔R3 gives every node three neighbors and unlocks both basic LFA
  and R-LFA scenarios without adding a sixth router.
- **NSR behavioral gap documented, not hidden.** IOSv has one route
  processor, so NSR's "survive an RP switchover without dropping
  adjacencies" cannot be physically demonstrated. The lab still
  configures NSR on R1 and explains what would happen on a dual-RP
  platform. The exam question pool asks about NSR configuration and
  concepts, not live RP-failover measurements.
- **BFD pattern: single-hop on directly connected IGP, multi-hop on
  loopback-sourced BGP.** This mirrors production. BFD single-hop on
  IS-IS catches physical-layer failures in ~150 ms; BFD multi-hop on
  loopback-sourced iBGP/eBGP catches control-plane failures without
  being fooled by fast-reroute around a downed link.
- **R5 dual-homed from lab-00 (both eBGP sessions up on day 1).** The
  alternative — activating L7 only at lab-03 — would conflate a
  *topology change* (new interface, new neighbor, new IS-IS adjacency
  if we were sloppy) with the *feature being taught* (add-paths + PIC
  controlling which already-learned paths get installed). Keeping the
  physical topology stable from day 1 isolates lab-03's learning to
  control-plane configuration: the student sees "I have two eBGP
  sessions but only one installed path → enable add-paths + best-external
  → now I have two installed paths → enable PIC → now the backup is
  pre-computed in the FIB." That's the actual exam-relevant insight,
  and it's cleaner without a mid-topic recable.
- **Failure-triggered testing in every lab.** Each lab ends with a
  controlled failure (link shut, neighbor reload, BFD-triggered
  teardown) and a measured convergence time. Students collect numbers
  — default ~30 s for untuned IS-IS, ~1 s with tuned timers, ~150 ms
  with BFD, ~50 ms with LFA precomputed — and the capstones grade
  against those targets.
- **Progressive chain: every mechanism stacks.** BFD from lab-00 stays
  on through lab-03. NSF/NSR from lab-01 stays on. LFA from lab-02
  stays on. By lab-03 the topology has BFD + NSF + LFA + BGP PIC all
  active — which is exactly the production deployment the exam expects
  students to configure end-to-end.
