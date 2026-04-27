# Lab 00 — eBGP and iBGP Foundations

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

**Exam Objective:** 1.4 — Describe the BGP scalability and performance; 1.5 / 1.5.a — Troubleshoot BGP route advertisement (300-510)

This lab establishes the foundational BGP topology used throughout the entire BGP chapter. You will configure the SP-core IGP, bring up your first eBGP sessions (customer-facing and external-peer-facing), wire up a minimal iBGP mesh, and trace a customer prefix all the way from Customer A to the external SP peer. The concepts introduced here — especially the iBGP full-mesh requirement and next-hop handling — are the root cause of most BGP faults you will diagnose in labs 01 through 08.

---

### eBGP vs iBGP — the Fundamental Split

BGP runs two modes distinguished only by whether the remote AS number matches your own:

| Property | eBGP | iBGP |
|---|---|---|
| Remote AS | Different from local | Same as local |
| AD | 20 | 200 |
| Next-hop behavior | Next-hop set to egress interface IP | Next-hop **unchanged** by default |
| TTL default | 1 (single-hop only) | 255 |
| Loop prevention | AS-path (ASPATH_LOOP) | Split horizon (no re-advertisement to iBGP peers) |
| Typical peering | Direct connected links | Loopback addresses (multi-hop via IGP) |

The next-hop difference is the single biggest source of iBGP problems. When R2 receives 172.16.1.0/24 from R1 via eBGP, the route's next-hop is R1's address (10.1.12.1). When R2 re-advertises this route to R5 via iBGP, the next-hop stays at 10.1.12.1 by default. R5 has no route to 10.1.12.1 (it is not in OSPF), so the route is installed but unusable. The fix is `next-hop-self`: R2 replaces the eBGP next-hop with its own Loopback0 address when advertising to iBGP peers, giving R5 a reachable next-hop via OSPF.

---

### iBGP Split Horizon and the Full-Mesh Requirement

iBGP does not re-advertise routes learned from one iBGP peer to another iBGP peer. This is called the iBGP split-horizon rule, and it exists to prevent routing loops inside an AS. The consequence: every iBGP speaker must peer directly with every other iBGP speaker — the full mesh.

For N iBGP routers, the number of required sessions is:

```
Sessions = N × (N − 1) / 2
```

| Routers | Sessions |
|---|---|
| 2 | 1 |
| 4 | 6 |
| 6 | 15 |
| 10 | 45 |
| 50 | 1225 |

This lab builds a minimal iBGP mesh (R2↔R5, just 1 session) to get prefix reachability working. Lab 01 introduces Route Reflectors to collapse the full-mesh requirement to O(N) sessions — the scalable SP solution.

---

### iBGP Peering on Loopbacks — Why It Matters

iBGP sessions between PEs in a real SP network always peer on loopback addresses, not physical interface IPs. The reasons:

1. **Resilience:** If a physical link fails but the router is still reachable via an alternate path through the IGP, the iBGP session stays up.
2. **Stability:** Loopback0 is always Up/Up as long as the router is powered. Physical interfaces can flap.
3. **Consistency:** Route-reflectors, communities, and policies are built around stable router identifiers (typically Loopback0 = the BGP Router-ID).

To peer on loopbacks, two things are required:
- `neighbor X.X.X.X update-source Loopback0` — forces TCP to source from Loopback0 instead of the egress physical interface.
- The loopback address must be reachable in the IGP (OSPF in this topology).

Without `update-source`, the TCP session sources from the outgoing interface IP. The remote peer's `neighbor` statement points to the loopback — so the source IP doesn't match, and the session is rejected.

---

### OSPF as the iBGP Underlay

BGP does not discover next-hops itself — it relies on the IGP to provide reachability to the next-hop addresses in the BGP table. In this lab, OSPF area 0 serves that role:

- R2, R3, R4, R5 all run OSPF area 0 on SP-internal links and Loopback0.
- This ensures every PE knows how to reach every other PE's Loopback0.
- iBGP sessions peer on these loopback addresses.
- Customer-facing links (R1↔R2, R1↔R3) and external-peer links (R5↔R6) are **not** in OSPF — they remain in their respective AS boundary.

**Skills this lab develops:**

| Skill | Description |
|---|---|
| OSPF area 0 deployment | Configuring OSPF on SP-core links and loopbacks as an iBGP underlay |
| eBGP session bring-up | Configuring eBGP peering on directly connected links |
| iBGP loopback peering | Using `update-source Loopback0` and verifying TCP source consistency |
| BGP next-hop-self | Replacing eBGP next-hop so iBGP peers have a reachable forwarding address |
| BGP prefix advertisement | Using the `network` statement with exact RIB match to inject prefixes |
| Route-path tracing | Chasing a prefix through `show ip bgp` across three ASes |

---

## 2. Topology & Scenario

**Scenario:** You have just joined the SP engineering team for TelcoCore (AS 65100). The network is at day zero. The SP core routers (R2, R3, R4, R5) are physically cabled and running with IP addresses only. Customer A (AS 65001, represented by R1) is dual-homed to PE East-1 (R2) and PE East-2 (R3), but only the primary path (R1↔R2) carries BGP in this lab. External SP peer TelcoWest (AS 65002, represented by R6) connects to PE West (R5).

Your job today: bring up the IGP, establish the eBGP and iBGP sessions, advertise Customer A's prefix (172.16.1.0/24) end-to-end, and document the full-mesh scaling problem that will drive the Route Reflector design in lab 01.

```
     AS 65001              AS 65100 (SP Core, OSPF Area 0)              AS 65002
  ┌─────────────┐  ┌──────────────────────────────────────────────┐  ┌─────────────┐
  │     R1      │  │  ┌──────────┐ L3 ┌──────────┐ L5 ┌────────┐ │  │     R6      │
  │  AS 65001   ├L1┼──┤    R2    ├────┤    R4    ├────┤   R5   ├─┼L7┤  AS 65002   │
  │ Lo0:10.0.0.1│  │  │ PE East-1│    │ P Router │    │ PE West│ │  │ Lo0:10.0.0.6│
  │ Lo1:172.16.1│  │  │ AS 65100 │    │ AS 65100 │    │AS 65100│ │  │ Lo1:172.16.6│
  └──────┬──────┘  │  │10.0.0.2  │ L6 │10.0.0.4  │    │10.0.0.5│ │  └─────────────┘
         │         │  └────┬─────┘    └────┬─────┘    └────────┘ │
         │ L2      │       │ L6            │ L4                   │
      (IP-only,    │  ┌────┴───────────────┴──────┐               │
       no BGP      │  │            R3              │               │
       in lab-00)  │  │        PE East-2           │               │
         │         │  │        AS 65100            │               │
         └─────────┼──│        Lo0:10.0.0.3        │               │
                   │  └────────────────────────────┘               │
                   └──────────────────────────────────────────────┘
```

**Key relationships for lab-00:**

- R1↔R2 (L1, 10.1.12.0/24): The only active eBGP session for Customer A in this lab. R1's L2 link to R3 is IP-addressed but carries no BGP until lab-02.
- R2↔R4↔R5 (L3, L5): OSPF path providing loopback reachability for the R2↔R5 iBGP session.
- R2↔R3 (L6, 10.1.23.0/24): OSPF IGP link between East PEs (no iBGP in lab-00; R3 is OSPF-only).
- R5↔R6 (L7, 10.1.56.0/24): The eBGP session toward external SP peer AS 65002.
- iBGP R2↔R5: The single iBGP session carrying Customer A's prefix from the East PE to the West PE.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) — OSPF only in lab-00 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P Router (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) | CSR1000v (IOS-XE) | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

