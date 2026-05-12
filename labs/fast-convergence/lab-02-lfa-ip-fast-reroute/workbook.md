# Lab 02 — IS-IS LFA and IP Fast Reroute

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

**Exam Objective:** 1.7.f — Implement Fast Convergence: LFA / IP-FRR (Fast Convergence topic)

This lab builds on the BFD, NSF, BGP GR, and NSR foundation from lab-00 and lab-01 and adds sub-50 ms IP convergence using IS-IS Loop-Free Alternate (LFA) and Remote LFA (R-LFA) with MPLS LDP tunnels. By the end of this lab, a link failure in the SP core will trigger a precomputed backup path in the FIB — the forwarding plane switches to the backup in microseconds without waiting for IS-IS SPF to recompute.

---

### Loop-Free Alternate (LFA)

An LFA is a directly-connected neighbor that provides a loop-free backup path to a destination if the primary next-hop link fails. The LFA condition is:

> **distance(N_alt, D) < distance(N_alt, S) + distance(S, D)**

Where `S` is the source (the router computing the LFA), `D` is the destination, and `N_alt` is the alternate neighbor. If this inequality holds, forwarding traffic through `N_alt` will not loop back to `S` — it will eventually reach `D`.

**Per-prefix LFA** evaluates this condition for every individual prefix in the routing table, computing a backup next-hop independent of the link that is being protected. This is more granular than per-link LFA, which selects one backup per link regardless of destination.

```
! Enable per-prefix LFA for IS-IS Level 2 on all prefixes
router isis
 fast-reroute per-prefix level-2 all
```

The keyword `all` means LFA computation applies to every IS-IS-learned route. You can also use a route-map to restrict LFA computation to specific prefixes.

### LFA Coverage Gap

Not every topology guarantees a per-prefix LFA for every destination. The LFA condition can fail when the alternate neighbor's best path to the destination is through the source router — meaning a loop would form. In ring topologies without cross-links, coverage can be as low as 50%.

The five-link meshed core in this lab (including the R1↔R3 diagonal) provides high coverage because every router has at least two diverse paths to every other router. Run `show isis fast-reroute summary` to see the actual coverage percentage.

### Remote LFA (R-LFA)

When no directly-connected neighbor qualifies as an LFA, Remote LFA uses a tunnel to a **PQ node** — a node that is in both:

- **P-space** of the source: the set of routers reachable from S without traversing the protected link.
- **Q-space** of the destination: the set of routers that can reach D without traversing the protected link.

A PQ node can forward the traffic toward D without looping back to S. R-LFA tunnels the packet to the PQ node using MPLS (LDP label stacking on IOSv, or SR on newer platforms). The PQ node then forwards natively to D.

```
! Enable Remote LFA with MPLS LDP tunnels
router isis
 fast-reroute per-prefix remote-lfa level-2 tunnel mpls-ldp
```

R-LFA requires MPLS LDP on all core IS-IS interfaces — the tunnel is built from LDP labels. Without end-to-end LDP, the R-LFA tunnel cannot be established.

### LFA vs R-LFA Comparison

| Feature | Per-Prefix LFA | Remote LFA |
|---------|---------------|------------|
| Backup type | Direct alternate neighbor | Tunnel to remote PQ node |
| Requires MPLS | No | Yes (LDP or SR) |
| Coverage in ring | ~50% | ~100% |
| Failure detection | BFD or carrier-delay | BFD or carrier-delay |
| Forwarding-plane switchover | < 50 ms | < 50 ms |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| LFA configuration | Configure per-prefix LFA for IS-IS L2; interpret LFA coverage reports |
| LFA failure testing | Measure sub-50 ms convergence via precomputed FIB backup |
| LFA coverage analysis | Identify prefixes without LFA backup; explain the LFA inequality |
| MPLS LDP deployment | Enable LDP on IS-IS core interfaces for R-LFA transport |
| Remote LFA configuration | Configure R-LFA with `tunnel mpls-ldp`; examine R-LFA tunnels |
| PQ-node analysis | Identify the PQ node from P-space / Q-space intersection |
| R-LFA failure testing | Verify R-LFA coverage extends to previously-uncovered prefixes |
| LFA misconfiguration diagnosis | Identify a broken prefix-list filter that silently disables LFA |

