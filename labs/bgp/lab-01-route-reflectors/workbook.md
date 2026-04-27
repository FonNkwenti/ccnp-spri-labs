# BGP Lab 01 — iBGP Route Reflectors and Cluster IDs

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

**Exam Objective:** 1.4.b — Route reflectors; 1.5.b — Troubleshoot BGP route reflectors

In lab-00 you built a minimal two-PE iBGP mesh. In this lab you scale that design: R4 (the P router) becomes a Route Reflector so that AS 65100's three PEs — R2, R3, and R5 — no longer need direct sessions between every pair. You will also bring R3 fully into the iBGP fabric for the first time.

---

### The Full-Mesh Scaling Problem

iBGP's split-horizon rule requires every router in an AS to have a direct session to every other BGP speaker. The number of sessions grows as N×(N-1)/2:

| PEs | Sessions Required |
|-----|-----------------|
| 2 | 1 |
| 3 | 3 |
| 5 | 10 |
| 10 | 45 |
| 20 | 190 |

Lab-00 used 1 session (R2↔R5). This lab replaces that model with a Route Reflector, reducing the session count as the network grows — the blueprint-1.4 scalability objective.

---

### Route Reflector Architecture

A **Route Reflector (RR)** relaxes the split-horizon rule. Instead of every iBGP speaker requiring a full mesh, clients peer only with the RR, and the RR reflects routes between them.

| Concept | Description |
|---------|-------------|
| Route Reflector (RR) | The central hub that reflects iBGP routes between clients |
| RR Client | A peer configured with `route-reflector-client` on the RR |
| Non-client iBGP peer | A regular iBGP peer of the RR — not tagged as client |
| Cluster | The RR plus its clients (identified by a shared cluster-id) |

**Reflection rules:**

```
Route received FROM a client  → reflected to all other clients AND non-clients
Route received FROM a non-client → reflected to clients only (not to other non-clients)
Route received via eBGP       → sent to all iBGP peers (clients + non-clients)
```

This means clients exchange routes without needing direct sessions between them, as long as the RR is in the path.

**Configuration on the RR:**

```
router bgp 65100
 bgp cluster-id 10.0.0.4
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 route-reflector-client
```

The `route-reflector-client` statement is added on the **RR** for each **client** peer. The client itself needs no special configuration — it simply has a regular iBGP session to the RR.

---

### RR Loop Prevention: ORIGINATOR_ID and CLUSTER_LIST

Without loop prevention, a reflected route could bounce between multiple RRs indefinitely. BGP adds two path attributes to prevent this:

| Attribute | Set By | Value | Purpose |
|-----------|--------|-------|---------|
| ORIGINATOR_ID | First RR to reflect the route | Router-id of the originating iBGP speaker | Client ignores routes with its own router-id as ORIGINATOR_ID |
| CLUSTER_LIST | Every RR that reflects the route | Prepended list of cluster-ids | RR drops routes with its own cluster-id already in the list |

When you run `show ip bgp 172.16.1.0` on R5, a reflected route looks like:

```
BGP routing table entry for 172.16.1.0/24
  ...
  Originator: 10.0.0.2, Cluster list: 10.0.0.4
```

`Originator: 10.0.0.2` = R2 originated this iBGP advertisement.
`Cluster list: 10.0.0.4` = R4 reflected it (its cluster-id).

---

### The cluster-id Attribute

`bgp cluster-id` is set on the RR. When multiple RRs share clients (a redundant design), all RRs in the same cluster must share the same cluster-id so CLUSTER_LIST loop detection works across them. With a single RR (this lab), the cluster-id is conventionally set to the RR's own Loopback0 address.

> **Exam tip:** If `bgp cluster-id` is not configured, IOS uses the BGP router-id as the cluster-id. This is fine for a single-RR design but becomes ambiguous with multiple RRs — always configure it explicitly.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Route Reflector configuration | `bgp cluster-id`, `route-reflector-client` per client neighbor |
| iBGP client peer setup | `update-source Loopback0` on the client side; no special RR statement |
| RR attribute inspection | Reading ORIGINATOR_ID and CLUSTER_LIST from `show ip bgp <prefix>` |
| BGP next-hop-self on ingress PEs | Why PEs (not the RR) apply `next-hop-self` so reflected routes resolve |
| Full-mesh to RR migration | Keeping legacy sessions (additive progressive rule); understanding production cleanup |

---

