# MPLS Lab 04: Full Mastery â€” Capstone I

> **Platform Mix Notice (XR-mixed capstone):** PE1 and PE2 in this capstone run
> **IOS XRv (light, 6.1.x)**; P1, P2, CE1, CE2 remain IOSv. This retrofit
> exposes you to XR CLI for LDP, BGP labeled-unicast, and RSVP-TE â€” the
> production-realistic SP edge platform â€” without changing the lab's exam
> coverage. The IOS commands shown throughout sections 4-9 still apply on
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

**Exam Objective:** 4.1.aâ€“4.1.e â€” Troubleshoot MPLS (LDP, LSP, Unified BGP, BGP-free core, RSVP-TE) â€” CCNP SPRI 300-510

This is a Capstone I lab. The previous four labs taught each MPLS component in isolation: lab-00 introduced LDP and label distribution; lab-01 used MPLS OAM to verify LSPs; lab-02 added the BGP-free core architecture and BGP labeled-unicast; lab-03 layered RSVP-TE tunnels with explicit paths on top. This lab combines every blueprint bullet into a single end-to-end build that you start from an interfaces-only baseline. There is no step-by-step guidance â€” you design the configuration order, verify each layer before adding the next, and produce a working SP MPLS network.

### MPLS Component Layering

Each protocol in the stack depends on the layers below it. Building the stack in the wrong order produces confusing failures because diagnostics from a higher layer point at problems in a lower layer. The correct build order is bottom-up:

```
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚ Layer 5 â€” Customer reachability  â”‚  ping CE1 â†’ CE2
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â–²
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚ Layer 4 â€” RSVP-TE tunnels        â”‚  Tunnel10 dyn + explicit
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â–²
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚ Layer 3 â€” BGP                    â”‚  iBGP+LU PEâ†”PE; eBGP CEâ†”PE
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â–²
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚ Layer 2 â€” MPLS LDP               â”‚  LIB/LFIB on every core link
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â–²
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚ Layer 1 â€” IS-IS L2 IGP           â”‚  loopback reachability
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

If you add LDP before IS-IS converges, LDP cannot pick a router-id and the session will not establish. If you add iBGP before LDP, BGP-LU has no underlying LSPs to advertise. If you add MPLS-TE before LDP, TE tunnels signal but the core has no native MPLS forwarding for non-TE traffic. The capstone's verification commands (Section 6) are organized in the same bottom-up order so you can confirm each layer before moving on.

### IS-IS L2 as the SP IGP

IS-IS is the SP-native IGP because it runs directly over Layer 2 (no IP transport for the protocol packets), supports unlimited area sizes via `metric-style wide`, and natively flooded TE sub-TLVs (TLV 22 Extended IS Reachability) without the OSPF opaque-LSA gymnastics. The MPLS topic uses IS-IS area 49.0001, level-2-only on all four core routers, with `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` enabling TE flooding.

```
router isis CORE
 net 49.0001.0000.0000.000<X>.00     ! X = 1 (PE1), 2 (P1), 3 (P2), 4 (PE2)
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

Use `isis network point-to-point` on every core interface to skip the DIS election. This is mandatory on broadcast-style transports (Ethernet) when only two routers share the segment â€” without it, every IS-IS hello carries DIS election fields and every adjacency runs the DIS state machine, which slows convergence.

### MPLS LDP and the LIB/LFIB Distinction

LDP advertises a label binding to *every* peer for *every* IGP-known prefix. Each LSR therefore stores many remote bindings per prefix in its Label Information Base (LIB). At forwarding time, the router must collapse this set down to the *one* label it will actually swap to. The LFIB is that collapsed view â€” for a given prefix, the LFIB entry is the label that the IGP next-hop advertised. LDP-LIB is "everything I know"; LDP-LFIB is "what I will use."

```
PE1# show mpls ldp bindings 10.0.0.4 32        ! LIB â€” many remote labels
   tib entry: 10.0.0.4/32, rev 12
        local binding:  label: imp-null
        remote binding: lsr: 10.0.0.2:0, label: 16     ! P1's label
        remote binding: lsr: 10.0.0.3:0, label: 17     ! P2's label

PE1# show mpls forwarding-table 10.0.0.4       ! LFIB â€” one outgoing label
Local      Outgoing   Prefix          Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id    Switched      interface
---        16         10.0.0.4/32     0             Gi0/1      10.10.12.2
```

When a fault breaks the LSP at one hop, `show mpls ldp bindings` looks unchanged on the headend (LIB still lists every remote label) but `show mpls forwarding-table` shows the consequence (the LFIB entry may say `Untagged` or change next-hop). Always compare the two views when diagnosing label-plane failures.

### Unified BGP (BGP Labeled-Unicast) and the BGP-Free Core

The "BGP-free core" is the architectural insight that P routers do not need BGP because they never originate or terminate customer traffic â€” they only swap labels. PE routers carry the customer routes; P routers carry only IGP and labels. To make this work, the PEâ†’PE path must transport customer packets *as labeled traffic* so the P routers never look at the inner IP header.

LDP gives every PE a label for every remote PE loopback. PE1 pushes that label onto a customer packet, P routers swap on it, the penultimate hop pops, and PE2 delivers the native IP packet to CE2. Throughout the transit, P1 and P2 never look at 198.51.100.0/24 â€” they only swap MPLS labels keyed off the outer label that targets PE2's loopback.

BGP labeled-unicast (`neighbor X send-label` under `address-family ipv4`) layers a *second* label-distribution channel on top of LDP, this time inside BGP. PE1 and PE2 advertise their loopbacks to each other with attached labels; the labels can come from LDP (when LDP is running between the PEs) or from a different label allocator (when the PEs are in different ASes â€” Option C / seamless MPLS). For the capstone, BGP-LU and LDP run side-by-side; LDP wins for forwarding because the LFIB sources its labels from the IGP next-hop. BGP-LU is the future-proofing for inter-AS deployments.

```
router bgp 65100
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 send-label                   ! BGP-LU enabled
  neighbor 10.0.0.4 next-hop-self                ! PE1 hides core nexthops from CE
  network 10.0.0.1 mask 255.255.255.255          ! advertise own loopback into BGP
```

Forgetting `send-label` on either side is a session-level mismatch â€” the BGP session comes up but `show ip bgp labels` is empty. This is fault #3 in lab-05.

