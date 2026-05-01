# Lab 01: Multilevel IS-IS and Route Advertisement

**Topic:** IS-IS Routing | **Exam:** 300-510 SPRI | **Blueprint:** 1.3, 1.3.a
**Difficulty:** Intermediate | **Time:** 75 minutes | **Type:** Progressive (lab-01 of 5)

---

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

**Exam Objective:** 1.3 — Troubleshoot IS-IS multilevel operations (IPv4 and IPv6); 1.3.a — Route advertisement

This lab evolves the single-area L1 domain from lab-00 into a two-area multilevel IS-IS topology.
You will promote two routers to L1/L2, move one router into a new area, bring up two new L1
routers, and observe how the IS-IS backbone automatically installs default routes into L1 areas via
the ATT bit — without any explicit redistribution command. The end state maps exactly to the
canonical SP-core IS-IS design: a flat L2 backbone connecting two L1 stub areas.

### IS-IS Router Levels — L1-Only, L2-Only, and L1/L2

IS-IS supports three router-level modes, set globally with `is-type`:

| `is-type` | Role | Databases maintained | Forms adjacency with |
|-----------|------|----------------------|----------------------|
| `level-1` | Stub router — intra-area only | L1 LSDB only | Other L1 and L1/L2 routers **in the same area** |
| `level-1-2` | ABR equivalent — sees both areas | L1 LSDB + L2 LSDB | L1 neighbours (same area) and L2 neighbours (any area) |
| `level-2-only` | Backbone-only router — no area membership | L2 LSDB only | Other L2 and L1/L2 routers |

In this lab, R2 and R3 are `level-1-2`. They each maintain **two separate LSDBs**:
one for their local L1 area and one shared L2 database. R1 is L1-only in area 49.0001;
R4 and R5 are L1-only in area 49.0002.

> **Exam tip:** An L1/L2 router is NOT the same as an L1 and an L2 router merged. It is
> a single router with two independent SPF calculations — one per database. Route leaking
> between the two databases requires explicit configuration (`redistribute isis ip level-2
> into level-1`), which arrives in lab-02.

### The ATT Bit — IS-IS Implicit Default Route

The ATT (Attached) bit is a single flag inside an L1 LSP. An L1/L2 router sets this bit
in its **L1 LSP** when it has at least one working L2 adjacency. L1-only routers that see
an ATT-bit-set LSP install a `0.0.0.0/0` default route pointing at that router.

```
R2 (L1/L2, area 49.0001)         R3 (L1/L2, area 49.0002)
     L1 LSDB floods ATT=1              L1 LSDB floods ATT=1
          ↓                                    ↓
R1 installs default: 0.0.0.0/0        R4 and R5 install default: 0.0.0.0/0
via 10.1.12.2 (R2)                    via 10.1.34.3 / 10.1.35.3 (R3)
```

Key ATT-bit behaviours to know for the 300-510 exam:

- The ATT bit is set automatically — no user configuration needed
- If the L1/L2 router loses all L2 adjacencies, the ATT bit clears and the default route withdraws
- Only one default route per L1 area (if multiple L1/L2 routers exist, the L1 router picks the closest one)
- The ATT bit only propagates within the L1 LSDB — it does not affect the L2 LSDB

### L1/L2 Adjacency Rules — Why R2↔R3 Is L2-Only

IS-IS adjacency formation depends on the level and the area:

| Scenario | L1 adjacency | L2 adjacency |
|----------|-------------|--------------|
| Same area, both `level-1` or `level-1-2` | Forms | N/A |
| Different areas, both `level-1-2` | **Never** (area IDs must match) | **Forms** (no area restriction) |
| One `level-1`, one `level-2-only` | Never | Never (no common level) |
| One `level-1`, one `level-1-2`, same area | Forms | Does not form (L1 only sends L1 Hellos) |

Between R2 (area 49.0001) and R3 (area 49.0002), the area IDs differ — so L1 adjacency is
impossible. Both are `level-1-2`, so L2 adjacency forms without restriction. Setting
`isis circuit-type level-2-only` on the interconnecting interfaces makes this explicit and
suppresses unnecessary L1 Hello traffic.

### Inter-Area Route Advertisement via the L2 LSDB

Once R2 and R3 form an L2 adjacency, they flood their L1 reachable prefixes **up** into the
L2 LSDB automatically. The mechanism:

1. R2 takes every prefix from its L1 LSDB (area 49.0001 reachable) and re-originates them
   into its L2 LSP — this is the **L1→L2 route injection** that happens automatically on every L1/L2 router.
2. R3 does the same for area 49.0002 prefixes.
3. R3 then **down-floods** the L2-learned prefixes into its L1 area via ATT bit (default route only,
   not specific prefixes — specific prefix leaking requires explicit config in lab-02).

The practical effect: R1 can ping R4's Loopback via the default route; R4 can ping R1's Loopback
via its own default route. No OSPF redistribution, no BGP — just IS-IS levels doing the work.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| is-type promotion | Upgrade a router from `level-1` to `level-1-2` without disrupting existing L1 peers |
| NET area change | Move a router between areas by changing the area field in the NET |
| L2 circuit configuration | Apply `isis circuit-type level-2-only` to constrain a link to the backbone level |
| ATT bit analysis | Use `show isis database detail` to locate and interpret the ATT bit in L1 LSPs |
| Default route tracing | Confirm that `0.0.0.0/0` is installed in the L1 RIB and trace it to the ATT source |
| Inter-area route verification | Trace a specific prefix from one area's L1 LSDB through the L2 backbone to the other area |
| L1/L2 LSDB comparison | Inspect both the L1 and L2 databases on R2/R3 to see which prefixes appear in each |

---

## 2. Topology & Scenario

**Scenario:** SP-Core Ltd has approved the IS-IS expansion plan. The three-router
single-area topology from lab-00 is the starting point. You must split the domain into
two areas (49.0001 and 49.0002), promote the border routers to L1/L2, and add two new
L1 stub routers (R4 and R5) in area 49.0002. The operations team wants to confirm that
R1's Loopback1 (172.16.1.0/24) is reachable from R4 and R5 using only IS-IS, and that
the ATT bit mechanism provides a default route to all L1-only routers without any manual
redistribution.

> **Design note:** lab-00 placed all three routers in area 49.0001 as L1-only for a clean
> single-LSDB baseline. Lab-01 is where the real IS-IS architecture begins — two areas,
> one L2 backbone adjacency, and the ATT bit in action. R4 and R5 are pure L1 stub routers;
> they have no L2 capability and rely entirely on R3's ATT bit for inter-area reachability.

