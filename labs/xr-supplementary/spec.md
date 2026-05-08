# IOS XR Supplementary — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint:** This is a supplementary topic. It does not map to a single
  blueprint section; instead it builds **IOS XR platform fluency** that
  reinforces every section already covered in the IOSv-native topics
  (BGP, OSPF, IS-IS, MPLS, BGP-dual-CE patterns).

> **Why this topic exists.** The project's primary lab corpus uses IOSv for
> exam coverage. IOSv is sufficient for protocol behavior but does not exercise
> IOS XR's distinct platform model — process-based architecture, two-stage
> commit, route-policy language (RPL), prefix-sets, XR-specific operational
> tooling. Topics that are inherently XR-only (`segment-routing`, `srv6`,
> `routing-policy`) already use XR platforms natively and are **not duplicated
> here**. This topic covers XR fluency for the IOSv-native technologies, plus
> standalone XR platform basics.

## Topic Structure

This topic is **not** a standard progressive chain. It has two halves:

1. **Basics labs (00–03)** — share a small dedicated topology focused on
   platform concepts. Each basics lab introduces XR features alongside their
   IOS equivalents using a side-by-side documentation pattern (see Design
   Decisions). Labs 00–03 are progressive: lab-N inherits lab-(N-1)'s configs.
2. **Capstone-XR labs (04–07)** — each is a self-contained capstone that
   **inherits its topology from the corresponding IOSv-native technology
   capstone**, with all routers translated to IOS XR. These do not chain from
   the basics labs; they are independent end-to-end scenarios.

This shape is unusual for the project (every other topic is a single
progressive chain inside one fixed topology). It is justified because:

- The basics labs need a small, focused topology that doesn't waste cycles
  on protocol setup before the platform lessons begin.
- The capstone-XR labs are most valuable when they replicate the *exact
  scenario* a learner already solved in IOSv — so the cognitive work is
  XR translation, not new topology comprehension.

## Basics Topology (Labs 00–03)

```
              ┌──────────────┐                  ┌──────────────┐
              │     XR1      │       L1         │     XR2      │
              │  10.0.0.1/32 ├──────────────────┤  10.0.0.2/32 │
              │  XRv-light   │  10.10.1.0/30    │  XRv-light   │
              │  IS-IS L2    │                  │  IS-IS L2    │
              │  NET ...0001 │                  │  NET ...0002 │
              └──────┬───────┘                  └──────────────┘
                     │ L2  (mgmt-eq side-channel)
                     │      10.10.2.0/30
              ┌──────┴───────┐
              │     R-IOS    │
              │  10.0.0.3/32 │     IOSv reference node — runs the IOS
              │     IOSv     │     equivalent commands shown side-by-side
              │  IS-IS L2    │     with XR1/XR2 throughout the basics labs
              │ NET ...0003  │
              └──────────────┘
```

Three nodes total: **XR1**, **XR2** (both IOS-XRv 6.1.x light, ~4 GB each),
and **R-IOS** (IOSv, ~1.5 GB). Total memory footprint ≈ 9.5 GB. This is
small enough to coexist with another lab on most hosts.

The IS-IS L2 adjacency between XR1 and XR2 is the working network.
**R-IOS** is a parallel reference node — it does not exchange routes with
XR1/XR2 in lab-00; from lab-01 onward it joins the IS-IS L2 area so learners
can compare interface, IGP, and BGP state on both platforms in real time.

| Link | Endpoints                          | Subnet            | Purpose                                  |
| ---- | ---------------------------------- | ----------------- | ---------------------------------------- |
| L1   | XR1:Gi0/0/0/0 ↔ XR2:Gi0/0/0/0      | 10.10.1.0/30      | IS-IS L2 adjacency (primary working net) |
| L2   | XR1:Gi0/0/0/1 ↔ R-IOS:Gi0/0        | 10.10.2.0/30      | IS-IS L2 adjacency from lab-01 onward    |

