# Lab 02: OSPFv3 Dual-Stack Multiarea

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

**Exam Objective:** 1.1, 1.2, 1.2.a — Implement OSPFv3 dual-stack multiarea; compare OSPFv3 LSA types with OSPFv2 equivalents

OSPFv2 carries IPv4 topology only. Service providers running dual-stack networks need a parallel routing protocol for IPv6. OSPFv3 was designed from the ground up to carry IPv6 topology, and IOS 15.0 introduced a unified `router ospfv3` process that supports both IPv4 and IPv6 address-families under a single process ID. In this lab you run OSPFv3 for IPv6 alongside the existing OSPFv2 for IPv4 — both use the same area structure and the same ABR routers. The result is a dual-stack domain where every router has both an IPv4 and an IPv6 path to every destination.

### OSPFv3 Architecture and Process Model

OSPFv3 uses the same conceptual model as OSPFv2: areas, LSAs, ABRs, and SPF. The key architectural differences:

| Feature | OSPFv2 | OSPFv3 |
|---------|--------|--------|
| Network layer | IPv4 | IPv6 (link-local for hellos and LSAs) |
| Authentication | MD5 / plain-text in OSPF header | IPsec (ESP/AH) — OSPF header has no auth field |
| Router-ID | Must be IPv4 address | Must be IPv4-format (even on IPv6-only devices) |
| Address announcement | Via `network` statement or `ip ospf area` | Via `ospfv3 N ipv6 area X` on the interface |
| Per-interface activation | `ip ospf <pid> area <N>` | `ospfv3 <pid> ipv6 area <N>` |
| Hello source | Unicast IPv4 | Link-local IPv6 (FE80::) |

The `router-id` in `router ospfv3 1` must be configured explicitly in dual-stack environments to match the OSPFv2 router-id — otherwise IOS picks the highest IPv4 loopback automatically, but explicit configuration prevents surprises after an interface change.

### OSPFv3 LSA Types

OSPFv3 introduces two new LSA types that replace the IPv4-carrying portions of OSPFv2's Type-1 and Type-2 LSAs:

| OSPFv3 Type | Name | Replaces / Complements | Flooded By | Content |
|------------|------|------------------------|------------|---------|
| 1 | Router-LSA | OSPFv2 Type-1 | Every router | Interface links (stub/transit/virtual) — no IPv6 addresses |
| 2 | Network-LSA | OSPFv2 Type-2 | DR on broadcast | List of routers on the segment — no IPv6 addresses |
| 3 | Inter-Area Prefix-LSA | OSPFv2 Type-3 | ABR | Inter-area IPv6 prefix reachability |
| 4 | Inter-Area Router-LSA | OSPFv2 Type-4 | ABR | Reachability to ASBR |
| 8 | Link-LSA | **New — no OSPFv2 equiv.** | Each router for its link | Link-local address + all on-link global prefixes for that link |
| 9 | Intra-Area Prefix-LSA | **New — no OSPFv2 equiv.** | Every router + DR | All IPv6 prefixes for stub interfaces (loopbacks) and transit segments |

The critical insight: in OSPFv3, **LSA Types 1 and 2 no longer carry any IP addresses**. All IPv6 prefixes move into Type-8 (Link-LSA, link-scoped) and Type-9 (Intra-Area Prefix-LSA, area-scoped). This separation of topology from addressing was a deliberate OSPFv3 design choice to enable future multi-protocol extension.

### Unified `router ospfv3` Process (IOS 15.0+)

IOS 15.0 introduced a unified OSPF process that handles both address families under a single process ID:

```
router ospfv3 1
 router-id 10.0.0.1
 !
 address-family ipv4 unicast
  ...    ← OSPFv2-equivalent for IPv4
 address-family ipv6 unicast
  ...    ← OSPFv3 for IPv6
```

