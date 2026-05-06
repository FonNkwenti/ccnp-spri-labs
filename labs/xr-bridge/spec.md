# XR Bridge — Lab Specification (build deferred)

> **Status:** Spec-only. **Build is deferred** — see
> `memory/xr-coverage-policy.md` §2 (`Bridge` posture). This topic exists as a
> bonus self-study track for students who want IOS-XR fluency beyond what the
> retrofitted capstones in topics 1-8 provide. It is not required for the
> 300-510 exam and is not on the project's main build path.

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets covered (re-tread on XR):**
  - **1.1.a** OSPFv2/v3 — re-treated on XR
  - **1.3.a** IS-IS L1/L2 — re-treated on XR
  - **1.5.a-d** BGP (peering, RR, confederations, attributes) — re-treated on XR
  - **1.6.c** IPv6 Provider Edge (6PE) — **primary coverage** (deferred from
    `ipv6-transition` per that topic's posture).
  - **1.7.b/c** NSF and NSR — XR-side reinforcement of `fast-convergence`.
  - **4.1.a-e** MPLS (LDP, LSP, BGP-LU, BGP-free core, RSVP-TE) — re-treated.

> This topic is the "second tour" of the protocol stack on a pure-XR platform.
> Students who completed topics 1-8 with the XR-mixed capstones already have
> XR exposure on these bullets; this topic is for candidates who want the
> XR-native workflow (config commits, two-stage commit model, route-policy
> language end-to-end, `show` command surface) drilled separately.

## Topology Summary

Six-router lab built from the project's three available platforms in the
proportions the policy doc mandates: **4× IOS XRv (light)** as the SP core,
**1× IOS-XRv 9000** as the feature-rich PE/RR (carries 6PE, anything that
plain XRv refuses), and **1× IOSv** as a customer/translation reference so
the student can put XR CLI side-by-side with classic IOS at lab time.

```
                       AS 65100 (SP core, IS-IS L2 + LDP)

       ┌────────┐                                  ┌────────┐
       │  XR1   ├────────── L1 ────────────────────┤  XR2   │
       │  XRv   │                                  │  XRv   │
       │ 10.0.1 │                                  │ 10.0.2 │
       └───┬────┘                                  └───┬────┘
           │                                           │
           L3                                          L4
           │                                           │
       ┌───┴────┐                                  ┌───┴────┐
       │  XR3   ├────────── L2 ────────────────────┤ XR9k   │
       │  XRv   │                                  │ XRv9k  │
       │ 10.0.3 │                                  │ 10.0.4 │
       └────────┘                                  └───┬────┘
                                                       │
                                                      L5 (eBGP, lab-02+)
                                                       │
                                                  ┌────┴────┐
                                                  │  IOS    │
                                                  │  iosv   │  AS 65200
                                                  │ 10.0.5  │
                                                  └─────────┘
       [Optional, lab-04+]
       ┌────────┐
       │  XR5   │  4th XRv, multicast PIM-SM source-side
       │  XRv   │  joins via L6 to XR1
       │ 10.0.6 │
       └────────┘
```

**Link summary:** L1 XR1↔XR2 (IS-IS+LDP), L2 XR3↔XR9k (IS-IS+LDP), L3 XR1↔XR3
(IS-IS+LDP), L4 XR2↔XR9k (IS-IS+LDP), L5 XR9k↔IOS (eBGP, lab-02+), L6 XR1↔XR5
(IS-IS, lab-04+ multicast only).

**Key relationships**

- The **diamond core** (XR1-XR2-XR9k-XR3) gives every PE pair two link-disjoint
  IGP paths — required for the LFA/TI-LFA work in lab-05 and for RSVP-TE
  alternates in lab-03. Same shape as `mpls` and `segment-routing` on purpose:
  topology familiarity lets the student focus on XR CLI differences, not on
  remembering which router is where.
- **XR9k is the feature anchor.** Plain XRv lacks 6PE, EVPN, advanced multicast
  features, and SRv6 — all anything that needs the heavier image lands on XR9k.
  This also lets a single lab compare the two XR images' feature surfaces, which
  is a real CCIE SP exam-room consideration.
- **IOS is the translation reference, not the customer.** Lab-02 brings up an
  IOSv eBGP peer to give the student an IOS-side view of attributes, communities,
  and route-maps that round-trip across an XR PE — this is the literal
  "translation" lesson of the bridge topic. The IOSv node never runs anything
  the SP core depends on.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-xr-cli-and-commit-model | IOS-XR CLI, Commit Model, and Config Groups | Foundation | 60m | progressive | (workflow) | XR1, XR2, XR3, XR9k |
| 01 | lab-01-xr-bgp-and-policy | XR BGP — RR, Confederations, RPL End-to-End | Intermediate | 90m | progressive | 1.5.a-d, 3.1, 3.2.d, 3.2.j | XR1, XR2, XR3, XR9k, IOS |
| 02 | lab-02-xr-mpls-stack | XR MPLS — LDP, BGP-LU, BGP-free Core, RSVP-TE | Intermediate | 90m | progressive | 4.1.a-e | XR1, XR2, XR3, XR9k, IOS |
| 03 | lab-03-xr-6pe | XR 6PE — IPv6 over MPLS | Intermediate | 75m | progressive | 1.6.c | XR1, XR2, XR3, XR9k, IOS |
| 04 | lab-04-xr-multicast | XR Multicast — PIM-SM and mLDP on XR | Intermediate | 90m | progressive | 2.x re-tread | XR1, XR2, XR3, XR9k, XR5 |
| 05 | lab-05-xr-convergence | XR Convergence — TI-LFA, BFD, NSR, GR | Intermediate | 90m | progressive | 1.7.b, 1.7.c | all |

No capstones. The whole topic is itself a capstone-style review of topics 1-8
on XR; adding an exam-style capstone on top would be redundant.

## Blueprint Coverage Matrix

| Bullet | Description | Covered In | XR Exercised? |
|---|---|---|---|
| 1.1.a | OSPFv2/v3 | lab-00 (IGP brought up under XR for context) | yes — re-tread |
| 1.3.a | IS-IS L1/L2 | lab-00 (primary IGP for the topic), lab-02, lab-04 | yes — primary |
| 1.5.a-d | BGP (peering, RR, confederations, attributes) | lab-01 (primary) | yes — primary |
| 1.6.c | IPv6 Provider Edge (6PE) | lab-03 (primary) | yes — primary (deferred from `ipv6-transition`) |
| 1.7.b | NSF | lab-05 | yes — primary |
| 1.7.c | NSR | lab-05 | yes — primary |
| 4.1.a | LDP | lab-02 (primary) | yes — re-tread |
| 4.1.b | LSP verification | lab-02 | yes — re-tread |
| 4.1.c | BGP-LU | lab-02 | yes — re-tread |
| 4.1.d | BGP-free core | lab-02 | yes — re-tread |
| 4.1.e | RSVP-TE tunnels | lab-02 | yes — re-tread |
| 2.x | Multicast (PIM-SM, mLDP, BSR) | lab-04 | yes — re-tread |

## Design Decisions

- **XR Coverage Posture: `Bridge`** (per `memory/xr-coverage-policy.md`). This
  is the sole topic in the project that uses the Bridge posture — it exists
  to give CCIE SP precursor candidates a self-contained second pass over the
  protocol stack on XR. **Build is deferred:** the spec, topology, and lab
  outline are documented here so a future contributor (or the same student
  later in their CCIE SP track) can pick it up without re-doing the design
  work.

- **6 labs, no capstones.** The entire topic is a re-tread of capstone-level
  material from topics 1-8 — adding a capstone on top would be a re-tread of
  a re-tread. Lab-05 (convergence) is the de-facto end-of-topic exam since
  it touches every protocol the topic has built up.

- **Platform mix: 4× IOS XRv + 1× XRv 9000 + 1× IOSv (~28 GB peak).**
  Matches the policy doc's platform-selection rule: use XRv for everything
  it can do (IS-IS, BGP, LDP, RSVP-TE, basic multicast) and reserve XRv 9000
  for what XRv refuses (6PE in lab-03 needs it on the PE; advanced multicast
  features in lab-04 prefer it). The single IOSv is a translation reference,
  not a feature dependency. Total RAM peak ≈ 4×3 + 1×16 + 1×0.5 = 28.5 GB,
  well within the 64 GB host.

- **Diamond core, same shape as `mpls`/`segment-routing`.** Topology
  familiarity is a feature: the student is not learning a new physical
  layout, only new CLI on the same wires. The L1-L4 link IDs even match
  the `mpls` topic's so a side-by-side comparison reads cleanly.

- **6PE is *primary* coverage here.** `ipv6-transition` left 1.6.c
  intentionally on the table (per its IOSv-only posture) and pointed
  students at this topic. Lab-03 is the only place in the entire project
  where 6PE is actually built and run.

- **NSR is primary coverage here too.** `fast-convergence` retrofits NSF/NSR
  into its capstones, but the *primary* teaching of NSR-the-feature is
  here in lab-05, where the XR9k node carries dual-RP-style behavior
  (XRv 9000 emulates the multi-RP architecture closely enough for the
  control-plane lesson; data-plane non-stop forwarding is observable but
  not benchmarkable on virtual hardware).

- **No clean_slate variant defined.** Because every lab here is itself a
  review of an exam topic, the progressive chain is the entire point — a
  clean_slate option would just re-create the same bring-up the student
  already did once in topic 1-8.

- **Build is deferred — but the spec is concrete.** This file is written
  to the same standard as the other 11 topic specs (link IDs, exact
  blueprint coverage, platform RAM math) so that picking it up later is
  a build job, not a re-design job.
