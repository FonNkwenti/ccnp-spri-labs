# MPLS — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **4.1** Troubleshoot MPLS
    - **4.1.a** LDP
    - **4.1.b** LSP
    - **4.1.c** Unified BGP (BGP labeled-unicast)
    - **4.1.d** BGP-free core
    - **4.1.e** RSVP-TE tunnels

> This topic depends on `ospf`, `isis`, and `bgp`. The IGP is IS-IS L2
> (SP-native, consistent with the `fast-convergence` topic). BGP
> fundamentals (iBGP/eBGP, loopback-sourced sessions) are assumed.

## Topology Summary

Four-router IOSv core in AS 65100 (PE1-P1-P2-PE2) forming a diamond
with a P1↔P2 cross — giving every PE two disjoint paths through the
core (required for RSVP-TE alternate-path demonstrations), plus two
optional external customer edges (CE1 in AS 65101, CE2 in AS 65102)
that activate at lab-02 when customer traffic needs to traverse the
BGP-free core. IS-IS L2 + MPLS LDP run on every core link throughout
the topic; iBGP is enabled only on the PEs; P1 and P2 never learn BGP.

```
                AS 65100 (SP core, IS-IS L2 + MPLS LDP)

     ┌─────┐                 ┌─────┐                 ┌─────┐
     │ PE1 ├────── L2 ───────┤ P1  ├────── L5 ───────┤ PE2 │
     └──┬──┘                 └──┬──┘                 └──┬──┘
        │                       │                       │
        │                      L4                       │
       L3                       │                      L6
        │                    ┌──┴──┐                    │
        └──────────────────-─┤ P2  ├──────────────-─────┘
                             └─────┘

        │                                               │
       L1                                              L7
        │                                               │
     ┌──┴──┐                                         ┌──┴──┐
     │ CE1 │  AS 65101 customer (optional, lab-02+)  │ CE2 │  AS 65102
     └─────┘                                         └─────┘  (optional)
```

Link summary: L1 CE1↔PE1 (eBGP, lab-02+), L2 PE1↔P1 (IS-IS+LDP), L3
PE1↔P2 (IS-IS+LDP), L4 P1↔P2 (IS-IS+LDP cross — enables RSVP-TE
alternate path), L5 P1↔PE2 (IS-IS+LDP), L6 P2↔PE2 (IS-IS+LDP), L7
CE2↔PE2 (eBGP, lab-02+).

**Key relationships**

- **Diamond core with P1↔P2 cross.** Every PE has two link-disjoint
  IGP paths to the other PE: PE1→P1→PE2 and PE1→P2→PE2. The L4 cross
  between P1 and P2 gives the core a third topological option (e.g.
  PE1→P1→P2→PE2) that RSVP-TE can pin to an explicit path in lab-03
  and that the unused LDP LSP can be steered toward.
- **PE1 and PE2 are the only BGP speakers in the core.** The topic's
  entire arc is "BGP-free core" — P1 and P2 run IS-IS and LDP and
  *nothing else*. They have no BGP configuration, no BGP RIB, no
  knowledge of customer prefixes. This is an invariant, not a lab step.
- **CE1 and CE2 are optional, booting only at lab-02.** Lab-00 and
  lab-01 work entirely within the core (LDP between PE and P routers,
  LSPs between PE loopbacks) — no customer prefixes are needed to
  teach label distribution, LIB/LFIB inspection, or MPLS OAM. CEs join
  at lab-02 when the lesson shifts to "BGP-free core carries customer
  traffic on labels."
- **IS-IS NET discriminator 49.0001.** All four core routers are in
  IS-IS area 49.0001, level-2 only, matching the `fast-convergence`
  topology convention.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-ldp-foundations | MPLS LDP Foundations and Label Distribution | Foundation | 75m | progressive | 4.1, 4.1.a | PE1, P1, P2, PE2 |