### RSVP-TE: Dynamic vs Explicit Path-Options on a Single Tunnel

A TE tunnel can hold a *list* of path-options, ordered by index, that the headend tries in sequence. The first one whose CSPF computation succeeds becomes the active path; the others are kept as standby alternatives. The MPLS capstone's Tunnel10 demonstrates this with two path-options:

```
interface Tunnel10
 tunnel mpls traffic-eng path-option 10 dynamic                   ! primary
 tunnel mpls traffic-eng path-option 20 explicit name PE1-via-P2  ! secondary
```

CSPF on PE1 picks the dynamic path first. With equal-cost L2 (PE1â†”P1) and L3 (PE1â†”P2) paths, the lower-router-id tie-break chooses P1, so the active path becomes PE1â†’P1â†’PE2. The secondary explicit path forces transit via P2 â€” true topological diversity from the primary because L4 (P1â†”P2) is shared by both paths only if both fail at once. Watching the tunnel re-optimize via `show mpls traffic-eng tunnels tunnel10 | include path` after a primary-path link shut is the most direct demonstration of TE resilience.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| End-to-end SP MPLS build | Layer IS-IS, LDP, BGP+LU, eBGP, MPLS-TE/RSVP, and TE tunnels in correct order from a clean baseline |
| BGP-free core architecture | Configure iBGP+LU only on PE routers; verify P routers have no BGP process |
| LDP forwarding inspection | Read LIB/LFIB output to confirm label distribution and forwarding correctness |
| BGP labeled-unicast | Enable `send-label` capability on iBGP between PEs; verify with `show ip bgp labels` |
| TE topology + CSPF | Build IS-IS TE flooding, RSVP bandwidth pools, dynamic CSPF, and explicit standby paths |
| Tunnel10 with dual path-options | Configure primary dynamic + secondary explicit on a single tunnel for path redundancy |
| End-to-end customer traffic | Steer CE1â†’CE2 traffic through the labeled core via autoroute-announce on Tunnel10 |
| Capstone-level integration testing | Verify each MPLS layer with the right show command before declaring the build complete |

---

## 2. Topology & Scenario

**Scenario:** A new SP point-of-presence has been racked. Interfaces are physically up, IP addresses are pre-loaded, and IS-IS, LDP, BGP, and MPLS-TE are unconfigured. As the senior engineer on duty, you are responsible for designing and configuring the entire MPLS stack from scratch, verifying every layer, and demonstrating end-to-end customer reachability between CE1 (AS 65101, 192.0.2.0/24) and CE2 (AS 65102, 198.51.100.0/24) carried as labeled traffic across a BGP-free core. Tunnel10 must be configured on PE1 with a primary dynamic path and a secondary explicit path that transits the P-router not chosen by CSPF, providing resilience without depending on dynamic path re-computation.

```
                     AS 65100  IS-IS L2 + MPLS LDP + BGP-LU + RSVP-TE

                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                â”‚            BGP-free core             â”‚
                â”‚                                      â”‚
   AS 65101     â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” L2 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”‚     AS 65102
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚  â”‚    PE1    â”œâ”€â”€â”€â”€â”¤    P1     â”‚      â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚   CE1    â”œL1â”€â”¤  â”‚ AS 65100  â”‚    â”‚(BGP-free) â”‚      â”‚L7â”€â”¤   CE2    â”‚
 â”‚10.0.0.11 â”‚   â”‚  â”‚10.0.0.1   â”‚    â”‚10.0.0.2   â”‚      â”‚   â”‚10.0.0.12 â”‚
 â”‚192.0.2.1 â”‚   â”‚  â””â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜      â”‚   â”‚198.51... â”‚
 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚   iBGP â”‚ L3        L4   â”‚     L5     â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                â”‚   +LU  â”‚                â”‚            â”‚
                â”‚        â”‚          â”Œâ”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”      â”‚
                â”‚  â”Œâ”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â” L6 â”‚    P2     â”‚      â”‚
                â”‚  â”‚    PE2    â”œâ”€â”€â”€â”€â”¤(BGP-free) â”‚      â”‚
                â”‚  â”‚ AS 65100  â”‚    â”‚10.0.0.3   â”‚      â”‚
                â”‚  â”‚10.0.0.4   â”‚    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â”‚
                â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                       â”‚
                â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

  Tunnel10 on PE1 â†’ PE2 with two path-options:
    path-option 10 dynamic                  â†’ CSPF chooses PE1â†’P1â†’PE2 (active)
    path-option 20 explicit PE1-via-P2      â†’ forces PE1â†’P2â†’PE2 (standby)
```

Full link table:

| Link | Endpoints | Subnet | Protocol |
|------|-----------|--------|----------|
| L1 | CE1 Gi0/0 â†” PE1 Gi0/0 | 10.10.111.0/24 | eBGP |
| L2 | PE1 Gi0/1 â†” P1 Gi0/0 | 10.10.12.0/24 | IS-IS L2 + LDP + RSVP |
| L3 | PE1 Gi0/2 â†” P2 Gi0/0 | 10.10.13.0/24 | IS-IS L2 + LDP + RSVP |
| L4 | P1 Gi0/1 â†” P2 Gi0/1 | 10.10.23.0/24 | IS-IS L2 + LDP + RSVP |
| L5 | P1 Gi0/2 â†” PE2 Gi0/1 | 10.10.24.0/24 | IS-IS L2 + LDP + RSVP |
| L6 | P2 Gi0/2 â†” PE2 Gi0/2 | 10.10.34.0/24 | IS-IS L2 + LDP + RSVP |
| L7 | PE2 Gi0/0 â†” CE2 Gi0/0 | 10.10.122.0/24 | eBGP |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge â€” RSVP-TE headend; iBGP+LU peer; eBGP to CE1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | SP Edge â€” RSVP-TE tail; iBGP+LU peer; eBGP to CE2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Customer Edge AS 65101 â€” announces 192.0.2.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer Edge AS 65102 â€” announces 198.51.100.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | IS-IS NET, LDP ID, BGP RID, RSVP-TE headend |
| P1 | Loopback0 | 10.0.0.2/32 | IS-IS NET, LDP ID, TE router-id |
| P2 | Loopback0 | 10.0.0.3/32 | IS-IS NET, LDP ID, TE router-id |
| PE2 | Loopback0 | 10.0.0.4/32 | IS-IS NET, LDP ID, BGP RID, RSVP-TE tail |
| CE1 | Loopback0 | 10.0.0.11/32 | CE router ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix announced via eBGP |
| CE2 | Loopback0 | 10.0.0.12/32 | CE router ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix announced via eBGP |

