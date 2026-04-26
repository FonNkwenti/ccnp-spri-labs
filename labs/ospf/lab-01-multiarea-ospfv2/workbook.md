# Lab 01: Multiarea OSPFv2 and LSA Propagation

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

**Exam Objective:** 1.2, 1.2.a — Implement and troubleshoot multiarea OSPFv2, LSA types, and inter-area route propagation

OSPF's multiarea design is the cornerstone of scalable service provider IGPs. A single flat Area 0 works for small labs but collapses under the weight of real-world topologies: a full SPF recalculation on every router every time a leaf link flaps is operationally unacceptable. Multiarea OSPF solves this by confining detailed topology information to its origin area and advertising summarised reachability across area boundaries. This lab transitions from the single-area baseline (lab-00) to a five-router, four-area topology, introducing two Area Border Routers, four LSA types, and the rules that govern which routers flood which LSAs into which areas.

### OSPF Area Architecture

An OSPF area is a group of routers and links that share a common LSDB (Link-State Database). Every router inside an area runs the full Dijkstra SPF algorithm on the LSDB for that area. Critically, routers in one area do **not** see the detailed topology of another area — they only see the inter-area summary routes (Type-3 LSAs) advertised by the ABR.

Rules that must be followed to maintain a valid multiarea domain:
- **Area 0 (backbone)** must exist and all other areas must connect to it directly or via a virtual link.
- An **ABR** (Area Border Router) sits at the boundary between two or more areas. It maintains a separate LSDB per area and originates Type-3 Summary-LSAs to advertise inter-area prefixes.
- An ABR is *not* elected — any router with active interfaces in two or more OSPF areas is automatically an ABR.
- All inter-area traffic transits Area 0. Traffic from Area 1 to Area 2 goes Area 1 → Area 0 → Area 2, even if a shorter physical path exists between them.

### LSA Type Reference

| Type | Name | Flooded By | Scope | Content |
|------|------|-----------|-------|---------|
| 1 | Router-LSA | Every router | Within its area | Router's interfaces and link costs |
| 2 | Network-LSA | DR on broadcast/NBMA segments | Within its area | List of routers on the multi-access segment |
| 3 | Summary-LSA (prefix) | ABR | Into adjacent areas | Inter-area prefix reachability, ABR sets metric |
| 4 | Summary-LSA (ASBR) | ABR | Into adjacent areas | Reachability to the ASBR router-id (lab-03) |
| 5 | AS-External-LSA | ASBR | Domain-wide | External prefix redistributed into OSPF (lab-03) |
| 7 | NSSA-External-LSA | ASBR in NSSA | Within NSSA area | External prefix in an NSSA area (lab-03) |

In this lab only Types 1, 2, and 3 are generated. Type 4 appears in lab-03 when an ASBR is added.

### ABR Behaviour and Type-3 LSA Generation

When an ABR runs SPF on Area 1, it computes the cost to each prefix in that area. For each prefix it then originates a Type-3 Summary-LSA into every other area it belongs to (e.g., Area 0). The cost in the Type-3 LSA is the ABR's own cost to reach that prefix — downstream routers add their cost to the ABR to compute the full inter-area metric.

Key behaviour to observe:
- A Type-3 LSA is **re-originated** by each successive ABR it crosses. If traffic from Area 2 must transit Area 0 to reach Area 1, R3 creates a Type-3 for Area 1 prefixes into Area 0, and R2 re-creates a new Type-3 for those same prefixes into Area 1 (and vice versa for Area 2 prefixes into Area 1). There is no Type-3 LSA that crosses more than one ABR unchanged.
- The metric accumulated on a Type-3 LSA is the **cost from the originating ABR to that prefix**, not the end-to-end path cost. Routers add their own cost to the ABR when computing the full route metric.

### The `network` Statement and Area Assignment

IOSv OSPF uses the `network <ip> <wildcard> area <N>` statement under `router ospf` to assign interfaces to areas. The router compares each interface's primary IP against all network statements in order and assigns the interface to the first matching area. The wildcard mask `0.0.0.255` matches any host in the /24 subnet; `0.0.0.0` is an exact host match (common for loopbacks).

