# Lab 03 — Summarization, Stub, and NSSA

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

**Exam Objective:** 1.2.b — Summarization (OSPF multiarea operations, IPv4 and IPv6)

This lab builds on the dual-stack multiarea OSPF topology from labs 01 and 02. You will
control how routes propagate across area boundaries using OSPF summarization, reduce the
impact of external routes using ASBR summary-address, and restrict LSA types with stub
and NSSA area variants. By the end, you will understand the differences between Type-3,
Type-5, and Type-7 LSAs in the context of area design decisions.

---

### Inter-Area Summarization (ABR `area range`)

When an Area Border Router (ABR) generates Type-3 Summary LSAs for routes in a non-backbone
area, each specific prefix generates one LSA. In a large network this creates unnecessary
LSDB churn — every prefix change floods across the entire domain.

`area range` on an ABR instructs it to replace a set of specific Type-3 LSAs with a single
summarized LSA. Routers outside the summarized area see one route instead of many:

```
router ospf 1
  area 1 range 172.16.0.0 255.255.248.0   ! covers 172.16.0–7.0/24 from Area 1
```

Key behaviors:
- Configured only on the **ABR** — internal routers in the area are unaffected
- All specific prefixes falling within the range are **suppressed** from being sent into Area 0
- A **single Type-3 LSA** for the summary is advertised into Area 0 (and from there into all other areas)
- If **no specific prefix** in the range is currently active, the summary LSA is also withdrawn

For OSPFv3 (IPv6), the equivalent is placed under the address-family:
```
router ospfv3 1
  address-family ipv6 unicast
    area 1 range 2001:db8:1::/48
  exit-address-family
```

---

### External Summarization (ASBR `summary-address`)

When an ASBR redistributes external routes into OSPF, each prefix generates a Type-5 External
LSA that floods throughout the entire OSPF domain (except stub/NSSA areas). The `summary-address`
command on the ASBR collapses multiple external Type-5 LSAs into one:

```
router ospf 1
  summary-address 192.168.0.0 255.255.0.0   ! collapses all 192.168.x.x/24 Type-5 LSAs
```

**Null0 discard route:** Whenever IOS generates an OSPF summary (both `area range` and
`summary-address`), it automatically installs a Null0 discard route with Administrative
Distance 254. This prevents routing loops — if a router receives traffic for a destination
within the summary range but has no more-specific route, the Null0 drops it rather than
forwarding to a default route and looping.

```
ip route 192.168.0.0 255.255.0.0 Null0     ! auto-installed by IOS; AD=254
```

This Null0 route is less preferred than any learned or static route (AD 254 is the highest
possible AD) but will match traffic if no more-specific route exists.

For OSPFv3:
```
router ospfv3 1
  address-family ipv6 unicast
    summary-prefix 2001:db8:66::/48
  exit-address-family
```

---

### Stub and Totally Stubby Areas

Stub areas reduce LSDB size for internal routers by blocking Type-5 External LSAs from
entering the area. The ABR injects a default route (Type-3) instead:

| Area Type | Blocks | Receives |
|-----------|--------|----------|
| Normal | Nothing | Type-1, 2, 3, 4, 5 LSAs |
| Stub | Type-5 | Type-1, 2, 3 LSAs + default |
| Totally Stubby | Type-5 AND Type-3 | Type-1, 2 LSAs + default only |

Configuration:
```
! On ABR (R3):
router ospf 1
  area 2 stub no-summary    ! totally stubby — blocks Type-3 AND Type-5

! On internal router (R4) — must match:
router ospf 1
  area 2 stub               ! internal routers only use "stub" (not no-summary)
```

If the `stub` flag doesn't match between neighbors, the OSPF adjacency will not form — the
area type is negotiated in Hello packets using the External Routing (E) bit.

---

### NSSA — Not-So-Stubby Areas

The stub area design has one limitation: no ASBR can exist inside a stub area because Type-5
LSAs are blocked. NSSA solves this by allowing external routes to enter the area as **Type-7
LSAs** instead of Type-5. The ABR then **translates** Type-7 to Type-5 for the rest of the
domain:

```
Area 3 (NSSA)                    Area 0
  R5 (ASBR) ─── Type-7 ──► R3 (ABR) ─── Type-5 ──► R1, R2, R4
               "NSSA External"          "AS External"
```

Configuration:
```
! On ABR (R3):
router ospf 1
  area 3 nssa               ! allows Type-7 in Area 3; R3 translates to Type-5

! On ASBR inside NSSA (R5):
router ospf 1
  area 3 nssa               ! must match ABR
  redistribute connected subnets route-map NSSA_EXTERNAL
```

The `no-redistribution` option on the ABR disables Type-7 → Type-5 translation. This is
occasionally needed when multiple ABRs exist and only one should translate. In a single-ABR
topology, using `no-redistribution` silently breaks external route propagation — a common
exam fault scenario.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Inter-area summarization | Configure and verify `area range` on ABR; observe LSA count reduction |
| External summarization | Configure `summary-address` on ASBR; identify Null0 discard route |
| Totally stubby area | Configure and verify stub `no-summary`; trace default route injection |
| NSSA with internal ASBR | Configure Type-7 redistribution and ABR translation |
| IPv6 parity | Mirror all OSPFv2 configurations in OSPFv3 process |
| LSA-type identification | Read `show ip ospf database` to identify LSA types and origins |