### Cabling

| Link | Device A | Interface | IP Address | Device B | Interface | IP Address |
|------|----------|-----------|------------|----------|-----------|------------|
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
| CE1 | 192.0.2.0/24 | eBGP network | Customer A aggregate (Loopback1) |
| CE2 | 198.51.100.0/24 | eBGP network | Customer B aggregate (Loopback1) |
| PE1 | 10.0.0.1/32 | iBGP+LU network | PE1 loopback advertised with label to PE2 |
| PE2 | 10.0.0.4/32 | iBGP+LU network | PE2 loopback advertised with label to PE1 |

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
- Interface IP addressing (all routed links and loopbacks on all six devices)
- DNS lookup disabled

**IS NOT pre-loaded** (student configures this):
- IS-IS L2 routing process and adjacencies
- IS-IS TE flooding extensions (level-2 + TE router-id)
- MPLS LDP global enablement and per-interface LDP
- MPLS LDP router-id sourced from Loopback0
- MPLS MTU on core-facing interfaces
- iBGP between PE1 and PE2 (loopback-sourced) with BGP labeled-unicast
- eBGP between PE1â†”CE1 and PE2â†”CE2 with customer prefix advertisement
- BGP next-hop-self on PE iBGP sessions
- MPLS-TE global enablement and per-interface RSVP/TE
- RSVP reservable bandwidth pools on all core links
- Tunnel10 with primary dynamic path-option and secondary explicit path-option (PE1-via-P2)
- Autoroute-announce on Tunnel10 to steer PE2-destined traffic into the tunnel
- Explicit path definition PE1-via-P2

Critical invariants that the student must preserve:
- P1 and P2 must remain BGP-free â€” no BGP process configuration on either device.
- Customer traffic CE1â†’CE2 must traverse the core as labeled MPLS, not as IP routed traffic.

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete MPLS solution from scratch â€” IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Design Requirements

Build the SP MPLS stack in this order (each layer depends on the one below it):

### Task 1: IS-IS L2 Underlay

- Bring up an IS-IS routing process tagged CORE in area 49.0001, level-2 only, on PE1, P1, P2, and PE2.
- Use NET addresses whose system-id matches the loopback last octet: 0000.0000.0001 on PE1, 0000.0000.0002 on P1, 0000.0000.0003 on P2, 0000.0000.0004 on PE2.
- Use the wide metric style (24-bit metrics) so the IS-IS LSPs can carry MPLS-TE sub-TLVs.
- Mark Loopback0 as passive on every router so loopback addresses are advertised but no hellos are sent out of them.
- Activate IS-IS on every core link (L2, L3, L4, L5, L6) and configure those interfaces as point-to-point so no DIS election runs.
- Do not run IS-IS on customer-facing interfaces (PE1 Gi0/0, PE2 Gi0/0).

**Verification:** `show clns neighbors` on every core router must show full IS-IS adjacency on every directly connected core link. `show ip route isis` on PE1 must show the other three core loopbacks (10.0.0.2, 10.0.0.3, 10.0.0.4) reachable via IS-IS.

---

### Task 2: MPLS LDP + Forwarding

- Enable MPLS LDP globally on PE1, P1, P2, PE2 and pin the LDP router-id to Loopback0 with the force option so LDP does not require IGP convergence to choose its router-id.
- Enable MPLS forwarding on every core-facing interface (L2, L3, L4, L5, L6 â€” both endpoints of each link).
- Set the MPLS MTU on every core-facing interface to 1508 bytes to absorb the two-label MPLS overhead without fragmenting full-sized IP frames.
- Do not enable MPLS on customer-facing interfaces (PE1 Gi0/0, PE2 Gi0/0).

**Verification:** `show mpls ldp neighbor` on every core router must list one LDP neighbor per directly connected core link, all in `Oper: Up` state. `show mpls forwarding-table 10.0.0.4` on PE1 must show an LFIB entry with an outgoing label and an outgoing core interface (Gi0/1 or Gi0/2). `show mpls ldp bindings 10.0.0.4 32` must show implicit-null advertised by PE2 â€” confirming PHP.

---

### Task 3: iBGP + BGP Labeled-Unicast (PE1â†”PE2)

- Configure a BGP process for AS 65100 on PE1 and PE2 only. P1 and P2 must remain BGP-free â€” any BGP process on either P router fails the lab.
- Establish a loopback-sourced iBGP session between PE1 and PE2 (update source Loopback0 on both ends).
- Enable BGP labeled-unicast on the iBGP session by adding the send-label capability under the IPv4 unicast address-family on both PEs. A one-sided send-label fails capability negotiation and no labels are exchanged.
- Apply next-hop-self on the iBGP session so eBGP-learned customer routes are re-advertised to the iBGP peer with the local PE's loopback as next-hop.
- Inject each PE's own Loopback0 (10.0.0.1 on PE1, 10.0.0.4 on PE2) into BGP so BGP-LU has something to label.

**Verification:** `show ip bgp summary` on PE1 must show neighbor 10.0.0.4 with State `Established`. `show ip bgp labels` on PE1 must list 10.0.0.4/32 with an in-label. `show ip bgp summary` on P1 and P2 must return `% BGP not active` â€” invariant.

---

### Task 4: eBGP to Customer Edges (CE1, CE2)

- Configure a BGP process for AS 65101 on CE1 with an eBGP neighbor toward PE1 (10.10.111.1, AS 65100) and advertise CE1's customer aggregate 192.0.2.0/24.
- Configure a BGP process for AS 65102 on CE2 with an eBGP neighbor toward PE2 (10.10.122.4, AS 65100) and advertise CE2's customer aggregate 198.51.100.0/24.
- Add the eBGP neighbor toward CE1 (10.10.111.11, AS 65101) under PE1's existing BGP process.
- Add the eBGP neighbor toward CE2 (10.10.122.12, AS 65102) under PE2's existing BGP process.
- Activate each eBGP neighbor under the IPv4 unicast address-family.