```
            Area 49.0001                              Area 49.0002
  ┌────────────────────────────┐    ┌────────────────────────────────────────┐
  │                            │    │                                        │
  │  ┌──────────────────────┐  │    │  ┌──────────────────────┐             │
  │  │          R1          │  │    │  │          R3          │             │
  │  │     (L1 router)      │  │    │  │    (L1/L2 router)    │             │
  │  │  NET: ...0001.00     │  │    │  │  NET: 49.0002....    │             │
  │  │  Lo0: 10.0.0.1/32    │  │    │  │  Lo0: 10.0.0.3/32   │             │
  │  │  Lo1: 172.16.1.1/24  │  │    │  └──────┬──────┬───────┘             │
  │  └──────────┬───────────┘  │    │         │      │                      │
  │             │ Gi0/0        │    │      Gi0/1  Gi0/2                     │
  │             │ 10.1.12.1/24 │    │   10.1.34.3 10.1.35.3                 │
  │             │              │    │      /24        /24                   │
  │             │ 10.1.12.2/24 │    │   10.1.34.4 10.1.35.5                 │
  │             │ Gi0/0        │    │    Gi0/0       Gi0/0                  │
  │  ┌──────────┴───────────┐  │    │  ┌──────┴───┐  ┌──────┴────┐         │
  │  │          R2          │  │    │  │    R4    │  │    R5     │         │
  │  │   (L1/L2 router)    │  │    │  │ (L1 rtr) │  │ (L1 rtr)  │         │
  │  │  NET: 49.0001....   │  │    │  │ Lo0:     │  │ Lo0:      │         │
  │  │  Lo0: 10.0.0.2/32  │  │    │  │10.0.0.4  │  │10.0.0.5   │         │
  │  └──────────┬──────────┘  │    │  │ Lo1:     │  │ Lo1:      │         │
  └─────────────┼─────────────┘    │  │172.16.4.1│  │172.16.5.1 │         │
                │ Gi0/1            │  └──────────┘  └───────────┘         │
                │ 10.1.23.2/24     └────────────────────────────────────────┘
                │ (L2-only)
                │ 10.1.23.3/24
                │ Gi0/0
  ┌─────────────┴───────────────────────────────────────────────────────────┐
  │    L2 backbone (single adjacency — R2 Gi0/1 ↔ R3 Gi0/0, 10.1.23.0/24) │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | L1 stub router, area 49.0001 | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R2 | L1/L2 border router, area 49.0001 side | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R3 | L1/L2 border router, area 49.0002 side | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R4 | L1 stub router, area 49.0002 | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R5 | L1 stub router, area 49.0002 | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router identity, IS-IS system ID source |
| R1 | Loopback1 | 172.16.1.1/24 | Inter-area reachability test prefix |
| R2 | Loopback0 | 10.0.0.2/32 | Router identity |
| R3 | Loopback0 | 10.0.0.3/32 | Router identity |
| R4 | Loopback0 | 10.0.0.4/32 | Router identity |
| R4 | Loopback1 | 172.16.4.1/24 | Inter-area reachability test prefix |
| R5 | Loopback0 | 10.0.0.5/32 | Router identity |
| R5 | Loopback1 | 172.16.5.1/24 | Inter-area reachability test prefix |

### Cabling

| Link | Source | Interface | Target | Interface | Subnet | IS-IS Level |
|------|--------|-----------|--------|-----------|--------|-------------|
| L1 | R1 | GigabitEthernet0/0 | R2 | GigabitEthernet0/0 | 10.1.12.0/24 | L1 |
| L2 | R2 | GigabitEthernet0/1 | R3 | GigabitEthernet0/0 | 10.1.23.0/24 | L2-only (backbone) |
| L3 | R3 | GigabitEthernet0/1 | R4 | GigabitEthernet0/0 | 10.1.34.0/24 | L1 |
| L4 | R3 | GigabitEthernet0/2 | R5 | GigabitEthernet0/0 | 10.1.35.0/24 | L1 |

### Console Access

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial-configs and discover ports automatically.

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames (R1–R5)
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all routers
- IS-IS process `CORE` with `is-type level-1` and `metric-style wide` on R1, R2, and R3 (carried forward from lab-00)
- Per-interface `ip router isis CORE` and `isis circuit-type level-1` on all IS-IS-enabled interfaces of R1, R2, and R3 (carried forward from lab-00)

**IS NOT pre-loaded** (student configures this):

- Promotion of R2 and R3 from `level-1` to `level-1-2`
- R3 NET change from area 49.0001 to area 49.0002
- `isis circuit-type level-2-only` on the R2↔R3 backbone link (both ends)
- IS-IS enablement on R3's new interfaces (GigabitEthernet0/1 and 0/2)
- IS-IS routing process, NET, and per-interface enablement on R4 and R5

> **Note:** R4 and R5 start with IP addressing only. R1 starts with a complete lab-00
> IS-IS config; R2 and R3 start with their lab-00 L1-only configs. The student's job is
> to surgically upgrade the existing config and add the two new routers.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Promote R2 and R3 to L1/L2 and Separate the Areas

- On R2, change the router-wide level to Level-1/Level-2 (`is-type level-1-2`). The NET remains `49.0001.0000.0000.0002.00` — R2 stays in area 49.0001 on the L1 side.
- On R3, change the router-wide level to Level-1/Level-2 and update the NET to move R3 from area 49.0001 to area 49.0002 — the new NET is `49.0002.0000.0000.0003.00`. Remove the old NET first, then add the new one.
- On the backbone link (R2 GigabitEthernet0/1 and R3 GigabitEthernet0/0), constrain IS-IS to Level-2 only on both interfaces. This makes the inter-area link explicit and stops unnecessary L1 Hello traffic between different areas.

**Verification:** `show clns neighbors` on R2 must show R1 in state Up (L1) and R3 in state Up (L2). `show isis neighbors detail` for R3 must show R2 with `Area Address(es): 49.0001` — confirming R2 and R3 are in different areas but still forming an L2 adjacency.

---

### Task 2: Add R4 and R5 as L1 Stub Routers in Area 49.0002

- On R4, create an IS-IS routing process named `CORE`, assign NET `49.0002.0000.0000.0004.00`, set `is-type level-1`, and enable `metric-style wide`.
- Enable IS-IS on R4's Loopback0, Loopback1, and GigabitEthernet0/0 at the `level-1` circuit type. Make both loopbacks passive.
- On R5, repeat with NET `49.0002.0000.0000.0005.00` and the same level, metric-style, and passive loopback settings.
- On R3, enable IS-IS on GigabitEthernet0/1 (→R4) and GigabitEthernet0/2 (→R5) at the `level-1` circuit type.

**Verification:** `show clns neighbors` on R3 must show R4 and R5 in state Up (L1). `show isis database` on R4 must show four LSPs in the L1 database — R3.00-00, R4.00-00, R5.00-00, and at least one pseudonode LSP.

---

### Task 3: Verify the ATT Bit and Default Route Installation

- On R2, inspect the L1 LSDB to confirm R2's own LSP has the ATT bit set (ATT=1 in the LSP flags). R2 sets ATT=1 because it now has a working L2 adjacency to R3.
- On R3, confirm the same ATT=1 in R3's L1 LSP within the L2 database, and that R3's L1 LSP in area 49.0002 also has ATT=1.
- On R1, verify that a default route `0.0.0.0/0` has been installed via R2's address on the R1↔R2 link. This default was not manually configured — it was triggered automatically by the ATT bit.
- On R4 and R5, confirm the same default route installation pointing at R3.

**Verification:** `show ip route` on R1 must show `i*L1 0.0.0.0/0 [115/20] via 10.1.12.2`. `show isis database R2.00-00 detail` on R1 must show `ATT/P/OL` flags as `1/0/0` in the LSP header line.

---

### Task 4: Trace Inter-Area Route Advertisement

- On R4, run `show ip route isis`. You will **not** see a specific entry for 172.16.1.0/24 — this is correct. R4 is an L1-only router; it receives only intra-area prefixes and the ATT-bit default route. It reaches R1's Loopback1 by forwarding to `0.0.0.0/0 via 10.1.34.3`. Explicit inter-area prefix leaking requires `redistribute isis ip level-2 into level-1`, which is covered in lab-02.
- On R2, run `show isis database R1.00-00 detail` to find 172.16.1.0/24 in R1's L1 LSP (advertised within area 49.0001). Then run `show isis database R2.00-00 detail level-2` to confirm R2 has re-originated that prefix into its L2 LSP (flooded up into the backbone). Note: `show isis database` without `detail` only shows LSP headers — prefix entries are hidden until you add `detail`.
- Confirm end-to-end reachability: ping R4's Loopback1 (172.16.4.1) from R1's Loopback1 (172.16.1.1) using a sourced ping.

**Verification:** `show ip route 172.16.4.0` on R1 must show the prefix reachable via 10.1.12.2 (the default route via R2). `ping 172.16.4.1 source 172.16.1.1` from R1 must succeed. `ping 172.16.1.1 source 172.16.4.1` from R4 must also succeed — R4 forwards via `0.0.0.0/0`, not a specific route.

---

### Task 5: Compare L1 and L2 LSDB Content on R2

- On R2, run `show isis database level-1` and `show isis database level-2` separately.
- Identify which LSPs are unique to each database: the L1 LSDB should contain R1, R2, and pseudonode LSPs for area 49.0001; the L2 LSDB should contain R2, R3, and the inter-area prefixes from both areas.
- Confirm that R4 and R5 do **not** appear in R2's L2 LSDB directly — only R3's L2 LSP carries their reachable prefixes as aggregated entries.

**Verification:** `show isis database level-1` on R2 must show R1.00-00, R2.00-00, and pseudonode LSPs; it must NOT show R3.00-00, R4.00-00, or R5.00-00. `show isis database level-2` on R2 must show R2.00-00 and R3.00-00 (and possibly their fragments), and must NOT show R1.00-00.

---

## 6. Verification & Analysis

### Adjacency Overview on R2 (Central Router)

```
R2# show clns neighbors