For this lab, only the IPv6 address-family is activated via interface-level commands (`ospfv3 1 ipv6 area X`). The IPv4 routing continues under the separate `router ospf 1` process — this keeps the dual-stack configuration additive (the student only adds OSPFv3; OSPFv2 is unchanged from lab-01).

### IS-IS Comparison (reference)

IS-IS uses a single topology by default for both IPv4 and IPv6 — every IS-IS router in the same level shares one SPF tree. OSPFv3, by contrast, runs a completely separate process and database for IPv6. IS-IS multi-topology (MT) mode can run separate topologies for IPv4 and IPv6, which is the IS-IS equivalent of running OSPFv2 + OSPFv3 in parallel. The SPRI exam tests this conceptual comparison in blueprint bullet 1.3.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| OSPFv3 activation | Enable IPv6 unicast routing and attach interfaces to the correct OSPFv3 area |
| Dual-stack verification | Confirm OSPFv2 and OSPFv3 adjacencies are both Full on every link simultaneously |
| LSA type identification | Distinguish Link-LSA (Type-8), Intra-Area Prefix-LSA (Type-9), and Inter-Area Prefix-LSA (Type-3) in OSPFv3 |
| Router-ID management | Set matching router-IDs across OSPFv2 and OSPFv3 processes |
| IPv6 adjacency diagnosis | Identify a missing interface area assignment as the cause of a one-sided OSPFv3 hello |

---

## 2. Topology & Scenario

**Scenario:** TelcoWide's network architecture team has approved the IPv6 rollout. All five routers in the multiarea OSPF domain must now carry dual-stack routing. IPv4 forwarding and OSPFv2 adjacencies from lab-01 must remain intact throughout — this is an additive migration. Your task is to add IPv6 addresses and activate OSPFv3 on every interface in the correct OSPF area, matching the four-area structure already in place for IPv4.

```
              ┌──────────────────────────────────┐
              │              R1                  │
              │       (Area 1 Internal)           │
              │  Lo0: 10.0.0.1 / 2001:db8::1     │
              │  Lo1: 172.16.1.1 / 2001:db8:1::1 │
              └──────────────┬────────────────────┘
                             │ Gi0/0
                             │  IPv4: 10.1.12.1/24
                             │  IPv6: 2001:db8:12::1/64
                             │     [Area 1]
                             │  IPv4: 10.1.12.2/24
                             │  IPv6: 2001:db8:12::2/64
                             │ Gi0/0
              ┌──────────────┴────────────────────┐
              │              R2                   │
              │          (ABR  0/1)               │
              │  Lo0: 10.0.0.2 / 2001:db8::2      │
              └──────────────┬────────────────────┘
                             │ Gi0/1
                             │  IPv4: 10.1.23.2/24
                             │  IPv6: 2001:db8:23::2/64
                             │     [Area 0]
                             │  IPv4: 10.1.23.3/24
                             │  IPv6: 2001:db8:23::3/64
                             │ Gi0/0
              ┌──────────────┴────────────────────┐
              │              R3                   │
              │         (ABR  0/2/3)              │
              │  Lo0: 10.0.0.3 / 2001:db8::3      │
              └──────┬──────────────┬─────────────┘
   Gi0/1  10.1.34.3  │              │  10.1.35.3  Gi0/2
  2001:db8:34::3/64  │              │  2001:db8:35::3/64
      [Area 2]        │              │      [Area 3]
   Gi0/0  10.1.34.4  │              │  10.1.35.5  Gi0/0
  2001:db8:34::4/64  │              │  2001:db8:35::5/64
┌──────────┐          │              │          ┌──────────┐
│    R4    │          │              │          │    R5    │
│ (Area 2) │          │              │          │ (Area 3) │
│Lo0: .4   │          │              │          │Lo0: .5   │
│Lo1:      │          │              │          │Lo1:      │
│172.16.4.1│          │              │          │172.16.5.1│
│2001:db8: │          │              │          │2001:db8: │
│4::1/64   │          │              │          │5::1/64   │
└──────────┘          │              │          └──────────┘
```

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