**Verification:** `show ip bgp 192.0.2.0/24` on PE1 must show the prefix learned from CE1 with valid/best status. `show ip bgp 198.51.100.0/24` on PE2 must show the prefix learned from CE2. After iBGP convergence, `show ip bgp 198.51.100.0/24` on PE1 must show the prefix learned from PE2 (10.0.0.4) via iBGP, and the converse on PE2 for 192.0.2.0/24.

---

### Task 5: MPLS Traffic Engineering Underlay

- Enable MPLS-TE globally on PE1, P1, P2, PE2.
- Enable MPLS-TE on every core-facing interface (per-interface activation is required in addition to the global switch).
- Under the IS-IS process on every core router, enable TE flooding at level-2 and pin the TE router-id to Loopback0 so TE sub-TLVs are originated for every core link.
- Configure RSVP reservable bandwidth on every core-facing interface at 100 Mbps total reservable and 100 Mbps maximum per-flow.

**Verification:** `show mpls traffic-eng topology` on any core router must list all four core nodes (PE1, P1, P2, PE2) and every core link with bandwidth attributes (â‰¥ 100,000 kbps reservable). `show ip rsvp interface` on every core router must list every core-facing interface with `i/f max` of 100,000 kbps.

---

### Task 6: Tunnel10 with Primary Dynamic + Secondary Explicit (PE1-via-P2)

- On PE1, define an explicit path named PE1-via-P2 with two loose hops: 10.0.0.3 (P2 loopback) and 10.0.0.4 (PE2 loopback). Loose hops let CSPF route between waypoints via any available links.
- On PE1, build a TE tunnel interface numbered 10 destined for PE2 (10.0.0.4) with these properties:
  - IP unnumbered from Loopback0 (avoids needing a /30 for the tunnel)
  - Tunnel mode set to MPLS traffic engineering
  - Tunnel-requested bandwidth of 10 Mbps (CSPF will prune any link with less than 10 Mbps available)
  - Setup and hold priority both set to 1 (high priority â€” allows preemption of lower-priority tunnels)
  - Autoroute announce enabled so IS-IS installs the tunnel destination via the tunnel
  - Primary path-option indexed 10 set to dynamic (CSPF-computed)
  - Secondary path-option indexed 20 set to explicit using the named path PE1-via-P2
- The dynamic primary will choose PE1â†’P1â†’PE2 (lower router-id tie-break). The explicit secondary forces PE1â†’P2â†’PE2 â€” the *other* P router â€” providing topological diversity from the primary.

**Verification:** `show mpls traffic-eng tunnels tunnel10` on PE1 must show `Admin: up`, `Oper: up`, `Signalling: connected`, with path-option 10 (dynamic) as the active path and path-option 20 (explicit PE1-via-P2) listed as configured. `show ip route 10.0.0.4` on PE1 must show the route exiting via Tunnel10 (autoroute installed). `traceroute 10.0.0.4` from PE1 must show Tunnel10 as the first-hop interface.

---

### Task 7: End-to-End Customer Reachability

- From CE1, ping CE2's customer prefix sourced from CE1's customer prefix (destination 198.51.100.1, source 192.0.2.1).
- The packet path must be: CE1 â†’ PE1 (eBGP IP) â†’ MPLS LSP via P1 (label-swapped, P1 never sees the inner IP) â†’ PE2 (label-popped, IP delivered to CE2) â†’ CE2.
- Confirm the BGP-free invariant on P1 and P2: BGP must not be running, and customer prefixes (192.0.2.0/24, 198.51.100.0/24) must not be in either P router's routing table. Customer reachability succeeds despite P routers having no knowledge of customer prefixes â€” the labels do the work.

**Verification:** CE1's ping to 198.51.100.1 with source 192.0.2.1 must return 5/5 success. `show ip bgp summary` on P1 and P2 must return `% BGP not active`. `show ip route 198.51.100.0` on P1 and P2 must return `% Network not in table`.

---

## 6. Verification & Analysis

### Task 1: IS-IS Adjacencies and Loopback Reachability

```
PE1# show clns neighbors
System Id      Interface   SNPA            State  Holdtime  Type Protocol
P1             Gi0/1       aabb.cc00.0210  Up     27        L2   IS-IS    ! â† L2 adjacency on L2
P2             Gi0/2       aabb.cc00.0310  Up     26        L2   IS-IS    ! â† L2 adjacency on L3

PE1# show ip route isis
i L2 10.0.0.2/32 [115/20] via 10.10.12.2, Gi0/1     ! â† P1 loopback via L2
i L2 10.0.0.3/32 [115/20] via 10.10.13.3, Gi0/2     ! â† P2 loopback via L3
i L2 10.0.0.4/32 [115/30] via 10.10.12.2, Gi0/1     ! â† PE2 loopback via P1
                          via 10.10.13.3, Gi0/2     ! â† PE2 also via P2 (ECMP)
```

### Task 2: MPLS LDP and Forwarding

```
PE1# show mpls ldp neighbor
    Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.2.646 - 10.0.0.1.49152
        State: Oper                                          ! â† must be 'Oper'
    Peer LDP Ident: 10.0.0.3:0; Local LDP Ident 10.0.0.1:0
        State: Oper                                          ! â† second neighbor (P2)

PE1# show mpls ldp bindings 10.0.0.4 32
   tib entry: 10.0.0.4/32, rev 12
        local binding:  label: 21
        remote binding: lsr: 10.0.0.2:0, label: 16            ! â† P1 advertised label 16
        remote binding: lsr: 10.0.0.3:0, label: 17            ! â† P2 advertised label 17

PE1# show mpls forwarding-table 10.0.0.4
Local      Outgoing   Prefix          Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id    Switched      interface
21         16         10.0.0.4/32     0             Gi0/1      10.10.12.2
                                                                ! â† LFIB picks the IGP-next-hop label (16 via P1)
```

### Task 3: iBGP + BGP-LU

```
PE1# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer InQ OutQ Up/Down  State/PfxRcd
10.0.0.4        4 65100      14      14        9    0    0 00:11:32        2     ! â† Established, prefixes learned
10.10.111.11    4 65101       8       9        9    0    0 00:06:18        1     ! â† eBGP CE1 also up

PE1# show ip bgp labels
   Network          Next Hop      In label/Out label
   10.0.0.1/32      0.0.0.0       imp-null/nolabel
   10.0.0.4/32      10.0.0.4      nolabel/21         ! â† BGP-LU label received from PE2

P1# show ip bgp summary
% BGP not active.                                     ! â† BGP-free core invariant
```