System Id      Interface     SNPA                State  Holdtime  Type Protocol
R1             Gi0/0         5000.0001.0000      Up     27        L1   IS-IS
R3             Gi0/1         5000.0003.0000      Up     28        L2   IS-IS
! ← R1 is L1 (same area 49.0001) — Type shows L1
! ← R3 is L2 (different area 49.0002, backbone link) — Type shows L2
! ← Both in state Up; no L1L2 here because the backbone link is level-2-only
```

### L2 Adjacency Detail (R2↔R3 Backbone)

```
R2# show isis neighbors detail

System Id      Type Interface     IP Address      State Holdtime Circuit Id
R3             L2   Gi0/1         10.1.23.3       UP    28       R2.02
  Area Address(es): 49.0002
  SNPA: 5000.0003.0000
  IPv4 Address(es):  10.1.23.3
  Hello Interval: 10 s, Hello Multiplier: 3
! ← Area Address 49.0002 — different from R2's own 49.0001; L2 ignores this
! ← Circuit Id R2.02 = pseudonode byte assigned for this LAN circuit
! ← Type L2 confirms isis circuit-type level-2-only is effective on both ends
```

### ATT Bit in R2's L1 LSP

```
R2# show isis database R2.00-00 detail

IS-IS Level-1 Link State Database:
R2.00-00            0x00000006   0xF3A1        1150          1/0/0
  Area Address: 49.0001                          ! ← R2's area
  Hostname:     R2
  IP Address:   10.0.0.2
  Metric: 10        IP-Extended 10.0.0.2/32
  Metric: 10        IP-Extended 10.1.12.0/24
  Metric: 10        IP-Extended 10.1.23.0/24
  Metric: 10        IS-Extended R1.01            ! ← neighbour via pseudonode