---

## 2. Topology & Scenario

**Scenario:** Your SP core already has BFD, tuned IS-IS timers, NSF, and BGP GR in place from lab-00 and lab-01. The next step is sub-50 ms convergence: you need to ensure that any single-link failure in the core does not require IS-IS SPF to recompute before forwarding can resume. You will deploy per-prefix LFA across all core routers, examine LFA coverage, and then extend coverage to any uncovered prefixes using Remote LFA with MPLS LDP tunnels.

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
   │ 10.0.0.4  │          │     Gi0/1 10.1.34.0  │  Lo0: 10.0.0.3/32     │
   │  /32      │◄── L3 ──►│              Gi0/0   │                        │
   └───────────┘  10.1.34 │              L3      └──┬───────────────────┬─┘
                          │                     L7  │ Gi0/3             │ Gi0/2
                          │               10.1.35.0 │                   │
                          │                         │                   │
                          │                ┌────────┴──────────────────┘
                          │                │
                          │       ┌────────┴──────────────────┐
                          └───────►         R5                │
                            L6 Gi0/0│   CE AS 65200           │
                         10.1.15.0  │  Lo0: 10.0.0.5/32      │
                                    │  Lo1: 192.0.2.1/24      │
                                    └────────────────────────-┘
```

**Link reference:**

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | Ring closer — IS-IS L2, LFA alternate, MPLS LDP |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | Diagonal — IS-IS L2, short path R1↔R3, MPLS LDP |
| L6 | R1 Gi0/3 | R5 Gi0/0 | 10.1.15.0/24 | eBGP R1 (AS 65100) ↔ R5 (AS 65200) |
| L7 | R3 Gi0/3 | R5 Gi0/1 | 10.1.35.0/24 | eBGP R3 (AS 65100) ↔ R5 (AS 65200) |

**Key relationships:**
- All five core links (L1–L5) carry IS-IS L2, iBGP transport, and — once MPLS LDP is configured — MPLS LDP label distribution. Each link has preconfigured BFD single-hop from lab-00.
- LFA computation takes place on every core router (R1–R4). Each router independently computes backup next-hops for IS-IS-learned prefixes.
- Remote LFA uses MPLS LDP tunnels, so MPLS must be enabled on all five core interfaces before R-LFA can establish tunnels.
- The eBGP links (L6, L7) carry no IS-IS and no MPLS — LFA protects only internal SP prefixes carried by IS-IS, not the external CE link itself.

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
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP peering source, BFD multi-hop source, MPLS LDP router-id |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source, MPLS LDP router-id |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source, BFD multi-hop source, MPLS LDP router-id |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, iBGP peering source, MPLS LDP router-id |
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
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all routers
- IS-IS L2 on R1–R4 with tuned hello/hold timers (1 s / 3 s) and SPF/PRC throttle
- BFD single-hop on all IS-IS core interfaces (150 ms × 3 = 450 ms detection)
- iBGP full mesh in AS 65100 (R1–R4), loopback-sourced with `next-hop-self` on R1 and R3
- eBGP sessions R1↔R5 and R3↔R5, loopback-sourced with multihop, BFD multi-hop, and tuned timers
- BGP multi-hop BFD templates and peer bindings on R1, R3, and R5
- BGP Graceful Restart on R1–R5 (`bgp graceful-restart` under `router bgp`)

> **Platform note:** IS-IS NSF (`nsf ietf`), IS-IS NSR (`nsr`), and BGP NSR (`bgp nsr`) are not available on IOSv — these commands are rejected. They appear conceptually in lab-01 but are not pre-loaded.

**IS NOT pre-loaded** (student configures this):
- Per-prefix LFA on R1–R4 under `router isis`
- MPLS LDP on all core IS-IS interfaces (R1–R4)
- Remote LFA (R-LFA) on R1 and R3

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable Per-Prefix LFA on R1–R4

- On each of R1, R2, R3, and R4, enable per-prefix Loop-Free Alternate for IS-IS Level 2. Use the `all` keyword to compute LFA backups for every IS-IS-learned prefix.
- Verify that LFA backup computation has completed using the IS-IS fast-reroute summary command. Confirm that the number of protected prefixes is greater than zero.

**Verification:** `show isis fast-reroute summary` on R1 must show `Fast-Reroute: enabled`, `Per-prefix: enabled`, and a non-zero count for `Prefixes protected`.

---

### Task 2: Examine an LFA Backup in Detail

- On R1, run the detailed LFA command for destination 10.0.0.4/32 (R4's loopback). Identify the primary path and the LFA backup path.
- Explain why the backup next-hop qualifies as a Loop-Free Alternate — write out the LFA inequality and calculate the distances using the topology's IS-IS metrics.
- Repeat the check for destination 10.0.0.2/32 and identify its LFA backup.

> IS-IS default metric on all links is 10. Each hop adds 10 to the total distance. Use `show isis database verbose` on R1 if you need to inspect the advertised metrics for each LSP.

**Verification:** `show isis fast-reroute 10.0.0.4/32 detail` on R1 must show a primary path and at least one backup/repair path with a specific next-hop interface and neighbor address.

---

### Task 3: LFA Failure Test — Measure Sub-50 ms Convergence

- From R2, start a sustained extended ping to R4's loopback (10.0.0.4) sourced from R2's Loopback0. R2's primary path to 10.0.0.4 is via R3 (L2+L3, metric 20).
- Shut down R2's Gi0/1 (L2 to R3). Observe that the ping experiences at most one or two lost packets — the precomputed LFA backup path via R1 (L1→L4 or L1→L5→L3) takes over in the FIB before IS-IS SPF recomputes.
- Bring the interface back up after observing the convergence. Note the approximate packet loss count.
- Compare this to what would happen without LFA: based on your lab-00 measurement, IS-IS with BFD takes ~450 ms to detect + SPF runtime ≈ 500 ms total. With LFA, the switchover is < 50 ms.

> Use `ping 10.0.0.4 source lo0 repeat 200 timeout 0` for a fast-firing sustained ping. The `timeout 0` sends pings as fast as IOS processes them — useful for catching sub-second gaps.

**Verification:** During the Gi0/1 shutdown, `show isis fast-reroute 10.0.0.4/32 detail` on R2 must show the backup path is in use (`Repair path in use` or similar indicator). After the interface comes back up, the primary path should be restored.

---

### Task 4: Identify an LFA Coverage Gap

- Run `show isis fast-reroute summary` on R1 and note the total prefix count versus the protected prefix count. Report the coverage percentage.
- Use `show isis fast-reroute` (without a destination) on R1 to list all IS-IS prefixes and their protection status. If any prefix shows `No backup`, note it.
- If the topology with all-default metrics produces 100% coverage, explain why: the R1↔R3 diagonal link ensures every router has at least two diverse paths to every destination. Under what conditions would a coverage gap appear? (Hint: consider what happens if one link has a much higher metric than the others.)

> This topology may produce 100% LFA coverage with default metrics. That is a valid result — the learning objective is understanding the LFA inequality, not manufacturing a bogus gap. If coverage is 100%, explain the topology property that guarantees it and describe a scenario (unequal metrics, different topology) that would create a gap.

**Verification:** `show isis fast-reroute summary` on R1 must show some protected count. Write a one-paragraph explanation of when and why LFA coverage gaps occur in ring topologies without diagonals.

---

### Task 5: Enable MPLS LDP for Remote LFA

Remote LFA uses MPLS LDP tunnels to reach PQ nodes. Before configuring R-LFA, LDP must be running on all core interfaces.

- On R1, R2, R3, and R4, configure MPLS LDP globally with the loopback0 interface as the router ID. Use the `force` keyword to ensure the router-id takes effect immediately.
- On every core IS-IS interface (Gi0/0, Gi0/1, Gi0/2 on each router; R2 and R4 only have Gi0/0, Gi0/1), enable MPLS LDP with the `mpls ip` interface command.
- Do NOT enable MPLS on the eBGP interfaces (R1 Gi0/3 L6, R3 Gi0/3 L7) or on R5 — MPLS is internal to the SP core only.

```
! Global LDP configuration (all four core routers)
mpls ldp router-id Loopback0 force
!
! On each core interface (R1 example)
interface GigabitEthernet0/0
 mpls ip