An area-mismatch fault — two adjacent routers advertising the same link in different areas — is one of the most common OSPF failures in production. The adjacency never progresses past the INIT state on that interface, and the symptom (two routers with the link in "FULL" state to other neighbors but "INIT"/"ATTEMPT" to each other on the mismatch link) points directly to the misconfiguration.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Multiarea design | Assign links and loopbacks to the correct areas; identify ABR vs internal routers |
| LSA identification | Read `show ip ospf database` and distinguish Type-1, 2, and 3 LSAs |
| ABR verification | Confirm a router is an ABR using `show ip ospf` and the "Area Border Router" flag |
| Inter-area route tracing | Follow a Type-3 Summary-LSA from origin area through backbone to destination area |
| Area-mismatch diagnosis | Identify a mismatch using `show ip ospf neighbor` and `show ip ospf database` |

---

## 2. Topology & Scenario

**Scenario:** You are the network engineer for TelcoWide Service Provider. The OSPF backbone is currently a single flat Area 0 spanning three routers (R1, R2, R3). The network architecture team has mandated a multiarea redesign: customer-edge-facing prefixes must be isolated into stub areas so that a flapping CE link does not trigger a domain-wide SPF recalculation. You must migrate to a four-area design, bring up two new routers (R4 and R5) in their respective areas, and verify that inter-area reachability is fully established. A junior engineer will then plant a configuration fault for you to diagnose.

```
              ┌──────────────────────────────┐
              │             R1               │
              │      (Area 1 Internal)       │
              │   Lo0: 10.0.0.1/32           │
              │   Lo1: 172.16.1.1/24         │
              └──────────────┬───────────────┘
                             │ Gi0/0  10.1.12.1/24
                             │     [Area 1]
                             │ Gi0/0  10.1.12.2/24
              ┌──────────────┴───────────────┐
              │             R2               │
              │         (ABR  0/1)           │
              │   Lo0: 10.0.0.2/32  (Area 0) │
              └──────────────┬───────────────┘
                             │ Gi0/1  10.1.23.2/24
                             │     [Area 0]
                             │ Gi0/0  10.1.23.3/24
              ┌──────────────┴───────────────┐
              │             R3               │
              │        (ABR  0/2/3)          │
              │   Lo0: 10.0.0.3/32  (Area 0) │
              └──────┬──────────────┬────────┘
   Gi0/1  10.1.34.3  │              │  10.1.35.3  Gi0/2
      [Area 2]        │              │    [Area 3]
   Gi0/0  10.1.34.4  │              │  10.1.35.5  Gi0/0
┌──────────┐          │              │          ┌──────────┐
│    R4    │          │              │          │    R5    │
│ (Area 2) │          │              │          │ (Area 3) │
│Lo0:      │          │              │          │Lo0:      │
│10.0.0.4  │          │              │          │10.0.0.5  │
│Lo1:      │          │              │          │Lo1:      │
│172.16.4.1│          │              │          │172.16.5.1│
└──────────┘          │              │          └──────────┘
```

**Link summary:**

| Link | Devices | Subnet | Area |
|------|---------|--------|------|
| L1 | R1 Gi0/0 ↔ R2 Gi0/0 | 10.1.12.0/24 | Area 1 |
| L2 | R2 Gi0/1 ↔ R3 Gi0/0 | 10.1.23.0/24 | Area 0 |
| L3 | R3 Gi0/1 ↔ R4 Gi0/0 | 10.1.34.0/24 | Area 2 |
| L4 | R3 Gi0/2 ↔ R5 Gi0/0 | 10.1.35.0/24 | Area 3 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Area 1 internal router | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | ABR (Area 0 / Area 1) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | ABR (Area 0 / Area 2 / Area 3) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Area 2 internal router | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Area 3 internal router | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Cabling Table

