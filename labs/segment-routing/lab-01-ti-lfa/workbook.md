# Lab 01 — Topology-Independent Loop-Free Alternate (TI-LFA)

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

**Exam Objective:** 4.2.c (TI-LFA) — CCNP SPRI 300-510

Topology-Independent Loop-Free Alternate (TI-LFA) is the Segment Routing native fast-reroute mechanism. It extends classic LFA by using an SR label stack to encode a post-convergence repair path that can bypass any single link or node failure with 100% topological coverage — a guarantee that classic LFA cannot provide because LFA requires a direct loop-free alternate neighbor, which may not exist for every destination.

### What Is TI-LFA?

TI-LFA runs as part of the IS-IS SPF computation on each router (the PLR — Point of Local Repair). For each protected link or node, the PLR:

1. Removes the protected element from the topology.
2. Runs a second SPF over the post-convergence graph.
3. Computes a repair label stack that steers traffic along the post-convergence path, bypassing the failure.
4. Pre-installs the repair entry in the hardware FIB *before* any failure occurs.

When a BFD session or IS-IS hello times out, the local FRR engine flips the forwarding entry from primary to repair in hardware — typically within 50ms — without waiting for IGP reconvergence.

### P-Nodes, Q-Nodes, and PQ-Nodes

TI-LFA classifies intermediate nodes by their relationship to the failing element:

**P-node** — reachable from the PLR without using the protected link/node.

**Q-node** — can reach the destination without passing through the protected link/node from the destination side.

**PQ-node** — a single node that is both P and Q. When a PQ-node exists adjacent to the destination, the repair label stack contains only one additional SID.

Example in this lab topology — protecting L2 (R2↔R3):

```
   Protected link: L2 (R2 ─── R3)
   PLR: R2

   Post-convergence path:  R2 → R1 (via L1) → R3 (via L5)

   R1 is a P-node: reachable from R2 via L1, not through L2.
   R1 is a Q-node: can reach R3 via L5, not through L2.
   Therefore R1 is the PQ-node.

   Repair label stack on R2 for 10.0.0.3/32: {16003}
     R1 is the immediate next-hop (adjacent on L1), so no outer steering label needed.
     R2 imposes only 16003; R1 forwards it to R3 via L5 (post-convergence path).
     A two-label stack {16001, 16003} would only be required if R1 were non-adjacent.
```

### The Role of the Diagonal (L5)

The L5 link (R1↔R3, Gi0/0/0/2 on both ends) is the key enabler of TI-LFA coverage in this topology. Without L5:

- For L2 (R2↔R3) failure: post-convergence path must go R2→R1→R4→R3 (three hops). R4 becomes the PQ-node; repair stack grows to two labels.
- For L1 (R1↔R2) failure from R2's side: no link-disjoint path to some destinations exists without the diagonal, meaning classic LFA would fail but TI-LFA would still compute a label-stack repair via R4.

With L5 present, every single-link failure in this topology has a short (one or two label) TI-LFA repair path.

### TI-LFA vs. Classic Per-Prefix LFA

| Feature | Classic LFA (RFC 5286) | TI-LFA |
|---------|----------------------|--------|
| Coverage | Topology-dependent; may be 0% for some destinations | 100% for any single link or node failure |
| Repair path encoding | Direct next-hop only | SR label stack (arbitrary path) |
| Configuration | `fast-reroute per-prefix` | `fast-reroute per-prefix ti-lfa` |
| Failure detection | IS-IS hello hold-down (default 30s) | BFD sub-50ms |
| Hardware pre-installation | Depends on platform | Yes — FIB swap happens locally |

### IOS-XR TI-LFA Configuration Structure

TI-LFA is enabled per-interface under IS-IS. The BFD config lives at the IS-IS interface level (not the global interface level):

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  bfd minimum-interval 50            ! BFD hello interval (ms)
  bfd multiplier 3                   ! BFD failure multiplier (3 × 50 = 150ms detect time)
  address-family ipv4 unicast
   fast-reroute per-prefix           ! enables FRR engine
   fast-reroute per-prefix ti-lfa   ! elevates to TI-LFA (label-stack repair)
  !
 !
