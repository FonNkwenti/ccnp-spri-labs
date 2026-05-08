# Lab 04 â€” MPLS Full Mastery â€” Capstone I

**Topic:** MPLS Â· **Difficulty:** Advanced Â· **Time:** 120 minutes
**Blueprint refs:** 4.1, 4.1.a, 4.1.b, 4.1.c, 4.1.d, 4.1.e Â· **Type:** capstone_i (clean-slate)
**Devices:** PE1, P1, P2, PE2, CE1, CE2

---

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

**Exam Objective:** 4.1 Troubleshoot MPLS â€” all sub-bullets (4.1.a LDP, 4.1.b LSP, 4.1.c Unified BGP, 4.1.d BGP-free core, 4.1.e RSVP-TE tunnels)

This capstone challenges you to build a complete service-provider MPLS stack from a bare-IP starting point. You will configure IS-IS L2 as the IGP underlay, enable MPLS LDP for label distribution, establish iBGP with BGP Labeled-Unicast between PE routers while keeping the core routers BGP-free, wire up eBGP to customer edges, and signal an RSVP-TE tunnel with both dynamic and explicit path options. Every blueprint bullet for the MPLS chapter is exercised in a single end-to-end configuration.

### IS-IS as the MPLS IGP Underlay

Every MPLS label-switched path (LSP) depends on the IGP for reachability. IS-IS Level-2 running on all core routers provides the loopback-to-loopback routes that LDP binds labels to. The IS-IS NET (Network Entity Title) uses area 49.0001 â€” a private OSI address â€” and all routers sit in a single Level-2 area so every loopback appears as a /32 host route without summarization.

Key IS-IS configuration elements:
- `router isis CORE` â€” named process for SP context
- `net 49.0001.0000.0000.000X.00` â€” unique NET per router (X = device number)
- `is-type level-2-only` â€” suppresses Level-1 adjacency overhead
- `metric-style wide` â€” required for TE extensions (narrow metric tops at 63)
- `passive-interface Loopback0` â€” advertises loopback without sending hellos
- Per core interface: `ip router isis CORE` + `isis network point-to-point` (no DR election on /24 links)

The IS-IS adjacency must come up on every core link (L2â€“L6) before any label distribution can begin.

### MPLS LDP: Label Distribution Protocol

LDP discovers neighbors via UDP hello multicast (224.0.0.2) on each MPLS-enabled interface, then establishes a TCP/646 session to exchange label bindings. Each LSR advertises one label per IGP prefix â€” the Label Information Base (LIB) collects all advertised labels; the Label Forwarding Information Base (LFIB) selects exactly one outgoing label per prefix based on the IGP next-hop.

Critical design decisions:
- **LDP router-id must be reachable and stable.** Set `mpls ldp router-id Loopback0 force` so the router-ID matches the loopback address and the TCP session can always come up.
- **PHP (Penultimate Hop Popping).** The egress PE advertises `implicit-null` (label 3) for its own loopback. The upstream LSR pops the label before forwarding, so the PE performs a single IP lookup instead of a label lookup + IP lookup.
- **Label scope is per-platform, not per-interface.** A label binding is valid across all MPLS-enabled interfaces â€” the LFIB maps (incoming label, outgoing interface, outgoing label).

```
Global:                     Per core interface:
mpls label protocol ldp     mpls ip
mpls ldp router-id Lo0      mpls mtu override 1508
```

### BGP-Free Core Architecture

In a service-provider core, P routers never learn customer prefixes. Forwarding relies entirely on labels: PE1 pushes the LDP label for PE2's loopback onto every customer packet before sending it into the core. P1 and P2 swap the label and forward â€” they never inspect the inner IP header.

To make this work, iBGP runs only between PE1 and PE2 (loopback-sourced). The critical command is `neighbor <peer> next-hop-self` â€” without it, PE2 inherits CE1's interface address as the BGP next-hop, which is unreachable through the core. With `next-hop-self`, PE2 sees PE1's loopback (10.0.0.1) as the next-hop, which IS-IS+LDP can reach.

P1 and P2 must have **zero BGP configuration.** The lab acceptance test runs `show ip bgp summary` on both P routers and expects `% BGP not active`.

### Unified BGP (BGP Labeled-Unicast)

BGP-LU (`neighbor <peer> send-label`) advertises a label alongside each IPv4 prefix over the iBGP session. This is the mechanism that enables inter-AS MPLS (Option C / seamless MPLS) â€” an ASBR in a remote AS can learn the PE loopback label without running LDP across AS boundaries.

In a same-AS setup, the LDP-advertised label and the BGP-LU-advertised label for the same loopback will differ. The router uses the IGP-next-hop-based LFIB entry for forwarding; BGP-LU labels become relevant only when LDP is absent (inter-AS case). Verifying both label sources exists teaches the student which control plane takes precedence.

### RSVP-TE: Traffic Engineering Tunnels

RSVP-TE enables explicit path selection with bandwidth reservation. Four components must be active:

| Component | Where | Command |
|-----------|-------|---------|
| TE topology flooding | IS-IS process | `mpls traffic-eng level-2` + `mpls traffic-eng router-id Loopback0` |
| TE enabled on links | Per core interface | `mpls traffic-eng tunnels` |
| RSVP signaling | Per core interface | `ip rsvp bandwidth <total> <max-flow>` |
| Tunnel definition | Headend only | `interface Tunnel10` with TE mode, destination, path-options |

The tunnel headend (PE1) runs CSPF (Constrained Shortest Path First) on the TE topology database, selects a path, and signals it with RSVP PATH/RESV messages. Adding `autoroute announce` causes IS-IS to install the tunnel destination's route through the tunnel interface rather than the physical next-hop.

**Dynamic vs. explicit paths:** A dynamic path-option lets CSPF compute the best path based on the TE database. An explicit path-option forces transit through specific hop addresses (loose or strict). Using both as primary (dynamic) and secondary (explicit) gives the student a ready fallback if the dynamic path fails.

`â˜… Insight â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€`
- IS-IS must converge fully before enabling LDP â€” LDP only binds labels to prefixes already in the RIB. If you enable both simultaneously, LDP sessions come up but bindings are empty until the IS-IS SPF completes.
- The `force` keyword in `mpls ldp router-id Loopback0 force` is critical: without it, IOS waits for the current router-ID to disappear naturally before switching. With `force`, the change takes effect immediately â€” which is what you want during initial bring-up.
- RSVP tunnels are unidirectional. PE1â†’PE2 traffic transits Tunnel10; return traffic from PE2â†’PE1 follows the normal LDP LSP. For symmetric TE, each PE needs its own tunnel to the other.
- P routers must have `mpls traffic-eng tunnels` globally and per-interface even though they have no tunnel definitions â€” RSVP PATH messages are processed hop-by-hop, and every transit LSR needs TE enabled to participate in signaling.
`â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€`

### Skills this lab develops:

| Skill | Description |
|-------|-------------|
| IS-IS underlay for MPLS | Configure Level-2-only IS-IS with TE extensions across a multi-hop core |
| LDP label distribution | Enable LDP, verify sessions, inspect LIB vs LFIB, understand PHP |
| BGP-free core | Wire iBGP only on PEs with next-hop-self; verify P routers carry no BGP |
| BGP Labeled-Unicast | Exchange labels over iBGP; compare LDP and BGP-LU label sources |
| RSVP-TE tunnel signaling | Enable TE flooding, RSVP reservations, build tunnels with dynamic + explicit paths |
| End-to-end integration | Build the complete SP stack from bare IP to customer traffic over a TE tunnel |

---

## 2. Topology & Scenario

**Scenario:** You are the lead network engineer at a regional service provider expanding into MPLS-based services. The core has been physically cabled â€” six routers (PE1, P1, P2, PE2, CE1, CE2) with IP addresses pre-assigned â€” but no protocols are running. Your task is to build the complete MPLS stack: IS-IS underlay, LDP label distribution, iBGP with BGP-LU between PEs, eBGP to customer edges, and an RSVP-TE tunnel with redundant path options. The core must remain BGP-free â€” only PE routers speak BGP. When complete, a customer packet sourced from CE1's network (192.0.2.0/24) must reach CE2's network (198.51.100.0/24) with every byte label-switched through the core.