| Link | Source | Source IP | Destination | Destination IP | Subnet |
|------|--------|-----------|-------------|----------------|--------|
| L1 | R1 Gi0/0 | 10.1.12.1 | R2 Gi0/0 | 10.1.12.2 | 10.1.12.0/24 |
| L2 | R2 Gi0/1 | 10.1.23.2 | R3 Gi0/0 | 10.1.23.3 | 10.1.23.0/24 |
| L3 | R3 Gi0/1 | 10.1.34.3 | R4 Gi0/0 | 10.1.34.4 | 10.1.34.0/24 |
| L4 | R3 Gi0/2 | 10.1.35.3 | R5 Gi0/0 | 10.1.35.5 | 10.1.35.0/24 |

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
- Interface IP addressing on all routed links and loopbacks (all five routers)
- `no ip domain-lookup` on all routers
- OSPFv2 process on R1, R2, R3 with all interfaces in Area 0 (carried forward from lab-00)
- R4 and R5 have IP addressing only — no OSPF configuration

**IS NOT pre-loaded** (student configures this):
- Correct area assignments for the L1 link (Area 1), L3 link (Area 2), and L4 link (Area 3)
- ABR configuration on R2 (Area 0 and Area 1) and R3 (Area 0, Area 2, Area 3)
- OSPFv2 process on R4 (Area 2) and R5 (Area 3)
- Loopback network advertisements on R4 and R5

> **Starting point:** R1, R2, R3 have OSPF adjacency in Area 0 (single-area from lab-00). Your first task is to migrate L1 to Area 1, then extend OSPF to R4 and R5 in their respective areas. After the migration R2 will become an ABR and R3 will become a three-area ABR.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Migrate Link L1 to Area 1

On R1, R2, and R3, update the OSPF process so that:
- The L1 subnet (10.1.12.0/24) is assigned to Area 1 instead of Area 0
- R1's loopback0 and loopback1 are also assigned to Area 1 (R1 is an internal Area 1 router)
- R2's loopback0 remains in Area 0 (R2 is an ABR; its management loopback anchors in the backbone)
- R2's L2 interface (toward R3) remains in Area 0

**Verification:** `show ip ospf` on R2 must show "Area Border Router" in the "This router is a…" line. `show ip ospf neighbor` on R2 must still show R1 and R3 as Full neighbors.

---

### Task 2: Extend OSPF to R4 in Area 2

Configure OSPF on R4 and extend R3's OSPF process to include the L3 subnet and R4's loopback addresses:
- Assign the L3 subnet (10.1.34.0/24), R4's loopback0 (10.0.0.4/32), and R4's loopback1 (172.16.4.0/24) all to Area 2
- Assign the L3 subnet on R3 (its Gi0/1 interface) to Area 2 as well

**Verification:** `show ip ospf neighbor` on R3 must show R4 as a Full neighbor. On R1, `show ip route ospf` must show 10.0.0.4/32 and 172.16.4.0/24 as inter-area (`O IA`) routes.

---

### Task 3: Extend OSPF to R5 in Area 3

Configure OSPF on R5 and extend R3's OSPF process to include the L4 subnet and R5's loopback addresses:
- Assign the L4 subnet (10.1.35.0/24), R5's loopback0 (10.0.0.5/32), and R5's loopback1 (172.16.5.0/24) all to Area 3
- Assign the L4 subnet on R3 (its Gi0/2 interface) to Area 3

**Verification:** `show ip ospf neighbor` on R3 must show R5 as Full. On R1, `show ip route ospf` must show 10.0.0.5/32 and 172.16.5.0/24 as `O IA` routes.

---

### Task 4: Verify LSA Propagation and Inter-Area Reachability

Without adding any new configuration, verify the following using `show` commands:
- On any router, `show ip ospf database summary` lists Type-3 Summary-LSAs for all inter-area prefixes
- The originating router-id in each Type-3 LSA matches the correct ABR (10.0.0.2 for Area 1 prefixes in Area 0; 10.0.0.3 for Area 2 and Area 3 prefixes in Area 0)
- End-to-end reachability: R1 can ping R4's loopback1 (172.16.4.1) and R5's loopback1 (172.16.5.1)