> R5 runs IOS-XE (CSR1000v) to support BGP FlowSpec NLRI in lab-05. Its interface naming
> differs from IOSv: GigabitEthernet2 and GigabitEthernet3 (not Gi0/0, Gi0/1).

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id, eBGP peering source |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A prefix source |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id (OSPF only in lab-00) |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id (P router, no BGP in lab-00) |
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

**IS pre-loaded:**
- Hostnames (R1 through R6)
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all devices

**IS NOT pre-loaded** (student configures this):
- OSPF routing process and area assignments on SP-core routers
- eBGP sessions (R1↔R2 and R5↔R6)
- iBGP session (R2↔R5) using loopback source addressing
- BGP prefix advertisements (172.16.1.0/24 from R1; 172.16.6.0/24 from R6)
- BGP next-hop-self for iBGP propagation

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure OSPF on the SP Core

Configure OSPF process 1 in area 0 on all AS 65100 routers (R2, R3, R4, R5). Include all SP-internal links and the Loopback0 address of each router. Do not include customer-facing links (toward R1) or external-peer links (toward R6) in OSPF.

Assign a stable router-id on each router equal to its Loopback0 address.

**Verification:** `show ip ospf neighbor` on R4 must show three FULL adjacencies (to R2, R3, and R5). `show ip route ospf` on R2 must include R5's loopback (10.0.0.5/32).

---

### Task 2: Bring Up eBGP — Customer A and External Peer

Establish the eBGP session between R1 (AS 65001) and R2 (AS 65100) using their directly connected addresses on the 10.1.12.0/24 subnet.

Establish the eBGP session between R5 (AS 65100) and R6 (AS 65002) using their directly connected addresses on the 10.1.56.0/24 subnet.

On each router, set the BGP router-id to its Loopback0 address and enable neighbor state-change logging.

**Verification:** `show ip bgp summary` on R2 must show R1 (10.1.12.1) in state `Estab`. `show ip bgp summary` on R5 must show R6 (10.1.56.6) in state `Estab`.

---

### Task 3: Configure Minimal iBGP Between R2 and R5

Configure a direct iBGP session between R2 and R5 using their Loopback0 addresses (10.0.0.2 and 10.0.0.5). Both routers are in AS 65100.

Configure both sides to source the TCP connection from their Loopback0 interface, ensuring session resilience across the IGP path.

Configure both sides so that the next-hop advertised to the iBGP peer is the advertising router's own loopback address, not the original eBGP next-hop. This ensures the remote iBGP peer can resolve the forwarding address via OSPF.

**Verification:** `show ip bgp summary` on R2 must show 10.0.0.5 in state `Estab`. `show ip bgp neighbors 10.0.0.5 | include BGP state` must confirm `Established`.

---

### Task 4: Advertise Customer Prefixes into BGP

Configure R1 to advertise its customer network (172.16.1.0/24, learned from Loopback1) into BGP toward AS 65100.

Configure R6 to advertise its external-peer network (172.16.6.0/24, learned from Loopback1) into BGP toward AS 65100.

For the advertisement to work, the exact prefix must be present in the router's routing table as a connected or static route.

**Verification:** `show ip bgp` on R6 must show 172.16.1.0/24 with AS-path `65100 65001`. `show ip bgp` on R1 must show 172.16.6.0/24 with AS-path `65100 65002`.

---

### Task 5: Identify the Full-Mesh Scaling Problem

Without making any configuration changes, analyze the current iBGP design. With only R2 and R5 in iBGP, the session count is 1. If you were to add R3, R4, and a fourth PE, calculate the total sessions required to maintain a full mesh and record this in your lab notes. Describe why the iBGP split-horizon rule makes the full mesh mandatory and explain what problem this would create in a real SP network with dozens of PEs.

**Verification:** No config changes needed. This is a design analysis task. Document your answer in a lab notes file and be ready to explain it to the instructor. The answer motivates lab-01 (Route Reflectors).

---

## 6. Verification & Analysis

### Task 1 Verification — OSPF Adjacencies on R4