!
interface GigabitEthernet0/1
 mpls ip
!
interface GigabitEthernet0/2
 mpls ip
```

**Verification:** `show mpls ldp neighbor` on R1 must show LDP sessions established with all three core neighbors (R2, R3, R4). `show mpls ldp binding` must show label bindings for all loopback prefixes (10.0.0.1–10.0.0.4).

---

### Task 6: Configure Remote LFA (R-LFA) on R1 and R3

- On R1 and R3, add the Remote LFA clause under `router isis` using `tunnel mpls-ldp`. This instructs IS-IS to use MPLS LDP tunnels as the transport for R-LFA backup paths.
- The R-LFA clause works alongside the existing `fast-reroute per-prefix level-2 all` — it does not replace it. Any prefix that has a direct LFA uses the direct LFA; R-LFA secondarily covers prefixes that lack a direct LFA.
- Verify that R-LFA tunnels are established.

**Verification:** `show isis fast-reroute remote-lfa tunnels` on R1 must show at least one R-LFA tunnel with an `Active` state. If the topology has 100% LFA coverage with default metrics, R-LFA tunnels may appear as `Ready` (computed but not needed as primary backup) — confirm they exist in the R-LFA table.

---

### Task 7: R-LFA PQ-Node Analysis

- On R1, examine the R-LFA tunnel table. Identify the PQ node used for a prefix that would NOT have a direct LFA (or, if coverage is 100%, choose the prefix 10.0.0.2/32 and identify which PQ node R-LFA would use when protecting against L1 failure).
- Explain why the identified node qualifies as a PQ node:
  - Show why it is in R1's P-space (reachable from R1 without traversing the protected link).
  - Show why it is in the destination's Q-space (can reach the destination without traversing the protected link).

> As a reference: for R1 protecting destinations via L1 (R1↔R2), the P-space includes R1, R3 (via L5), and R4 (via L4). For destination R2's loopback, the Q-space includes R2 itself and R3 (via L2). The intersection PQ = {R3} — R3 is the PQ node reachable from R1 via L5.

**Verification:** Write a short explanation (3–4 sentences) in your lab notes identifying the PQ node and justifying its qualification for a specific source-destination-protected-link triple.

---

### Task 8: Troubleshoot a Broken Prefix-List LFA Filter (Guided)

> This task simulates a fault planted by the operations team. Use the inject script in Section 9 to introduce the fault, then diagnose and fix it.

- After injecting Ticket 1's fault, run `show isis fast-reroute summary` on R1. Observe that the protected prefix count is now zero despite the LFA clause appearing in the IS-IS configuration.
- Examine the exact `fast-reroute` configuration on R1 using `show running-config | section router isis`. Identify that the `all` keyword has been replaced with a route-map that references a non-existent prefix-list.
- Restore the correct configuration so that LFA computation resumes for all IS-IS prefixes.

**Verification:** `show isis fast-reroute summary` on R1 must show protected prefixes > 0 after the fix. `show run | section router isis` must show `fast-reroute per-prefix level-2 all`.

---

## 6. Verification & Analysis

### Task 1 — LFA Configuration Summary

```
R1# show isis fast-reroute summary
IS-IS IPv4 Fast-Reroute Summary:

Protection Level    Capability        State
---------- ------   ----------        -----
Level-2             Per-Prefix        Enabled

Prefixes:
  Total:           6
  Protected:       6                  ! ← all 6 IS-IS prefixes have LFA backup
  Coverage:        100.00%
```

### Task 2 — LFA Backup Detail

```
R1# show isis fast-reroute 10.0.0.4/32 detail
L2 10.0.0.4/32 [20/115]
     via 10.1.14.4, GigabitEthernet0/1, R4, Weight: 0    ! ← primary path (L4 direct)
       Backup path: 10.1.13.3, GigabitEthernet0/2, R3, Weight: 0, Metric: 30  ! ← LFA via R3 (L5+L3)
       P: No, TM: 30, LC: No, NP: No, D: No
     via 10.1.13.3, GigabitEthernet0/2, R3, Weight: 0
       Backup path: 10.1.14.4, GigabitEthernet0/1, R4, Weight: 0, Metric: 30  ! ← LFA via R4 (L4+L3)

R1# show isis fast-reroute 10.0.0.2/32 detail
L2 10.0.0.2/32 [15/115]
     via 10.1.12.2, GigabitEthernet0/0, R2, Weight: 0    ! ← primary path (L1)
       Backup path: 10.1.13.3, GigabitEthernet0/2, R3, Weight: 0, Metric: 20  ! ← LFA via R3 (L5+L2)
       P: No, TM: 20, LC: No, NP: No, D: No