**Verification:** `ping 172.16.4.1 source loopback0` from R1 must succeed (5/5 replies). `ping 172.16.5.1 source loopback0` from R1 must also succeed.

---

### Task 5: Diagnose a Planted Area-Mismatch Fault

After completing Tasks 1–4, a colleague changes a single `network` statement on one router. OSPF adjacency on one link drops to INIT and inter-area routes disappear. Using only `show` commands (no debug), identify:
- Which link is affected
- Which router has the misconfigured area number
- The correct area assignment that restores Full adjacency

**Verification:** Restore the correct configuration. `show ip ospf neighbor` must show all four neighbors as Full. `ping 172.16.4.1 source loopback0` from R1 must succeed.

---

## 6. Verification & Analysis

### Task 1 — R2 ABR Verification

```
R2# show ip ospf
 Routing Process "ospf 1" with ID 10.0.0.2
 ...
 This router is a Border router       ! ← confirms R2 is now an ABR
 ...
 Number of areas in this router is 2. 2 normal 0 stub 0 nssa
 ...
   Area BACKBONE(0)                   ! ← Area 0 present
       ...
   Area 1                             ! ← Area 1 present
       ...

R2# show ip ospf neighbor
Neighbor ID     Pri   State    Dead Time  Address         Interface
10.0.0.1          1   FULL/DR  00:00:38   10.1.12.1       GigabitEthernet0/0  ! ← R1 Full in Area 1
10.0.0.3          1   FULL/DR  00:00:35   10.1.23.3       GigabitEthernet0/1  ! ← R3 Full in Area 0
```

### Task 2 — R4 Adjacency and Inter-Area Routes on R1

```
R3# show ip ospf neighbor
Neighbor ID     Pri   State    Dead Time  Address         Interface
10.0.0.2          1   FULL/DR  00:00:37   10.1.23.2       GigabitEthernet0/0  ! ← R2 Full in Area 0
10.0.0.4          1   FULL/DR  00:00:36   10.1.34.4       GigabitEthernet0/1  ! ← R4 Full in Area 2
10.0.0.5          1   FULL/DR  00:00:34   10.1.35.5       GigabitEthernet0/2  ! ← R5 Full in Area 3

R1# show ip route ospf
      10.0.0.0/32 is subnetted, 5 subnets
O IA     10.0.0.2 [110/2] via 10.1.12.2, 00:01:10, GigabitEthernet0/0   ! ← R2 lo0 inter-area
O IA     10.0.0.3 [110/3] via 10.1.12.2, 00:01:10, GigabitEthernet0/0   ! ← R3 lo0 inter-area
O IA     10.0.0.4 [110/4] via 10.1.12.2, 00:01:05, GigabitEthernet0/0   ! ← R4 lo0 O IA
O IA     10.0.0.5 [110/4] via 10.1.12.2, 00:01:03, GigabitEthernet0/0   ! ← R5 lo0 O IA
      172.16.0.0/24 is subnetted
O IA     172.16.4.0 [110/5] via 10.1.12.2, 00:01:05, GigabitEthernet0/0 ! ← R4 lo1 O IA
O IA     172.16.5.0 [110/5] via 10.1.12.2, 00:01:03, GigabitEthernet0/0 ! ← R5 lo1 O IA
```

### Task 4 — LSA Database Inspection