| 01 | lab-01-lsp-verification-and-troubleshooting | LSP Verification with MPLS OAM | Intermediate | 75m | progressive | 4.1.b | PE1, P1, P2, PE2 |
| 02 | lab-02-bgp-free-core-and-unified-bgp | BGP-Free Core and Unified BGP (Labeled Unicast) | Intermediate | 90m | progressive | 4.1.c, 4.1.d | PE1, P1, P2, PE2, CE1, CE2 |
| 03 | lab-03-rsvp-te-tunnels | RSVP-TE Tunnels with Explicit Paths | Intermediate | 90m | progressive | 4.1.e | PE1, P1, P2, PE2, CE1, CE2 |
| 04 | lab-04-capstone-config | MPLS Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 05 | lab-05-capstone-troubleshooting | MPLS Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Bullet | Description | Covered In |
|--------|-------------|------------|
| 4.1 | Troubleshoot MPLS (umbrella) | lab-00 through lab-05 |
| 4.1.a | LDP session, discovery, bindings, LIB/LFIB | lab-00 (primary), lab-01, lab-04, lab-05 |
| 4.1.b | LSP verification (mpls ping/traceroute, PHP, MTU) | lab-01 (primary), lab-04, lab-05 |
| 4.1.c | Unified BGP (BGP labeled-unicast, `send-label`) | lab-02 (primary), lab-04, lab-05 |
| 4.1.d | BGP-free core (P routers have no BGP) | lab-02 (primary), lab-04, lab-05 |
| 4.1.e | RSVP-TE tunnels (dynamic + explicit path) | lab-03 (primary), lab-04, lab-05 |

Every blueprint bullet has a dedicated primary lab; capstones exercise
every bullet again end-to-end.

## Design Decisions

- **Six labs (matches topic-plan estimate of 6).** One primary lab per
  blueprint bullet, with 4.1.c (Unified BGP) and 4.1.d (BGP-free core)
  co-located in lab-02 because they describe the *same architecture*
  from two angles — the PE-only control plane (4.1.d) is what makes
  BGP-LU (4.1.c) necessary and interesting. Splitting them would
  duplicate setup and fragment the teaching point.
- **IS-IS L2 as the sole IGP.** Consistent with `fast-convergence` and
  SP-native practice. MPLS is protocol-agnostic, but running a single
  IGP across the topic keeps the student focused on the label plane
  rather than mediating between OSPF and IS-IS. IOSv 15.9 supports
  IS-IS with MPLS-TE extensions natively.
- **All IOSv — no heavy XRv/CSR.** IOSv 15.9(3)M6 supports LDP
  (platform + interface mode), MP-BGP with `send-label`, and MPLS
  traffic engineering with RSVP signaling, which is every feature the
  blueprint lists. Six IOSv nodes fit in 3 GB RAM total; no XRv/CSR
  boot latency is incurred. Students who want IOS-XR production parity
  can re-run on XRv9k later, but it is not required for exam coverage.
- **Diamond core + P1↔P2 cross (L4).** A straight PE1-P1-PE2 chain
  would have only one LSP and no alternate, making RSVP-TE
  uninteresting (explicit paths would need to traverse the same hops).
  The four-router diamond with the P1↔P2 cross gives three distinct
  paths between PE1 and PE2 (via P1, via P2, or via P1→P2) — enough
  for RSVP-TE to demonstrate dynamic CSPF vs explicit path, and for
  LDP LSPs to differ from TE-signaled LSPs.
- **CE1/CE2 optional, booting at lab-02.** Lab-00 and lab-01 teach the
  pure label plane (LDP sessions, LIB/LFIB, LSP OAM) using PE loopbacks
  as the only traffic destinations — no customer traffic is needed.
  Deferring CE boot keeps early labs at 4 nodes / 2 GB RAM. When the
  topic shifts to "labels carry *someone else's* traffic" (BGP-LU +
  BGP-free core), the CEs join and announce customer prefixes.
- **iBGP between PE1 and PE2 only — P routers are BGP-free by design.**
  The `bgp-free core` concept is the *entire* point of lab-02; making
  it an invariant of the topology (not a lab-step to add) forces the
  teaching to be about *why* it works (labels replace BGP next-hop
  lookups in the core), not about configuring it. Lab-02 demonstrates
  reachability from CE1 to CE2 through a P-core that has no knowledge
  of either customer prefix — the "aha" moment.
- **RSVP-TE with IS-IS TE extensions (not OSPF-TE).** Since the IGP is
  IS-IS, TE flooding uses IS-IS sub-TLVs 22 (Extended IS Reachability)
  and 135 (Extended IP Reachability). IOSv supports these natively
  under `router isis` with `mpls traffic-eng level-2`.
- **Progressive chain is strict: only add config between labs.** LDP
  from lab-00 stays on through lab-03. iBGP and eBGP from lab-02 stay
  on. RSVP-TE tunnels from lab-03 stay up. By lab-03 the topology has
  the full SP MPLS stack active — which is exactly the end-state the
  capstones test against a clean_slate restart.
