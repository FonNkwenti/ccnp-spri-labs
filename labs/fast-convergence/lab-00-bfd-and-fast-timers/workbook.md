# Lab 00 — BFD and Fast Timer Tuning

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

**Exam Objective:** 1.7, 1.7.a, 1.7.d — Implement Fast Convergence: BFD and Timers (Fast Convergence topic)

This lab builds the IS-IS and BGP foundation for the entire Fast Convergence topic chain, then progressively accelerates failure detection from the default 30-second IS-IS hold time down to sub-500 ms using BFD. You will measure each convergence improvement as you apply it — seeing exactly how much each knob buys you.

---

### IS-IS Hello and Hold Timers

IS-IS discovers neighbors and detects link failures via Hello PDUs. Each router sends a Hello every `hello-interval` seconds; if a neighbor goes `hello-multiplier × hello-interval` seconds without a Hello, the adjacency is declared down. The default is a 10-second hello and 30-second hold, meaning a link failure takes up to 30 seconds to detect.

Tuning these down is the fastest no-extra-software improvement available:

```
! Tune hellos per-interface (not globally — IS-IS timers are interface-scoped)
interface GigabitEthernet0/0
 isis hello-interval 1         ! send a hello every 1 second
 isis hello-multiplier 3       ! hold time = 1 × 3 = 3 seconds
```

A 3-second hold is a significant improvement over 30 seconds, but still sluggish for a modern SP core. This is where BFD comes in.

### Bidirectional Forwarding Detection (BFD)

BFD is a protocol-agnostic rapid failure detection mechanism defined in RFC 5880. It runs a separate lightweight session between directly-connected nodes, exchanging packets at sub-second intervals. When a BFD session detects a failure, it immediately notifies the registered protocol (IS-IS, BGP, OSPF, etc.) — the protocol then reacts without waiting for its own timer to expire.

BFD comes in two modes:

| Mode | When | Configuration |
|------|------|---------------|
| Single-hop | Directly connected neighbors | `bfd interval` on interface + protocol enable command |
| Multi-hop | Loopback-sourced sessions | `bfd-template multi-hop` + per-peer binding |

For IS-IS, single-hop BFD is the right fit — the IS-IS adjacency is always between directly-connected interfaces. For loopback-sourced BGP (iBGP or eBGP via loopback), multi-hop BFD detects control-plane failures without being confused by a fast-reroute that silently reroutes traffic around the downed link.

**BFD detection time formula:** `detection_time = min_rx × multiplier`

With `bfd interval 150 min_rx 150 multiplier 3`, both peers negotiate down to 150 ms tx/rx intervals. After 3 consecutive missed packets (3 × 150 ms = 450 ms), the session is declared down and IS-IS reacts immediately.

```
! Single-hop BFD on IS-IS interface
interface GigabitEthernet0/0
 bfd interval 150 min_rx 150 multiplier 3  ! 150 ms intervals, 450 ms detection
 isis bfd                                   ! register IS-IS as a BFD client
```

```
! Multi-hop BFD template for loopback-sourced eBGP
bfd-template multi-hop BFD_MULTIHOP
 interval min-tx 150 min-rx 150 multiplier 3
!
ip bfd peer 10.0.0.5 multihop src 10.0.0.1 template BFD_MULTIHOP
!
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

### IS-IS SPF and PRC Throttle

Even after BFD delivers instant failure notification, IS-IS still has to recompute the Shortest Path First (SPF) tree before it can install new routes. By default, IOS imposes no minimum delay between consecutive SPF computations, which can cause CPU thrashing if LSPs arrive in a burst.

The `spf-interval` command introduces an exponential backoff:

```
router isis
 spf-interval 5 50 200      ! max-wait=5s, initial-wait=50ms, second-wait=200ms
 prc-interval 5 50 200      ! same for Partial Route Computation (prefix-only changes)
```

On first trigger, SPF fires after 50 ms. If triggered again immediately, it waits 200 ms, then doubles up to 5 s maximum. This gives fast initial reaction while protecting the CPU from oscillating topologies.

### BGP Keepalive and Hold Timers

BGP detects neighbor failures via keepalives. The default is 60-second keepalive / 180-second hold, meaning a BGP session takes up to 3 minutes to detect a dead neighbor (or 3 minutes if keepalives simply stop arriving). For eBGP sessions to external CEs, this is far too slow.

Tuning the timers reduces detection, but BFD multi-hop is better for loopback-sourced sessions because it decouples detection from the BGP state machine:

```
! Tune per-neighbor (overrides global)
router bgp 65100
 neighbor 10.0.0.5 timers 5 15     ! keepalive=5s, hold=15s