### Task 4: eBGP and CE-side Reachability

```
PE1# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 5
  Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65101
    10.10.111.11 from 10.10.111.11 (10.0.0.11)        ! â† learned from CE1 via eBGP
      Origin IGP, valid, external, best

PE2# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 8
  Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65101, (Received from a RR-client)
    10.0.0.1 (metric 30) from 10.0.0.1 (10.0.0.1)     ! â† learned from PE1 via iBGP, NH=10.0.0.1
      Origin IGP, metric 0, localpref 100, valid, internal, best
      mpls labels in/out nolabel/24                    ! â† BGP-LU label advertised by PE1
```

### Task 5: MPLS-TE Topology and RSVP

```
PE1# show mpls traffic-eng topology
My_System_id: 0000.0000.0001.00 (isis CORE)
 Link[0]: Point-to-Point, Nbr Node id 1, gen 3
   Intf Address: 10.10.12.1, Nbr Intf Address: 10.10.12.2
   BW[0]: 100000        100000        100000        100000        100000  ! â† 100 Mbps reservable on L2
 Link[1]: Point-to-Point, Nbr Node id 2, gen 3
   Intf Address: 10.10.13.1, Nbr Intf Address: 10.10.13.3
   BW[0]: 100000        100000        100000        100000        100000  ! â† 100 Mbps reservable on L3

PE1# show ip rsvp interface
            allocated  i/f max  flow max
Gi0/1          0         100000   100000  ! â† L2 toward P1
Gi0/2          0         100000   100000  ! â† L3 toward P2
```

### Task 6: Tunnel10 Status

```
PE1# show mpls traffic-eng tunnels tunnel10
Name: PE1_t10                          (Tunnel10) Destination: 10.0.0.4
  Status:
    Admin: up         Oper: up     Path: valid       Signalling: connected   ! â† all four must be 'up/valid/connected'

    path option 10, type dynamic (Basis for Setup, path weight 2)
    Path info (PCE disabled):
      Explicit Route: 10.10.12.2 10.10.24.2 10.0.0.4   ! â† active path: PE1â†’P1â†’PE2

    path option 20, type explicit PE1-via-P2          ! â† secondary: forces transit via P2

PE1# show ip route 10.0.0.4
Routing entry for 10.0.0.4/32
  Known via "isis", distance 115, metric 30, type level-2
  Routing Descriptor Blocks:
  * directly connected, via Tunnel10                  ! â† autoroute installed PE2 loopback via tunnel

PE1# traceroute 10.0.0.4
  1 10.0.0.4 [MPLS: Labels ...] 4 msec 4 msec 4 msec  ! â† first-hop exits via Tunnel10
```

### Task 7: End-to-End Customer Reachability and BGP-Free Verification

```
CE1# ping 198.51.100.1 source 192.0.2.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 198.51.100.1, timeout is 2 seconds:
Packet sent with a source address of 192.0.2.1
!!!!!                                                  ! â† 5/5 success â€” labeled core delivery
Success rate is 100 percent (5/5)

P1# show ip bgp summary
% BGP not active.                                      ! â† BGP-free invariant preserved

P1# show ip route 198.51.100.0
% Network not in table                                 ! â† P1 has no knowledge of customer prefixes

P2# show ip bgp summary
% BGP not active.                                      ! â† same on P2

P2# show ip route 198.51.100.0
% Network not in table                                 ! â† labels carry traffic, not IP lookup
```

---

## 7. Verification Cheatsheet

### IS-IS L2 Process Configuration

```
router isis CORE
 net 49.0001.0000.0000.000<X>.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0

interface GigabitEthernet0/N
 ip router isis CORE
 isis network point-to-point
```

| Command | Purpose |
|---------|---------|
| `router isis <tag>` | Create the IS-IS process (named tag, here CORE) |
| `net <NET>` | Set the IS-IS NET address (area + system-id) |
| `is-type level-2-only` | Restrict the router to level-2 (SP backbone) |
| `metric-style wide` | Use 24-bit metrics (required for TE) |
| `isis network point-to-point` | Skip DIS election on Ethernet between two routers |

> **Exam tip:** `metric-style wide` is mandatory for MPLS-TE because TE sub-TLVs use the wide-metric encoding. Forgetting it leaves IS-IS in narrow-metric mode and CSPF cannot read TE attributes.

### MPLS LDP Configuration

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force

interface GigabitEthernet0/N
 mpls ip
 mpls mtu override 1508
```

| Command | Purpose |
|---------|---------|
| `mpls label protocol ldp` | Set LDP as the label-distribution protocol (vs TDP) |
| `mpls ldp router-id Loopback0 force` | Pin LDP ID to Loopback0; `force` skips reachability check |
| `mpls ip` | Enable LDP on the interface |
| `mpls mtu override 1508` | Add 8 bytes (two labels) of headroom for label-stack frames |

> **Exam tip:** LDP router-id MUST be reachable. Sourcing it from a non-existent loopback flaps the LDP session every 30 s â€” a classic capstone fault.

### iBGP + BGP Labeled-Unicast (PE only)

```
router bgp 65100
 bgp router-id 10.0.0.X
 neighbor 10.0.0.Y remote-as 65100
 neighbor 10.0.0.Y update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.Y activate
  neighbor 10.0.0.Y send-label
  neighbor 10.0.0.Y next-hop-self
  network 10.0.0.X mask 255.255.255.255
```

| Command | Purpose |
|---------|---------|
| `update-source Loopback0` | Source the iBGP TCP session from the loopback (stable) |
| `send-label` | Enable BGP-LU capability â€” advertise labels with prefixes |
| `next-hop-self` | Rewrite next-hop to local PE's loopback when re-advertising eBGP routes |
| `network <Lo0>` | Inject the local PE loopback into BGP so BGP-LU has something to label |

> **Exam tip:** `send-label` MUST be on both ends of the iBGP session. A one-sided `send-label` causes a capability mismatch â€” the session comes up but no labels are exchanged. Verify with `show ip bgp neighbor X capability`.

### MPLS-TE + RSVP Configuration

```
mpls traffic-eng tunnels                    ! global on every TE-aware router