---

## 2. Topology & Scenario

**Scenario:** Your ISP network has grown. The network team has identified three problems with
the current multiarea OSPF deployment:

1. Each router in Areas 1, 2, and 3 carries hundreds of specific prefixes from all other areas,
   consuming memory and slowing convergence after topology changes.
2. Area 2 (which serves a remote data centre with no external connectivity) is receiving all
   external LSAs from the ASBR — wasted overhead since it has no use for them.
3. Area 3 has a new edge router (R5) that needs to inject external routes, but company policy
   requires Area 3 to remain stub-like (not receiving external LSAs from elsewhere).

Your task is to deploy summarization, convert Area 2 to totally stubby, convert Area 3 to
NSSA, and bring up the new ASBR connection via R6.

```
              Area 1                  Area 0                 Area 2
 ┌──────────────────────┐    ┌──────────────────────┐    ┌────────────────────┐
 │          R1          │    │          R2          │    │         R3         │
 │  (Area 1 Internal)   │    │   (ABR: Area 0/1)    │    │ (ABR: Area 0/2/3)  │
 │  Lo0: 10.0.0.1/32    ├────┤  Lo0: 10.0.0.2/32    ├────┤  Lo0: 10.0.0.3/32  │
 │  Lo1: 172.16.1.1/24  │    │                      │    │                    │
 │  Lo2: 172.16.2.1/24  │    │  Gi0/0: 10.1.12.2/24 │    │ Gi0/0: 10.1.23.3/24│
 │  Lo3: 172.16.3.1/24  │    │  Gi0/1: 10.1.23.2/24 │    │ Gi0/1: 10.1.34.3/24│
 │  Gi0/0: 10.1.12.1/24 │    │                      │    │ Gi0/2: 10.1.35.3/24│
 └──────────────────────┘    └──────────────────────┘    │ Gi0/3: 10.1.36.3/24│
                                                         └───────┬────┬───────┘
                              L1: 10.1.12.0/24 (Area 1)          │    │
                              L2: 10.1.23.0/24 (Area 0)          │    │
                                                                  │    │
                             L3: 10.1.34.0/24 (Area 2) ──────────┘    │ L4: 10.1.35.0/24 (Area 3)
                             L5: 10.1.36.0/24 (external) ─────────────┘
                                                           │
                            ┌──────────────────┐          │  ┌──────────────────────┐
                            │        R4        │          │  │          R5          │
                            │ (Area 2 Internal)│          │  │  (Area 3 NSSA ASBR)  │
                            │ Lo0: 10.0.0.4/32 │          │  │  Lo0: 10.0.0.5/32    │
                            │ Lo1: 172.16.4.1/24│         │  │  Lo1: 172.16.5.1/24  │
                            │ Gi0/0:10.1.34.4/24│         │  │  Lo2: 192.168.55.1/24│
                            └──────────────────┘          │  │  Gi0/0:10.1.35.5/24  │
                                                           │  └──────────────────────┘
                            ┌──────────────────┐          │
                            │        R6        │──────────┘
                            │ (External AS)    │
                            │ Lo0: 10.0.0.6/32 │
                            │ Lo1:192.168.66.1/24│
                            │ Gi0/0:10.1.36.6/24│
                            └──────────────────┘
```

**Key relationships:**
- R2 is the ABR for Area 1 — applies inter-area summarization (`area 1 range`) for all three 172.16.1-3.x prefixes from R1
- R3 is the triple ABR and ASBR — applies external summarization for R6's prefix, converts Area 2 to totally stubby, converts Area 3 to NSSA
- R5 acts as ASBR inside Area 3 — redistributes its Loopback2 as a Type-7 LSA
- R6 stays IP-only throughout — R3 uses static routes and redistribution to inject R6's prefix into OSPF

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Area 1 internal router | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | ABR (Area 0 / Area 1) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Triple ABR + ASBR (Area 0 / 2 / 3 + external) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Area 2 internal router (totally stubby) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Area 3 NSSA internal router + ASBR | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | External AS router (no OSPF) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Cabling

| Link ID | From | Interface | To | Interface | Subnet | Area |
|---------|------|-----------|----|-----------|--------|------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | 1 |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/24 | 0 |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 | 10.1.34.0/24 | 2 |
| L4 | R3 | Gi0/2 | R5 | Gi0/0 | 10.1.35.0/24 | 3 |
| L5 | R3 | Gi0/3 | R6 | Gi0/0 | 10.1.36.0/24 | external |

### IP Address Plan

Comprehensive addressing table for all routers. Loopback addresses serve as router identifiers and test prefixes within each area; interface addresses are used for adjacency formation. This lab extends the dual-stack topology from labs 01–02 with additional loopbacks on R1 (Lo2/Lo3 for summarization testing) and external AS loopbacks on R5 and R6.