```
                    AS 65100 (SP core, IS-IS L2 + MPLS LDP)

       10.0.0.1                                        10.0.0.4
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚     PE1      â”‚                               â”‚     PE2      â”‚
   â”‚  SP Edge     â”‚                               â”‚  SP Edge     â”‚
   â”‚  Lo0: .1     â”‚                               â”‚  Lo0: .4     â”‚
   â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”˜                               â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”˜
 Gi0/1â”‚       â”‚Gi0/2                            Gi0/1â”‚       â”‚Gi0/2
  .1  â”‚       â”‚ .1                               .4  â”‚       â”‚ .4
      â”‚  L2   â”‚    L3                                â”‚  L5   â”‚    L6
  .2  â”‚       â”‚ .2                               .2  â”‚       â”‚ .3
 Gi0/0â”‚       â”‚Gi0/0                            Gi0/2â”‚       â”‚Gi0/2
   â”Œâ”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”         10.10.23.0/24         â”Œâ”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”
   â”‚     P1      â”‚â”€â”€â”€ L4 (Gi0/1â†”Gi0/1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚     P2      â”‚
   â”‚  SP Core    â”‚      .2          .3           â”‚  SP Core    â”‚
   â”‚  Lo0: .2    â”‚                               â”‚  Lo0: .3    â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

          L1 â”‚                                          â”‚ L7
   10.10.111.0/24                              10.10.122.0/24
    .11       â”‚ .1                             .4        â”‚ .12
        Gi0/0 â”‚                                    Gi0/0 â”‚
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”                               â”Œâ”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚     CE1     â”‚                               â”‚     CE2         â”‚
   â”‚ AS 65101    â”‚                               â”‚ AS 65102        â”‚
   â”‚ Lo0: .11    â”‚                               â”‚ Lo0: .12        â”‚
   â”‚ Lo1: 192.0.2.1/24                           â”‚ Lo1: 198.51.100.1/24
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Key relationships:**
- The diamond core gives PE1 two link-disjoint paths to PE2 (via P1 or via P2).
- The P1â†”P2 cross (L4) provides a third path (PE1â†’P1â†’P2â†’PE2) for RSVP-TE explicit path demonstrations.
- P1 and P2 are BGP-free by design â€” no BGP configuration on either router.
- CE1 and CE2 boot with all six routers; customer prefixes (192.0.2.0/24, 198.51.100.0/24) are pre-assigned on Loopback1 of each CE.

---

## 3. Hardware & Environment Specifications

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge â€” RSVP-TE headend, iBGP to PE2, eBGP to CE1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | SP Core (BGP-free) â€” IS-IS L2 + LDP + RSVP transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | SP Edge â€” RSVP-TE tail, iBGP to PE1, eBGP to CE2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Customer Edge AS 65101 â€” announces 192.0.2.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer Edge AS 65102 â€” announces 198.51.100.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP source, LDP router-id, TE router-id |
| P1 | Loopback0 | 10.0.0.2/32 | Router ID, LDP router-id, TE router-id |
| P2 | Loopback0 | 10.0.0.3/32 | Router ID, LDP router-id, TE router-id |
| PE2 | Loopback0 | 10.0.0.4/32 | Router ID, iBGP source, LDP router-id, TE router-id, tunnel destination |
| CE1 | Loopback0 | 10.0.0.11/32 | Router ID, eBGP router-id |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix advertised to PE1 |
| CE2 | Loopback0 | 10.0.0.12/32 | Router ID, eBGP router-id |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix advertised to PE2 |

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| CE1 | 192.0.2.0/24 | eBGP network | Customer A aggregate, announced to PE1 |
| CE2 | 198.51.100.0/24 | eBGP network | Customer B aggregate, announced to PE2 |
| PE1 | 10.0.0.1/32 | iBGP network | PE1 loopback for BGP-LU |
| PE2 | 10.0.0.4/32 | iBGP network | PE2 loopback for BGP-LU |

| Link | Endpoints | Subnet | Purpose |
|------|-----------|--------|---------|
| L1 | CE1 Gi0/0 â†” PE1 Gi0/0 | 10.10.111.0/24 | eBGP CE1â†”PE1 |
| L2 | PE1 Gi0/1 â†” P1 Gi0/0 | 10.10.12.0/24 | Core (IS-IS + LDP + RSVP) |
| L3 | PE1 Gi0/2 â†” P2 Gi0/0 | 10.10.13.0/24 | Core (IS-IS + LDP + RSVP) |
| L4 | P1 Gi0/1 â†” P2 Gi0/1 | 10.10.23.0/24 | P-cross (IS-IS + LDP + RSVP) |
| L5 | P1 Gi0/2 â†” PE2 Gi0/1 | 10.10.24.0/24 | Core (IS-IS + LDP + RSVP) |
| L6 | P2 Gi0/2 â†” PE2 Gi0/2 | 10.10.34.0/24 | Core (IS-IS + LDP + RSVP) |
| L7 | PE2 Gi0/0 â†” CE2 Gi0/0 | 10.10.122.0/24 | eBGP PE2â†”CE2 |

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
- Hostnames (PE1, P1, P2, PE2, CE1, CE2)
- `no ip domain-lookup` on all devices
- Loopback0 IP addressing on all six routers with `/32` mask
- Loopback1 on CE1 (192.0.2.1/24) and CE2 (198.51.100.1/24)
- All core-facing and CE-facing interface IP addressing with descriptions
- All interfaces in `no shutdown` state

**IS NOT pre-loaded** (student configures this):
- IS-IS routing process on PE1, P1, P2, PE2
- MPLS LDP global and per-interface configuration
- iBGP session between PE1 and PE2 with BGP Labeled-Unicast
- eBGP sessions PE1â†”CE1 and PE2â†”CE2
- MPLS Traffic Engineering (global, per-interface, IS-IS TE extensions)
- RSVP signaling and bandwidth reservations on all core links
- RSVP-TE tunnel on PE1 with dynamic and explicit path-options
- No BGP process of any kind on P1 or P2

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete MPLS solution from scratch â€” IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Task 1 â€” Deploy IS-IS Level-2 as the Core IGP

- Configure the IS-IS process named CORE on PE1, P1, P2, and PE2.
- Use NET 49.0001.0000.0000.000X.00 where X is the device number (PE1=1, P1=2, P2=3, PE2=4).
- Set the IS-IS process to Level-2-only with wide metrics.
- Advertise Loopback0 as a passive interface.
- Enable IS-IS on every core-facing interface (L2, L3, L4, L5, L6) and set the network type to point-to-point.
- Do NOT enable IS-IS on CE-facing interfaces (L1 on PE1 Gi0/0, L7 on PE2 Gi0/0).

**Verification:** `show clns neighbors` must show an adjacency on every core link. `show ip route isis` must contain all four loopbacks (/32).

---

### Task 2 â€” Enable MPLS LDP Across the Core

- Set the global label protocol to LDP and force the LDP router-ID to Loopback0 on PE1, P1, P2, and PE2.
- Enable `mpls ip` on every core-facing interface (L2, L3, L4, L5, L6).
- Set `mpls mtu override 1508` on all core interfaces to accommodate a two-label stack.
- Do NOT enable MPLS on Loopback interfaces or CE-facing interfaces.

**Verification:** `show mpls ldp neighbor` must show an operational session for every directly connected core pair. `show mpls ldp bindings` must contain local and remote bindings for every PE and P loopback (/32). `show mpls forwarding-table` must show one outgoing label per remote loopback.

---

### Task 3 â€” Configure iBGP with BGP Labeled-Unicast Between PEs

- Create the BGP process in AS 65100 on PE1 and PE2 with router-ID from Loopback0.
- Establish an iBGP session between PE1 and PE2 sourced from Loopback0.
- Under the IPv4 address-family, activate both neighbors and configure `next-hop-self` so each PE rewrites the BGP next-hop to its own loopback.
- Add `send-label` on both sides so the PEs exchange labels alongside prefixes via BGP-LU.
- Advertise each PE's own loopback (/32) into BGP with a network statement.
- Do NOT configure BGP on P1 or P2 â€” the core must remain BGP-free.

**Verification:** `show ip bgp summary` on PE1 and PE2 must show the iBGP session in Established state. `show ip bgp labels` must list PE loopbacks with a label. `show ip bgp summary` on P1 and P2 must return `% BGP not active`.

---

### Task 4 â€” Configure eBGP to Customer Edges

- On CE1 (AS 65101), configure eBGP to PE1 (AS 65100) and advertise 192.0.2.0/24 via a network statement.
- On CE2 (AS 65102), configure eBGP to PE2 (AS 65100) and advertise 198.51.100.0/24 via a network statement.
- On PE1, configure the eBGP session to CE1 and activate it in the IPv4 address-family.
- On PE2, configure the eBGP session to CE2 and activate it in the IPv4 address-family.

**Verification:** `show ip bgp` on PE1 must show 192.0.2.0/24 as an eBGP learned route. `show ip bgp` on PE2 must show 198.51.100.0/24 as an eBGP learned route. `show ip bgp` on PE2 must also show 192.0.2.0/24 learned via iBGP from PE1 with next-hop 10.0.0.1, and vice versa on PE1 for 198.51.100.0/24.

---

### Task 5 â€” Enable MPLS Traffic Engineering with RSVP

- Enable MPLS traffic engineering globally (`mpls traffic-eng tunnels`) on PE1, P1, P2, and PE2.
- Enable TE on every core-facing interface (`mpls traffic-eng tunnels` under each interface on L2, L3, L4, L5, L6).
- Under the IS-IS process on each core router, enable TE extensions with `mpls traffic-eng level-2` and set the TE router-ID to Loopback0.
- Configure RSVP on every core interface: `ip rsvp bandwidth 100000 100000` (100 Mbps total reservable, 100 Mbps per-flow maximum).

**Verification:** `show mpls traffic-eng topology` must list every TE-enabled router and link with bandwidth attributes. `show ip rsvp interface` must show RSVP enabled on every core interface.

---

### Task 6 â€” Build RSVP-TE Tunnel with Redundant Path Options

- On PE1, create two explicit paths:
  - `PE1-via-P1`: loose next-address 10.0.0.2 (P1 loopback) then loose next-address 10.0.0.4 (PE2 loopback).
  - `PE1-via-P2`: loose next-address 10.0.0.3 (P2 loopback) then loose next-address 10.0.0.4 (PE2 loopback).
- Create Tunnel10 on PE1:
  - Set tunnel mode to MPLS traffic engineering.
  - Set the tunnel destination to PE2's Loopback0 (10.0.0.4).
  - Use `ip unnumbered Loopback0` as the tunnel source.
  - Set bandwidth to 10000 kbps and priority to 1 1.
  - Configure path-option 10 as **dynamic** (primary).
  - Run `show mpls traffic-eng tunnels tunnel10` to see which P router the dynamic CSPF chose (P1 or P2).
  - Configure path-option 20 as **explicit** using the explicit path that transits the P router NOT chosen by the dynamic path. If dynamic chose P1, use `PE1-via-P2`. If dynamic chose P2, use `PE1-via-P1`.
  - Enable `autoroute announce` so IS-IS installs PE2's loopback route through Tunnel10.

**Verification:** `show mpls traffic-eng tunnels tunnel10` must show both path-options in the signaled state. `traceroute 10.0.0.4` from PE1 must show Tunnel10 as the output interface. `ping 198.51.100.1 source 192.0.2.1` from CE1 must succeed.

---

### Task 7 â€” End-to-End Acceptance Test

- From CE1, verify reachability to CE2's customer network: `ping 198.51.100.1 source 192.0.2.1` must succeed.
- From PE1, run `traceroute 10.0.0.4` and confirm the path goes through Tunnel10.
- On P1, verify no BGP process is active: `show ip bgp summary`.
- On P2, verify no BGP process is active: `show ip bgp summary`.
- On PE1, verify LDP neighbor sessions are operational on all core links.
- On PE1, verify the TE tunnel has both path-options signaled and available.

**Verification:** All checks pass without any protocol flaps or partial states.

---

## 6. Verification & Analysis

### Task 1 â€” IS-IS Adjacencies

```bash
PE1# show clns neighbors

