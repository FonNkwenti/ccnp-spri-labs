# Lab 03 — BGP PIC Edge/Core and Additional Paths

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

**Exam Objectives:**
- **1.7.e** — BGP PIC (edge and core)
- **1.7.g** — BGP additional and backup path

This lab builds on the full fast-convergence stack from lab-00, lab-01, and lab-02: BFD, tuned timers, IS-IS NSF, BGP GR, and IS-IS LFA/R-LFA with MPLS LDP are all active. You will now add BGP Prefix-Independent Convergence (PIC) — the BGP-level mechanism that pre-computes and installs a backup next-hop in the FIB/Cisco Express Forwarding table so that BGP convergence on an edge failure happens in the forwarding plane without waiting for BGP best-path recomputation.

The lab also covers **BGP Add-Paths** (additional paths) — the mechanism that allows BGP speakers to advertise more than one path for the same prefix. Add-paths is the plumbing that delivers multiple paths to iBGP peers; PIC consumes those additional paths to pre-install the backup.

---

### BGP PIC (Prefix-Independent Convergence)

BGP PIC decouples BGP convergence from IGP convergence. Normally, when a BGP next-hop becomes unreachable (e.g., an eBGP edge router's loopback disappears from the IGP), every BGP prefix with that next-hop must be re-evaluated — best-path selection runs, and the RIB is recalculated prefix by prefix. For an SP core with hundreds of thousands of prefixes, this can take seconds or even tens of seconds.

**BGP PIC Edge** pre-installs a backup path for eBGP-learned prefixes on the edge router. When the primary eBGP session fails (BFD detects the failure in ~150 ms), the router immediately switches to the backup path in the FIB — no BGP best-path recomputation needed.

**BGP PIC Core** extends this to iBGP speakers. When a core router loses reachability to a BGP next-hop (e.g., the edge router's loopback), it already has a backup next-hop computed and installed in the FIB. The forwarding plane switches in sub-second time.

The key commands:

```
! Global — enable additional paths and PIC backup selection
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
 !
 ! Per-neighbor — advertise and receive additional paths
 address-family ipv4
  neighbor 10.0.0.2 advertise additional-paths best 2
  neighbor 10.0.0.2 additional-paths receive
```

| Command | Purpose |
|---------|---------|
| `bgp recursion host` | Uses IGP next-hop for recursive BGP resolution (required for PIC) |
| `bgp additional-paths install` | Enables the router to install multiple paths per prefix in the RIB |
| `bgp additional-paths select backup` | Automatically selects the second-best path as a PIC backup |
| `neighbor X advertise additional-paths best 2` | Sends up to 2 best paths to this neighbor (sender side) |
| `neighbor X additional-paths receive` | Capability to receive multiple paths from this neighbor (receiver side) |

**How PIC works:**

1. R1 learns 192.0.2.0/24 via eBGP from R5 (primary, next-hop 10.0.0.5).
2. R3 also learns 192.0.2.0/24 via eBGP from R5 (next-hop 10.0.0.5).
3. R1 and R3 advertise the prefix to iBGP peers with `next-hop-self` (making next-hop 10.0.0.1 or 10.0.0.3, which are the edge routers' loopbacks reachable via IS-IS).
4. **Without add-paths**: each iBGP speaker has only one best path. R2 sees 192.0.2.0/24 via R1 (best path) — it never installs the path via R3.
5. **With add-paths**: R1 and R3 each advertise two paths. R2 receives both: best via R1, second-best via R3 (or vice versa).
6. **PIC backup selection**: `bgp additional-paths select backup` automatically picks the second-best path and installs it as a backup in the FIB.
7. **Failure**: When the primary next-hop fails, the FIB already has the backup next-hop pre-programmed. Forwarding switches in < 1 second — no BGP convergence run needed.

### BGP Add-Paths

Add-paths (RFC 7911) extends BGP UPDATE messages to carry multiple paths for the same NLRI (Network Layer Reachability Information). Each path has a **path identifier** that distinguishes it.

On CSR1000v, add-paths is configured per neighbor under the address-family:

```
address-family ipv4
 neighbor 10.0.0.2 advertise additional-paths best 2
 neighbor 10.0.0.2 additional-paths receive
```

- `advertise additional-paths best N` tells the router to advertise up to N best paths to the specified neighbor.
- `additional-paths receive` enables the capability to accept additional paths from that neighbor. Both sides must have this for the negotiation to succeed.

**Without add-paths**, only the best path is advertised — even if the advertising router has multiple paths in its own BGP table, only the selected best appears in UPDATE messages to iBGP peers.

**With add-paths**, the sender sends every path that qualifies (up to the `best N` limit), and the receiver can install them all (assuming `bgp additional-paths install` is configured globally).

### BGP PIC vs IS-IS LFA — Two Layers of Protection

| Layer | Mechanism | Protects Against | Convergence Time |
|-------|-----------|-----------------|------------------|
| IGP (lab-02) | IS-IS LFA / R-LFA | Link/node failure within IS-IS domain | < 50 ms (forwarding-plane) |
| BGP (lab-03) | BGP PIC Edge/Core | BGP next-hop unreachable (eBGP or edge router failure) | < 1 s (forwarding-plane) |

LFA protects the IGP next-hop — if a link fails, the packet is rerouted at the IGP level without IS-IS SPF. PIC protects the BGP next-hop — if the edge router's loopback becomes unreachable or the eBGP session drops, BGP prefixes are already backed up in the FIB.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Add-paths configuration | Enable add-paths on iBGP sessions; advertise/receive multiple paths |
| BGP PIC edge | Configure PIC on edge routers R1 and R3 for the eBGP-learned prefix |
| BGP PIC core | Configure PIC on core routers R2 and R4 for iBGP-learned prefixes |
| Multi-path BGP table inspection | Use `show ip bgp <prefix>` to see all installed paths with path IDs |
| PIC backup verification | Use `show ip cef <prefix> detail` to confirm backup next-hop |
| PIC failure testing | Measure convergence time with PIC enabled vs disabled |
| Add-paths receipt troubleshooting | Diagnose a missing `additional-paths receive` capability |
| PIC backup selection gap | Identify when `select backup` is missing and only one path is in FIB |

---

## 2. Topology & Scenario

**Scenario:** Your SP core already has BFD, tuned IS-IS timers, IS-IS NSF, BGP GR, and IS-IS LFA/R-LFA from labs 00–02. The NOC has observed that during an eBGP edge-router failure, BGP convergence on the external prefix (192.0.2.0/24) takes 5–10 seconds because every iBGP speaker recomputes best-path from scratch. You must deploy BGP PIC and Add-Paths to pre-compute backup next-hops in the FIB so that forwarding-plane switchover is sub-second.

```
              AS 65100 (SP core — IS-IS L2 + iBGP full mesh)

         ┌──────────────────────┐              ┌──────────────────────┐
         │         R1           │── L1 ─────── │         R2           │
         │  SP Edge AS 65100    │  Gi1   Gi1   │  SP Core AS 65100    │
         │  Lo0: 10.0.0.1/32    │  10.1.12.0   │  Lo0: 10.0.0.2/32    │
         └──┬──────┬──────┬─────┘              └────────────┬─────────┘
        L4  │  L5  │  L6  │ Gi4                          L2  │ Gi2
       Gi2  │ Gi3  │      │ 10.1.15.0                       │ 10.1.23.0
            │      │      │                                  │
   ┌────────┴──┐   │      │                      ┌───────────┴────────────┐
   │    R4     │   └──────┼──────────────────────►         R3             │
   │  SP Core  │          │             Gi3 L5  │  SP Edge AS 65100      │
   │ 10.0.0.4  │          │       Gi2 10.1.34.0  │  Lo0: 10.0.0.3/32     │
   │  /32      │◄── L3 ──►│              Gi1     │                        │
   └───────────┘  10.1.34 │              L3      └──┬───────────────────┬─┘
       Gi1 R4            │                     L7  │ Gi4              L5 │ Gi3
                          │               10.1.35.0 │                   │
                          │                         │                   │
                          │                ┌────────┴──────────────────┘
                          │                │
                          │       ┌────────┴──────────────────┐
                          └───────►         R5                │
                            L6 Gi1│   CE AS 65200             │
                         10.1.15.0 │  Lo0: 10.0.0.5/32        │
                                    │  Lo1: 192.0.2.1/24      │
                                    └────────────────────────-┘
```

**Link reference:**

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi1 | R2 Gi1 | 10.1.12.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L2 | R2 Gi2 | R3 Gi1 | 10.1.23.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L3 | R3 Gi2 | R4 Gi1 | 10.1.34.0/24 | SP core — IS-IS L2, iBGP transport, MPLS LDP |
| L4 | R1 Gi2 | R4 Gi2 | 10.1.14.0/24 | Ring closer — IS-IS L2, LFA alternate, MPLS LDP |
| L5 | R1 Gi3 | R3 Gi3 | 10.1.13.0/24 | Diagonal — IS-IS L2, short path R1↔R3, MPLS LDP |
| L6 | R1 Gi4 | R5 Gi1 | 10.1.15.0/24 | eBGP R1 (AS 65100) ↔ R5 (AS 65200) |
| L7 | R3 Gi4 | R5 Gi2 | 10.1.35.0/24 | eBGP R3 (AS 65100) ↔ R5 (AS 65200) |

**Key relationships:**
- R1 and R3 are the BGP PIC edge routers. Each runs an eBGP session to R5 (AS 65200) and learns the external prefix 192.0.2.0/24. With add-paths, each edge router conveys the R5-learned path plus any additional iBGP paths from the other edge router.
- R2 and R4 are the BGP PIC core routers. They receive multiple paths for 192.0.2.0/24 via add-paths from both R1 and R3. PIC core pre-installs the backup next-hop.
- The full convergence stack from labs 00–02 (BFD, IS-IS NSF, BGP GR, LFA/R-LFA, MPLS LDP) remains active — this lab adds BGP PIC as the final layer.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R2 | SP Core — iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R3 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R4 | SP Core — redundant path, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R5 | External CE — dual-homed eBGP in AS 65200 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |

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
| L1 | R1 | R2 | 10.1.12.0/24 | GigabitEthernet1 | GigabitEthernet1 |
| L2 | R2 | R3 | 10.1.23.0/24 | GigabitEthernet2 | GigabitEthernet1 |
| L3 | R3 | R4 | 10.1.34.0/24 | GigabitEthernet2 | GigabitEthernet1 |
| L4 | R1 | R4 | 10.1.14.0/24 | GigabitEthernet2 | GigabitEthernet2 |
| L5 | R1 | R3 | 10.1.13.0/24 | GigabitEthernet3 | GigabitEthernet3 |
| L6 | R1 | R5 | 10.1.15.0/24 | GigabitEthernet4 | GigabitEthernet1 |
| L7 | R3 | R5 | 10.1.35.0/24 | GigabitEthernet4 | GigabitEthernet2 |

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
- `no ip domain lookup` on all routers
- IS-IS L2 on R1–R4 with tuned hello/hold timers (1 s / 3 s) and SPF/PRC throttle
- IS-IS Graceful Restart (NSF) on R1–R4 (`nsf ietf` under `router isis`) — inherited from lab-01
- BFD single-hop on all IS-IS core interfaces (150 ms × 3 = 450 ms detection)
- iBGP full mesh in AS 65100 (R1–R4), loopback-sourced with `next-hop-self` on R1 and R3
- eBGP sessions R1↔R5 and R3↔R5, loopback-sourced with multihop, BFD multi-hop, and tuned timers
- BGP multi-hop BFD templates and peer bindings on R1, R3, and R5
- BGP Graceful Restart on R1–R5 (`bgp graceful-restart` under `router bgp`)
- Per-prefix LFA on R1–R4 (`fast-reroute per-prefix level-2 all`)
- Remote LFA on R1 and R3 (`fast-reroute per-prefix remote-lfa level-2 tunnel mpls-ldp`)
- MPLS LDP on all core IS-IS interfaces (R1–R4) — `mpls ldp router-id Loopback0 force` globally, `mpls ip` on each core interface

> **Platform note:** IS-IS NSR (`nsr`) and BGP NSR (`bgp nsr`) are not supported on the single-RP CSR1000v platform. These commands are rejected. They are covered conceptually in lab-01.

**IS NOT pre-loaded** (student configures this):
- `bgp additional-paths install` and `bgp additional-paths select backup` on R1–R4
- `bgp recursion host` on R1–R4
- Per-neighbor `advertise additional-paths best 2` and `additional-paths receive` on all iBGP peers (R1–R4)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Observe Pre-PIC BGP State — Single Path Only

Before configuring PIC, observe the current BGP behavior to establish a baseline.

- On R2, examine the BGP table for prefix 192.0.2.0/24. Note that only one path is installed — R2 runs best-path selection and selects only the winning path.
- On R2, examine the CEF/FIB entry for 192.0.2.0/24. The prefix is installed via a single next-hop. There is no backup.
- Repeat this check on R4 — same result.

> R2's best path to 192.0.2.0/24 depends on IGP metrics to the next-hop (10.0.0.1 or 10.0.0.3). Since R2 is directly connected to both R1 (L1) and R3 (L2) with metric-10 links, the path through the lower router-ID may be preferred if distances are equal. Document the current best path.

**Verification:** `show ip bgp 192.0.2.0` on R2 must show exactly one path with `>` (best). `show ip cef 192.0.2.0 detail` must show a single next-hop with no backup.

---

### Task 2: Enable BGP Add-Paths Globally on R1–R4

Add-paths is the prerequisite for PIC — without it, routers cannot receive or install multiple paths for the same prefix.

- On R1, R2, R3, and R4, enable add-paths globally:
  ```
  router bgp 65100
   bgp additional-paths install
   bgp additional-paths select backup
   bgp recursion host
  ```

> **`bgp recursion host`**: Forces BGP to use the IGP next-hop for recursive resolution. This is critical for PIC because the backup path must be resolved through the IGP's precomputed LFA backup if both BGP and IGP convergence events coincide. Without it, BGP might resolve the next-hop through a different recursive path and lose the backup.

> **`bgp additional-paths select backup`**: Automatically selects the second-best path as the backup path for PIC. Without this, even though multiple paths are in the BGP table, the router does not tag one as a backup for FIB installation.

**Verification:** `show run | section router bgp` on each router must show all three global commands. BGP sessions will not flap — these are non-disruptive additions.

---

### Task 3: Configure Add-Paths on iBGP Neighbors

Enable add-paths advertisement and receipt on every iBGP session. This must be done on all four core routers — add-paths is a negotiated capability and both sides must agree.

- On each of R1, R2, R3, and R4, under `address-family ipv4`, configure every iBGP neighbor:
  ```
  neighbor 10.0.0.X advertise additional-paths best 2
  neighbor 10.0.0.X additional-paths receive
  ```
- `best 2` advertises up to two best paths. This is sufficient for the dual-homed R5 topology — R5 has two eBGP paths into AS 65100, and we want iBGP speakers to know both.
- You do NOT need to add these commands on the eBGP sessions to R5. Add-paths is only needed within the iBGP mesh. R5 will continue to send only one path per eBGP session.

> **Important:** BGP sessions must be reset (soft clear) after the add-paths capability change. The capability is negotiated during session establishment, and a configuration change to capabilities does not automatically renegotiate unless the session flaps or you issue a soft reset. Use `clear ip bgp * soft` or per-neighbor `clear ip bgp 10.0.0.X soft` after configuring both sides.

**Verification:** After soft-clearing sessions, wait 30 seconds for BGP convergence. On R2, run `show ip bgp 192.0.2.0` — you should now see **two paths** (one via R1, one via R3) with the `>` marker on the best path.

---

### Task 4: Verify PIC Backup Path Installation

With add-paths and PIC configured, the backup path should be pre-installed in the FIB.

- On R2, verify the BGP table for 192.0.2.0/24 shows two installed paths. Note the path IDs assigned to each.
- On R2, check the CEF table: `show ip cef 192.0.2.0 detail`. The output should show the primary next-hop and a **backup next-hop**.
- The backup is the second-best path that `bgp additional-paths select backup` selected automatically.
- Repeat this on R4 — the backup should also be pre-installed.

**Verification:** `show ip cef 192.0.2.0 detail` on R2 must show both a primary and backup next-hop. The backup should be different from the primary (one via R1's loopback, one via R3's loopback).

---

### Task 5: PIC Edge Failure Test — Shut eBGP Session on R1

Now test the PIC edge behavior by failing R1's eBGP session to R5.

- Before the failure, verify R1's BGP table for 192.0.2.0 shows the primary path via eBGP (R5) and any additional iBGP paths. R1 may receive the prefix from R3 via iBGP as a backup.
- On R2, start a sustained extended ping to 192.0.2.1 (the external prefix) sourced from Loopback0:
  ```
  ping 192.0.2.1 source lo0 repeat 200 timeout 0
  ```
- Shut down R1's Gi4 (L6 to R5). This removes R1's eBGP-learned path to 192.0.2.0/24.
- Observe the ping on R2. With PIC:
  - **If R2's primary path was via R1**, R2's FIB already has the backup via R3 pre-installed. The switchover should be sub-second with at most a few dropped pings.
  - **If R2's primary path was via R3**, the disruption should be zero — R2's primary is unaffected.
- Bring Gi4 back up after testing.
- Repeat the test by shutting R3's Gi4 (L7 to R5) instead.

> `ping 192.0.2.1 source lo0 repeat 200 timeout 0` sends pings as fast as IOS processes them — useful for catching sub-second gaps.

**Verification:** During the failure, `show ip bgp 192.0.2.0` on R2 must show the remaining path is still installed and forwarding. `show ip cef 192.0.2.0 detail` on R2 must show the backup path has become the active next-hop (or the primary was already unaffected). Ping loss should be ≤ 3 packets.

---

### Task 6: PIC Core Failure Test — Remove Edge Router Loopback from IS-IS

This test simulates the failure of an entire edge router — its loopback disappears from IS-IS, affecting BGP next-hop reachability for all iBGP-learned prefixes.

- On R1, remove IS-IS from Loopback0 (`no ip router isis` on Loopback0). This withdraws 10.0.0.1/32 from the IS-IS LSP.
- All iBGP peers will lose reachability to 10.0.0.1 as a BGP next-hop. Without PIC, this would trigger a full BGP best-path recomputation for every prefix with next-hop 10.0.0.1.
- With PIC on R2:
  - If 10.0.0.1 was R2's primary next-hop for 192.0.2.0/24, the backup via 10.0.0.3 (R3's loopback) should take over in the FIB.
  - The ping from R2 to 192.0.2.1 should survive with minimal loss.
- Restore IS-IS on R1's Loopback0 after testing:
  ```
  interface Loopback0
   ip router isis
  ```

> **Note:** This test removes the BGP next-hop from the IGP — a more fundamental disruption than shutting an eBGP link. BGP PIC Core specifically handles this case. Without PIC, BGP would take several seconds to withdraw the path via R1 and select the R3 path.

**Verification:** During the Loopback0 IS-IS removal, `show ip cef 192.0.2.0 detail` on R2 must show the backup next-hop (R3's loopback) is now forwarding. After restoring, R1's path should return as primary or backup.

---

### Task 7: Add-Paths Path Identifier Inspection

- On R2, use `show ip bgp 192.0.2.0` to display all installed paths. Note the path IDs (labeled as `rx pathid` / `tx pathid` in the output).
- On R2, use `show ip bgp neighbors 10.0.0.1 advertised-routes` to see what paths R2 is sending to R1. Since R2 is a core router receiving from both edges, does it re-advertise both paths?
- On R1, use `show ip bgp neighbors 10.0.0.2 advertised-routes` to see what paths R1 is sending to R2. How many paths does R1 advertise for 192.0.2.0/24?

> A core router (R2) that receives two paths for 192.0.2.0/24 may re-advertise both if add-paths is configured in both directions. An edge router (R1) learns the prefix from eBGP plus iBGP — it may have multiple paths, but only the best (eBGP from R5) is typically sent unless iBGP-learned paths are also in the top N.

**Verification:** Document the path identifier values and the number of paths exchanged between each iBGP pair. Confirm that add-paths is working bidirectionally on all iBGP sessions.

---

### Task 8: Troubleshoot Missing Backup Path (Guided)

> This task simulates a fault planted by the operations team. Use the inject script in Section 9 to introduce the fault, then diagnose and fix it.

- After injecting Ticket 1's fault, run `show ip bgp 192.0.2.0` on R2. Observe that only one path is installed — the second path is missing from the BGP table.
- Check the running configuration on R2's BGP process. Look for the global add-paths commands.
- Identify the missing statement and restore it so that the backup path is pre-installed in the FIB again.

**Verification:** `show ip cef 192.0.2.0 detail` on R2 must show both a primary and backup next-hop after the fix. `show run | section router bgp` must include `bgp additional-paths install` and `bgp additional-paths select backup`.

---

## 6. Verification & Analysis

### Task 1 — Pre-PIC Baseline (Single Path)

```
R2# show ip bgp 192.0.2.0
BGP routing table entry for 192.0.2.0/24, version 17
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65200
    10.0.0.1 (metric 20) from 10.0.0.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 0, tx pathid: 0

R2# show ip cef 192.0.2.0 detail
192.0.2.0/24, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.0.0.1
    attached to GigabitEthernet1
                  ! ← single next-hop, no backup
```

### Task 4 — PIC Backup Path Verification (Two Paths with Backup)

```
R2# show ip bgp 192.0.2.0
BGP routing table entry for 192.0.2.0/24, version 21
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65200
    10.0.0.1 (metric 20) from 10.0.0.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 1, tx pathid: 1
  65200
    10.0.0.3 (metric 20) from 10.0.0.3 (10.0.0.3)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 2, tx pathid: 0

R2# show ip cef 192.0.2.0 detail
192.0.2.0/24, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.0.0.1
    attached to GigabitEthernet1
  recursive via 10.0.0.3, backup          ! ← backup next-hop pre-installed
    attached to GigabitEthernet2
```

### Task 5 — PIC Edge Failure Test

```
! Before failure: sustained ping R2 → 192.0.2.1
R2# ping 192.0.2.1 source lo0 repeat 100 timeout 0

Type escape sequence to abort.
Sending 100, 100-byte ICMP Echos to 192.0.2.1, timeout is 0 seconds:
Packet sent with a source address of 10.0.0.2
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Success rate is 100 percent (100/100)

! Shut R1 Gi4 (L6 to R5) during ping
R1(config)# interface gigabitEthernet4
R1(config-if)# shutdown

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!.!.!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Success rate is 99 percent (99/100)    ! ← 1 drop (PIC sub-second switchover)

! Check CEF on R2 — backup via R3 is now forwarding
R2# show ip cef 192.0.2.0 detail
192.0.2.0/24, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.0.0.3              ! ← backup now active
    attached to GigabitEthernet2
```

### Task 6 — PIC Core Failure Test

```
! Remove IS-IS from R1 Loopback0
R1(config)# interface Loopback0
R1(config-if)# no ip router isis

! On R2 — observe FIB switchover
R2# show ip cef 192.0.2.0 detail
192.0.2.0/24, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.0.0.3              ! ← only R3's loopback reachable now
    attached to GigabitEthernet2

! R2 BGP table — R1 path withdrawn (next-hop unreachable)
R2# show ip bgp 192.0.2.0
BGP routing table entry for 192.0.2.0/24, version 22
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65200
    10.0.0.3 (metric 20) from 10.0.0.3 (10.0.0.3)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 2, tx pathid: 1

! Restore
R1(config)# interface Loopback0
R1(config-if)# ip router isis
```

---

## 7. Verification Cheatsheet

### BGP PIC and Add-Paths Global Configuration

```
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
```

| Command | Purpose |
|---------|---------|
| `bgp recursion host` | Use IGP next-hop for BGP recursive resolution (required for PIC) |
| `bgp additional-paths install` | Enable installation of multiple paths per prefix in RIB |
| `bgp additional-paths select backup` | Auto-select second-best path as PIC backup for FIB |

### Add-Paths Per-Neighbor Configuration

```
address-family ipv4
 neighbor 10.0.0.X advertise additional-paths best 2
 neighbor 10.0.0.X additional-paths receive
```

| Command | Purpose |
|---------|---------|
| `advertise additional-paths best N` | Send up to N best paths to this neighbor |
| `additional-paths receive` | Enable capability to receive multiple paths from this neighbor |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp 192.0.2.0` | Number of paths installed (should be 2 after PIC) |
| `show ip bgp 192.0.2.0` | `rx pathid` and `tx pathid` — non-zero indicates add-paths active |
| `show ip cef 192.0.2.0 detail` | `recursive via X, backup` — indicates PIC backup installed |
| `show ip bgp neighbors 10.0.0.X advertised-routes` | Check paths advertised to a specific iBGP peer |
| `show ip bgp neighbors 10.0.0.X | include additional-paths` | Check add-paths capability negotiated |
| `show ip bgp neighbors 10.0.0.X | include path` | Check add-paths send/receive state |
| `show ip bgp all summary` | Verify all BGP sessions are established |

### Common BGP PIC / Add-Paths Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Only one path in `show ip bgp 192.0.2.0` after configuration | `bgp additional-paths install` missing globally; or sessions not soft-cleared after capability change |
| Two paths in BGP table but no backup in CEF | `bgp additional-paths select backup` missing |
| `additional-paths` not shown in neighbor capabilities | `additional-paths receive` missing on one side; or session not cleared after config |
| Add-paths capability negotiated but only one path received | Sender missing `advertise additional-paths best N`; or eBGP session missing add-paths (R5 not configured) |
| Backup path installed but failure test shows high loss | `bgp recursion host` missing — BGP resolving next-hop through different path |
| Path ID always 0 | Add-paths not negotiated for that session; or global `bgp additional-paths install` missing |

> **Exam tip:** Add-paths requires configuration on **both sides** of the BGP session. The sender needs `advertise additional-paths`; the receiver needs `additional-paths receive`. If either side is missing its directive, the capability is not negotiated and only one path is exchanged — even if the global `bgp additional-paths install` is present on both routers.

> **Exam tip:** `bgp additional-paths select backup` is what actually creates the PIC backup in the FIB. Without it, multiple paths may be in the BGP table but CEF only installs one (the best). The `select backup` keyword tells IOS to pre-program the second-best path's next-hop as a backup in the forwarding table.

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 2: Global Add-Paths and PIC on R1–R4

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Global add-paths + PIC
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — Global add-paths + PIC
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — Global add-paths + PIC
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Global add-paths + PIC
router bgp 65100
 bgp recursion host
 bgp additional-paths install
 bgp additional-paths select backup
```

</details>

---

### Task 3: Add-Paths on iBGP Neighbors

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Per-neighbor add-paths (all iBGP peers)
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.2 advertise additional-paths best 2
  neighbor 10.0.0.2 additional-paths receive
  neighbor 10.0.0.3 advertise additional-paths best 2
  neighbor 10.0.0.3 additional-paths receive
  neighbor 10.0.0.4 advertise additional-paths best 2
  neighbor 10.0.0.4 additional-paths receive
 exit-address-family
!
! Soft-clear all sessions to renegotiate add-paths capability
clear ip bgp * soft
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — Per-neighbor add-paths (all iBGP peers)
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 advertise additional-paths best 2
  neighbor 10.0.0.1 additional-paths receive
  neighbor 10.0.0.3 advertise additional-paths best 2
  neighbor 10.0.0.3 additional-paths receive
  neighbor 10.0.0.4 advertise additional-paths best 2
  neighbor 10.0.0.4 additional-paths receive
 exit-address-family
!
clear ip bgp * soft
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — Per-neighbor add-paths (all iBGP peers)
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 advertise additional-paths best 2
  neighbor 10.0.0.1 additional-paths receive
  neighbor 10.0.0.2 advertise additional-paths best 2
  neighbor 10.0.0.2 additional-paths receive
  neighbor 10.0.0.4 advertise additional-paths best 2
  neighbor 10.0.0.4 additional-paths receive
 exit-address-family
!
clear ip bgp * soft
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Per-neighbor add-paths (all iBGP peers)
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 advertise additional-paths best 2
  neighbor 10.0.0.1 additional-paths receive
  neighbor 10.0.0.2 advertise additional-paths best 2
  neighbor 10.0.0.2 additional-paths receive
  neighbor 10.0.0.3 advertise additional-paths best 2
  neighbor 10.0.0.3 additional-paths receive
 exit-address-family
!
clear ip bgp * soft
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

### Ticket 1 — R2 Shows Only One Path Despite Add-Paths Configured

After configuring add-paths and soft-clearing sessions, R2's BGP table for 192.0.2.0/24 still shows only one installed path. All BGP sessions are up and the global `bgp additional-paths install` is present on R2, but the expected second path via R3 is missing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 192.0.2.0` on R2 shows two paths (paths available: 2). `show ip cef 192.0.2.0 detail` shows a backup next-hop.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp 192.0.2.0` on R2 — only one path (via R1) is in the table.
2. Run `show ip bgp neighbors 10.0.0.3 | include additional-paths` — the add-paths capability is not shown in the output. The capability negotiation failed.
3. Run `show running-config | section router bgp` on R2 — check the address-family section. The `neighbor 10.0.0.3 additional-paths receive` statement is missing. Only the `advertise additional-paths best 2` command is present.
4. Run the same check on R3 — R3 has `advertise additional-paths best 2` toward R2 but also missing `additional-paths receive`. Neither side can accept additional paths from the other.
5. Root cause: The `additional-paths receive` clause was omitted on the R2↔R3 iBGP session. Without it, the add-paths capability is not negotiated between these peers, and R3 only advertises its best path (via eBGP from R5) to R2.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, add the missing `additional-paths receive` for neighbor 10.0.0.3:

```bash
! On R2
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.3 additional-paths receive
 exit-address-family
!
clear ip bgp 10.0.0.3 soft in
```

Also check and fix R3 if needed:

```bash
! On R3
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.2 additional-paths receive
 exit-address-family
!
clear ip bgp 10.0.0.2 soft in
```

After 30 seconds, run `show ip bgp 192.0.2.0` on R2 — two paths should now appear. Verify with `show ip cef 192.0.2.0 detail` that the backup next-hop is installed.

</details>

---

### Ticket 2 — CEF Shows No Backup Path Despite Two BGP Paths

The NOC monitoring dashboard shows that R2 has two paths in the BGP table for 192.0.2.0/24, but CEF only shows a single next-hop — the backup is missing from the forwarding table. PIC is supposed to pre-install the backup in FIB.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip cef 192.0.2.0 detail` on R2 shows a `backup` next-hop entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp 192.0.2.0` on R2 — two paths are present (one best, one second). Path IDs are non-zero, confirming add-paths is working.
2. Run `show ip cef 192.0.2.0 detail` on R2 — only one recursive next-hop, no `backup` keyword.
3. Run `show running-config | section router bgp` on R2 — the global commands `bgp additional-paths install` and `bgp recursion host` are present, but `bgp additional-paths select backup` is **missing**.
4. Root cause: `bgp additional-paths select backup` was removed or never added. Without this command, IOS installs multiple paths in the BGP RIB but does not select one as a PIC backup for FIB installation. The second path is purely informational in the BGP table.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, add the missing `select backup` directive:

```bash
! On R2
router bgp 65100
 bgp additional-paths select backup
```

No BGP session reset is needed — this is a local decision affecting FIB installation only. After the command takes effect (a few seconds), run `show ip cef 192.0.2.0 detail` and confirm the backup next-hop now appears.

</details>

---

### Ticket 3 — R4 Has No Add-Paths Capability With R1

An audit reveals that R4's iBGP session with R1 is not exchanging additional paths. All other sessions in the mesh are working correctly — only R4↔R1 is affected. R4's BGP table for 192.0.2.0/24 shows one path.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.0.0.1 | include additional-paths` on R4 shows the capability is negotiated. `show ip bgp 192.0.2.0` on R4 shows two paths.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp 192.0.2.0` on R4 — only one path is installed. The path IDs are 0 (no add-paths).
2. Run `show ip bgp neighbors 10.0.0.1 | include additional-paths` on R4 — add-paths capability is not listed.
3. Run `show running-config | section router bgp` on R4 — the global `bgp additional-paths install` and `bgp additional-paths select backup` are present. Check under `address-family ipv4` — the `neighbor 10.0.0.1 advertise additional-paths best 2` and `neighbor 10.0.0.1 additional-paths receive` commands are **missing**. All other iBGP neighbors have them.
4. Root cause: The add-paths per-neighbor configuration was applied to R4's sessions with R2 and R3, but the R1 session was accidentally omitted. This is a common mistake in full-mesh configurations where one session is overlooked during a bulk configuration push.

</details>

<details>
<summary>Click to view Fix</summary>

On R4, add the missing add-paths configuration for neighbor 10.0.0.1:

```bash
! On R4
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 advertise additional-paths best 2
  neighbor 10.0.0.1 additional-paths receive
 exit-address-family
!
clear ip bgp 10.0.0.1 soft
```

Also check R1 to ensure it has the reciprocal configuration for R4:

```bash
! On R1 (if missing)
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.4 advertise additional-paths best 2
  neighbor 10.0.0.4 additional-paths receive
 exit-address-family
!
clear ip bgp 10.0.0.4 soft
```

After the sessions re-establish, verify with `show ip bgp 192.0.2.0` on R4 — two paths should now appear.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Pre-PIC baseline observed: `show ip bgp 192.0.2.0` on R2/R4 shows exactly one path (Task 1)
- [ ] Global add-paths enabled on R1–R4: `show run | section router bgp` includes `bgp additional-paths install`, `bgp additional-paths select backup`, and `bgp recursion host` (Task 2)
- [ ] Add-paths configured per-neighbor on all iBGP sessions: both `advertise additional-paths best 2` and `additional-paths receive` present for every iBGP peer on every router (Task 3)
- [ ] BGP sessions soft-cleared after configuration; two paths visible for 192.0.2.0/24 on R2: `show ip bgp 192.0.2.0` shows `Paths: (2 available)` (Task 3)
- [ ] PIC backup confirmed in CEF: `show ip cef 192.0.2.0 detail` on R2 shows `recursive via X, backup` (Task 4)
- [ ] PIC edge failure test: R1 Gi4 shutdown causes ≤ 3 ping drops from R2 to 192.0.2.1 (Task 5)
- [ ] PIC core failure test: R1 Loopback0 IS-IS removal causes ≤ 5 ping drops from R2 to 192.0.2.1 (Task 6)
- [ ] Add-paths path identifier inspection: path IDs documented for each iBGP session (Task 7)

### Troubleshooting

- [ ] Ticket 1: Missing `additional-paths receive` on R2↔R3 identified and restored; two paths now in BGP table
- [ ] Ticket 2: Missing `bgp additional-paths select backup` on R2 identified and restored; backup now in CEF
- [ ] Ticket 3: Missing add-paths config on R4↔R1 session identified and restored; R4 now has two paths

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