| Router | Interface | IPv4 Address | IPv6 Address | Subnet Mask / Prefix | OSPF Area | Purpose |
|--------|-----------|--------------|--------------|----------------------|-----------|---------|
| **R1** | Loopback0 | 10.0.0.1 | 2001:db8::1 | /32 / /128 | 1 | Router identifier |
| **R1** | Loopback1 | 172.16.1.1 | 2001:db8:1:0::1 | /24 / /64 | 1 | Test stub prefix (summarization) |
| **R1** | Loopback2 | 172.16.2.1 | 2001:db8:1:1::1 | /24 / /64 | 1 | Test stub prefix (summarization) |
| **R1** | Loopback3 | 172.16.3.1 | 2001:db8:1:2::1 | /24 / /64 | 1 | Test stub prefix (summarization) |
| **R1** | Gi0/0 | 10.1.12.1 | 2001:db8:12::1 | /24 / /64 | 1 | Link to R2 (Area 1) |
| **R2** | Loopback0 | 10.0.0.2 | 2001:db8::2 | /32 / /128 | 0 | Router identifier |
| **R2** | Gi0/0 | 10.1.12.2 | 2001:db8:12::2 | /24 / /64 | 1 | Link to R1 (Area 1) |
| **R2** | Gi0/1 | 10.1.23.2 | 2001:db8:23::2 | /24 / /64 | 0 | Link to R3 (Area 0) — ABR interface |
| **R3** | Loopback0 | 10.0.0.3 | 2001:db8::3 | /32 / /128 | 0 | Router identifier |
| **R3** | Gi0/0 | 10.1.23.3 | 2001:db8:23::3 | /24 / /64 | 0 | Link to R2 (Area 0) — ABR interface |
| **R3** | Gi0/1 | 10.1.34.3 | 2001:db8:34::3 | /24 / /64 | 2 | Link to R4 (Area 2, Totally Stubby) — ABR interface |
| **R3** | Gi0/2 | 10.1.35.3 | 2001:db8:35::3 | /24 / /64 | 3 | Link to R5 (Area 3, NSSA) — ABR interface |
| **R3** | Gi0/3 | 10.1.36.3 | 2001:db8:36::3 | /24 / /64 | external | Link to R6 (external AS) — ASBR interface |
| **R4** | Loopback0 | 10.0.0.4 | 2001:db8::4 | /32 / /128 | 2 | Router identifier |
| **R4** | Loopback1 | 172.16.4.1 | 2001:db8:4::1 | /24 / /64 | 2 | Stub prefix (internal to Area 2) |
| **R4** | Gi0/0 | 10.1.34.4 | 2001:db8:34::4 | /24 / /64 | 2 | Link to R3 (Area 2, Totally Stubby) |
| **R5** | Loopback0 | 10.0.0.5 | 2001:db8::5 | /32 / /128 | 3 | Router identifier |
| **R5** | Loopback1 | 172.16.5.1 | 2001:db8:5::1 | /24 / /64 | 3 | Stub prefix (internal to Area 3 NSSA) |
| **R5** | Loopback2 | 192.168.55.1 | 2001:db8:55::1 | /24 / /64 | 3 | External prefix (NSSA ASBR Type-7 injection) |
| **R5** | Gi0/0 | 10.1.35.5 | 2001:db8:35::5 | /24 / /64 | 3 | Link to R3 (Area 3, NSSA) |
| **R6** | Loopback0 | 10.0.0.6 | 2001:db8::6 | /32 / /128 | N/A | External AS router identifier |
| **R6** | Loopback1 | 192.168.66.1 | 2001:db8:66::1 | /24 / /64 | N/A | External AS prefix (redistributed via R3) |
| **R6** | Gi0/0 | 10.1.36.6 | 2001:db8:36::6 | /24 / /64 | N/A | Link to R3 (external, no OSPF) |

**Key relationships:**
- **Router identifiers (Loopback0):** 10.0.0.1–5 for OSPF routers (R1–R5); 10.0.0.6 for external AS (R6); serves as router-id in both OSPFv2 and OSPFv3
- **R1 secondary loopbacks (Lo1–Lo3):** 172.16.x.1/24 subnets that R2 will summarize into a single 172.16.0.0/21 range across Area 1
- **R5 Loopback2:** 192.168.55.0/24 used for NSSA Type-7 redistribution testing; represents an external prefix inside an NSSA area
- **R6 external prefix:** 192.168.66.0/24 redistributed into OSPF via static routes on R3; R3 will summarize this to 192.168.0.0/16
- **Area 2 (R3–R4):** Converted to totally stubby to block both inter-area specific routes and external routes
- **Area 3 (R3–R5):** Configured as NSSA to allow R5 to act as an ASBR while remaining stub-like for external Type-5 LSAs from other areas

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R6 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on all six routers
- Interface IP addressing (all routed links and loopbacks including R1 Lo2/Lo3 and R5 Lo2)
- `ipv6 unicast-routing` and `no ip domain-lookup` on all routers
- OSPFv2 (router ospf 1) and OSPFv3 (router ospfv3 1) processes with router-IDs
- OSPFv2 `network` statements placing all links and loopbacks in their correct areas
- OSPFv3 interface-level `ospfv3 1 ipv6 area X` assignments on all OSPF-participating interfaces
- R3 Gi0/3 IP addressing (link to R6) — interface is up but NOT in any OSPF area