```
R4# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/DR         00:00:33    10.1.24.2       GigabitEthernet0/0  ! ← R2 must be FULL
10.0.0.3          1   FULL/DR         00:00:31    10.1.34.3       GigabitEthernet0/1  ! ← R3 must be FULL
10.0.0.5          1   FULL/DR         00:00:36    10.1.45.5       GigabitEthernet0/2  ! ← R5 must be FULL
```

```
R2# show ip route ospf
O     10.0.0.3/32 [110/2] via 10.1.23.3, 00:05:12, GigabitEthernet0/2  ! ← R3 loopback
O     10.0.0.4/32 [110/2] via 10.1.24.4, 00:05:12, GigabitEthernet0/1  ! ← R4 loopback
O     10.0.0.5/32 [110/3] via 10.1.24.4, 00:05:12, GigabitEthernet0/1  ! ← R5 loopback must be reachable
O     10.1.34.0/24 [110/2] via 10.1.24.4, 00:05:12, GigabitEthernet0/1
O     10.1.45.0/24 [110/2] via 10.1.24.4, 00:05:12, GigabitEthernet0/1
```

### Task 2 Verification — eBGP Sessions

```
R2# show ip bgp summary
BGP router identifier 10.0.0.2, local AS number 65100
...
Neighbor        V    AS  MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down  State/PfxRcd
10.1.12.1       4  65001      12       12       3    0     0  00:04:31        1  ! ← R1 Established, 1 prefix
10.0.0.5        4  65100       8        8       3    0     0  00:02:10        0  ! ← R5 iBGP Established
```

```
R5# show ip bgp summary
BGP router identifier 10.0.0.5, local AS number 65100
...
Neighbor        V    AS  MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down  State/PfxRcd
10.1.56.6       4  65002      10       10       4    0     0  00:03:20        1  ! ← R6 Established, 1 prefix
10.0.0.2        4  65100       8        8       4    0     0  00:02:10        1  ! ← R2 iBGP Established
```

### Task 3 Verification — iBGP Next-Hop Behavior

```
R5# show ip bgp 172.16.1.0
BGP routing table entry for 172.16.1.0/24
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001
    10.0.0.2 from 10.0.0.2 (10.0.0.2)   ! ← next-hop is R2's loopback (next-hop-self in effect)
      Origin IGP, localpref 100, valid, internal, best
      rx pathid: 0, tx pathid: 0x0
```

```
R5# show ip bgp neighbors 10.0.0.2 | include BGP state
  BGP state = Established, up for 00:02:10   ! ← must be Established
```

### Task 4 Verification — End-to-End Prefix Propagation

```
R6# show ip bgp
BGP table version is 3, local router ID is 10.0.0.6
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
Origin codes: i - IGP, e - EGP, ? - incomplete

   Network          Next Hop            Metric LocPrf Weight Path
*> 172.16.1.0/24    10.1.56.5                              0 65100 65001 i  ! ← Customer A prefix, path via AS 65100 then 65001
*> 172.16.6.0/24    0.0.0.0                  0         32768 i
```

```
R1# show ip bgp
BGP table version is 3, local router ID is 10.0.0.1
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 172.16.1.0/24    0.0.0.0                  0         32768 i
*> 172.16.6.0/24    10.1.12.2                              0 65100 65002 i  ! ← External peer prefix, path via AS 65100 then 65002
```

---

## 7. Verification Cheatsheet

### OSPF Process and Adjacency

```
router ospf 1
 router-id <loopback-ip>
 network <subnet> <wildcard> area 0
```

| Command | Purpose |
|---|---|
| `show ip ospf neighbor` | Verify adjacency states (need FULL) |
| `show ip ospf database` | Inspect LSA database |
| `show ip route ospf` | Confirm OSPF-learned routes including remote loopbacks |
| `show ip ospf interface brief` | Verify which interfaces are running OSPF |

