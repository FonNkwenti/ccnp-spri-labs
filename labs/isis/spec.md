# IS-IS Routing — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **1.3** Troubleshoot IS-IS multilevel operations (IPv4 and IPv6)
    - **1.3.a** Route advertisement
    - **1.3.b** Summarization

> Bullet 1.1 (Compare OSPF and IS-IS) is anchored in the `ospf` topic. Labs 00 and
> 02 here carry cross-references back to that comparison so students re-anchor the
> LSA-vs-LSP / area-vs-level distinctions while working inside IS-IS.

## Topology Summary

Same physical five-router layout used by the `ospf` topic — deliberately reused so
students see one wiring diagram running two different IGPs. Two IS-IS areas
(49.0001 and 49.0002) and one L1/L2 backbone adjacency anchor the multilevel
behavior; R6 is an optional external-prefix source introduced in lab-02.

```
     Area 49.0001                    Area 49.0002
     ┌────┐        ┌────┐          ┌────┐          ┌────┐
     │ R1 ├──L1────┤ R2 ├───L2─────┤ R3 ├────L3────┤ R4 │
     └────┘        └────┘          └────┘          └────┘
       L1           L1/L2           L1/L2           L1
                         └── L2 adj ─┘       │
                                            L4
                                             │
                                          ┌────┐
                                          │ R5 │  L1
                                          └────┘

     [Optional, from lab-02]
     R6 ── L5 ── R3    external prefix source; redistributed into IS-IS on R3
```

**Key relationships**

- R2 and R3 are L1/L2 routers in *different* areas. The R2↔R3 link only forms
  an L2 adjacency — this is the singular place in the topology where the IS-IS
  backbone exists.
- R1 is a strict L1 router inside 49.0001. R4 and R5 are strict L1 routers
  inside 49.0002.
- The default route from L2 → L1 via the ATT bit is teachable on R1 and on
  R4/R5 simultaneously, from opposite sides of the backbone.
- R6 is not an IS-IS speaker — it injects external IPv4 and IPv6 prefixes that
  R3 redistributes, so summary-address behavior and LSP external-prefix TLVs
  can be practiced without a second IGP domain.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-single-level-isis | Single-Level IS-IS Foundations | Foundation | 45m | progressive | 1.3 | R1, R2, R3 |
| 01 | lab-01-multilevel-isis | Multilevel IS-IS and Route Advertisement | Intermediate | 75m | progressive | 1.3, 1.3.a | R1, R2, R3, R4, R5 |
| 02 | lab-02-dual-stack-summarization | Dual-Stack IS-IS with Summarization and Route Leaking | Intermediate | 90m | progressive | 1.3, 1.3.a, 1.3.b | R1, R2, R3, R4, R5, R6 |
| 03 | lab-03-capstone-config | IS-IS Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, R5, R6 |
| 04 | lab-04-capstone-troubleshooting | IS-IS Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, R5, R6 |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|--------|-------------|------------|---------------|
| 1.3 | Troubleshoot IS-IS multilevel operations (IPv4 and IPv6) | lab-00 (single-level baseline), lab-01 (multilevel IPv4), lab-02 (IPv6 MT), lab-04 (TS) | yes — capstone |
| 1.3.a | Route advertisement | lab-01 (L1→L2, L2→L1 via ATT), lab-02 (route leaking with `redistribute isis ip level-2 into level-1`), lab-03 | yes — capstone |
| 1.3.b | Summarization | lab-02 (`summary-address` IPv4+IPv6 at L1/L2 boundary and for redistributed external prefixes), lab-03, lab-04 | yes — capstone |

## Design Decisions

- **XR Coverage Posture: `XR-mixed`** (per `memory/xr-coverage-policy.md`).
  Foundation labs (00–02) run on IOSv 15.9 to match the `ospf` topology and
  keep RAM low; the capstones replace 2 of the 6 nodes with IOS XRv to give
  students hands-on exposure to XR's `router isis` address-family hierarchy
  and L1/L2 route-leak CLI. Driven by §1.3 multilevel — XR's IS-IS dialect
  (NET configured under `router isis` rather than as an interface
  command, address-family-scoped `summary-prefix`, RPL-based route leaking)
  is materially different even though level mechanics are identical.
  Capstone exposure lands via Phase 3 #3 of the
  [`2026-05-06 XR Coverage Retrofit`](../../tasks/2026-05-06-xr-coverage-retrofit.md);
  full XR re-treatment of multilevel IS-IS is also covered in
  `labs/xr-bridge/lab-00-xr-igp-foundations` (build deferred).
- **Physical topology mirrors the `ospf` topic.** Same interfaces, same IP plan
  on the transit links and loopbacks. Students reuse muscle memory on wiring and
  addressing; the cognitive load is spent on IS-IS semantics (levels, NET,
  LSP TLVs) rather than re-learning the diagram.
- **Two areas, single L2 adjacency (R2↔R3).** A minimal backbone is the
  clearest way to see the L1/L2 boundary. A larger L2 mesh would dilute the
  focus on the ATT bit and route-leak mechanics.
- **Platform: `iosv` (IOS 15.9) for foundation labs; mixed IOSv + IOS XRv for
  capstones (Phase 3 #3 retrofit).** IOSv supports IS-IS multilevel,
  multi-topology IPv6, `summary-address` at any level, and the route-leak
  knobs — sufficient for the foundation labs at ~3 GB RAM. The capstones add
  2× IOS XRv for CCIE SP precursor exposure (~10 GB peak); see RAM table in
  `memory/xr-coverage-policy.md` §5.
- **Multi-topology (MT) IPv6** is the default in lab-02 because it gives
  independent SPFs for IPv4 and IPv6 and matches what modern SP deployments
  run. Single-topology IS-IS for IPv6 is mentioned in scope_notes only, not
  configured.
- **R6 as non-IS-IS external source.** Keeps the IS-IS LSP database clean of a
  second IGP's prefixes. Redistribution on R3 creates ATT-bit-independent
  externals whose summarization is practiced in lab-02.
- **Config chaining (progressive labs):** lab-NN solutions become the
  initial-configs for lab-NN+1. Only additions between labs, never removals.