```

### Task 3 — LFA Failure Test

```
! Before failure: sustained ping R2 → 10.0.0.4
R2# ping 10.0.0.4 source lo0 repeat 100 timeout 0

Type escape sequence to abort.
Sending 100, 100-byte ICMP Echos to 10.0.0.4, timeout is 0 seconds:
Packet sent with a source address of 10.0.0.2
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Success rate is 100 percent (100/100)

! Shut Gi0/1 (L2 to R3) during ping — observe at most 1-2 drops
R2(config)# interface gi0/1
R2(config-if)# shutdown
...
!!!!!!!!!!!!!!!!!!.!.!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  ! ← 1-2 drops at most
Success rate is 99 percent (99/100)

! Verify backup path is active
R2# show isis fast-reroute 10.0.0.4/32 detail
L2 10.0.0.4/32 [20/115]
     via 10.1.23.3, GigabitEthernet0/1, R3, Weight: 0             ! ← primary (now down)
       Backup path: 10.1.12.1, GigabitEthernet0/0, R1, Weight: 0, Metric: 40  ! ← LFA in use via R1
       P: No, TM: 40, LC: No, NP: No, D: No
```

### Task 5 — MPLS LDP Verification

```
R1# show mpls ldp neighbor
    Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.2.646 - 10.0.0.1.20050
        State: Oper; Msgs sent/rcvd: 42/40; Downstream
        Up time: 00:15:32
        LDP discovery sources:
          GigabitEthernet0/0, Src IP addr: 10.1.12.2
    Peer LDP Ident: 10.0.0.3:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.3.646 - 10.0.0.1.16384
        State: Oper; Msgs sent/rcvd: 38/35; Downstream
        Up time: 00:15:30
        LDP discovery sources:
          GigabitEthernet0/2, Src IP addr: 10.1.13.3
    Peer LDP Ident: 10.0.0.4:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.4.646 - 10.0.0.1.14326
        State: Oper; Msgs sent/rcvd: 35/33; Downstream
        Up time: 00:15:28
        LDP discovery sources:
          GigabitEthernet0/1, Src IP addr: 10.1.14.4
```

### Task 6 — R-LFA Tunnels

```
R1# show isis fast-reroute remote-lfa tunnels

Load for five secs: 11%/0%; one minute: 10%; five minutes: 8%
No time source, 00:31:07.626 UTC Sat May 9 2026

L2 Remote LFA Tunnels:

Interface                     Destination  State         Exit
Gi0/1 (to R4)                 10.0.0.2     Ready         Gi0/2 (to R3)  ! ← PQ-node tunnel to R3
Gi0/0 (to R2)                 10.0.0.4     Ready         Gi0/2 (to R3)  ! ← PQ-node tunnel to R3

R1# show isis fast-reroute summary
IS-IS IPv4 Fast-Reroute Summary:

Protection Level    Capability                State
---------- ------   ----------                -----
Level-2             Per-Prefix                Enabled
Level-2             Remote-LFA (mpls-ldp)     Enabled

Prefixes:
  Total:           6
  Protected:       6                  ! ← either direct LFA or R-LFA
  Coverage:        100.00%
```

---

## 7. Verification Cheatsheet

### Per-Prefix LFA

```
router isis
 fast-reroute per-prefix level-2 all
```

| Command | Purpose |
|---------|---------|
| `show isis fast-reroute summary` | Summary: enabled/disabled, prefix count, protected count, coverage % |
| `show isis fast-reroute X.X.X.X/32 detail` | Per-prefix: primary path + backup path with next-hop and metric |
| `show isis fast-reroute` | All IS-IS prefixes with protection status |

> **Exam tip:** `fast-reroute per-prefix` under `router isis` enables the feature. The `all` keyword applies it to every IS-IS-learned prefix. Replacing `all` with a route-map restricts LFA to only matching prefixes. A route-map referencing a non-existent prefix-list computes zero backups — the configuration is accepted but produces no protection.

### MPLS LDP (for R-LFA tunnels)

```
! Global
mpls ldp router-id Loopback0 force
!
! Per core interface
interface GigabitEthernet0/0
 mpls ip
```

| Command | Purpose |
|---------|---------|
| `show mpls ldp neighbor` | Verify LDP sessions with core neighbors |
| `show mpls ldp binding` | Display label bindings for loopback prefixes |
| `show mpls forwarding-table` | Show MPLS forwarding table (LFIB) |

> **Exam tip:** LDP uses the loopback as the transport address for TCP sessions. If the loopback is not advertised by IS-IS (not `ip router isis`), LDP sessions will not establish — the remote peer cannot reach the transport address.

### Remote LFA (R-LFA)

```
router isis
 fast-reroute per-prefix remote-lfa level-2 tunnel mpls-ldp
```

| Command | Purpose |
|---------|---------|
| `show isis fast-reroute remote-lfa tunnels` | List R-LFA tunnels, destination, state, and exit interface |
| `show isis fast-reroute remote-lfa summary` | R-LFA coverage summary |
| `show isis fast-reroute X.X.X.X/32 detail` | Check if prefix uses direct LFA or R-LFA backup |

> **Exam tip:** `tunnel mpls-ldp` is the tunnel method for IOSv. On newer platforms (IOS-XR, NX-OS), `tunnel mpls-ldp` is also valid, and SR platforms use `tunnel segment-routing`. The R-LFA clause is additive — it extends coverage beyond direct LFA; it does not replace per-prefix LFA.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis fast-reroute summary` | Protection level: Per-Prefix enabled; Coverage % |
| `show isis fast-reroute X.X.X.X/32 detail` | Backup path with next-hop, interface, and metric |
| `show mpls ldp neighbor` | `State: Oper` for all core peers (R2, R3, R4 from R1) |
| `show mpls ldp binding` | Label bindings for 10.0.0.1/32, 10.0.0.2/32, etc. |
| `show isis fast-reroute remote-lfa tunnels` | R-LFA tunnels with `State: Ready` or `Active` |