System Id      Interface   SNPA                State  Holdtime  Type Protocol
P1             Gi0/1       aabb.cc00.0200      Up     25        L2   IS-IS  ! â† L2 adjacency on L2
P2             Gi0/2       aabb.cc00.0300      Up     25        L2   IS-IS  ! â† L2 adjacency on L3

PE1# show ip route isis
      10.0.0.2/32 is subnetted, 1 subnets
i L2    10.0.0.2 [115/20] via 10.10.12.2, 00:05:00, GigabitEthernet0/1  ! â† P1 loopback
      10.0.0.3/32 is subnetted, 1 subnets
i L2    10.0.0.3 [115/20] via 10.10.13.3, 00:05:00, GigabitEthernet0/2  ! â† P2 loopback
      10.0.0.4/32 is subnetted, 1 subnets
i L2    10.0.0.4 [115/30] via 10.10.12.2, 00:05:00, GigabitEthernet0/1  ! â† PE2 loopback via P1
                 [115/30] via 10.10.13.3, 00:05:00, GigabitEthernet0/2  ! â† ECMP via P2
```

### Task 2 â€” LDP Sessions and LFIB

```bash
PE1# show mpls ldp neighbor
    Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.2.646 - 10.0.0.1.12345
        State: Oper; Msgs sent/rcvd: 25/25; Downstream  ! â† P1 session UP
        Up time: 00:10:00
    Peer LDP Ident: 10.0.0.3:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.3.646 - 10.0.0.1.12346
        State: Oper; Msgs sent/rcvd: 25/25; Downstream  ! â† P2 session UP
        Up time: 00:10:00

