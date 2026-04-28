# BGP Lab 02 — eBGP Multihoming and Traffic Engineering

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

**Exam Objective:** 1.5.d — Troubleshoot BGP multihoming

eBGP multihoming means a customer AS connects to a provider AS via two or more separate eBGP sessions on different physical links. The immediate benefit is link redundancy — losing one physical path does not disconnect the customer. The harder problem is *traffic engineering*: without deliberate configuration, BGP treats both paths equally and the SP core may load-balance or make arbitrary choices. This lab introduces the three primary knobs that shape traffic flow in a dual-homed design.

### LOCAL_PREF

`LOCAL_PREF` (BGP attribute code 5) is an iBGP-only, non-transitive attribute. It is set by the receiving PE when a prefix arrives via eBGP, and it propagates across the entire iBGP fabric. All routers in the same AS compare `LOCAL_PREF` before any other attribute — **higher value wins**. The default is 100.

In a dual-homed design, the PE connected to the primary link sets `LOCAL_PREF 200` on inbound routes from the customer. Every iBGP speaker in the provider AS (including the Route Reflector and all other PEs) then sees one path with `LOCAL_PREF 200` and one with the default `100` — and consistently prefers the primary PE as the egress point to reach the customer.

```
! On R2 (primary PE) — inbound route-map from Customer A:
route-map FROM-CUST-A-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set local-preference 200
```

### AS-Path Prepending

`AS-path prepending` inflates the AS-path length of advertisements sent *out* by the customer on the backup link. Because BGP's best-path algorithm prefers shorter AS-paths (after checking `LOCAL_PREF`), making the backup path artificially longer discourages AS 65100 from using it when the primary path is available.

Critically, AS-path prepending works in the *opposite direction* from `LOCAL_PREF`: `LOCAL_PREF` controls how AS 65100 reaches the customer (egress from the SP); AS-path prepending on the customer router controls how the customer looks to AS 65100 — still affecting SP ingress selection.

```
! On R1 — outbound toward R3 (backup PE):
route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set as-path prepend 65001
```

The resulting AS-path seen by AS 65100 via R3 is `65001 65001` (two hops) versus `65001` (one hop) via R2.

### MED (MULTI_EXIT_DISC)

`MED` (BGP attribute code 4) is an optional, non-transitive attribute. It is relevant **only when two routes to the same prefix were learned from the same neighboring AS**, and only when `bgp always-compare-med` is not set (the default). MED provides a secondary signal to AS 65100 about the customer's preferred ingress point — lower MED wins.

In this lab, R1 sets MED 10 on advertisements toward R2 and MED 50 toward R3. Because `LOCAL_PREF` and AS-path length are checked first, MED is rarely the deciding factor here — but it demonstrates a defense-in-depth approach and matches real SP configurations where operators want explicit signaling at every knob level.

```
! On R1 — outbound toward R2 (primary PE):
route-map TO-R2-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set metric 10

! Outbound toward R3 (backup PE):
route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set metric 50
 set as-path prepend 65001
```

### BGP Best-Path Selection (Relevant Order)

| Step | Attribute | Higher/Lower wins | Notes |
|------|-----------|-------------------|-------|
| 1 | Weight (Cisco proprietary) | Higher | Local to router only; not in this lab |
| 2 | LOCAL_PREF | **Higher** | iBGP-wide; most impactful knob |
| 3 | Locally originated | — | `network` statement beats iBGP-learned |
| 4 | AS-path length | **Shorter** | AS-path prepend exploits this |
| 5 | Origin (IGP > EGP > incomplete) | IGP preferred | Usually irrelevant in eBGP designs |
| 6 | MED | **Lower** | Only compared for same-AS neighbors |
| 7 | eBGP over iBGP | eBGP preferred | — |
| 8 | IGP metric to next-hop | Lower | OSPF cost to the next-hop loopback |
| 9 | Router-ID / neighbor IP | Lower | Tiebreaker of last resort |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Dual-homed eBGP activation | Enable a second eBGP session on an existing IP-addressed link |
| `next-hop-self` placement | Apply on the backup PE so eBGP next-hops are reachable via OSPF |
| LOCAL_PREF via route-map | Use inbound route-map on the primary PE to raise preference |
| AS-path prepending | Use outbound route-map on the CE to lengthen the backup path |
| MED signaling | Set differential MED values to signal preferred ingress |
| Failover verification | Validate path switchover by shutting the primary link |
| Best-path attribute reading | Read `show ip bgp <prefix>` to identify which attribute decides the winner |