router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0

interface GigabitEthernet0/N
 mpls traffic-eng tunnels                   ! per-interface
 ip rsvp bandwidth 100000 100000            ! 100 Mbps reservable, 100 Mbps per-flow
```

| Command | Purpose |
|---------|---------|
| `mpls traffic-eng tunnels` (global) | Enable the MPLS-TE control plane on the router |
| `mpls traffic-eng tunnels` (interface) | Allow TE LSPs to traverse this interface |
| `mpls traffic-eng level-2` | Enable TE flooding at IS-IS level-2 (SP backbone) |
| `ip rsvp bandwidth <total> <per-flow>` | Enable RSVP and set the reservable bandwidth pool |

> **Exam tip:** `mpls traffic-eng tunnels` must be configured BOTH globally AND per-interface. Either alone is silent and broken. RSVP is also disabled by default â€” `ip rsvp bandwidth` is mandatory.

### Tunnel with Dual Path-Options (PE1)

```
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3
 next-address loose 10.0.0.4

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
| `tunnel mpls traffic-eng path-option 10 dynamic` | Primary path â€” let CSPF compute it |
| `tunnel mpls traffic-eng path-option 20 explicit name X` | Standby path â€” forced via the named explicit-path |
| `tunnel mpls traffic-eng autoroute announce` | Install the tunnel destination into IS-IS as a tunnel adjacency |
| `tunnel mpls traffic-eng bandwidth N` | Tell CSPF how much bandwidth to reserve along the path |

> **Exam tip:** Path-options are tried in *index order*. Path-option 10 wins if its CSPF computation succeeds; path-option 20 only signals if 10 fails. Listing the dynamic option last (e.g. 10 explicit, 20 dynamic) inverts the failover behaviour.

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show clns neighbors` | One full IS-IS adjacency per directly connected core link |
| `show mpls ldp neighbor` | One LDP neighbor per core link, all `Oper: Up`, LDP IDs sourced from Loopback0 |
| `show mpls ldp bindings 10.0.0.4 32` | Local + remote bindings; `imp-null` from PE2 confirms PHP |
| `show mpls forwarding-table 10.0.0.4` | LFIB entry with outgoing label and core interface |
| `show ip bgp summary` (on PE) | Both iBGP and eBGP neighbors `Established` |
| `show ip bgp summary` (on P) | Must return `% BGP not active` |
| `show ip bgp labels` | BGP-LU labels advertised between PE1 and PE2 |
| `show mpls traffic-eng topology` | All four core nodes; bandwidth attributes on every link |
| `show mpls traffic-eng tunnels tunnel10` | `Oper: up`, both path-options listed, active path is the dynamic one |
| `show ip route 10.0.0.4` (on PE1) | Outgoing interface = Tunnel10 (autoroute installed) |
| `ping 198.51.100.1 source 192.0.2.1` (on CE1) | 5/5 success â€” end-to-end labeled forwarding |

### Common MPLS Stack Failure Causes

| Symptom | Likely Cause |
|---------|--------------|
| LDP neighbor flaps every 30 s | LDP router-id sourced from a non-existent loopback |
| LFIB shows `Untagged` for a remote loopback | `mpls ip` missing on the outgoing core interface |
| 1500-byte ping fails end-to-end through core | `mpls mtu override 1508` not set on a core interface (default 1500 + label = drop) |
| BGP session up but `show ip bgp labels` empty | `send-label` mismatch â€” only one side configured |
| CE1â†’CE2 ping fails despite all sessions up | iBGP `next-hop-self` missing â€” PE2 cannot resolve PE1-learned eBGP next-hop |
| Tunnel10 stays DOWN | `mpls traffic-eng tunnels` missing globally on a P router (silent drop of RSVP PATH) |
| Tunnel10 secondary never signals | RSVP bandwidth too low on a transit link; CSPF prunes the path |
| `show mpls traffic-eng topology` missing a P router | `mpls traffic-eng level-2` not under that router's IS-IS process |
| BGP "active" on a P router | Someone violated the BGP-free invariant with a stray `router bgp` block |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS L2 Underlay

<details>
<summary>Click to view PE1 IS-IS Configuration</summary>

```bash
! PE1
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
!
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```
</details>

<details>
<summary>Click to view P1 IS-IS Configuration</summary>

```bash
! P1
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
!
router isis CORE
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```
</details>

<details>
<summary>Click to view P2 IS-IS Configuration</summary>

```bash
! P2 â€” same shape as P1, NET 0000.0000.0003
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
!
router isis CORE
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```
</details>

<details>
<summary>Click to view PE2 IS-IS Configuration</summary>

```bash
! PE2 â€” Gi0/0 is customer-facing (no IS-IS); Gi0/1 and Gi0/2 are core
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
!
router isis CORE
 net 49.0001.0000.0000.0004.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show clns neighbors
show ip route isis
show isis database
```
</details>

---

### Task 2: MPLS LDP

<details>
<summary>Click to view LDP Configuration â€” All Core Routers</summary>

```bash
! PE1, P1, P2, PE2 â€” global
mpls label protocol ldp
mpls ldp router-id Loopback0 force

! On every core-facing interface (PE1 Gi0/1, Gi0/2; P1 Gi0/0, Gi0/1, Gi0/2;
!  P2 Gi0/0, Gi0/1, Gi0/2; PE2 Gi0/1, Gi0/2):
interface GigabitEthernet0/N
 mpls ip
 mpls mtu override 1508
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp neighbor
show mpls ldp bindings 10.0.0.4 32
show mpls forwarding-table 10.0.0.4
```
</details>

---

### Task 3: iBGP + BGP Labeled-Unicast

<details>
<summary>Click to view PE1 iBGP+LU Configuration</summary>

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
<summary>Click to view PE2 iBGP+LU Configuration</summary>

```bash
! PE2 â€” mirror of PE1
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 neighbor 10.0.0.1 remote-as 65100
 neighbor 10.0.0.1 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.1 send-label
  neighbor 10.0.0.1 next-hop-self
  network 10.0.0.4 mask 255.255.255.255
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp labels
show ip bgp neighbor 10.0.0.4
```
</details>

---

### Task 4: eBGP to CE1 and CE2

<details>
<summary>Click to view CE1 BGP Configuration</summary>

```bash
! CE1 â€” AS 65101
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
<summary>Click to view CE2 BGP Configuration</summary>