!
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| TI-LFA configuration | Enabling and verifying per-prefix TI-LFA on all core interfaces |
| P/PQ-node analysis | Identifying repair nodes from the post-convergence SPF graph |
| Repair label stack reading | Interpreting `show isis fast-reroute` label stacks |
| BFD integration | Configuring BFD for sub-50ms failure detection with TI-LFA |
| FRR coverage analysis | Comparing TI-LFA vs. classic LFA coverage gaps |
| Topology impact | Understanding how the L5 diagonal affects FRR path diversity |

---

## 2. Topology & Scenario

### Scenario

You are the SP core engineer responsible for adding fast-reroute protection to the four-router IS-IS/SR-MPLS core. Lab-00 established the IS-IS Level 2 adjacencies and the SR label plane (prefix SIDs 16001–16004). In production this core carries customer traffic that cannot tolerate multi-second outages from IGP reconvergence.

Your task is to enable TI-LFA on every core link, verify that every prefix has a pre-programmed repair path, and configure BFD so that a link failure is detected within 150ms rather than waiting for the 30-second IS-IS hello holddown.

### Topology

```
                IS-IS Level 2  •  SR-MPLS  •  TI-LFA  •  BFD 50ms  •  SRGB 16000-23999

   ┌───────────────────────────┐    L1 — 10.1.12.0/24    ┌───────────────────────────┐
   │             R1            │  Gi0/0/0/0 ══ Gi0/0/0/0 │             R2            │
   │ Lo0       10.0.0.1/32     ├═════════════════════════┤ Lo0       10.0.0.2/32     │
   │ NET   49.0001..0001.00    │                         │ NET   49.0001..0002.00    │
   │ Prefix-SID  idx 1 → 16001 │                         │ Prefix-SID  idx 2 → 16002 │
   │ Gi0/0/0/1 → R4 (L4)       │                         │ Gi0/0/0/1 → R3 (L2)       │
   │ Gi0/0/0/2 → R3 (L5)       │                         │                           │
   └──────────────┬────────────┘                         └────────────┬──────────────┘
                  ║                                                   ║
                  ║                                                   ║
            L4    ║                                             L2    ║
       10.1.14.0/24                                       10.1.23.0/24
                  ║                                                   ║
                  ║                                                   ║
   ┌──────────────┴────────────┐    L3 — 10.1.34.0/24    ┌────────────┴──────────────┐
   │             R4            │  Gi0/0/0/0 ══ Gi0/0/0/1 │             R3            │
   │ Lo0       10.0.0.4/32     ├═════════════════════════┤ Lo0       10.0.0.3/32     │
   │ NET   49.0001..0004.00    │                         │ NET   49.0001..0003.00    │
   │ Prefix-SID  idx 4 → 16004 │                         │ Prefix-SID  idx 3 → 16003 │
   │ Gi0/0/0/1 → R1 (L4)       │                         │ Gi0/0/0/2 → R1 (L5)       │
   └───────────────────────────┘                         └───────────────────────────┘

         L5 (R1↔R3 diagonal) — 10.1.13.0/24 — Gi0/0/0/2 ⇄ Gi0/0/0/2
              not drawn above; declared on each box's interface list.
```

Square ring R1↔R2↔R3↔R4↔R1 (links L1–L4) plus the L5 diagonal (R1↔R3). TI-LFA
uses L5 as the key link-disjoint alternate: when L2 (R2↔R3) fails, R2's repair
path is R2→R1 (L1) → R3 (L5). Without L5, that repair would require an extra hop
through R4, growing the label stack. Five IS-IS L2 adjacencies, all TI-LFA
protected.

| Router | Loopback0 | IS-IS NET | Prefix SID | SR Label |
|--------|-----------|-----------|------------|----------|
| R1 | 10.0.0.1/32 | 49.0001.0000.0000.0001.00 | index 1 | 16001 |
| R2 | 10.0.0.2/32 | 49.0001.0000.0000.0002.00 | index 2 | 16002 |
| R3 | 10.0.0.3/32 | 49.0001.0000.0000.0003.00 | index 3 | 16003 |
| R4 | 10.0.0.4/32 | 49.0001.0000.0000.0004.00 | index 4 | 16004 |

