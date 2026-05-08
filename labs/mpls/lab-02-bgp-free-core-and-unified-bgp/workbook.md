# MPLS Lab 02 â€” BGP-Free Core and Unified BGP (Labeled Unicast)

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

**Exam Objective:** 4.1.c Unified BGP (BGP labeled-unicast) | 4.1.d BGP-free core â€” MPLS (300-510)

This lab completes the MPLS forwarding arc begun in labs 00 and 01. Having established the IS-IS/LDP underlay and verified LSP health, the focus shifts to carrying customer traffic across a core that deliberately runs no BGP. You will bring two customer edge routers online, wire up eBGP sessions at each PE, establish an iBGP session between the PEs that keeps P routers completely BGP-free, and then extend the iBGP session to exchange labels using BGP Labeled-Unicast (BGP-LU) â€” the mechanism that makes inter-AS MPLS (Option C) possible.

### BGP-Free Core Architecture

In a service-provider network, P (Provider) core routers can carry millions of customer routes if they run BGP. The BGP-free core model eliminates this burden: P routers run only IS-IS and LDP, holding no BGP RIB and no knowledge of customer destination prefixes. Forwarding works because every customer packet is label-switched on a PE-to-PE LSP. The P router never inspects the inner IP header â€” it reads the top MPLS label, looks up the LFIB, and swaps the label. Only the PE routers at the edges speak BGP and know where customer prefixes actually live.

```
  CE1 â†’ PE1 â†’ P1 â†’ PE2 â†’ CE2
              â†‘
       P1 only knows:
       "label 18 â†’ swap to 20, out Gi0/2"
       No knowledge of 198.51.100.0/24
```

The architectural significance: P routers scale without holding the global routing table (DFZ), making it feasible to build very large SP cores without upgrading P-router memory for every new customer.

### iBGP, Next-Hop-Self, and the BGP-Free Core

The iBGP session between PE1 and PE2 carries customer prefix reachability. A critical subtlety is the BGP next-hop:

- CE1 announces 192.0.2.0/24 to PE1 via eBGP. CE1's interface address (10.10.111.11) becomes the BGP next-hop.
- PE1 reflects this prefix to PE2 via iBGP. **Without `next-hop-self`**, PE2 inherits 10.10.111.11 as the BGP next-hop.
- PE2 has no IS-IS route to 10.10.111.11 (that subnet is off a PE-CE link not in IS-IS) â†’ BGP route is **inaccessible** â†’ return traffic fails.
- **With `next-hop-self`** on PE1, PE2 receives 192.0.2.0/24 with next-hop 10.0.0.1 (PE1's loopback) â†’ 10.0.0.1 IS reachable via IS-IS+LDP â†’ PE2 pushes the LDP label for 10.0.0.1's loopback and label-switches toward PE1.

`next-hop-self` is therefore the linchpin of BGP-free core operation. It causes the PE to advertise its own loopback as the BGP next-hop, which is always IS-IS reachable from the remote PE.

### Unified BGP (BGP Labeled-Unicast)

Standard LDP distributes labels only within a single IGP domain. When traffic must traverse **multiple autonomous systems** (inter-AS MPLS, Option C), there is no LDP session across the AS boundary. BGP Labeled-Unicast (BGP-LU, RFC 3107) solves this: it allows BGP to carry both a prefix **and** a label in the same UPDATE. The receiving router installs that label into its LFIB just as it would an LDP-learned label.

Key points:
- Enabled per-neighbor with `neighbor X send-label` under `address-family ipv4 unicast`.
- The prefix must be in the BGP RIB (via `network` statement or redistribution) for a label to be allocated and advertised.
- The label allocated by BGP-LU is **distinct from the LDP label** for the same prefix â€” both can coexist in the LFIB, but the active forwarding entry depends on the protocol preference and next-hop resolution.
- In intra-domain use (this lab), BGP-LU lets a remote ASBR learn PE loopbacks with labels attached â€” enabling end-to-end label-switched paths without LDP across AS boundaries.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| eBGP PE-CE sessions | Connect customer edge routers to the SP core |
| iBGP PE-PE (loopback-sourced) | Carry customer reachability between PEs without BGP on P routers |
| next-hop-self | Make iBGP next-hops recurse correctly via IS-IS/LDP |
| BGP-free core verification | Confirm P routers carry zero BGP state |
| End-to-end MPLS forwarding | Trace label operations hop-by-hop through the core |
| BGP Labeled-Unicast (send-label) | Extend iBGP to exchange labels alongside prefixes |
| BGP-LU vs LDP comparison | Understand when each label source is authoritative |

---

## 2. Topology & Scenario

**Scenario:** TeleCom Services operates a 4-router MPLS SP core (AS 65100) running IS-IS L2 and MPLS LDP on all core links. Two enterprise customers â€” Acme Corp (AS 65101, CE1) and Synapse Inc (AS 65102, CE2) â€” have contracted for IP connectivity across the SP backbone.

The SP's P routers (P1 and P2) are BGP-free by design: they have no BGP configuration, no routing table entries for customer prefixes, and no iBGP sessions. Your task is to extend the previously built LDP underlay to carry customer traffic end-to-end using eBGP at the PE edges, iBGP between PEs, and finally BGP Labeled-Unicast for inter-AS label distribution.

```
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”           â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚     CE1      â”‚           â”‚                  AS 65100 (SP Core)             â”‚
  â”‚  AS 65101    â”‚           â”‚           IS-IS L2 + MPLS LDP on all core links â”‚
  â”‚ Lo0:10.0.0.11â”‚           â”‚                                                 â”‚
  â”‚ Lo1:192.0.2.1â”‚           â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜           â”‚  â”‚       PE1        â”‚   â”‚       PE2        â”‚   â”‚
         â”‚ Gi0/0             â”‚  â”‚  Lo0:10.0.0.1/32 â”‚   â”‚  Lo0:10.0.0.4/32 â”‚   â”‚
         â”‚10.10.111.11/24    â”‚  â”‚  iBGP â†” PE2      â”‚   â”‚  iBGP â†” PE1      â”‚   â”‚
         â”‚ L1                â”‚  â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”˜   â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”˜   â”‚
         â”‚10.10.111.1/24 Gi0/0    â”‚Gi0/1 L2   â”‚Gi0/2 L3  â”‚Gi0/1 L5  â”‚Gi0/2 L6â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚           â”‚           â”‚          â”‚         â”‚
                                 â”‚           â””â”€â”€â”€â”€â”  â”Œâ”€â”€â”˜          â”‚         â”‚
                                 â”‚         â”Œâ”€â”€â”€â”€â”€â”€â”´â”€â”€â”´â”€â”€â”€â”€â”€â”       â”‚         â”‚
                              â”Œâ”€â”€â”´â”€â”€â”€â”€â”€â”€â”  â”‚      P2       â”‚â”€â”€â”€â”€â”€â”€â”€â”˜         â”‚
                              â”‚   P1    â”‚  â”‚ Lo0:10.0.0.3  â”‚                 â”‚
                              â”‚Lo0:10.0 â”‚  â”‚  (BGP-free)   â”‚                 â”‚
                              â”‚   .0.2  â”œâ”€â”€â”¤               â”‚                 â”‚
                              â”‚(BGP-freeâ”‚L4â”‚               â”‚                 â”‚
                              â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                 â”‚
                                           â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                                        â”‚ Gi0/0
                                                               10.10.122.4/24
                                                                        â”‚ L7
                                                               10.10.122.12/24 Gi0/0
                                                               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                                               â”‚      CE2       â”‚
                                                               â”‚   AS 65102     â”‚
                                                               â”‚ Lo0:10.0.0.12  â”‚
                                                               â”‚ Lo1:198.51.100.1â”‚
                                                               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Key link subnets:**

| Link ID | Source | Target | Subnet |
|---------|--------|--------|--------|
| L1 | CE1 Gi0/0 | PE1 Gi0/0 | 10.10.111.0/24 |
| L2 | PE1 Gi0/1 | P1 Gi0/0 | 10.10.12.0/24 |
| L3 | PE1 Gi0/2 | P2 Gi0/0 | 10.10.13.0/24 |
| L4 | P1 Gi0/1 | P2 Gi0/1 | 10.10.23.0/24 |
| L5 | P1 Gi0/2 | PE2 Gi0/1 | 10.10.24.0/24 |
| L6 | P2 Gi0/2 | PE2 Gi0/2 | 10.10.34.0/24 |
| L7 | CE2 Gi0/0 | PE2 Gi0/0 | 10.10.122.0/24 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge â€” eBGP to CE1, iBGP to PE2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | SP Core (BGP-free) â€” IS-IS L2 + MPLS LDP only | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | SP Core (BGP-free) â€” IS-IS L2 + MPLS LDP only | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | SP Edge â€” eBGP to CE2, iBGP to PE1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Customer Edge â€” AS 65101, announces 192.0.2.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer Edge â€” AS 65102, announces 198.51.100.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Address Table

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | Router-ID, iBGP peering source, BGP-LU advertisement |
| P1 | Loopback0 | 10.0.0.2/32 | Router-ID, IS-IS reachability |
| P2 | Loopback0 | 10.0.0.3/32 | Router-ID, IS-IS reachability |
| PE2 | Loopback0 | 10.0.0.4/32 | Router-ID, iBGP peering source, BGP-LU advertisement |
| CE1 | Loopback0 | 10.0.0.11/32 | Router-ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix (announced to PE1 via eBGP) |
| CE2 | Loopback0 | 10.0.0.12/32 | Router-ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix (announced to PE2 via eBGP) |

### Cabling Table

| Link | From Device | Interface | To Device | Interface | Subnet |
|------|------------|-----------|-----------|-----------|--------|
| L1 | CE1 | Gi0/0 | PE1 | Gi0/0 | 10.10.111.0/24 |
| L2 | PE1 | Gi0/1 | P1 | Gi0/0 | 10.10.12.0/24 |
| L3 | PE1 | Gi0/2 | P2 | Gi0/0 | 10.10.13.0/24 |
| L4 | P1 | Gi0/1 | P2 | Gi0/1 | 10.10.23.0/24 |
| L5 | P1 | Gi0/2 | PE2 | Gi0/1 | 10.10.24.0/24 |
| L6 | P2 | Gi0/2 | PE2 | Gi0/2 | 10.10.34.0/24 |
| L7 | CE2 | Gi0/0 | PE2 | Gi0/0 | 10.10.122.0/24 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| CE1 | 192.0.2.0/24 | eBGP network | Acme Corp customer aggregate (sourced from Loopback1) |
| CE2 | 198.51.100.0/24 | eBGP network | Synapse Inc customer aggregate (sourced from Loopback1) |
| PE1 | 10.0.0.1/32 | BGP-LU network | PE loopback â€” advertised with label for inter-AS use |
| PE2 | 10.0.0.4/32 | BGP-LU network | PE loopback â€” advertised with label for inter-AS use |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| PE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on all six devices
- Interface IP addressing (all routed links L1â€“L7 and all loopbacks)
- `no ip domain-lookup` on all devices
- IS-IS L2-only (process CORE) on PE1, P1, P2, PE2 â€” all core interfaces and loopbacks
- MPLS LDP globally (`mpls label protocol ldp`, `mpls ldp router-id Loopback0 force`) on PE1, P1, P2, PE2
- `mpls ip` and `mpls mtu override 1508` on all core-facing interfaces (Gi0/1, Gi0/2 on PE1/PE2; all three interfaces on P1/P2)

**IS NOT pre-loaded** (student configures this):
- eBGP sessions (PE1â†”CE1 in AS 65101, PE2â†”CE2 in AS 65102)
- iBGP session (PE1â†”PE2 loopback-sourced within AS 65100)
- BGP next-hop-self on iBGP sessions
- BGP `network` statements for PE loopbacks (required for BGP-LU)
- Unified BGP labeled-unicast (`send-label`) on iBGP sessions
- Customer prefix advertisement on CE1 and CE2

---

## 5. Lab Challenge: Core Implementation

### Task 1: Verify CEâ€“PE Link Reachability

- On PE1, confirm Gi0/0 (10.10.111.1/24) is up and the link to CE1 (10.10.111.11) is reachable.
- On PE2, confirm Gi0/0 (10.10.122.4/24) is up and the link to CE2 (10.10.122.12) is reachable.
- On CE1, confirm reachability to PE1 Gi0/0 (10.10.111.1).
- On CE2, confirm reachability to PE2 Gi0/0 (10.10.122.4).

**Verification:** `ping 10.10.111.1` from CE1 and `ping 10.10.122.4` from CE2 â€” both must succeed. `show interfaces GigabitEthernet0/0` on each CE must show line protocol up.

---

### Task 2: Configure eBGP PEâ€“CE Sessions

- On PE1, establish an eBGP session to CE1 (remote AS 65101, neighbor address 10.10.111.11). Activate the neighbor in address-family IPv4 unicast.
- On CE1, establish an eBGP session to PE1 (remote AS 65100, neighbor address 10.10.111.1). Advertise the 192.0.2.0/24 prefix from Loopback1 into BGP.
- On PE2, establish an eBGP session to CE2 (remote AS 65102, neighbor address 10.10.122.12). Activate the neighbor in address-family IPv4 unicast.
- On CE2, establish an eBGP session to PE2 (remote AS 65100, neighbor address 10.10.122.4). Advertise the 198.51.100.0/24 prefix from Loopback1 into BGP.

**Verification:** `show ip bgp summary` on PE1 must show CE1 (10.10.111.11) as an established neighbor with PfxRcd = 1. Same check on PE2 for CE2 (10.10.122.12). `show ip bgp 192.0.2.0/24` on PE1 must show the prefix as best (`>`) with next-hop 10.10.111.11.

---

### Task 3: Configure iBGP PE1â†”PE2 with Next-Hop-Self

- On PE1, configure iBGP (AS 65100) with PE2's loopback 10.0.0.4 as neighbor. Source the session from Loopback0. Activate the neighbor in address-family IPv4 unicast. Enable next-hop-self so PE2 receives customer prefixes with PE1's loopback as next-hop.
- On PE2, configure iBGP (AS 65100) with PE1's loopback 10.0.0.1 as neighbor. Source the session from Loopback0. Activate and enable next-hop-self symmetrically.
- Do NOT configure any BGP on P1 or P2.

**Verification:** `show ip bgp summary` on PE1 must show PE2 (10.0.0.4) as established with PfxRcd = 1. `show ip bgp 198.51.100.0/24` on PE1 must show the prefix with next-hop **10.0.0.4** (PE2's loopback â€” proving next-hop-self is in effect). Same cross-check on PE2 for 192.0.2.0/24 with next-hop 10.0.0.1.

---

### Task 4: Verify the BGP-Free Core Invariant

- Confirm that P1 and P2 have no BGP process. No `router bgp` configuration must exist on either P router.
- Confirm that P1 has no route to 192.0.2.0/24 or 198.51.100.0/24 in its routing table.
- Confirm that P1's LFIB still shows LSP entries for PE loopbacks (10.0.0.1/32, 10.0.0.4/32) as it has since lab-00.

**Verification:** `show ip bgp summary` on P1 must return `% BGP not active`. `show ip route 198.51.100.0` on P1 must return "not in routing table". `show mpls forwarding-table 10.0.0.4` on P1 must show a valid outgoing label entry.

---

### Task 5: Verify End-to-End BGP-Free Customer Forwarding

- From CE1, ping 198.51.100.1 (CE2's Loopback1) sourced from 192.0.2.1 (CE1's Loopback1). All 5 ICMP replies must succeed.
- Trace the label stack hop by hop from PE1 to PE2.
- On P1, confirm that the MPLS forwarding table (not the IP routing table) is what drives CE1â†’CE2 traffic.

**Verification:** `ping 198.51.100.1 source 192.0.2.1 repeat 5` from CE1 â€” 100% success rate. `show mpls forwarding-table 10.0.0.4` on P1 must show an active label-swap entry with a non-zero outgoing label. `show ip route 198.51.100.0` on P1 must confirm `% not in routing table` (the P router forwards on label, not IP lookup).

---

### Task 6: Enable Unified BGP (Labeled-Unicast) on the iBGP Session

- On PE1 and PE2, advertise each router's own loopback (10.0.0.1/32 and 10.0.0.4/32 respectively) into BGP using a `network` statement under address-family IPv4 unicast.
- On PE1, add `send-label` to the neighbor statement for PE2 (10.0.0.4) under address-family IPv4 unicast.
- On PE2, add `send-label` to the neighbor statement for PE1 (10.0.0.1) under address-family IPv4 unicast. Both sides must have `send-label` â€” capability negotiation fails if only one side configures it.
- Verify that PE loopback prefixes now carry an MPLS label in the BGP table.

**Verification:** `show ip bgp labels` on PE1 must show both 10.0.0.1/32 and 10.0.0.4/32. `show ip bgp labels` on PE2 must show both 10.0.0.4/32 and 10.0.0.1/32. For each PE's **own** loopback the in-label will show `imp-null` (this PE is the egress â€” PHP applies). For the **remote** PE's loopback the out-label will show `imp-null` (the remote PE advertised PHP for its own loopback) and the in-label will show `nolabel` â€” this is correct in a two-PE intra-domain topology where no third BGP-LU peer exists to re-advertise the prefix to. In an inter-AS topology a real numeric in-label would appear here. Confirm capability negotiation with `show ip bgp neighbor 10.0.0.4 | include Labeled`.

---

## 6. Verification & Analysis

### Task 1 â€” CEâ€“PE link reachability

```
CE1# ping 10.10.111.1 repeat 5
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.10.111.1, timeout is 2 seconds:
!!!!!                        ! â† all 5 replies received â€” L1 link is up
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms
```

### Task 2 â€” eBGP PEâ€“CE sessions

```
PE1# show ip bgp summary
BGP router identifier 10.0.0.1, local AS number 65100
BGP table version is 4, main routing table version 4
2 network entries using 296 bytes of memory
2 path entries using 160 bytes of memory

Neighbor        V   AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.4        4 65100       6       6        4    0    0 00:02:30        1   ! â† iBGP PE2 (task 3)
10.10.111.11    4 65101       5       5        4    0    0 00:01:45        1   ! â† eBGP CE1: PfxRcd=1

PE1# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 3
Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65101
    10.10.111.11 from 10.10.111.11 (10.0.0.11)   ! â† CE1 source, next-hop is CE1 interface
      Origin IGP, metric 0, localpref 100, valid, external, best
```

### Task 3 â€” iBGP with next-hop-self

```
PE2# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 3
Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65101
    10.0.0.1 from 10.0.0.1 (10.0.0.1)      ! â† next-hop is PE1's LOOPBACK â€” next-hop-self worked
      Origin IGP, metric 0, localpref 100, valid, internal, best
      mpls labels in/out nolabel/17          ! â† LDP label for LSP to PE1

PE1# show ip route 198.51.100.0
Routing entry for 198.51.100.0/24
  Known via "bgp 65100", distance 200, metric 0
  Tag 65102, type internal
  Last update from 10.0.0.4 00:02:10 ago
  Routing Descriptor Blocks:
  * 10.0.0.4, from 10.0.0.4, 00:02:10 ago    ! â† next-hop is PE2 loopback â€” resolves via IS-IS
      Route metric is 0, traffic share count is 1
```

### Task 4 â€” BGP-free invariant

```
P1# show ip bgp summary
% BGP not active                             ! â† P1 has NO BGP process â€” invariant confirmed

P1# show ip route 198.51.100.0
% Network not in table                       ! â† P1 holds no customer route

P1# show mpls forwarding-table 10.0.0.4
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label or   or Tunnel Id     Switched      interface
20         Pop Label  10.0.0.4/32      0             Gi0/2      10.10.24.4   ! â† P1 label-switches to PE2 without knowing the customer IP
```

### Task 5 â€” End-to-end forwarding

```
CE1# ping 198.51.100.1 source 192.0.2.1 repeat 5
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 198.51.100.1, timeout is 2 seconds:
Packet sent with a source address of 192.0.2.1
!!!!!                           ! â† CE1â†’CE2 reachability confirmed
Success rate is 100 percent (5/5), round-trip min/avg/max = 4/6/11 ms

P1# debug mpls packet
*Mar  1 00:04:31.213: MPLS pak, label:20, Gi0/0 ->Gi0/2  ! â† P1 swaps label â€” never reads inner IP
P1# undebug all
```

### Task 6 â€” Unified BGP labels

```
PE1# show ip bgp labels
   Network          Next Hop      In label/Out label
   10.0.0.1/32      0.0.0.0         imp-null/nolabel   ! â† PE1's own loopback; imp-null = PHP; egress for its own prefix
   10.0.0.4/32      10.0.0.4        nolabel/imp-null   ! â† PE2's loopback; out-label imp-null received from PE2 (PHP)
   192.0.2.0        10.10.111.11    22/nolabel         ! â† customer prefix (eBGP); in-label allocated for iBGP re-advertisement
   198.51.100.0     10.0.0.4        nolabel/22         ! â† customer prefix (iBGP); out-label 22 received from PE2

! Note: nolabel as in-label for 10.0.0.4/32 is correct on IOSv in a two-PE intra-domain topology.
! A real numeric in-label would appear here only if PE1 were re-advertising PE2's loopback
! to a third BGP-LU peer (inter-AS ASBR scenario). imp-null as out-label is PE2 signalling PHP
! for its own loopback â€” the same behaviour LDP uses, carried over BGP.

PE2# show ip bgp neighbor 10.0.0.1 | include label|Labeled|capability
    BGP label table is maintained
    Labeled-Unicast: received (capability)   ! â† send-label capability negotiated on both sides
```

---

## 7. Verification Cheatsheet

### eBGP PEâ€“CE Configuration

```
router bgp <SP-AS>
 bgp router-id <loopback-IP>
 neighbor <CE-IP> remote-as <CE-AS>
 !
 address-family ipv4
  neighbor <CE-IP> activate
```

| Command | Purpose |
|---------|---------|
| `show ip bgp summary` | Session state and prefix count per neighbor |
| `show ip bgp <prefix>` | BGP path attributes for a specific prefix |
| `show ip bgp neighbors <IP> | include State` | Confirm Established state |

> **Exam tip:** eBGP sessions use the directly connected interface address as the source by default. No `update-source` is needed for single-hop eBGP.

### iBGP PEâ€“PE Configuration

```
router bgp <SP-AS>
 neighbor <PE-loopback> remote-as <SP-AS>
 neighbor <PE-loopback> update-source Loopback0
 !
 address-family ipv4
  neighbor <PE-loopback> activate
  neighbor <PE-loopback> next-hop-self
```

| Command | Purpose |
|---------|---------|
| `show ip bgp <CE-prefix>` | Verify next-hop is peer PE's loopback (not CE interface) |
| `show ip route <CE-prefix>` | Confirm BGP route is active with loopback as next-hop |

> **Exam tip:** Without `next-hop-self`, iBGP sends the eBGP-learned next-hop unchanged. The remote PE cannot recurse on a CE subnet not in IS-IS, making the route inaccessible.

### BGP-Free Core Verification

```
show ip bgp summary                ! must return "% BGP not active" on P routers
show ip route <customer-prefix>    ! must return "not in table" on P routers
show mpls forwarding-table         ! confirms P router forwards on labels only
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp summary` on P1/P2 | `% BGP not active` â€” confirms zero BGP configuration |
| `show ip route 198.51.100.0` on P1/P2 | `% Network not in table` â€” no BGP routes |
| `show mpls forwarding-table 10.0.0.4` on P1 | Active outgoing label for PE2's loopback |

### Unified BGP (send-label) Configuration

```
router bgp <SP-AS>
 address-family ipv4
  neighbor <iBGP-peer> send-label
  network <PE-loopback> mask 255.255.255.255
```

| Command | Purpose |
|---------|---------|
| `show ip bgp labels` | Display prefixâ€“label bindings in the BGP label table |
| `show ip bgp neighbor <IP> | include label\|capability` | Confirm BGP-LU capability negotiated |
| `show mpls forwarding-table` | Confirm BGP-LU label installed in LFIB |

> **Exam tip:** `send-label` requires capability negotiation â€” both neighbors must configure it. If only one side has it, the session stays up but no labels are exchanged (`show ip bgp labels` shows empty).

### Common BGP-Free Core Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| CE1 ping to CE2 fails; BGP sessions established | `next-hop-self` missing â€” BGP next-hop is CE interface, unreachable from remote PE |
| `show ip bgp labels` empty after `send-label` | PE loopback not in BGP (`network` statement missing) |
| `show ip bgp labels` empty; sessions up | `send-label` configured on one PE only â€” capability mismatch |
| BGP active on P router | Misconfiguration violating BGP-free invariant â€” `no router bgp` required |
| CE1â†’CE2 ping fails; traceroute shows * at P hop | LDP LSP broken to remote PE loopback (check lab-01 troubleshooting) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: CEâ€“PE Link Reachability

<details>
<summary>Click to view â€” this task is pre-configured by setup_lab.py (interface IPs already present)</summary>

```bash
! CE1 â€” verify interfaces are up
CE1# show interfaces GigabitEthernet0/0 | include line
GigabitEthernet0/0 is up, line protocol is up
CE1# ping 10.10.111.1
!!!!!
! PE1 â€” verify Gi0/0 link to CE1
PE1# show interfaces GigabitEthernet0/0 | include line
GigabitEthernet0/0 is up, line protocol is up
```

</details>

---

### Task 2: eBGP PEâ€“CE Sessions

<details>
<summary>Click to view PE1 configuration</summary>

```bash
! PE1
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.10.111.11 remote-as 65101
 !
 address-family ipv4
  neighbor 10.10.111.11 activate
```

</details>

<details>
<summary>Click to view CE1 configuration</summary>

```bash
! CE1
router bgp 65101
 bgp router-id 10.0.0.11
 bgp log-neighbor-changes
 neighbor 10.10.111.1 remote-as 65100
 !
 address-family ipv4
  neighbor 10.10.111.1 activate
  network 192.0.2.0 mask 255.255.255.0
```

</details>

<details>
<summary>Click to view PE2 configuration</summary>

```bash
! PE2
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 neighbor 10.10.122.12 remote-as 65102
 !
 address-family ipv4
  neighbor 10.10.122.12 activate
```

</details>

<details>
<summary>Click to view CE2 configuration</summary>

```bash
! CE2
router bgp 65102
 bgp router-id 10.0.0.12
 bgp log-neighbor-changes
 neighbor 10.10.122.4 remote-as 65100
 !
 address-family ipv4
  neighbor 10.10.122.4 activate
  network 198.51.100.0 mask 255.255.255.0
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
PE1# show ip bgp summary
PE1# show ip bgp 192.0.2.0/24
PE2# show ip bgp 198.51.100.0/24
```

</details>

---

### Task 3: iBGP PE1â†”PE2 with Next-Hop-Self

<details>
<summary>Click to view PE1 iBGP configuration</summary>

```bash
! PE1 â€” add iBGP neighbor to existing router bgp 65100
router bgp 65100
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
```

</details>

<details>
<summary>Click to view PE2 iBGP configuration</summary>

```bash
! PE2 â€” add iBGP neighbor to existing router bgp 65100
router bgp 65100
 neighbor 10.0.0.1 remote-as 65100
 neighbor 10.0.0.1 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.1 next-hop-self
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Confirm iBGP session and next-hop-self effect
PE2# show ip bgp 192.0.2.0/24
! Look for: next-hop = 10.0.0.1 (PE1 loopback, NOT 10.10.111.11)
PE1# show ip bgp 198.51.100.0/24
! Look for: next-hop = 10.0.0.4 (PE2 loopback, NOT 10.10.122.12)
```

</details>

---

### Task 4: BGP-Free Core Invariant

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Run on BOTH P1 and P2
P1# show ip bgp summary
! Expected: % BGP not active
P1# show running-config | section bgp
! Expected: no output (no router bgp stanza exists)
P1# show ip route 198.51.100.0
! Expected: % Network not in table
P1# show mpls forwarding-table 10.0.0.4
! Expected: active label-swap entry exists
```

</details>

---

### Task 5: End-to-End Customer Forwarding

<details>
<summary>Click to view Verification Commands</summary>

```bash
CE1# ping 198.51.100.1 source 192.0.2.1 repeat 5
! Expected: !!!!! (100% success)

PE1# traceroute 198.51.100.1 source 192.0.2.1
! Expected: PE1 â†’ P1 or P2 (label hop) â†’ PE2 â†’ 198.51.100.1
! P router hops may show as * (MPLS TTL not decremented for unlabeled ICMP replies)
```

</details>

---

### Task 6: Unified BGP (BGP-LU send-label)

<details>
<summary>Click to view PE1 BGP-LU configuration</summary>

```bash
! PE1 â€” add to existing router bgp 65100 address-family ipv4
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.4 send-label
  network 10.0.0.1 mask 255.255.255.255
```

</details>

<details>
<summary>Click to view PE2 BGP-LU configuration</summary>

```bash
! PE2 â€” add to existing router bgp 65100 address-family ipv4
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 send-label
  network 10.0.0.4 mask 255.255.255.255
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
PE1# show ip bgp labels
! Expected: 10.0.0.1/32 with local in-label; 10.0.0.4/32 with out-label from PE2
PE2# show ip bgp labels
! Expected: 10.0.0.4/32 with local in-label; 10.0.0.1/32 with out-label from PE1
PE1# show ip bgp neighbor 10.0.0.4 | include label|capability
! Expected: Labeled-Unicast capability in received capabilities
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 â€” Customer Traffic Between CE1 and CE2 Is Down

The eBGP and iBGP sessions are established and showing prefixes. However, a ping from CE1 to CE2's Loopback1 (198.51.100.1) fails completely. The SP NOC has confirmed that the IS-IS adjacencies and LDP sessions are all healthy.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `ping 198.51.100.1 source 192.0.2.1` from CE1 returns 100% success.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm BGP sessions are up
PE1# show ip bgp summary
! Both 10.0.0.4 (iBGP) and 10.10.111.11 (eBGP) should show Established

! Step 2: Check BGP routing table for customer prefix at remote PE
PE2# show ip bgp 192.0.2.0/24
! Look at the "Next Hop" field â€” if it shows 10.10.111.11 instead of 10.0.0.1,
! next-hop-self is missing. 10.10.111.11 is unreachable from PE2 via IS-IS.

PE1# show ip bgp 198.51.100.0/24
! Same check â€” next-hop should be 10.0.0.4, not 10.10.122.12

! Step 3: Verify route reachability
PE2# show ip route 10.10.111.0
! Expected: "not in table" â€” confirms the CE subnet is unreachable from the remote PE
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Add next-hop-self to BOTH PEs (the fault removes it from both)
PE1(config)# router bgp 65100
PE1(config-router)# address-family ipv4
PE1(config-router-af)# neighbor 10.0.0.4 next-hop-self

PE2(config)# router bgp 65100
PE2(config-router)# address-family ipv4
PE2(config-router-af)# neighbor 10.0.0.1 next-hop-self

! Verify
PE2# show ip bgp 192.0.2.0/24
! Next Hop must now show 10.0.0.1 (PE1 loopback)
CE1# ping 198.51.100.1 source 192.0.2.1
! Expected: !!!!!
```

</details>

---

### Ticket 2 â€” Monitoring Alert: BGP Process Detected on P1

A network monitoring system has flagged that P1 is showing a BGP process active. The SP's compliance policy requires all P routers to be BGP-free. No change window was scheduled for P1.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp summary` on P1 returns `% BGP not active`. P1 has no BGP stanza in `show running-config`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm the violation
P1# show ip bgp summary
! Will show BGP process active with a neighbor in Idle or Active state

! Step 2: Identify what was added
P1# show running-config | section bgp
! Will reveal: router bgp 65100 with a neighbor stanza pointing to PE1's loopback
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Remove the BGP process entirely from P1
P1(config)# no router bgp 65100

! Verify
P1# show ip bgp summary
! Expected: % BGP not active
P1# show running-config | section bgp
! Expected: no output
```

</details>

---

### Ticket 3 â€” BGP Label Table Is Empty on PE2 After Unified BGP Configuration

PE1 shows labels in `show ip bgp labels` for its own loopback and PE2's loopback. PE2 shows its own loopback label but reports no label for PE1's loopback (10.0.0.1/32). The iBGP session between PE1 and PE2 is Established.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp labels` on PE2 shows both 10.0.0.4/32 (local) and 10.0.0.1/32 (from PE1) with non-zero labels.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Inspect label tables
PE1# show ip bgp labels
! PE1 shows labels for both loopbacks â€” confirms PE1's config is correct

PE2# show ip bgp labels
! PE2 shows 10.0.0.4/32 only â€” 10.0.0.1/32 is missing, meaning PE2 received
! no label advertisement from PE1... or PE1 received none from PE2

! Step 2: Check BGP-LU capability negotiation
PE2# show ip bgp neighbor 10.0.0.1 | include label|capability|send
! Look for: "Labeled-Unicast: received" â€” if missing, capability wasn't negotiated

PE1# show ip bgp neighbor 10.0.0.4 | include label|capability|send
! If PE1 shows "send-label" in its neighbor config but PE2 does not,
! the session is one-sided â€” BGP-LU requires BOTH peers to advertise the capability

! Step 3: Confirm via running-config
PE2# show running-config | section bgp
! Look for "send-label" under address-family ipv4 â€” it will be absent
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Add send-label to PE2's iBGP neighbor config
PE2(config)# router bgp 65100
PE2(config-router)# address-family ipv4
PE2(config-router-af)# neighbor 10.0.0.1 send-label

! Allow BGP to re-negotiate (may need to soft-reset)
PE2# clear ip bgp 10.0.0.1 soft

! Verify
PE2# show ip bgp labels
! Expected: both 10.0.0.4/32 and 10.0.0.1/32 with non-zero labels
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] CE1â†’PE1 (L1) and CE2â†’PE2 (L7) links are up; ping succeeds on both CE-PE subnets
- [ ] PE1 has eBGP session to CE1 (AS 65101) â€” Established, PfxRcd = 1 (192.0.2.0/24)
- [ ] PE2 has eBGP session to CE2 (AS 65102) â€” Established, PfxRcd = 1 (198.51.100.0/24)
- [ ] PE1 has iBGP session to PE2 (AS 65100) â€” Established, sourced from Loopback0
- [ ] PE2 receives 192.0.2.0/24 with next-hop 10.0.0.1 (next-hop-self confirmed)
- [ ] PE1 receives 198.51.100.0/24 with next-hop 10.0.0.4 (next-hop-self confirmed)
- [ ] `show ip bgp summary` on P1 returns `% BGP not active`
- [ ] `show ip route 198.51.100.0` on P1 returns `% Network not in table`
- [ ] `ping 198.51.100.1 source 192.0.2.1` from CE1 succeeds 5/5
- [ ] `show ip bgp labels` on PE1 shows both 10.0.0.1/32 and 10.0.0.4/32 with non-zero labels
- [ ] `show ip bgp labels` on PE2 shows both 10.0.0.4/32 and 10.0.0.1/32 with non-zero labels

### Troubleshooting

- [ ] Ticket 1 injected, fault diagnosed (missing next-hop-self), CE1â†’CE2 ping restored
- [ ] Ticket 2 injected, fault diagnosed (BGP on P1), BGP-free invariant restored
- [ ] Ticket 3 injected, fault diagnosed (missing send-label on PE2), BGP labels restored on PE2

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