```bash
! CE2 â€” AS 65102
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
<summary>Click to view PE1 and PE2 eBGP Additions</summary>

```bash
! PE1 â€” add eBGP peer toward CE1
router bgp 65100
 neighbor 10.10.111.11 remote-as 65101
 !
 address-family ipv4
  neighbor 10.10.111.11 activate
 exit-address-family

! PE2 â€” add eBGP peer toward CE2
router bgp 65100
 neighbor 10.10.122.12 remote-as 65102
 !
 address-family ipv4
  neighbor 10.10.122.12 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 192.0.2.0/24
show ip bgp 198.51.100.0/24
show ip bgp summary
```
</details>

---

### Task 5: MPLS-TE Underlay (Global, IS-IS, RSVP)

<details>
<summary>Click to view TE Global + IS-IS TE Extensions â€” All Core Routers</summary>

```bash
! Global on PE1, P1, P2, PE2
mpls traffic-eng tunnels

! Under IS-IS on every core router
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view Per-Interface TE + RSVP â€” All Core Interfaces</summary>

```bash
! On every core-facing interface (PE1 Gi0/1, Gi0/2; P1 Gi0/0, Gi0/1, Gi0/2;
!  P2 Gi0/0, Gi0/1, Gi0/2; PE2 Gi0/1, Gi0/2):
interface GigabitEthernet0/N
 mpls traffic-eng tunnels
 ip rsvp bandwidth 100000 100000
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng topology
show ip rsvp interface
show mpls interfaces detail
```
</details>

---

### Task 6: Tunnel10 with Dual Path-Options (PE1)

<details>
<summary>Click to view PE1 Tunnel10 + Explicit Path Configuration</summary>

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

### Task 7: End-to-End Customer Reachability

<details>
<summary>Click to view End-to-End Verification</summary>