PE1# show mpls forwarding-table
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
16     Pop Label  10.0.0.2/32      0             Gi0/1      10.10.12.2  ! â† PHP on P1 loopback
17     Pop Label  10.0.0.3/32      0             Gi0/2      10.10.13.3  ! â† PHP on P2 loopback
18     20         10.0.0.4/32      0             Gi0/1      10.10.12.2  ! â† PE2 via P1
       21         10.0.0.4/32      0             Gi0/2      10.10.13.3  ! â† PE2 via P2 (ECMP)
```

### Task 3 â€” iBGP and BGP-LU

```bash
PE1# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.4        4 65100      10      10        5    0    0 00:05:00        3  ! â† iBGP established
10.10.111.11    4 65101       8       8        5    0    0 00:04:00        1  ! â† eBGP CE1

PE1# show ip bgp labels
   Network          Next Hop      In label/Out label
   10.0.0.1/32      0.0.0.0         imp-null/18         ! â† local loopback
   10.0.0.4/32      10.0.0.4       22/imp-null          ! â† PE2 loopback with BGP-LU label

P1# show ip bgp summary
% BGP not active                                          ! â† BGP-free core invariant
```

### Task 4 â€” Customer Prefix Propagation

```bash
PE1# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.0.0.1/32      0.0.0.0                  0         32768 i
*>i10.0.0.4/32      10.0.0.4                 0    100      0 i
*> 192.0.2.0/24     10.10.111.11             0             0 65101 i  ! â† from CE1
*>i198.51.100.0/24  10.0.0.4                 0    100      0 65102 i  ! â† from PE2 (iBGP)

PE2# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24
  10.0.0.1 from 10.0.0.1 (10.0.0.1)                            ! â† next-hop is PE1 loopback
    Origin IGP, metric 0, localpref 100, valid, internal, best
```

### Task 5 â€” TE Topology and RSVP

```bash
PE1# show mpls traffic-eng topology
IGP Id: 10.0.0.1, MPLS-TE Id: 10.0.0.1
  Link[1]: Gi0/1, 10.10.12.1
    Nbr IGP Id: 10.0.0.2                            ! â† P1 visible in TE topology
    Bandwidth: max reservable 100000, allocated 0
IGP Id: 10.0.0.2, MPLS-TE Id: 10.0.0.2
  Link[1]: Gi0/0, 10.10.12.2
  Link[2]: Gi0/1, 10.10.23.2
  Link[3]: Gi0/2, 10.10.24.2
IGP Id: 10.0.0.3, MPLS-TE Id: 10.0.0.3              ! â† P2 visible in TE topology
  ...

PE1# show ip rsvp interface
Interface         Max BW  Max Flow  Allocated  Reserved
Gi0/1             100M    100M      0          0       ! â† RSVP enabled on L2
Gi0/2             100M    100M      0          0       ! â† RSVP enabled on L3
```

### Task 6 â€” RSVP-TE Tunnel

```bash
PE1# show mpls traffic-eng tunnels tunnel10