| Link | Source | IPv4 | IPv6 | Destination | IPv4 | IPv6 | Area |
|------|--------|------|------|-------------|------|------|------|
| L1 | R1 Gi0/0 | 10.1.12.1 | 2001:db8:12::1 | R2 Gi0/0 | 10.1.12.2 | 2001:db8:12::2 | 1 |
| L2 | R2 Gi0/1 | 10.1.23.2 | 2001:db8:23::2 | R3 Gi0/0 | 10.1.23.3 | 2001:db8:23::3 | 0 |
| L3 | R3 Gi0/1 | 10.1.34.3 | 2001:db8:34::3 | R4 Gi0/0 | 10.1.34.4 | 2001:db8:34::4 | 2 |
| L4 | R3 Gi0/2 | 10.1.35.3 | 2001:db8:35::3 | R5 Gi0/0 | 10.1.35.5 | 2001:db8:35::5 | 3 |

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
- IPv4 addressing on all interfaces and loopbacks
- `no ip domain-lookup` on all routers
- OSPFv2 process 1 fully functional: multiarea, R1-R5, all adjacencies Full (carried forward from lab-01)

**IS NOT pre-loaded** (student configures this):
- `ipv6 unicast-routing` global command on each router
- IPv6 addresses on all interfaces and loopbacks
- OSPFv3 process (router-id, process definition)
- OSPFv3 area assignments per interface (`ospfv3 1 ipv6 area X`)

> **Additive rule:** Do not remove or modify any IPv4 or OSPFv2 configuration from lab-01. This lab adds IPv6 and OSPFv3 only. At the end, OSPFv2 and OSPFv3 must both show Full adjacency on every link simultaneously.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IPv6 Unicast Routing and Add IPv6 Addresses

On every router, enable IPv6 forwarding and configure IPv6 addresses on all interfaces (loopbacks and routed links) according to the address plan in Section 3. Do not modify any existing IPv4 configuration.

**Verification:** `show ipv6 interface brief` on each router must show all interfaces as `[UP/UP]` with their assigned IPv6 addresses.

---

### Task 2: Activate OSPFv3 on R1, R2, and R3

Start the OSPFv3 process on R1, R2, and R3 with router-IDs matching their OSPFv2 router-IDs (10.0.0.1, 10.0.0.2, 10.0.0.3). Assign each interface to the same OSPF area that it uses under OSPFv2:
- R1: loopback0, loopback1, and Gi0/0 all in Area 1
- R2: loopback0 and Gi0/1 in Area 0; Gi0/0 in Area 1
- R3: loopback0 and Gi0/0 in Area 0; Gi0/1 in Area 2; Gi0/2 in Area 3

**Verification:** `show ospfv3 neighbor` on R2 must show R1 (Area 1) and R3 (Area 0) as Full neighbors. `show ospfv3` on R2 must show the "Area Border Router" designation.

---

### Task 3: Extend OSPFv3 to R4 and R5

Activate OSPFv3 on R4 (router-id 10.0.0.4) and R5 (router-id 10.0.0.5). Assign their loopbacks and uplinks to the correct areas. Confirm both reach Full adjacency with R3.

**Verification:** `show ospfv3 neighbor` on R3 must show R4 (Area 2) and R5 (Area 3) as Full. On R1, `show ipv6 route ospf` must show R4 and R5 loopbacks as inter-area routes (`OI`).

---

### Task 4: Verify Dual-Stack Adjacency and LSA Database

Confirm that OSPFv2 and OSPFv3 adjacencies are simultaneously Full on all four links, and inspect the OSPFv3 LSDB to identify Link-LSAs (Type-8) and Intra-Area Prefix-LSAs (Type-9):
- Verify all OSPFv2 adjacencies remain Full (no disruption from OSPFv2 during the IPv6 additions)
- Verify all OSPFv3 adjacencies are Full
- Run `show ospfv3 database` on any router and identify at least one Type-8 and one Type-9 LSA