---

## 2. Topology & Scenario

**Scenario:** Customer A (AS 65001) is dual-homed to the SP core (AS 65100). The primary link connects R1 to R2 (PE East-1) via L1. The backup link connects R1 to R3 (PE East-2) via L2. L2 was IP-addressed in labs 00–01 but had no BGP session — the student activates it now and applies traffic-engineering policy so traffic consistently prefers the primary path.

```
     AS 65001                        AS 65100 (OSPF area 0)                   AS 65002
  ┌───────────────────┐                                                 ┌──────────────────┐
  │        R1         │                                                 │        R6        │
  │  Customer A CE    │                                                 │  Ext SP Peer     │
  │  Lo0: 10.0.0.1/32 │                                                 │  Lo0: 10.0.0.6/32│
  │  Lo1:172.16.1.1/24│                                                 │  Lo1:172.16.6.1  │
  └─────┬────────┬────┘                                                 └────────┬─────────┘
   Gi0/0│        │Gi0/1                                                    Gi0/0 │
10.1.12.1│       │10.1.13.1                                            10.1.56.6 │
  (L1)  │        │ (L2)                                                  (L7)   │
primary │        │ backup                                                        │ Gi3
        │        │                                                    10.1.56.5  │
  Gi0/0 │   Gi0/0│                                                               │
 10.1.12.2   10.1.13.3                                              ┌────────────┴──────────┐
  ┌────┴──────┐  ┌┴───────────┐         ┌──────────────────────────┤        R5             │
  │    R2     │  │     R3     │         │                          │   PE West (IOS-XE)    │
  │ PE East-1 │  │  PE East-2 │         │                          │   Lo0: 10.0.0.5/32    │
  │(AS 65100) │  │ (AS 65100) │         │                          └─────────┬─────────────┘
  │Lo0:10.0.0.2│ │Lo0:10.0.0.3│        │                               Gi2  │
  └──┬─────┬──┘  └───┬────────┘         │                          10.1.45.5 │
Gi0/1│Gi0/2│   Gi0/1 │                  │                               (L5) │
     │     │   10.1.34.3                │                          10.1.45.4  │
  (L3)│ (L6)│    (L4)│                  │ Gi0/2                        Gi0/2 │
10.1.24.2│ │10.1.23.2│                  └──────────────────────────────────┐  │
  Gi0/0│ └─────┘ Gi0/1│                                                    │  │
10.1.24.4 10.1.23.3 10.1.34.4                                         ┌────┴──┴───────────┐
       └──────────────┘                                                │        R4         │
                │                                                      │  P / Rte Reflector│
                └──────────────────────────────────────────────────────│  Lo0: 10.0.0.4/32 │
                                                                       │  cluster-id:10.0.0.4│
                                                                       └───────────────────┘
```