Name: PE1_t10                              (Tunnel10) Destination: 10.0.0.4
  Status:
    Admin: up         Oper: up     Path: valid       Signalling: connected  ! â† tunnel UP

    path option 10, type dynamic (Basis for Setup, path weight 20)  ! â† primary dynamic
    path option 20, type explicit PE1-via-P2 (Basis for Standby, path weight 30)  ! â† secondary explicit

  Config Parameters:
    Bandwidth: 10000   kbps (Global)  Priority: 1  1   Affinity: 0x0/0xFFFF
    AutoRoute: enabled   LockDown: disabled

PE1# traceroute 10.0.0.4
Type escape sequence to abort.
Tracing the route to 10.0.0.4
  1 10.10.12.2 [MPLS: Label 20 Exp 0] 4 msec 4 msec 4 msec  ! â† via Tunnel10
  2 10.10.24.4 4 msec *  4 msec                                  ! â† PE2 (PHP)

CE1# ping 198.51.100.1 source 192.0.2.1
Sending 5, 100-byte ICMP Echos to 198.51.100.1, timeout is 2 seconds:
Packet sent with a source address of 192.0.2.1
!!!!!                                                           ! â† end-to-end success
Success rate is 100 percent (5/5), round-trip min/avg/max = 4/5/8 ms
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
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

| Command | Purpose |
|---------|---------|
| `router isis CORE` | Named IS-IS process |
| `net 49.0001.0000.0000.000X.00` | Unique NET per router |
| `is-type level-2-only` | Suppress Level-1 adjacency |
| `metric-style wide` | Enable TE-compatible wide metrics |
| `ip router isis CORE` (interface) | Activate IS-IS on an interface |
| `isis network point-to-point` (interface) | Suppress DR/BDR election |

> **Exam tip:** IS-IS must converge before enabling LDP. If you configure both at once, LDP bindings appear empty until the SPF completes â€” this is a common troubleshooting scenario.

### MPLS LDP Configuration

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
```

| Command | Purpose |
|---------|---------|
| `mpls label protocol ldp` | Set label distribution to LDP (global) |
| `mpls ldp router-id Loopback0 force` | Stable LDP ID sourced from Loopback0 |
| `mpls ip` (interface) | Enable MPLS forwarding on interface |
| `mpls mtu override 1508` (interface) | Raise MTU for two-label stack (1500 + 8 bytes) |

### BGP-Free Core + BGP-LU Configuration

```
router bgp 65100
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 send-label
  neighbor 10.0.0.4 next-hop-self
  network 10.0.0.1 mask 255.255.255.255
```

| Command | Purpose |
|---------|---------|
| `neighbor <peer> remote-as 65100` | iBGP (same AS); eBGP (different AS) |
| `neighbor <peer> update-source Loopback0` | Source TCP from loopback for resilience |
| `neighbor <peer> send-label` | Enable BGP Labeled-Unicast |
| `neighbor <peer> next-hop-self` | Rewrite BGP next-hop to local loopback |
| `network <prefix> mask <mask>` | Inject prefix into BGP from RIB |

### RSVP-TE Configuration

```
mpls traffic-eng tunnels (global)
mpls traffic-eng tunnels (interface)
ip rsvp bandwidth 100000 100000 (interface)
```

| Command | Purpose |
|---------|---------|
| `mpls traffic-eng tunnels` (global) | Enable TE globally on router |
| `mpls traffic-eng tunnels` (interface) | Enable TE on a specific link |
| `mpls traffic-eng level-2` (router isis) | Flood TE LSAs in IS-IS L2 |
| `mpls traffic-eng router-id Loopback0` (router isis) | Stable TE router-ID |
| `ip rsvp bandwidth <total> <max-flow>` | Enable RSVP with bandwidth reservation |

### Tunnel Headend Configuration

```
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
| `tunnel mode mpls traffic-eng` | Set tunnel type to MPLS-TE |
| `tunnel destination <ip>` | Tail-end router loopback |
| `tunnel mpls traffic-eng autoroute announce` | Install tunnel in IGP routing table |
| `tunnel mpls traffic-eng path-option N dynamic` | Let CSPF compute path |
| `tunnel mpls traffic-eng path-option N explicit name <NAME>` | Force path through named hops |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | IS-IS adjacency on every core link, State = Up |
| `show ip route isis` | All PE/P loopbacks as i L2 /32 routes |
| `show mpls ldp neighbor` | Session State = Oper for every core peer pair |
| `show mpls ldp bindings` | Local + remote binding for every /32 loopback |
| `show mpls forwarding-table` | One outgoing label per remote loopback per ECMP path |
| `show ip bgp summary` | Established iBGP (PE1â†”PE2), eBGP to CEs; BGP not active on P1/P2 |
| `show ip bgp labels` | BGP-LU labels for PE loopbacks |
| `show ip bgp` | Customer prefixes (192.0.2.0/24, 198.51.100.0/24) with correct next-hops |
| `show mpls traffic-eng topology` | All routers and links visible with bandwidth attributes |
| `show ip rsvp interface` | RSVP enabled on every core interface |
| `show mpls traffic-eng tunnels tunnel10` | Tunnel Up, both path-options signaled |
| `ping 198.51.100.1 source 192.0.2.1` (CE1) | 100% success |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /24 | 0.0.0.255 | Interface subnet matching |
| /32 | 0.0.0.0 | Host route / loopback |