## 2. Topology & Scenario

**Scenario:** GlobalNet SP (AS 65100) has grown. You now have three PE routers — R2 (East-1), R3 (East-2), and R5 (West) — and the full-mesh requirement is already 3 iBGP sessions. Your network architect has projected 10 PEs within 18 months, which would require 45 sessions. The decision is made to deploy R4 (the P router) as a Route Reflector now, so iBGP session management scales linearly with PE count rather than quadratically.

Your task: migrate the existing minimal iBGP mesh to an RR architecture. The legacy R2↔R5 direct iBGP session from lab-00 remains in place during this lab (the progressive build rule — never remove, only add). A design note is included explaining when production would remove it.

```
     AS 65001              AS 65100 (SP Core, OSPF Area 0)              AS 65002
  ┌─────────────┐  ┌──────────────────────────────────────────────┐  ┌─────────────┐
  │     R1      │  │  ┌──────────┐ L3 ┌──────────┐ L5 ┌────────┐ │  │     R6      │
  │  AS 65001   ├L1┼──┤    R2    ├────┤  R4 (RR) ├────┤   R5   ├─┼L7┤  AS 65002   │
  │ Lo0:10.0.0.1│  │  │ PE East-1│    │ AS 65100 │    │ PE West│ │  │ Lo0:10.0.0.6│
  │ Lo1:172.16.1│  │  │ AS 65100 │    │10.0.0.4  │    │AS 65100│ │  │ Lo1:172.16.6│
  └──────┬──────┘  │  │10.0.0.2  │ L6 │cluster-id│    │10.0.0.5│ │  └─────────────┘
         │         │  └────┬─────┘    └────┬─────┘    └────────┘ │
         │ L2      │       │ L6            │ L4                   │
      (IP-only,    │  ┌────┴───────────────┴──────┐               │
       no BGP      │  │            R3              │               │
       in lab-01)  │  │        PE East-2           │               │
         │         │  │        AS 65100            │               │
         └─────────┼──│        Lo0:10.0.0.3        │               │
                   │  └────────────────────────────┘               │
                   └──────────────────────────────────────────────┘
```

**BGP session overlay (lab-01):**

```
                         ┌──────────────┐
                         │  R4 (RR)     │
                         │ 10.0.0.4     │
                         └──┬───┬───┬───┘
              iBGP (client) │   │   │ iBGP (client)
               ┌────────────┘   │   └──────────────┐
               │          iBGP  │          (client) │
          ┌────┴─────┐   (client)┌──────────┐  ┌───┴────┐
          │  R2      │    │      │  R3      │  │  R5    │
          │10.0.0.2  │    └──────│10.0.0.3  │  │10.0.0.5│
          └────┬─────┘           └──────────┘  └────────┘
               │                                    │
               └────────────────────────────────────┘
                       legacy iBGP (lab-00)
                       kept for lab-01 (additive)
```

**Key relationships:**

- R4 is now both the P router (forwarding plane) and the Route Reflector (BGP control plane).
- R4 peers with R2, R3, and R5 as clients. The RR reflects routes between all clients automatically.
- R3 joins the iBGP fabric for the first time in this lab. Its only iBGP peer is R4.
- R2 and R5 retain the direct legacy iBGP session from lab-00 (both also peer with R4 as RR).
- L2 (R1↔R3) remains IP-only in this lab; the second eBGP path to Customer A is not activated until lab-02.
- `next-hop-self` stays on R2 and R5 toward all iBGP peers, including R4. R4 does NOT set `next-hop-self` — the ingress PE changes the next-hop before the route reaches R4 for reflection.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) — iBGP client in lab-01 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P Router / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) | CSR1000v (IOS-XE) | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

> R5 runs IOS-XE (CSR1000v). Its interface naming differs from IOSv: GigabitEthernet2 and GigabitEthernet3.

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id, eBGP peering source |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A prefix source |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, RR cluster-id |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP peering source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id, eBGP peering source |
| R6 | Loopback1 | 172.16.6.1/24 | External peer prefix source |

### Cabling Table

