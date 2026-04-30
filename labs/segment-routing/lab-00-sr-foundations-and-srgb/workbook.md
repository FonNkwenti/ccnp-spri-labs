# Segment Routing Lab 00: SR-MPLS Foundations, SRGB, and Prefix SIDs

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

**Exam Objective:** 4.2, 4.2.a (IS-IS SR extensions), 4.2.b (SRGB and SRLB) — CCNP SPRI 300-510

Segment Routing MPLS (SR-MPLS) replaces per-hop LDP label distribution with a topology-sourced label plane: the IGP itself carries label assignments as extensions to existing routing TLVs. Every router knows every other router's prefix labels directly from the IGP database — no targeted LDP sessions, no separate label distribution protocol. This lab establishes the foundational SR control plane that every subsequent lab in this topic builds on.

### The Segment Routing Label Plane

Three label ranges govern how SR allocates MPLS labels:

**Segment Routing Global Block (SRGB)** — a contiguous label range reserved on every router in the SR domain. Cisco IOS-XR defaults to 16000–23999 (8000 labels). Every router in the domain SHOULD use the same SRGB so that prefix SID labels are globally consistent. A prefix SID of index *N* maps to label `SRGB_start + N` on every router; there is no per-router negotiation.

**Prefix SID** — an index assigned to a specific prefix (typically a router's loopback) within the SRGB. When R1 advertises prefix SID index 1 for 10.0.0.1/32, every other router installs label `16000 + 1 = 16001` pointing toward R1. The label is globally unambiguous — any router in the SR domain can push label 16001 to reach R1, regardless of physical path.

**Segment Routing Local Block (SRLB)** — a per-node label range for locally-significant adjacency SIDs (adj-SIDs). The default SRLB on IOS-XR is 15000–15999. Unlike the SRGB, SRLB labels are not globally meaningful — they only have significance on the node that advertises them. Adj-SIDs are assigned automatically once SR is enabled; you do not configure them per-interface.

### SR-MPLS vs. LDP

| Property | LDP | SR-MPLS |
|----------|-----|---------|
| Label distribution | Targeted/link-local LDP sessions | IGP extensions (IS-IS TLV 135 sub-TLVs) |
| Per-hop state | Per-FEC bindings on every LSR | Computed from IGP database |
| FRR (local protection) | LFA / U-turn (gaps possible) | TI-LFA (100% topology-independent) |
| Label significance | Locally significant, swap each hop | Globally significant within SRGB |
| Migration | Lab-02 introduces `sr-prefer` and mapping server | — |

### IS-IS SR Extensions

IS-IS carries SR prefix SIDs as sub-TLVs inside **Extended IP Reachability TLV 135**. Two prerequisites:

1. **`metric-style wide`** — narrow (legacy) IS-IS TLVs cannot carry SR sub-TLVs at all. Without wide metrics, the SR sub-TLV is never originated; SR silently does not work.
2. **`segment-routing mpls`** under the IS-IS IPv4 address-family — activates SR in IS-IS and instructs the router to originate and process SR sub-TLVs.

### IOS-XR Configuration Structure

On IOS-XR, SR configuration spans two locations — they look unrelated but must both be present:

```
segment-routing
 global-block 16000 23999            ! SRGB definition (TOP-LEVEL, not under mpls)
!

router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 address-family ipv4 unicast
  metric-style wide
  segment-routing mpls               ! activates SR extensions in IS-IS
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
   prefix-sid index 1                ! assigns this loopback's prefix SID
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
 !
!
```

The `segment-routing global-block` command is a **top-level IOS-XR config block** — not nested under `mpls`, `router isis`, or any other subsystem. New IOS-XR operators frequently search for it under the MPLS subsystem (where IOS-XE puts a similar knob); on IOS-XR it lives at the top.

---

## 2. Topology & Scenario

### Scenario

You are bringing up the Segment Routing control plane for a four-router service provider core. The routers run IOS-XRv 9000 in EVE-NG. Currently only IP addresses and loopbacks are configured — no IGP, no MPLS, no SR. Your task is to:

1. Bring up IS-IS Level 2 on all five core links and the four loopbacks.
2. Configure the global SRGB on every router (16000–23999).
3. Allocate per-node prefix SIDs (R1 → index 1, R2 → 2, R3 → 3, R4 → 4) so each loopback resolves to a globally-consistent SR label.

The end-state forwarding plane must let any router reach any other router's loopback using a single MPLS label — the foundation that lab-01 (TI-LFA), lab-02 (LDP coexistence), lab-03 (SR-TE), and lab-04 (PCE) all build on.

### Topology

```
                IS-IS Level 2  •  SR-MPLS  •  SRGB 16000-23999  •  SRLB 15000-15999

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

The square ring R1↔R2↔R3↔R4↔R1 carries links L1/L2/L3/L4. L5 is the R1↔R3
diagonal — the fifth physical edge. Pure-ASCII cannot draw a clean diagonal
without colliding with the ring lines, so L5 is declared on R1's and R3's
interface lists inside their boxes (`Gi0/0/0/2 → ...`). L5 carries no special
role in lab-00 — IS-IS treats it as a fifth equal-cost edge — but it is the
link-disjoint alternate that TI-LFA programs as the backup path in lab-01.
**Five physical links → five IS-IS L2 adjacencies** expected when the core
is fully converged.

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

Five links → five IS-IS L2 adjacencies expected when the core is fully converged.

---

## 3. Hardware & Environment Specifications

| Component | Value |
|-----------|-------|
| Platform | Cisco IOS-XRv 9000, version 7.x |
| Hypervisor | EVE-NG Pro |
| RAM per node | 12 GB |
| Boot time per node | 8–12 minutes (must wait for `RP/0/0/CPU0:<host>#` prompt) |
| Total nodes | 4 (R1, R2, R3, R4) |
| Console driver | `cisco_xr_telnet` (Netmiko) |

> **Boot warning:** Do not run `setup_lab.py` until every router has reached the `RP/0/0/CPU0:<hostname>#` exec prompt. IOS-XRv does not accept config commands during the management-plane boot phase.

---

## 4. Base Configuration

`setup_lab.py` pushes the following per-router state onto each node:

- Hostname
- Loopback0 IP (10.0.0.X/32)
- All physical interfaces with descriptions, IP addresses, and `no shutdown`
- `commit` to write to running-config

**IS NOT pre-loaded** (student configures this):

- IS-IS process and address-family
- Per-interface IS-IS attachment (passive on Loopback0, point-to-point on core links)
- `metric-style wide`
- Top-level `segment-routing global-block`
- `segment-routing mpls` under IS-IS IPv4 unicast AF
- `prefix-sid index N` on each router's Loopback0

Run setup before continuing:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Bring Up IS-IS Level 2 on All Four Routers

- On each router, configure IS-IS process `CORE` with the NET shown in the device table (system ID = `0000.0000.000X` where X = router number).
- Set `is-type level-2-only` (production SP cores rarely need L1).
- Under `address-family ipv4 unicast`, enable `metric-style wide`. This is a strict prerequisite for SR — without it, no SR sub-TLVs are originated.
- Attach Loopback0 to IS-IS as `passive` (we want it advertised but no hellos sent).
- Attach every core-facing GigabitEthernet to IS-IS as `point-to-point` (skips the L2 DIS election overhead on a 2-node link).

**Verification:** `show isis adjacency` on each router lists every directly-connected core neighbor in `Up` state. R1 sees 3 neighbors (R2, R3, R4); R2 sees 2 (R1, R3); R3 sees 3 (R1, R2, R4); R4 sees 2 (R1, R3). The total unique adjacency count across the domain is 5 — one per link.

---

### Task 2: Configure the SRGB on Every Router

- Add the top-level `segment-routing` block on R1, R2, R3, R4 with `global-block 16000 23999`. This is the IOS-XR default range; you are explicitly setting it to make the configuration self-documenting.
- The SRLB is left at the IOS-XR default (15000–15999) — no explicit `local-block` command is required for this lab.

**Verification:** `show mpls label range` on each router shows the SRGB allocated. `show segment-routing srgb` lists 16000–23999 as the active range.

> **Common pitfall:** `segment-routing` on IOS-XR is a top-level config block. It is NOT nested under `mpls`, `router isis`, or any other subsystem. Looking for it under the `mpls` hierarchy is the most common first-time XR mistake on this objective.

---

### Task 3: Activate SR Under IS-IS

- Under `router isis CORE / address-family ipv4 unicast`, add `segment-routing mpls`. This single command tells IS-IS to originate and process SR sub-TLVs inside Extended IP Reachability TLV 135.
- Without this, the SRGB is reserved but unused — IS-IS doesn't know it's supposed to advertise SR information.

**Verification:** `show isis segment-routing label table` returns a non-empty table once at least one prefix SID is configured (Task 4).

---

### Task 4: Allocate Per-Node Prefix SIDs

- On each router, attach a prefix SID to Loopback0:
  - R1: `prefix-sid index 1` (resolves to label 16001)
  - R2: `prefix-sid index 2` (label 16002)
  - R3: `prefix-sid index 3` (label 16003)
  - R4: `prefix-sid index 4` (label 16004)
- The `index N` form is preferred over `absolute N` because it survives an SRGB renumber: change the SRGB start, the absolute label changes, but the index stays the same on the originating router.

**Verification:**

- `show isis segment-routing label table` on any router lists all four loopbacks with their assigned labels.
- `show mpls forwarding labels 16001 16004` on any router lists the SR LFIB entries for every remote loopback (with swap or pop, depending on whether the router is the penultimate hop).

---

### Task 5: End-to-End SR Forwarding Verification

- From R1, run `traceroute mpls ipv4 10.0.0.3/32`. The output must show a label-switched path (not an IP-only path) with one MPLS label per hop until the penultimate router pops the label.
- Run `ping 10.0.0.3 source 10.0.0.1` from R1 — should succeed (5/5).

The forwarding plane is now SR-only. Any router can reach any other router's loopback by pushing a single SR label.

---

## 6. Verification & Analysis

### Task 1: IS-IS Adjacency Verification

```
RP/0/0/CPU0:R1# show isis adjacency
IS-IS CORE Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 BFD IPv6 BFD
R2             Gi0/0/0/0                *PtoP*         Up    27   00:01:32 Yes  None     None
R3             Gi0/0/0/2                *PtoP*         Up    25   00:01:30 Yes  None     None    ! ← L5 diagonal
R4             Gi0/0/0/1                *PtoP*         Up    28   00:01:34 Yes  None     None
Total adjacency count: 3
```

R1 has three neighbors. R2 has two (R1, R3). R3 has three (R1, R2, R4). R4 has two (R1, R3). Per-link unique count = 5.

### Task 2: SRGB Verification

```
RP/0/0/CPU0:R1# show mpls label range
                          Min            Max
Range for dynamic labels: 24000          1048575
SRGB                    : 16000          23999          ! ← matches lab-wide SRGB
SRLB                    : 15000          15999          ! ← IOS-XR default

RP/0/0/CPU0:R1# show segment-routing srgb
Segment Routing Global Block (SRGB) entries:
  Lower-bound: 16000     Upper-bound: 23999
  Size       : 8000      State      : Created
```

If `Range for SRGB` is missing, the top-level `segment-routing` block was not committed. If the range is `0/0`, SRGB was rejected (likely overlap with a static MPLS label).

### Task 3 + 4: Prefix SID Label Table

```
RP/0/0/CPU0:R1# show isis segment-routing label table
IS-IS CORE - Label table:
Label         Prefix/Interface
-------       ---------------
16001         Loopback0           ! ← R1's own prefix SID (locally-allocated)
16002         10.0.0.2/32         ! ← R2's prefix SID
16003         10.0.0.3/32         ! ← R3's prefix SID
16004         10.0.0.4/32         ! ← R4's prefix SID
```

A complete, healthy SR control plane has exactly four entries on every router (one local + three remote).

```
RP/0/0/CPU0:R1# show mpls forwarding labels 16003
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
16003  Pop         SR Pfx (idx 3)     Gi0/0/0/2    10.1.13.3       0    ! ← pop, R1 is penultimate via L5
       16003       SR Pfx (idx 3)     Gi0/0/0/0    10.1.12.2       0    ! ← swap via L1 (alternate ECMP/LFA path)
```

R1 reaches R3 through L5 (diagonal) at 1 IGP hop — penultimate, so it pops the label. The alternate path through L1 (R1→R2→R3) is at 2 IGP hops, so R1 swaps 16003 → 16003 (the receiving router R2 becomes penultimate).

### Task 5: End-to-End SR Forwarding

```
RP/0/0/CPU0:R1# traceroute mpls ipv4 10.0.0.3/32
Tracing MPLS Label Switched Path to 10.0.0.3/32, timeout is 2 seconds
Type escape sequence to abort.
  0 10.1.13.1 MRU 1500 [Labels: 16003 Exp: 0]
  1 10.1.13.3 0 ms ! Reply received                  ! ← R3's loopback, single hop via L5
```

`Labels: 16003` confirms the SR-MPLS label was pushed at R1 and the path is label-switched, not IP-routed.

```
RP/0/0/CPU0:R1# ping 10.0.0.3 source 10.0.0.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.0.3, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/2/2 ms
```

---

## 7. Verification Cheatsheet

### IS-IS State

```
show isis adjacency              ! per-link L2 adjacencies, must be Up
show isis database               ! LSP database, one LSP per router
show isis route                  ! IS-IS-learned IP prefixes
```

### Segment Routing State

```
show segment-routing srgb                       ! SRGB lower/upper bounds
show mpls label range                           ! same info, MPLS-side view
show isis segment-routing label table           ! all SR labels in the domain
show mpls forwarding labels <label>             ! LFIB entry for one SR label
show isis database verbose | include "Prefix-SID"  ! sub-TLV in TLV 135
```

| Command | What to Look For |
|---------|------------------|
| `show isis adjacency` | Every neighbor in `Up` state, total = 5 unique adjacencies |
| `show segment-routing srgb` | 16000–23999, State `Created` |
| `show isis segment-routing label table` | 4 entries (one local, three remote) on every router |
| `show mpls forwarding labels 16001 16004` | LFIB entries with swap or pop |
| `traceroute mpls ipv4 10.0.0.X/32` | Label printed in path, not just IP |

> **Exam tip:** On IOS-XR, the SR control plane has **two independent toggles** — the top-level `segment-routing` block (allocates SRGB) and `segment-routing mpls` under IS-IS af (originates SR sub-TLVs). Removing either one breaks SR but in different ways. Knowing which toggle controls which behavior is the diagnostic skill that scenario 01 tests.

### Common SR Failure Modes

| Symptom | Likely Cause |
|---------|-------------|
| `show segment-routing srgb` returns no output | Top-level `segment-routing global-block` not committed |
| Label table empty on every router | `metric-style wide` missing under IS-IS af — no TLV 135 origination |
| One router missing from label table | That router's `segment-routing mpls` missing under IS-IS af |
| Label table has prefix but no `prefix-sid index` | `prefix-sid index N` missing on that router's Loopback0 |
| Ping to remote loopback works, but `traceroute mpls` fails | IS-IS routes the prefix, but the SR sub-TLV is missing → IP-only forwarding |

---

## 8. Solutions (Spoiler Alert!)

> Try Tasks 1–5 yourself before opening these.

### Task 1: IS-IS Process and Adjacencies

<details>
<summary>Click to view R1 Configuration</summary>

```
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/2
  point-to-point
  address-family ipv4 unicast
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view R2, R3, R4 Configuration</summary>

R2, R3, R4 follow the same pattern. The only differences:
- NET system ID: `0000.0000.0002`, `0000.0000.0003`, `0000.0000.0004`
- R2 has only Gi0/0/0/0 and Gi0/0/0/1; R4 has only Gi0/0/0/0 and Gi0/0/0/1; R3 has Gi0/0/0/0, Gi0/0/0/1, Gi0/0/0/2 (full set).

See `solutions/R2.cfg`, `solutions/R3.cfg`, `solutions/R4.cfg` for the complete configs.
</details>

---

### Task 2: SRGB

<details>
<summary>Click to view SRGB Configuration (all routers)</summary>

```
segment-routing
 global-block 16000 23999
!
commit
```
</details>

---

### Task 3 + 4: SR Activation and Prefix SIDs

<details>
<summary>Click to view R1 SR Activation</summary>

```
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls
 !
 interface Loopback0
  address-family ipv4 unicast
   prefix-sid index 1
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view R2, R3, R4 SR Activation</summary>

Same structure as R1, only the prefix-sid index changes:
- R2: `prefix-sid index 2`
- R3: `prefix-sid index 3`
- R4: `prefix-sid index 4`
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands. Restore the lab between tickets.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — One Prefix SID Missing Across the Domain

A network engineer reports that `traceroute mpls ipv4 10.0.0.3/32` from R1 fails ("no MPLS forwarding entry"), but plain `ping 10.0.0.3` succeeds. Customers are reporting that an SR-TE policy under design that targets R3 cannot establish — it claims it cannot resolve R3's prefix SID.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Symptom:**
- IS-IS adjacencies are all Up (5 total).
- IP routes are present in the RIB on every router.
- `show isis segment-routing label table` on R1, R2, and R4 shows three entries instead of four — labels 16001, 16002, and 16004 are present but `10.0.0.3 → 16003` is missing.
- On R3 itself, the label table is empty (R3 has stopped originating SR information entirely).
- `show mpls forwarding labels 16003` returns no output on any router.
- IP pings to 10.0.0.3 still succeed (IS-IS still advertises the prefix without the SR sub-TLV) but traffic is not label-switched.

**Success criteria:** `show isis segment-routing label table` on every router shows all four labels (16001–16004). `traceroute mpls ipv4 10.0.0.3/32` from R1 succeeds with a label in the path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm scope: `show isis segment-routing label table` on R1 shows 16001/16002/16004 only — every other router is fine, only the entry for 10.0.0.3 is missing. The fault is **localized to one router** (the one whose prefix is missing), not domain-wide.
2. Connect to R3 (the absent router). Check the SR control plane in two places — these are the two independent toggles:
   - Top-level: `show segment-routing srgb` — SRGB is allocated 16000–23999. SRGB is fine.
   - IS-IS: `show running-config router isis CORE` — the `address-family ipv4 unicast` block on R3 is missing `segment-routing mpls`.
3. Confirm the impact: without `segment-routing mpls` under the IS-IS af, R3 does not originate any SR sub-TLV in TLV 135. Other routers see R3's LSP for 10.0.0.3/32, which is why IP forwarding still works, but they have no SID to install in the LFIB.
4. Cross-check via the LSP itself: on R2, `show isis database R3 detail | include SID` returns no Prefix-SID sub-TLV — the smoking gun.

The hint pattern: when **one** SR label is missing on **every** router, the fault is on the originating router (the one whose loopback is missing). When **all** labels are missing on **one** router, the fault is on that one router's SRGB or `metric-style wide`. The two failure modes look superficially similar but require opposite diagnostic moves.
</details>

<details>
<summary>Click to view Fix</summary>

On R3:
```
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls
 !
!
commit
```

IS-IS LSPs propagate the SR sub-TLV within seconds. Verify on R1:
```
show isis segment-routing label table          ! 16003 reappears
traceroute mpls ipv4 10.0.0.3/32                ! label-switched again
```
</details>

---

### Ticket 2 — One IS-IS Adjacency Down on R4

Operators noticed that R4 is "intermittent" — `show isis adjacency` on R4 only lists one neighbor instead of two. Pings to 10.0.0.4 still work from every router. The team performed "only routine cleanup" on R4 earlier today.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Symptom:**
- `show isis adjacency` on R4 lists only R1 (over Gi0/0/0/1 / L4). The L3 adjacency to R3 is missing.
- `show isis adjacency` on R3 also lists only 2 neighbors instead of 3 — R4 is no longer adjacent over L3.
- `show isis database` on R4 still has the full LSP set (R4 reaches the rest of the topology via R1).
- IP ping to 10.0.0.4 succeeds from every router (R2/R3 reach 10.0.0.4 via R1).
- Total domain-wide adjacency count drops from 5 to 4. Forwarding still works but the topology has no R3↔R4 redundancy — if L4 (R1↔R4) goes down, R4 is fully isolated.

**Success criteria:** `show isis adjacency` on R4 lists 2 neighbors (R1 and R3). Total domain-wide adjacencies = 5.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Locate the missing adjacency: `show isis adjacency` on R4 — only Gi0/0/0/1 (L4 to R1) shows Up. Gi0/0/0/0 (L3 to R3) is absent from the adjacency list entirely.
2. Confirm the L1/L2 path is fine: `ping 10.1.34.3 source 10.1.34.4` from R4 succeeds — IP connectivity over L3 works. The fault is not physical, not L1/L2, not even L3 IP — it is at the IS-IS layer.
3. Inspect the IS-IS interface attachment on R4: `show running-config router isis CORE` — under `interface GigabitEthernet0/0/0/0`, the `address-family ipv4 unicast` sub-block is missing.
4. Understand the impact: on IOS-XR, an IS-IS interface needs both `point-to-point` (or default broadcast) AND a per-interface address-family block to actually run IS-IS for that AF. With the AF block removed, the interface stays attached to IS-IS but does not exchange IPv4 hellos — adjacency cannot form.
5. Cross-check from R3's side: `show isis adjacency` on R3 also misses R4 — confirming the failure is symmetric (no IS-IS hello traffic from either side reaches the other).
</details>

<details>
<summary>Click to view Fix</summary>

On R4:
```
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
  !
 !
!
commit
```

Adjacency forms within seconds (one IS-IS hello interval). Verify on R4:
```
show isis adjacency               ! 2 neighbors: R1 and R3
```

And on R3:
```
show isis adjacency               ! 3 neighbors: R1, R2, R4
```
</details>

---

### Ticket 3 — Label 16004 Absent from Every LFIB

A network engineer is debugging an SR-TE policy from R1 toward R4. The policy fails with "no SID for endpoint 10.0.0.4." But R4 is otherwise healthy: IS-IS adjacencies are all Up, ping to 10.0.0.4 succeeds, and all other prefix SIDs (16001, 16002, 16003) are present in the label table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Symptom:**
- All 5 IS-IS adjacencies are Up.
- `show isis segment-routing label table` on R1, R2, and R3 shows 3 entries (16001, 16002, 16003) — label 16004 is missing.
- On R4 itself, the label table shows the three remote labels but no local SID for its own loopback.
- `show mpls forwarding labels 16004` returns nothing on any router.
- IP routes for 10.0.0.4/32 are present and IP ping succeeds — IS-IS still advertises the prefix.

This looks superficially like Ticket 1 (one prefix SID missing) but the fault is at a different layer.

**Success criteria:** `show isis segment-routing label table` on every router shows all four labels (16001–16004).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the scope: only label 16004 (R4's loopback) is missing; the other three SIDs are present everywhere. As in Ticket 1, the fault is on the originating router (R4).
2. On R4, check the two SR toggles:
   - `show segment-routing srgb` — SRGB 16000–23999 is allocated. SRGB is fine.
   - `show running-config router isis CORE / address-family ipv4 unicast` — `segment-routing mpls` IS present. SR is active in IS-IS.
3. So why no SID? Drill into the per-interface IS-IS config: `show running-config router isis CORE / interface Loopback0`. The `address-family ipv4 unicast` sub-block is present but `prefix-sid index 4` is missing.
4. Understand the distinction from Ticket 1: in Ticket 1, R3 was not originating SR sub-TLVs at all (so R3's *own* table was empty too). Here, R4 IS originating SR sub-TLVs for the SR-active prefixes — it just has not assigned itself a prefix SID. Without the per-interface `prefix-sid index N`, R4's loopback is in IS-IS but not in the SR plane.
5. Confirm via the LSP: `show isis database R4 detail | include Prefix-SID` from R1 — TLV 135 has the prefix `10.0.0.4/32` but no SID/Label sub-TLV under it.

Three failure modes for "missing label" — distinguishing them is the lesson:
- Ticket 1 (R3 missing `segment-routing mpls`): R3 originates **no** SR sub-TLVs for any prefix.
- Ticket 3 (R4 missing `prefix-sid index 4`): R4 originates SR sub-TLVs in general but **none for its own loopback**.
- A third possibility (not in this ticket set): SRGB mismatch — would prevent label installation downstream, not advertisement upstream.
</details>

<details>
<summary>Click to view Fix</summary>

On R4:
```
router isis CORE
 interface Loopback0
  address-family ipv4 unicast
   prefix-sid index 4
  !
 !
!
commit
```

Verify on R1:
```
show isis segment-routing label table     ! 16004 reappears
show mpls forwarding labels 16004          ! LFIB entry installed
traceroute mpls ipv4 10.0.0.4/32           ! label-switched again
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS CORE process configured on R1, R2, R3, R4 with correct NET (`49.0001.0000.0000.000X.00`)
- [ ] `is-type level-2-only` on every router
- [ ] `metric-style wide` under IS-IS IPv4 unicast af on every router
- [ ] Loopback0 attached as `passive`; core interfaces attached as `point-to-point`
- [ ] `show isis adjacency` shows 5 unique adjacencies across the domain (3 on R1, 2 on R2, 3 on R3, 2 on R4)
- [ ] Top-level `segment-routing global-block 16000 23999` configured on every router
- [ ] `show segment-routing srgb` shows 16000–23999 on every router
- [ ] `segment-routing mpls` under IS-IS IPv4 unicast af on every router
- [ ] `prefix-sid index N` configured on each router's Loopback0 (1, 2, 3, 4)
- [ ] `show isis segment-routing label table` shows 4 entries (16001–16004) on every router
- [ ] `show mpls forwarding labels 16003` from R1 shows the SR LFIB entry
- [ ] `traceroute mpls ipv4 10.0.0.3/32` from R1 shows label 16003 in the path
- [ ] `ping 10.0.0.4 source 10.0.0.1` succeeds (5/5)

### Troubleshooting

- [ ] Ticket 1 resolved: label 16003 reappears after `segment-routing mpls` re-added under R3 IS-IS af
- [ ] Ticket 2 resolved: R4's L3 adjacency reappears after re-attaching `address-family ipv4 unicast` under R4 Gi0/0/0/0
- [ ] Ticket 3 resolved: label 16004 reappears after `prefix-sid index 4` re-added on R4 Loopback0

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided (placeholder detected) | All scripts |
| 3 | EVE-NG connectivity or port discovery error | All scripts |
| 4 | Pre-flight check failed (lab not in expected state) | Inject scripts only |