```

With BFD multi-hop enabled (`fall-over bfd multi-hop`), BGP uses BFD's sub-second detection and ignores its own keepalive cycle — the timer tuning is belt-and-suspenders protection for the case where BFD itself is unavailable.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IS-IS L2 adjacency formation | Configure NET addresses, is-type, metric-style, passive-interface |
| iBGP full mesh | Loopback-sourced iBGP sessions with update-source, next-hop-self |
| Loopback-sourced eBGP | ebgp-multihop, static host routes, loopback peering |
| Convergence benchmarking | Controlled link failure + time measurement with ping |
| BFD single-hop on IS-IS | bfd interval + isis bfd on core interfaces |
| BFD multi-hop on BGP | bfd-template multi-hop, ip bfd peer, neighbor fall-over bfd multi-hop |
| IS-IS timer tuning | hello-interval, hello-multiplier, spf-interval, prc-interval |
| BGP timer tuning | neighbor timers keepalive hold |

---

## 2. Topology & Scenario

**Scenario:** You are a SP network engineer provisioning a new five-router core. The core uses IS-IS L2 as the sole IGP — consistent with SP practice — and a full-mesh iBGP to carry customer prefixes. An external CE (R5, AS 65200) is dual-homed to two SP edge nodes (R1 and R3) for resilience.

Your mandate: reduce IS-IS convergence from the default 30 seconds to under 500 ms, then demonstrate the improvement with live failure tests. Then protect the eBGP sessions to R5 with BFD multi-hop so that a control-plane failure is detected in milliseconds rather than minutes.

```
              AS 65100 (SP core — IS-IS L2 + iBGP full mesh)

         ┌──────────────────────┐              ┌──────────────────────┐
         │         R1           │── L1 ─────── │         R2           │
         │  SP Edge AS 65100    │  Gi0/0 Gi0/0 │  SP Core AS 65100    │
         │  Lo0: 10.0.0.1/32    │  10.1.12.0   │  Lo0: 10.0.0.2/32    │
         └──┬──────┬──────┬─────┘              └────────────┬─────────┘
        L4  │  L5  │  L6  │ Gi0/3                       L2  │ Gi0/1
      Gi0/1 │ Gi0/2│      │ 10.1.15.0                       │ 10.1.23.0
            │      │      │                                  │
   ┌────────┴──┐   │      │                      ┌───────────┴────────────┐
   │    R4     │   └──────┼──────────────────────►         R3             │
   │  SP Core  │          │            Gi0/2 L5  │  SP Edge AS 65100      │
   │ 10.0.0.4  │◄── L3 ──►│     Gi0/1 10.1.34.0  │  Lo0: 10.0.0.3/32     │
   │  /32      │ 10.1.34.0│              Gi0/0   │                        │
   └───────────┘          │              L3      └──┬───────────────────┬─┘
      Gi0/0 R4            │                     L7 │ Gi0/3         L5  │
                          │               10.1.35.0 │                   │ Gi0/2
                          │                         │                   │
                          │                 ┌───────┴───────────────────┘
                          │                 │
                          │        ┌────────┴──────────────────┐
                          └────────►         R5                │
                            L6 Gi0/0│   CE AS 65200            │
                         10.1.15.0  │  Lo0: 10.0.0.5/32       │
                                    │  Lo1: 192.0.2.1/24       │
                                    └───────────────────────────┘