!  ATT/P/OL = 1/0/0 ← ATT bit is SET (R2 has a working L2 adjacency to R3)
!  This ATT=1 tells R1 "I have L2 connectivity — use me as your default gateway"
```

### Default Route on R1 (ATT Bit Effect)

```
R1# show ip route

Gateway of last resort is 10.1.12.2 to network 0.0.0.0

i*L1  0.0.0.0/0 [115/20] via 10.1.12.2, GigabitEthernet0/0
                                              ! ← i*L1 = IS-IS Level-1 default
      10.0.0.0/8 is variably subnetted
i L1  10.0.0.2/32 [115/20] via 10.1.12.2, GigabitEthernet0/0
i L1  10.0.0.3/32 [115/30] via 10.1.12.2, GigabitEthernet0/0
i L1  10.1.23.0/24 [115/20] via 10.1.12.2, GigabitEthernet0/0
      172.16.0.0/24 is subnetted
C        172.16.1.0 is directly connected, Loopback1

! 10.0.0.3/32 and inter-area routes reach R1 because R2's L2 LSP re-originates them
! into the L1 database automatically (L2->L1 injection for directly connected L2 prefixes)
! Note: R4/R5 loopbacks are NOT here as specific routes — R1 uses 0.0.0.0/0 to reach them
```

### R4's Adjacency and Default Route

```
R4# show clns neighbors

System Id      Interface     SNPA                State  Holdtime  Type Protocol
R3             Gi0/0         5000.0003.0001      Up     25        L1   IS-IS
! ← Only one neighbour — R3 is R4's sole IS-IS peer (L1, same area 49.0002)

R4# show ip route
i*L1  0.0.0.0/0 [115/20] via 10.1.34.3, GigabitEthernet0/0
! ← Default route via R3's ATT bit — identical mechanism to R1/R2, different area
```

### L2 LSDB on R2 (Backbone Database)

```
R2# show isis database level-2

IS-IS Level-2 Link State Database:
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime  ATT/P/OL
R2.00-00              0x00000003   0x7B4C        1160          0/0/0
R3.00-00              0x00000004   0x2D91        1150          0/0/0

! Only R2 and R3 in the L2 database — this is the entire IS-IS backbone
! R1, R4, R5 are L1-only and do NOT appear in the L2 LSDB
! R2's L2 LSP carries area-49.0001 prefixes; R3's carries area-49.0002 prefixes
```

### End-to-End Reachability

```
R1# ping 172.16.4.1 source 172.16.1.1 repeat 5
!!!!!     ! ← R1 Lo1 → R4 Lo1 via ATT default route through R2→R3

R4# ping 172.16.1.1 source 172.16.4.1 repeat 5
!!!!!     ! ← Symmetric: R4 Lo1 → R1 Lo1 via ATT default route through R3→R2
```

---

## 7. Verification Cheatsheet

### is-type Promotion and NET Change

```
router isis CORE
 is-type level-1-2
 no net 49.0001.0000.0000.0003.00   ! remove old NET first (R3 only)
 net 49.0002.0000.0000.0003.00       ! apply new area NET (R3 only)
