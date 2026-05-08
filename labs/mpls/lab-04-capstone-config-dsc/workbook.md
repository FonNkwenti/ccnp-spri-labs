# MPLS Lab 04: Full Mastery â€” Capstone I

> **Platform Mix Notice (XR-mixed capstone):** PE1 and PE2 in this capstone run
> **IOS XRv (light, 6.1.x)**; P1, P2, CE1, CE2 remain IOSv. This retrofit
> exposes you to XR CLI for LDP, BGP labeled-unicast, and RSVP-TE â€” the
> production-realistic SP edge platform â€” without changing the lab's exam
> coverage. The IOS commands shown throughout the workbook still apply on
> P1/P2/CE1/CE2; for the XR equivalents on PE1 and PE2, see
> [Appendix B: XR-side Command Reference](#appendix-b-xr-side-command-reference).
> Status: configs are syntactically translated and need EVE-NG verification.

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)
11. [Appendix: Script Exit Codes](#11-appendix-script-exit-codes)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 4.1 â€” MPLS (CCNP SPRI 300-510), all sub-topics

This capstone challenges you to build a complete MPLS service provider core from an IP-only starting point. You will configure IS-IS, LDP, iBGP with labeled unicast, eBGP to customer edges, RSVP-TE, and a TE tunnel with path diversity. Every protocol must interoperate correctly; a single missing step breaks the forwarding chain. By the end, you will have assembled the full MPLS stack and verified that a customer packet crosses the BGP-free core entirely on labels.

### IS-IS as the MPLS IGP

IS-IS is the dominant IGP in service provider MPLS networks because it is protocol-agnostic (it carries IPv4 and IPv6 natively in TLVs), converges faster than OSPF in large topologies, and has mature TE extensions (TLV 22 for Extended IS Reachability). In this lab, IS-IS runs at Level 2 only on all four core routers in area 49.0001.

Key IS-IS design decisions for MPLS:
- **Level-2-only** â€” a flat L2 domain eliminates the need for L1/L2 border routers and simplifies the TE topology database.
- **Wide metrics** â€” `metric-style wide` enables 24-bit metrics (up to 16,777,215) needed for TE metric propagation. Narrow metrics (6-bit, max 63) are insufficient for modern networks.
- **Point-to-point network type** â€” explicit `isis network point-to-point` on each core link avoids the DIS election overhead and 10-second pseudo-node LSP delay inherent to broadcast networks.
- **Passive loopback** â€” `passive-interface Loopback0` prevents IS-IS hellos on the loopback while still advertising the /32 prefix in LSPs.

IS-IS NET addresses use the format `49.xxxx.yyyy.yyyy.yyyy.00` where `49` denotes a private AFI, `xxxx` is the area ID, and `yyyy.yyyy.yyyy` is the 6-byte system ID (padded from the router's loopback IP).

```
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```

### MPLS LDP Fundamentals

LDP (Label Distribution Protocol) is the workhorse label distribution mechanism in most SP networks. It operates on a simple principle: every LSR assigns a local label to each IGP-learned prefix and advertises that binding to its LDP neighbors. The downstream router uses the upstream router's advertised label when sending traffic.

The LDP session lifecycle proceeds through three phases:
1. **Discovery** â€” UDP hello packets (port 646) sent to 224.0.0.2. If a router hears a hello on an interface, it discovers a potential LDP peer at that neighbor's LDP router-id (typically a loopback).
2. **Session establishment** â€” TCP connection (port 646) from the higher LDP router-id to the lower. The two routers negotiate session parameters (label advertisement mode, VPI/VCI ranges, keepalive timers).
3. **Label exchange** â€” after the session is operational, each router advertises label bindings for every IGP-learned /32 prefix. The LIB holds all received bindings; the LFIB holds only the one selected by the IGP next-hop.

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
```

The `force` keyword ensures the router-id changes immediately without waiting for the existing LDP session to drop â€” essential when correcting a misconfigured or default router-id.

### BGP-Free Core and Unified BGP

The BGP-free core is the defining architectural pattern of MPLS Layer 3 VPNs. P routers run only IS-IS and LDP â€” they have zero BGP configuration. When a packet arrives at a P router with an MPLS label, the P router consults only its LFIB (label forwarding information base), swaps the top label, and forwards the packet. The P router never examines the inner IP header. This means:

- P routers do not need the full Internet routing table (DFZ) â€” they hold only IGP routes and label bindings.
- The core scales independently of the edge: adding new customers or VPNs requires no changes to P routers.
- Forwarding remains wire-speed because label lookup is a simple table index, not a longest-prefix match.

Unified BGP (BGP labeled unicast, or BGP-LU) adds a label to BGP-advertised prefixes. In the `address-family ipv4 unicast` context, `neighbor <peer> send-label` instructs BGP to advertise an MPLS label alongside each IPv4 prefix. Inside a single AS this is redundant with LDP (LDP already provides labels for the same loopbacks), but it becomes essential for inter-AS MPLS (Option C) where LDP does not cross AS boundaries.

Critically, P1 and P2 must have **no BGP configuration whatsoever**. `show ip bgp summary` on either P router must return `% BGP not active`. If you find BGP running on a P router during verification, you have broken the BGP-free core invariant and must remove it.

### RSVP-TE Architecture

RSVP-TE (Resource Reservation Protocol â€” Traffic Engineering) lets the operator steer traffic onto explicit paths with bandwidth guarantees, independent of the IGP best-path. The TE control plane has four components, all of which must be active:

1. **TE topology database (TED)** â€” built from IS-IS Extended IS Reachability (TLV 22) sub-TLVs carrying per-link bandwidth, maximum reservable bandwidth, TE metric, and admin group (affinity). Every TE-enabled router floods these TLVs; every router builds a complete TED from them.
2. **CSPF (Constrained Shortest Path First)** â€” runs on the tunnel headend. Reads the TED, prunes links that fail constraints (insufficient bandwidth, wrong affinity), runs Dijkstra on what remains.
3. **RSVP signaling** â€” the headend sends PATH messages hop-by-hop toward the tail; each transit LSR performs admission control and forwards the PATH. The tail responds with RESV messages back toward the headend, creating a label reservation at each hop.
4. **Forwarding** â€” after RESV completes, the headend installs a label forwarding entry for the tunnel. Traffic steered into the tunnel follows the RSVP-reserved path, not the IGP best path.

```
 Headend (PE1)          Transit (P1)           Tail (PE2)
      â”‚     PATH â”€â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”‚     PATH â”€â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”‚
      â”‚   (BW request)     â”‚  (admission ok)    â”‚
      â”‚â—„â”€â”€â”€â”€ RESV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚â—„â”€â”€â”€â”€ RESV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚
      â”‚  (label received)  â”‚  (label received)  â”‚
```

A tunnel with dual path-options provides resilience: the secondary is pre-signaled (hot standby) or computed but not signaled (lockdown). If the primary path fails, the headend switches to the secondary without re-computation.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IS-IS L2 deployment | Bring up IS-IS adjacencies on a diamond core with NET, level-2-only, wide metrics, and point-to-point links |
| MPLS LDP configuration | Enable LDP globally and per-interface, force router-id from loopback, verify LIB/LFIB consistency |
| BGP-free core | Configure iBGP with send-label between PEs while keeping P routers BGP-free |
| eBGP to customer edge | Establish eBGP sessions to CE1 (AS 65101) and CE2 (AS 65102), announce customer prefixes |
| MPLS-TE global enablement | Enable TE at global and per-interface levels |
| IS-IS TE extensions | Configure TE LSA flooding for CSPF topology awareness |
| RSVP bandwidth admission | Set reservable bandwidth pools and understand admission control behavior |
| TE tunnel with path diversity | Build dynamic primary + explicit secondary path-options on a headend tunnel |
| Autoroute announce | Steer IGP traffic into a TE tunnel automatically |
| End-to-end label forwarding | Trace a customer packet through the full MPLS stack: IPâ†’MPLSâ†’label-swapâ†’popâ†’IP |

---

## 2. Topology & Scenario

**Scenario:** You are the lead network engineer for a service provider (AS 65100) building a greenfield MPLS core. Four core routers (PE1, P1, P2, PE2) have been racked and cabled in a diamond topology. Two customer edge routers (CE1 in AS 65101, CE2 in AS 65102) are connected to PE1 and PE2 respectively. The IP addressing is pre-assigned. Nothing else is configured â€” no routing protocol, no MPLS, no BGP, no TE.

Your task: build the complete MPLS stack from scratch. Configure IS-IS L2 as the IGP. Enable LDP on every core link. Establish iBGP between PE1 and PE2 with labeled unicast â€” but keep P1 and P2 BGP-free. Set up eBGP to both CEs. Enable RSVP-TE on all core links. Build Tunnel10 from PE1 to PE2 with a dynamic primary path and an explicit secondary path through P2 for path diversity. When finished, verify a customer packet from CE1 to CE2 traverses the core entirely on MPLS labels.

```
                   AS 65100  IS-IS L2 + MPLS LDP + RSVP-TE

              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â”‚          BGP-free core               â”‚
              â”‚                                      â”‚
  AS 65101    â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”‚   AS 65102
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚  â”‚    PE1    â”œL2â”€â”¤    P1     â”‚       â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   CE1    â”œL1â”¤  â”‚ AS 65100  â”‚   â”‚(BGP-free) â”‚       â”‚L7â”¤   CE2    â”‚
â”‚10.0.0.11 â”‚  â”‚  â”‚10.0.0.1   â”‚   â”‚10.0.0.2   â”‚       â”‚  â”‚10.0.0.12 â”‚
â”‚192.0.2.1 â”‚  â”‚  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”¬â”˜   â””â”€â”€â”¬â”€â”€â”€â”¬â”€â”€â”€â”¬â”˜       â”‚  â”‚198.51... â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚     L3â”‚     â”‚iBGP   â”‚L4 â”‚   â”‚L5      â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚       â”‚     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚       â”‚
              â”‚  â”Œâ”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”    â”‚
              â”‚  â”‚    P2     â”œâ”€L6â”€â”€â”€â”€â”€â”€â”¤    PE2    â”‚    â”‚
              â”‚  â”‚(BGP-free) â”‚         â”‚ AS 65100  â”‚    â”‚
              â”‚  â”‚10.0.0.3   â”‚         â”‚10.0.0.4   â”‚    â”‚
              â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
              â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Link table:**

| Link | Endpoints | Subnet | Protocols |
|------|-----------|--------|-----------|
| L1 | CE1 Gi0/0 â†” PE1 Gi0/0 | 10.10.111.0/24 | eBGP |
| L2 | PE1 Gi0/1 â†” P1 Gi0/0 | 10.10.12.0/24 | IS-IS L2 + LDP + RSVP |
| L3 | PE1 Gi0/2 â†” P2 Gi0/0 | 10.10.13.0/24 | IS-IS L2 + LDP + RSVP |
| L4 | P1 Gi0/1 â†” P2 Gi0/1 | 10.10.23.0/24 | IS-IS L2 + LDP + RSVP |
| L5 | P1 Gi0/2 â†” PE2 Gi0/1 | 10.10.24.0/24 | IS-IS L2 + LDP + RSVP |
| L6 | P2 Gi0/2 â†” PE2 Gi0/2 | 10.10.34.0/24 | IS-IS L2 + LDP + RSVP |
| L7 | PE2 Gi0/0 â†” CE2 Gi0/0 | 10.10.122.0/24 | eBGP |

**Path diversity note:** The diamond topology provides three paths from PE1 to PE2:
- PE1â†’P1â†’PE2 (via L2 + L5) â€” likely the dynamic CSPF choice (lower metric)
- PE1â†’P2â†’PE2 (via L3 + L6) â€” the explicit secondary
- PE1â†’P1â†’P2â†’PE2 (via L2 + L4 + L6) â€” a third path through the P1â†”P2 cross-link

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| PE1 | SP Edge â€” TE headend, iBGP to PE2, eBGP to CE1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| P1 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| P2 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| PE2 | SP Edge â€” TE tail, iBGP to PE1, eBGP to CE2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| CE1 | Customer Edge AS 65101 â€” announces 192.0.2.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| CE2 | Customer Edge AS 65102 â€” announces 198.51.100.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | Router ID, LDP ID, iBGP source, RSVP headend |
| P1 | Loopback0 | 10.0.0.2/32 | Router ID, LDP ID, TE router-id |
| P2 | Loopback0 | 10.0.0.3/32 | Router ID, LDP ID, TE router-id |
| PE2 | Loopback0 | 10.0.0.4/32 | Router ID, LDP ID, iBGP source, RSVP tail |
| CE1 | Loopback0 | 10.0.0.11/32 | CE router ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix announced via eBGP |
| CE2 | Loopback0 | 10.0.0.12/32 | CE router ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix announced via eBGP |

### Cabling

| Link | Device A | Interface | IP Address | Device B | Interface | IP Address |
|------|----------|-----------|-----------|----------|-----------|-----------|
| L1 | CE1 | Gi0/0 | 10.10.111.11/24 | PE1 | Gi0/0 | 10.10.111.1/24 |
| L2 | PE1 | Gi0/1 | 10.10.12.1/24 | P1 | Gi0/0 | 10.10.12.2/24 |
| L3 | PE1 | Gi0/2 | 10.10.13.1/24 | P2 | Gi0/0 | 10.10.13.3/24 |
| L4 | P1 | Gi0/1 | 10.10.23.2/24 | P2 | Gi0/1 | 10.10.23.3/24 |
| L5 | P1 | Gi0/2 | 10.10.24.2/24 | PE2 | Gi0/1 | 10.10.24.4/24 |
| L6 | P2 | Gi0/2 | 10.10.34.3/24 | PE2 | Gi0/2 | 10.10.34.4/24 |
| L7 | PE2 | Gi0/0 | 10.10.122.4/24 | CE2 | Gi0/0 | 10.10.122.12/24 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| CE1 | 192.0.2.0/24 | eBGP network | Customer A aggregate |
| CE2 | 198.51.100.0/24 | eBGP network | Customer B aggregate |

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
- Hostnames
- Interface IP addressing (all routed links and loopbacks)
- DNS lookup disabled
- All interfaces administratively enabled

**IS NOT pre-loaded** (student configures this):
- IS-IS routing process and adjacencies
- MPLS LDP on core-facing interfaces
- iBGP between PE1 and PE2 with labeled unicast
- eBGP to CE1 and CE2 with customer prefix advertisement
- MPLS TE global and per-interface enablement
- IS-IS TE topology flooding extensions
- RSVP reservable bandwidth on core links
- TE tunnel interfaces and explicit path definitions
- Autoroute announce

---

## 5. Lab Challenge: Full Protocol Mastery

### Task 1: Deploy IS-IS Level 2 as the Core IGP

- On PE1, P1, P2, and PE2, create an IS-IS routing process named CORE.
- Assign each router the correct NET address: `49.0001.0000.0000.000X.00` where X is the router's loopback digit (PE1=1, P1=2, P2=3, PE2=4).
- Set the IS-IS level to level-2-only and enable wide metrics.
- Place Loopback0 in passive mode so its /32 prefix is advertised without sending hellos.
- Activate IS-IS on every core-facing interface (L2, L3, L4, L5, L6 â€” both endpoints). Customer-facing interfaces (L1, L7) do not run IS-IS.
- Set the network type to point-to-point on every core IS-IS interface. This eliminates DIS election overhead and speeds adjacency formation.

**Verification:** `show clns neighbors` on each core router must show IS-IS adjacencies on every connected core link. `show ip route 10.0.0.X/32` from any core router must show IS-IS-learned routes to all four loopbacks. P1 and P2 must see each other's loopback via the L4 cross-link.

---

### Task 2: Enable MPLS LDP on All Core Interfaces

- Enable LDP globally on PE1, P1, P2, PE2. Set the label protocol to LDP and force the router-id to Loopback0.
- Activate MPLS forwarding on every core-facing interface: PE1 Gi0/1 and Gi0/2; P1 Gi0/0, Gi0/1, and Gi0/2; P2 Gi0/0, Gi0/1, and Gi0/2; PE2 Gi0/1 and Gi0/2.
- Set the MPLS MTU to 1508 on every core-facing interface. Two MPLS labels add 8 bytes of overhead (4 bytes each), so the interface MTU must accommodate 1500-byte payloads plus the label stack.

**Verification:** `show mpls ldp neighbor` on each core router must list every directly connected core neighbor with state `Oper`. `show mpls ldp bindings` must show local and remote label bindings for every /32 loopback. `show mpls forwarding-table` must show LFIB entries for each loopback with a valid outgoing label and interface.

---

### Task 3: Establish iBGP Between PEs with Labeled Unicast

- Configure BGP AS 65100 on PE1 and PE2 only. P1 and P2 must have zero BGP configuration.
- On PE1, create an iBGP neighbor relationship to PE2 using PE2's Loopback0 (10.0.0.4) with the update source set to Loopback0.
- On PE2, create the reciprocal iBGP neighbor relationship to PE1.
- Under the IPv4 address family, activate the iBGP neighbor and enable `send-label` on both PEs. This advertises an MPLS label alongside each BGP prefix â€” the foundation of Unified BGP / BGP-LU.
- On PE1, configure `next-hop-self` toward PE2 so that routes learned from CE1 are re-advertised to PE2 with PE1's loopback as the next hop.
- Advertise each PE's own loopback (10.0.0.1/32 on PE1, 10.0.0.4/32 on PE2) into BGP via the `network` statement.

**Verification:** `show ip bgp summary` on PE1 must show PE2 in state `Established` (or a number in the `State/PfxRcd` column). `show ip bgp summary` on P1 and P2 must return `% BGP not active`. `show ip bgp labels` on PE1 must show PE2's loopback (10.0.0.4/32) with an MPLS label.

---

### Task 4: Configure eBGP to Customer Edges

- On CE1, configure BGP AS 65101. Establish an eBGP session to PE1 (10.10.111.1). Advertise the customer prefix 192.0.2.0/24 (Loopback1) using a `network` statement.
- On PE1, add CE1 as an eBGP neighbor under the existing BGP process.
- On CE2, configure BGP AS 65102. Establish an eBGP session to PE2 (10.10.122.4). Advertise the customer prefix 198.51.100.0/24 (Loopback1) using a `network` statement.
- On PE2, add CE2 as an eBGP neighbor under the existing BGP process.

**Verification:** `show ip bgp summary` on PE1 must show CE1 (10.10.111.11) as an eBGP neighbor. `show ip bgp summary` on PE2 must show CE2 (10.10.122.12) as an eBGP neighbor. `show ip bgp 192.0.2.0/24` on PE1 must show the prefix learned from CE1. `show ip bgp 198.51.100.0/24` on PE2 must show the prefix learned from CE2.

---

### Task 5: Enable MPLS Traffic Engineering Globally and Per-Interface

- Enable MPLS TE globally on PE1, P1, P2, and PE2. The global command alone is not sufficient â€” you must also enable TE on each core-facing interface.
- Enable MPLS TE on every core-facing interface: PE1 Gi0/1 and Gi0/2; P1 Gi0/0, Gi0/1, and Gi0/2; P2 Gi0/0, Gi0/1, and Gi0/2; PE2 Gi0/1 and Gi0/2. Customer-facing interfaces (PE1 Gi0/0, PE2 Gi0/0) do not need TE.

**Verification:** `show mpls interfaces detail` must show `Traffic Engineering: enabled` on each core-facing interface where TE was applied.

---

### Task 6: Enable IS-IS Traffic Engineering Extensions

- On each core router (PE1, P1, P2, PE2), under the IS-IS process, enable TE topology flooding for level-2 and set the TE router-id to Loopback0. These two commands instruct IS-IS to originate Extended IS Reachability (TLV 22) sub-TLVs carrying per-link bandwidth, max reservable bandwidth, and TE metric.

**Verification:** `show mpls traffic-eng topology` on PE1 must list all four core routers (PE1, P1, P2, PE2) as TE nodes, with per-link bandwidth attributes for every connected core interface. If any router is absent, its IS-IS TE extensions are not configured.

---

### Task 7: Configure RSVP Bandwidth Reservations on Core Links

- On every core-facing interface of PE1, P1, P2, and PE2 (all six links L2â€“L6, both endpoints), configure RSVP reservable bandwidth: 100,000 kbps (100 Mbps) total pool and 100,000 kbps (100 Mbps) maximum per-flow. This enables RSVP on the interface and sets the admission control threshold.

**Verification:** `show ip rsvp interface` on each core router must show all core-facing interfaces listed with 100,000 kbps allocated (ifIndex max) and 100,000 kbps maximum per-flow (flow max).

---

### Task 8: Build Tunnel10 with Path Diversity and Autoroute

- On PE1, define an explicit path named `PE1-via-P2` that transits through P2. Use loose next-address hops: first P2's loopback (10.0.0.3), then PE2's loopback (10.0.0.4). Loose hops let CSPF route between waypoints via any available links.
- Create a TE tunnel interface numbered 10 destined for PE2's loopback (10.0.0.4).
- Set the tunnel IP address to unnumbered Loopback0 (avoids consuming a /30 subnet per tunnel).
- Set the tunnel mode to MPLS TE.
- Set the tunnel bandwidth to 10,000 kbps (10 Mbps). CSPF uses this value during path computation â€” any link with less than 10,000 kbps available will be pruned.
- Set the tunnel setup and hold priorities to 1 (high priority). Equal priorities prevent the tunnel from preempting others or being preempted.
- Attach `path-option 10 dynamic` as the primary path â€” CSPF computes the best path automatically.
- Attach `path-option 20 explicit name PE1-via-P2` as the secondary path â€” this forces transit through P2, providing true path diversity from whichever path the dynamic primary selects.
- Enable autoroute announce so IS-IS installs PE2's loopback reachability through Tunnel10. Without this, the tunnel exists but no traffic uses it.

**Verification:** `show mpls traffic-eng tunnels tunnel10` must show `Admin: up Oper: up` and `Signalling: connected`. Both path-options must be listed (path-option 10 dynamic, path-option 20 explicit PE1-via-P2). `show ip route 10.0.0.4` on PE1 must show Tunnel10 as the outgoing interface (autoroute installed).

---

### Task 9: End-to-End Customer Reachability and Core Invariants

- From PE1, verify the full forwarding path to PE2 using `traceroute 10.0.0.4` â€” it must exit via Tunnel10, not a physical interface.
- From CE1, verify end-to-end customer traffic by pinging CE2's customer prefix: `ping 198.51.100.1 source 192.0.2.1`.
- Verify the BGP-free core invariant: `show ip bgp summary` on P1 and P2 must both return `% BGP not active`.
- Verify LDP health: `show mpls ldp neighbor` on every core router shows all directly connected neighbors with state `Oper`.
- Verify the TE tunnel's secondary path is ready: `show mpls traffic-eng tunnels tunnel10` shows path-option 20 in standby state.

**Verification:** CE1-to-CE2 ping must succeed (5/5 success). Traceroute from PE1 to 10.0.0.4 must exit Tunnel10. No BGP process on P1 or P2. All LDP sessions operational. Tunnel10 UP with both path-options visible.

---

## 6. Verification & Analysis

### Task 1: IS-IS Adjacencies and Loopback Reachability

```
PE1# show clns neighbors

System Id      Interface   SNPA                State  Holdtime  Type Protocol
P1             Gi0/1       aabb.cc00.0200      Up     26        L2   IS-IS
P2             Gi0/2       aabb.cc00.0300      Up     25        L2   IS-IS
! â† PE1 must have L2 adjacencies on both Gi0/1 (to P1) and Gi0/2 (to P2)

P1# show clns neighbors

System Id      Interface   SNPA                State  Holdtime  Type Protocol
PE1            Gi0/0       aabb.cc00.0101      Up     27        L2   IS-IS
P2             Gi0/1       aabb.cc00.0301      Up     28        L2   IS-IS
PE2            Gi0/2       aabb.cc00.0401      Up     26        L2   IS-IS
! â† P1 must have 3 adjacencies: PE1, P2 (via L4), PE2

PE1# show ip route 10.0.0.4
Routing entry for 10.0.0.4/32
  Known via "isis", distance 115, metric 20, type level-2
  ! â† PE2's loopback must be reachable via IS-IS with a valid metric
```

### Task 2: LDP Sessions and Label Bindings

```
PE1# show mpls ldp neighbor
    Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.2.646 - 10.0.0.1.50000
        State: Oper; Msgs sent/rcvd: 45/44; Downstream
        ! â† PE1â†”P1 LDP session UP, state Oper
    Peer LDP Ident: 10.0.0.3:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.3.646 - 10.0.0.1.50001
        State: Oper; Msgs sent/rcvd: 42/41; Downstream
        ! â† PE1â†”P2 LDP session UP

PE1# show mpls forwarding-table 10.0.0.4
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Swapped      interface
16         17         10.0.0.4/32      0             Gi0/1      10.10.12.2
! â† LFIB shows the label PE1 pushes (17 learned from P1) and the outgoing interface
```

### Task 3: iBGP with Labeled Unicast

```
PE1# show ip bgp summary
BGP router identifier 10.0.0.1, local AS number 65100
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.4        4        65100      50      51        5    0    0 00:42:30        1
! â† iBGP session to PE2 UP; 1 prefix received

P1# show ip bgp summary
% BGP not active
! â† CRITICAL: This must be the exact output. If BGP is running on P1, remove it.

PE1# show ip bgp labels
   Network          Next Hop      In label/Out label
   10.0.0.1/32      0.0.0.0         imp-null/nolabel        ! â† own loopback, no label needed
   10.0.0.4/32      10.0.0.4        nolabel/20              ! â† PE2's loopback: BGP-LU label 20
```

### Tasks 4 & 5: eBGP and TE Enablement

```
PE1# show ip bgp 192.0.2.0
BGP routing table entry for 192.0.2.0/24, version 2
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65101
    10.10.111.11 from 10.10.111.11 (10.0.0.11)
      Origin IGP, metric 0, localpref 100, valid, external, best
      ! â† CE1's prefix learned via eBGP

PE1# show mpls interfaces detail
Interface GigabitEthernet0/1:
        IP Forwarding: enabled
        MPLS operational: YES
        MPLS installed: YES
        Traffic Engineering: enabled     ! â† must show 'enabled'
```

### Tasks 6 & 7: TE Topology and RSVP

```
PE1# show mpls traffic-eng topology
...
My_System_id: 0000.0000.0001.00 (isis CORE)
Prio    BW[0]       BW[1]       BW[2]       BW[3]       BW[4]       BW[5]       BW[6]       BW[7]
 Link[0]: Point-to-Point, Nbr Node id 1, gen 3
   frag_id 0, Intf Address: 10.10.12.1, Nbr Intf Address: 10.10.12.2
   BW[0]: 100000        100000        100000        100000        100000  ! â† 100 Mbps on L2
 Link[1]: Point-to-Point, Nbr Node id 2, gen 3
   frag_id 0, Intf Address: 10.10.13.1, Nbr Intf Address: 10.10.13.3
   BW[0]: 100000        100000        100000        100000        100000  ! â† 100 Mbps on L3
! â† All 4 core nodes (PE1, P1, P2, PE2) must appear with bandwidth attributes.
!    If any node is missing, its IS-IS TE extensions are not configured.

PE1# show ip rsvp interface
            allocated  i/f max  flow max
Gi0/1          0         100000   100000  ! â† 100,000 kbps (100 Mbps)
Gi0/2          0         100000   100000  ! â† both core PE1 interfaces

P1# show ip rsvp interface
            allocated  i/f max  flow max
Gi0/0          0         100000   100000  ! â† L2 toward PE1
Gi0/1          0         100000   100000  ! â† L4 toward P2
Gi0/2          0         100000   100000  ! â† L5 toward PE2
```

### Task 8: Tunnel10 with Dual Path-Options

```
PE1# show mpls traffic-eng tunnels tunnel10
Name:PE1_t10                             (Tunnel10) Destination: 10.0.0.4
  Status:
    Admin: up         Oper: up     Path: valid       Signalling: connected

    path option 10, type dynamic (Basis for Setup, path weight 2)
    Path info (PCE disabled):
      Explicit Route: 10.10.12.2 10.10.24.2 10.0.0.4
      ! â† CSPF chose the path via P1 (PE1â†’P1â†’PE2)

    path option 20, type explicit PE1-via-P2
    ! â† Secondary: forces PE1â†’P2â†’PE2 transit. Standby â€” active only if primary fails.

PE1# show ip route 10.0.0.4
Routing entry for 10.0.0.4/32
  Known via "isis", distance 115, metric 30, type level-2
  Routing Descriptor Blocks:
  * directly connected, via Tunnel10
    ! â† autoroute announce installed â€” PE2's loopback reachable via the tunnel
```

### Task 9: End-to-End Forwarding

```
PE1# traceroute 10.0.0.4
Type escape sequence to abort.
Tracing the route to 10.0.0.4
  1 10.0.0.4 [MPLS: Labels 17/Exp 0] 4 msec 4 msec 4 msec
    ! â† First hop exits via Tunnel10; MPLS label stack pushed

CE1# ping 198.51.100.1 source 192.0.2.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 198.51.100.1, timeout is 2 seconds:
Packet sent with a source address of 192.0.2.1
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 12/15/20 ms
! â† Customer traffic flows end-to-end across the MPLS core through the BGP-free P routers

P2# show ip bgp summary
% BGP not active
! â† BGP-free core invariant verified on P2
```

---

## 7. Verification Cheatsheet

### IS-IS Process Configuration

```
router isis CORE
 net 49.0001.0000.0000.000X.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface GigabitEthernet0/X
 ip router isis CORE
 isis network point-to-point
```

| Command | Purpose |
|---------|---------|
| `show clns neighbors` | Verify IS-IS adjacencies on all core links |
| `show clns is-neighbors detail` | Confirm level-2-only and point-to-point |
| `show isis database verbose` | Inspect LSP contents and sequence numbers |
| `show ip route isis` | Check IS-IS-learned routes |

> **Exam tip:** `isis network point-to-point` on Ethernet interfaces eliminates the 40-second DIS election and pseudo-node LSP generation. Without it, IS-IS treats the link as broadcast and generates unnecessary type-2 LSPs.

### MPLS LDP Configuration

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/X
 mpls ip
 mpls mtu override 1508
```

| Command | Purpose |
|---------|---------|
| `show mpls ldp neighbor` | Verify LDP sessions (state Oper, not INIT or OPENREC) |
| `show mpls ldp discovery` | Check hello-level neighbor discovery |
| `show mpls ldp bindings` | LIB: all label bindings (local + remote) per prefix |
| `show mpls forwarding-table` | LFIB: the single next-hop label actually used to forward |

> **Exam tip:** The LIB contains ALL received label bindings. The LFIB contains only the ONE chosen by the IGP next-hop. The LIB can show 3+ remote bindings for a prefix while the LFIB shows only the IGP-best-path label.

### iBGP with Labeled Unicast

```
router bgp 65100
 neighbor 10.0.0.X remote-as 65100
 neighbor 10.0.0.X update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.X activate
  neighbor 10.0.0.X send-label
  neighbor 10.0.0.X next-hop-self
  network 10.0.0.X mask 255.255.255.255
```

| Command | Purpose |
|---------|---------|
| `show ip bgp summary` | Verify BGP sessions (PE1â†”PE2, PE1â†”CE1, PE2â†”CE2) |
| `show ip bgp labels` | Show BGP-LU label assignments per prefix |
| `show ip bgp neighbors <peer> advertised-routes` | Check what we're sending |

> **Exam tip:** `send-label` under `address-family ipv4 unicast` is what makes it "Unified BGP." Without it, BGP advertises prefixes but no labels â€” the BGP-free core cannot forward labeled traffic because the ingress PE has no BGP-LU label to stack.

### eBGP to Customer Edge

```
router bgp 6510X
 neighbor <CE-IP> remote-as 6510X
 !
 address-family ipv4
  neighbor <CE-IP> activate
  network <prefix> mask <mask>
```

| Command | Purpose |
|---------|---------|
| `show ip bgp 192.0.2.0/24` | Confirm CE1 prefix learned on PE1 |
| `show ip bgp 198.51.100.0/24` | Confirm CE2 prefix learned on PE2 |
| `show ip bgp neighbors <CE-IP> routes` | Check routes advertised/received |

### MPLS TE Global and Interface Enablement

```
mpls traffic-eng tunnels        ! global (all core routers)
!
interface GigabitEthernet0/X
 mpls traffic-eng tunnels       ! per core-facing interface
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng tunnels` | List all TE tunnels and their state |
| `show mpls interfaces detail` | Verify TE is enabled on each interface |

> **Exam tip:** `mpls traffic-eng tunnels` must be configured at BOTH the global level AND per interface. Missing either one â€” even with the other present â€” disables TE on that interface.

### IS-IS TE Extensions

```
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng topology` | Verify all routers visible in TED with bandwidth attributes |
| `show isis database verbose \| include TE` | Confirm TE sub-TLVs in IS-IS LSPs |

> **Exam tip:** A router in IS-IS but missing `mpls traffic-eng level-2` is invisible to CSPF. Its links won't appear in the TE topology, so no tunnel can be routed through it â€” even though the router is fully reachable via IS-IS.

### RSVP Interface Configuration

```
interface GigabitEthernet0/X
 ip rsvp bandwidth 100000 100000   ! total-kbps / max-flow-kbps
```

| Command | Purpose |
|---------|---------|
| `show ip rsvp interface` | List RSVP-enabled interfaces and bandwidth |
| `show ip rsvp request` | Show active RSVP PATH states |
| `show ip rsvp reservation` | Show active RESV states (bandwidth reserved) |

> **Exam tip:** RSVP is disabled on all interfaces by default. `ip rsvp bandwidth` is NOT optional â€” without it, no RSVP PATH message can traverse the interface and the tunnel stays DOWN with `Signalling: Down`.

### TE Tunnel Configuration (PE1 Headend)

```
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3
 next-address loose 10.0.0.4
!
interface Tunnel10
 ip unnumbered Loopback0
 tunnel mode mpls traffic-eng
 tunnel destination 10.0.0.4
 tunnel mpls traffic-eng autoroute announce
 tunnel mpls traffic-eng bandwidth 10000
 tunnel mpls traffic-eng priority 1 1
 tunnel mpls traffic-eng path-option 10 dynamic
 tunnel mpls traffic-eng path-option 20 explicit name PE1-via-P2
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng tunnels tunnel10` | Tunnel state, active path, path-options |
| `show mpls traffic-eng tunnels tunnel10 detail` | ERO hops, RSVP session details, bandwidth |
| `show ip route 10.0.0.4` | Confirm autoroute installed PE2 via tunnel |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | All core adjacencies UP, L2 IS-IS, correct neighbor system IDs |
| `show ip route 10.0.0.X/32` | IS-IS-learned loopback routes on every core router |
| `show mpls ldp neighbor` | State `Oper` for every directly connected core LDP peer |
| `show mpls forwarding-table` | LFIB entries for all loopbacks with valid labels |
| `show mpls interfaces detail` | `Traffic Engineering: enabled` on every core-facing interface |
| `show ip bgp summary` | PE1â†”PE2 iBGP + PE1â†”CE1 eBGP + PE2â†”CE2 eBGP all Established |
| `show ip bgp labels` | BGP-LU label for 10.0.0.4/32 on PE1 |
| `show mpls traffic-eng topology` | All 4 core nodes with bandwidth attributes |
| `show ip rsvp interface` | 100,000 kbps on all core-facing interfaces |
| `show mpls traffic-eng tunnels tunnel10` | Admin/Oper UP, both path-options listed |
| `show ip route 10.0.0.4` | Tunnel10 as outgoing interface (autoroute) |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| 255.255.255.255 | 0.0.0.0 | Loopback /32 host route |
| 255.255.255.0 | 0.0.0.255 | Point-to-point /24 links |
| 255.255.255.252 | 0.0.0.3 | /30 serial links |

### Common MPLS Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No IS-IS adjacency on a core link | `ip router isis CORE` missing on one side |
| LDP session stuck in INIT | LDP router-id mismatch or unreachable; TCP port 646 blocked |
| `show mpls ldp neighbor` empty | `mpls ip` missing on the interface |
| P router has BGP routes in RIB | BGP was configured on P1 or P2 â€” violates BGP-free core |
| Tunnel stays DOWN after configuration | IS-IS TE extensions missing on transit router; CSPF has no path |
| Tunnel UP but `show ip route` shows physical interface | `autoroute announce` missing on tunnel |
| P2 not in `show mpls traffic-eng topology` | `mpls traffic-eng level-2` missing under `router isis` on P2 |
| CE1â†’CE2 ping fails | Check the full chain: IS-IS reachability â†’ LDP sessions â†’ BGP routes â†’ label bindings |
| `show ip rsvp interface` shows interface missing | `ip rsvp bandwidth` not configured on that interface |
| Secondary path never comes up | RSVP bandwidth too low on transit link; CSPF pruned it |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS L2 IGP Deployment

<details>
<summary>Click to view PE1 Configuration</summary>

```bash
! PE1
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point
```
</details>

<details>
<summary>Click to view P1 Configuration</summary>

```bash
! P1
router isis CORE
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point
```
</details>

<details>
<summary>Click to view P2 Configuration</summary>

```bash
! P2
router isis CORE
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point
```
</details>

<details>
<summary>Click to view PE2 Configuration</summary>

```bash
! PE2
router isis CORE
 net 49.0001.0000.0000.0004.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
!
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show clns neighbors
show ip route isis
```
</details>

---

### Task 2: MPLS LDP Configuration

<details>
<summary>Click to view PE1 Configuration</summary>

```bash
! PE1
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/1
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/2
 mpls ip
 mpls mtu override 1508
```
</details>

<details>
<summary>Click to view P1 Configuration</summary>

```bash
! P1
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/1
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/2
 mpls ip
 mpls mtu override 1508
```
</details>

<details>
<summary>Click to view P2 Configuration</summary>

```bash
! P2
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/1
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/2
 mpls ip
 mpls mtu override 1508
```
</details>

<details>
<summary>Click to view PE2 Configuration</summary>

```bash
! PE2
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/1
 mpls ip
 mpls mtu override 1508
!
interface GigabitEthernet0/2
 mpls ip
 mpls mtu override 1508
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp neighbor
show mpls ldp bindings
show mpls forwarding-table
```
</details>

---

### Task 3: iBGP with Labeled Unicast

<details>
<summary>Click to view PE1 Configuration</summary>

```bash
! PE1
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 send-label
  neighbor 10.0.0.4 next-hop-self
  network 10.0.0.1 mask 255.255.255.255
 exit-address-family
```
</details>

<details>
<summary>Click to view PE2 Configuration</summary>

```bash
! PE2
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 neighbor 10.0.0.1 remote-as 65100
 neighbor 10.0.0.1 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.1 send-label
  network 10.0.0.4 mask 255.255.255.255
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp labels
show ip bgp
```
</details>

---

### Task 4: eBGP to Customer Edges

<details>
<summary>Click to view CE1 Configuration</summary>

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
 exit-address-family
```
</details>

<details>
<summary>Click to view PE1 eBGP Addition</summary>

```bash
! PE1 â€” add to existing BGP config from Task 3
router bgp 65100
 neighbor 10.10.111.11 remote-as 65101
 !
 address-family ipv4
  neighbor 10.10.111.11 activate
```
</details>

<details>
<summary>Click to view CE2 Configuration</summary>

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
 exit-address-family
```
</details>

<details>
<summary>Click to view PE2 eBGP Addition</summary>

```bash
! PE2 â€” add to existing BGP config from Task 3
router bgp 65100
 neighbor 10.10.122.12 remote-as 65102
 !
 address-family ipv4
  neighbor 10.10.122.12 activate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp 192.0.2.0/24
show ip bgp 198.51.100.0/24
```
</details>

---

### Tasks 5 & 6: MPLS TE Global and IS-IS TE Extensions

<details>
<summary>Click to view PE1 Configuration</summary>

```bash
! PE1
mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
!
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view P1 Configuration</summary>

```bash
! P1
mpls traffic-eng tunnels
!
interface GigabitEthernet0/0
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
!
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view P2 Configuration</summary>

```bash
! P2
mpls traffic-eng tunnels
!
interface GigabitEthernet0/0
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
!
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view PE2 Configuration</summary>

```bash
! PE2
mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
!
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls interfaces detail
show mpls traffic-eng topology
```
</details>

---

### Task 7: RSVP Bandwidth Configuration

<details>
<summary>Click to view All Core Routers RSVP Configuration</summary>

```bash
! PE1
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! P1
interface GigabitEthernet0/0
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! P2
interface GigabitEthernet0/0
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! PE2
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
!
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip rsvp interface
```
</details>

---

### Task 8: Tunnel10 with Path Diversity and Autoroute

<details>
<summary>Click to view PE1 Tunnel and Explicit Path Configuration</summary>

```bash
! PE1
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3
 next-address loose 10.0.0.4
!
interface Tunnel10
 ip unnumbered Loopback0
 tunnel mode mpls traffic-eng
 tunnel destination 10.0.0.4
 tunnel mpls traffic-eng autoroute announce
 tunnel mpls traffic-eng bandwidth 10000
 tunnel mpls traffic-eng priority 1 1
 tunnel mpls traffic-eng path-option 10 dynamic
 tunnel mpls traffic-eng path-option 20 explicit name PE1-via-P2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng tunnels tunnel10
show mpls traffic-eng tunnels tunnel10 detail
show ip route 10.0.0.4
traceroute 10.0.0.4
```
</details>

---

### Task 9: End-to-End Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On PE1
traceroute 10.0.0.4

! On CE1
ping 198.51.100.1 source 192.0.2.1

! On P1
show ip bgp summary

! On P2
show ip bgp summary

! On all core routers
show mpls ldp neighbor
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 â€” P2 Missing from TE Topology â€” Tunnel10 Secondary Path Not Viable

An engineer reports that the secondary path-option on Tunnel10 cannot signal. Tunnel10 is UP with its primary dynamic path, but `show mpls traffic-eng tunnels tunnel10` shows path-option 20 in a failed state. The customer has not noticed any outage because the primary path is active, but the team is concerned about path diversity during maintenance.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng topology` on PE1 must list P2 (10.0.0.3) as a TE node. Tunnel10 path-option 20 (explicit PE1-via-P2) must show as a viable secondary path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel10` â€” path-option 20 shows `[failed]` or is absent from the active/standby list. The explicit path `PE1-via-P2` has P2 as its first waypoint.
2. Inspect the TE topology: `show mpls traffic-eng topology` on PE1 â€” P2 (10.0.0.3) is absent from the node list. P1 and PE2 appear. P2 is reachable via IS-IS (`show ip route 10.0.0.3` returns a valid route).
3. Connect to P2 and check the IS-IS TE configuration: `show running-config | section isis` â€” the `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` lines are missing.
4. Confirm root cause: without TE flooding enabled, P2 does not originate Extended IS Reachability (TLV 22) sub-TLVs. CSPF on PE1 cannot see any links connected to P2, so it cannot compute a path through P2.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! P2
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

IS-IS TE LSAs flood within seconds. Verify on PE1: `show mpls traffic-eng topology` â€” P2 reappears with its L3, L4, and L6 links. The explicit secondary path `PE1-via-P2` can now signal.
</details>

---

### Ticket 2 â€” CE1-to-CE2 Ping Fails After a "Routine" P1 Change

CE1-to-CE2 ping (192.0.2.1 â†’ 198.51.100.1) is failing. The core IS-IS adjacencies and LDP sessions are all UP on every link. The tunnel (Tunnel10) is UP and signaling. BGP sessions between PE1â†”CE1 and PE2â†”CE2 are established, and BGP-LU between PE1â†”PE2 is exchanging labels. Yet customer traffic does not reach the far side. A junior engineer performed a "BGP-related maintenance" on P1 earlier today.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** CE1-to-CE2 ping succeeds. `show ip bgp summary` on P1 and P2 must both return `% BGP not active`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: CE1 `ping 198.51.100.1 source 192.0.2.1` fails. All single-hop checks pass (PE1 can ping PE2 loopback, CE1 can ping PE1, CE2 can ping PE2).
2. Check BGP route propagation: on PE1, `show ip bgp 198.51.100.0/24` is present (learned from PE2 via iBGP). On PE2, `show ip bgp 192.0.2.0/24` is present (learned from PE1). Routes are exchanged successfully.
3. Check the BGP-free core invariant: `show ip bgp summary` on P1 â€” instead of `% BGP not active`, the output shows a BGP process running with neighbor 10.0.0.1. BGP was configured on P1.
4. Understand the impact: when P1 runs BGP, it can intercept labeled traffic and try to IP-route it. Even if it doesn't break forwarding directly, it violates the architectural invariant (BGP-free core) and introduces unpredictable behavior at the P router level.
5. Check P1's running config: `show running-config | section router bgp` â€” a `router bgp 65100` block with a neighbor statement exists.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! P1
no router bgp 65100
```

After removal, `show ip bgp summary` on P1 returns `% BGP not active`. CE1-to-CE2 ping resumes. This is a critical lesson: P routers must never run BGP in a BGP-free core architecture. Any BGP configuration on P1 or P2 breaks the lab acceptance criteria.
</details>

---

### Ticket 3 â€” Tunnel10 Down After P1 Maintenance

A scheduled maintenance window on P1 involved a configuration reload. After the reload, Tunnel10 went down. IS-IS adjacencies are UP, LDP sessions are operational, and BGP is stable. The tunnel destination (10.0.0.4) is reachable via IS-IS from PE1. RSVP interfaces on P1's core links all show the correct bandwidth. Yet Tunnel10 is stuck in `Oper: down` with `Signalling: Down`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel10` must show `Admin: up Oper: up` and `Signalling: connected`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel10` â€” `Oper: down`, `Signalling: Down`. The primary path-option 10 (dynamic) is unable to signal.
2. Check the RSVP PATH flow: the headend PE1 sends PATH toward the next hop. On P1, `show ip rsvp interface` shows Gi0/0, Gi0/1, and Gi0/2 all listed with correct bandwidth (100,000 kbps). RSVP per-interface configuration is correct.
3. Check global TE state on P1: `show mpls interfaces detail` â€” interfaces show `Traffic Engineering: disabled` despite per-interface TE configuration. The global `mpls traffic-eng tunnels` command was not restored after the reload.
4. Check P1's running config: `show running-config | include traffic-eng` â€” only the per-interface commands appear. The global `mpls traffic-eng tunnels` is absent. TE is effectively disabled on P1 even though per-interface commands are present.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! P1
mpls traffic-eng tunnels
```

The single global command re-enables the TE control plane on P1. All per-interface `mpls traffic-eng tunnels` settings become active. RSVP PATH messages now pass through P1, RESV returns from PE2, and Tunnel10 re-establishes within seconds.

Verify: `show mpls traffic-eng tunnels tunnel10` shows `Oper: up` and `Signalling: connected`. `show mpls interfaces detail` on P1 shows `Traffic Engineering: enabled` on all core interfaces.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS L2 adjacencies on every core link (L2â€“L6); `show clns neighbors` shows all peers
- [ ] All four core loopbacks reachable via IS-IS from every core router
- [ ] `mpls label protocol ldp` and `mpls ldp router-id Loopback0 force` on PE1, P1, P2, PE2
- [ ] `mpls ip` and `mpls mtu override 1508` on every core-facing interface (L2â€“L6, both endpoints)
- [ ] `show mpls ldp neighbor` shows state `Oper` for every directly connected core pair
- [ ] `show mpls forwarding-table` has LFIB entries for all loopbacks with valid labels
- [ ] iBGP PE1â†”PE2 established; `show ip bgp summary` shows state `Established` on both PEs
- [ ] `send-label` under IPv4 address-family on both PE1 and PE2
- [ ] `show ip bgp labels` shows label bindings for PE loopbacks
- [ ] `show ip bgp summary` on P1 and P2 returns `% BGP not active`
- [ ] eBGP PE1â†”CE1 established; CE1 announces 192.0.2.0/24
- [ ] eBGP PE2â†”CE2 established; CE2 announces 198.51.100.0/24
- [ ] `mpls traffic-eng tunnels` globally configured on PE1, P1, P2, PE2
- [ ] `mpls traffic-eng tunnels` on every core-facing interface
- [ ] `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` under router isis CORE on all four core routers
- [ ] `show mpls traffic-eng topology` shows all 4 core nodes with bandwidth attributes
- [ ] `ip rsvp bandwidth 100000 100000` on all six core links (L2â€“L6), both endpoints
- [ ] `show ip rsvp interface` shows 100,000 kbps on every core-facing interface
- [ ] Tunnel10 UP with dynamic primary (path-option 10) and explicit secondary `PE1-via-P2` (path-option 20)
- [ ] `autoroute announce` enabled on Tunnel10 â€” `show ip route 10.0.0.4` exits via Tunnel10
- [ ] `traceroute 10.0.0.4` from PE1 shows Tunnel10 as the first hop
- [ ] CE1-to-CE2 ping (192.0.2.1 â†’ 198.51.100.1) succeeds with 5/5

### Troubleshooting

- [ ] Ticket 1 resolved: P2 visible in TE topology; Tunnel10 secondary path viable
- [ ] Ticket 2 resolved: BGP removed from P1; BGP-free core invariant restored
- [ ] Ticket 3 resolved: Tunnel10 re-established after restoring global TE on P1

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |

---

## Appendix B: XR-side Command Reference

PE1 and PE2 run **IOS XRv (light)** in this capstone. The IOS show/config
commands referenced earlier in the workbook do not exist on XR â€” use the
equivalents below when working on PE1 or PE2. P1, P2, CE1, and CE2 are still
IOSv; their commands are unchanged.

### Why XR here

The 300-510 blueprint is platform-agnostic for MPLS, but production SP edges
overwhelmingly run XR. The retrofit exposes you to XR's two-stage commit
model, mandatory route-policies, and the LDP / BGP-LU / RSVP-TE syntax you
will see in the CCIE SP lab and in real network operations. See
`memory/xr-coverage-policy.md` Â§2 (XR-mixed posture) for the project-wide
rationale.

### XR commit model (one-time orientation)

XR uses a **candidate / running** config split. Changes you type are staged
in the candidate config and do not take effect until you `commit`:

```
RP/0/0/CPU0:PE1# configure
RP/0/0/CPU0:PE1(config)# router bgp 65100
RP/0/0/CPU0:PE1(config-bgp)#  ...
RP/0/0/CPU0:PE1(config-bgp)# commit          ! applies to running
RP/0/0/CPU0:PE1(config-bgp)# end
```

`abort` discards uncommitted candidate. `show configuration` displays the
candidate diff before commit. `!` is a comment in XR â€” it does NOT exit a
sub-mode (use `exit` or `root`).

### IOS â†’ XR command equivalents (PE1 / PE2 only)

| Purpose | IOS (P1, P2, CE1, CE2) | IOS XR (PE1, PE2) |
|---|---|---|
| Show interface IP | `show ip interface brief` | `show ipv4 interface brief` |
| IS-IS adjacencies | `show clns neighbors` | `show isis neighbors` |
| IS-IS database | `show isis database` | `show isis database` |
| LDP neighbor / session | `show mpls ldp neighbor` | `show mpls ldp neighbor` |
| LDP discovery | `show mpls ldp discovery` | `show mpls ldp discovery` |
| LDP bindings | `show mpls ldp bindings` | `show mpls ldp bindings` |
| LIB / LFIB | `show mpls forwarding-table` | `show mpls forwarding` |
| BGP summary | `show ip bgp summary` | `show bgp ipv4 unicast summary` |
| BGP-LU summary | `show ip bgp ipv4 unicast neighbors X advertised-routes` | `show bgp ipv4 labeled-unicast summary` |
| BGP-LU labels | `show ip bgp labels` | `show bgp ipv4 labeled-unicast` |
| RSVP neighbors | `show ip rsvp neighbor` | `show rsvp neighbors` |
| RSVP reservations | `show ip rsvp reservation` | `show rsvp reservation` |
| TE tunnel state | `show mpls traffic-eng tunnels brief` | `show mpls traffic-eng tunnels brief` |
| TE topology | `show mpls traffic-eng topology` | `show mpls traffic-eng topology` |
| TE explicit-path | `show ip explicit-paths` | `show explicit-paths` |
| Save running config | `write memory` | `commit` (auto-persists; no separate save) |
| Reload | `reload` | `reload location all` |

### IOS â†’ XR config-block equivalents

| Purpose | IOS line | XR equivalent |
|---|---|---|
| Enable LDP on int | `mpls ip` (under int) | `mpls ldp\n interface GigE0/0/0/X` (global stanza) |
| BGP-LU on session | `neighbor X.X.X.X send-label` | `address-family ipv4 labeled-unicast` (session AF) |
| TE tunnel interface | `interface Tunnel10` | `interface tunnel-te10` |
| RSVP bandwidth | `ip rsvp bandwidth ... ` (under int) | `rsvp\n interface GigE0/0/0/X\n  bandwidth ...` |
| Mandatory policy | (not required) | `route-policy PASS\n pass\nend-policy` + `route-policy PASS in/out` per AF |
| Sub-mode exit | `!` or `exit` | `exit` (ALWAYS â€” `!` is a comment) |

### Verification flow on PE1 (XR-side)

```
RP/0/0/CPU0:PE1# show isis neighbors
RP/0/0/CPU0:PE1# show mpls ldp neighbor brief
RP/0/0/CPU0:PE1# show bgp ipv4 unicast summary
RP/0/0/CPU0:PE1# show bgp ipv4 labeled-unicast
RP/0/0/CPU0:PE1# show mpls traffic-eng tunnels tunnel-te10
RP/0/0/CPU0:PE1# show rsvp neighbors
RP/0/0/CPU0:PE1# show mpls forwarding
```

The expected outcomes (adjacency up, LDP session up, iBGP-LU established,
tunnel-te10 in `up/up` state) match the IOS-side checklist â€” only the
syntax differs.

### Known gaps

- This appendix gives commands, not full per-task XR rewrites. The verification
  tasks earlier in the workbook still describe the IOS workflow; running them
  on PE1/PE2 requires translating each `show` per the table above.
- XRv (light) does not support every advanced TE feature (no Flex-Algo, no
  P2MP TE, no PCEP). For features beyond what is exercised here see the
  `xr-bridge` topic (build deferred â€” `memory/xr-coverage-policy.md` Â§2).
- Configs are syntactically translated from the IOS sibling solution but
  have **not yet been verified in EVE-NG**. Expect minor adjustments after
  first boot â€” report any failures so the configs can be corrected.