> **Exam tip:** An iBGP session on loopbacks will not form unless the loopback is reachable in the IGP. Always verify `show ip route ospf` includes the remote loopback before troubleshooting BGP.

### eBGP Configuration

```
router bgp <local-as>
 bgp router-id <loopback-ip>
 bgp log-neighbor-changes
 neighbor <peer-ip> remote-as <remote-as>
 neighbor <peer-ip> description <label>
 address-family ipv4
  network <prefix> mask <mask>
  neighbor <peer-ip> activate
 exit-address-family
```

| Command | Purpose |
|---|---|
| `show ip bgp summary` | Session state, prefix counts |
| `show ip bgp neighbors <ip>` | Full session detail, timers, counters |
| `show ip bgp neighbors <ip> advertised-routes` | What this router sends to the peer |
| `show ip bgp neighbors <ip> received-routes` | What the peer sends (requires `soft-reconfiguration inbound`) |
| `show ip bgp <prefix>` | Best-path selection detail for a specific prefix |

> **Exam tip:** eBGP sessions use TTL=1 by default — the peer must be directly connected (or use `ebgp-multihop`). Verify `show ip bgp neighbors <ip> | include TTL`.

### iBGP Loopback Peering

```
neighbor <loopback-ip> remote-as <same-as>
neighbor <loopback-ip> update-source Loopback0
address-family ipv4
 neighbor <loopback-ip> activate
 neighbor <loopback-ip> next-hop-self
exit-address-family
```

| Command | Purpose |
|---|---|
| `show ip bgp neighbors <ip> | include source` | Confirm update-source is Loopback0 |
| `show ip bgp <prefix>` | Verify next-hop is the iBGP peer's loopback (not the original eBGP next-hop) |
| `show tcp brief` | Confirm TCP session is sourced from Loopback0 IP |

> **Exam tip:** Missing `update-source Loopback0` causes the session to source from the physical egress interface. The remote peer only listens on the loopback — so the session is never accepted. Symptom: session stays in Active indefinitely.

### Verification Commands

| Command | What to Look For |
|---|---|
| `show ip bgp summary` | All peers must show a numeric prefix count (not Idle/Active) |
| `show ip bgp` | 172.16.1.0/24 with `>` (best) on R5 and R6; 172.16.6.0/24 on R2 and R1 |
| `show ip bgp <prefix>` | Next-hop must be an OSPF-reachable address; path shows correct AS sequence |
| `show ip ospf neighbor` | R4 must have three FULL neighbors |
| `show ip route 172.16.1.0` | R6 must show this route via 10.1.56.5 (R5 eBGP next-hop) |

### Common BGP Failure Causes

| Symptom | Likely Cause |
|---|---|
| Session stays in Active | Wrong remote-as, unreachable peer, or ACL blocking TCP/179 |
| Session Established but no prefixes | `neighbor activate` missing in `address-family ipv4` |
| Prefix in BGP table but not in RIB | Next-hop unresolvable (missing `next-hop-self` or IGP gap) |
| iBGP session won't form | `update-source Loopback0` missing; loopback not in OSPF |
| Prefix not advertised by R1 | `network` statement doesn't exactly match the prefix in the RIB |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: OSPF on the SP Core

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 router-id 10.0.0.2
 network 10.0.0.2 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.23.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospf 1
 router-id 10.0.0.3
 network 10.0.0.3 0.0.0.0 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 10.1.23.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 router-id 10.0.0.4
 network 10.0.0.4 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 10.1.45.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router ospf 1
 router-id 10.0.0.5
 network 10.0.0.5 0.0.0.0 area 0
 network 10.1.45.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf neighbor
show ip route ospf
show ip ospf interface brief
```
</details>

---

### Task 2: eBGP Sessions

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router bgp 65001
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65100
 neighbor 10.1.12.2 description PE-East-1-R2-eBGP
 address-family ipv4
  neighbor 10.1.12.2 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 eBGP Neighbor Configuration</summary>

```bash
! R2 (eBGP portion only)
router bgp 65100
 bgp router-id 10.0.0.2
 bgp log-neighbor-changes
 neighbor 10.1.12.1 remote-as 65001
 neighbor 10.1.12.1 description Customer-A-CE-R1
 address-family ipv4
  neighbor 10.1.12.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 eBGP Neighbor Configuration</summary>