```

**Link reference:**

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | SP core — IS-IS L2, iBGP transport |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | SP core — IS-IS L2, iBGP transport |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | SP core — IS-IS L2, iBGP transport |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | Ring closer — IS-IS L2, provides LFA alternate |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | Diagonal — IS-IS L2, short path R1↔R3 |
| L6 | R1 Gi0/3 | R5 Gi0/0 | 10.1.15.0/24 | eBGP R1 (AS 65100) ↔ R5 (AS 65200) |
| L7 | R3 Gi0/3 | R5 Gi0/1 | 10.1.35.0/24 | eBGP R3 (AS 65100) ↔ R5 (AS 65200) |

**Key relationships:**
- R1, R2, R3, R4 form a meshed core: R1↔R2 (L1), R2↔R3 (L2), R3↔R4 (L3), R1↔R4 (L4), R1↔R3 (L5). Every single-link failure has at least one alternate path — prerequisite for LFA in lab-02.
- R5 is dual-homed via L6 (to R1) and L7 (to R3). Both sessions are active from day 1; BGP PIC in lab-03 exploits this pre-existing dual path.
- eBGP uses loopback-to-loopback peering (ebgp-multihop 2 + static host routes), consistent with SP practice. BFD multi-hop monitors the loopback-sourced TCP session.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | SP Core — iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | SP Core — redundant path, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5 | External CE — dual-homed eBGP in AS 65200 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP peering source, BFD multi-hop source |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source, BFD multi-hop source |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, iBGP peering source |
| R5 | Loopback0 | 10.0.0.5/32 | Router ID, eBGP peering source, BFD multi-hop endpoint |
| R5 | Loopback1 | 192.0.2.1/24 | External prefix announced into AS 65100 via eBGP |

### Cabling

| Link ID | From | To | Subnet | Interface (From) | Interface (To) |
|---------|------|----|--------|-----------------|----------------|
| L1 | R1 | R2 | 10.1.12.0/24 | GigabitEthernet0/0 | GigabitEthernet0/0 |
| L2 | R2 | R3 | 10.1.23.0/24 | GigabitEthernet0/1 | GigabitEthernet0/0 |
| L3 | R3 | R4 | 10.1.34.0/24 | GigabitEthernet0/1 | GigabitEthernet0/0 |
| L4 | R1 | R4 | 10.1.14.0/24 | GigabitEthernet0/1 | GigabitEthernet0/1 |
| L5 | R1 | R3 | 10.1.13.0/24 | GigabitEthernet0/2 | GigabitEthernet0/2 |
| L6 | R1 | R5 | 10.1.15.0/24 | GigabitEthernet0/3 | GigabitEthernet0/0 |
| L7 | R3 | R5 | 10.1.35.0/24 | GigabitEthernet0/3 | GigabitEthernet0/1 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R5 | 192.0.2.0/24 | eBGP network statement | External CE prefix; announced to R1 and R3 via eBGP |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on all five routers
- Interface IP addressing on all routed links and both loopbacks (Loopback0 and Loopback1 on R5)
- `no ip domain-lookup` on all routers
- Interface descriptions matching the link IDs (L1 through L7)

**IS NOT pre-loaded** (student configures this):
- IS-IS Level-2 routing process and NET addressing on R1–R4
- IS-IS on each core interface (Loopback0 passive, data interfaces active)
- IS-IS hello and hold timer tuning
- BFD single-hop sessions on IS-IS interfaces
- IS-IS SPF and PRC throttle timers
- iBGP full mesh in AS 65100 (R1, R2, R3, R4), loopback-sourced
- eBGP sessions R1↔R5 and R3↔R5, loopback-sourced with multihop
- Static host routes enabling loopback-sourced eBGP
- BFD multi-hop sessions on eBGP links
- BGP keepalive and hold timer tuning on eBGP sessions

---

## 5. Lab Challenge: Core Implementation

### Task 1: Build the IS-IS L2 Underlay (R1–R4)

- On each of R1, R2, R3, and R4, create an IS-IS routing process using Level-2 Only mode.
- Assign each router a unique NET address in area 49.0001 using the router's loopback0 IP as the system-ID (e.g., R1 at 10.0.0.1 → system-ID `0000.0000.0001`).
- Enable wide-style metrics on all four routers.
- Enable IS-IS on every IS-IS core interface (L1 through L5 as applicable per router) and on Loopback0. Configure Loopback0 as passive on each router so it advertises the address without sending hellos.
- R5 does not run IS-IS — it is in a separate AS with no IGP requirement.

**Verification:** `show clns neighbors` on R1 must show three IS-IS L2 adjacencies (R2, R3, R4). `show ip route isis` on R1 must show all remote loopbacks (10.0.0.2/32, 10.0.0.3/32, 10.0.0.4/32).

---

### Task 2: Build iBGP Full Mesh and eBGP Dual-Homing

- On R1, R2, R3, and R4, establish a full-mesh iBGP within AS 65100. Source all iBGP sessions from Loopback0 (IS-IS carries the reachability).
- On R1, establish an eBGP session to R5 (AS 65200). Source the session from Loopback0. Because R5's Loopback0 (10.0.0.5) is not reachable via IS-IS, add a static host route on R1 toward R5's loopback via the L6 next-hop. Set multihop to 2 so the loopback-sourced TCP can complete.
- On R3, establish an equivalent eBGP session to R5 sourced from Loopback0, with a static host route via the L7 next-hop.
- On R5, configure matching eBGP neighbors toward R1 and R3 loopbacks with identical multihop and update-source settings. Add static host routes on R5 for R1's and R3's loopbacks.
- Have R5 originate its external prefix (192.0.2.0/24 — the Loopback1 network) into BGP using a network statement.
- Apply `next-hop-self` on each iBGP neighbor on R1 and R3 so the external prefix (192.0.2.0/24) learned from R5 is re-advertised inward with the local loopback as next-hop, making it resolvable via IS-IS. Do not apply `next-hop-self` on the eBGP neighbor (R5).

**Verification:** `show ip bgp summary` on R1 must show all three iBGP neighbors (R2, R3, R4) and one eBGP neighbor (R5) as Established. `show ip bgp 192.0.2.0/24` on R2 must show a path with a next-hop of R1's or R3's loopback (10.0.0.1 or 10.0.0.3).

---

### Task 3: Measure Default IS-IS Convergence

- From R2, start a sustained extended ping to R3's loopback (10.0.0.3) with a rapid interval (e.g., 100 ms). Note the time.
- Shut down interface L2 (R2's connection to R3 — GigabitEthernet0/1 on R2).
- Record how many seconds elapse from the interface shutdown to when the ping resumes (the routing path will switch to the alternate via R2→R1→R3 or R2→R1→R4→R3). The default hold time is 30 seconds, so expect ~27–30 seconds of packet loss.
- Restore L2 before proceeding.

**Verification:** `show isis neighbors` on R2 before the test must show L2 adjacencies with a Hold timer of approximately 29–30 seconds (default 10-second hello interval, multiplier 3 — hold time = 30 seconds). Record the observed convergence time in the table below and compare to the BFD result in Task 6.

| Test | Hold Timer | Observed Convergence |
|------|------------|----------------------|
| Default IS-IS (Task 3) | ~30 s | ___ s |
| Tuned hellos (Task 4) | ~3 s | ___ s |
| With BFD (Task 6) | 450 ms | ___ ms |

---

### Task 4: Tune IS-IS Hello and Hold Timers

- On every IS-IS data interface of R1, R2, R3, and R4 (not on Loopback0 — it is passive), configure a 1-second hello interval and a hello multiplier of 3. This gives a 3-second hold time.
- Do not change the IS-IS hello settings on Loopback0.
- Repeat the failure test from Task 3: shut L2, measure convergence time. Expect approximately 3 seconds.

**Verification:** `show isis neighbors detail` on R2 must show a Hold timer in the 2–3 s range on all active interfaces. After the link-shut test, confirm the ping resumes in approximately 3 seconds.

---

### Task 5: Enable BFD Single-Hop on IS-IS Core Interfaces

- On every IS-IS data interface of R1, R2, R3, and R4, enable BFD single-hop with a 150 ms transmit interval, 150 ms minimum receive interval, and a multiplier of 3. This gives a detection time of 450 ms.
- Register IS-IS as a BFD client on each of these interfaces.
- Verify that BFD sessions form between all directly-connected IS-IS neighbor pairs.

**Verification:** `show bfd neighbors` on R1 must show sessions with R2 (Gi0/0), R4 (Gi0/1), and R3 (Gi0/2) all in the Up state. The `St` column must read `Up` for all sessions. Confirm IS-IS adjacencies remain up — BFD addition is non-disruptive when configured symmetrically.

---

### Task 6: Measure IS-IS Convergence with BFD

- From R2, restart the sustained extended ping to R3's loopback (10.0.0.3).
- Shut down L2 on R2. Record the convergence time.
- With BFD active, IS-IS detects the failure via BFD notification (~450 ms) rather than the hello hold timer (~3 s). Expect sub-500 ms convergence.
- Restore L2 and record your result in the table from Task 3.

**Verification:** The ping should resume within 500 ms. `show isis event-log` on R1 (if supported) or `debug isis adj-packets` will show the BFD-triggered adjacency change. `show bfd neighbors` after restoration must show all sessions returning to Up.

---

### Task 7: Enable BFD Multi-Hop on eBGP Sessions

- On R1, create a BFD multi-hop template that specifies 150 ms transmit interval, 150 ms minimum receive interval, and a multiplier of 3. Name the template BFD_MULTIHOP.
- Bind the multi-hop template to the BFD session toward R5's loopback (10.0.0.5), specifying R1's loopback (10.0.0.1) as the source.
- Configure R1's eBGP neighbor (R5's loopback) to fall over using BFD multi-hop.
- Repeat the same configuration on R3 for its eBGP session to R5, binding to R5's loopback from R3's loopback (10.0.0.3).
- Configure matching multi-hop BFD on R5: create the same BFD_MULTIHOP template and bind sessions toward both R1's loopback (10.0.0.1 from 10.0.0.5) and R3's loopback (10.0.0.3 from 10.0.0.5). Enable fall-over BFD multi-hop on both eBGP neighbors.

**Verification:** `show bfd neighbors` on R1 must show a multi-hop BFD session to 10.0.0.5 in the Up state. `show ip bgp neighbors 10.0.0.5` on R1 must show `BFD: enabled, Multi-hop` (or equivalent) and `BGP state: Established`.

---

### Task 8: Tune SPF Throttle and BGP Timers

- On R1, R2, R3, and R4, configure IS-IS SPF throttle with a maximum wait of 5 seconds, initial wait of 50 ms, and second wait of 200 ms.
- Configure IS-IS PRC (Partial Route Computation) throttle with the same values.
- On R1 and R3, tune the BGP keepalive/hold timers on the eBGP session to R5 to 5 seconds keepalive and 15 seconds hold.
- Configure matching timers on R5 for both eBGP neighbors (R1 and R3).

**Verification:** `show isis spf-log` must show recent SPF events with timestamps consistent with the throttle delay (first run fires ~50 ms after a topology change). `show ip bgp neighbors 10.0.0.5` on R1 must show `Hold time: 15, Keepalive interval: 5` in the BGP timers section.

---

### Task 9: Troubleshoot Asymmetric BFD Timers (Guided)

> This task simulates a fault planted by the operations team. Use the inject script in Section 9 to introduce the fault, then diagnose and fix it.

- After injecting Ticket 1's fault, observe that the BFD session between R1 and R2 reports as Down despite both routers showing BFD configured on their shared interface.
- Examine the BFD session negotiated parameters on R1 and compare the BFD interval and multiplier configuration on R1 and R2. Note that one side uses a faster interval than the other, and a mismatched multiplier on one router causes the detection window to be too tight.
- Identify which router has the incorrect BFD timer configuration and correct it so both sides use a 150 ms transmit interval, 150 ms minimum receive interval, and a multiplier of 3 — matching the symmetric configuration applied in Task 5.

**Verification:** `show bfd neighbors` on R1 must show the R2 session (Gi0/0) as `Up` with negotiated timers consistent with the 150/150/3 configuration. `show bfd neighbors details` must confirm matching intervals and multiplier on both sides. `show isis neighbors` must show R2 in the Up/Up state.

---

## 6. Verification & Analysis

### Task 1 — IS-IS Adjacencies

```
R1# show clns neighbors

