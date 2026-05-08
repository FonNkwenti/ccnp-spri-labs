# Lab 00 — Route-Maps, Prefix-Lists, and ACL Matching

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

**Exam Objective:** 3.1.a — Implement routing policy using route-maps, prefix-lists, and ACLs

This lab introduces the **building blocks of IOS routing policy**: ACLs, prefix-lists, and route-maps. Starting from a clean interfaces-only baseline, you will bring up a three-router SP core running OSPF, IS-IS, and iBGP, peer with an external AS across two eBGP sessions, and then build and apply an inbound filter to block a specific external prefix on one of those sessions. The filter deliberately leaves the prefix reachable via the other eBGP session — exactly the kind of path-specific policy you see on real SP networks.

### ACLs as Match Objects

Standard numbered ACLs (1-99, 1300-1999) match on source IP only. Extended named or numbered ACLs (100-199, 2000-2699) match source, destination, protocol, and port. Both can be referenced from a route-map `match ip address NN` clause, but prefix-lists are preferred for routing decisions because they support explicit prefix-length matching with `ge` and `le`.

### Prefix-Lists

Purpose-built for routing decisions. Each entry matches a prefix and optionally a length range:

- `ip prefix-list NAME permit A.B.C.D/M` — exact-length match (only /M)
- `ip prefix-list NAME permit A.B.C.D/M ge X` — prefix-length ≥ X
- `ip prefix-list NAME permit A.B.C.D/M le Y` — prefix-length ≤ Y
- `ip prefix-list NAME permit A.B.C.D/M ge X le Y` — X ≤ prefix-length ≤ Y

The prefix must still fall within A.B.C.D/M regardless of the `ge`/`le` constraint.

### Route-Map Mechanics

Route-maps are sequenced policy statements. Each sequence has:

- A **permit/deny** action — if matched, permit runs `set` clauses and accepts the route; deny drops it.
- Optional **match** clauses — AND logic across different match types (prefix-list AND community AND as-path, etc.). No `match` means "match everything."
- Optional **set** clauses — modify attributes of matched routes.
- An **implicit deny** at the end — any route that reaches the end without matching is dropped.

Sequences are evaluated top-to-bottom; first match wins and evaluation stops (unless `continue` is used).

### Route-Map Application Points

The same route-map syntax is used at two places:

| Application point | Command | What it filters |
|-------------------|---------|-----------------|
| BGP neighbor inbound | `neighbor X route-map NAME in` | Routes received from peer X |
| BGP neighbor outbound | `neighbor X route-map NAME out` | Routes advertised to peer X |
| Redistribution | `redistribute PROTO route-map NAME` | Routes injected from PROTO into this routing process |

Wrong direction (e.g., applying an inbound filter outbound) silently does nothing visible on the local BGP RIB-IN — a common troubleshooting trap.

### `continue` Clause

Inside a route-map sequence, `continue [seq]` runs this sequence's `set` actions, then resumes evaluation at the next (or specified) sequence rather than stopping. Without `continue`, evaluation stops at the first matching sequence.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Standard and extended ACL construction | Build ACLs as match objects for route-map `match ip address` clauses |
| Prefix-list with `ge`/`le` | Match any /24 inside a /16 supernet |
| Prefix-list exact match | Match a single specific prefix and length |
| Route-map sequence logic | Predict permit/deny outcomes and implicit deny behavior |
| Inbound BGP filter | Apply `route-map ... in` on an eBGP session and verify RIB-IN changes |
| `continue` clause | Understand multi-sequence evaluation with attribute accumulation |
| Redistribution vs neighbor application | Distinguish where each application point intercepts a route |

---

## 2. Topology & Scenario

**Scenario:** SP-CORE's network team needs to accept only one of R4's two external prefixes on R1's eBGP session, while leaving R3's session unfiltered. Your task is to build the SP core IGP and iBGP baseline, establish both eBGP sessions to R4, then apply an inbound route-map on R1 that blocks `172.20.5.0/24` (R4's Lo2) without disturbing `172.20.4.0/24` (R4's Lo1). R3's unfiltered session means `172.20.5.0/24` still reaches the iBGP table via R3 — so R1 can still forward traffic toward it, just not via the direct R4 path.