```bash
! R5 (eBGP portion only)
router bgp 65100
 bgp router-id 10.0.0.5
 bgp log-neighbor-changes
 neighbor 10.1.56.6 remote-as 65002
 neighbor 10.1.56.6 description External-SP-Peer-R6
 address-family ipv4
  neighbor 10.1.56.6 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R6 Configuration</summary>

```bash
! R6
router bgp 65002
 bgp router-id 10.0.0.6
 bgp log-neighbor-changes
 neighbor 10.1.56.5 remote-as 65100
 neighbor 10.1.56.5 description SP-Core-PE-West-R5
 address-family ipv4
  neighbor 10.1.56.5 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp neighbors 10.1.12.1
show ip bgp neighbors 10.1.56.6
```
</details>

---

### Task 3: iBGP R2↔R5

<details>
<summary>Click to view R2 iBGP Configuration</summary>

```bash
! R2 (iBGP additions)
router bgp 65100
 neighbor 10.0.0.5 remote-as 65100
 neighbor 10.0.0.5 description iBGP-PE-West-R5
 neighbor 10.0.0.5 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.5 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 iBGP Configuration</summary>

```bash
! R5 (iBGP additions)
router bgp 65100
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 description iBGP-PE-East-1-R2
 neighbor 10.0.0.2 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp neighbors 10.0.0.5 | include state|source
show ip bgp 172.16.1.0
```
</details>

---

### Task 4: Prefix Advertisement

<details>
<summary>Click to view R1 Network Statement</summary>

```bash
! R1 — Loopback1 (172.16.1.0/24) must be in the RIB for this to work
router bgp 65001
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
 exit-address-family
```
</details>

<details>
<summary>Click to view R6 Network Statement</summary>

```bash
! R6 — Loopback1 (172.16.6.0/24) must be in the RIB for this to work
router bgp 65002
 address-family ipv4
  network 172.16.6.0 mask 255.255.255.0
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp
show ip bgp 172.16.1.0
show ip bgp neighbors 10.1.12.2 advertised-routes
show ip route 172.16.1.0
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                          # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — R5 Has No Routes in Its BGP Table

The NOC reports that R5 is running BGP but its BGP table is empty. The iBGP session to R2 appears to be in Active state permanently.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R5's BGP table shows 172.16.1.0/24 and the iBGP session to R2 reaches Established state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R5 — confirms iBGP peer 10.0.0.2 is in Active or Idle (never Established).
2. `show ip bgp neighbors 10.0.0.2 | include source` — check whether `update-source` is set to Loopback0.
3. `show ip route 10.0.0.2` on R5 — confirm R2's loopback is reachable via OSPF.
4. `show tcp brief` on R5 — the TCP session for BGP will show the source IP is a physical interface address, not Loopback0.
5. The mismatch: R5 expects TCP connections from 10.0.0.2 (R2's loopback), but R2 is sourcing from 10.1.24.2 (physical interface). R5 rejects the session.
</details>

<details>
<summary>Click to view Fix</summary>

On R2, add the missing `update-source Loopback0` directive for the iBGP neighbor:

```bash
router bgp 65100
 neighbor 10.0.0.5 update-source Loopback0