System Id      Interface   SNPA               State  Holdtime  Type Protocol
R2             Gi0/0       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R2 adjacency on L1
R4             Gi0/1       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R4 adjacency on L4
R3             Gi0/2       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R3 adjacency on L5

R1# show ip route isis | include 10.0.0
i L2  10.0.0.2/32 [115/20] via 10.1.12.2, 00:01:30, GigabitEthernet0/0   ! ← R2 loopback
i L2  10.0.0.3/32 [115/20] via 10.1.13.3, 00:01:30, GigabitEthernet0/2   ! ← R3 loopback via L5
i L2  10.0.0.4/32 [115/20] via 10.1.14.4, 00:01:30, GigabitEthernet0/1   ! ← R4 loopback via L4
```

### Task 2 — BGP Sessions

```
R1# show ip bgp summary
Neighbor    V    AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down  State/PfxRcd
10.0.0.2    4 65100      15      15      5   0    0 00:05:10          0   ! ← iBGP R2 Established
10.0.0.3    4 65100      15      15      5   0    0 00:05:10          0   ! ← iBGP R3 Established
10.0.0.4    4 65100      15      15      5   0    0 00:05:10          0   ! ← iBGP R4 Established
10.0.0.5    4 65200      12      12      5   0    0 00:04:30          1   ! ← eBGP R5, 1 prefix received