### Common LFA / R-LFA Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show isis fast-reroute summary` shows 0 protected prefixes | `all` replaced with non-existent route-map; or `fast-reroute` missing entirely |
| LFA computed but no R-LFA tunnels appear | `remote-lfa` clause missing or `tunnel mpls-ldp` not specified |
| R-LFA tunnels in `LDP not ready` state | `mpls ip` missing on one or more core interfaces |
| `show mpls ldp neighbor` shows no peers or only some peers | `mpls ip` missing on interfaces or IS-IS not advertising loopback |
| Coverage < 100% after LFA + R-LFA | Trace the uncovered prefix: check P-space and Q-space to find the PQ node gap |
| LDP session flapping | IS-IS hello/hold timers out of sync; check BFD and adjacency stability |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Per-Prefix LFA on R1–R4

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router isis
 fast-reroute per-prefix level-2 all
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router isis
 fast-reroute per-prefix level-2 all
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router isis
 fast-reroute per-prefix level-2 all
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router isis
 fast-reroute per-prefix level-2 all
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis fast-reroute summary
show isis fast-reroute
```

</details>

---

### Task 5: MPLS LDP on Core Interfaces

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Global LDP + per-interface
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
!
interface GigabitEthernet0/1
 mpls ip
!
interface GigabitEthernet0/2
 mpls ip
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — Global LDP + per-interface
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
!
interface GigabitEthernet0/1
 mpls ip
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — Global LDP + per-interface
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
!
interface GigabitEthernet0/1
 mpls ip
!
interface GigabitEthernet0/2
 mpls ip
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Global LDP + per-interface
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
!
interface GigabitEthernet0/1
 mpls ip
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp neighbor
show mpls ldp binding
show mpls forwarding-table
```

</details>

---

### Task 6: Remote LFA on R1 and R3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router isis
 fast-reroute per-prefix remote-lfa level-2 tunnel mpls-ldp
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router isis
 fast-reroute per-prefix remote-lfa level-2 tunnel mpls-ldp
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis fast-reroute remote-lfa tunnels
show isis fast-reroute remote-lfa summary
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                       # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>         # restore
```

---

### Ticket 1 — LFA Shows Zero Protected Prefixes Despite Configuration

After completing the LFA deployment, a colleague reports that R1's `show isis fast-reroute summary` output shows zero protected prefixes — though the `fast-reroute` command is visible in the running configuration.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show isis fast-reroute summary` on R1 shows non-zero protected prefixes and `show run | section router isis` shows `fast-reroute per-prefix level-2 all`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis fast-reroute summary` on R1 — `Prefixes protected: 0` despite `Fast-Reroute` showing the feature is enabled.
2. Run `show running-config | section router isis` on R1 — observe that the `fast-reroute` line references `route-map NONEXISTENT` instead of `all`. A route-map with a non-existent prefix-list matches zero prefixes, so IS-IS computes zero LFA backups.
3. Run `show route-map NONEXISTENT` — this returns an error or empty output, confirming the route-map does not exist.
4. Root cause: someone pasted an LFA configuration snippet from another domain that used a local route-map name (`NONEXISTENT`). The router accepted the configuration because the `fast-reroute` command does not validate the route-map at commit time — it only evaluates it during computation. Since the route-map references nothing, zero prefixes match and zero backups are computed.

</details>

<details>
<summary>Click to view Fix</summary>

On R1, replace the broken route-map reference with the `all` keyword:

```bash
! On R1
router isis
 no fast-reroute per-prefix level-2 route-map NONEXISTENT
 fast-reroute per-prefix level-2 all