**Key relationships:**
- R1 advertises `172.16.1.0/24` (Customer A aggregate) into both eBGP sessions
- R2 raises `LOCAL_PREF` to 200 on routes received from R1 → entire SP core prefers the R2 path
- R1 prepends AS 65001 once on advertisements to R3 → R2 path appears with shorter AS-path
- R4 (Route Reflector) reflects both paths to all iBGP clients; clients see primary (LP=200) and backup (LP=100, longer AS-path)
- R3 must have `next-hop-self` toward R4 so R1's eBGP next-hop (10.1.13.1) is replaced with R3's loopback before entering the iBGP fabric

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 — primary eBGP PE (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 — backup eBGP PE (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P Router / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id, eBGP session source |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A prefix source |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, iBGP peering source, RR cluster-id |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP peering source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id, eBGP peering source |
| R6 | Loopback1 | 172.16.6.1/24 | External peer prefix source |

### Cabling Table

| Link ID | Source | Source IP | Target | Target IP | Subnet | Purpose |
|---------|--------|-----------|--------|-----------|--------|---------|
| L1 | R1 Gi0/0 | 10.1.12.1 | R2 Gi0/0 | 10.1.12.2 | 10.1.12.0/24 | eBGP primary (CE↔PE East-1) |
| L2 | R1 Gi0/1 | 10.1.13.1 | R3 Gi0/0 | 10.1.13.3 | 10.1.13.0/24 | eBGP backup (CE↔PE East-2) |
| L3 | R2 Gi0/1 | 10.1.24.2 | R4 Gi0/0 | 10.1.24.4 | 10.1.24.0/24 | OSPF/iBGP R2↔R4 |
| L4 | R3 Gi0/1 | 10.1.34.3 | R4 Gi0/1 | 10.1.34.4 | 10.1.34.0/24 | OSPF/iBGP R3↔R4 |
| L5 | R4 Gi0/2 | 10.1.45.4 | R5 Gi2 | 10.1.45.5 | 10.1.45.0/24 | OSPF/iBGP R4↔R5 |
| L6 | R2 Gi0/2 | 10.1.23.2 | R3 Gi0/2 | 10.1.23.3 | 10.1.23.0/24 | OSPF IGP East PE resilience |
| L7 | R5 Gi3 | 10.1.56.5 | R6 Gi0/0 | 10.1.56.6 | 10.1.56.0/24 | eBGP AS 65100↔65002 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP `network` | Customer A aggregate; sourced from Loopback1 |
| R6 | 172.16.6.0/24 | eBGP `network` | External peer aggregate; sourced from Loopback1 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R6 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames, `no ip domain-lookup`, interface IP addressing on all links and loopbacks
- OSPF area 0 on R2, R3, R4, R5 (loopbacks + core links L3–L6)
- eBGP R1↔R2 (primary path, AS 65001↔65100) — Established
- eBGP R5↔R6 (external SP peer, AS 65100↔65002) — Established
- iBGP full mesh upgrade from lab-01: R4 as Route Reflector; R2, R3, R5 as RR clients
- Legacy direct iBGP R2↔R5 from lab-00 (additive continuity)
- `bgp cluster-id 10.0.0.4` on R4
- `next-hop-self` on R2 and R5 toward iBGP peers

**IS NOT pre-loaded** (student configures this):
- Second eBGP session R1↔R3 on L2 (backup path)
- `next-hop-self` on R3 toward R4 for routes learned from R1
- LOCAL_PREF route-map on R2 inbound from Customer A
- AS-path prepending on R1 outbound toward R3
- MED outbound on R1 toward both PEs

---

## 5. Lab Challenge: Core Implementation

### Task 1: Activate the R1–R3 Backup eBGP Session

- On R1 (AS 65001), configure an eBGP peer to R3 using the 10.1.13.0/24 link. R3 is in AS 65100.
- On R3 (AS 65100), configure an eBGP peer to R1 (AS 65001) on that same link. Activate the peer in the IPv4 address family.
- On R3, configure `next-hop-self` toward R4 so that Customer A routes learned from R1 are forwarded into the iBGP fabric with a resolvable next-hop.
- Advertise Customer A's prefix on R1 into both eBGP sessions.

**Verification:** `show ip bgp summary` on R3 must show the R1 peer `Established` with at least 1 prefix received. `show ip bgp 172.16.1.0/24` on R4 must show two paths — one via R2 (next-hop 10.0.0.2) and one via R3 (next-hop 10.0.0.3).

---

### Task 2: Configure LOCAL_PREF to Prefer the R2 Path

- On R2, create a prefix-list matching Customer A's prefix `172.16.1.0/24`.
- Apply an inbound route-map to R2's eBGP session with R1. For Customer A's prefix, set `local-preference 200`. All other prefixes should pass unchanged.
- After applying, perform a soft inbound reset on R2's R1 session to activate the new policy without dropping the session.

**Verification:** `show ip bgp 172.16.1.0/24` on R4 must show the path via R2 (next-hop 10.0.0.2) with `localpref 200` and the `>` (best) indicator. The path via R3 must show `localpref 100` and no `>`.

---

### Task 3: Configure AS-Path Prepending on R1 Toward R3

- On R1, apply an outbound route-map to the R3 eBGP session. For Customer A's prefix, prepend AS 65001 once. All other prefixes should pass unchanged.
- This makes the AS-path for the backup path `65001 65001` (length 2) versus `65001` (length 1) via R2.

**Verification:** `show ip bgp 172.16.1.0/24` on R3 must show the locally-received prefix with AS-path `65001 65001`. On R4, confirm the reflected path via R3 carries the longer AS-path.

---

### Task 4: Set MED Outbound on R1

- On R1, apply outbound route-maps to both eBGP sessions. For Customer A's prefix, set MED 10 toward R2 (primary) and MED 50 toward R3 (backup).
- R1's route-map toward R3 should apply both the MED and the AS-path prepend in a single permit clause.

**Verification:** `show ip bgp 172.16.1.0/24` on R2 must show metric (MED) value `10`. The same command on R3 must show MED `50`.

---

### Task 5: Verify Primary/Backup Failover

- Confirm the steady-state path: all SP core routers should select R2 as the best next-hop to reach Customer A.
- Simulate primary link failure: shut GigabitEthernet0/0 on R1. Wait for BGP to converge.
- Verify that Customer A's prefix is now reachable via R3 by checking `show ip bgp 172.16.1.0/24` and `show ip route bgp` on R4 and R5.
- Re-enable the primary link and confirm traffic reverts to R2.

**Verification:** After shutting R1 Gi0/0, `show ip bgp summary` on R2 must show the R1 session `Idle`. `show ip bgp 172.16.1.0/24` on R4 must show only one path, via R3, with `localpref 100` and `>`. `show ip route 172.16.1.0` on R5 must show the route installed with next-hop resolving via R3's loopback.

---

## 6. Verification & Analysis

### Task 1: BGP Session and Path Verification on R4

```
R3# show ip bgp summary
BGP router identifier 10.0.0.3, local AS number 65100
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.13.1       4 65001      15      12        3    0    0 00:02:10         1   ! ← R1 Established, 1 prefix received
10.0.0.4        4 65100      20      18        3    0    0 00:05:44         2   ! ← R4 RR session active

R4# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 5
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001
    10.0.0.2 (metric 2) from 10.0.0.2 (10.0.0.2)     ! ← path via R2, next-hop R2's loopback
      Origin IGP, metric 10, localpref 200, valid, internal, best   ! ← LP=200, MED=10, BEST
      rx path id: 0x0
  Refresh Epoch 1
  65001 65001
    10.0.0.3 (metric 2) from 10.0.0.3 (10.0.0.3)     ! ← path via R3, AS-path prepended
      Origin IGP, metric 50, localpref 100, valid, internal         ! ← LP=100, MED=50, not best
      rx path id: 0x0
```

### Task 2: LOCAL_PREF on R2

```
R2# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 3
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001
    10.1.12.1 from 10.1.12.1 (10.0.0.1)
      Origin IGP, metric 10, localpref 200, valid, external, best   ! ← LP=200 SET by route-map, MED=10
```

### Task 3: AS-Path on R3

```
R3# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 2
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  65001 65001
    10.1.13.1 from 10.1.13.1 (10.0.0.1)
      Origin IGP, metric 50, localpref 100, valid, external, best   ! ← AS-path 65001 65001 (length 2)
```

### Task 5: Post-Failover State on R4

```
R4# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 6
Paths: (1 available, best #1, table default)
  Refresh Epoch 2
  65001 65001
    10.0.0.3 (metric 2) from 10.0.0.3 (10.0.0.3)
      Origin IGP, metric 50, localpref 100, valid, internal, best   ! ← only R3 path remains; now best

R5# show ip route 172.16.1.0
Routing entry for 172.16.1.0/24
  Known via "bgp 65100", distance 200, metric 50
  Tag 65001, type internal
  Last update from 10.0.0.3 00:00:28 ago    ! ← route installed via R3 after failover
  Routing Descriptor Blocks:
  * 10.0.0.3, from 10.0.0.4, 00:00:28 ago
      Route metric is 50, traffic share count is 1
```

---

## 7. Verification Cheatsheet

### BGP Session State

```
show ip bgp summary
show ip bgp neighbors <ip> | inc BGP state
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp summary` | State/PfxRcd column — Established + prefix count |
| `show ip bgp neighbors <ip>` | `BGP state = Established` |
| `show ip bgp neighbors <ip> advertised-routes` | Prefixes being sent to that peer |
| `show ip bgp neighbors <ip> received-routes` | Prefixes received (requires soft-reconfig) |

### BGP Path Attributes

```
show ip bgp 172.16.1.0/24
show ip bgp 172.16.1.0
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp <prefix>` | `localpref`, `metric` (MED), AS-path, `>` best indicator |
| `show ip bgp` | Full table — `>` = best, `*` = valid, `i` = iBGP |
| `show ip route bgp` | BGP routes installed in RIB |
| `show ip route 172.16.1.0` | Next-hop and distance for the installed route |

### Route-Map and Prefix-List

```
show route-map
show ip prefix-list
show bgp ipv4 unicast neighbors <ip> policy
```

| Command | What to Look For |
|---------|-----------------|
| `show route-map` | Policy matches and set actions; match/set counters |
| `show ip prefix-list` | Prefix-list entries and hit counts |
| `show bgp ipv4 unicast neighbors <ip> policy` | Applied inbound/outbound route-maps |

> **Exam tip:** `show ip bgp <prefix>` is the fastest way to confirm which best-path attribute decided the winner — the best path shows `>`, and the attribute values (localpref, metric, as-path) are printed next to each path. Trace upward through the best-path algorithm to find the deciding step.

### BGP Soft Reset

```
clear ip bgp <neighbor-ip> soft in
clear ip bgp <neighbor-ip> soft out
clear ip bgp * soft
```

| Command | Purpose |
|---------|---------|
| `clear ip bgp <ip> soft in` | Re-apply inbound policy without resetting session |
| `clear ip bgp <ip> soft out` | Re-advertise all prefixes to peer with new outbound policy |

> **Exam tip:** Always use `soft` resets in production. Hard resets (`clear ip bgp <ip>`) drop and re-establish the TCP session, causing a BGP convergence event.

### Common BGP Multihoming Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Both paths show equal LOCAL_PREF (100) | Route-map not applied inbound on primary PE, or `soft in` reset missed |
| R3 path shows as `r` (inaccessible) | Missing `next-hop-self` on R3; R1's eBGP next-hop not in OSPF |
| AS-path prepend not visible on R3's reflected path | Route-map not applied outbound on R1 toward R3 |
| MED values not appearing | Route-map not applied; check `show route-map` counters |
| Primary path not restored after link recovery | Route-map still counting hits — soft reset needed; or BGP hold-down in progress |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Activate R1–R3 Backup eBGP Session

<details>
<summary>Click to view R1 Configuration (Task 1 portion)</summary>

```bash
! R1 — add R3 eBGP peer
router bgp 65001
 neighbor 10.1.13.3 remote-as 65100
 neighbor 10.1.13.3 description PE-East-2-R3-eBGP-backup
 address-family ipv4
  neighbor 10.1.13.3 activate
```
</details>

<details>
<summary>Click to view R3 Configuration (Task 1 portion)</summary>

```bash
! R3 — activate eBGP to R1 and add next-hop-self toward R4
router bgp 65100
 neighbor 10.1.13.1 remote-as 65001
 neighbor 10.1.13.1 description Customer-A-CE-R1-backup
 address-family ipv4
  neighbor 10.1.13.1 activate
  neighbor 10.0.0.4 next-hop-self
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary              ! on R3: R1 session Established, PfxRcd >= 1
show ip bgp 172.16.1.0/24        ! on R4: two paths visible
```
</details>

---

### Task 2: LOCAL_PREF on R2

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — prefix-list and inbound route-map
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24

route-map FROM-CUST-A-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set local-preference 200
route-map FROM-CUST-A-PRIMARY permit 20

router bgp 65100
 address-family ipv4
  neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in

! Activate without session reset
clear ip bgp 10.1.12.1 soft in
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 172.16.1.0/24        ! on R2: localpref 200
show ip bgp 172.16.1.0/24        ! on R4: path via R2 is best (>), LP=200
show route-map FROM-CUST-A-PRIMARY  ! match count should increment
```
</details>

---

### Task 3: AS-Path Prepending on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — prefix-list and outbound route-map toward R3
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24

route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set as-path prepend 65001
route-map TO-R3-BACKUP permit 20

router bgp 65001
 address-family ipv4
  neighbor 10.1.13.3 route-map TO-R3-BACKUP out

clear ip bgp 10.1.13.3 soft out
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 172.16.1.0/24        ! on R3: AS-path shows "65001 65001"
show ip bgp 172.16.1.0/24        ! on R4: R3 path has longer AS-path than R2 path
```
</details>

---

### Task 4: MED on R1

<details>
<summary>Click to view R1 Configuration (full outbound policy)</summary>

```bash
! R1 — complete outbound route-maps with both MED and AS-path prepend
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24

route-map TO-R2-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set metric 10
route-map TO-R2-PRIMARY permit 20

route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set metric 50
 set as-path prepend 65001
route-map TO-R3-BACKUP permit 20

router bgp 65001
 address-family ipv4
  neighbor 10.1.12.2 route-map TO-R2-PRIMARY out
  neighbor 10.1.13.3 route-map TO-R3-BACKUP out

clear ip bgp 10.1.12.2 soft out
clear ip bgp 10.1.13.3 soft out
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 172.16.1.0/24        ! on R2: metric 10
show ip bgp 172.16.1.0/24        ! on R3: metric 50
```
</details>

---

### Task 5: Failover Verification

<details>
<summary>Click to view Failover Steps</summary>

```bash
! Simulate primary link failure
R1(config)# interface GigabitEthernet0/0
R1(config-if)# shutdown

! Wait ~30 seconds for BGP hold-timer, then verify:
show ip bgp summary              ! on R2: R1 neighbor Idle
show ip bgp 172.16.1.0/24        ! on R4: single path via R3 (LP=100), marked >
show ip route bgp                ! on R5: 172.16.1.0/24 via R3's loopback

! Restore primary link
R1(config)# interface GigabitEthernet0/0
R1(config-if)# no shutdown

! After BGP reconvergence:
show ip bgp 172.16.1.0/24        ! on R4: two paths, R2 path (LP=200) is best again
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 apply_solution.py --host <eve-ng-ip>          # restore known-good state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>  # Ticket 2
python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>  # Ticket 3
python3 apply_solution.py --host <eve-ng-ip>          # restore after each ticket
```

---

### Ticket 1 — Customer A Routes from the Eastern Backup PE Are Missing Everywhere

The network team reports that after activating the backup eBGP session on R3, `show ip bgp 172.16.1.0/24` on R4 only shows one path. The R3 session to R1 is Established, but R3's routes never appear in any other router's BGP table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R4 shows two paths (one via R2, one via R3).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip bgp 172.16.1.0/24` — is the prefix in R3's table with a valid next-hop?
   - If next-hop shows `10.1.13.1` (R1's physical IP) and status is `r` — next-hop unreachable.
   - Confirm with `show ip route 10.1.13.1` — route should be absent from OSPF.
2. On R3: `show ip bgp neighbors 10.0.0.4 advertised-routes` — is `172.16.1.0/24` being sent to R4?
   - If the prefix is absent here, the next-hop is not resolvable and the route is not exported.
3. On R3: `show running-config | section router bgp` — check whether `next-hop-self` is configured under the R4 neighbor.
4. Root cause: `neighbor 10.0.0.4 next-hop-self` is missing. Without it, R3 forwards R1's eBGP next-hop (10.1.13.1) into the iBGP fabric. 10.1.13.1 is not reachable via OSPF, so R4 marks the route inaccessible.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# router bgp 65100
R3(config-router)# address-family ipv4
R3(config-router-af)# neighbor 10.0.0.4 next-hop-self

! Trigger R3 to re-advertise to R4 with updated next-hop:
R3# clear ip bgp 10.0.0.4 soft out
```

Verify: `show ip bgp 172.16.1.0/24` on R4 now shows the R3 path with next-hop 10.0.0.3.
</details>

---

### Ticket 2 — Both PEs Appear with Equal Preference in the SP Core's BGP Table

A change window modified R2's BGP policy. Now `show ip bgp 172.16.1.0/24` on R4 shows both the R2 and R3 paths with `localpref 100`. Traffic to Customer A is load-balancing across both PEs instead of consistently using R2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R4 shows the R2 path with `localpref 200` and the `>` best indicator.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip bgp 172.16.1.0/24` — compare `localpref` values on both paths.
   - Both showing `localpref 100` confirms the policy is not being applied on R2.
2. On R2: `show running-config | section router bgp` — check for `neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in`.
3. On R2: `show route-map FROM-CUST-A-PRIMARY` — does the route-map exist? Is the match count 0?
   - If the route-map exists but the match count is 0, the route-map is not applied to the neighbor.
   - If the route-map is absent, it was removed.
4. Root cause: `neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in` is missing from R2's address-family ipv4.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in

R2# clear ip bgp 10.1.12.1 soft in
```

Verify: `show ip bgp 172.16.1.0/24` on R4 shows R2 path with `localpref 200`, marked as best (`>`).
</details>

---

### Ticket 3 — Customer A Prefix Shows Equal AS-Path Length via Both PEs

Operations reports that `show ip bgp 172.16.1.0/24` on R4 shows both the R2 and R3 paths with AS-path `65001` (length 1). The AS-path prepend configuration that should make R3 look less attractive has stopped working.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R3 shows AS-path `65001 65001` (length 2). On R4, the R3 path shows the longer AS-path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip bgp 172.16.1.0/24` — check the AS-path field.
   - If AS-path shows `65001` (single entry), R1 is not prepending.
2. On R1: `show running-config | section router bgp` — check whether `neighbor 10.1.13.3 route-map TO-R3-BACKUP out` is present.
3. On R1: `show route-map TO-R3-BACKUP` — does the route-map exist with a `set as-path prepend` clause?
4. Root cause: the outbound route-map application to the R3 neighbor is missing — `neighbor 10.1.13.3 route-map TO-R3-BACKUP out` was removed from the address-family.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# router bgp 65001
R1(config-router)# address-family ipv4
R1(config-router-af)# neighbor 10.1.13.3 route-map TO-R3-BACKUP out

R1# clear ip bgp 10.1.13.3 soft out
```

Verify: `show ip bgp 172.16.1.0/24` on R3 shows AS-path `65001 65001`. On R4, the R3 path has AS-path length 2, confirming it is not best.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R1–R3 eBGP session Established; R3 receives `172.16.1.0/24` from R1
- [ ] `next-hop-self` on R3 toward R4; R3's path appears on R4 with next-hop `10.0.0.3`
- [ ] R4 shows two paths to `172.16.1.0/24` — one via R2 (LP=200), one via R3 (LP=100)
- [ ] R2 path is consistently best (`>`) due to LOCAL_PREF 200
- [ ] R3 path has AS-path `65001 65001` (length 2); R2 path has `65001` (length 1)
- [ ] R2 shows MED 10; R3 shows MED 50 for `172.16.1.0/24`
- [ ] After shutting R1 Gi0/0, traffic switches to R3 path; route reinstalled via R3
- [ ] After restoring R1 Gi0/0, R2 path reclaims best with LP=200

### Troubleshooting

- [ ] Ticket 1 diagnosed: missing `next-hop-self` on R3; fixed and verified on R4
- [ ] Ticket 2 diagnosed: missing route-map on R2 inbound; fixed and LP=200 restored
- [ ] Ticket 3 diagnosed: missing route-map on R1 outbound to R3; AS-path prepend restored

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