## Capstone-XR Topologies (Labs 04–07)

Each capstone-XR lab inherits its topology from the source capstone listed
below, with **all routers translated to IOS-XRv (6.1.x light unless noted)**.
Initial configs and solutions are re-derived in XR syntax; the topology
shape, addressing plan, and scenario goals are preserved verbatim.

| XR Lab | Source Capstone                              | Source Nodes | XR Image     | Mem (GB) |
| ------ | -------------------------------------------- | ------------ | ------------ | -------- |
| 04     | `bgp/lab-07-capstone-config`                  | R1–R7 (7)    | XRv-light    | ~28      |
| 05     | `ospf/lab-04-capstone-config`                 | R1–R6 (6)    | XRv-light    | ~24      |
| 06     | `isis/lab-03-capstone-config` (TBD; see note) | TBD          | XRv-light    | ~20-24   |
| 07     | `mpls/lab-04-capstone-config`                 | PE1, P1, P2, PE2, CE1, CE2 (6) | XRv-light | ~24 |

> **Note on lab-06 (IS-IS-XR).** `isis/lab-03-capstone-config` is currently
> a scaffolded but **unbuilt** folder. Two options at build time: (a) wait
> until the IOSv IS-IS capstone is built and mirror it; (b) define a
> standalone XR IS-IS scenario directly, using `isis/lab-02-dual-stack-summarization`
> as the topology reference. Decision deferred to lab-06 build kickoff.

> **Memory caveat.** lab-04 (BGP-XR) is the largest at ~28 GB. On a host with
> < 32 GB usable RAM, the BGP-XR topology may need reduction (drop R7 or
> consolidate two CEs). This decision is deferred to lab-04 build kickoff —
> no reduction is mandated at the spec level.

## Lab Progression

| #  | Folder                              | Title                                       | Difficulty   | Time | Type             | Topology Source                 |
| -- | ----------------------------------- | ------------------------------------------- | ------------ | ---- | ---------------- | ------------------------------- |
| 00 | lab-00-platform-basics              | XR Platform Basics                          | Foundation   | 60m  | progressive      | basics topology                 |
| 01 | lab-01-config-foundations           | Config Foundations + IOS↔XR Reference       | Foundation   | 75m  | progressive      | basics topology                 |
| 02 | lab-02-routing-policy-language      | Route-Policy Language (RPL) and Prefix-Sets | Intermediate | 90m  | progressive      | basics topology                 |
| 03 | lab-03-ops-and-troubleshooting      | XR Operations and Troubleshooting           | Intermediate | 75m  | progressive      | basics topology                 |
| 04 | lab-04-bgp-capstone-xr              | BGP Comprehensive — XR Capstone             | Advanced     | 150m | capstone_i       | bgp/lab-07-capstone-config      |
| 05 | lab-05-ospf-capstone-xr             | OSPF Multi-Area + Stub Variants — XR        | Advanced     | 120m | capstone_i       | ospf/lab-04-capstone-config     |
| 06 | lab-06-isis-capstone-xr             | IS-IS Dual-Stack + Summarization — XR       | Advanced     | 120m | capstone_i       | isis/lab-03 (TBD)               |
| 07 | lab-07-mpls-capstone-xr             | MPLS LDP + RSVP-TE + L3VPN — XR             | Advanced     | 150m | capstone_i       | mpls/lab-04-capstone-config     |

## Lab Objectives Summary

### lab-00 — XR Platform Basics

- Boot XRv-light, identify XR process model (sysadmin vs XR plane, key processes)
- Use admin mode for chassis-level vs router config-mode for routing
- Two-stage commit: `commit`, `commit confirmed`, `commit replace`, `rollback`
- Compare with IOS write-memory single-stage save (R-IOS reference)
- Inspect installed packages, software state, and process health
- IOS↔XR command map: `show version`, `show inventory`, `show platform`,
  `show running-config`, basic CLI navigation differences