```
          ┌──────────────────────────────────────────────────┐
          │                    AS 65100                       │
          │                                                   │
          │    ┌────┐    L1 10.1.12.0/24    ┌────┐           │
          │    │ R1 ├───────────────────────┤ R2 │           │
          │    └──┬─┘   OSPF/IS-IS/iBGP     └──┬─┘           │
          │       │ L5 10.1.13.0/24         L2 │ 10.1.23.0/24│
          │       │   OSPF/IS-IS/iBGP          │             │
          │    ┌──┴─────────────────────────────┴──┐         │
          │    │                R3                  │         │
          │    └───────────────────────────────────┘         │
          └───────────────────────────────────────────────────┘
              │ L4 (eBGP)                  │ L3 (eBGP)
          10.1.14.0/24                 10.1.34.0/24
         FILTER_R4_IN                   (no filter)
              │                             │
              └──────────── R4 ─────────────┘
                          AS 65200
                     Lo1: 172.20.4.0/24  ← accepted on R1
                     Lo2: 172.20.5.0/24  ← blocked on R1, accepted on R3
```

**Key relationships:**

- **R1, R2, R3** form the SP core: OSPF area 0, IS-IS L2, and iBGP full-mesh (peer-group IBGP, source Loopback0) run on all three links (L1, L2, L5).
- **R4 has two eBGP sessions**: L4 to R1 and L3 to R3. R2 has no eBGP — it is pure transit.
- **Filter target**: `172.20.5.0/24` is denied inbound on R1's session with R4. It remains reachable on R1 via iBGP from R3 (next-hop 10.0.0.3) — the route does not disappear from R1's BGP table, only the directly-learned path from 10.1.14.4 is absent.
- **R1 also advertises** `172.16.1.0/24` (Lo1) into BGP to simulate a customer prefix.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP Core / eBGP Edge | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | SP Core / iBGP Transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | SP Core / eBGP Edge | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | External Peer | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

> **Note:** All devices run Cisco IOS. Commands in this lab use IOS syntax — not IOS-XR.

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router-ID, iBGP update-source |
| R1 | Loopback1 | 172.16.1.0/24 | Customer prefix advertised into BGP |
| R2 | Loopback0 | 10.0.0.2/32 | Router-ID, iBGP update-source |
| R3 | Loopback0 | 10.0.0.3/32 | Router-ID, iBGP update-source |
| R4 | Loopback0 | 10.0.0.4/32 | Router-ID |
| R4 | Loopback1 | 172.20.4.0/24 | External prefix #1 — accepted on R1 |
| R4 | Loopback2 | 172.20.5.0/24 | External prefix #2 — filtered on R1 |

### Cabling

| Link ID | Source | Interface | Target | Interface | Subnet | Protocols |
|---------|--------|-----------|--------|-----------|--------|-----------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | OSPF area 0 / IS-IS L2 / iBGP transport |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/24 | OSPF area 0 / IS-IS L2 / iBGP transport |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 | 10.1.34.0/24 | eBGP only |
| L4 | R1 | Gi0/1 | R4 | Gi0/1 | 10.1.14.0/24 | eBGP only |
| L5 | R1 | Gi0/2 | R3 | Gi0/2 | 10.1.13.0/24 | OSPF area 0 / IS-IS L2 / iBGP transport |

### Console Access

| Device | Port | Connection |
|--------|------|------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames (R1, R2, R3, R4)
- Interface IP addressing on all five core links (L1–L5) and all loopbacks
- Interface descriptions referencing the link IDs
- `no ip domain-lookup` and `ip cef` on all devices

**IS NOT pre-loaded** (student configures this):