**Verification:** `ping 2001:db8:4::1 source loopback0` from R1 must succeed 5/5. `show ip ospf neighbor` must still show all four neighbors as Full (IPv4 unaffected).

---

### Task 5: Diagnose an OSPFv3 Adjacency Failure

A colleague introduces a fault: one link loses its OSPFv3 adjacency while the IPv4/OSPFv2 adjacency on the same link stays Full. Using only `show` commands, identify which interface is missing its `ospfv3 1 ipv6 area X` assignment and restore Full adjacency.

**Verification:** `show ospfv3 neighbor` on all routers must show all four neighbors as Full. `ping 2001:db8:5::1 source loopback0` from R1 must succeed 5/5.

---

## 6. Verification & Analysis

### Task 2 — OSPFv3 Adjacency on R2

```
R2# show ospfv3 neighbor
          OSPFv3 1 address-family ipv6 (router-id 10.0.0.2)

Neighbor ID     Pri   State           Dead Time   Interface ID    Interface
10.0.0.1          1   FULL/DR         00:00:34    4               GigabitEthernet0/0  ! ← R1 Full in Area 1
10.0.0.3          1   FULL/DR         00:00:38    4               GigabitEthernet0/1  ! ← R3 Full in Area 0

R2# show ospfv3 | include Border
  This router is a Border router            ! ← OSPFv3 ABR designation confirmed
```

### Task 3 — Inter-Area IPv6 Routes on R1

```
R1# show ipv6 route ospf
...
OI  2001:DB8::2/128 [110/2]
     via FE80::R2, GigabitEthernet0/0     ! ← R2 lo0 via OSPFv3 inter-area (OI)
OI  2001:DB8::4/128 [110/4]
     via FE80::R2, GigabitEthernet0/0     ! ← R4 lo0 inter-area
OI  2001:DB8:4::/64 [110/5]
     via FE80::R2, GigabitEthernet0/0     ! ← R4 lo1 inter-area
OI  2001:DB8::5/128 [110/4]
     via FE80::R2, GigabitEthernet0/0     ! ← R5 lo0 inter-area
OI  2001:DB8:5::/64 [110/5]
     via FE80::R2, GigabitEthernet0/0     ! ← R5 lo1 inter-area
```

### Task 4 — OSPFv3 LSA Database and Dual-Stack Adjacency

```
R1# show ospfv3 database
          OSPFv3 1 address-family ipv6 (router-id 10.0.0.1)

                Router Link States (Area 1)

ADV Router       Age  Seq#       Fragment ID  Link count  Bits
10.0.0.1         142  0x80000005 0            1           B       ! ← Type-1 Router-LSA (no IPv6 addresses)
10.0.0.2         138  0x80000003 0            1           B

                Net Link States (Area 1)

ADV Router       Age  Seq#       Link ID    Rtr count
10.0.0.1         142  0x80000002 4          2          ! ← Type-2 Network-LSA (broadcast segment)

                Inter Area Prefix Link States (Area 1)

ADV Router       Age  Seq#       Prefix
10.0.0.2         135  0x80000002 2001:DB8::2/128        ! ← Type-3 from R2 (Inter-Area Prefix)
10.0.0.2         133  0x80000002 2001:DB8::4/128
10.0.0.2         131  0x80000002 2001:DB8:4::/64

                Link (Type-8) Link States (Area 1)

ADV Router       Age  Seq#       Link ID    Interface
10.0.0.1         142  0x80000002 4          GigabitEthernet0/0  ! ← Type-8: link-local + on-link prefixes
10.0.0.2         138  0x80000002 4          GigabitEthernet0/0

                Intra Area Prefix Link States (Area 1)

ADV Router       Age  Seq#       Link ID    Ref-lstype  Ref-LSID
10.0.0.1         142  0x80000003 0          0x2001      0         ! ← Type-9: R1 loopback prefixes

R1# show ip ospf neighbor
Neighbor ID     Pri   State    Dead Time  Address         Interface
10.0.0.2          1   FULL/DR  00:00:38   10.1.12.2       GigabitEthernet0/0  ! ← OSPFv2 still Full

R1# ping 2001:db8:4::1 source loopback0
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:4::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8::1
!!!!!                                                               ! ← 5/5 success
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/3/5 ms
```