```
R2# show ip ospf database summary

            OSPF Router with ID (10.0.0.2) (Process ID 1)

                Summary Net Link States (Area 0)

Link ID         ADV Router      Age   Seq#       Checksum
172.16.1.0      10.0.0.2        142   0x80000001 0xXXXX    ! ← R2 originated, Area 1 prefix
10.0.0.1        10.0.0.2        142   0x80000001 0xXXXX    ! ← R2 originated, R1 lo0
10.0.0.4        10.0.0.3        118   0x80000001 0xXXXX    ! ← R3 originated, R4 lo0
172.16.4.0      10.0.0.3        118   0x80000001 0xXXXX    ! ← R3 originated, R4 lo1
10.0.0.5        10.0.0.3        116   0x80000001 0xXXXX    ! ← R3 originated, R5 lo0
172.16.5.0      10.0.0.3        116   0x80000001 0xXXXX    ! ← R3 originated, R5 lo1

                Summary Net Link States (Area 1)

Link ID         ADV Router      Age   Seq#       Checksum
10.0.0.2        10.0.0.2        142   0x80000001 0xXXXX    ! ← R2 injects backbone summary into Area 1
10.0.0.3        10.0.0.2        142   0x80000001 0xXXXX
10.0.0.4        10.0.0.2        118   0x80000001 0xXXXX    ! ← R2 re-originates R4 lo0 into Area 1
172.16.4.0      10.0.0.2        118   0x80000001 0xXXXX    ! ← R2 re-originates R4 lo1 into Area 1
10.0.0.5        10.0.0.2        116   0x80000001 0xXXXX
172.16.5.0      10.0.0.2        116   0x80000001 0xXXXX

R1# ping 172.16.4.1 source loopback0
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 172.16.4.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.0.1
!!!!!                                                    ! ← 5/5 success
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/3/4 ms
```

---

## 7. Verification Cheatsheet

### OSPF Process and Role Verification

```
show ip ospf
show ip ospf border-routers
```

| Command | Purpose |
|---------|---------|
| `show ip ospf` | Shows router type (ABR flag), area count, process details |
| `show ip ospf border-routers` | Lists all ABRs and ASBRs known to this router |

> **Exam tip:** An OSPF router becomes an ABR automatically when it has active interfaces in two or more areas. There is no explicit `abr` command — the designation is computed.

### Neighbor and Adjacency Verification

```
show ip ospf neighbor
show ip ospf neighbor detail
```

| Command | Purpose |
|---------|---------|
| `show ip ospf neighbor` | All OSPF neighbors: state, dead-time, interface |
| `show ip ospf neighbor detail` | Shows neighbor's area, DR/BDR role, options byte |
| `show ip ospf interface brief` | Interface areas, cost, state (DR/BDR/DROTHER) |

### LSA Database Inspection

```
show ip ospf database
show ip ospf database summary
show ip ospf database router
show ip ospf database network
```

| Command | Purpose |
|---------|---------|
| `show ip ospf database` | Summary count of all LSA types per area |
| `show ip ospf database summary` | All Type-3 Summary-LSAs (inter-area prefixes) |
| `show ip ospf database summary <prefix>` | Detail for a specific Type-3 LSA |
| `show ip ospf database router` | All Type-1 Router-LSAs in current area |
| `show ip ospf database network` | All Type-2 Network-LSAs in current area |

> **Exam tip:** Type-3 LSAs are scoped to one area at a time. An ABR re-originates new Type-3 LSAs into each area it belongs to — it does not forward the original Type-3 LSA unchanged.

### Routing Table Verification

```
show ip route ospf
show ip route <prefix> longer-prefixes
```

| Command | Purpose |
|---------|---------|
| `show ip route ospf` | All OSPF routes: `O` = intra-area, `O IA` = inter-area, `O E1/E2` = external |
| `show ip route 10.0.0.0 255.0.0.0 longer-prefixes` | All OSPF routes under 10/8 |

### Area Mismatch Diagnosis

```
show ip ospf interface <int>
show ip ospf neighbor
debug ip ospf adj
```

| Command | Purpose |
|---------|---------|
| `show ip ospf interface Gi0/0` | Shows the area this interface is assigned to |
| `show ip ospf neighbor` | Stuck-in-INIT indicates possible area mismatch or auth mismatch |
| `debug ip ospf adj` | Shows hello packets with area field — compare area on each side |