### Common MPLS Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| LDP neighbor stuck in INIT | LDP router-ID unreachable (wrong or missing loopback) |
| LDP session flaps every 30s | LDP router-ID sourced from non-existent interface |
| LFIB shows Untagged for a prefix | `no mpls ip` on the next-hop interface |
| BGP route inaccessible on remote PE | Missing `next-hop-self` â€” BGP next-hop is CE interface, not loopback |
| RSVP tunnel path option stuck in Signalling: Down | CSPF cannot find path â€” check RSVP bandwidth or TE flooding |
| Router missing from TE topology | Missing `mpls traffic-eng level-2` or `mpls traffic-eng router-id` under `router isis` |
| Tunnel Up but traffic not using it | Missing `tunnel mpls traffic-eng autoroute announce` |
| BGP-LU labels empty | Mismatched `send-label` â€” both sides must have it |
| BGP active on P router | Someone configured `router bgp 65100` on a core router â€” violates invariant |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 â€” IS-IS L2 Underlay

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
<summary>Click to view Verification Commands</summary>

```bash
show clns neighbors
show ip route isis
```
</details>

### Task 2 â€” MPLS LDP

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
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp neighbor
show mpls ldp bindings
show mpls forwarding-table
```
</details>

### Task 3 â€” iBGP with BGP-LU

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
show ip bgp
! On P1 and P2:
show ip bgp summary          ! must return "% BGP not active"
```
</details>

### Task 4 â€” eBGP to Customer Edges

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
<summary>Click to view PE1/PE2 eBGP Configuration</summary>

```bash
! PE1 (add to existing router bgp 65100)
 neighbor 10.10.111.11 remote-as 65101
 !
 address-family ipv4
  neighbor 10.10.111.11 activate

! PE2 (add to existing router bgp 65100)
 neighbor 10.10.122.12 remote-as 65102
 !
 address-family ipv4
  neighbor 10.10.122.12 activate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 192.0.2.0/24     ! on PE1
show ip bgp 198.51.100.0/24   ! on PE2
show ip bgp                   ! verify cross-propagation of customer prefixes
```
</details>

### Task 5 â€” MPLS Traffic Engineering + RSVP

<details>
<summary>Click to view All Core Router Configuration</summary>

```bash
! PE1, P1, P2, PE2 â€” add to global config:
mpls traffic-eng tunnels

! Under every core interface (Gi0/1, Gi0/2 on PEs; Gi0/0, Gi0/1, Gi0/2 on Ps):
 mpls traffic-eng tunnels
 ip rsvp bandwidth 100000 100000

! Under router isis CORE on PE1, P1, P2, PE2:
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng topology
show ip rsvp interface
```
</details>

### Task 6 â€” RSVP-TE Tunnel

<details>
<summary>Click to view PE1 Tunnel Configuration</summary>