---

## 7. Verification Cheatsheet

### IPv6 Interface and Unicast Routing

```
ipv6 unicast-routing
show ipv6 interface brief
```

| Command | Purpose |
|---------|---------|
| `ipv6 unicast-routing` | Global command required before any IPv6 routing protocol |
| `show ipv6 interface brief` | All IPv6 interfaces: status and configured addresses |
| `show ipv6 interface Gi0/0` | Link-local and global addresses, ND state |

> **Exam tip:** `ipv6 unicast-routing` must be configured globally before `router ospfv3` can form any adjacency. The process will start but hellos will not be sent until IPv6 forwarding is enabled.

### OSPFv3 Process and Area Assignment

```
router ospfv3 1
 router-id 10.0.0.N

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area N
```

| Command | Purpose |
|---------|---------|
| `router ospfv3 1` | Create the unified OSPFv3 process |
| `router-id A.B.C.D` | Must be IPv4-format; set explicitly to match OSPFv2 |
| `ospfv3 1 ipv6 area N` | Enable OSPFv3 IPv6 AF on the interface, assign to area N |
| `show ospfv3 interface brief` | All OSPFv3 interfaces with area, cost, state |

### OSPFv3 Neighbor and Database Verification

```
show ospfv3 neighbor
show ospfv3 database
show ospfv3 database link
show ospfv3 database prefix
```

| Command | Purpose |
|---------|---------|
| `show ospfv3 neighbor` | All OSPFv3 neighbors: state, area, interface |
| `show ospfv3 database` | Summary of all LSA types per area |
| `show ospfv3 database link` | Type-8 Link-LSAs (link-local + on-link prefixes) |
| `show ospfv3 database prefix` | Type-9 Intra-Area Prefix-LSAs |
| `show ospfv3 database summary` | Type-3 Inter-Area Prefix-LSAs |

> **Exam tip:** In OSPFv3, `show ospfv3 database` shows LSA types by name (`Router`, `Network`, `Inter Area Prefix`, `Link`, `Intra Area Prefix`). Type-8 (Link) and Type-9 (Intra Area Prefix) have no OSPFv2 equivalents — they carry all IPv6 prefix information that OSPFv2 Type-1 and Type-2 carry implicitly via their IP fields.

### IPv6 Routing Table

```
show ipv6 route
show ipv6 route ospf
```

| Command | Purpose |
|---------|---------|
| `show ipv6 route ospf` | All OSPF IPv6 routes: `O` intra-area, `OI` inter-area |
| `show ipv6 route <prefix>` | Specific IPv6 prefix lookup |

### OSPFv3 vs OSPFv2 LSA Comparison

| OSPFv2 Type | OSPFv3 Equivalent | Key Difference |
|-------------|-------------------|----------------|
| Type-1 Router-LSA | Type-1 Router-LSA | OSPFv3 Type-1 has NO IP addresses |
| Type-2 Network-LSA | Type-2 Network-LSA | OSPFv3 Type-2 has NO IP addresses |
| Type-3 Summary-LSA (prefix) | Type-3 Inter-Area Prefix-LSA | Same role, IPv6 prefixes |
| *(no equivalent)* | Type-8 Link-LSA | Link-local address + on-link prefixes |
| *(no equivalent)* | Type-9 Intra-Area Prefix-LSA | All IPv6 prefix info (stubs + transit) |