> **Exam tip:** A neighbor stuck in INIT state (one-way hellos received) usually indicates a mismatched area ID, MTU mismatch, or authentication mismatch. Check `show ip ospf interface` on both sides first before enabling debug.

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /32 (255.255.255.255) | 0.0.0.0 | Exact loopback match |
| /30 (255.255.255.252) | 0.0.0.3 | Point-to-point link |
| /24 (255.255.255.0) | 0.0.0.255 | LAN / point-to-point match |
| /16 (255.255.0.0) | 0.0.255.255 | Summary range |

### Common OSPF Area Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Neighbor stuck in INIT | Area ID mismatch on the link |
| Neighbor goes FULL then drops | Dead-interval timer mismatch |
| Routes show `O` instead of `O IA` | Loopback placed in wrong area (should be non-backbone for internal router) |
| No Type-3 LSAs for a prefix | ABR network statement missing for that area |
| `show ip ospf` does not show ABR | Router only has interfaces in one area |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Migrate L1 to Area 1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospf 1
 no network 10.0.0.1 0.0.0.0 area 0
 no network 10.1.12.0 0.0.0.255 area 0
 no network 172.16.1.0 0.0.0.255 area 0
 network 10.0.0.1 0.0.0.0 area 1
 network 10.1.12.0 0.0.0.255 area 1
 network 172.16.1.0 0.0.0.255 area 1
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — loopback0 stays in Area 0; L1 moves to Area 1
router ospf 1
 no network 10.1.12.0 0.0.0.255 area 0
 network 10.1.12.0 0.0.0.255 area 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf
show ip ospf neighbor
```
</details>

---

### Task 2: Extend OSPF to R4 in Area 2

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — add L3 link and R4-facing area
interface GigabitEthernet0/1
 ip address 10.1.34.3 255.255.255.0
 no shutdown

router ospf 1
 network 10.1.34.0 0.0.0.255 area 2
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — full OSPF config from scratch
router ospf 1
 router-id 10.0.0.4
 network 10.0.0.4 0.0.0.0 area 2
 network 10.1.34.0 0.0.0.255 area 2
 network 172.16.4.0 0.0.0.255 area 2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf neighbor
show ip route ospf
```
</details>

---

### Task 3: Extend OSPF to R5 in Area 3

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — add L4 link
interface GigabitEthernet0/2
 ip address 10.1.35.3 255.255.255.0
 no shutdown

router ospf 1
 network 10.1.35.0 0.0.0.255 area 3
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — full OSPF config from scratch
router ospf 1
 router-id 10.0.0.5
 network 10.0.0.5 0.0.0.0 area 3
 network 10.1.35.0 0.0.0.255 area 3
 network 172.16.5.0 0.0.0.255 area 3
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf neighbor
show ip route ospf
ping 172.16.4.1 source loopback0
ping 172.16.5.1 source loopback0
```
</details>

---

### Task 4: LSA Propagation Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R2 — inspect Type-3 LSAs for each area
show ip ospf database summary

! Confirm ABR designation
show ip ospf | include Border

! Confirm all inter-area routes visible from R1
show ip route ospf
```
</details>

---

### Task 5: Area-Mismatch Diagnosis

<details>
<summary>Click to view Diagnosis Approach</summary>

```bash
! Step 1 — find which neighbor lost Full state
show ip ospf neighbor

! Step 2 — check area assignment on each side of the affected link
show ip ospf interface GigabitEthernet0/1   ! run on R3
show ip ospf interface GigabitEthernet0/0   ! run on R4

! Step 3 — compare: if one side shows "Area 0" and the other shows "Area 2",
! the area ID is mismatched. Fix the one with the wrong area number.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On whichever router has the wrong area (e.g., R3 with L3 in area 0 instead of area 2):
router ospf 1
 no network 10.1.34.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 2
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                              # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>       # restore
```

---

### Ticket 1 — R4 Reports No OSPF Neighbors

You receive an alert: R4 has had no OSPF neighbors for the past 5 minutes. The link L3 is up (pings to 10.1.34.3 succeed from R4), but `show ip ospf neighbor` on R4 is empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R4 shows R3 (10.0.0.3) as a Full neighbor. R1 can reach 172.16.4.1 via `O IA`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R4 — confirm link is up and OSPF is running
show ip ospf interface GigabitEthernet0/0