| Link | Endpoints | Subnet | Local Intf (LHS) | Remote Intf (RHS) |
|------|-----------|--------|------------------|--------------------|
| L1 | R1 ↔ R2 | 10.1.12.0/24 | R1 Gi0/0/0/0 | R2 Gi0/0/0/0 |
| L2 | R2 ↔ R3 | 10.1.23.0/24 | R2 Gi0/0/0/1 | R3 Gi0/0/0/0 |
| L3 | R3 ↔ R4 | 10.1.34.0/24 | R3 Gi0/0/0/1 | R4 Gi0/0/0/0 |
| L4 | R1 ↔ R4 | 10.1.14.0/24 | R1 Gi0/0/0/1 | R4 Gi0/0/0/1 |
| L5 | R1 ↔ R3 | 10.1.13.0/24 | R1 Gi0/0/0/2 | R3 Gi0/0/0/2 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP edge / SR ingress / TI-LFA PLR | IOS-XRv (classic) | xrvr-os-mbi-6.3.1 |
| R2 | SP core / TI-LFA PLR | IOS-XRv (classic) | xrvr-os-mbi-6.3.1 |
| R3 | SP edge / SR egress / TI-LFA PLR | IOS-XRv (classic) | xrvr-os-mbi-6.3.1 |
| R4 | SP core / TI-LFA alternate-path router | IOS-XRv (classic) | xrvr-os-mbi-6.3.1 |

> **Platform note:** These nodes run classic IOS-XRv 6.3.1 (software forwarding, 3 GB RAM).
> All TI-LFA and SR features work correctly. BFD sub-50ms sessions do not form on this
> virtual platform — use `show isis adjacency detail` to verify TI-LFA protection instead.
> Commands have been verified against the actual running platform.

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, prefix SID 16001, BGP source (lab-03+) |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, prefix SID 16002 |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, prefix SID 16003, BGP source (lab-03+) |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, prefix SID 16004 |

### Cabling Table

| Link | Source Device | Source Interface | Dest Device | Dest Interface | Subnet |
|------|--------------|-----------------|-------------|----------------|--------|
| L1 | R1 | Gi0/0/0/0 | R2 | Gi0/0/0/0 | 10.1.12.0/24 |
| L2 | R2 | Gi0/0/0/1 | R3 | Gi0/0/0/0 | 10.1.23.0/24 |
| L3 | R3 | Gi0/0/0/1 | R4 | Gi0/0/0/0 | 10.1.34.0/24 |
| L4 | R1 | Gi0/0/0/1 | R4 | Gi0/0/0/1 | 10.1.14.0/24 |
| L5 | R1 | Gi0/0/0/2 | R3 | Gi0/0/0/2 | 10.1.13.0/24 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Ports are assigned dynamically by EVE-NG. Run `setup_lab.py --host <ip>` to push
initial configs — it uses the EVE-NG REST API to discover ports automatically.

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py` (from `initial-configs/`):

**IS pre-loaded:**
- Hostnames on all routers
- Interface IP addressing (all routed links L1–L5 and loopbacks)
- SRGB declaration (`segment-routing global-block 16000 23999`)
- IS-IS Level 2 process with `metric-style wide` and `segment-routing mpls`
- Per-node prefix SIDs on Loopback0 (index 1 through 4)
- IS-IS adjacencies on all five core links (L1–L5), loopbacks passive
- SR labels 16001–16004 installed in the LFIB on every router

**IS NOT pre-loaded** (student configures this):
- TI-LFA fast-reroute per-prefix (classic LFA)
- TI-LFA label-stack repair extension
- BFD sessions for sub-50ms failure detection
- BFD fast-detect integration with IS-IS

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable TI-LFA on All Core Interfaces

- On every core router (R1, R2, R3, R4), enable the FRR engine and TI-LFA extension under IS-IS for each core-facing interface (all GigabitEthernet interfaces participating in IS-IS). Do NOT enable on Loopback0 (passive).
- Both the base per-prefix FRR knob and the TI-LFA extension knob must be configured per-interface under the IS-IS IPv4 unicast address-family.
- Interfaces: R1 (3 core interfaces), R2 (2), R3 (3), R4 (2).

**Verification:** `show isis fast-reroute summary` on any router must show TI-LFA enabled on all core interfaces with protected prefixes > 0.

---

### Task 2: Inspect the TI-LFA Backup Topology

- On R2, display the full per-prefix FRR topology table for IPv4 unicast. For each destination prefix, identify: primary next-hop, backup next-hop, and the repair label stack.
- Confirm that every destination has a backup path (0 prefixes without backup).
- Identify which destination has the shortest repair label stack (R2 is directly adjacent, so PHP applies) and which has the longest.

**Verification:** `show isis fast-reroute detail` on R2 — every prefix must show a non-empty FRR backup entry.

---

### Task 3: Analyze the Repair Path for R3's Loopback

- From R2's perspective, identify the primary and backup next-hop for destination 10.0.0.3/32 (R3's loopback).
- Determine which router is the PQ-node for the L2 (R2↔R3) failure scenario and explain why.
- Confirm the repair label stack and explain what each label in the stack does.

**Verification:** `show isis fast-reroute detail 10.0.0.3/32` on R2 — must show primary via Gi0/0/0/1 (L2) and FRR backup via Gi0/0/0/0 (L1→R1) with repair label 16003.

---

### Task 4: Enable BFD for Sub-50ms Failure Detection

- Configure BFD on all core IS-IS interfaces (R1, R2, R3, R4) with a 50ms hello interval and a multiplier of 3. This gives a 150ms failure detection time.
- Integrate BFD with IS-IS fast-detect so that a BFD session failure triggers the TI-LFA repair immediately rather than waiting for the IS-IS hello holddown.
- Demonstrate sub-50ms failover: start a sustained ping from R2 loopback (10.0.0.2) sourced to R3 loopback (10.0.0.3), then administratively shut L2 (R3's Gi0/0/0/0). Count the number of dropped packets — with TI-LFA and BFD, at most one or two packets should be lost.

**Verification:** `show bfd session` on R2 must show active BFD sessions toward both R1 (via L1) and R3 (via L2) with negotiated interval 50ms.

---

### Task 5: Compare TI-LFA vs. Classic LFA Coverage

- On R2's Gi0/0/0/0 (L1), temporarily remove the TI-LFA extension (keep the base per-prefix FRR but remove the TI-LFA knob).
- Run `show isis fast-reroute summary` and `show isis fast-reroute detail`. Note: because L5 (the R1↔R3 diagonal) gives every prefix a classic loop-free alternate in this topology, coverage stays at 100% even without TI-LFA. This is by design — L5 is what makes TI-LFA's repair paths one-label rather than two.
- The observable difference is in `show isis fast-reroute detail` flag changes: with TI-LFA, some entries show NP/D attributes indicating node-protecting and downstream-disjoint paths; classic LFA does not guarantee these stronger protection properties.
- Restore TI-LFA and verify `show isis fast-reroute detail` returns to full TI-LFA flag coverage.

**Verification:** `show isis fast-reroute summary` shows 100% in both states (expected). `show isis fast-reroute detail` is the differentiator — compare backup path flags before and after restoring TI-LFA.

---

## 6. Verification & Analysis

### Task 1 — TI-LFA Enabled

```
RP/0/0/CPU0:R2# show isis fast-reroute summary

