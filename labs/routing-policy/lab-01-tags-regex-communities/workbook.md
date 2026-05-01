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

Separately, R4 (AS 65200) has dual eBGP sessions to R1 and R3. The network team wants to classify R4's prefixes with BGP communities at entry — `65100:100` on R1's side and `65100:200` on R3's side — so that downstream policy can reference the community value rather than re-applying prefix-list matches at every iBGP speaker.

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
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source |
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
- BGP AS 65100 full-mesh iBGP among R1, R2, R3 with `update-source Loopback0`
- eBGP sessions R1↔R4 and R3↔R4 (AS 65200)
- R1 `FILTER_R4_IN` route-map denying 172.20.5.0/24 inbound from R4
- All prefix-lists and ACLs from lab-00 (PFX_R4_LE_24, PFX_R4_LO2_EXACT, ACL_EXT_R4_LO2)
- Demo route-maps from lab-00 (DEMO_CONTINUE, DEMO_REDIST) — not applied

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

### Task 1: Redistribute OSPF into IS-IS on R2 (with tagging)

**Prerequisite — create OSPF E1 routes on R1:** The `match route-type external type-1` sequences in your redistribution route-maps need at least one OSPF E1 route in the domain. Without one, seq 10 in every `OSPF_TO_ISIS` map will have a zero hit counter and you cannot confirm that E1 handling works.

- On R1, add `redistribute connected metric-type 1 subnets` under `router ospf 1`. This injects R1's directly connected interfaces (Lo1 172.16.1.0/24 and Gi0/1 10.1.14.0/24) into OSPF as E1 routes — metric-type 1 means the OSPF cost accumulates across links as the route propagates.
- Confirm: `show ip route ospf` on R2 must list 172.16.1.0/24 and 10.1.14.0/24 as `O E1` before you proceed to the redistribution tasks.

**R2 redistribution:**

- Activate bidirectional redistribution between OSPF process 1 and IS-IS process SP.
- For OSPF→IS-IS: create a route-map that covers all three OSPF route types (external type-1, external type-2, and internal). Set tag 100 on every permitted route.
- For IS-IS→OSPF: create a route-map that permits all IS-IS routes. Set tag 200 and set metric 20 on every permitted route.
- Apply both route-maps to the respective redistribution commands. Do not add any deny sequences on R2 — R2 is the "tagger only."

**Verification:** `show route-map OSPF_TO_ISIS` on R2 must show non-zero hits on seq 10 (`match route-type external type-1`) — R1's E1 routes trigger this sequence. `show ip route ospf` on R3 must show IS-IS-originated prefixes with tag 200. `show isis database` on R1 must show OSPF-originated prefixes with tag 100.

---

### Task 2: Redistribute OSPF into IS-IS on R3 (with loop prevention)

- On R3, activate the same bidirectional redistribution as Task 1.
- For OSPF→IS-IS on R3: add a deny sequence at the top that matches tag 200 (IS-IS-origin marker), then permit the remaining routes by route-type and set tag 100.
- For IS-IS→OSPF on R3: add a deny sequence at the top that matches tag 100 (OSPF-origin marker), then permit the remaining routes and set tag 200 and metric 20.
- Verify that no routing loops form after both routers are redistributing.

**Verification:** `show ip route | include ^O E` on R1 should show IS-IS-learned prefixes with tag 200 but NOT looping routes. `show route-map OSPF_TO_ISIS` on R3 must show the deny sequence with a non-zero match count.

---

### Task 3: Add `send-community both` to all iBGP peer groups

- On R1, R2, and R3, enable community propagation on the IBGP peer group. Without this, any community values set in later tasks will be silently stripped before reaching iBGP neighbors.

**Verification:** `show bgp neighbors 10.0.0.2 | include Community` on R1 must show "Community attribute sent to this neighbor."

---

### Task 4: Set BGP communities inbound from R4 on R1 and R3

- On R1, extend the existing `FILTER_R4_IN permit 20` sequence to set community `65100:100` and set local-preference 150 on accepted routes from R4.
- On R3, create a new inbound route-map `FILTER_R4_ASPATH` with two sequences:
  - Sequence 10: match the AS-path ACL (Task 5) and set community `65100:200`.
  - Sequence 20: explicit deny (belt-and-suspenders; blocks anything not matching the AS-path filter).