! On R3 — compare area assignment
show ip ospf interface GigabitEthernet0/1

! If R3 shows Area 0 and R4 shows Area 2 → area mismatch
! If both show the same area but no neighbor → check hello/dead timers
! show ip ospf interface <int> shows: hello interval, dead interval, area
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R3 — the L3 network statement was changed from area 2 to area 0
router ospf 1
 no network 10.1.34.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 2
```
</details>

---

### Ticket 2 — R1 Cannot Reach R5 Loopback1 but Can Reach R5 Loopback0

Operations reports that R5's management address (10.0.0.5) is reachable from R1 but R5's customer loopback (172.16.5.1) is unreachable. R5's OSPF adjacency with R3 is Full.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `ping 172.16.5.1 source loopback0` from R1 succeeds 5/5.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R1 — confirm 172.16.5.0/24 is missing from routing table
show ip route ospf
! If 10.0.0.5 is O IA but 172.16.5.0 is absent → prefix not advertised

! On R5 — check what networks are in the OSPF process
show ip ospf database router
! R5's Type-1 LSA should list Lo1 stub; if absent, network statement is missing

! On R5 — check OSPF interface status
show ip ospf interface brief
! Lo1 (172.16.5.1) must appear; if absent, it was removed from the OSPF process
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R5 — the Lo1 network statement was removed
router ospf 1
 network 172.16.5.0 0.0.0.255 area 3
```
</details>

---

### Ticket 3 — R2 Has Lost Its ABR Designation

A monitoring alert fires: OSPF Type-3 Summary-LSAs for Area 1 prefixes are no longer being generated by R2. R1–R2 adjacency is Full, R2–R3 adjacency is Full, but R3 cannot see any Type-3 LSAs for 172.16.1.0/24 or 10.0.0.1/32 in Area 0.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip ospf database summary` on R3 shows Type-3 LSAs for 172.16.1.0/24 and 10.0.0.1/32 with advertising router 10.0.0.2. `show ip ospf` on R2 shows "Border router".

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R2 — confirm ABR flag
show ip ospf | include Border
! If output shows only "Internal router" → R2 lost one area

! On R2 — check how many areas are active
show ip ospf
! "Number of areas in this router is 1" → only in Area 0, L1 moved back to Area 0

! On R2 — check interface area assignments
show ip ospf interface GigabitEthernet0/0
! If Gi0/0 shows Area 0 → the network statement for Area 1 was removed or changed
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2 — the L1 area was reverted from Area 1 back to Area 0
router ospf 1
 no network 10.1.12.0 0.0.0.255 area 0
 network 10.1.12.0 0.0.0.255 area 1
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R1 fully in Area 1 (lo0, lo1, Gi0/0 all area 1)
- [ ] R2 is ABR: `show ip ospf` shows "Border router" and two areas (0 and 1)
- [ ] R3 is ABR: `show ip ospf` shows three areas (0, 2, and 3)
- [ ] R4 adjacency with R3 is Full in Area 2
- [ ] R5 adjacency with R3 is Full in Area 3
- [ ] `show ip ospf database summary` on R2 shows Type-3 LSAs for Area 1 prefixes in Area 0 (ADV Router 10.0.0.2)
- [ ] `show ip ospf database summary` on R3 shows Type-3 LSAs for Area 2 and Area 3 prefixes in Area 0 (ADV Router 10.0.0.3)
- [ ] `show ip route ospf` on R1 shows R4 and R5 loopbacks as `O IA`
- [ ] `ping 172.16.4.1 source loopback0` from R1 succeeds 5/5
- [ ] `ping 172.16.5.1 source loopback0` from R1 succeeds 5/5

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved (area-mismatch on L3)
- [ ] Ticket 2 diagnosed and resolved (missing Lo1 network statement on R5)
- [ ] Ticket 3 diagnosed and resolved (L1 reverted to Area 0 on R2, ABR designation lost)

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