IS-IS CORE IPv4 Unicast FRR summary

                          Critical   High       Medium     Low        Total
                          Priority   Priority   Priority   Priority
Prefixes reachable in L2
  All paths protected     0          0          3          5          8    ! ← 8 total, all protected
  Some paths protected    0          0          0          0          0
  Unprotected             0          0          0          0          0    ! ← must be 0
  Protection coverage     0.00%      0.00%      100.00%    100.00%    100.00%
```

> **What to verify:** The "Unprotected" row is all zeros and "Total" All paths protected = 8.
> Critical/High show 0.00% because IS-IS assigns loopbacks/links to Medium and Low priority
> by default — 0.00% on Critical/High is expected and correct (no critical-priority prefixes).

### Task 2 — Per-Prefix FRR Topology

```
RP/0/0/CPU0:R2# show isis fast-reroute detail
Wed May 13 07:48:15.210 UTC

IS-IS CORE IPv4 Unicast FRR backups

Codes: D - Downstream, LC - Line card disjoint, NP - Node protecting
       P - Primary path, SRLG - SRLG disjoint, TM - Total metric via backup

L2 10.0.0.1/32 [10/115] medium priority
     via 10.1.12.1, GigabitEthernet0/0/0/0, R1, SRGB Base: 16000, Weight: 0
       FRR backup via 10.1.23.3, GigabitEthernet0/0/0/1, R3, SRGB Base: 16000, Weight: 0, Metric: 20
       P: No, TM: 20, LC: No, NP: No, D: No, SRLG: Yes