- Side-by-side: copy/paste IOS config to XR, observe what fails and why

### lab-01 — Config Foundations + IOS↔XR Reference

- Interface naming model: `GigabitEthernet0/0/0/0` and what each digit means
- IPv4/IPv6 addressing on XR (inline form vs. address-family blocks)
- Loopback configuration; admin-state semantics (`shutdown` vs `no shutdown`)
- IS-IS L2 bring-up between XR1 ↔ XR2 ↔ R-IOS (mixed-platform adjacency)
- AAA local users; SSH server enable; banner; hostname
- Management plane: `MgmtEth0/RP0/CPU0/0` (XR) vs `interface Mgmt0` (IOS)
- Side-by-side appendix: IOS↔XR config primitives table

### lab-02 — Route-Policy Language (RPL) and Prefix-Sets

- `prefix-set` definition; `route-policy` language (if/then/else/done, `apply`)
- Translation patterns: prefix-list → prefix-set, route-map → route-policy
- Use RPL on BGP neighbors to filter, set local-pref, set community,
  prepend AS-path; observe behavior on the XR1↔XR2 BGP session
- Inspect compiled vs source policy; `show rpl route-policy NAME`
- IOS↔XR translation gotchas: implicit deny-all in route-map vs explicit
  drop in RPL; community-set syntax differences; `regex` differences
- Side-by-side appendix: RPL ↔ route-map translation reference

### lab-03 — XR Operations and Troubleshooting

- `show` command structure differences; common pivot commands
- Logging architecture: `show logging`, `logging buffered`, `logging archive`
- Process introspection: `show processes`, `show watchdog`
- Telemetry overview (model-driven, no hands-on streaming — too
  infrastructure-heavy for a lab; conceptual + sample config only)
- `monitor interface`, `monitor traffic interface`, `traceroute`, `ping mpls`
- Troubleshooting workflow: induce a misconfig on XR1 (broken IS-IS net-id,
  invalid RPL apply), diagnose using XR-native tools; compare with how the
  same misconfig would be diagnosed on R-IOS
- Side-by-side appendix: IOS↔XR troubleshooting command map

### lab-04 — BGP Comprehensive — XR Capstone

Inherits the BGP capstone scenario (eBGP/iBGP, route-reflector, dual-CE
multihoming, communities, FlowSpec install) and translates all configuration
to IOS XR. Exercises:

- BGP address-family hierarchy (XR's stricter AF-block model vs IOS)
- Route-policy language for inbound/outbound policy on every neighbor
- Community-sets vs IOS community-lists; extcommunity-set
- BGP RR-client config differences
- Implicit-vs-explicit policy posture (XR's "deny all unless permitted")
- FlowSpec install on XR (if scenario coverage permits with XRv-light;
  otherwise note as XR-specific deferred to xrv9k)

### lab-05 — OSPF Multi-Area + Stub Variants — XR

Inherits the OSPF capstone (multi-area + totally-stubby + NSSA + ASBR
redistribution) and translates to XR. Exercises:

- OSPF area hierarchy in XR (`router ospf` ... `area X` ... `interface ...`)
- Stub/totally-stubby/NSSA semantics on XR (`stub`, `stub no-summary`, `nssa`)
- Redistribution into OSPF using route-policy
- LSA inspection: `show ospf database` differences and richer XR output

### lab-06 — IS-IS Dual-Stack + Summarization — XR

Inherits the IS-IS capstone (multi-level + IPv4/IPv6 dual-stack +
summarization at L1↔L2 boundary) and translates to XR. Exercises:

- IS-IS NET configuration on XR; per-AF advertisement
- Wide metrics (XR default; IOS opt-in)
- Summarization: `summary-prefix` placement and propagation
- Multi-topology vs single-topology behavior

### lab-07 — MPLS LDP + RSVP-TE + L3VPN — XR

Inherits the MPLS capstone (BGP-free core, LDP, RSVP-TE tunnels, BGP-LU
or L3VPN) and translates to XR. Exercises:

- LDP configuration on XR (`mpls ldp` block, no-implicit interface enable)
- RSVP-TE: explicit-paths, tunnels, fast-reroute concepts
- BGP-LU configuration on XR
- L3VPN VRF configuration; VPNv4 route exchange
- Forwarding-plane verification: `show mpls forwarding`,
  `show mpls traffic-eng tunnels`

## Blueprint Coverage Reinforcement

This topic does **not** add net-new blueprint coverage. It reinforces
sections already covered in IOSv-native topics by exercising the same
behavior on a second platform:

| Blueprint Section | Reinforced In        |
| ----------------- | -------------------- |
| 1.x BGP           | lab-04               |
| 2.1 OSPF          | lab-05               |
| 2.2 IS-IS         | lab-06               |
| 3.x MPLS          | lab-07               |
| Cross-cutting     | lab-00, 01, 02, 03   |

## Design Decisions

- **Skip technologies that are already XR.** `segment-routing/`, `srv6/`,
  and `routing-policy/` topics already use XR platforms natively. Building
  XR variants here would duplicate them. The XR-supplementary topic covers
  only the IOSv-native technologies plus standalone platform fluency.

- **One image (XRv-light 6.1.x) for all labs.** xrv9k is overkill for
  these scenarios — the basics labs and the capstone-XR labs cover BGP,
  OSPF, IS-IS, MPLS LDP, RSVP-TE, BGP-LU, L3VPN, none of which require
  xrv9k. XRv-light's ~4 GB-per-node footprint keeps the BGP-XR capstone
  (the largest) at ~28 GB, which is feasible on most lab hosts. SRv6 and
  modern SR-PCE features (which would require xrv9k) are out of scope —
  those live in the SRv6 and segment-routing topics.

- **Side-by-side IOS↔XR coverage uses both inline callouts and an
  appendix.** Inline `> IOS equivalent: <command>` callouts appear next
  to each XR command as it is first introduced (teaches translation in
  context); a consolidated **Appendix A — IOS↔XR Reference Table** at the
  end of every basics workbook indexes the same content as a study
  reference (teaches lookup). The two formats serve different reading
  modes; both are mandatory in the basics labs (00–03). Capstone-XR labs
  (04–07) include the inline callouts where helpful but **do not** repeat
  the appendix — by lab-04 the learner is expected to use the basics
  appendices as their reference.

- **Basics labs share a 3-node topology; capstones inherit from source.**
  Documented at the top of this spec under Topic Structure. The asymmetry
  is intentional and called out in `baseline.yaml` via two distinct
  topology blocks (basics + per-capstone inheritance pointers).

- **Capstone-XR labs are `capstone_i` (config-only).** No troubleshooting
  capstones in this topic. The IOSv-native troubleshooting capstones
  already cover the troubleshooting craft; XR-specific troubleshooting
  diagnostic patterns are introduced in lab-03 and reinforced inline
  during lab-04 through lab-07.

- **R-IOS reference node in basics labs.** Including a single IOSv router
  as a parallel reference inside the same lab is unconventional but
  pedagogically essential for this topic — it lets learners run the IOS
  command on R-IOS and the XR command on XR1 in the same `console`
  workflow, observing the side-by-side comparison directly rather than
  reading about it.

- **Memory budget escape hatch on lab-04.** If host memory is tight,
  lab-04 (BGP-XR, ~28 GB) may have its topology reduced at build time —
  drop R7 and one CE to save ~8 GB. The reduction is allowed but not
  mandated; the build-kickoff conversation determines it based on the
  user's actual host.

- **Branch policy for this topic.** Per `BRANCHING.md`, this topic is
  built on `master` because the basics labs (00–03) are clearly shipping
  regardless of how the capstones go. If lab-04 (BGP-XR) hits memory
  trouble, the *topology reduction* for that single lab can be done on a
  short-lived `experiment/` branch — not the whole topic.