```

After applying, run `show isis fast-reroute summary` and confirm `Prefixes protected` is now non-zero. Run `show isis fast-reroute` to see individual backup paths.

</details>

---

### Ticket 2 — R-LFA Tunnels Show "LDP Not Ready" for Some Destinations

The monitoring dashboard shows that R1's Remote LFA tunnels for certain destinations are stuck in a `LDP not ready` state. Per-prefix LFA is working correctly — only the R-LFA extension is impaired.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show mpls ldp neighbor` on R2 shows both R1 and R3 as LDP peers; `show isis fast-reroute remote-lfa tunnels` on R1 shows all R-LFA tunnels in `Ready` or `Active` state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis fast-reroute remote-lfa tunnels` on R1 — some tunnels show `State: LDP not ready` instead of `Ready` or `Active`.
2. Run `show mpls ldp neighbor` on R1 — all three neighbors (R2, R3, R4) appear `Oper`. R1's LDP is fine.
3. Run `show mpls ldp neighbor` on R2 — only R1 appears as an LDP peer. R3 is missing.
4. Run `show running-config interface GigabitEthernet0/1` on R2 — the L2 interface to R3 is missing `mpls ip`. LDP is not enabled on this interface, so R2 and R3 cannot exchange labels over L2.
5. Root cause: `mpls ip` was removed from R2's Gi0/1 (L2 to R3). This breaks the end-to-end LDP LSP across the R2↔R3 segment, preventing R-LFA tunnels that require traversal through R2→R3 from being built.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, re-enable MPLS LDP on the L2 interface:

```bash
! On R2
interface GigabitEthernet0/1
 mpls ip
```

Wait 10–20 seconds for LDP discovery and session establishment. Verify with `show mpls ldp neighbor` on R2 — R3's LDP session should now appear. Then check `show isis fast-reroute remote-lfa tunnels` on R1 — all tunnels should transition to `Ready` or `Active`.

</details>

---

### Ticket 3 — R3 Has No LFA Protection

An operations engineer observes that R3's convergence on link failures is much slower than expected — approximately 500 ms (IS-IS SPF recompute time) instead of < 50 ms. Per-prefix LFA was supposed to be deployed domain-wide, but R3 appears to have no backup paths.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show isis fast-reroute summary` on R3 shows non-zero protected prefixes and LFA coverage matches the other core routers.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis fast-reroute summary` on R3 — the command either shows `Fast-Reroute: disabled` or errors out because the feature clause is missing entirely.
2. Run `show running-config | section router isis` on R3 — confirm that no `fast-reroute` clause exists under the IS-IS process. R3 has BFD, timers, and NSF, but the LFA configuration was never applied or was accidentally removed.
3. Run the same check on R1, R2, and R4 — they all have `fast-reroute per-prefix level-2 all`. The gap is specific to R3.
4. Root cause: the `fast-reroute per-prefix level-2 all` command was removed from R3's IS-IS process. R3 is an unprotected node in an otherwise LFA-covered mesh. Any link failure adjacent to R3 causes a full IS-IS SPF recompute on R3.

</details>

<details>
<summary>Click to view Fix</summary>

On R3, restore the LFA configuration:

```bash
! On R3
router isis
 fast-reroute per-prefix level-2 all
```

After applying, run `show isis fast-reroute summary` on R3 and confirm `Prefixes protected` matches the other routers. Run `show isis fast-reroute` to verify individual backup paths for IS-IS-learned prefixes.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Per-prefix LFA enabled on R1–R4: `show isis fast-reroute summary` shows enabled and protected prefixes > 0 on all four routers
- [ ] LFA backup detail examined: `show isis fast-reroute 10.0.0.4/32 detail` on R1 shows at least one backup path
- [ ] LFA failure test (Task 3): R2→10.0.0.4 ping survives L2 shutdown with ≤ 2 packet drops
- [ ] LFA coverage analysis (Task 4): Coverage percentage noted; LFA inequality explained in writing
- [ ] MPLS LDP enabled on all core interfaces: `show mpls ldp neighbor` shows LDP sessions between all core pairs
- [ ] Remote LFA configured on R1 and R3: `show isis fast-reroute remote-lfa tunnels` shows R-LFA tunnels in `Ready` or `Active`
- [ ] PQ-node analysis (Task 7): PQ node identified and P-space/Q-space intersection explained in writing

### Troubleshooting

- [ ] Ticket 1: Broken route-map prefix-list filter on R1 identified and replaced with `all`
- [ ] Ticket 2: Missing `mpls ip` on R2 Gi0/1 identified and restored; R-LFA tunnels back to `Ready`
- [ ] Ticket 3: Missing `fast-reroute` clause on R3 identified and restored; all four routers now LFA-protected

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