L2 10.0.0.3/32 [10/115] medium priority           ! ← backup via R1 (Gi0/0/0/0)
     via 10.1.23.3, GigabitEthernet0/0/0/1, R3, SRGB Base: 16000, Weight: 0
       FRR backup via 10.1.12.1, GigabitEthernet0/0/0/0, R1, SRGB Base: 16000, Weight: 0, Metric: 20
       P: No, TM: 20, LC: No, NP: No, D: No, SRLG: Yes
L2 10.0.0.4/32 [20/115] medium priority           ! ← two equal-cost paths, each backs up the other
     via 10.1.23.3, GigabitEthernet0/0/0/1, R3, ...
       FRR backup via 10.1.12.1, GigabitEthernet0/0/0/0, R1, ...
     via 10.1.12.1, GigabitEthernet0/0/0/0, R1, ...
       FRR backup via 10.1.23.3, GigabitEthernet0/0/0/1, R3, ...
! ... link subnets follow, all showing FRR backup entries ...
```

### Task 3 — Repair Label Stack for 10.0.0.3/32

```
RP/0/0/CPU0:R2# show isis fast-reroute detail 10.0.0.3/32
Wed May 13 07:48:15.500 UTC

L2 10.0.0.3/32 [10/115] medium priority
     via 10.1.23.3, GigabitEthernet0/0/0/1, R3, SRGB Base: 16000, Weight: 0
       FRR backup via 10.1.12.1, GigabitEthernet0/0/0/0, R1, SRGB Base: 16000, Weight: 0, Metric: 20
       P: No, TM: 20, LC: No, NP: No, D: No, SRLG: Yes

RP/0/0/CPU0:R2# show mpls forwarding prefix 10.0.0.3/32 detail
! Primary:  Pop  via Gi0/0/0/1 (R3 via L2)   Label Stack: { Imp-Null }  (PHP)
! Backup:   16003 via Gi0/0/0/0 (R1 via L1)  Label Stack: { 16003 }     ! ← repair label
! (!) marks the FRR pure backup entry

RP/0/0/CPU0:R2# show route ipv4 10.0.0.3/32 detail
  10.1.12.1, via GigabitEthernet0/0/0/0, Backup (Local-LFA)
    Label: 16003                                   ! ← R1 forwards 16003 to R3 via L5
  10.1.23.3, via GigabitEthernet0/0/0/1, Protected ! ← primary via L2

Explanation:
  R1 is the PQ-node and is R2's immediate neighbor (adjacent on L1).
  Because R1 is the next-hop, no outer steering label (16001) is needed.
  R2 imposes only label 16003 on the backup path via Gi0/0/0/0.
  R1 receives label 16003 and routes it to R3 via L5 (post-convergence path).
  R3 pops 16003 (implicit-null / PHP), delivers native IP.
  Repair label stack = { 16003 }  (one label; R1 is adjacent PQ-node)