**IS NOT pre-loaded** (student configures this):
- Inter-area summarization on R2 (IPv4 and IPv6)
- Static routes on R3 pointing to R6's networks
- Redistribution of static routes into OSPFv2 and OSPFv3 on R3 (making R3 the ASBR)
- External summarization on R3 (IPv4 and IPv6)
- Area 2 totally stubby configuration (R3 as ABR + R4 as internal)
- Area 3 NSSA configuration (R3 as ABR + R5 as internal ASBR)
- R5 redistribution of Loopback2 (192.168.55.0/24) into OSPF as Type-7

---

## 5. Lab Challenge: Core Implementation

### Task 1: Activate External AS (R6) via Static Redistribution

R3's Gi0/3 is already IP-addressed. Bring R6's network (192.168.66.0/24) into the OSPF
domain through redistribution on R3.

- Add static routes on R3 pointing R6's Loopback1 network (IPv4 and IPv6) toward R6's
  Gi0/0 addresses (10.1.36.6 and 2001:db8:36::6)
- Redistribute the static routes into both OSPFv2 and OSPFv3 on R3, making R3 the ASBR
- Use the `subnets` keyword for OSPFv2 redistribution to include classless prefixes

**Verification:** On R1, `show ip route ospf | include 192.168` must show 192.168.66.0/24
as an OSPF external (E2) route. `show ipv6 route ospf | include 2001:db8:66` must show the
IPv6 external route. On R3, `show ip ospf database external` must list 192.168.66.0 as a
Type-5 LSA.

---

### Task 2: Configure Inter-Area Summarization on R2

R1 has three loopbacks in Area 1 (172.16.1.0/24, 172.16.2.0/24, 172.16.3.0/24). Configure
R2 (ABR for Area 1) to summarize them into a single Type-3 LSA.

- On R2, configure an inter-area summary for 172.16.0.0/21 covering all three Area-1
  loopback prefixes (this range covers 172.16.0.0 through 172.16.7.255)
- Configure the equivalent IPv6 summary for Area 1's three loopback prefixes under the
  OSPFv3 address-family (range 2001:db8:1::/48)

**Verification:** On R4, `show ip route ospf` must show a single O IA 172.16.0.0/21 route
instead of three separate /24s. On R2, `show ip ospf database summary` must show the summary
LSA with the summarized prefix. Confirm that no individual 172.16.x.0/24 routes from Area 1
appear in R4's or R3's routing table.

---

### Task 3: Configure External Summarization on R3

R3 is the ASBR injecting R6's 192.168.66.0/24 as a Type-5 LSA. Configure R3 to summarize
all external routes in the 192.168.0.0/16 range into a single Type-5 summary LSA.

- Apply an external summary on R3 for the 192.168.0.0/16 range under OSPFv2
- Apply the equivalent prefix summary for 2001:db8:66::/48 under the OSPFv3 address-family
- Verify that IOS auto-installs a Null0 discard route for the summarized range

**Verification:** On R1, `show ip route ospf | include 192` must show a single O E2 route
for 192.168.0.0/16 instead of 192.168.66.0/24. On R3, `show ip route static` must show
192.168.0.0/16 via Null0 (AD 254). On R3, `show ip ospf database external` must show only
the summary LSA, not the original /24.

---

### Task 4: Convert Area 2 to Totally Stubby

Area 2 (R3 ↔ R4) carries a remote data centre and requires no external routes.

- On R3 (ABR), configure Area 2 as totally stubby to block both Type-3 inter-area LSAs and
  Type-5 external LSAs from entering Area 2 while injecting a single default Type-3 LSA
- On R4 (internal router), configure the matching stub declaration (internal routers use
  `area stub` without `no-summary`)
- Apply the equivalent configuration for OSPFv3 on both routers

**Verification:** On R4, `show ip route ospf` must show only intra-area routes (O) and a
single O IA 0.0.0.0/0 default route — no inter-area specific routes, no external routes.
`show ip ospf` on R4 must confirm `Area 2 is a stub area`. R3-R4 adjacency must remain Full.

---

### Task 5: Convert Area 3 to NSSA and Configure R5 as ASBR

Area 3 (R3 ↔ R5) should not receive external LSAs from R3, but R5 needs to inject its own
external prefix (Loopback2: 192.168.55.0/24) into the OSPF domain.

- On R3 (ABR) and R5 (internal), configure Area 3 as NSSA
- On R5, redistribute Loopback2 (192.168.55.0/24) into OSPF using a route-map filter
  (prefix-list named NSSA_LO2, route-map named NSSA_EXTERNAL) to redistribute only that
  specific prefix — not all connected interfaces
- Apply the OSPFv3 NSSA area declaration on R3 and R5 under the address-family