| Link ID | Source | Interface | Target | Interface | Subnet |
|---------|--------|-----------|--------|-----------|--------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 |
| L2 | R1 | Gi0/1 | R3 | Gi0/0 | 10.1.13.0/24 |
| L3 | R2 | Gi0/1 | R4 | Gi0/0 | 10.1.24.0/24 |
| L4 | R3 | Gi0/1 | R4 | Gi0/1 | 10.1.34.0/24 |
| L5 | R4 | Gi0/2 | R5 | Gi2 | 10.1.45.0/24 |
| L6 | R2 | Gi0/2 | R3 | Gi0/2 | 10.1.23.0/24 |
| L7 | R5 | Gi3 | R6 | Gi0/0 | 10.1.56.0/24 |

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

**IS pre-loaded** (lab-00 complete solution):
- Hostnames (R1 through R6)
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all devices
- OSPF process 1 on R2, R3, R4, R5 (area 0, SP-internal links + Loopback0)
- eBGP session R1↔R2 (AS 65001 ↔ AS 65100) with `network 172.16.1.0/24` on R1
- eBGP session R5↔R6 (AS 65100 ↔ AS 65002) with `network 172.16.6.0/24` on R6
- Legacy iBGP session R2↔R5 (direct, loopback-sourced) with `next-hop-self` on both sides

**IS NOT pre-loaded** (student configures this):
- BGP process on R4 (Route Reflector)
- BGP process on R3 (new iBGP client)
- R4 configured as Route Reflector with cluster-id and client designations for R2, R3, R5
- iBGP sessions from R2 and R5 toward R4

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure R4 as the Route Reflector

Configure a BGP process on R4 in AS 65100. R4 will serve as the Route Reflector for the entire SP core iBGP fabric.

- Set R4's BGP router-id to its Loopback0 address and enable neighbor state-change logging.
- Configure R4 with a cluster-id equal to its own Loopback0 address (10.0.0.4).
- Establish iBGP sessions to R2 (10.0.0.2), R3 (10.0.0.3), and R5 (10.0.0.5), all sourced from Loopback0.
- In the IPv4 unicast address family, designate all three peers as route-reflector clients.

**Verification:** `show ip bgp summary` on R4 must show three iBGP peers (R2, R3, R5) in `Estab` state. `show ip bgp` on R4 must show routes from R1 (172.16.1.0/24) and R6 (172.16.6.0/24).

---

### Task 2: Bring R3 into the iBGP Fabric

Configure a BGP process on R3 in AS 65100. R3's only iBGP peer will be R4 (the RR).

- Set R3's BGP router-id to its Loopback0 address and enable neighbor state-change logging.
- Establish an iBGP session to R4 (10.0.0.4), sourced from Loopback0.
- Activate the session in the IPv4 unicast address family.

**Verification:** `show ip bgp summary` on R3 must show R4 (10.0.0.4) in `Estab` state. `show ip bgp` on R3 must show 172.16.1.0/24 (Customer A prefix, reflected via R4) and 172.16.6.0/24 (external SP peer prefix, reflected via R4).

---

### Task 3: Connect R2 and R5 to the Route Reflector

Add iBGP sessions from R2 and R5 toward R4, keeping the existing legacy direct session between R2 and R5.

- On R2: add R4 (10.0.0.4) as an iBGP peer, sourced from Loopback0. Apply `next-hop-self` toward R4 in the IPv4 unicast address family.
- On R5: add R4 (10.0.0.4) as an iBGP peer, sourced from Loopback0. Apply `next-hop-self` toward R4 in the IPv4 unicast address family.
- Do not remove or modify the existing R2↔R5 direct iBGP session on either router.

**Verification:** `show ip bgp summary` on R2 must show both R4 (10.0.0.4) and R5 (10.0.0.5) as established iBGP peers. `show ip bgp summary` on R5 must show both R4 (10.0.0.4) and R2 (10.0.0.2) as established iBGP peers.

---

### Task 4: Verify End-to-End Reachability via the RR Fabric

Confirm that prefix advertisement reaches all expected endpoints through the RR, not just through the legacy direct session.

- On R3, verify that 172.16.1.0/24 (Customer A) and 172.16.6.0/24 (external peer) are both present in the BGP table and installed in the routing table.
- On R5, verify that 172.16.1.0/24 shows a next-hop of 10.0.0.2 (R2's loopback) — not 10.1.12.1 (R1's physical IP). This confirms `next-hop-self` is working.
- Confirm `ping 172.16.1.1` from R6 succeeds (end-to-end path: R6 → R5 → R4 → R2 → R1).

**Verification:** `show ip route bgp` on R3 must include both prefixes. `show ip bgp 172.16.1.0` on R5 must show `Next Hop: 10.0.0.2`.