```

### Task 4 — BFD Sessions

> **Platform note:** On classic XRv 6.3.1 (the image actually running in this EVE-NG lab),
> BFD sessions for IS-IS do not form even when correctly configured. This is a software
> forwarding limitation of the classic XRv platform — BFD sub-50ms hardware timers require
> XRv9k or physical hardware. The BFD configuration commands are still correct and exam-relevant;
> verify TI-LFA protection via `show isis adjacency detail` instead, which shows Adjacency SID
> protection status independently of BFD.

```
RP/0/0/CPU0:R2# show bfd session
! On XRv 6.3.1: output will be empty (BFD sessions don't form on classic XRv).
! On XRv9k / physical hardware the expected output is:
!   Interface           Dest Addr           Local det time(int*mult)  State
!   Gi0/0/0/0           10.1.12.1           150ms(50ms*3)             Up    ← R1 via L1
!   Gi0/0/0/1           10.1.23.3           150ms(50ms*3)             Up    ← R3 via L2

RP/0/0/CPU0:R2# show isis adjacency detail
! Use this instead — confirms TI-LFA protection is active via Adjacency SIDs:

IS-IS CORE Level-2 adjacencies:
R1  Gi0/0/0/0  *PtoP*  Up  28  00:32:18 Yes None None
  Adjacency SID:  24000 (protected)                  ! ← (protected) = TI-LFA backup pre-installed
   Backup label stack:    [16001]                    ! ← repair label for this adjacency
   Backup interface:      Gi0/0/0/1
   Backup nexthop:        10.1.23.3
R3  Gi0/0/0/1  *PtoP*  Up  29  00:28:27 Yes None None
  Adjacency SID:  24002 (protected)
   Backup label stack:    [16003]
   Backup interface:      Gi0/0/0/0
   Backup nexthop:        10.1.12.1
```

### Task 5 — Coverage Drop Without ti-lfa

> **Note:** In this topology, the L5 diagonal (R1↔R3) means every prefix already has a
> classic loop-free alternate neighbor, so `show isis fast-reroute summary` stays at 100%
> coverage even after removing TI-LFA from Gi0/0/0/0. The coverage-drop effect requires
> a topology without complete LFA coverage (e.g., a simple ring without L5). The value of
> this task is observing that backup paths still exist under classic LFA, then confirming
> TI-LFA restores the extended repair capabilities (node-protecting, arbitrary label stack).

```
RP/0/0/CPU0:R2# show isis fast-reroute summary
! (after removing fast-reroute per-prefix ti-lfa from Gi0/0/0/0 — classic LFA only)

IS-IS CORE IPv4 Unicast FRR summary

                          Critical   High       Medium     Low        Total
                          Priority   Priority   Priority   Priority
Prefixes reachable in L2
  All paths protected     0          0          3          5          8    ! ← still 100%; L5 provides classic LFA
  Some paths protected    0          0          0          0          0
  Unprotected             0          0          0          0          0
  Protection coverage     0.00%      0.00%      100.00%    100.00%    100.00%

! Re-enable TI-LFA, then verify summary is identical (coverage was never lost):
! The key difference is in 'show isis fast-reroute detail' — TI-LFA provides
! node-protecting (NP: Yes) and downstream-disjoint (D: Yes) backup paths
! that classic LFA cannot guarantee.
```

---

## 7. Verification Cheatsheet

### TI-LFA Configuration

```
router isis CORE
 interface GigabitEthernet0/0/0/X
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
```

| Command | Purpose |
|---------|---------|
| `fast-reroute per-prefix` | Enables the IS-IS FRR engine for this interface |
| `fast-reroute per-prefix ti-lfa` | Elevates to TI-LFA (label-stack repair paths) |
| `bfd minimum-interval 50` | BFD hello every 50ms (IS-IS interface level) |
| `bfd multiplier 3` | Declare failure after 3 missed hellos = 150ms; enabling both is sufficient to activate BFD under IS-IS |

> **Exam tip:** Both `fast-reroute per-prefix` AND `fast-reroute per-prefix ti-lfa` must be configured. The second line alone is not sufficient — IOS-XR requires the base FRR knob to be present before the TI-LFA extension is accepted.

### TI-LFA Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis fast-reroute summary` | TI-LFA enabled on all interfaces; 100% coverage |
| `show isis fast-reroute detail` | Every prefix has a non-empty FRR backup entry |
| `show isis fast-reroute detail <prefix>` | Primary NH and FRR backup NH for a specific prefix |
| `show mpls forwarding prefix <prefix> detail` | Repair label stack under the `(!)` backup entry |
| `show route ipv4 <prefix> detail` | Backup path with imposed label; confirms backup NH |
| `show bfd session` | BFD sessions Up with 150ms detect time (XRv9k/hardware only; empty on classic XRv 6.3.1) |
| `show isis adjacency detail` | Adjacency SID shows `(protected)` with backup label stack — works on all XR platforms |
| `show isis segment-routing label table` | SR label bindings still intact (not TI-LFA-specific) |
| `show mpls forwarding` | FRR next-hop column shows backup NH installed |

> **Exam tip (IOS-XR):** `show isis fast-reroute detail` and `show isis fast-reroute summary` are the primary diagnostic commands for TI-LFA. The former gives per-prefix backup detail; the latter gives coverage percentages by priority. The `topology` subcommand does not exist on IOS-XR — use `detail` instead. On classic XRv 6.3.1, use `show isis adjacency detail` to confirm TI-LFA protection (BFD sessions won't form on that platform).

### BFD Quick Reference

```
! Enable BFD for IS-IS interface (under router isis, NOT global interface):
router isis CORE
 interface GigabitEthernet0/0/0/X
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
```

| Command | What to Look For |
|---------|-----------------|
| `show bfd session` | State = Up; interval = 50ms; multiplier = 3 (XRv9k/hardware only) |
| `show bfd session detail` | Last state change, down reason if not Up |
| `show isis adjacency detail` | Adjacency SID `(protected)` + backup label/interface — use on XRv 6.3.1 |

### Common TI-LFA Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `fast-reroute per-prefix ti-lfa` rejected by IOS-XR | `fast-reroute per-prefix` (base knob) missing on same interface |
| TI-LFA shows 0% coverage | `segment-routing mpls` missing under IS-IS af — SR labels absent |
| BFD sessions flap | Timer mismatch between endpoints; `bfd minimum-interval` must match on both sides |
| Coverage drops after L5 shut | L5 is the diagonal used as repair path for L2/L3 failures; without it, some repairs require longer label stacks |
| `show isis fast-reroute topology` empty | IS-IS not fully converged, or `fast-reroute per-prefix ti-lfa` not configured on any interface |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 4: TI-LFA + BFD on All Interfaces

<details>
<summary>Click to view R1 Configuration</summary>

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/1
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/2
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/1
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/1
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/2
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
 interface GigabitEthernet0/0/0/1
  bfd minimum-interval 50
  bfd multiplier 3
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show isis fast-reroute summary
show isis fast-reroute detail
show isis fast-reroute detail 10.0.0.3/32
show mpls forwarding prefix 10.0.0.3/32 detail
show bfd session
```
</details>

### Task 5: Temporarily Remove TI-LFA and Restore

<details>
<summary>Click to view Remove TI-LFA (R2 Gi0/0/0/0)</summary>

```
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   no fast-reroute per-prefix ti-lfa
  !
 !
!
commit
! Coverage stays 100% (L5 provides classic LFA for all prefixes in this topology).
! Compare flag differences instead:
show isis fast-reroute summary
show isis fast-reroute detail

! Restore TI-LFA:
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
show isis fast-reroute summary
show isis fast-reroute detail
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

> **Prerequisite:** Complete Section 5 (Enable TI-LFA) on all routers before running any
> fault-injection script. The inject scripts require the solution-state config (TI-LFA + BFD)
> to be present. If you reset with `setup_lab.py`, you will push the initial-configs (no
> TI-LFA), and the inject scripts will exit with a preflight failure.

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # reset to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>         # restore after each
```

---

### Ticket 1 — R2 Reports No Backup Path for Prefix 10.0.0.1/32

The operations team has just completed a maintenance window on R2. After the window, an automated monitoring script reports that TI-LFA coverage on R2 is below 100% — specifically, at least one prefix has no backup path via L1.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show isis fast-reroute summary` on R2 shows 100% TI-LFA coverage on both Gi0/0/0/0 (L1) and Gi0/0/0/1 (L2); `show isis fast-reroute ipv4 10.0.0.1/32` shows a non-empty Repair entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Confirm coverage gap
R2# show isis fast-reroute summary
! Look for Gi0/0/0/0 showing TI-LFA: Disabled or < 100% coverage

! Step 2: Check specific prefix
R2# show isis fast-reroute detail 10.0.0.1/32
! No FRR backup entry visible

! Step 3: Inspect running config for Gi0/0/0/0
R2# show running-config router isis CORE
! Look for missing fast-reroute per-prefix ti-lfa under Gi0/0/0/0 address-family
```
</details>

<details>
<summary>Click to view Fix</summary>

```
! The fault: fast-reroute per-prefix ti-lfa was removed from R2's Gi0/0/0/0 af.
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   fast-reroute per-prefix ti-lfa
  !
 !
!
commit
! Verify:
show isis fast-reroute summary
show isis fast-reroute detail 10.0.0.1/32
```
</details>

---

### Ticket 2 — Link Failure on L2 Takes 30 Seconds to Reconverge

A network operator reports that when L2 (R2↔R3) goes down, traffic to R3 blackholes for approximately 30 seconds before recovering — far longer than the sub-second behavior expected from TI-LFA. The TI-LFA repair paths appear to be correctly installed in `show isis fast-reroute detail`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** After fix, `show running-config router isis CORE` on R2 shows `bfd minimum-interval 50` and `bfd multiplier 3` under Gi0/0/0/1. On XRv9k/hardware: `show bfd session` shows State = Up for Gi0/0/0/1. On classic XRv 6.3.1: BFD sessions won't form (platform limitation), but the config is correct.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Confirm TI-LFA repair paths are present (they are)
R2# show isis fast-reroute detail
! 10.0.0.3/32 shows FRR backup via Gi0/0/0/0 (R1) — repair IS pre-installed

! Step 2: Check BFD sessions
R2# show bfd session
! Gi0/0/0/1 entry is missing or the BFD session is Down

! Step 3: Check IS-IS BFD config
R2# show running-config router isis CORE
! Look under interface GigabitEthernet0/0/0/1 — bfd minimum-interval and
! bfd multiplier are missing. Without these, no BFD session forms.

! Explanation: TI-LFA repairs are installed but the activation trigger is the
! IS-IS hello holddown (default 30s), not BFD. BFD is only active when
! bfd minimum-interval + bfd multiplier are configured at the interface level.
! The repair only fires after IS-IS declares the neighbor down — 30 seconds later.
```
</details>

<details>
<summary>Click to view Fix</summary>

```
! The fault: bfd minimum-interval and bfd multiplier removed from R2 Gi0/0/0/1.
! Without BFD timers, no BFD session forms — failover waits for IS-IS holddown (30s).
router isis CORE
 interface GigabitEthernet0/0/0/1
  bfd minimum-interval 50
  bfd multiplier 3
 !
!
commit
! Verify:
show bfd session
! Gi0/0/0/1 must show State Up, interval 50ms, multiplier 3
```
</details>

---

### Ticket 3 — TI-LFA Coverage Drops After Topology Change

Following a fiber relocation project, `show isis fast-reroute summary` on R2 suddenly shows that some prefixes no longer have a backup path via their expected interface. The FRR table has changed significantly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** After fix, `show isis fast-reroute summary` on all routers returns to 100% TI-LFA coverage on all interfaces; `show isis adjacency` shows 5 adjacencies domain-wide.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Observe coverage change
R2# show isis fast-reroute summary
! One or more interfaces show < 100% coverage or "No backup" for some prefixes

! Step 2: Count IS-IS adjacencies
R1# show isis adjacency
! Fewer than 5 adjacencies — one adjacency is missing

! Step 3: Find the missing adjacency
R1# show isis interface GigabitEthernet0/0/0/2
! L5 (Gi0/0/0/2) is admin down or IS-IS is not active on it

! Step 4: Confirm physical state
R1# show interfaces GigabitEthernet0/0/0/2
! Line protocol down — interface has been shut

! Explanation: L5 is the key diagonal used as the repair path for L2/L3
! failures. Without L5, the PQ-node for some repair paths must be R4
! instead of R1, requiring longer or unavailable label stacks.
```
</details>

<details>
<summary>Click to view Fix</summary>

```
! The fault: R1's Gi0/0/0/2 (L5) was shut administratively.
interface GigabitEthernet0/0/0/2
 no shutdown
!
commit
! Verify L5 adjacency restored:
show isis adjacency
! 5 adjacencies must be present
! Verify TI-LFA coverage restored:
show isis fast-reroute summary
! 100% on all interfaces
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] TI-LFA enabled on all core IS-IS interfaces on R1, R2, R3, R4
- [ ] `show isis fast-reroute summary` shows 100% TI-LFA coverage on all interfaces on all routers
- [ ] `show isis fast-reroute detail` on R2 shows a non-empty FRR backup entry for every prefix
- [ ] `show isis fast-reroute detail 10.0.0.3/32` on R2 shows FRR backup via Gi0/0/0/0 (R1); `show mpls forwarding prefix 10.0.0.3/32 detail` shows backup label stack `{ 16003 }`
- [ ] BFD sessions configured (`bfd minimum-interval 50` + `bfd multiplier 3`) on all core IS-IS interfaces
- [ ] BFD config verified in `show run router isis CORE` (sessions Up only on XRv9k/hardware; empty on classic XRv 6.3.1)
- [ ] `show isis adjacency detail` on R2 shows Adjacency SIDs as `(protected)` with backup label stacks
- [ ] Classic LFA vs. TI-LFA compared: coverage stays 100% in both states (L5 ensures classic LFA works); flag differences in `show isis fast-reroute detail` observed (NP/D attributes)

### Troubleshooting

- [ ] Ticket 1: TI-LFA coverage gap (missing `ti-lfa` on Gi0/0/0/0) identified and fixed
- [ ] Ticket 2: Slow failover (missing BFD timers on interface) identified and fixed
- [ ] Ticket 3: Coverage drop (L5 diagonal shut) identified and fixed
- [ ] `apply_solution.py` run after each ticket to restore lab to known-good state

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