**Verification:** On R5, `show ip ospf database nssa-external` must list 192.168.55.0 as
a Type-7 LSA. On R1, `show ip route ospf | include 192.168.55` must show the route as an
O E2 (translated from Type-7 by R3). On R3, `show ip ospf database external | include 192.168.55`
must confirm R3 has translated it to Type-5. R5 must NOT have a Type-5 database entry for
192.168.66.0/24 (blocked by NSSA).

---

## 6. Verification & Analysis

### Task 1 Verification — External Route Injection

```
R1# show ip route ospf | begin 192
O E2  192.168.0.0/16 [110/20] via 10.1.12.2, Fa 00:xx:xx, GigabitEthernet0/0
                                                            ! Type-5 external; metric 20 (default E2 seed)

R3# show ip ospf database external
            OSPF Router with ID (10.0.0.3) (Process ID 1)
                Type-5 AS External Link States
  Link ID         ADV Router      Age  Seq#       Checksum  Tag
  192.168.0.0     10.0.0.3        xx   0x80000001 0xxxxxx   0   ! R3 = ASBR; summarized /16 LSA

R3# show ip route static
S    192.168.66.0/24 [1/0] via 10.1.36.6                        ! specific static still in RIB
S    192.168.0.0/16 is directly connected, Null0                 ! auto-installed Null0 (AD 254 not shown for direct)
```

### Task 2 Verification — Inter-Area Summarization

```
R4# show ip route ospf
O IA 172.16.0.0/21 [110/3] via 10.1.34.3, 00:xx:xx, GigabitEthernet0/0  ! single summary; no /24s
O IA 10.0.0.1/32   [110/3] via 10.1.34.3, 00:xx:xx, GigabitEthernet0/0
O IA 10.0.0.2/32   [110/2] via 10.1.34.3, 00:xx:xx, GigabitEthernet0/0
O IA 10.1.12.0/24  [110/3] via 10.1.34.3, 00:xx:xx, GigabitEthernet0/0  ! link still propagated (outside range)

R4# show ip route 172.16.1.1
% Subnet 172.16.1.0/24 not in table    ! specific /24s suppressed by summary ← confirm this

R2# show ip ospf database summary | begin 172.16
  Link ID: 172.16.0.0  ADV Router: 10.0.0.2  Age: xx  Seq#: 0x80000001  ! R2 advertising summary
```

### Task 3 Verification — External Summarization

```
R1# show ip route ospf | include 192
O E2  192.168.0.0/16 [110/20] via 10.1.12.2, 00:xx:xx, GigabitEthernet0/0  ! /16 summary replaces /24

R3# show ip route | include Null
S    192.168.0.0/16 is directly connected, Null0   ! Null0 discard (type: static, AD 254)

R3# show ip ospf database external
  Link ID: 192.168.0.0  ADV Router: 10.0.0.3  Age: xx  Seq#: 0x80000001  ! only summary LSA, no /24
```

### Task 4 Verification — Totally Stubby Area 2

```
R4# show ip route ospf
O    10.0.0.4/32 is directly connected
O    172.16.4.0/24 is directly connected
O    10.1.34.0/24 is directly connected
O*IA 0.0.0.0/0 [110/2] via 10.1.34.3, 00:xx:xx, GigabitEthernet0/0  ! only a default route; no specifics

R4# show ip ospf | include stub
    Area 2 is a stub area, no summary LSA   ! confirms totally stubby

R3# show ip ospf neighbor
Neighbor ID   Pri   State    Dead Time  Address    Interface
10.0.0.4      1     FULL/DR  00:00:xx   10.1.34.4  GigabitEthernet0/1   ! R3-R4 adjacency still Full
```

### Task 5 Verification — NSSA with R5 as ASBR

```
R5# show ip ospf database nssa-external
            OSPF Router with ID (10.0.0.5) (Process ID 1)
                Type-7 AS External Link States (Area 3)
  Link ID: 192.168.55.0  ADV Router: 10.0.0.5  Age: xx  ! R5 generated Type-7 ← verify this

R1# show ip route ospf | include 192.168.55
O E2  192.168.55.0/24 [110/20] via 10.1.12.2, 00:xx:xx, GigabitEthernet0/0  ! Type-5 reached R1

R5# show ip route ospf
O*IA 0.0.0.0/0 [110/2] via 10.1.35.3, 00:xx:xx, GigabitEthernet0/0  ! default from NSSA; no Type-5 from outside
     (192.168.0.0/16 and 192.168.66.x MUST NOT appear in R5's table)
```

---

## 7. Verification Cheatsheet

### Static Routes and Redistribution (R3)

```
ip route 192.168.66.0 255.255.255.0 10.1.36.6
ipv6 route 2001:db8:66::/64 2001:db8:36::6

router ospf 1
  redistribute static subnets
  summary-address 192.168.0.0 255.255.0.0

router ospfv3 1
  address-family ipv6 unicast
    redistribute static
    summary-prefix 2001:db8:66::/48
  exit-address-family
```