```bash
! PE1 â€” add to global config
ip explicit-path name PE1-via-P1 enable
 next-address loose 10.0.0.2
 next-address loose 10.0.0.4
!
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
 ! Use PE1-via-P2 if dynamic chose P1, or PE1-via-P1 if dynamic chose P2
 tunnel mpls traffic-eng path-option 20 explicit name PE1-via-P2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng tunnels tunnel10
traceroute 10.0.0.4
ping 198.51.100.1 source 192.0.2.1     ! from CE1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 â€” LDP Session Between P1 and P2 Flaps Every 30 Seconds

The operations team reports that P1's LDP session to P2 cycles through INIT â†’ OPER â†’ NONEXISTENT every 30 seconds, and MPLS forwarding across the P1â†”P2 cross-link is unreliable. All other LDP sessions on P1 (to PE1 and PE2) are stable.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show mpls ldp neighbor` on P1 shows the session to P2 in Oper state with uptime increasing. `show mpls forwarding-table` on P1 has stable LFIB entries for 10.0.0.3 (P2) and 10.0.0.4 (PE2).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show mpls ldp neighbor` on P1 â€” note the session to P2 cycles through states every 30 seconds.
2. `show mpls ldp discovery` on P1 â€” hello discovery is active to P2; the problem is at the TCP session level.
3. Check the LDP router-ID: `show mpls ldp parameters` on P1. Look for `LDP Router ID` â€” if it points to a non-existent or unreachable address, the TCP/646 session to P2 will be sourced from the wrong IP and P2 cannot complete the three-way handshake.
4. Confirm the root cause: `show running-config | include mpls ldp router-id` reveals `mpls ldp router-id Loopback1` on P1, but Loopback1 does not exist.
</details>

<details>
<summary>Click to view Fix</summary>

Remove the incorrect router-ID and set it correctly:

```bash
P1# configure terminal
P1(config)# no mpls ldp router-id Loopback1 force
P1(config)# mpls ldp router-id Loopback0 force
P1(config)# end
```

Verify the session re-establishes: `show mpls ldp neighbor` â€” P2 session transitions to Oper and stays stable.
</details>

---

### Ticket 2 â€” PE1 Can Ping CE2's Network but CE1 Cannot

CE1 successfully pings PE1's interface (10.10.111.1), and PE1 can reach CE2's customer network (198.51.100.1) from its own loopback. However, a ping from CE1 sourced from 192.0.2.1 to 198.51.100.1 fails. Traceroute from CE1 shows the packet reaches PE1 but dies there.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `ping 198.51.100.1 source 192.0.2.1` from CE1 returns 100% success.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From CE1: `ping 198.51.100.1 source 192.0.2.1` â€” fails.
2. From CE1: `traceroute 198.51.100.1 source 192.0.2.1` â€” reaches PE1 but does not progress further.
3. On PE1: `show ip route 198.51.100.0` â€” check the BGP route for the customer prefix. Look at the BGP next-hop.
4. `show ip bgp 198.51.100.0/24` on PE1 â€” if the next-hop is 10.10.122.12 (CE2's interface) instead of 10.0.0.4 (PE2's loopback), the route is unreachable because PE1 has no IS-IS route to CE2's subnet.
5. The fault: PE2 is missing `next-hop-self` toward PE1. Without it, PE2 advertises CE2's interface address as the next-hop, which is not known in IS-IS.
</details>

<details>
<summary>Click to view Fix</summary>

On PE2, add `next-hop-self` for the iBGP neighbor:

```bash
PE2# configure terminal
PE2(config)# router bgp 65100
PE2(config-router)# address-family ipv4
PE2(config-router-af)# neighbor 10.0.0.1 next-hop-self
PE2(config-router-af)# end
PE2# clear ip bgp 10.0.0.1 soft out
```

Wait ~5 seconds for the re-advertisement. Verify: `show ip bgp 198.51.100.0/24` on PE1 now shows next-hop 10.0.0.4. CE1's ping to 198.51.100.1 now succeeds.
</details>

---

### Ticket 3 â€” RSVP-TE Tunnel Has Only One Path Option Signaled

Tunnel10 on PE1 is operational but only one path-option is in the "connected" state. The secondary path-option shows "Signalling: Down." Operations wants both path-options available for resilience. All RSVP interfaces appear configured correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show mpls traffic-eng tunnels tunnel10` shows both path-option 10 and path-option 20 in the signaled state (one connected/active, the other standby).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show mpls traffic-eng tunnels tunnel10` â€” note the secondary path-option shows "Signalling: Down."
2. `show mpls traffic-eng topology` on PE1 â€” look at the L4 link (P1â†”P2). Check the available bandwidth. If the link shows max reservable bandwidth of only 10 kbps, CSPF will reject it for a path that requests 10000 kbps.
3. The explicit path's route may depend on L4 (especially if it transits P1â†’P2â†’PE2). Check `show ip rsvp interface` on P1 or P2 for interface Gi0/1 (L4) â€” if the RSVP bandwidth is only 10 kbps, the tunnel cannot signal through that path.
</details>

<details>
<summary>Click to view Fix</summary>

On the router where L4 has insufficient RSVP bandwidth (P1 or P2), correct the reservation:

```bash
P1# configure terminal
P1(config)# interface GigabitEthernet0/1
P1(config-if)# ip rsvp bandwidth 100000 100000
P1(config-if)# end
```

Wait for RSVP to re-signal the secondary path. Verify: `show mpls traffic-eng tunnels tunnel10` â€” both path-options now show as signaled.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS L2 adjacency UP on all core links (L2â€“L6)
- [ ] All PE/P loopbacks reachable via IS-IS (`show ip route isis`)
- [ ] LDP neighbor sessions in Oper state on every core peer pair
- [ ] LFIB populated with outgoing labels for all remote loopbacks
- [ ] iBGP session PE1â†”PE2 Established
- [ ] BGP-LU labels exchanged (`show ip bgp labels` populated on both PEs)
- [ ] eBGP sessions PE1â†”CE1 and PE2â†”CE2 Established
- [ ] Customer prefixes cross-propagated: PE1 sees 198.51.100.0/24, PE2 sees 192.0.2.0/24
- [ ] BGP next-hop for remote customer prefixes is the remote PE loopback (not CE interface)
- [ ] MPLS-TE enabled globally and per-interface on all core routers
- [ ] IS-IS TE extensions configured on all core routers
- [ ] RSVP enabled with 100000/100000 on every core interface
- [ ] Tunnel10 on PE1: dynamic path-option signaled + explicit path-option signaled
- [ ] `autoroute announce` active â€” `traceroute 10.0.0.4` from PE1 shows Tunnel10
- [ ] CE1â†’CE2 ping (`ping 198.51.100.1 source 192.0.2.1`) succeeds
- [ ] P1 and P2 have no BGP configuration (`show ip bgp summary` returns `% BGP not active`)

### Troubleshooting

- [ ] Ticket 1 resolved: P1 LDP session to P2 stable, LFIB entries stable
- [ ] Ticket 2 resolved: CE1â†’CE2 ping succeeds end-to-end
- [ ] Ticket 3 resolved: Tunnel10 has both path-options in signaled state

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