---

### Task 5: Inspect RR Attributes and Analyze the Legacy Session

Use BGP show commands to observe how the RR adds loop-prevention attributes to reflected routes, and document the design implication of the legacy session.

- On R5, run `show ip bgp 172.16.1.0` and locate the `Originator` and `Cluster list` fields.
- On R3, run `show ip bgp 172.16.6.0` and locate the same fields.
- Identify which value represents R2's router-id and which represents R4's cluster-id.
- In your lab notes, write a one-sentence answer: why does the legacy R2↔R5 direct session persist, and what would need to happen before it could be safely removed in production?

**Verification:** `show ip bgp 172.16.1.0` on R5 shows `Originator: 10.0.0.2` and `Cluster list: 10.0.0.4`. `show ip bgp 172.16.6.0` on R3 shows `Originator: 10.0.0.5` and `Cluster list: 10.0.0.4`.

---

## 6. Verification & Analysis

### Task 1 — R4 as Route Reflector

```
R4# show ip bgp summary
BGP router identifier 10.0.0.4, local AS number 65100
...
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.2        4 65100      12      12        4    0    0 00:04:21  1       ! ← R2 Estab, 1 prefix (172.16.1.0/24)
10.0.0.3        4 65100       8       8        4    0    0 00:03:10  0       ! ← R3 Estab, 0 prefixes (R3 has no eBGP yet)
10.0.0.5        4 65100      10      10        4    0    0 00:03:55  1       ! ← R5 Estab, 1 prefix (172.16.6.0/24)

R4# show ip bgp
BGP table version is 4, local router ID is 10.0.0.4
     Network          Next Hop            Metric LocPrf Weight Path
 *>i 172.16.1.0/24   10.0.0.2                 0    100      0 65001 i  ! ← via R2 (iBGP client)
 *>i 172.16.6.0/24   10.0.0.5                 0    100      0 65002 i  ! ← via R5 (iBGP client)
```

### Task 2 — R3 in the iBGP Fabric

```
R3# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.4        4 65100      10      10        4    0    0 00:03:20  2       ! ← R4 Estab; 2 prefixes reflected

R3# show ip bgp
     Network          Next Hop            Metric LocPrf Weight Path
 *>i 172.16.1.0/24   10.0.0.2                 0    100      0 65001 i  ! ← next-hop = R2 loopback (OSPF-reachable)
 *>i 172.16.6.0/24   10.0.0.5                 0    100      0 65002 i  ! ← next-hop = R5 loopback (OSPF-reachable)
```

### Task 3 — R2 and R5 Connected to RR

```
R2# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.12.1       4 65001      10       9        4    0    0 00:05:11  1       ! ← R1 eBGP Estab
10.0.0.4        4 65100       9       9        4    0    0 00:03:44  1       ! ← R4 (RR) iBGP Estab
10.0.0.5        4 65100       8       8        4    0    0 00:04:01  1       ! ← R5 legacy iBGP Estab

R5# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.56.6       4 65002      10       9        4    0    0 00:05:20  1       ! ← R6 eBGP Estab
10.0.0.4        4 65100       9       9        4    0    0 00:03:55  1       ! ← R4 (RR) iBGP Estab
10.0.0.2        4 65100       8       8        4    0    0 00:04:10  1       ! ← R2 legacy iBGP Estab
```

### Task 4 — End-to-End Reachability

```
R3# show ip route bgp
      172.16.0.0/24 is subnetted, 2 subnets
B        172.16.1.0 [200/0] via 10.0.0.2, 00:03:10   ! ← installed, AD=200 (iBGP), next-hop = R2 loopback
B        172.16.6.0 [200/0] via 10.0.0.5, 00:03:10   ! ← installed, AD=200 (iBGP), next-hop = R5 loopback

R5# show ip bgp 172.16.1.0
BGP routing table entry for 172.16.1.0/24, version 3
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001
    10.0.0.2 (metric 3) from 10.0.0.4 (10.0.0.4)   ! ← path via RR (10.0.0.4)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Originator: 10.0.0.2, Cluster list: 10.0.0.4  ! ← RR attributes: originator=R2, cluster=R4
  65001
    10.0.0.2 (metric 3) from 10.0.0.2 (10.0.0.2)   ! ← path via legacy direct R2 session
      Origin IGP, metric 0, localpref 100, valid, internal
```

### Task 5 — RR Attribute Inspection