### Common OSPFv3 Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| OSPFv3 process started but no neighbors | `ipv6 unicast-routing` missing |
| One side has neighbor, other does not | Missing `ospfv3 1 ipv6 area X` on one interface |
| Adjacency fails after OSPFv2 is Full | Area ID mismatch in `ospfv3 1 ipv6 area X` on one side |
| IPv6 routes absent from table | OSPFv3 adjacency Full but wrong area (prefixes excluded) |
| `show ospfv3` shows Internal, not Border | Router missing an interface assignment in a second area |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Enable IPv6 and Add Addresses (example: R1)

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ipv6 unicast-routing

interface Loopback0
 ipv6 address 2001:db8::1/128

interface Loopback1
 ipv6 address 2001:db8:1::1/64

interface GigabitEthernet0/0
 ipv6 address 2001:db8:12::1/64
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 interface brief
```
</details>

---

### Task 2: Activate OSPFv3 on R1, R2, R3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospfv3 1
 router-id 10.0.0.1

interface Loopback0
 ospfv3 1 ipv6 area 1

interface Loopback1
 ospfv3 1 ipv6 area 1

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 1
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — ABR: Lo0 and Gi0/1 in Area 0, Gi0/0 in Area 1
router ospfv3 1
 router-id 10.0.0.2

interface Loopback0
 ospfv3 1 ipv6 area 0

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 1

interface GigabitEthernet0/1
 ospfv3 1 ipv6 area 0
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — ABR: Lo0 and Gi0/0 in Area 0; Gi0/1 in Area 2; Gi0/2 in Area 3
router ospfv3 1
 router-id 10.0.0.3

interface Loopback0
 ospfv3 1 ipv6 area 0

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 0

interface GigabitEthernet0/1
 ospfv3 1 ipv6 area 2

interface GigabitEthernet0/2
 ospfv3 1 ipv6 area 3
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospfv3 neighbor
show ospfv3 | include Border
```
</details>

---

### Task 3: Extend OSPFv3 to R4 and R5

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospfv3 1
 router-id 10.0.0.4

interface Loopback0
 ospfv3 1 ipv6 area 2

interface Loopback1
 ospfv3 1 ipv6 area 2

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 2
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router ospfv3 1
 router-id 10.0.0.5

interface Loopback0
 ospfv3 1 ipv6 area 3

interface Loopback1
 ospfv3 1 ipv6 area 3

interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 3
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospfv3 neighbor
show ipv6 route ospf
ping 2001:db8:4::1 source loopback0
ping 2001:db8:5::1 source loopback0
```
</details>

---

### Task 4: Dual-Stack and LSA Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Confirm both protocols Full
show ip ospf neighbor
show ospfv3 neighbor

! Find Type-8 and Type-9 LSAs
show ospfv3 database link
show ospfv3 database prefix

! End-to-end IPv6 ping
ping 2001:db8:4::1 source loopback0
ping 2001:db8:5::1 source loopback0
```
</details>

---

### Task 5: OSPFv3 Adjacency Fault Diagnosis

<details>
<summary>Click to view Diagnosis Approach</summary>

```bash
! Step 1 — find which OSPFv3 adjacency is missing
show ospfv3 neighbor

! Step 2 — check ospfv3 interface state on both sides of the affected link
show ospfv3 interface brief    ! run on each router

! Step 3 — if one side shows the interface but the other does not,
! the missing side lacks the 'ospfv3 1 ipv6 area X' command
show running-config interface GigabitEthernet0/0   ! look for ospfv3 line
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On the router with the missing assignment (example: R5 Gi0/0 removed from Area 3)
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 3
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

### Ticket 1 — R4 Has No OSPFv3 Neighbors

Operations reports R4's IPv6 routing table is empty. R4's IPv4 adjacency with R3 is Full, but `show ospfv3 neighbor` on R4 shows nothing. Pings from R1 to 2001:db8:4::1 fail.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ospfv3 neighbor` on R4 shows R3 as Full. `ping 2001:db8:4::1 source loopback0` from R1 succeeds 5/5.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R4 — check whether OSPFv3 is assigned to any interface
show ospfv3 interface brief
! If Gi0/0 is absent → ospfv3 1 ipv6 area 2 was removed from R4 Gi0/0