| Command | Purpose |
|---------|---------|
| `redistribute static subnets` | Injects static routes into OSPF as Type-5 LSAs; `subnets` required for /24+ |
| `summary-address A.B.C.D M.M.M.M` | Collapses external Type-5 LSAs on ASBR; installs Null0 |
| `summary-prefix X::/len` | OSPFv3 equivalent of `summary-address` on ASBR |

> **Exam tip:** `redistribute connected subnets` without `subnets` will only redistribute
> classful networks. Always use `subnets` when redistributing classless (VLSM) routes into OSPF.

### Inter-Area Summarization (R2 ABR)

```
router ospf 1
  area 1 range 172.16.0.0 255.255.248.0

router ospfv3 1
  address-family ipv6 unicast
    area 1 range 2001:db8:1::/48
  exit-address-family
```

| Command | Purpose |
|---------|---------|
| `area N range A.B.C.D M` | ABR suppresses specific Type-3s and advertises one summary |
| `area N range not-advertise` | Suppresses the summary too — removes all visibility of the range |
| `show ip ospf database summary` | Lists all Type-3 LSAs; look for summarized prefix |

> **Exam tip:** `area range` is configured only on the ABR. Internal routers in the area
> are unaffected. If no route in the range is active, the summary LSA is also withdrawn.

### Totally Stubby Area (R3 ABR + R4 internal)

```
! R3 (ABR only):
router ospf 1
  area 2 stub no-summary

! R4 (internal — "stub" only, no "no-summary"):
router ospf 1
  area 2 stub

! OSPFv3 equivalent:
router ospfv3 1
  address-family ipv6 unicast
    area 2 stub no-summary   ! on ABR
    ! or: area 2 stub        ! on internal router
  exit-address-family
```

| Command | Purpose |
|---------|---------|
| `area N stub` | Prevents Type-5 LSAs from entering; ABR injects default |
| `area N stub no-summary` | Also blocks Type-3 LSAs; ABR injects only default |
| `show ip ospf` | Shows area type; look for "stub area" or "no summary LSA" |

> **Exam tip:** A stub area mismatch (one side `stub`, other side normal) prevents OSPF
> adjacency from forming. The E bit in Hello packets must match between neighbors.

### NSSA Configuration (R3 ABR + R5 ASBR)

```
! R3 (ABR):
router ospf 1
  area 3 nssa

! R5 (ASBR inside NSSA):
router ospf 1
  area 3 nssa
  redistribute connected subnets route-map NSSA_EXTERNAL

ip prefix-list NSSA_LO2 seq 5 permit 192.168.55.0/24
route-map NSSA_EXTERNAL permit 10
  match ip address prefix-list NSSA_LO2
```

| Command | Purpose |
|---------|---------|
| `area N nssa` | Allows Type-7 LSAs in area; ABR translates to Type-5 for rest of domain |
| `area N nssa no-summary` | NSSA + no inter-area Type-3s (totally NSSA) |
| `area N nssa no-redistribution` | ABR does not translate Type-7 to Type-5 |
| `show ip ospf database nssa-external` | Lists Type-7 LSAs inside NSSA area |
| `show ip ospf database external` | Lists Type-5 LSAs (translated by ABR) |

> **Exam tip:** `no-redistribution` on the NSSA ABR silently stops Type-7 → Type-5 translation.
> External routes from inside the NSSA area become invisible to the rest of the domain.

### Wildcard Mask Quick Reference

Wildcard masks are the bitwise inverse of subnet masks. For summarization, compute the wildcard
from the prefix length: `255.255.255.255 XOR <subnet mask>`.

| Prefix Length | Subnet Mask | Wildcard Mask | Hosts in Range |
|--------------|-------------|---------------|----------------|
| /16 | 255.255.0.0 | 0.0.255.255 | 65536 |
| /20 | 255.255.240.0 | 0.0.15.255 | 4096 |
| /21 | 255.255.248.0 | 0.0.7.255 | 2048 |
| /22 | 255.255.252.0 | 0.0.3.255 | 1024 |
| /23 | 255.255.254.0 | 0.0.1.255 | 512 |
| /24 | 255.255.255.0 | 0.0.0.255 | 256 |
| /25 | 255.255.255.128 | 0.0.0.127 | 128 |
| /32 | 255.255.255.255 | 0.0.0.0 | 1 (host) |

