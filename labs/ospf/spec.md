# OSPF Routing — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **1.1** Compare OSPF and IS-IS routing protocols
  - **1.2** Troubleshoot OSPF multiarea operations (IPv4 and IPv6)
    - **1.2.a** Route advertisement
    - **1.2.b** Summarization

> Bullet 1.1 is anchored in this topic by design (see `specs/topic-plan.yaml`). The
> `isis` topic carries a cross-reference rather than re-teaching the comparison.

## Topology Summary

Five-router dual-stack backbone plus one optional ASBR. Three non-backbone areas
branch off a single-link Area 0 (R2↔R3). R2 is ABR for Area 1, R3 is ABR for
Areas 2 and 3, and R6 (optional, introduced in lab-03) simulates an external
autonomous system for summary-address practice.

```
      Area 1          Area 0          Area 2
     ┌────┐          ┌────┐          ┌────┐          ┌────┐
     │ R1 ├──L1──────┤ R2 ├──L2──────┤ R3 ├──L3──────┤ R4 │
     └────┘          └────┘          └────┘          └────┘
                      ABR             ABR │
                                          L4
                                          │
                                       ┌────┐
                                       │ R5 │  Area 3 (NSSA in lab-03+)
                                       └────┘

     [Optional, from lab-03]
     R6 ── L5 ── R3    external AS, redistributed into OSPF via R6 as ASBR
```

**Key relationships**

- Area 0 is a single P2P link (R2↔R3). Keeping the backbone tiny puts the
  emphasis on ABR/ASBR behavior and LSA propagation rather than intra-area
  design.
- R3 is a triple-ABR (Areas 0, 2, 3) — the natural focal point for
  summarization, stub/NSSA conversions, and LSA type 3/5/7 filtering.
- R6 stays dark until lab-03 so earlier labs see a pure OSPF domain with
  no Type-5 LSAs muddying the baseline.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-single-area-ospfv2 | Single-Area OSPFv2 Foundations | Foundation | 45m | progressive | 1.1 | R1, R2, R3 |
| 01 | lab-01-multiarea-ospfv2 | Multiarea OSPFv2 and LSA Propagation | Foundation | 60m | progressive | 1.2, 1.2.a | R1, R2, R3, R4, R5 |
| 02 | lab-02-ospfv3-dual-stack | OSPFv3 Dual-Stack Multiarea | Intermediate | 75m | progressive | 1.2, 1.2.a | R1, R2, R3, R4, R5 |
| 03 | lab-03-summarization-stub-nssa | Summarization, Stub, and NSSA | Intermediate | 90m | progressive | 1.2.b | R1, R2, R3, R4, R5, R6 |
| 04 | lab-04-capstone-config | OSPF Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, R5, R6 |
| 05 | lab-05-capstone-troubleshooting | OSPF Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, R5, R6 |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|--------|-------------|------------|---------------|
| 1.1 | Compare OSPF and IS-IS routing protocols | lab-00 (concepts, LSA types, metrics), lab-02 (v2 vs v3 and cross-reference to IS-IS L1/L2) | no — deferred to `xr-bridge` |
| 1.2 | Troubleshoot OSPF multiarea operations (IPv4 and IPv6) | lab-01 (IPv4), lab-02 (IPv6), lab-05 (troubleshooting) | yes — capstone |
| 1.2.a | Route advertisement | lab-01, lab-02, lab-04 | yes — capstone |
| 1.2.b | Summarization | lab-03 (area range + summary-address), lab-04, lab-05 | yes — capstone |

## Design Decisions

- **XR Coverage Posture: `XR-mixed`** (per `memory/xr-coverage-policy.md`).
  Foundation labs (00–03) run on IOSv 15.9 to keep RAM low and focus on
  OSPFv2/v3 mechanics; the capstones replace 2 of the 6 nodes with IOS XRv to
  give CCIE SP precursor exposure to XR's `router ospf` address-family
  hierarchy and ABR CLI. Driven by §1.2 multiarea — XR ABR/ASBR behavior is
  materially different in dialect even though the protocol mechanics are
  identical. Capstone exposure lands via Phase 3 #4 of the
  [`2026-05-06 XR Coverage Retrofit`](../../tasks/2026-05-06-xr-coverage-retrofit.md);
  XR coverage for §1.1 (OSPF vs IS-IS comparison on XR) is deferred to
  `labs/xr-bridge/lab-00-xr-igp-foundations` (build deferred — see policy doc).
- **Platform: `iosv` (IOS 15.9) for foundation labs; mixed IOSv + IOS XRv
  for capstones (Phase 3 retrofit).** IOSv supports all required OSPFv2/v3
  features (multiarea, stub/NSSA variants, area range, summary-address,
  virtual links) and is far lighter than CSR1000v — a 5-router foundation
  topology runs in ~2.5 GB of RAM. Capstone peak ≈ 9 GB (3×IOSv + 2×XRv);
  see RAM table in `memory/xr-coverage-policy.md` §5.
- **Area 0 kept minimal (R2↔R3 only).** Puts the pedagogical weight on inter-area
  behavior, ABR roles, and LSA filtering rather than backbone design.
- **Single triple-ABR (R3).** Concentrates Areas 2 and 3 on one router so
  lab-03 can flip between stub, totally-stubby, and NSSA variants by editing
  one config, reinforcing the mechanics rather than multiplying device count.
- **Dual-stack from lab-02 onward.** OSPFv3 rides the same topology and
  interfaces as OSPFv2 — students compare LSA types, process selection
  (`ipv6 router ospf`), and address-family behavior side-by-side.
- **R6 as optional ASBR.** Reserved but dark until lab-03 so early labs show a
  pure intra-OSPF topology. Introducing external routes only when needed keeps
  lab-01's `show ip ospf database` output readable.
- **Config chaining (progressive labs):** solutions from lab-NN become
  initial-configs for lab-NN+1. Only additions between labs, never removals
  (per `memory/lab-standards.md`).