```

After adding the statement, the session resets and re-establishes within ~30 seconds. Verify with `show ip bgp summary` — both sides must show `Estab` with a prefix count.
</details>

---

### Ticket 2 — R6 Does Not Learn the 172.16.1.0/24 Customer Prefix

Customer A reports its prefix is not reachable from the external SP peer side. R5's BGP table shows 172.16.1.0/24 as best, but R6's BGP table is empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** R6's BGP table shows 172.16.1.0/24 with AS-path `65100 65001`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R5 — the R6 session shows Established but `PfxSnd` is 0.
2. `show ip bgp neighbors 10.1.56.6 advertised-routes` on R5 — output is empty; R5 is not sending anything to R6.
3. `show ip bgp` on R5 — 172.16.1.0/24 is present and best (`>`), so the prefix exists.
4. `show ip bgp neighbors 10.1.56.6 | include activate` — neighbor 10.1.56.6 is not activated in address-family ipv4. Without activation, BGP opens the session but does not negotiate to exchange IPv4 unicast NLRIs.
</details>

<details>
<summary>Click to view Fix</summary>

On R5, activate the R6 neighbor in the IPv4 unicast address-family:

```bash
router bgp 65100
 address-family ipv4
  neighbor 10.1.56.6 activate
 exit-address-family
```

The session automatically sends an UPDATE carrying 172.16.1.0/24. Verify on R6: `show ip bgp` must show the prefix.
</details>

---

### Ticket 3 — R1's BGP Session to R2 Stays in Active

A change was made to R2 during a maintenance window and now R1's BGP session to R2 never reaches Established. R1 logs show `%BGP-3-NOTIFICATION: received from neighbor 10.1.12.2 2/2 (peer in wrong AS)`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R1's eBGP session to R2 is Established and 172.16.1.0/24 is exchanged.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R1 — peer 10.1.12.2 shows Active.
2. `show log` on R1 — `%BGP-3-NOTIFICATION: received from neighbor 10.1.12.2 2/2 (peer in wrong AS)`. R2 received R1's OPEN (which correctly states AS 65001) but R2's config expects AS 65999 — so R2 sends the NOTIFICATION to R1.
3. `show ip bgp neighbors 10.1.12.2` on R1 — shows `Remote AS 65100, Local AS 65001`. This looks correct on R1.
4. Check R2: `show ip bgp neighbors 10.1.12.1` — the remote-as configured on R2 for R1 is not 65001. R2's `neighbor 10.1.12.1 remote-as` statement specifies the wrong expected AS for R1.
5. `show running-config | section router bgp` on R2 — `neighbor 10.1.12.1 remote-as 65999` reveals the misconfiguration.
</details>

<details>
<summary>Click to view Fix</summary>

On R2, correct the remote-as for R1 from 65999 to 65001:

```bash
router bgp 65100
 no neighbor 10.1.12.1 remote-as 65999
 neighbor 10.1.12.1 remote-as 65001
```

The session immediately re-establishes. Verify `show ip bgp summary` on R2 — R1 must show `Estab` with a prefix count of 1.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show ip ospf neighbor` on R4 shows three FULL adjacencies (R2, R3, R5)
- [ ] `show ip route ospf` on R2 includes 10.0.0.5/32 (R5 loopback reachable)
- [ ] `show ip bgp summary` on R2 shows R1 (10.1.12.1) in `Estab`
- [ ] `show ip bgp summary` on R5 shows R6 (10.1.56.6) in `Estab`
- [ ] `show ip bgp summary` on R2 shows R5 (10.0.0.5) iBGP in `Estab`
- [ ] `show ip bgp 172.16.1.0` on R5 shows next-hop 10.0.0.2 (next-hop-self in effect)
- [ ] `show ip bgp` on R6 shows 172.16.1.0/24 with path `65100 65001`
- [ ] `show ip bgp` on R1 shows 172.16.6.0/24 with path `65100 65002`
- [ ] Full-mesh scaling analysis documented (N×(N−1)/2 session count for 5 PEs)

### Troubleshooting

- [ ] Ticket 1 resolved — R5 iBGP session Established after injecting missing update-source
- [ ] Ticket 2 resolved — R6 receives 172.16.1.0/24 after injecting missing neighbor activate
- [ ] Ticket 3 resolved — R1 eBGP session Established after correcting wrong remote-as on R2

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