```bash
! From CE1
ping 198.51.100.1 source 192.0.2.1

! On P1 and P2 â€” confirm BGP-free invariant
show ip bgp summary
show ip route 198.51.100.0
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands. The faults in this capstone test the most common build mistakes from Tasks 1â€“6 â€” fix them and the entire stack returns to the working state.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 â€” Tunnel10 Stays Down After a Routine Maintenance Window

The NOC reports that Tunnel10 has been down since the last change window even though the LDP-based LSP between PE1 and PE2 is working â€” `ping mpls ipv4 10.0.0.4/32` succeeds and IP traceroute exits via a physical core interface (no longer Tunnel10). All IS-IS adjacencies and LDP sessions are up. The headend RSVP PATH messages appear to be lost in transit.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel10` shows `Admin: up Oper: up Signalling: connected`. `show ip route 10.0.0.4` on PE1 exits via Tunnel10. `show mpls traffic-eng tunnels` on PE1 shows path-option 10 active.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel10` on PE1 â€” `Oper: down`, `Signalling: Down`, path-option 10 status `[failed]`.
2. The dynamic primary path runs PE1â†’P1â†’PE2. Check P1's TE state: connect to P1, run `show mpls traffic-eng tunnels` â€” returns no output (expected on a transit P), but `show mpls interfaces` shows `Traffic Engineering: disabled` on every core interface.
3. Inspect P1's running config: `show running-config | include traffic-eng` â€” the global `mpls traffic-eng tunnels` command is missing. Without it, P1 silently drops every RSVP PATH message arriving from PE1.
4. Confirm RSVP is also affected: `show ip rsvp interface` on P1 returns no output. RSVP needs the global TE switch enabled before any per-interface RSVP state is active.
</details>

<details>
<summary>Click to view Fix</summary>

On P1:
```bash
mpls traffic-eng tunnels
```

The single global command activates TE on P1. All previously configured per-interface `mpls traffic-eng tunnels` and `ip rsvp bandwidth` directives become operational. RSVP PATH messages now traverse P1, RESV returns to PE1, and Tunnel10 re-signals within seconds.

Verify: `show ip rsvp interface` on P1 lists all three core interfaces with 100,000 kbps. `show mpls traffic-eng tunnels tunnel10` on PE1 shows `Oper: up`. `show ip route 10.0.0.4` exits via Tunnel10 again.
</details>

---

### Ticket 2 â€” BGP Session Up but No Labels Exchanged

CE1 cannot reach 198.51.100.1 (CE2's customer prefix) sourced from 192.0.2.1. The iBGP session between PE1 and PE2 is `Established`. On PE1, `show ip bgp 198.51.100.0/24` shows the prefix learned from PE2. On PE2, `show ip bgp 192.0.2.0/24` shows the prefix learned from PE1. From PE1, `ping 10.0.0.4` (PE2's loopback) succeeds, but `traceroute 198.51.100.1` from PE1 fails after the first hop.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp labels` on PE1 lists 10.0.0.4/32 with a non-`nolabel` In/Out label entry. `ping 198.51.100.1 source 192.0.2.1` from CE1 succeeds 5/5.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Verify BGP session state: `show ip bgp summary` on PE1 â€” neighbor 10.0.0.4 `Established`, normal prefix counts. The session is healthy.
2. Inspect BGP-LU label exchange: `show ip bgp labels` on PE1 â€” entry for 10.0.0.4/32 shows `In label: nolabel` and `Out label: nolabel`. No labels are being exchanged despite the session being up.
3. Check capability negotiation: `show ip bgp neighbor 10.0.0.4 | include capability` â€” the IPv4-Unicast Add-Path / Send-Labels capability is missing on the receiving side.
4. Connect to PE2 and check the BGP config: `show running-config | section bgp` â€” the `neighbor 10.0.0.1 send-label` line is missing under address-family ipv4. Capability mismatch: PE1 advertises send-label, PE2 does not, so BGP-LU never activates.
5. Customer traffic path consequence: PE2 receives 192.0.2.0/24 from PE1 via iBGP with next-hop 10.0.0.1 (PE1's loopback, set by `next-hop-self`). PE2 has no BGP-LU label for 10.0.0.1, so the LDP fallback is used â€” which works for the reverse path. But the forward path from PE1 to PE2 uses the BGP-LU label that PE2 should have advertised. Without it, PE1 silently drops the traffic on the BGP route lookup.
</details>

<details>
<summary>Click to view Fix</summary>

On PE2:
```bash
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 send-label
 exit-address-family
```

Adding `send-label` triggers a soft BGP refresh; PE2 now advertises 10.0.0.4/32 with a label and the capability negotiation re-runs. Within seconds, `show ip bgp labels` on PE1 shows the label populated.

Verify: `show ip bgp labels` on PE1 lists 10.0.0.4/32 with `In label: nolabel  Out label: 24` (or similar). `ping 198.51.100.1 source 192.0.2.1` from CE1 returns 5/5 success.
</details>

---

### Ticket 3 â€” Tunnel10 Up but Secondary Path Never Signals

Pre-maintenance review: the NOC wants to confirm Tunnel10 has a viable secondary path before the planned shut on link L2 (PE1â†”P1). `show mpls traffic-eng tunnels tunnel10` shows `Oper: up` with the dynamic primary signaled, but path-option 20 (PE1-via-P2) shows `[failed]` in the standby status. The team is concerned the tunnel will tear down completely when L2 is shut, with no failover.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel10` on PE1 shows path-option 20 (PE1-via-P2) in a signalable state â€” both path-options report `valid`/computed without `[failed]`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel10` on PE1 â€” primary path-option 10 (dynamic) is up; path-option 20 (explicit PE1-via-P2) shows `[failed]`. The standby never signaled.
2. The explicit secondary forces transit via P2 (10.0.0.3). The shortest path from PE1 to P2 then to PE2 is PE1â†’P2â†’PE2 (using L3 then L6). Check the TE topology for L3 and L6 bandwidth: `show mpls traffic-eng topology` on PE1.
3. Look at the L3 link entry (between PE1 10.10.13.1 and P2 10.10.13.3): the BW[0] entry shows an unusually low value (â‰ˆ10 kbps) instead of 100,000 kbps. Tunnel10 requests 10,000 kbps, so CSPF prunes L3 from any path computation.
4. Confirm with the source: `show ip rsvp interface` on PE1 â€” Gi0/2 (toward P2) shows `i/f max` â‰ˆ 10 kbps. Someone misconfigured the RSVP bandwidth on this interface.
5. The dynamic primary path (PE1â†’P1â†’PE2) doesn't transit L3, so it isn't affected. But the explicit secondary requires routing through P2 from PE1, which means using L3. Misconfigured RSVP on a single link silently breaks the standby path.
</details>

<details>
<summary>Click to view Fix</summary>

On PE1:
```bash
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000
```

IS-IS TE LSAs propagate the corrected bandwidth within seconds. Tunnel10's CSPF re-runs for path-option 20.

Verify: `show ip rsvp interface` on PE1 shows Gi0/2 at 100,000 kbps. `show mpls traffic-eng topology` on PE1 shows L3 with full bandwidth available. `show mpls traffic-eng tunnels tunnel10` on PE1 shows path-option 20 in a signalable (or signaled) state, ready for failover.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS L2 process configured on PE1, P1, P2, PE2 with correct NET addresses
- [ ] All core links have full IS-IS adjacency (`show clns neighbors` Up on every core link)
- [ ] All four core loopbacks reachable via IS-IS from any core router
- [ ] MPLS LDP enabled globally on PE1, P1, P2, PE2 with router-id from Loopback0
- [ ] `mpls ip` and `mpls mtu override 1508` configured on every core-facing interface
- [ ] LDP neighbors `Oper: Up` on every directly connected core link
- [ ] `show mpls forwarding-table 10.0.0.4` on PE1 shows an outgoing label for PE2
- [ ] iBGP PE1â†”PE2 session `Established` with `send-label` and `next-hop-self`
- [ ] `show ip bgp labels` on PE1 shows a label for 10.0.0.4/32
- [ ] eBGP PE1â†”CE1 and PE2â†”CE2 sessions `Established`
- [ ] CE1's 192.0.2.0/24 visible on PE2; CE2's 198.51.100.0/24 visible on PE1
- [ ] `show ip bgp summary` on P1 and P2 returns `% BGP not active` (BGP-free invariant)
- [ ] `mpls traffic-eng tunnels` configured globally and per-interface on every core router
- [ ] `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` under IS-IS on every core router
- [ ] `ip rsvp bandwidth 100000 100000` on every core-facing interface
- [ ] `show mpls traffic-eng topology` lists all four core nodes with bandwidth attributes
- [ ] Tunnel10 on PE1 with path-option 10 dynamic + path-option 20 explicit (PE1-via-P2)
- [ ] `show mpls traffic-eng tunnels tunnel10` reports `Oper: up`, primary path active
- [ ] `show ip route 10.0.0.4` on PE1 exits via Tunnel10 (autoroute installed)
- [ ] `traceroute 10.0.0.4` from PE1 shows Tunnel10 as first-hop interface
- [ ] CE1 â†’ CE2 ping (`ping 198.51.100.1 source 192.0.2.1`) returns 5/5 success

### Troubleshooting

- [ ] Ticket 1 resolved: Tunnel10 restored after `mpls traffic-eng tunnels` re-added globally on the affected P router
- [ ] Ticket 2 resolved: BGP-LU labels exchanging again after `send-label` re-added on the affected PE
- [ ] Ticket 3 resolved: Tunnel10 secondary path signals after RSVP bandwidth restored on the affected core link

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
commands referenced in sections 4-9 do not exist on XR â€” use the equivalents
below when working on PE1 or PE2. P1, P2, CE1, and CE2 are still IOSv; their
commands are unchanged.

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
tunnel-te10 in `up/up` state) match the IOS-side checklist in section 6 â€”
only the syntax differs.

### Known gaps

- This appendix gives commands, not full per-task XR rewrites. The verification
  tasks in section 6 still describe the IOS workflow; running them on PE1/PE2
  requires translating each `show` per the table above.
- XRv (light) does not support every advanced TE feature (no Flex-Algo, no
  P2MP TE, no PCEP). For features beyond what is exercised here see the
  `xr-bridge` topic (build deferred â€” `memory/xr-coverage-policy.md` Â§2).
- Configs are syntactically translated from the IOS sibling solution but
  have **not yet been verified in EVE-NG**. Expect minor adjustments after
  first boot â€” report any failures so the configs can be corrected.
