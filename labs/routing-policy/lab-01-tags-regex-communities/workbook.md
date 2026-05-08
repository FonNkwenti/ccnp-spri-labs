# Lab 01 — Tags, Route Types, Regex, and BGP Communities

**Topic:** Routing Policy and Manipulation | **Exam:** 300-510 SPRI | **Time:** 75 min | **Difficulty:** Foundation

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Core Implementation](#5-lab-challenge-core-implementation)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)
11. [Appendix: Script Exit Codes](#11-appendix-script-exit-codes)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 3.2.c (route tags), 3.2.e (route-type matching), 3.2.h (AS-path regex), 3.2.i (BGP communities)

This lab extends the route-map foundation from Lab 00 into four advanced matching and classification tools used in real SP environments: route tags for redistribution loop prevention, route-type matching to distinguish OSPF/IS-IS route classes during redistribution, AS-path regular expressions to scope BGP policy to specific neighbor ASes, and BGP communities for structured route signalling across iBGP speakers. Every concept here addresses a specific failure mode that is silent without the right verification commands.

### Route Tags and Redistribution Loop Prevention

When two routing protocols are redistributed into each other (mutual redistribution), a route can bounce indefinitely: OSPF → IS-IS → OSPF → IS-IS. IOS does not detect this automatically. Tags are a 32-bit integer stamped on a route by one `set tag` clause and matched by `match tag` on the other side.

The standard two-router, two-protocol loop prevention pattern:

```
                  OSPF ←──────────────────────────── IS-IS
                                (tag 200)
R2 ──┤ redistributes with set tag ├── R3 ──┤ denies match tag ├──
                  OSPF ───────────────────────────→ IS-IS
                                (tag 100)
```

Tags must be stamped **at redistribution** using `set tag` in the route-map and denied **on the receiving side** using `match tag` in the opposing route-map's deny sequence.

| Tag | Meaning | Set by | Denied by |
|-----|---------|--------|-----------|
| 100 | Originated in OSPF | OSPF→IS-IS maps on R2 and R3 | IS-IS→OSPF deny on R3 |
| 200 | Originated in IS-IS | IS-IS→OSPF maps on R2 and R3 | OSPF→IS-IS deny on R3 |

> **Reference document:** For a deeper walkthrough of the tag-based loop prevention design — including step-by-step traces of both loop directions, the tag state machine, and diagnosis of failed loop prevention — see [`docs/tag-based-loop-prevention.md`](docs/tag-based-loop-prevention.md).

### Route-Type Matching

`match route-type` lets you distinguish how a route entered the routing table. In OSPF, this is critical when redistributing into IS-IS because IS-IS has no concept of external/internal — all redistributed routes are IS-IS external — so the differentiation must happen before they cross the protocol boundary.

| `match route-type` value | Matches |
|--------------------------|---------|
| `internal` | OSPF intra-area (O) and inter-area (O IA) |
| `external type-1` | OSPF external E1 — metric includes internal cost |
| `external type-2` | OSPF external E2 — metric ignores internal cost (default for `redistribute`) |
| `local` | Routes sourced on this router (connected/static fed into protocol) |

**Exam trap:** `redistribute ospf 1` into IS-IS on a router that has both E1 and E2 routes: if your route-map only matches `external type-2`, the E1 routes silently fall through to the implicit deny and are dropped. Always cover all three classes.

### AS-Path Regular Expressions

Cisco IOS AS-path ACLs use POSIX-style regex with one special token: `_` (underscore), which matches any of: a space, the start of string, or the end of string.

| Pattern | Meaning | Example match |
|---------|---------|--------------|
| `^$` | Empty AS-path (locally originated) | iBGP routes with no external AS-path |
| `_65200$` | 65200 is the last (rightmost) AS | Routes from a single-hop AS 65200 peer |
| `_65200_` | 65200 appears anywhere with separators | Routes transiting through AS 65200 |
| `^65200_` | AS-path starts with 65200 | Routes directly received from 65200 |
| `.*` | Any AS-path | All external routes (highly over-permissive) |

**Critical distinction:** `_65200$` vs `_65200_` are equivalent in a leaf topology (AS 65200 is always the last AS), but diverge in production when AS 65200 is a transit AS in the middle of a longer path. Always use `_65200$` when you mean "originated in AS 65200."

### BGP Communities

A BGP community is a 32-bit attribute carried in BGP UPDATE messages. The convention is `ASN:value` (e.g., 65100:100). Communities survive iBGP propagation only if **`send-community both`** is configured on the peer — IOS strips communities by default.

**Well-known communities** (recognized by all BGP implementations):

| Community | Effect |
|-----------|--------|
| `no-export` | Do not advertise beyond the local AS (or confederation) |
| `no-advertise` | Do not advertise to any BGP peer |
| `local-as` | Do not advertise outside the local sub-AS (confederation use) |
| `internet` | Default: advertise to all peers |

**Community lists:**

| Type | Syntax | Use |
|------|--------|-----|
| standard | `ip community-list standard NAME permit ASN:value` | Exact match |
| expanded | `ip community-list expanded NAME permit regex` | Regex match (e.g., `65100:1[0-9][0-9]`) |

Expanded community lists apply Cisco IOS regex to the community string. The pattern `65100:1[0-9][0-9]` matches any 65100:1xx community (100–199).

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Redistribution loop prevention | Two-router, two-protocol tagging + deny pattern |
| Route-type classification | Matching E1, E2, and internal OSPF types in `match route-type` |
| AS-path scoping | Writing `_ASN$` anchored regex for leaf-AS filtering |
| Community marking | Setting communities inbound from eBGP peers; verifying propagation |
| Community matching | Standard and expanded community-list matching |
| Well-known community semantics | Applying no-export/no-advertise and observing neighbor table changes |

---

## 2. Topology & Scenario

Your SP team runs AS 65100 across three routers (R1, R2, R3). Both OSPF and IS-IS are active on the core links — the SP uses OSPF as the primary IGP and IS-IS as a backup, and both redistribute into each other on R2 and R3. A route-filtering incident last quarter proved that uncontrolled mutual redistribution caused routing loops. Your task is to retrofit the redistribution with tag-based loop prevention.

**The two-router design philosophy:** Redistribution runs on both R2 and R3, but they have **different roles**:

- **R2 is the "tagger only"** — it stamps tags on routes as they cross from one protocol to the other, but applies no filtering. Its route-maps permit all route types and set a tag value so the origin protocol is identifiable downstream.
- **R3 is the "loop protector"** — it also redistributes both ways, but adds a deny sequence at the top of each route-map that matches the tag from the *opposite direction*. This prevents a route that was just redistributed out of OSPF (tag 100) from being picked up by IS-IS→OSPF and sent back into OSPF, and vice versa.

The key insight: the deny sequence must go on the **receiving side** of the loop — the router that could pull a route back into the protocol it just left. With redistribution on two routers, this means R3 is the designated break point. If both routers simply stamped tags without blocking, a route could bounce: OSPF → IS-IS (tag 100 on R2) → OSPF (tag 200 on R3) → IS-IS (tag 100 on R2) → … indefinitely.

Separately, R4 (AS 65200) has dual eBGP sessions to R1 and R3. The network team wants to classify R4's prefixes with BGP communities at entry — `65100:100` on R1's side and `65100:200` on R3's side — so that downstream policy can reference the community value rather than re-applying prefix-list matches at every iBGP speaker.

```
                    ┌──────────────────────────┐
                    │            R4            │
                    │        AS 65200          │
                    │   Lo0: 10.0.0.4/32       │
                    │   Lo1: 172.20.4.1/24     │
                    │   Lo2: 172.20.5.1/24     │
                    └────┬──────────────┬──────┘
                         │              │
         L4 10.1.14.0/24 │              │ L3 10.1.34.0/24
         eBGP R1↔R4      │              │ eBGP R3↔R4
                         │              │
          ┌──────────────┘              └──────────────┐
          │                                            │
┌─────────┴───────────────┐            ┌──────────────┴──────────┐
│           R1            │            │            R3            │
│     AS 65100 eBGP edge  ├────────────┤   AS 65100 eBGP edge    │
│   Lo0: 10.0.0.1/32      │ L5         │   Lo0: 10.0.0.3/32      │
│   Lo1: 172.16.1.1/24    │ 10.1.13.0  │                         │
└───────────┬─────────────┘ /24        └────────────┬────────────┘
            │ L1 10.1.12.0/24                        │ L2 10.1.23.0/24
            │ R1-R2                                  │ R2-R3
            │              ┌──────────────────────┐  │
            └──────────────┤          R2          ├──┘
                           │   AS 65100 core      │
                           │   Lo0: 10.0.0.2/32   │
                           └──────────────────────┘
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP core / eBGP edge (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | SP core transit (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | SP core / eBGP edge (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | External AS edge (AS 65200) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP peering source |
| R1 | Loopback1 | 172.16.1.1/24 | Customer prefix advertised into BGP |
| R1 | Loopback10 | 10.200.0.1/32 | IS-IS-only demonstration prefix (not in OSPF) |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source |
| R2 | Loopback10 | 10.200.0.2/32 | IS-IS-only demonstration prefix (not in OSPF) |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source |
| R3 | Loopback10 | 10.200.0.3/32 | IS-IS-only demonstration prefix (not in OSPF) |
| R4 | Loopback0 | 10.0.0.4/32 | Management/router ID |
| R4 | Loopback1 | 172.20.4.1/24 | External prefix advertised to AS 65100 |
| R4 | Loopback2 | 172.20.5.1/24 | Second external prefix (filter target on R1) |

### Cabling

| Link | Source | Destination | Subnet | Purpose |
|------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | SP core (OSPF, IS-IS, iBGP) |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | SP core (OSPF, IS-IS, iBGP) |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | eBGP R3↔R4 |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | eBGP R1↔R4 |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | SP core diagonal (OSPF, IS-IS, iBGP) |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | BGP network | AS 65100 customer aggregate |
| R4 | 172.20.4.0/24 | BGP network | AS 65200 Lo1 — accepted by R1 (permit seq 20) |
| R4 | 172.20.5.0/24 | BGP network | AS 65200 Lo2 — denied by R1 (deny seq 10) |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames and `no ip domain-lookup`
- Interface IP addressing (all routed links and loopbacks)
- OSPF area 0 on all three SP core links and Loopback0 interfaces
- IS-IS level-2-only process SP (wide metrics, point-to-point network type)
- **Loopback10 on R1, R2, R3** — `ip router isis SP` only, NOT in OSPF. These IS-IS-only prefixes (10.200.0.x/32) give IS-IS unique routes to win the RIB and verify IS-IS→OSPF redistribution with tag 200. They exist because OSPF (AD 110) and IS-IS (AD 115) share all core links, so IS-IS never wins the RIB for shared prefixes.
- BGP AS 65100 full-mesh iBGP among R1, R2, R3 with `update-source Loopback0`
- eBGP sessions R1↔R4 and R3↔R4 (AS 65200)
- R1 `FILTER_R4_IN` route-map denying 172.20.5.0/24 inbound from R4
- All prefix-lists and ACLs from lab-00 (PFX_R4_LE_24, PFX_R4_LO2_EXACT, ACL_EXT_R4_LO2)
- Demo route-maps from lab-00 (DEMO_CONTINUE, DEMO_REDIST) — not applied
- R1 `DEMO_WELL_KNOWN` route-map — matches `PFX_R4_LE_24` and sets community `no-export`; not applied (used in Task 7)

**IS NOT pre-loaded** (student configures this):

- R1 `redistribute connected metric-type 1 subnets` under `router ospf 1` (prerequisite E1 route source for route-type demonstrations)
- OSPF↔IS-IS mutual redistribution on R2 and R3
- Route tags on redistribution route-maps (tag 100 for OSPF→IS-IS, tag 200 for IS-IS→OSPF)
- Route-type matching clauses in redistribution route-maps (external type-1, type-2, internal)
- Loop-prevention deny sequences on R3
- AS-path access-list and inbound route-map on R3's eBGP session to R4
- Community assignments on R1 and R3 inbound from R4
- `send-community both` on all iBGP peer groups
- Community-list definitions on all three SP routers

---

## 5. Lab Challenge: Core Implementation

> **Reference:** If you find the tag flow or the two-router division of labour confusing, read [`docs/tag-based-loop-prevention.md`](docs/tag-based-loop-prevention.md) *before* starting the tasks below. It contains full traces of both loop directions with ASCII art, a tag state machine, and verification commands.

### Task 1: Redistribute OSPF into IS-IS on R2 (with tagging)

**Prerequisite — create OSPF E1 routes on R1:** The `match route-type external type-1` sequence in `OSPF_TO_ISIS` needs at least one OSPF E1 route in the domain so that you can verify tag 100 appears on an E1 prefix in R2's IS-IS LSP.

- On R1, add `redistribute connected metric-type 1 subnets` under `router ospf 1`. This injects R1's directly connected interfaces (Lo1 172.16.1.0/24 and Gi0/1 10.1.14.0/24) into OSPF as E1 routes — metric-type 1 means the OSPF cost accumulates across links as the route propagates.
- Confirm: `show ip route ospf` on R2 must list 172.16.1.0/24 and 10.1.14.0/24 as `O E1` before you proceed to the redistribution tasks.

**R2 redistribution — the "tagger only":**

R2 is the simplest of the two redistribution routers. Its job is purely additive: stamp the origin protocol's tag on every route that crosses the boundary. Because R2 never denies anything, it creates no path asymmetry — both OSPF→IS-IS and IS-IS→OSPF flows pass through freely. The tag itself (100 for OSPF, 200 for IS-IS) does not prevent loops on R2; it simply marks the route so that R3 (the loop protector) can identify and block it on the return leg.

- Activate bidirectional redistribution between OSPF process 1 and IS-IS process SP.
- For OSPF→IS-IS: create a route-map that covers all three OSPF route types (external type-1, external type-2, and internal). Set tag 100 on every permitted route.
- For IS-IS→OSPF: create a route-map that permits all IS-IS routes. Set tag 200 and set metric 20 on every permitted route.
- Apply both route-maps to the respective redistribution commands. **Do not add any deny sequences on R2** — R2 is the "tagger only." The loop-protection denies will be placed on R3 in Task 2.

**Verification:**

> **Platform note:** `show route-map` "Policy routing matches" is a PBR counter — it is always 0 for redistribution route-maps. Use the IS-IS LSP and OSPF database as the ground truth instead.

- `show isis database R2.00-00 verbose` on R1 must show `Route Admin Tag: 100` beneath each OSPF-redistributed prefix (10.1.14.0/24, 172.16.1.0/24, 10.0.0.1/32, 10.0.0.3/32, 10.200.0.1/32). The `verbose` keyword is required — `detail` hides sub-TLVs. Redistributed prefixes also show `Prefix-attr: X:1` (External bit set).
- `show ip route 10.200.0.3` on R1 must show `Tag 200, type extern 2` — confirming IS-IS→OSPF redistribution from R2 tagged R3's IS-IS-only prefix (10.200.0.3/32) correctly.
- `show ip ospf database external 10.200.0.3` on R2 must show `External Route Tag: 200` and `Metric Type: 2 ... Metric: 20` — the OSPF LSA generated by R2's IS-IS→OSPF redistribution.

> **Why 10.200.0.x prefixes?** OSPF (AD 110) and IS-IS (AD 115) share the same interfaces in this topology, so OSPF wins the RIB for all shared prefixes and the IS-IS routing table stays empty. Loopback10 interfaces (pre-loaded on R1, R2, R3) are IS-IS-only — they give IS-IS unique prefixes that win their RIB entries and are available for IS-IS→OSPF redistribution on R2.

---

### Task 2: Redistribute OSPF into IS-IS on R3 (with loop prevention)

R3's route-maps are structurally identical to R2's, with one critical addition: each map has a **deny sequence at the top** that matches the tag from the opposite direction. This is where the loop stops.

Trace what happens when a route tries to loop:

1. An OSPF route enters IS-IS on R2 — R2 stamps **tag 100** (OSPF origin).
2. R3 redistributes that IS-IS route back into OSPF — but R3's `ISIS_TO_OSPF` has `deny 10 match tag 100`. The route hits the deny before it reaches the permit sequence and is **blocked** from re-entering OSPF.
3. The same logic works in reverse: an IS-IS route redistributed into OSPF on R2 carries **tag 200** (IS-IS origin). R3's `OSPF_TO_ISIS deny 10 match tag 200` blocks it from bouncing back into IS-IS.

The deny thus lives on the **re-entry side** of the loop, one hop after R2's tag was stamped. R2 never blocks anything — it just tags. R3 enforces the gate.

- On R3, activate the same bidirectional redistribution as Task 1.
- For OSPF→IS-IS on R3: add a deny sequence at the top that matches tag 200 (IS-IS-origin marker), then permit the remaining routes by route-type and set tag 100.
- For IS-IS→OSPF on R3: add a deny sequence at the top that matches tag 100 (OSPF-origin marker), then permit the remaining routes and set tag 200 and metric 20.
- Verify that no routing loops form after both routers are redistributing.

**Verification:**

- `show ip route 10.200.0.2` on R1 must show `Tag 200, type extern 2` — R2's IS-IS-only loopback (native IS-IS, no tag 100) redistributed into OSPF by R3 with tag 200. Check on R1, not R3: R3 originated the Type-5 LSA for this prefix and does not install its own redistributed LSA back into its routing table.
- `show isis database R3.00-00 verbose` on R1 must show `Route Admin Tag: 100` on redistributed OSPF prefixes and `Prefix-attr: X:0` with NO tag on native IS-IS prefixes (10.200.0.3/32). This confirms R3's `OSPF_TO_ISIS` permit sequences are tagging correctly.
- **Loop prevention proof 1 — OSPF→IS-IS deny:** `show isis database R3.00-00 verbose` on R1 must NOT show 10.200.0.2/32 in R3's LSP. R3 redistributed 10.200.0.2/32 into OSPF (tag 200); R3's `OSPF_TO_ISIS deny 10 match tag 200` must then block it from re-entering IS-IS via R3. If it appears in R3's LSP with tag 100, the deny is not firing.
- **Loop prevention proof 2 — IS-IS→OSPF deny:** `show ip ospf database external 10.1.14.0` on any router must show Advertising Router `10.0.0.1` only — R1's original redistribution. If `10.0.0.3` (R3) also appears, R3's `ISIS_TO_OSPF deny 10 match tag 100` is not blocking the OSPF-tagged IS-IS route from looping back into OSPF.
- `show route-map OSPF_TO_ISIS` and `show route-map ISIS_TO_OSPF` on R3 — "Policy routing matches" is always 0 (PBR counter, ignore it). Confirm the deny sequences and match tag clauses are present in the route-map definition output.

---

### Task 3: Add `send-community both` to all iBGP peer groups

- On R1, R2, and R3, enable community propagation on the IBGP peer group. Without this, any community values set in later tasks will be silently stripped before reaching iBGP neighbors.

**Verification:** `show ip bgp neighbors 10.0.0.2 | include Community` on R1 must show "Community attribute sent to this neighbor."

---

### Task 4: Write an AS-path ACL for AS 65200

- Create AS-path access-list 1 that permits only routes whose AS-path ends with AS 65200. Use the anchored regex form `_65200$` (not `_65200_`).

**Verification:** `show ip bgp regexp _65200$` on R3 must show both 172.20.4.0/24 and 172.20.5.0/24 (R4's two prefixes). `show ip as-path-access-list` must confirm the permit statement.

---

### Task 5: Set BGP communities inbound from R4 on R1 and R3

- On R1, extend the existing `FILTER_R4_IN permit 20` sequence to set community `65100:100` and set local-preference 150 on accepted routes from R4.
- On R3, create a new inbound route-map `FILTER_R4_ASPATH` with two sequences:
  - Sequence 10: match the AS-path ACL (Task 4) and set community `65100:200`.
  - Sequence 20: explicit deny (belt-and-suspenders; blocks anything not matching the AS-path filter).
- Apply `FILTER_R4_ASPATH` inbound on R3's eBGP neighbor session to R4.

**Before verifying:** Run `ip bgp-community new-format` in global configuration on R1, R2, and R3. Without this, IOS displays communities as a raw 32-bit decimal integer (e.g., `4259840100`) instead of the `ASN:value` format (`65100:100`). This is a display-only change and does not affect BGP operation.

**Verification:** `show ip bgp 172.20.4.0` on R1 must show "Community: 65100:100, local pref 150." `show ip bgp 172.20.4.0` on R2 must show the community propagated via iBGP.

---

### Task 6: Define community-list match objects on all three SP routers

- On R1, R2, and R3, define three community-list entries:
  - A standard community-list named `COMM_65100_100` that exactly matches community `65100:100`.
  - An expanded community-list named `COMM_65100_1XX` that matches any community in the pattern `65100:1[0-9][0-9]` (range 65100:100 to 65100:199).
  - An expanded community-list named `COMM_65100_2XX` that matches any community in the pattern `65100:2[0-9]*` (any 65100:2xx or 65100:2xxx value).
- These lists are not applied to any route-map yet — they serve as verification objects for this lab and policy hooks for lab-02.

**Verification:** `show ip community-list` on R2 must show all three entries. Run `show ip bgp community 65100:100` on R2 — the routes propagated via iBGP from R1 must appear.

---

### Task 7: Contrast well-known communities (optional demonstration)

- On R1, review the pre-defined `DEMO_WELL_KNOWN` route-map (it sets community `no-export` on routes matching the prefix-list for R4's prefixes).
- Temporarily apply it inbound on R1's eBGP session to R4 (replacing or chaining with `FILTER_R4_IN`).
- Observe on R2 that routes carrying `no-export` no longer appear in R2's outgoing BGP advertisements (`show ip bgp neighbors 10.0.0.3 advertised-routes`).
- Remove the temporary application before proceeding to the troubleshooting section.

**Verification:** With `no-export` applied: `show ip bgp community no-export` on R1 shows the marked routes. On R2, `show ip bgp neighbors <R3-loopback> advertised-routes` should show 0 routes carrying that community.

---

## 6. Verification & Analysis

### Objective 1 — Redistribution with Tags (R2)

```
R2# show ip route isis
! i L2  10.200.0.3/32 [115/20] via 10.1.23.3, GigabitEthernet0/1
! R3's IS-IS-only loopback appears here — the ONLY route IS-IS wins over OSPF.
! An empty output means no IS-IS-only prefixes exist; check Loopback10 on R1/R3.

R1# show isis database R2.00-00 verbose
! CRITICAL: use "verbose", NOT "detail". The "detail" keyword omits sub-TLVs.
! Expected output for each OSPF-redistributed prefix:
!
!   Metric: 0          IP 10.1.14.0/24
!     Route Admin Tag: 100          <── tag sub-TLV (set by set tag 100 in route-map)
!     Prefix-attr: X:1 R:0 N:0     <── X:1 = External (redistributed from OSPF)
!
!   Metric: 10         IP 10.200.0.2/32
!     Prefix-attr: X:0 R:0 N:1     <── X:0, N:1 = native IS-IS loopback, NO tag
!
! If "Route Admin Tag: 100" is absent on redistributed prefixes, the route-map
! is not structured correctly — ensure each sequence has exactly ONE match route-type.

R1# show ip route 10.200.0.3
! Routing entry for 10.200.0.3/32
!   Known via "ospf 1", distance 110, metric 20
!   Tag 200, type extern 2              <── set tag 200 from ISIS_TO_OSPF map
!   Route tag 200
! This route originated in IS-IS on R3 (Lo10) and was redistributed into OSPF
! by R2 with tag 200 and metric 20. The tag confirms ISIS_TO_OSPF is firing.

R2# show ip ospf database external 10.200.0.3
!   External Route Tag: 200    <── verifies OSPF LSA carries the tag
!   Metric: 20                 <── set metric 20 from ISIS_TO_OSPF map

R2# show route-map OSPF_TO_ISIS
! "Policy routing matches: 0 packets, 0 bytes" will ALWAYS be 0 — this counter
! is for PBR only and does not track redistribution. Ignore it. Verify tags
! via "show isis database verbose" instead.
```

### Objective 2 — Loop Prevention (R3)

```
R1# show isis database R3.00-00 verbose
! Confirms R3's OSPF→IS-IS redistribution with tags. Expected pattern:
!
!   Metric: 0          IP 10.1.14.0/24
!     Route Admin Tag: 100           ← OSPF E1 route, tagged by R3's OSPF_TO_ISIS
!     Prefix-attr: X:1 R:0 N:0
!
!   Metric: 10         IP 10.200.0.3/32
!     Prefix-attr: X:0 R:0 N:1      ← native IS-IS loopback — NO tag, X:0
!
! ALSO verify what is NOT in R3's LSP: the prefix 10.200.0.2/32 (R2's Lo10)
! must NOT appear in R3's IS-IS LSP with tag 100. R3 redistributed 10.200.0.2/32
! from IS-IS into OSPF with tag 200; the OSPF→IS-IS deny tag 200 must then block
! it from re-entering IS-IS via R3. If it appears in R3's LSP tagged 100, the
! deny seq is not firing — a loop is forming.

R1# show ip ospf database external 10.1.14.0
! Advertising Router must be 10.0.0.1 (R1) ONLY.
! If 10.0.0.3 (R3) also appears as an advertising router, R3's ISIS_TO_OSPF
! deny tag 100 is not blocking OSPF-origin routes from re-entering OSPF.

R1# show ip route 10.200.0.2
! Routing entry for 10.200.0.2/32
!   Known via "ospf 1", distance 110, metric 20
!   Tag 200, type extern 2
! R2's IS-IS-only loopback, redistributed into OSPF by R3 with tag 200.
! This confirms R3's ISIS_TO_OSPF permit sequence is redistributing native
! IS-IS routes (no tag 100) correctly.

! NOTE: show route-map "Policy routing matches" is always 0 for redistribution.
! Do not use it to verify whether deny sequences are firing.
```

### Objective 3 — AS-Path Regex

```
R3# show ip bgp regexp _65200$
! Both 172.20.4.0/24 and 172.20.5.0/24 must appear here (R4's two prefixes).
! If neither appears, the session may be down or the regex has a syntax error.

R3# show ip bgp neighbors 10.1.34.4 routes
! Before applying FILTER_R4_ASPATH: two routes visible with no community.
! After applying: routes appear with community 65100:200 in the community column.

R3# show ip as-path-access-list
! "ip as-path access-list 1 permit _65200$" must appear exactly.
! A typo (_65200_ instead of _65200$) passes in this topology but is wrong
! in production — document the difference in your notes.
```

### Objective 4 — Community Propagation

```
R1# show ip bgp 172.20.4.0
!
! Network          Next Hop         Metric LocPrf Weight Path
! *>  172.20.4.0/24  10.1.14.4           0    150      0 65200 i
!                                               ^^^^ local-preference 150
! Community: 65100:100   <── must appear here

R2# show ip bgp 172.20.4.0
! The same route must show "Community: 65100:100" — proving iBGP propagation.
! If community is missing on R2 but present on R1, check "send-community both"
! on R1's IBGP peer group.

R2# show ip bgp community 65100:100
! Routes carrying community 65100:100 (those accepted via R1→R2 iBGP path).
! Routes arriving via R3→R2 iBGP should carry community 65100:200.

R2# show ip bgp community 65100:200
! Routes carrying community 65100:200 (those accepted via R3→R2 iBGP path).
```

---

## 7. Verification Cheatsheet

### Redistribution and Route-Type

```
router ospf 1
 redistribute isis <process> level-2 subnets route-map <map>

router isis <process>
 redistribute ospf <pid> route-map <map>

route-map <OSPF_TO_ISIS> permit 10
 match route-type external type-1
 set tag 100
```

| Command | Purpose |
|---------|---------|
| `show ip route <prefix>` | Confirm tag value for a specific route (`Tag 200, type extern 2`) |
| `show ip ospf database external <prefix>` | OSPF LSA detail — confirms `External Route Tag` value |
| `show isis database <hostname> verbose` | IS-IS LSP sub-TLVs — `Route Admin Tag: 100` and `Prefix-attr: X:1` for redistributed routes. **Use `verbose`, not `detail`** — `detail` omits sub-TLVs. |
| `show ip route isis` | IS-IS routes that WON the RIB. Only IS-IS-only prefixes (not shared with OSPF) appear here. |
| `show ip route ospf` | OSPF routes in the table — IS-IS redistributed routes appear as O E2 |
| `show route-map <name>` | Route-map structure verification — "Policy routing matches" is a PBR counter only, always 0 for redistribution. |

> **Exam tip:** `match route-type external type-1` and `match route-type external type-2` are separate match clauses. A route-map that only matches type-2 silently drops type-1 routes (implicit deny). Always write explicit sequences for every route-type class you expect to redistribute.

> **Exam tip:** On shared-link topologies where OSPF (AD 110) and IS-IS (AD 115) run on the same interfaces, IS-IS never wins the RIB for those prefixes. IS-IS-only loopbacks (not in OSPF) are the only routes visible via `show ip route isis` and the only source for IS-IS→OSPF redistribution.

### AS-Path Access Lists

```
ip as-path access-list <acl-id> permit <regex>

route-map <NAME> permit 10
 match as-path <acl-id>
```

| Command | Purpose |
|---------|---------|
| `show ip as-path-access-list` | List all defined AS-path ACLs |
| `show ip bgp regexp <pattern>` | Test a regex against the live BGP table |
| `show ip bgp neighbors <peer> routes` | Routes received from a specific neighbor |

> **Exam tip:** Test your regex with `show ip bgp regexp` before applying it in a route-map. A match on `.*` will return the entire BGP table — a quick signal that your pattern is over-permissive.

### BGP Communities

```
neighbor <peer-group> send-community both

route-map <NAME> permit 10
 match as-path 1
 set community 65100:100

ip community-list standard <NAME> permit <ASN:value>
ip community-list expanded <NAME> permit <regex>
```

| Command | Purpose |
|---------|---------|
| `show ip bgp community <ASN:value>` | Routes carrying the specified community |
| `show ip bgp community no-export` | Routes carrying well-known no-export community |
| `show ip bgp neighbors <peer> | include Community` | Confirm send-community is active on a session |
| `show ip community-list` | All defined community-lists |

> **Exam tip:** `send-community` is off by default on all IOS BGP peers — including iBGP. Omitting it is the most common cause of "community set but not visible at other routers." Apply it to the peer-group, not individual neighbors, so it covers all members automatically.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp 172.20.4.0` | Community value, local-preference, best-path marker |
| `show ip bgp community 65100:100` | Prefixes carrying community 65100:100 |
| `show ip bgp regexp _65200$` | Prefixes with AS-path ending in 65200 |
| `show route-map <name>` | Sequence numbers, match/set clauses, hit counters |
| `show ip route | include tag` | Tag values in the RIB |
| `show ip as-path-access-list` | Defined AS-path ACLs |
| `show ip community-list` | Defined community-lists |
| `show ip bgp neighbors <ip> | include Community` | send-community status |
| `show isis database detail` | IS-IS LSP TLV including external routes and tags |

### Common Routing Policy Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Community visible on R1 but not R2 | `send-community both` missing on IBGP peer group |
| Route-map deny seq never matches | Tag not being set by the upstream redistribution map |
| All routes dropped at redistribution | Route-map has only deny sequences — no final permit |
| IS-IS routes appear in OSPF with wrong metric | `set metric` missing or wrong value in route-map |
| AS-path regex matches nothing | Regex anchoring error — test with `show ip bgp regexp` first |
| Routing loop after mutual redistribution | Loop-prevention deny sequence missing or wrong tag |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: Redistribution with Tags and Loop Prevention

<details>
<summary>Click to view R1 Prerequisite — OSPF E1 Route Source</summary>

```bash
! R1 — inject connected interfaces into OSPF as E1 routes
! Lo1 (172.16.1.0/24) and Gi0/1 (10.1.14.0/24) will appear as O E1 on R2 and R3.
! This is required so that "match route-type external type-1" sequences fire.
router ospf 1
 redistribute connected metric-type 1 subnets
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — OSPF↔IS-IS redistribution (tagger only — no deny sequences)
router ospf 1
 redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF
!
router isis SP
 redistribute ospf 1 route-map OSPF_TO_ISIS
!
! Tag 100 = OSPF-origin; three sequences cover all OSPF route types
route-map OSPF_TO_ISIS permit 10
 match route-type external type-1
 set tag 100
!
route-map OSPF_TO_ISIS permit 20
 match route-type external type-2
 set tag 100
!
route-map OSPF_TO_ISIS permit 30
 match route-type internal
 set tag 100
!
! Tag 200 = IS-IS-origin
route-map ISIS_TO_OSPF permit 10
 set tag 200
 set metric 20
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — OSPF↔IS-IS redistribution with loop-prevention deny sequences
router ospf 1
 redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF
!
router isis SP
 redistribute ospf 1 route-map OSPF_TO_ISIS
!
! Deny IS-IS-tagged routes re-entering IS-IS; permit others by type
route-map OSPF_TO_ISIS deny 10
 match tag 200
!
route-map OSPF_TO_ISIS permit 20
 match route-type external type-1
 set tag 100
!
route-map OSPF_TO_ISIS permit 30
 match route-type external type-2
 set tag 100
!
route-map OSPF_TO_ISIS permit 40
 match route-type internal
 set tag 100
!
! Deny OSPF-tagged routes re-entering OSPF; permit others
route-map ISIS_TO_OSPF deny 10
 match tag 100
!
route-map ISIS_TO_OSPF permit 20
 set tag 200
 set metric 20
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show route-map OSPF_TO_ISIS
show route-map ISIS_TO_OSPF
show ip route | include tag
show isis database detail
```

</details>

### Task 3: send-community

<details>
<summary>Click to view R1/R2/R3 Configuration</summary>

```bash
! Apply on all three SP routers under address-family ipv4
router bgp 65100
 address-family ipv4
  neighbor IBGP send-community both
```

</details>

### Task 4 & 5: AS-Path ACL and Community Setting

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! Extend FILTER_R4_IN permit 20 with community and local-preference
route-map FILTER_R4_IN permit 20
 match ip address prefix-list PFX_R4_LE_24
 set community 65100:100
 set local-preference 150
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! AS-path ACL — anchored to AS 65200 at end of path
ip as-path access-list 1 permit _65200$
!
! Community-setting route-map applied inbound from R4
route-map FILTER_R4_ASPATH permit 10
 match as-path 1
 set community 65100:200
!
route-map FILTER_R4_ASPATH deny 20
!
! Apply under address-family ipv4
router bgp 65100
 address-family ipv4
  neighbor 10.1.34.4 route-map FILTER_R4_ASPATH in
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 172.20.4.0
show ip bgp regexp _65200$
show ip as-path-access-list
show ip bgp neighbors 10.0.0.2 | include Community
```

</details>

### Task 6: Community Lists

<details>
<summary>Click to view R1/R2/R3 Configuration</summary>

```bash
ip community-list standard COMM_65100_100 permit 65100:100
ip community-list expanded COMM_65100_1XX permit 65100:1[0-9][0-9]
ip community-list expanded COMM_65100_2XX permit 65100:2[0-9]*
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Run the inject script, diagnose using only `show` commands, then fix.

```
python3 scripts/fault-injection/inject_scenario_0N.py --host <eve-ng-ip>
python3 scripts/fault-injection/apply_solution.py   --host <eve-ng-ip> [--node R1]
```

### Ticket 1 — Routes Arriving at R2 from R3 Carry Unexpected Community 65100:200

**Scenario:** After a maintenance window, all prefixes received from R4 now carry community `65100:200` on R2, regardless of which eBGP session learned them. The network team expects R1-learned routes to carry `65100:100` and R3-learned routes to carry `65100:200`.

**Inject script:** `inject_scenario_01.py`

**Success criteria:** `show ip bgp 172.20.4.0` on R2 shows `65100:100` for the best path (via R1) and `65100:200` for the R3 path.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R1 — check community on the R4 route
show ip bgp 172.20.4.0
! If community shows 65100:200 instead of 65100:100, the fault is on R1

! On R1 — inspect FILTER_R4_IN permit 20
show route-map FILTER_R4_IN
! Look for "set community 65100:100" in seq 20. If it shows 65100:200, the
! community value was changed in the route-map.

! Confirm AS-path ACL is not referenced by R1's map (should only be on R3)
show ip as-path-access-list
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — correct the community value in FILTER_R4_IN
route-map FILTER_R4_IN permit 20
 no set community 65100:200
 set community 65100:100
 set local-preference 150
! Clear soft inbound to re-evaluate
clear ip bgp 10.1.14.4 soft in
```

</details>

---

### Ticket 2 — R3's IS-IS-Only Prefix Disappears from R1's OSPF Table

**Scenario:** After a config audit on R2, `10.200.0.3/32` (R3's IS-IS-only loopback) has disappeared from R1's OSPF table. `10.200.0.2/32` is still visible as O E2. R2 and R3 both show IS-IS adjacencies as up.

**Inject script:** `inject_scenario_02.py`

**Success criteria:** `show ip route 10.200.0.3` on R1 shows `O E2` with `Tag 200`. `show ip ospf database external 10.200.0.3` shows advertising router `10.0.0.2` (R2).

> **Diagnostic clue:** The partial disappearance is the key signal. `10.200.0.2/32` is still present because R3 learned it via IS-IS and redistributes it into OSPF. `10.200.0.3/32` is gone because R3 cannot redistribute its own locally-originated loopback via `redistribute isis` — only a remote router (R2) that learned it via IS-IS can do that. The fault is therefore on R2, not R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm the partial disappearance on R1
show ip route 10.200.0.3
! Expected after fault: route not found (or stale via R3 with wrong attributes).
show ip route 10.200.0.2
! Expected: still present as O E2 — confirms R3's ISIS_TO_OSPF is intact.

! Step 2 — On R2, check whether the redistribute isis command is present
show run | section router ospf
! Look for: redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF
! If the line is absent, R2's IS-IS→OSPF redistribution was removed — this is the fault.

! Step 3 — Confirm on the OSPF database: R2 should be the advertising router
show ip ospf database external 10.200.0.3
! Before fix: entry absent or advertising router is not 10.0.0.2.
! After fix: advertising router 10.0.0.2, metric 20, tag 200.
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! The fault is removal of the redistribute isis command from R2's OSPF process.
! R2 is the only router that can redistribute 10.200.0.3/32 (R3's Lo10) into OSPF
! because R2 learns it via IS-IS. R3 cannot redistribute its own locally-originated
! prefix via "redistribute isis".
!
! On R2 — restore redistribution
router ospf 1
 redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF
```

</details>

---

### Ticket 3 — BGP Communities Missing on R2 Despite Being Set on R1

**Scenario:** A peer reports that route-policy decisions on R2 that rely on community values are not working. On R1, `show ip bgp 172.20.4.0` correctly shows `Community: 65100:100`. On R2, the same prefix shows no community at all.

**Inject script:** `inject_scenario_03.py`

**Success criteria:** `show ip bgp 172.20.4.0` on R2 shows `Community: 65100:100`. `show ip bgp neighbors 10.0.0.2 | include Community` on R1 shows "Community attribute sent to this neighbor."

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm community present on R1 but absent on R2
R1# show ip bgp 172.20.4.0
! Community: 65100:100 should appear here. If it does, the fault is in propagation.

R2# show ip bgp 172.20.4.0
! If community is absent here, the fault is between R1 and R2 — not in the
! route-map itself.

! Step 2 — Check whether R1 is sending communities to its iBGP peers
R1# show ip bgp neighbors 10.0.0.2 | include Community
! Expected (working): "Community attribute sent to this neighbor"
! Expected (fault active): line absent or "Community attribute not sent"
! This is the key command — communities are stripped by default on all IOS BGP
! peers including iBGP. "send-community both" must be explicit.

! Step 3 — Confirm under the BGP peer-group definition
R1# show run | section router bgp
! Look for "neighbor IBGP send-community both" under address-family ipv4.
! If the line is absent, that is the fault.
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — restore send-community on the IBGP peer group
router bgp 65100
 address-family ipv4
  neighbor IBGP send-community both

! Soft-clear outbound iBGP sessions to push updated attributes immediately
clear ip bgp 10.0.0.2 soft out
clear ip bgp 10.0.0.3 soft out
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] R1: `redistribute connected metric-type 1 subnets` under `router ospf 1` (creates O E1 routes visible on R2 and R3 — required for route-type seq 10 hit counters)
- [x] R2: OSPF redistributed into IS-IS with `OSPF_TO_ISIS` route-map (type-1, type-2, internal — all tagged 100)
- [x] R2: IS-IS redistributed into OSPF with `ISIS_TO_OSPF` route-map (tag 200, metric 20)
- [x] R3: `OSPF_TO_ISIS` includes deny seq for tag 200 before permit sequences
- [x] R3: `ISIS_TO_OSPF` includes deny seq for tag 100 before permit sequences
- [x] No routing loops observed (`show ip route | include tag` shows stable tags)
- [x] `send-community both` active on IBGP peer group on R1, R2, and R3
- [x] R1 `FILTER_R4_IN permit 20` sets community `65100:100` and local-preference 150
- [x] `ip as-path access-list 1 permit _65200$` defined on R3
- [x] `FILTER_R4_ASPATH` applied inbound on R3's R4 neighbor session
- [x] Community `65100:200` visible on R2 for routes learned via R3
- [x] Community `65100:100` visible on R2 for routes learned via R1
- [x] Community-lists `COMM_65100_100`, `COMM_65100_1XX`, `COMM_65100_2XX` defined on all three SP routers

### Troubleshooting

- [x] Ticket 1 resolved: community value corrected on R1
- [x] Ticket 2 resolved: IS-IS redistribution restored on R2
- [ ] Ticket 3 resolved: `send-community both` restored on R1's IBGP peer group; community `65100:100` visible on R2

---

## 11. Appendix: Script Exit Codes

| Script | Exit 0 | Exit 1 | Exit 2 | Exit 3 |
|--------|--------|--------|--------|--------|
| `setup_lab.py` | All nodes configured | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
| `inject_scenario_0N.py` | Fault injected | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
| `apply_solution.py` | Solution applied | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