> **This lab:** The 172.16.0.0/21 summary uses wildcard `0.0.7.255` — covers 172.16.0.0
> through 172.16.7.255. The 192.168.0.0/16 external summary uses wildcard `0.0.255.255`.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip route ospf` | E2 routes = external; IA routes = inter-area; O routes = intra-area |
| `show ip ospf database` | Summary of all LSA types in the LSDB |
| `show ip ospf database external` | All Type-5 LSAs; confirm ASBR and prefix |
| `show ip ospf database nssa-external` | All Type-7 LSAs inside NSSA area |
| `show ip ospf database summary` | All Type-3 LSAs; look for summarized prefixes |
| `show ip ospf neighbor` | Adjacency state; mismatch drops adjacency |
| `show ip ospf` | Area types, ABR/ASBR status, statistics |
| `show ipv6 route ospf` | IPv6 OSPFv3 routing table |
| `show ospfv3 database` | OSPFv3 LSDB across all address families |

### LSA Type Quick Reference

| LSA Type | Name | Generated By | Scope |
|----------|------|--------------|-------|
| 1 | Router LSA | Every router | Within area |
| 2 | Network LSA | DR on broadcast | Within area |
| 3 | Summary LSA | ABR | Between areas |
| 4 | ASBR Summary | ABR | Between areas |
| 5 | AS External | ASBR | Entire domain (except stub) |
| 7 | NSSA External | ASBR inside NSSA | Within NSSA area only |

### Common OSPF Summarization Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Summary LSA not appearing in neighboring area | `area range` missing on ABR, or no active routes in range |
| Specific routes still visible despite summary | `area range` configured but pointing to wrong area or wrong prefix |
| External route missing everywhere | `redistribute` missing or wrong keyword (`subnets`) |
| External routes missing from one area only | Area is stub/totally-stubby (by design); check `show ip ospf` |
| R4/R5 adjacency dropped after stub config | Stub flag mismatch — must match on both neighbors |
| Type-7 routes not reaching Area 0 as Type-5 | `area 3 nssa no-redistribution` on ABR, or NSSA mismatch |
| Null0 route installed | Normal; IOS auto-installs discard route whenever summary is active |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: External AS Activation (R3)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — static routes to R6's networks
ip route 192.168.66.0 255.255.255.0 10.1.36.6
ipv6 route 2001:db8:66::/64 2001:db8:36::6

! R3 — redistribute into OSPFv2
router ospf 1
  redistribute static subnets

! R3 — redistribute into OSPFv3
router ospfv3 1
  address-family ipv6 unicast
    redistribute static
  exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R3# show ip ospf database external
R1# show ip route ospf | include 192
R1# show ipv6 route ospf
```
</details>

---

### Task 2: Inter-Area Summarization (R2)

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — OSPFv2 inter-area summary
router ospf 1
  area 1 range 172.16.0.0 255.255.248.0

! R2 — OSPFv3 inter-area summary
router ospfv3 1
  address-family ipv6 unicast
    area 1 range 2001:db8:1::/48
  exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R4# show ip route ospf | include 172.16
R2# show ip ospf database summary
R4# show ipv6 route ospf
```
</details>

---

### Task 3: External Summarization (R3)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — OSPFv2 external summary (add to router ospf 1 block)
router ospf 1
  summary-address 192.168.0.0 255.255.0.0

! R3 — OSPFv3 external summary
router ospfv3 1
  address-family ipv6 unicast
    summary-prefix 2001:db8:66::/48
  exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R1# show ip route ospf | include 192
R3# show ip route | include Null
R3# show ip ospf database external
```
</details>

---

### Task 4: Totally Stubby Area 2 (R3 + R4)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — ABR: totally stubby (blocks Type-3 AND Type-5)
router ospf 1
  area 2 stub no-summary

router ospfv3 1
  address-family ipv6 unicast
    area 2 stub no-summary
  exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — internal router: stub only (no "no-summary")
router ospf 1
  area 2 stub

router ospfv3 1
  address-family ipv6 unicast
    area 2 stub
  exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R4# show ip route ospf
R4# show ip ospf
R3# show ip ospf neighbor
```
</details>

---

### Task 5: NSSA — Area 3 with R5 as ASBR (R3 + R5)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — ABR: NSSA (allows Type-7; translates to Type-5 for rest of domain)
router ospf 1
  area 3 nssa

router ospfv3 1
  address-family ipv6 unicast
    area 3 nssa
  exit-address-family
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — OSPFv2 NSSA area declaration + redistribution
router ospf 1
  area 3 nssa

! R5 — redistribute only Loopback2 as Type-7 LSA
ip prefix-list NSSA_LO2 seq 5 permit 192.168.55.0/24
route-map NSSA_EXTERNAL permit 10
  match ip address prefix-list NSSA_LO2

router ospf 1
  redistribute connected subnets route-map NSSA_EXTERNAL

! R5 — OSPFv3 NSSA area declaration (must match R3's OSPFv3 area type)
router ospfv3 1
  address-family ipv6 unicast
    area 3 nssa
  exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip ospf database nssa-external
R1# show ip route ospf | include 192.168.55
R3# show ip ospf database external | include 192.168.55
R5# show ip route ospf
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore all
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip> --node R3   # restore one device
```

---

### Ticket 1 — External Prefix Vanishes from All Routers

A colleague reports that 192.168.66.1 is no longer reachable from anywhere in the OSPF
domain. The R3-R6 link shows as up and the static route to 192.168.66.0/24 is present
in R3's routing table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip route` on R1 shows 192.168.0.0/16 as O E2 and pings to
192.168.66.1 succeed.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm external route is missing on R1
R1# show ip route ospf | include 192
  (empty — no external routes)

! Step 2: Check R3's OSPF database for external LSAs
R3# show ip ospf database external
  (empty or missing 192.168.66.0 / 192.168.0.0 entries)