```

| Command | Purpose |
|---------|---------|
| `is-type level-1-2` | Promote router to participate in both L1 and L2; creates second LSDB |
| `no net <old-net>` | Remove the existing NET before changing area — avoid running dual NETs |
| `net <new-net>` | Assign the new NET (area change takes effect immediately) |

> **Exam tip:** You can have up to three NETs on one router simultaneously (for area
> renumbering migrations). During normal operation, one NET is the standard. Always
> remove the old NET after confirming the new area adjacency is stable.

### Backbone Link (Level-2-Only Circuit)

```
interface GigabitEthernet0/1
 ip router isis CORE
 isis circuit-type level-2-only
```

| Command | Purpose |
|---------|---------|
| `isis circuit-type level-2-only` | Suppress L1 Hellos on this interface; only L2 Hellos are sent/processed |
| `isis circuit-type level-1` | Default on a `level-1-2` router — sends both L1 and L2 Hellos |
| `isis circuit-type level-1-2` | Explicit equivalent of the default for clarity |

> **Exam tip:** On an inter-area link between two `level-1-2` routers, NOT setting
> `level-2-only` still works — the L1 adjacency attempt will fail (area mismatch) and
> only the L2 adjacency forms. But the failed L1 Hello attempts generate log noise and
> waste CPU. Best practice is always to be explicit.

### ATT Bit Verification

```
show isis database <router-lspid> detail   ! find ATT/P/OL flags in LSP header
show ip route                              ! look for i*L1 0.0.0.0/0
show isis database level-1                 ! L1-only view
show isis database level-2                 ! L2-only view (backbone)
```

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | State Up; Type column: L1, L2, or L1L2 |
| `show isis neighbors detail` | Area Address(es) line — confirms area and level |
| `show isis database R2.00-00 detail` | ATT/P/OL header field — 1/0/0 means ATT is set |
| `show ip route` | `i*L1 0.0.0.0/0` entry — ATT-bit default route |
| `show isis database level-1` | Area-local prefixes only |
| `show isis database level-2` | Backbone prefixes — should only show L1/L2 routers |
| `ping X.X.X.X source Lo1` | End-to-end reachability across areas |

### NET Format Quick Reference

| NET | Decoded |
|-----|---------|
| `49.0001.0000.0000.0001.00` | AFI=49, area=0001, system-ID=0000.0000.0001, NSEL=00 |
| `49.0001.0000.0000.0002.00` | Same area (49.0001); R2 |
| `49.0002.0000.0000.0003.00` | **Different area (49.0002)**; R3 after promotion |
| `49.0002.0000.0000.0004.00` | Area 49.0002; R4 |
| `49.0002.0000.0000.0005.00` | Area 49.0002; R5 |

### Common IS-IS Multilevel Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| R2↔R3 stuck in INIT (L2 only) | `isis circuit-type level-1` on one or both backbone interfaces — no L2 Hellos sent |
| R2↔R3 no adjacency at all | `is-type level-1` left on R2 or R3 — router doesn't send L2 Hellos |
| No default route on R1 | R2's L2 adjacency is down — ATT bit clears automatically |
| R4/R5 missing from R3's L1 LSDB | Missing `ip router isis CORE` on R3 Gi0/1 or Gi0/2 |
| R4 has no default route | R3 not promoting to L1/L2 — check `is-type` on R3 |
| 172.16.1.0/24 not reachable from R4 | Default route missing (see above) or R1 Lo1 missing `ip router isis CORE` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Promote R2 and R3 to L1/L2 and Configure the Backbone Link

<details>
<summary>Click to view R2 configuration changes</summary>

```
router isis CORE
 is-type level-1-2
!
interface GigabitEthernet0/1
 isis circuit-type level-2-only
```

</details>

<details>
<summary>Click to view R3 configuration changes (area move + L1/L2 promotion)</summary>

```
router isis CORE
 no net 49.0001.0000.0000.0003.00
 net 49.0002.0000.0000.0003.00
 is-type level-1-2
!
interface GigabitEthernet0/0
 isis circuit-type level-2-only
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show clns neighbors
show isis neighbors detail
show isis database R2.00-00 detail
```

</details>

### Task 2: Add R4 and R5 as L1 Routers

<details>
<summary>Click to view R4 full IS-IS configuration</summary>

```
router isis CORE
 net 49.0002.0000.0000.0004.00
 is-type level-1
 metric-style wide
 passive-interface Loopback0
 passive-interface Loopback1