- Apply `FILTER_R4_ASPATH` inbound on R3's eBGP neighbor session to R4.

**Verification:** `show ip bgp 172.20.4.0` on R1 must show "Community: 65100:100, local pref 150." `show ip bgp 172.20.4.0` on R2 must show the community propagated via iBGP.

---

### Task 5: Write an AS-path ACL for AS 65200 and apply it on R3

- Create AS-path access-list 1 that permits only routes whose AS-path ends with AS 65200. Use the anchored regex form `_65200$` (not `_65200_`).
- Reference this ACL in `FILTER_R4_ASPATH` sequence 10 from Task 4.

**Verification:** `show ip bgp regexp _65200$` on R3 must show both 172.20.4.0/24 and 172.20.5.0/24 (R4's two prefixes). `show ip as-path-access-list` must confirm the permit statement.

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
R2# show ip route ospf
! Lines marked "tag 100" confirm OSPF routes redistributed into IS-IS were
! stamped correctly. You will NOT see "tag 100" here on the OSPF table itself —
! the tag is visible in IS-IS, not on the redistributed source side.

R2# show isis database R2.00-00 detail
! Look for the external reachability TLV. Routes that originated in OSPF will
! appear in the IS-IS LSP with the tag value embedded in the TLV sub-TLV.

R2# show route-map OSPF_TO_ISIS
! Expected hit pattern:
!   seq 10 (match route-type external type-1): > 0 — R1's connected routes
!     (172.16.1.0/24, 10.1.14.0/24) redistributed with metric-type 1 are E1.
!   seq 20 (match route-type external type-2): 0 — no E2 source in this topology.
!     This is expected; the sequence is correct and necessary for production use
!     where "redistribute" defaults to metric-type 2.
!   seq 30 (match route-type internal): > 0 — OSPF intra/inter-area routes.
! If seq 10 stays at zero, confirm R1 has "redistribute connected metric-type 1
! subnets" under router ospf 1.

R2# show route-map ISIS_TO_OSPF
! The permit 10 counter should show hits for each IS-IS prefix that entered OSPF.
! "set metric 20" is visible in the route-map definition output.
```

### Objective 2 — Loop Prevention (R3)

```
R3# show route-map OSPF_TO_ISIS
! Seq 10 deny "match tag 200" MUST show hits > 0 once redistribution is active.
! A zero hit counter here means no IS-IS-tagged routes are reaching R3's
! OSPF table — check that R2's ISIS_TO_OSPF map is setting tag 200.

R3# show route-map ISIS_TO_OSPF
! Seq 10 deny "match tag 100" should show hits > 0 — OSPF-tagged routes
! are arriving in R3's IS-IS table from R2's OSPF_TO_ISIS redistribution.

R3# show ip route | include tag
! No route should carry BOTH tag 100 and tag 200 simultaneously.
! If the same prefix appears with alternating tags across routers, a loop is active.
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
| `show ip route | include tag` | Confirm tag values in the routing table |
| `show route-map <name>` | Policy hit counters per sequence |
| `show isis database <hostname> detail` | IS-IS LSP TLV — confirms redistributed routes and tags |
| `show ip route ospf` | OSPF routes in the table — IS-IS redistributed routes appear as O E2 |

> **Exam tip:** `match route-type external type-1` and `match route-type external type-2` are separate match clauses. A route-map that only matches type-2 silently drops type-1 routes (implicit deny). Always write explicit sequences for every route-type class you expect to redistribute.

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
| `show bgp neighbors <peer> | include Community` | Confirm send-community is active on a session |
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
| `show bgp neighbors <ip> | include Community` | send-community status |
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

### Task 4 & 5: AS-Path Regex and Community Setting

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
show bgp neighbors 10.0.0.2 | include Community
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

### Ticket 2 — IS-IS Routes Disappear from the OSPF Table on R1

**Scenario:** After a config audit, IS-IS routes that were previously visible in R1's OSPF table as external routes have vanished. R2 and R3 both show IS-IS adjacencies as up.

**Inject script:** `inject_scenario_02.py`

**Success criteria:** `show ip route ospf` on R1 shows IS-IS-originated prefixes redistributed into OSPF with O E2 designation.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R2 — check if ISIS_TO_OSPF route-map is applied
show run | section router ospf
! Look for "redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF"
! If the route-map name is missing or wrong, redistribution is not happening.

! On R2 — check route-map hit counters
show route-map ISIS_TO_OSPF
! If hit counter is 0, no IS-IS routes are being processed by the route-map.

! On R3 — check loop-prevention deny in ISIS_TO_OSPF
show route-map ISIS_TO_OSPF
! If seq 10 deny "match tag 100" has very high hits, OSPF-tagged routes are
! looping — but that would also affect R2. Check R2's route-map first.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! The fault is a wrong route-map reference — redistribution points to a
! non-existent or misnamed route-map, causing IOS to use an empty implicit map
! which permits all routes but sets no tags. Or the redistribute command was
! removed entirely.
!
! On R2 — restore redistribution with correct route-map
router ospf 1
 redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF
```
</details>

---

### Ticket 3 — AS-Path Filter on R3 Passes All Routes from R4 Including Unexpected Ones

**Scenario:** During a peer audit, `show ip bgp regexp _65200$` on R3 returns routes you did not expect — the filter is too broad.

**Inject script:** `inject_scenario_03.py`

**Success criteria:** `show ip as-path-access-list 1` on R3 shows `permit _65200$` (anchored). The filter passes only routes where 65200 is the last (originating) AS.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R3 — inspect the AS-path ACL
show ip as-path-access-list
! Look for the regex pattern. A common error: "permit _65200_" (trailing
! underscore instead of $). In this lab topology they behave identically,
! but in production _65200_ also matches 65200 as a transit AS in the middle
! of a longer path. The correct production form is _65200$.

! Confirm by testing both patterns against the live table:
show ip bgp regexp _65200_
show ip bgp regexp _65200$
! In this topology the output is identical — but document WHY _65200$ is correct.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R3 — replace the AS-path ACL with the anchored form
no ip as-path access-list 1 permit _65200_
ip as-path access-list 1 permit _65200$
! Soft-clear the eBGP session to re-evaluate
clear ip bgp 10.1.34.4 soft in
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R1: `redistribute connected metric-type 1 subnets` under `router ospf 1` (creates O E1 routes visible on R2 and R3 — required for route-type seq 10 hit counters)
- [ ] R2: OSPF redistributed into IS-IS with `OSPF_TO_ISIS` route-map (type-1, type-2, internal — all tagged 100)
- [ ] R2: IS-IS redistributed into OSPF with `ISIS_TO_OSPF` route-map (tag 200, metric 20)
- [ ] R3: `OSPF_TO_ISIS` includes deny seq for tag 200 before permit sequences
- [ ] R3: `ISIS_TO_OSPF` includes deny seq for tag 100 before permit sequences
- [ ] No routing loops observed (`show ip route | include tag` shows stable tags)
- [ ] `send-community both` active on IBGP peer group on R1, R2, and R3
- [ ] R1 `FILTER_R4_IN permit 20` sets community `65100:100` and local-preference 150
- [ ] `ip as-path access-list 1 permit _65200$` defined on R3
- [ ] `FILTER_R4_ASPATH` applied inbound on R3's R4 neighbor session
- [ ] Community `65100:200` visible on R2 for routes learned via R3
- [ ] Community `65100:100` visible on R2 for routes learned via R1
- [ ] Community-lists `COMM_65100_100`, `COMM_65100_1XX`, `COMM_65100_2XX` defined on all three SP routers

### Troubleshooting

- [ ] Ticket 1 resolved: community value corrected on R1
- [ ] Ticket 2 resolved: IS-IS redistribution restored on R2
- [ ] Ticket 3 resolved: AS-path ACL corrected to `_65200$` on R3

---

## 11. Appendix: Script Exit Codes

| Script | Exit 0 | Exit 1 | Exit 2 | Exit 3 |
|--------|--------|--------|--------|--------|
| `setup_lab.py` | All nodes configured | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
| `inject_scenario_0N.py` | Fault injected | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
| `apply_solution.py` | Solution applied | One or more nodes failed | Invalid `--node` argument | EVE-NG API error |