```
R3# show ip bgp 172.16.6.0
BGP routing table entry for 172.16.6.0/24, version 4
Paths: (1 available, best #1, table default)
  65002
    10.0.0.5 (metric 3) from 10.0.0.4 (10.0.0.4)   ! ← reflected by R4
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Originator: 10.0.0.5, Cluster list: 10.0.0.4  ! ← R5 originated; R4 reflected
```

> **Design note — legacy R2↔R5 session:** The direct session persists in this lab because the progressive build rule disallows removing config. In production, you would remove it once the RR is verified stable — the RR provides the same connectivity with fewer sessions and without requiring `next-hop-self` to be tuned separately on each PE pair.

---

## 7. Verification Cheatsheet

### Route Reflector Configuration

```
router bgp 65100
 bgp cluster-id <rr-loopback>
 neighbor <client-ip> remote-as 65100
 neighbor <client-ip> update-source Loopback0
 !
 address-family ipv4
  neighbor <client-ip> activate
  neighbor <client-ip> route-reflector-client
```

| Command | Purpose |
|---------|---------|
| `bgp cluster-id <id>` | Identifies this router's RR cluster; prevents reflection loops in multi-RR designs |
| `neighbor X route-reflector-client` | Marks peer as RR client — must be on the RR, not the client |
| `neighbor X update-source Loopback0` | Sources TCP session from loopback for resilience |

> **Exam tip:** `route-reflector-client` is configured on the **RR**, in the address-family. The client itself has no special configuration — it just has a regular iBGP session to the RR.

### Client Configuration (no special RR statements)

```
router bgp 65100
 neighbor <rr-loopback> remote-as 65100
 neighbor <rr-loopback> update-source Loopback0
 !
 address-family ipv4
  neighbor <rr-loopback> activate
  neighbor <rr-loopback> next-hop-self   ! only on ingress PEs (R2, R5)
```

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp summary` | All iBGP peers in `Estab` state; non-zero `PfxRcd` on clients |
| `show ip bgp` | `*>i` prefix status code: valid, best, internal (iBGP-learned) |
| `show ip bgp <prefix>` | `Originator` and `Cluster list` fields on reflected routes |
| `show ip route bgp` | Prefix with `[200/0]` in RIB confirms iBGP install (AD=200) |
| `show ip bgp neighbors <ip> | include source` | Confirms `update-source` is Loopback0 |
| `show tcp brief` | TCP session source IP for BGP — must be loopback, not physical interface |

### BGP Status Codes Quick Reference

| Code | Meaning |
|------|---------|
| `*` | Valid route (next-hop reachable) |
| `>` | Best path |
| `i` | Learned via iBGP |
| `r` | Next-hop unreachable (route in BGP table but NOT in RIB) |

### Common Route Reflector Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Client has Estab session to RR but BGP table empty | `route-reflector-client` missing on RR for that client |
| RR session stays in Active | `update-source Loopback0` missing on client or RR; loopback not in OSPF |
| Prefix in BGP table but not RIB (`r` status) | `next-hop-self` missing on ingress PE — next-hop is a physical IP not in OSPF |
| Routes present but ORIGINATOR_ID is own router-id | Route reflecting loop — check CLUSTER_LIST for own cluster-id |
| Symmetric failure (no prefixes on either side) | iBGP session never formed; check `bgp router-id`, `update-source`, MTU |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: R4 Route Reflector Configuration

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — add BGP process as Route Reflector
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 bgp cluster-id 10.0.0.4
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 description iBGP-RR-client-R2
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 description iBGP-RR-client-R3
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.5 remote-as 65100
 neighbor 10.0.0.5 description iBGP-RR-client-R5
 neighbor 10.0.0.5 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 route-reflector-client
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 route-reflector-client
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.5 route-reflector-client
 exit-address-family
```

</details>

<details>
<summary>Click to view Verification</summary>

```bash
show ip bgp summary                   ! three peers Estab
show ip bgp                           ! 172.16.1.0/24 and 172.16.6.0/24 present
show run | section router bgp         ! confirm cluster-id and route-reflector-client
```

</details>

---

### Task 2: R3 iBGP Client Configuration

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — add BGP process as RR client
router bgp 65100
 bgp router-id 10.0.0.3
 bgp log-neighbor-changes
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view Verification</summary>