!
interface Loopback0
 ip router isis CORE
 isis circuit-type level-1
!
interface Loopback1
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis circuit-type level-1
```

</details>

<details>
<summary>Click to view R5 full IS-IS configuration</summary>

```
router isis CORE
 net 49.0002.0000.0000.0005.00
 is-type level-1
 metric-style wide
 passive-interface Loopback0
 passive-interface Loopback1
!
interface Loopback0
 ip router isis CORE
 isis circuit-type level-1
!
interface Loopback1
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis circuit-type level-1
```

</details>

<details>
<summary>Click to view R3 interface additions</summary>

```
interface GigabitEthernet0/1
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/2
 ip router isis CORE
 isis circuit-type level-1
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show clns neighbors           ! on R3: must show R4 and R5 Up (L1)
show isis database            ! on R4: must show R3, R4, R5, plus pseudonode LSPs
```

</details>

### Tasks 3 & 4: ATT Bit and Inter-Area Reachability

<details>
<summary>Click to view Verification Commands</summary>

```
! On R2 — confirm ATT bit set
show isis database R2.00-00 detail

! On R1 — confirm default route
show ip route

! End-to-end test
R1# ping 172.16.4.1 source 172.16.1.1
R4# ping 172.16.1.1 source 172.16.4.1
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and
fix using only show commands and your knowledge of IS-IS multilevel operations.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                      # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>         # restore
```

---

### Ticket 1 — R4 Has No IS-IS Neighbours and Cannot Reach R1

The NOC has reported that 10.0.0.4/32 disappeared from R3's L1 routing table. R5 is
healthy. R3 shows IS-IS running but R4 is not listed as a neighbour. R4 itself shows
the IS-IS process as active and reports it is sending Hellos.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R3 shows R4 in state Up (L1). `show ip route isis`
on R1 shows 10.0.0.4/32 reachable via the default route.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R3# show clns neighbors
! R4 is missing or in INIT — check if L1 Hellos are being exchanged

R4# show clns neighbors
! R3 may appear in INIT — area ID mismatch prevents UP

R4# show running-config | section router isis
! Inspect the NET — is the area field still 49.0002?

R3# show isis neighbors detail
! Look at Area Address(es) for any partial R4 entry — INIT means Hello passed
! Layer-2 but L1 area validation failed
```

The fault is on **R4**: its NET was changed to `49.0099.0000.0000.0004.00`. The area
field `0099` does not match R3's area `0002`, so the L1 adjacency stalls at INIT —
both sides receive Hellos but neither can advance to UP.
</details>

<details>
<summary>Click to view Fix</summary>

On R4:

```
router isis CORE
 no net 49.0099.0000.0000.0004.00
 net 49.0002.0000.0000.0004.00
```

Verify:

```
R4# show clns neighbors           ! R3 reaches state Up within ~30 s
R3# show clns neighbors           ! R4 appears in Up state
R1# show ip route isis            ! 10.0.0.4/32 reachable via default route
```

</details>

---

### Ticket 2 — R1 Has No IS-IS Routes and Cannot Reach Any Remote Prefix

After a routine maintenance window, R1 is showing only connected routes. No IS-IS
entries appear in the RIB. R2 reports IS-IS is running, but R1 shows R2 as either
DOWN or stuck in INIT on the R1↔R2 link.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R1 shows R2 in state Up (L1). `show ip route`
on R1 shows `i*L1 0.0.0.0/0` and IS-IS routes for the 10.0.0.0/8 subnets.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R1# show clns neighbors
! R2 is in INIT or absent — Hellos may be arriving but level does not match

R1# show isis neighbors detail
! If a partial entry for R2 appears, check the Type column — mismatch here
! signals that R2 is sending a different level Hello than R1 expects

R2# show running-config | section router isis
! Is is-type correct? Check for level-2-only instead of level-1-2
! A level-2-only router sends only L2 Hellos — R1 (level-1) never sees a
! matching Hello and cannot advance the adjacency past INIT
```

The fault is on **R2**: `is-type level-2-only` was applied during the maintenance window.
R2 now sends only L2 Hellos on Gi0/0. R1 is `level-1` and only processes L1 Hellos —
the two sides never agree on a level and the adjacency stays in INIT (or drops to DOWN
after the hold timer expires).
</details>

<details>
<summary>Click to view Fix</summary>

On R2:

```
router isis CORE
 is-type level-1-2