! On R3 — confirm R3 Gi0/1 is still in OSPFv3 Area 2
show ospfv3 interface GigabitEthernet0/1
! If R3 shows Area 2 but R4 shows no ospfv3 interface → fault is on R4
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R4 — restore the missing ospfv3 area assignment
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 2
```
</details>

---

### Ticket 2 — R1 Cannot Reach R5 via IPv6 but IPv4 Works

R1 can ping 10.0.0.5 (IPv4) but `ping 2001:db8::5 source loopback0` fails. `show ospfv3 neighbor` on R3 shows R4 as Full but R5 is absent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ospfv3 neighbor` on R3 shows R5 as Full. `ping 2001:db8::5 source loopback0` from R1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R5 — check ipv6 unicast-routing and ospfv3 interfaces
show ipv6 interface brief
! If Gi0/0 shows [UP/UP] with IPv6 address but is absent from OSPFv3 → check interface config

show ospfv3 interface brief
! If empty or Gi0/0 missing → ospfv3 1 ipv6 area 3 was removed

! Alternatively check running-config
show running-config interface GigabitEthernet0/0
! The ospfv3 1 ipv6 area 3 line will be absent
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R5 — restore ospfv3 on Gi0/0
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 3
```
</details>

---

### Ticket 3 — R2 Not Advertising IPv6 Inter-Area Prefixes for Area 1

R3 can reach 2001:db8::2/128 (R2 lo0) but has no route to 2001:db8::1/128 (R1 lo0) or 2001:db8:1::/64 (R1 lo1). R2's OSPFv3 neighbor with R1 shows Full, but R2 is no longer generating Type-3 Inter-Area Prefix-LSAs for Area 1 prefixes into Area 0.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ospfv3 database summary` on R3 shows Type-3 LSAs for 2001:db8::1/128 and 2001:db8:1::/64 with advertising router 10.0.0.2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! On R2 — check OSPFv3 role
show ospfv3 | include Border
! If output shows "Internal router" → R2 has only one OSPFv3 area active

! On R2 — check interface area assignments
show ospfv3 interface brief
! Gi0/0 must show Area 1 and Gi0/1 must show Area 0
! If both show Area 0 → Gi0/0 ospfv3 assignment was changed from area 1 to area 0

show running-config interface GigabitEthernet0/0
! The ospfv3 1 ipv6 area line will show area 0 instead of area 1
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2 — restore Gi0/0 to Area 1
interface GigabitEthernet0/0
 no ospfv3 1 ipv6 area 0
 ospfv3 1 ipv6 area 1
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ipv6 unicast-routing` enabled on all five routers
- [ ] All interfaces have correct IPv6 addresses per the address plan
- [ ] `router ospfv3 1` with matching router-id configured on all five routers
- [ ] All interfaces assigned to their OSPFv3 areas via `ospfv3 1 ipv6 area X`
- [ ] `show ospfv3 neighbor` shows all four adjacencies as Full
- [ ] `show ospfv3` on R2 shows "Border router"
- [ ] `show ospfv3` on R3 shows three areas (0, 2, 3) and "Border router"
- [ ] `show ospfv3 database` shows Type-8 (Link) and Type-9 (Intra Area Prefix) LSAs
- [ ] `ping 2001:db8:4::1 source loopback0` from R1 succeeds 5/5
- [ ] `ping 2001:db8:5::1 source loopback0` from R1 succeeds 5/5
- [ ] `show ip ospf neighbor` still shows all OSPFv2 adjacencies as Full (no regression)

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved (missing `ospfv3 1 ipv6 area 2` on R4 Gi0/0)
- [ ] Ticket 2 diagnosed and resolved (missing `ospfv3 1 ipv6 area 3` on R5 Gi0/0)
- [ ] Ticket 3 diagnosed and resolved (R2 Gi0/0 area 0 instead of area 1 in OSPFv3)

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