! Step 3: Check if R3 is redistributing
R3# show ip ospf | include redistribute
  or
R3# show running-config | section router ospf

! Step 4: Check for a distribute-list filtering outbound
R3# show running-config | include distribute-list
  (likely shows: distribute-list prefix BLOCK_EXT out)

! Step 5: Confirm the prefix-list is blocking 192.168.66.0/24
R3# show ip prefix-list BLOCK_EXT
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Remove the distribute-list and the prefix-list from R3
R3# conf t
R3(config)# router ospf 1
R3(config-router)# no distribute-list prefix BLOCK_EXT out
R3(config-router)# exit
R3(config)# no ip prefix-list BLOCK_EXT
```
</details>

---

### Ticket 2 — R4 Reports No OSPF Adjacency with R3

R4 has lost its only OSPF neighbor. No routes are being received. The Gi0/0-Gi0/1 link
between R3 and R4 shows as up at Layer 1/2, but `show ip ospf neighbor` on R4 shows empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip ospf neighbor` on R4 shows R3 in FULL state and R4's routing
table contains a default route from the stub area.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm adjacency is down
R4# show ip ospf neighbor
  (empty)

! Step 2: Check R4's OSPF area configuration
R4# show ip ospf | include Area
  Area 2 is a stub area

! Step 3: Check R3's area 2 configuration
R3# show ip ospf | include Area
  Area 2 might show "nssa" instead of "stub" ← mismatch

! Step 4: Check for area type conflict in config
R3# show running-config | section router ospf
  area 2 nssa   ← should be "area 2 stub no-summary"

! Root cause: R3 has Area 2 as NSSA; R4 has Area 2 as stub.
! OSPF Hello packets carry area type flags — mismatch prevents adjacency.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix R3 — restore totally stubby configuration for Area 2
R3# conf t
R3(config)# router ospf 1
R3(config-router)# no area 2 nssa
R3(config-router)# area 2 stub no-summary
R3(config-router)# exit

! Also fix in OSPFv3 if needed:
R3(config)# router ospfv3 1
R3(config-router)# address-family ipv6 unicast
R3(config-router-af)# no area 2 nssa
R3(config-router-af)# area 2 stub no-summary
```
</details>

---

### Ticket 3 — R5's External Route Not Visible Outside Area 3

R5 is generating a Type-7 LSA for 192.168.55.0/24. You can see it with
`show ip ospf database nssa-external` on R5 and R3. But R1 has no route to 192.168.55.0/24
and neither does R4 or R2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R1's `show ip route ospf` shows 192.168.55.0/24 as O E2 (Type-5
translated from Type-7 by R3).

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm Type-7 is present in Area 3
R5# show ip ospf database nssa-external
  Link ID: 192.168.55.0  ADV Router: 10.0.0.5   ← Type-7 exists in area

! Step 2: Check if R3 has Type-5 for 192.168.55.0
R3# show ip ospf database external | include 192.168.55
  (empty — R3 has the Type-7 but did not translate it)

! Step 3: Check R3's NSSA configuration
R3# show running-config | section router ospf
  area 3 nssa no-redistribution   ← this disables Type-7 to Type-5 translation

! Root cause: "no-redistribution" prevents the ABR from translating Type-7 to Type-5.
! The Type-7 stays within Area 3 and never becomes a Type-5 visible elsewhere.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix R3 — remove no-redistribution to restore translation
R3# conf t
R3(config)# router ospf 1
R3(config-router)# no area 3 nssa no-redistribution
R3(config-router)# area 3 nssa
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R3 has static routes to 192.168.66.0/24 and 2001:db8:66::/64 via R6
- [ ] R3 redistributes static routes into OSPFv2 (with `subnets`) and OSPFv3
- [ ] R1 shows O E2 route for 192.168.0.0/16 (summarized external)
- [ ] R2 is configured with `area 1 range 172.16.0.0 255.255.248.0`
- [ ] R4 shows single O IA 172.16.0.0/21 summary (no individual /24s from Area 1)
- [ ] R3 has `summary-address 192.168.0.0 255.255.0.0` and Null0 discard route
- [ ] Area 2 is totally stubby: R4 shows only default O*IA and intra-area routes
- [ ] R4 shows `Area 2 is a stub area, no summary LSA` in `show ip ospf`
- [ ] Area 3 is NSSA: R5 shows `Area 3 is a NSSA area` in `show ip ospf`
- [ ] R5's 192.168.55.0/24 is visible as O E2 on R1 (Type-7 → Type-5 translated by R3)
- [ ] OSPFv3 parity: R1, R4 show IPv6 equivalents; R5 has no Type-5 IPv6 external routes
- [ ] All adjacencies are FULL: R1↔R2, R2↔R3, R3↔R4, R3↔R5

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved (distribute-list on R3 removed)
- [ ] Ticket 2 diagnosed and resolved (area 2 type mismatch fixed on R3)
- [ ] Ticket 3 diagnosed and resolved (NSSA no-redistribution removed from R3)

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