```

Verify:

```
R2# show clns neighbors           ! R1 (L1) and R3 (L2) both reach Up
R1# show ip route                 ! i*L1 0.0.0.0/0 reappears via 10.1.12.2
R1# ping 10.0.0.4 repeat 5       ! end-to-end restored
```

</details>

---

### Ticket 3 — R2 and R3 Have No L2 Adjacency; Inter-Area Routes Are Gone

A junior engineer pushed a config change to R2. The R1↔R2 L1 adjacency is healthy,
but `show ip route` on R1 no longer shows 10.0.0.4/32 or 10.0.0.5/32. R2 does not
appear in R3's neighbour list. R3 has R4 and R5 in state Up (L1).

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R2 shows R3 in state Up (L2). `show ip route`
on R1 shows the `i*L1 0.0.0.0/0` default route and 10.0.0.3/32, 10.0.0.4/32, 10.0.0.5/32.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R2# show clns neighbors
! R1 is Up (L1) — L1 side is healthy; R3 is missing or DOWN

R2# show clns interface GigabitEthernet0/1
! Check "Circuit Type" — should be Level-2-only; if it shows Level-1, R2
! is sending L1 Hellos on the inter-area link, which can never match R3's L2 Hellos

R3# show clns neighbors
! R2 is absent — R3 is configured correctly (level-2-only on Gi0/0) so it
! sends L2 Hellos; R2 is not responding with L2 Hellos

R2# show running-config interface GigabitEthernet0/1
! Look for isis circuit-type — was it changed back to level-1?
```

The fault is on **R2**: the junior engineer changed `isis circuit-type level-2-only`
back to `isis circuit-type level-1` on GigabitEthernet0/1. R2 now sends only L1 Hellos
on the backbone link. R3 sends only L2 Hellos. The levels never match and no adjacency
forms. The ATT bit on R2 clears (no L2 adjacency), causing R1's default route to withdraw.
</details>

<details>
<summary>Click to view Fix</summary>

On R2:

```
interface GigabitEthernet0/1
 isis circuit-type level-2-only
```

Verify:

```
R2# show clns neighbors           ! R3 appears in Up state (L2) within ~30 s
R2# show isis database R2.00-00 detail   ! ATT/P/OL should be 1/0/0 again
R1# show ip route                 ! i*L1 0.0.0.0/0 reappears; 10.0.0.4/32 visible
R1# ping 172.16.4.1 source 172.16.1.1   ! end-to-end reachability restored
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] R2 and R3 are `is-type level-1-2` with `metric-style wide`
- [x] R3 NET is `49.0002.0000.0000.0003.00` (old 49.0001 NET removed)
- [x] `isis circuit-type level-2-only` on R2 Gi0/1 and R3 Gi0/0
- [x] `show clns neighbors` on R2 shows R1 Up (L1) and R3 Up (L2)
- [x] R4 and R5 configured with `is-type level-1`, correct NETs, and passive loopbacks
- [x] `show clns neighbors` on R3 shows R4 and R5 Up (L1)
- [x] `show isis database R2.00-00 detail` shows ATT/P/OL = 1/0/0
- [x] `show ip route` on R1 contains `i*L1 0.0.0.0/0 via 10.1.12.2`
- [x] `show ip route` on R4 contains `i*L1 0.0.0.0/0 via 10.1.34.3`
- [x] `ping 172.16.4.1 source 172.16.1.1` from R1 succeeds (5/5)
- [x] `show isis database level-2` on R2 shows only R2.00-00 and R3.00-00

### Troubleshooting

- [x] Ticket 1 diagnosed and fixed (NET area-ID typo 49.0099 on R4)
- [x] Ticket 2 diagnosed and fixed (`is-type level-2-only` planted on R2)
- [x] Ticket 3 diagnosed and fixed (`isis circuit-type level-1` on R2 Gi0/1)
- [x] `apply_solution.py` run to confirm clean state before proceeding to lab-02

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success — all devices configured or restored | All scripts |
| 1 | Partial failure — one or more devices failed | `apply_solution.py` only |
| 2 | `--host` not provided (placeholder value detected) | All scripts |
| 3 | EVE-NG connectivity or port discovery error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