R1# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 5
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     2
  Refresh Epoch 1
  65200
    10.0.0.5 from 10.0.0.5 (10.0.0.5)          ! ← next-hop is R5 loopback
      Origin IGP, localpref 100, valid, external, best
```

```
R2# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 5
Paths: (1 available, best #1, table default)
  65200
    10.0.0.1 from 10.0.0.1 (10.0.0.1)          ! ← next-hop is R1 loopback (next-hop-self)
      Origin IGP, localpref 100, valid, internal, best
```

### Task 3 — Default Convergence Measurement

```
R2# show isis neighbors
System Id      Interface   SNPA               State  Holdtime  Type Protocol
R1             Gi0/0       xxxx.xxxx.xxxx     Up     29        L2   M-ISIS  ! ← Hold=29s (default)
R3             Gi0/1       xxxx.xxxx.xxxx     Up     29        L2   M-ISIS
```

After shutting Gi0/1 on R2, observe ~30 seconds of ping loss before the alternate path via R2→R1→R3 (L1+L5) or R2→R1→R4→R3 (L1+L4+L3) is installed.

### Task 4 — Tuned Timers

```
R2# show isis neighbors
System Id      Interface   SNPA               State  Holdtime  Type Protocol
R1             Gi0/0       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← Hold=2s (1s × 3)
R3             Gi0/1       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← Hold=2s
```

### Task 5 — BFD Single-Hop Sessions

```
R1# show bfd neighbors
NeighAddr     LD/RD    RH/RS  State  Int
10.1.12.2     4097/4097  Up    Up    Gi0/0   ! ← BFD to R2 via L1
10.1.14.4     4098/4098  Up    Up    Gi0/1   ! ← BFD to R4 via L4
10.1.13.3     4099/4099  Up    Up    Gi0/2   ! ← BFD to R3 via L5

R1# show bfd neighbors details | include Registered
Registered Protocols: ISIS                       ! ← IS-IS is registered as BFD client
```

### Task 7 — BFD Multi-Hop Sessions

```
R1# show bfd neighbors
NeighAddr     LD/RD    RH/RS  State  Int
10.1.12.2     4097/4097  Up    Up    Gi0/0
10.1.14.4     4098/4098  Up    Up    Gi0/1
10.1.13.3     4099/4099  Up    Up    Gi0/2
10.0.0.5      4100/4100  Up    Up    *System*   ! ← Multi-hop BFD to R5 loopback

R1# show ip bgp neighbors 10.0.0.5 | include BFD|state
BGP state = Established, up for 00:04:00        ! ← session is up
BFD: enabled, Multi-hop                          ! ← multi-hop BFD registered
```

### Task 8 — SPF Throttle and BGP Timers

```
R1# show isis spf-log
 Level   When     Duration   Nodes   Count  Last triggered by
 L2      00:00:15 0 ms       5       1      new adjacency       ! ← 50 ms initial throttle

R1# show ip bgp neighbors 10.0.0.5 | include Hold|Keepalive
Hold time: 15, Keepalive interval: 5 seconds   ! ← tuned from default 180/60
```

---

## 7. Verification Cheatsheet

### IS-IS Process and Adjacency

```
router isis
 net <area>.<sysid>.00          ! NET format: 49.0001.xxxx.xxxx.xxxx.00
 is-type level-2-only           ! SP core uses L2 only
 metric-style wide              ! required for TE metrics > 63
 passive-interface Loopback0    ! advertise but don't send hellos
!
interface GigabitEthernet0/0
 ip router isis                 ! enable IS-IS on interface
```

| Command | Purpose |
|---------|---------|
| `show clns neighbors` | IS-IS adjacency table with hold times |
| `show ip route isis` | IS-IS routes in the RIB |
| `show isis neighbors detail` | Detailed adjacency including timers |
| `show isis database` | Link State Database |

> **Exam tip:** IS-IS hellos are sent per-interface, not globally. `hello-interval` and `hello-multiplier` must be configured on each interface individually. The hold time received by a neighbor is `local_hello_interval × local_multiplier`.

### IS-IS Hello Timer Tuning

```
interface GigabitEthernet0/0
 isis hello-interval 1          ! send hello every 1 second
 isis hello-multiplier 3        ! hold = 1 × 3 = 3 seconds
```

| Command | Purpose |
|---------|---------|
| `show isis neighbors` | Current hold timers on each adjacency |
| `debug isis adj-packets` | Watch hello exchanges in real time |

> **Exam tip:** The hold time advertised to a neighbor is computed locally: `hello-interval × hello-multiplier`. Both sides can use different intervals — IS-IS accepts the neighbors' advertised hold time, not the local one. Asymmetry is allowed but unusual.

### IS-IS SPF and PRC Throttle

```
router isis
 spf-interval 5 50 200         ! max-wait=5s, initial-wait=50ms, second-wait=200ms
 prc-interval 5 50 200         ! same for prefix-only changes
```

| Command | Purpose |
|---------|---------|
| `show isis spf-log` | SPF run history with duration and trigger |
| `show isis timers` | Current throttle configuration |

### BFD Single-Hop (IS-IS)

```
interface GigabitEthernet0/0
 bfd interval 150 min_rx 150 multiplier 3   ! 150 ms intervals, 450 ms detection
 isis bfd                                    ! register IS-IS as BFD client
```

| Command | Purpose |
|---------|---------|
| `show bfd neighbors` | All BFD sessions with state |
| `show bfd neighbors details` | Timers, registered protocols, counters |
| `show bfd summary` | Session counts by state |

> **Exam tip:** BFD sessions are negotiated to the slower of the two sides. If R1 sends `min_rx 150` and R2 sends `interval 50`, the negotiated TX rate is 150 ms (R1's minimum receive). Asymmetric configs cause unexpected detection times — always configure both sides symmetrically.

### BFD Multi-Hop (eBGP)

```
! Step 1: define the multi-hop template
bfd-template multi-hop BFD_MULTIHOP
 interval min-tx 150 min-rx 150 multiplier 3
!
! Step 2: bind to the peer (destination + source loopbacks)
ip bfd peer 10.0.0.5 multihop src 10.0.0.1 template BFD_MULTIHOP
!
! Step 3: enable in BGP
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

| Command | Purpose |
|---------|---------|
| `show bfd neighbors` | Multi-hop sessions appear with interface `*System*` |
| `show ip bgp neighbors X.X.X.X | include BFD` | Confirm BFD registration for a BGP peer |

### BGP Session Configuration

```
router bgp 65100
 neighbor 10.0.0.2 remote-as 65100         ! iBGP: same AS
 neighbor 10.0.0.2 update-source Loopback0 ! source from loopback
 neighbor 10.0.0.5 remote-as 65200         ! eBGP: different AS
 neighbor 10.0.0.5 ebgp-multihop 2         ! required for loopback-sourced eBGP
 neighbor 10.0.0.5 timers 5 15             ! keepalive=5s, hold=15s
 neighbor 10.0.0.5 fall-over bfd multi-hop ! use BFD for failure detection
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self          ! rewrite next-hop on iBGP peers, not eBGP peer
  neighbor 10.0.0.5 activate
```

| Command | Purpose |
|---------|---------|
| `show ip bgp summary` | All BGP neighbors and state |
| `show ip bgp neighbors X` | Detailed session info including BFD and timers |
| `show ip bgp 192.0.2.0/24` | Path detail for a specific prefix |

> **Exam tip:** Loopback-sourced eBGP requires three things working together: (1) `update-source Loopback0` on both sides, (2) `ebgp-multihop 2`, and (3) a static route on each side to reach the peer's loopback. Missing any one of these causes the session to stay in Active.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | All L2 adjacencies Up, hold times match configured values |
| `show ip route isis` | All /32 loopbacks of remote IS-IS routers present |
| `show bfd neighbors` | All single-hop sessions Up on IS-IS interfaces |
| `show bfd neighbors details` | Registered Protocols includes ISIS |
| `show ip bgp summary` | All iBGP + eBGP sessions Established |
| `show ip bgp 192.0.2.0/24` | Path reachable from all iBGP speakers |
| `show isis spf-log` | SPF runs with sub-100 ms initial delay |
| `show ip bgp neighbors X | include Hold\|Keepalive` | Tuned timers reflected |

### Common IS-IS and BFD Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| IS-IS adjacency stays in INIT | MTU mismatch or authentication mismatch |
| BFD session stays Down | Asymmetric timers; one side missing `bfd interval`; `isis bfd` not configured |
| BFD session flapping | Interval too aggressive for CPU; reduce to 300 ms or higher |
| eBGP session stays in Active | Missing static route to peer loopback; ebgp-multihop not configured; source mismatch |
| BGP receives no prefixes | Missing `network` statement or `activate` in address-family |
| Multi-hop BFD session not forming | `ip bfd peer` binding missing; template name mismatch; static route absent |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS L2 Underlay

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
interface Loopback0
 ip router isis
!
interface GigabitEthernet0/0
 ip router isis
!
interface GigabitEthernet0/1
 ip router isis
!
interface GigabitEthernet0/2
 ip router isis
!
router isis
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface Loopback0
 ip router isis
!
interface GigabitEthernet0/0
 ip router isis
!
interface GigabitEthernet0/1
 ip router isis
!
router isis
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface Loopback0
 ip router isis
!
interface GigabitEthernet0/0
 ip router isis
!
interface GigabitEthernet0/1
 ip router isis
!
interface GigabitEthernet0/2
 ip router isis
!
router isis
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
interface Loopback0
 ip router isis
!
interface GigabitEthernet0/0
 ip router isis
!
interface GigabitEthernet0/1
 ip router isis
!
router isis
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

### Task 2: iBGP Full Mesh and eBGP Dual-Homing

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ip route 10.0.0.5 255.255.255.255 10.1.15.5
!
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 description iBGP-R2
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 description iBGP-R3
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-R4
 neighbor 10.0.0.4 update-source Loopback0
 neighbor 10.0.0.5 remote-as 65200
 neighbor 10.0.0.5 description eBGP-R5-AS65200
 neighbor 10.0.0.5 update-source Loopback0
 neighbor 10.0.0.5 ebgp-multihop 2
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 next-hop-self
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.5 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
ip route 10.0.0.1 255.255.255.255 10.1.15.1
ip route 10.0.0.3 255.255.255.255 10.1.35.3
!
router bgp 65200
 bgp router-id 10.0.0.5
 bgp log-neighbor-changes
 neighbor 10.0.0.1 remote-as 65100
 neighbor 10.0.0.1 description eBGP-R1-AS65100
 neighbor 10.0.0.1 update-source Loopback0
 neighbor 10.0.0.1 ebgp-multihop 2
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 description eBGP-R3-AS65100
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.3 ebgp-multihop 2
 !
 address-family ipv4
  network 192.0.2.0 mask 255.255.255.0
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.3 activate
 exit-address-family
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp 192.0.2.0/24
show ip route 10.0.0.5
```

</details>

---

### Task 4: IS-IS Hello Timer Tuning

<details>
<summary>Click to view All Routers Configuration (R1–R4 per-interface)</summary>

```bash
! On each IS-IS data interface of R1, R2, R3, R4:
interface GigabitEthernet0/0
 isis hello-interval 1
 isis hello-multiplier 3
! Repeat for each additional IS-IS interface on each router
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis neighbors
show isis neighbors detail
```

</details>

---

### Task 5: BFD Single-Hop on IS-IS Interfaces

<details>
<summary>Click to view All Routers Configuration (per IS-IS data interface)</summary>

```bash
! On each IS-IS data interface (not Loopback0):
interface GigabitEthernet0/0
 bfd interval 150 min_rx 150 multiplier 3
 isis bfd
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show bfd neighbors
show bfd neighbors details
show isis neighbors
```

</details>

---

### Task 7: BFD Multi-Hop on eBGP Sessions

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
bfd-template multi-hop BFD_MULTIHOP
 interval min-tx 150 min-rx 150 multiplier 3
!
ip bfd peer 10.0.0.5 multihop src 10.0.0.1 template BFD_MULTIHOP
!
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
bfd-template multi-hop BFD_MULTIHOP
 interval min-tx 150 min-rx 150 multiplier 3
!
ip bfd peer 10.0.0.5 multihop src 10.0.0.3 template BFD_MULTIHOP
!
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
bfd-template multi-hop BFD_MULTIHOP
 interval min-tx 150 min-rx 150 multiplier 3
!
ip bfd peer 10.0.0.1 multihop src 10.0.0.5 template BFD_MULTIHOP
ip bfd peer 10.0.0.3 multihop src 10.0.0.5 template BFD_MULTIHOP
!
router bgp 65200
 neighbor 10.0.0.1 fall-over bfd multi-hop
 neighbor 10.0.0.3 fall-over bfd multi-hop
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show bfd neighbors
show ip bgp neighbors 10.0.0.5 | include BFD|state
```

</details>

---

### Task 8: SPF Throttle and BGP Timers

<details>
<summary>Click to view All Routers Configuration</summary>

```bash
! On R1, R2, R3, R4 — under router isis:
router isis
 spf-interval 5 50 200
 prc-interval 5 50 200
!
! On R1 and R3 — under router bgp:
router bgp 65100
 neighbor 10.0.0.5 timers 5 15
!
! On R5 — under router bgp:
router bgp 65200
 neighbor 10.0.0.1 timers 5 15
 neighbor 10.0.0.3 timers 5 15
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis spf-log
show ip bgp neighbors 10.0.0.5 | include Hold|Keepalive
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>            # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore
```

---

### Ticket 1 — BFD Sessions Between R1 and R2 Are Reported as Down

A colleague reports that after a scheduled maintenance window on R2, `show bfd neighbors` on R1 shows the R2 BFD session as `Down`. IS-IS is still showing the R2 adjacency as Up (running on hello timers), but the fast-convergence SLA is not being met.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show bfd neighbors` on R1 shows the R2 session (Gi0/0) as `Up`. IS-IS convergence on an L1 failure is sub-500 ms.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show bfd neighbors` on R1 — confirm the Gi0/0 session to R2 shows `Down`.
2. Run `show bfd neighbors details` on R1 — note the `Our Diag` and `Remote Diag` fields. Look for "Control Detection Time Expired" which indicates the session is not receiving packets within the detection window.
3. Run `show run interface GigabitEthernet0/0` on both R1 and R2 — compare the `bfd interval` values.
4. Observe that R2's `bfd interval` is set to `50 min_rx 50` while R1's is `500 min_rx 500`. The session negotiates to TX=500 ms (R1's min_rx). With R2's multiplier misconfigured to 1, the detection window on R2 is 500 × 1 = 500 ms — too tight for a heavily loaded EVE-NG host. R2 sees the session as Down and sends a BFD Control packet with the Down state, causing R1 to also declare Down.
5. Confirm with `show bfd neighbors details` — look for `Multiplier` values: R2's multiplier shows 1 instead of 3.

</details>

<details>
<summary>Click to view Fix</summary>

Both R1 and R2 must be corrected to symmetric values. On R1, the slow-side misconfiguration is the root cause of the 500 ms negotiated interval; on R2, the multiplier of 1 causes the detection window to collapse to a single packet.

```bash
! On R1 — GigabitEthernet0/0 (L1 toward R2)
interface GigabitEthernet0/0
 bfd interval 150 min_rx 150 multiplier 3

! On R2 — GigabitEthernet0/0 (L1 toward R1)
interface GigabitEthernet0/0
 bfd interval 150 min_rx 150 multiplier 3
```

After applying both, run `show bfd neighbors` on R1 and confirm the Gi0/0 session transitions from Down to Up within one detection interval (~1-2 seconds).

</details>

---

### Ticket 2 — eBGP Session to R5 Stays in Active State After Lab Reset

The operations team reset R5's configuration and reports that the eBGP session from R1 is stuck in `Active` state. R3's session to R5 is also affected. BGP log on R1 shows repeated connection attempts with no success.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp summary` on R1 shows neighbor 10.0.0.5 in `Established` state with at least 1 prefix received.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp summary` on R1 — confirm 10.0.0.5 shows `Active` in the State column.
2. Run `show ip bgp neighbors 10.0.0.5 | include BGP state|TCP` on R1 — confirm the TCP connection fails. The session cannot complete because R5 cannot route back to R1's loopback (10.0.0.1).
3. From R1, ping 10.0.0.5 — the ping should succeed (direct L6 link is up, R1 has a static route to R5's loopback). But from R5, ping 10.0.0.1 — this fails, confirming R5 has no route to R1's loopback.
4. Run `show ip route 10.0.0.1` on R5 — no route exists. The static host routes (`ip route 10.0.0.1 255.255.255.255 10.1.15.1` and `ip route 10.0.0.3 255.255.255.255 10.1.35.3`) are missing from R5.

</details>

<details>
<summary>Click to view Fix</summary>

On R5, restore the missing static host routes:

```bash
! On R5
ip route 10.0.0.1 255.255.255.255 10.1.15.1
ip route 10.0.0.3 255.255.255.255 10.1.35.3
```

Run `show ip bgp summary` on R1. BGP should transition from `Active` to `Established` within the next keepalive cycle (~15 seconds with the tuned hold timer).

</details>

---

### Ticket 3 — IS-IS Convergence Remains Slow on One Link Despite BFD Configuration

A network audit shows that IS-IS convergence on the R1↔R4 path (L4) is taking approximately 3 seconds after link failure — identical to the pre-BFD baseline. All other IS-IS paths converge in under 500 ms. BFD appears configured on L4 based on the interface configuration, but IS-IS is not reacting to BFD events.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show bfd neighbors` on R1 shows the Gi0/1 session to R4 as `Up` and `show bfd neighbors details` on R1 shows `Registered Protocols: ISIS` for the Gi0/1 session. A link-shut test on L4 converges in under 500 ms.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show bfd neighbors` on R1 — note that the Gi0/1 session (to R4 via L4) shows `Up` but `RH/RS` may show a non-registration state. Or the session shows Up with no protocol registered.
2. Run `show bfd neighbors details` on R1 — examine the Gi0/1 entry. Look at the `Registered Protocols` field — it shows empty or `None` instead of `ISIS`.
3. Run `show run interface GigabitEthernet0/1` on R1 — observe that `bfd interval 150 min_rx 150 multiplier 3` is present, but `isis bfd` is missing. The BFD session itself formed (because BFD runs independently), but IS-IS never registered as a client.
4. Confirm by running `show isis neighbors detail` — the R4 adjacency does not show `BFD` in the flags column.

</details>

<details>
<summary>Click to view Fix</summary>

On R1, add the missing IS-IS BFD registration on the L4 interface:

```bash
! On R1 — GigabitEthernet0/1 (L4 toward R4)
interface GigabitEthernet0/1
 isis bfd
```

Run `show bfd neighbors details` on R1. The Gi0/1 entry should now show `Registered Protocols: ISIS`. Repeat the L4 link-shut test and confirm convergence is sub-500 ms.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS L2 adjacencies established: R1 has three neighbors (R2, R3, R4); all loopbacks reachable via IS-IS
- [ ] iBGP full mesh established: R1, R2, R3, R4 all show three iBGP peers in Established state
- [ ] eBGP dual-homing: R1 and R3 each show one eBGP peer (R5, AS 65200) in Established state
- [ ] 192.0.2.0/24 reachable from all iBGP speakers via next-hop-self rewrite
- [ ] IS-IS hello timers tuned: hold time ~3 s on all IS-IS data interfaces
- [ ] BFD single-hop: all IS-IS interface pairs show Up BFD sessions with ISIS registered
- [ ] Convergence measurement: Task 3 (30 s), Task 4 (3 s), Task 6 (<500 ms) recorded in table
- [ ] BFD multi-hop: R1 and R3 show multi-hop BFD session to R5 (10.0.0.5) as Up
- [ ] BGP fall-over BFD multi-hop registered on R1, R3, and R5 for eBGP neighbors
- [ ] IS-IS SPF/PRC throttle configured on R1–R4: initial-wait=50 ms
- [ ] BGP timers tuned on eBGP sessions: keepalive=5 s, hold=15 s

### Troubleshooting

- [ ] Ticket 1: BFD session between R1 and R2 restored to Up; root cause (asymmetric interval + bad multiplier) identified and corrected
- [ ] Ticket 2: eBGP session R1↔R5 restored to Established; root cause (missing static routes on R5) identified and corrected
- [ ] Ticket 3: IS-IS registered as BFD client on R1 Gi0/1; L4 convergence reduced to sub-500 ms

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