```bash
show ip bgp summary                   ! R4 in Estab, PfxRcd = 2
show ip bgp                           ! both prefixes present
show ip route bgp                     ! both prefixes in RIB with [200/0]
```

</details>

---

### Task 3: R2 and R5 — Add RR Sessions

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — add iBGP session toward R4 (keep existing R5 session)
router bgp 65100
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
 exit-address-family
```

</details>

<details>
<summary>Click to view R5 Configuration (IOS-XE)</summary>

```bash
! R5 — add iBGP session toward R4 (keep existing R2 session)
router bgp 65100
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
 exit-address-family
```

</details>

<details>
<summary>Click to view Verification</summary>

```bash
! On R2
show ip bgp summary     ! R4 (10.0.0.4) and R5 (10.0.0.5) both Estab

! On R5
show ip bgp summary     ! R4 (10.0.0.4) and R2 (10.0.0.2) both Estab
```

</details>

---

### Task 4: End-to-End Reachability

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R3 — confirm both prefixes installed in RIB
show ip route bgp

! On R5 — confirm next-hop of reflected route is R2's loopback, not R1's physical IP
show ip bgp 172.16.1.0

! On R6 — confirm end-to-end path
ping 172.16.1.1 source 172.16.6.1
```

</details>

---

### Task 5: RR Attribute Inspection

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R5 — view ORIGINATOR_ID and CLUSTER_LIST for Customer A prefix
show ip bgp 172.16.1.0
! Expected: Originator: 10.0.0.2, Cluster list: 10.0.0.4

! On R3 — view RR attributes for the external SP peer prefix
show ip bgp 172.16.6.0
! Expected: Originator: 10.0.0.5, Cluster list: 10.0.0.4
```

**Design note — legacy session removal:**
The direct R2↔R5 iBGP session would be removed in production once the RR is verified stable for at least one maintenance window. Removal requires coordinated `clear ip bgp` resets and validation that no route is exclusively sourced from the direct session. In lab-01 the session remains, consistent with the progressive build rule.

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — R3 Has an Established Session to R4 but Its BGP Table Is Empty

The NOC reports that R3 was recently brought into the iBGP fabric but `show ip bgp` on R3 shows no prefixes — even though R4's `show ip bgp summary` confirms the session is Established with R3.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp` on R3 shows both 172.16.1.0/24 and 172.16.6.0/24 as best (`*>i`) routes, and both are installed in the routing table.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R3 — session with R4 is `Estab` but `PfxRcd = 0`. Session is up but R4 is not sending any routes.
2. `show ip bgp summary` on R4 — R3 shows as `Estab` with `0` prefixes sent/received from R3. On R4, run `show ip bgp neighbors 10.0.0.3 | include reflector`. If the output is empty (no `Route-Reflector Client` line), R3 has NOT been designated as a client.
3. `show running-config | section router bgp` on R4 — check whether `neighbor 10.0.0.3 route-reflector-client` is present in the `address-family ipv4` stanza.
4. The fault: the `route-reflector-client` statement is missing for neighbor 10.0.0.3 on R4. Because R3 is treated as a non-client iBGP peer, R4 applies split-horizon and does not re-advertise iBGP-learned routes to R3 (non-clients only receive routes from eBGP sources and from clients, not from other non-clients).

</details>

<details>
<summary>Click to view Fix</summary>

On R4, add the missing `route-reflector-client` designation for R3:

```bash
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.3 route-reflector-client
```

Verify: `show ip bgp` on R3 now shows both prefixes. `show ip bgp neighbors 10.0.0.3 | include reflector` on R4 shows `Route-Reflector Client`.

</details>

---

### Ticket 2 — R3's iBGP Session to R4 Stays in Active State

After a configuration change, the NOC reports that R3 cannot establish its iBGP session to R4. `show ip bgp summary` on R3 shows neighbor 10.0.0.4 permanently in `Active` state. R4's session to R3 is also `Active`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp summary` on R3 shows neighbor 10.0.0.4 in `Estab` state with `PfxRcd = 2`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R3 — 10.0.0.4 is in `Active` state. BGP is attempting TCP but not completing.
2. `show ip bgp neighbors 10.0.0.4 | include source` on R3 — check whether `update-source` is configured. If not shown, R3's TCP connection originates from a physical interface IP.
3. `show ip ospf neighbor` on R3 — confirm R4 is an OSPF neighbor (10.1.34.4). OSPF is up, so 10.0.0.4 is reachable, but only via OSPF-advertised loopbacks.
4. `show tcp brief` on R3 — observe the source IP of the TCP connection to 10.0.0.4. If the source is 10.1.34.3 (physical interface) instead of 10.0.0.3 (loopback), R4 rejects the connection — R4 expects TCP from 10.0.0.3.
5. The fault: `update-source Loopback0` is missing on R3 for neighbor 10.0.0.4. R3 sources the TCP session from its physical egress interface, R4 only accepts connections from R3's loopback (10.0.0.3), so the session is rejected.