- OSPF area 0 process and interface assignments
- IS-IS instance SP and interface assignments
- BGP AS 65100 iBGP full-mesh (peer-group IBGP) between R1/R2/R3
- eBGP sessions R1↔R4 and R3↔R4
- BGP `network` statements for Lo1 on R1, Lo1 and Lo2 on R4
- Standard ACL `10` and extended ACL `ACL_EXT_R4_LO2` on R1
- Prefix-lists `PFX_R4_LE_24` and `PFX_R4_LO2_EXACT` on R1
- Route-maps `FILTER_R4_IN`, `DEMO_CONTINUE`, and `DEMO_REDIST` on R1

---

## 5. Lab Challenge: Core Implementation

### Task 1: IGP and BGP Baseline

Configure the SP core routing:

- **OSPF process 1** on R1, R2, R3: assign Lo0 (passive), Gi0/0, Gi0/1 (where applicable), and Gi0/2 to area 0. Set `ip ospf network point-to-point` on all core links. Use explicit `router-id` equal to the loopback address.
- **IS-IS instance SP** on R1, R2, R3: `is-type level-2-only`, `metric-style wide`. Assign the same interfaces. Set NET addresses as `49.0001.0000.0000.000X.00` where X is the router number.
- **BGP AS 65100** on R1, R2, R3: create peer-group `IBGP` with `remote-as 65100`, `update-source Loopback0`, `next-hop-self`. Activate the peer-group in `address-family ipv4`. Configure `no bgp default ipv4-unicast`.
- **eBGP** on R1: add `neighbor 10.1.14.4 remote-as 65200`. Activate in `address-family ipv4`. Advertise `network 172.16.1.0 mask 255.255.255.0`.
- **eBGP** on R3: add `neighbor 10.1.34.4 remote-as 65200`. Activate in `address-family ipv4`.
- **BGP AS 65200** on R4: add neighbors 10.1.14.1 and 10.1.34.3 as remote-as 65100. Advertise `network 172.20.4.0 mask 255.255.255.0` and `network 172.20.5.0 mask 255.255.255.0`.

**Verification:** `show ip ospf neighbor` and `show isis neighbors` on R1/R2/R3 must show all adjacencies up. `show ip bgp summary` on R1 must show R2, R3, and 10.1.14.4 all in Established state. R1's BGP table must contain both `172.20.4.0/24` and `172.20.5.0/24` via 10.1.14.4 with AS-path `65200`.

---

### Task 2: Build a Standard ACL and an Extended ACL

On R1, build two ACLs that will serve as match objects in route-maps:

- **Standard ACL 10** — `permit 172.20.4.0 0.0.0.255` (matches R4's Lo1 source network).
- **Extended named ACL `ACL_EXT_R4_LO2`** — `permit ip 172.20.5.0 0.0.0.255 any` (matches R4's Lo2 as source, any destination).

These are not applied to any interface — they exist as match objects for route-maps only.

**Verification:** `show access-lists 10` and `show ip access-lists ACL_EXT_R4_LO2` must display the configured entries.

---

### Task 3: Build Prefix-Lists with ge/le and Exact Match

On R1, build two prefix-lists:

- **`PFX_R4_LE_24`** — `ip prefix-list PFX_R4_LE_24 seq 5 permit 172.20.0.0/16 ge 24 le 24`. Matches any /24 that falls within 172.20.0.0/16 (both Lo1 and Lo2 of R4 match this).
- **`PFX_R4_LO2_EXACT`** — `ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.5.0/24`. Exact-length match for R4's Lo2 only.

**Verification:** `show ip prefix-list` must list both entries. `show ip prefix-list detail PFX_R4_LO2_EXACT` must show the exact-length entry with no `ge`/`le` qualifiers.

---

### Task 4: Apply an Inbound Route-Map that Denies One R4 Prefix

On R1, build `route-map FILTER_R4_IN` with two sequences:

- **Sequence 10 — `deny`**: `match ip address prefix-list PFX_R4_LO2_EXACT` — drops 172.20.5.0/24.
- **Sequence 20 — `permit`**: `match ip address prefix-list PFX_R4_LE_24` — permits 172.20.4.0/24.

Apply inbound on neighbor 10.1.14.4:

```
neighbor 10.1.14.4 route-map FILTER_R4_IN in
```

Soft-reset to activate without tearing down the session:

```
clear ip bgp 10.1.14.4 soft in
```

**Verification:** `show ip bgp neighbors 10.1.14.4 routes` must show only `172.20.4.0/24` — not `172.20.5.0/24`. Run `show ip bgp 172.20.5.0` and confirm the prefix is still in the BGP table via iBGP from R3 (next-hop 10.0.0.3), not via 10.1.14.4.

---

### Task 5: Demonstrate `continue` and Multi-Sequence Semantics

On R1, build `route-map DEMO_CONTINUE` (do not apply it to any neighbor):

- **Sequence 10 — `permit`**: `match ip address prefix-list PFX_R4_LE_24`, `set community 65100:100`, `continue 20`.
- **Sequence 20 — `permit`**: `set local-preference 200` (no `match` — matches anything that reaches it).

Walk through three scenarios mentally:

(a) A `172.20.4.0/24` prefix enters the map: seq 10 matches, community 65100:100 is set, `continue 20` causes evaluation to proceed to seq 20, local-preference 200 is also set. Both attributes accumulate.

(b) A `10.0.0.0/8` prefix enters the map: seq 10 does not match (prefix not in PFX_R4_LE_24), falls through to seq 20 which has no `match`, matches and sets local-preference 200.

(c) If `continue 20` is removed from seq 10: a `172.20.4.0/24` prefix stops after seq 10 — only community 65100:100 is set, local-preference is not touched.

**Verification:** `show route-map DEMO_CONTINUE` must display both sequences and the `continue` clause under seq 10.

---

### Task 6: Contrast Redistribution vs Neighbor Application

On R1, build `route-map DEMO_REDIST` (do not apply it):

- **Sequence 10 — `permit`**: `match ip address 10`, `set tag 100`.

This uses ACL 10 (which matches 172.20.4.0/24) as the match object. Observe that the exact same route-map can be applied in two fundamentally different places:

| Application point | Command syntax | Where it intercepts |
|-------------------|---------------|---------------------|
| Outbound to a BGP peer | `neighbor 10.1.14.4 route-map DEMO_REDIST out` | Routes being advertised to R4 |
| Into OSPF from BGP | `router ospf 1` → `redistribute bgp 65100 subnets route-map DEMO_REDIST` | Routes being injected from BGP into OSPF |

Do not actually apply either. The purpose is to read the route-map and explain where each application point intercepts the route — redistribution fires when a route moves from one protocol database to another; neighbor out fires per-peer when building BGP Update messages.

**Verification:** `show route-map DEMO_REDIST` must display seq 10 with the ACL match and `set tag 100` action.

---

## 6. Verification & Analysis

### Task 1: IGP and BGP Baseline

```
R1# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/  -        00:00:37    10.1.12.2       GigabitEthernet0/0    ! ← point-to-point: no DR role
10.0.0.3          1   FULL/  -        00:00:38    10.1.13.3       GigabitEthernet0/2    ! ← L5 diagonal to R3
```

```
R1# show isis neighbors

System Id      Type Interface   IP Address      State Holdtime Circuit Id
R2             L2   Gi0/0       10.1.12.2       UP    24       R2.01
R3             L2   Gi0/2       10.1.13.3       UP    23       R3.01
```

```
R1# show ip bgp summary

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.2        4        65100      14      14        4    0    0 00:05:12        2
10.0.0.3        4        65100      14      14        4    0    0 00:05:10        2
10.1.14.4       4        65200      10      10        4    0    0 00:03:44        2    ! ← 2 prefixes from R4
```

### Task 4: Inbound Filter Active

```
R1# show ip bgp neighbors 10.1.14.4 routes

   Network          Next Hop            Metric LocPrf Weight Path
*> 172.20.4.0/24    10.1.14.4                0             0 65200 i    ! ← Lo1 accepted
```

```
R1# show ip bgp 172.20.5.0

BGP routing table entry for 172.20.5.0/24, version 5
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65200
    10.0.0.3 (metric 2) from 10.0.0.3 (10.0.0.3)   ! ← only via iBGP from R3; R4 path denied
      Origin IGP, metric 0, localpref 100, valid, internal, best
```

```
R1# show route-map FILTER_R4_IN

route-map FILTER_R4_IN, deny, sequence 10
  Match clauses:
    ip address prefix-lists: PFX_R4_LO2_EXACT     ! ← exact match for 172.20.5.0/24
  Set clauses:
  Policy routing matches: 0 packets, 0 bytes
route-map FILTER_R4_IN, permit, sequence 20
  Match clauses:
    ip address prefix-lists: PFX_R4_LE_24          ! ← catch-all for remaining /24s in 172.20/16
  Set clauses:
  ! Note: implicit deny at the end; seq 20 is what saves 172.20.4.0/24
```

### Task 5: DEMO_CONTINUE

```
R1# show route-map DEMO_CONTINUE

route-map DEMO_CONTINUE, permit, sequence 10
  Match clauses:
    ip address prefix-lists: PFX_R4_LE_24
  Set clauses:
    community 65100:100
  Continue: sequence 20                              ! ← execution resumes at seq 20 after set
route-map DEMO_CONTINUE, permit, sequence 20
  Match clauses:
  Set clauses:
    local-preference 200
```

---

## 7. Verification Cheatsheet

### Prefix-List Configuration Skeleton (IOS)

```
! Aggregate match — any /24 inside 172.20.0.0/16
ip prefix-list PFX_R4_LE_24 seq 5 permit 172.20.0.0/16 ge 24 le 24

! Exact match — one specific prefix only
ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.5.0/24
```

### Route-Map Configuration Skeleton (IOS)

```
! Deny one prefix, permit the rest
route-map FILTER_R4_IN deny 10
 match ip address prefix-list PFX_R4_LO2_EXACT
!
route-map FILTER_R4_IN permit 20
 match ip address prefix-list PFX_R4_LE_24
!
! Apply inbound on the eBGP session
router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 route-map FILTER_R4_IN in
!
! Soft-reset to activate without resetting the session
clear ip bgp 10.1.14.4 soft in
```

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show route-map [NAME]` | Sequences, match/set clauses, continue directives, hit counters |
| `show ip prefix-list [NAME]` | Prefix and length-range entries, hit counters |
| `show ip prefix-list detail NAME` | Per-entry detail including `ge`/`le` values |
| `show access-lists [NAME\|NN]` | ACL entries and match counters |
| `show ip bgp neighbors X routes` | RIB-IN after inbound policy — only accepted prefixes appear |
| `show ip bgp neighbors X received-routes` | RIB-IN before policy (requires `soft-reconfiguration inbound`) |
| `show ip bgp X.X.X.X` | Per-prefix detail showing all paths and which is best |
| `show ip bgp summary` | All BGP sessions, state, prefix counts |
| `clear ip bgp X soft in` | Soft-reset inbound — re-applies the route-map without resetting the session |

### Common Route-Map Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| All prefixes from peer disappear | Route-map has only a `deny` sequence — implicit deny at end drops everything not explicitly permitted |
| Filter supposed to block one prefix blocks more | Prefix-list in the deny sequence is too broad (`le 24` instead of exact match) |
| Filter has no effect on received routes | Route-map applied `out` instead of `in`; or `soft in` reset not run after applying |
| `match ip address NN` vs `prefix-list` confusion | Numeric argument references an ACL; `prefix-list NAME` references a prefix-list — they are different |
| `ge`/`le` not matching as expected | Outer prefix must still be a prefix-match; `ge` minimum applies to the matched prefix length |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IGP and BGP Baseline

> **Platform note (IOSv 15.6(2)T — EVE-NG):** `neighbor IBGP activate` inside `address-family ipv4` is rejected on this image with `% Activation failed : configure "bgp listener range" before activating peergroup`. Omit that line and activate each peer-group member individually instead (`neighbor 10.0.0.X activate`). All other peer-group attributes are still inherited. This restriction does not exist on IOS-XE or physical hardware.

<details>
<summary>Click to view R1 Configuration</summary>

```
! R1 — OSPF, IS-IS, BGP with eBGP to R4
interface Loopback0
 ip ospf 1 area 0
 ip router isis SP
!
interface GigabitEthernet0/0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
router ospf 1
 router-id 10.0.0.1
 passive-interface Loopback0
!
router isis SP
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor IBGP peer-group
 neighbor IBGP remote-as 65100
 neighbor IBGP update-source Loopback0
 neighbor 10.0.0.2 peer-group IBGP
 neighbor 10.0.0.3 peer-group IBGP
 neighbor 10.1.14.4 remote-as 65200
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  neighbor IBGP next-hop-self
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.3 activate
  neighbor 10.1.14.4 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```
! R2 — OSPF, IS-IS, iBGP transit only
interface Loopback0
 ip ospf 1 area 0
 ip router isis SP
!
interface GigabitEthernet0/0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
interface GigabitEthernet0/1
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
router ospf 1
 router-id 10.0.0.2
 passive-interface Loopback0
!
router isis SP
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
router bgp 65100
 bgp router-id 10.0.0.2
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor IBGP peer-group
 neighbor IBGP remote-as 65100
 neighbor IBGP update-source Loopback0
 neighbor 10.0.0.1 peer-group IBGP
 neighbor 10.0.0.3 peer-group IBGP
 !
 address-family ipv4
  neighbor IBGP next-hop-self
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.3 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```
! R3 — OSPF, IS-IS, iBGP + eBGP to R4
interface Loopback0
 ip ospf 1 area 0
 ip router isis SP
!
interface GigabitEthernet0/0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip ospf network point-to-point
 ip ospf 1 area 0
 ip router isis SP
 isis network point-to-point
!
router ospf 1
 router-id 10.0.0.3
 passive-interface Loopback0
!
router isis SP
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
router bgp 65100
 bgp router-id 10.0.0.3
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor IBGP peer-group
 neighbor IBGP remote-as 65100
 neighbor IBGP update-source Loopback0
 neighbor 10.0.0.1 peer-group IBGP
 neighbor 10.0.0.2 peer-group IBGP
 neighbor 10.1.34.4 remote-as 65200
 !
 address-family ipv4
  neighbor IBGP next-hop-self
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.2 activate
  neighbor 10.1.34.4 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```
! R4 — eBGP to R1 and R3; advertises Lo1 and Lo2
router bgp 65200
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.1.14.1 remote-as 65100
 neighbor 10.1.34.3 remote-as 65100
 !
 address-family ipv4
  network 172.20.4.0 mask 255.255.255.0
  network 172.20.5.0 mask 255.255.255.0
  neighbor 10.1.14.1 activate
  neighbor 10.1.34.3 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show ip ospf neighbor
show isis neighbors
show ip bgp summary
show ip bgp
```

</details>

---

### Tasks 2 & 3: ACLs and Prefix-Lists

<details>
<summary>Click to view R1 Match Objects</summary>

```
! Standard ACL — source match for 172.20.4.0/24
access-list 10 permit 172.20.4.0 0.0.0.255

! Extended ACL — source/destination match for 172.20.5.0/24
ip access-list extended ACL_EXT_R4_LO2
 permit ip 172.20.5.0 0.0.0.255 any

! Prefix-list — any /24 inside 172.20.0.0/16
ip prefix-list PFX_R4_LE_24 seq 5 permit 172.20.0.0/16 ge 24 le 24

! Prefix-list — exact match for 172.20.5.0/24 only
ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.5.0/24
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show access-lists 10
show ip access-lists ACL_EXT_R4_LO2
show ip prefix-list
show ip prefix-list detail PFX_R4_LO2_EXACT
```

</details>

---

### Task 4: Inbound Filter

<details>
<summary>Click to view R1 Route-Map and BGP Application</summary>

```
route-map FILTER_R4_IN deny 10
 match ip address prefix-list PFX_R4_LO2_EXACT
!
route-map FILTER_R4_IN permit 20
 match ip address prefix-list PFX_R4_LE_24
!
router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 route-map FILTER_R4_IN in
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
clear ip bgp 10.1.14.4 soft in
show ip bgp neighbors 10.1.14.4 routes
show ip bgp 172.20.5.0
show route-map FILTER_R4_IN
```

</details>

---

### Tasks 5 & 6: DEMO_CONTINUE and DEMO_REDIST

<details>
<summary>Click to view R1 Demo Route-Maps</summary>

```
route-map DEMO_CONTINUE permit 10
 match ip address prefix-list PFX_R4_LE_24
 set community 65100:100
 continue 20
!
route-map DEMO_CONTINUE permit 20
 set local-preference 200
!
route-map DEMO_REDIST permit 10
 match ip address 10
 set tag 100
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show route-map DEMO_CONTINUE
show route-map DEMO_REDIST
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world route-map misconfiguration on R1. Inject the fault, diagnose using only `show` commands, then restore.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore after each
```

---

### Ticket 1 — "All R4 Prefixes Have Disappeared"

The NOC reports that after a change window on R1, **none** of R4's prefixes appear in R1's BGP RIB-IN from neighbor 10.1.14.4 — neither `172.20.4.0/24` nor `172.20.5.0/24`. Other PEs (R2, R3) still have them. The session itself is Established.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.14.4 routes` on R1 shows `172.20.4.0/24` accepted; `172.20.5.0/24` absent (filtered). Both prefixes visible via R3 path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp neighbors 10.1.14.4 routes` — if completely empty while the session is up, the inbound route-map is denying everything.
2. On R1: `show route-map FILTER_R4_IN` — count the sequences. If only sequence 10 (deny) is present and sequence 20 (permit) is missing, the implicit deny at the end of the map drops `172.20.4.0/24` too.
3. Confirm: `show running-config | section route-map FILTER_R4_IN` — sequence 20 is absent.
4. Root cause: `route-map FILTER_R4_IN permit 20` (the catch-all permit for `PFX_R4_LE_24`) was removed. With only `deny 10` remaining, the implicit deny at the end of the map drops all other prefixes including `172.20.4.0/24`.

</details>

<details>
<summary>Click to view Fix</summary>

On R1: re-add sequence 20 to the route-map.

```
R1(config)# route-map FILTER_R4_IN permit 20
R1(config-route-map)# match ip address prefix-list PFX_R4_LE_24
R1(config-route-map)# exit
R1# clear ip bgp 10.1.14.4 soft in
```

Verify: `show ip bgp neighbors 10.1.14.4 routes` now shows `172.20.4.0/24`; `show route-map FILTER_R4_IN` shows both sequences.
</details>

---

### Ticket 2 — "Filter Is Over-Matching"

The inbound filter on R1 from R4 was supposed to drop **only** `172.20.5.0/24`, but reports show that `172.20.4.0/24` is also being dropped from R1's RIB-IN. The session is Established and R4 is advertising both prefixes.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.14.4 routes` on R1 shows only `172.20.4.0/24`; `172.20.5.0/24` absent.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp neighbors 10.1.14.4 routes` — both prefixes absent from RIB-IN; session is up.
2. On R1: `show route-map FILTER_R4_IN` — seq 10 is a deny with `PFX_R4_LO2_EXACT`. If both prefixes are being dropped by seq 10, the prefix-list must match more than just Lo2.
3. On R1: `show ip prefix-list PFX_R4_LO2_EXACT` — expected output is `permit 172.20.5.0/24`. If the entry shows `permit 172.20.0.0/16 le 24` instead, it now matches all /24s in 172.20/16 including Lo1.
4. Root cause: `PFX_R4_LO2_EXACT` was widened from an exact-length `/24` entry to `172.20.0.0/16 le 24`, which matches both Lo1 and Lo2. Seq 10 (deny) now catches both, so both are dropped.

</details>

<details>
<summary>Click to view Fix</summary>

On R1: restore the exact-match entry in `PFX_R4_LO2_EXACT`.

```
R1(config)# no ip prefix-list PFX_R4_LO2_EXACT
R1(config)# ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.5.0/24
R1# clear ip bgp 10.1.14.4 soft in
```

> **IOSv note:** `no ip prefix-list NAME seq N` (seq-only deletion) is rejected with `% Incomplete command.` on IOSv. Use `no ip prefix-list NAME` to delete the entire list, then re-add the correct entry.
>
> **Timing note:** Wait ~5 seconds after `clear ip bgp soft in` before checking `show ip bgp neighbors 10.1.14.4 routes` — the Route Refresh from R4 and re-evaluation takes a moment to complete.

Verify: `show ip prefix-list PFX_R4_LO2_EXACT` shows the exact `/24` entry. `show ip bgp neighbors 10.1.14.4 routes` shows `172.20.4.0/24` accepted.
</details>

---

### Ticket 3 — "Filter Has No Effect"

The inbound filter on R1 from R4 is supposed to block `172.20.5.0/24`, but that prefix is still appearing in R1's BGP RIB-IN directly from 10.1.14.4. The configuration on R1 "looks almost right."

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.14.4 routes` on R1 shows only `172.20.4.0/24`. `172.20.5.0/24` not present from 10.1.14.4.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp neighbors 10.1.14.4 routes` — both `172.20.4.0/24` and `172.20.5.0/24` visible from 10.1.14.4. Filter is not active inbound.
2. On R1: `show ip bgp neighbors 10.1.14.4` — look for the line showing route-map application. If it reads `Route map for outgoing advertisements is FILTER_R4_IN`, the map is applied outbound, not inbound.
3. On R1: `show running-config | include route-map FILTER_R4_IN` — look for `out` instead of `in`.
4. Root cause: `neighbor 10.1.14.4 route-map FILTER_R4_IN out` was set instead of `in`. An outbound filter controls what R1 sends to R4 — it does not filter what R1 receives from R4. The inbound RIB-IN is completely unaffected.

</details>

<details>
<summary>Click to view Fix</summary>

On R1: change the route-map direction from `out` to `in`.

```
R1(config)# router bgp 65100
R1(config-router)# address-family ipv4
R1(config-router-af)# no neighbor 10.1.14.4 route-map FILTER_R4_IN out
R1(config-router-af)# neighbor 10.1.14.4 route-map FILTER_R4_IN in
R1(config-router-af)# exit
R1# clear ip bgp 10.1.14.4 soft in
```

Verify: `show ip bgp neighbors 10.1.14.4` now shows `Route map for incoming advertisements is FILTER_R4_IN`. `show ip bgp neighbors 10.1.14.4 routes` shows only `172.20.4.0/24`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] All OSPF and IS-IS adjacencies up between R1/R2/R3 on L1, L2, and L5
- [x] iBGP full-mesh established (R1↔R2, R2↔R3, R1↔R3) via Loopback0 sessions
- [x] eBGP sessions up: R1↔R4 (10.1.14.4) and R3↔R4 (10.1.34.4)
- [x] R1 advertises `172.16.1.0/24`; R4 advertises `172.20.4.0/24` and `172.20.5.0/24`
- [x] Standard ACL `10` and extended ACL `ACL_EXT_R4_LO2` defined on R1
- [x] Prefix-lists `PFX_R4_LE_24` (ge/le 24) and `PFX_R4_LO2_EXACT` (exact) defined on R1
- [x] `route-map FILTER_R4_IN` applied inbound on R1's neighbor 10.1.14.4
- [x] `show ip bgp neighbors 10.1.14.4 routes` shows only `172.20.4.0/24`
- [x] `show ip bgp 172.20.5.0` on R1 shows prefix reachable only via iBGP from R3
- [x] `route-map DEMO_CONTINUE` and `route-map DEMO_REDIST` defined (not applied) on R1

### Troubleshooting

- [x] Ticket 1 diagnosed (implicit deny from missing seq 20) and resolved — both R4 prefixes properly filtered/permitted
- [x] Ticket 2 diagnosed (PFX_R4_LO2_EXACT too broad) and resolved — only 172.20.5.0/24 denied
- [x] Ticket 3 diagnosed (route-map applied outbound instead of inbound) and resolved — filter active inbound

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error or node not found | All scripts |
| 4 | Pre-flight check failed — run `apply_solution.py` first | Inject scripts only |