</details>

<details>
<summary>Click to view Fix</summary>

On R3, add the missing `update-source` directive:

```bash
router bgp 65100
 neighbor 10.0.0.4 update-source Loopback0
```

Verify: `show ip bgp summary` on R3 shows R4 in `Estab` state. `show tcp brief` on R3 shows the BGP TCP session sourced from 10.0.0.3.

</details>

---

### Ticket 3 — Prefixes Appear in the BGP Table but Are Not Installed in the Routing Table

A junior engineer reports that `show ip bgp` on R3 shows 172.16.1.0/24, but `show ip route bgp` is empty and pings to 172.16.1.1 from R3 fail. The BGP session to R4 is Established.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip route bgp` on R3 shows 172.16.1.0/24 and 172.16.6.0/24 installed with next-hops 10.0.0.2 and 10.0.0.5 respectively.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp` on R3 — 172.16.1.0/24 has status `r>i` or just `ri`. The `r` code means the next-hop is unresolvable.
2. `show ip bgp 172.16.1.0` on R3 — observe the `Next Hop` field. If it shows `10.1.12.1` (R1's physical interface IP on L1), the next-hop is not in the OSPF domain and cannot be resolved.
3. `show ip route 10.1.12.1` on R3 — returns nothing. The 10.1.12.0/24 subnet is not in OSPF (it is a customer-facing link, not a core SP link).
4. `show ip bgp neighbors 10.0.0.2 | include next` on R4 — check whether `next-hop-self` is set on R2's iBGP neighbor for R4. If `next-hop-self` is missing, R2 advertises Customer A's prefix to R4 with the original eBGP next-hop (R1's physical IP), and R4 reflects that unchanged next-hop to all clients.
5. `show running-config | section router bgp` on R2 — confirm `neighbor 10.0.0.4 next-hop-self` is absent from address-family ipv4.
6. The fault: `next-hop-self` was removed from R2 for its iBGP neighbors. Without it, routes from Customer A (AS 65001) are reflected with next-hop = 10.1.12.1 — a physical IP that exists only on L1, not in OSPF.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, restore `next-hop-self` for all iBGP neighbors:

```bash
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.5 next-hop-self
```

Verify: `show ip bgp 172.16.1.0` on R3 now shows `Next Hop: 10.0.0.2`. `show ip route bgp` on R3 shows both prefixes installed.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R4 has `router bgp 65100` with `bgp cluster-id 10.0.0.4`
- [ ] R4 has three iBGP peers (R2: 10.0.0.2, R3: 10.0.0.3, R5: 10.0.0.5), all as `route-reflector-client`
- [ ] R3 has `router bgp 65100` with one iBGP peer (R4: 10.0.0.4)
- [ ] R2 has iBGP sessions to both R4 (new RR) and R5 (legacy direct)
- [ ] R5 has iBGP sessions to both R4 (new RR) and R2 (legacy direct)
- [ ] `show ip bgp summary` on R4 shows three Estab iBGP peers
- [ ] `show ip bgp summary` on R3 shows R4 Estab with PfxRcd = 2
- [ ] `show ip route bgp` on R3 shows both prefixes installed with [200/0]
- [ ] `show ip bgp 172.16.1.0` on R5 shows `Originator: 10.0.0.2, Cluster list: 10.0.0.4`
- [ ] `show ip bgp 172.16.6.0` on R3 shows `Originator: 10.0.0.5, Cluster list: 10.0.0.4`
- [ ] `ping 172.16.1.1 source 172.16.6.1` from R6 succeeds (end-to-end path)

### Troubleshooting

- [ ] Ticket 1: Identified missing `route-reflector-client` on R4 for R3; restored and verified
- [ ] Ticket 2: Identified missing `update-source Loopback0` on R3; restored and verified session
- [ ] Ticket 3: Identified missing `next-hop-self` on R2; restored and verified prefix installation in RIB

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
