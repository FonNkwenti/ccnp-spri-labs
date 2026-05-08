# Lab 03 — Route Manipulation for IS-IS and OSPF

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

**Exam Objective:** 3.3 Troubleshoot route manipulation for IGPs — 3.3.a IS-IS, 3.3.b OSPF

This lab builds on the routing-policy foundations and RPL skills from labs 00–02 and applies
them directly to IGP route manipulation. You will use OSPF distribute-lists, ABR filter-lists,
and interface-level prefix suppression to control how OSPF routes appear in the RIB and the
LSDB. You will then create a live IS-IS level boundary, selectively leak L1 prefixes into the
L2 domain using both IOS route-maps and XR RPL, and control what the XR router advertises
into IS-IS using hierarchical `apply` policies. These are the mechanisms SPRI examiners test
when asking why a route is missing from a router's table or why IGP redistribution is
inconsistent across the domain.

---

### OSPF Route Filtering: distribute-list vs filter-list

OSPF is a link-state protocol — every router in an area has the same LSDB. Filtering at the
LSDB level is limited to ABR operations (Type 3 LSA suppression). Filtering at the RIB level
affects only the local router's routing table while leaving the LSDB untouched.

**`distribute-list prefix-list X in` under `router ospf`**

Filters which OSPF-computed routes are installed in the RIB. The LSA for the blocked prefix
remains in the LSDB and continues to be flooded. SPF still computes the path; the route is
simply not installed.

```
router ospf 1
  distribute-list prefix BLOCK_MGMT in
```

Key exam point: `show ip route` will not show the blocked prefix, but `show ip ospf database`
will still show the corresponding Type 1 or Type 5 LSA. This is different from other IGPs
where a distribute-list actually prevents route learning.

**`area N filter-list prefix X in/out` under `router ospf` (ABR only)**

Controls which inter-area Type 3 LSAs are generated or accepted by an ABR:

- `in` — filters Type 3 LSAs being flooded *into* area N from other areas
- `out` — filters Type 3 LSAs being generated *out* from area N toward other areas

```
router ospf 1
  area 0 filter-list prefix FILTER_TRANSIT in
```

This must be configured on the ABR. A non-ABR router silently ignores the command.

---

### OSPF Prefix Suppression

`ip ospf prefix-suppression` on a transit interface prevents the connected subnet from being
included in the router's Type 1 LSA while the OSPF adjacency remains up. The router still
forms neighborship and floods LSAs for other routers' prefixes; it simply omits its own
connected subnet from its own Type 1 Router LSA.

```
interface GigabitEthernet0/0
  ip ospf prefix-suppression
```

Exam use case: suppress transit link addresses to reduce the attack surface and shrink the
LSDB without losing OSPF reachability to router IDs.

---

### IS-IS Level Hierarchy and Route Leaking

IS-IS organises routers into Level 1 (intra-area) and Level 2 (backbone) domains. An L1-L2
router sits on the boundary between them.

**Default leaking behaviour:** A Level 1-2 IOS router automatically leaks *all* L1 routes
into L2 unless explicitly configured otherwise. This is the opposite of OSPF where an ABR
only generates Type 3 summaries for prefixes in the area range.

**Selective leaking — IOS:**

```
router isis SP
  is-type level-1-2
  redistribute isis ip level-1 into level-2 route-map LEAK_L1_TO_L2
  distance 109 ip
```

The `ip` keyword targets IPv4 routes (required on IOSv). `distance 109 ip` lowers the IS-IS
IP AD below OSPF (110) on this router so L1 routes install in the RIB — necessary because
XRv 6.3.1 floods loopbacks into both L1 and L2, causing OSPF redistribution to otherwise
supersede IS-IS L1. The route-map permits only the prefixes that should be leaked; everything
else is blocked by the implicit deny.

**Selective leaking — XR RPL:**

```
router isis SP
  address-family ipv4 unicast
    redistribute isis level 1 route-policy LEAK_L1_TO_L2
```

**IS-IS circuit-type:** Controls which levels an interface participates in. `isis circuit-type
level-1` restricts the link to L1 hellos only, which is how you form a pure L1 adjacency
between an L1-L2 router and an L1-only peer.

---

### XR IS-IS Filtering with RPL `apply`

IOS uses `distribute-list prefix-list X out` under `router isis` to filter which prefixes
are advertised into IS-IS.

On **IOS XRv 9000 (6.5+)** and later platforms, XR exposes a `route-policy` knob at the IS-IS
address-family level:

```
router isis SP
  address-family ipv4 unicast
    route-policy ISIS_L1_FILTER_PARENT out   ! XRv 9000 / 6.5+ only
```

On **IOS XRv classic (6.3.x)** — the platform used in this lab — that knob is not present.
The closest equivalent is:

```
router isis SP
  address-family ipv4 unicast
    advertise passive-only   ! restricts IS-IS to advertising only passive-interface prefixes
```

`advertise passive-only` is a boolean flag, not a policy: any interface marked `passive` in
the IS-IS process has its connected prefix advertised; all active-interface prefixes are
suppressed. Because only Loopback0 and Loopback1 are passive on XR1, the effect is the
same as a two-prefix whitelist — but it is less precise than a named RPL filter.

The RPL `apply` statement calls a child policy, enabling hierarchical composition:

```
route-policy ISIS_L1_FILTER_PARENT
  apply ISIS_L1_FILTER_CHILD
end-policy

route-policy ISIS_L1_FILTER_CHILD
  if destination in P_XR1_LOOPBACKS then
    pass
  else
    drop
  endif
end-policy
```

In this lab the RPL policies are **defined** to demonstrate the `apply` pattern, but they
are **not attached to IS-IS** (the platform does not support it). The `apply` mechanism
itself is fully functional for BGP on this platform — see lab-02.

Key difference from IOS: XR RPL `drop` in a child policy propagates to the parent and halts
evaluation. IOS `distribute-list deny` simply skips the route. The XR model also allows the
filter policy to be reused across multiple protocols by referencing the same named set.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| OSPF RIB filtering | Use distribute-list to block OSPF routes from entering the RIB without removing them from the LSDB |
| OSPF Type 3 LSA suppression | Use ABR filter-list to block inter-area LSA flooding |
| OSPF transit suppression | Use prefix-suppression on transit interfaces to shrink the LSDB |
| IS-IS level boundary configuration | Configure L1-L2 boundary between IOSv and XRv9k nodes |
| IS-IS selective level leaking | Leak specific L1 prefixes to L2 using route-maps (IOS) and route-policy (XR) |
| RPL hierarchical IS-IS filtering | Define nested `apply` RPL policies; use `advertise passive-only` as the 6.3.1 IS-IS advertisement control (XRv 9000 6.5+ uses `route-policy out`) |
| OSPF-to-IS-IS redistribution control | Redistribute OSPF external routes into IS-IS with metric-type internal and tag 300 |
| Implicit deny troubleshooting | Diagnose route-maps where a missing permit sequence silently drops routes |

---

## 2. Topology & Scenario

**Scenario:** You are a SP network engineer responsible for the 6-router SP core. The network
team has asked you to harden the routing domain: suppress unnecessary transit prefixes from
OSPF advertisements, filter inter-area LSA flooding from a new stub area, and tighten IS-IS
level boundary behaviour so that only explicitly approved L1 prefixes from the XR router
reach the L2 backbone. A redistribution route-map between OSPF and IS-IS has also been
reported to be losing routes intermittently — you need to diagnose and fix it.

```
                    AS 65100 — OSPF area 0 / IS-IS L2
┌───────────────────┐   Gi0/0        Gi0/0   ┌───────────────────┐
│        R1         │ 10.1.12.1/24 10.1.12.2/24│       R2          │
│  Lo0: 10.0.0.1/32 │────────── L1 ───────────│  Lo0: 10.0.0.2/32 │
│  Lo1: 172.16.1/24 │                         │  Lo1: 10.2.1.2/24 │
│ [OSPF pfx-supp    │   Gi0/2        Gi0/1    │ [OSPF ABR area0/1]│
│  on Gi0/0,Gi0/2]  │ 10.1.13.1   10.1.23.2  │ [IS-IS L1-L2 ABR] │
└──────┬──────┬─────┘      │           │      └──────────┬─────────┘
       │      └────── L5 ──┘           └── L2 ──┐        │ Gi0/2 (IS-IS L1)
       │ Gi0/1                                  │        │ 10.1.25.2/24
      L4 eBGP                                  Gi0/0     │
       │ 10.1.14.1                              │         │
       │                      Gi0/1        Gi0/3│       Gi0/0/0/0
┌──────┴───────────┐   10.1.34.3   10.1.36.3   ├─────── L6 (IS-IS L1)────────┐
│       R4         │     │              │       │    10.1.25.5/24              │
│ Lo0: 10.0.0.4/32 │     │              │       │                              │
│ Lo1: 172.20.4/24 │     └─────────────┤      [AS 65100 XR domain]            │
│ Lo2: 172.20.5/24 │               Gi0/0       │                              │
│    AS 65200       │     ┌─────────────┤       │                              │
└──────────────────┘     │             │       ▼                              │
                    ┌────┴─────────────┴──┐  ┌──────────────────┐            │
                    │        R3           │  │       XR1        │            │
                    │  Lo0: 10.0.0.3/32   │  │ Lo0: 10.0.0.5/32 │            │
                    │  [IS-IS L2-only]    │  │ Lo1: 172.16.11/24│            │
                    └───────┬─────────────┘  │ [IS-IS L1-2]     │            │
                            │ Gi0/3           │ [RPL IS-IS filter]│            │
                            │ 10.1.36.3      └───────┬──────────┘            │
                            │                        │ Gi0/0/0/1             │
                            └── L7 (IS-IS L2) ───────┤                       │
                                10.1.36.6/24      ┌──┴──────────────┐         │
                                             Gi0/0/0/0│     XR2     │         │
                                                   │  Lo0: 10.0.0.6 │         │
                                                   │  [IS-IS L2-only│         │
                                                   └─────────────────┘         │
                                                                                │
                                                        L8: XR1↔XR2 (IS-IS L2) ┘
                                                        10.1.56.x/24
```

**Key relationships in lab-03:**

- R2 gains Loopback1 (10.2.1.2/24) in OSPF area 1, making it an ABR between area 0 and area 1
- R1's transit interfaces (Gi0/0, Gi0/2) use `ip ospf prefix-suppression` — the 10.1.12.0/24 and 10.1.13.0/24 subnets are suppressed from R1's Type 1 LSA
- R2's Gi0/2 becomes an IS-IS Level-1-only link to XR1; R2 is the L1/L2 boundary
- XR1 changes from level-2-only to level-1-2; it forms L1 with R2 and L2 with XR2
- R2 leaks selected L1 prefixes (XR1's loopbacks) into L2 via `LEAK_L1_TO_L2` route-map

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP core — eBGP edge to AS 65200 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | SP core — OSPF ABR, IS-IS L1-L2 boundary | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | SP core — eBGP edge to AS 65200, IS-IS L2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | External AS edge (AS 65200) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| XR1 | IOS-XR RPL node — IS-IS L1-2 | IOS XRv (classic) | xrvr-fullk9-6.3.1 |
| XR2 | IOS-XR RPL node — IS-IS L2-only | IOS XRv (classic) | xrvr-fullk9-6.3.1 |

### Loopback Address Table

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP peering source |
| R1 | Loopback1 | 172.16.1.0/24 | Customer prefix (redistributed into OSPF/BGP) |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source |
| R2 | Loopback1 | 10.2.1.2/24 | Area 1 stub ABR demo (lab-03 Task 2) |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID |
| R4 | Loopback1 | 172.20.4.0/24 | External prefix (advertised to AS 65100 via eBGP) |
| R4 | Loopback2 | 172.20.5.0/24 | External prefix (filter target on R1) |
| XR1 | Loopback0 | 10.0.0.5/32 | Router ID, iBGP peering source |
| XR1 | Loopback1 | 172.16.11.0/24 | Customer prefix for RPL/IS-IS filter demos |
| XR2 | Loopback0 | 10.0.0.6/32 | Router ID, iBGP peering source |

### Cabling Table

| Link ID | Source | Interface | Target | Interface | Subnet | Purpose |
|---------|--------|-----------|--------|-----------|--------|---------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | OSPF area 0, IS-IS L2, iBGP |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/24 | OSPF area 0, IS-IS L2, iBGP |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 | 10.1.34.0/24 | eBGP R3↔R4 |
| L4 | R1 | Gi0/1 | R4 | Gi0/1 | 10.1.14.0/24 | eBGP R1↔R4 |
| L5 | R1 | Gi0/2 | R3 | Gi0/2 | 10.1.13.0/24 | OSPF area 0, IS-IS L2, iBGP |
| L6 | R2 | Gi0/2 | XR1 | Gi0/0/0/0 | 10.1.25.0/24 | IS-IS L1 boundary (lab-03) |
| L7 | R3 | Gi0/3 | XR2 | Gi0/0/0/0 | 10.1.36.0/24 | IS-IS L2, iBGP |
| L8 | XR1 | Gi0/0/0/1 | XR2 | Gi0/0/0/1 | 10.1.56.0/24 | IS-IS L2, iBGP |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | OSPF E1 (redistribute connected) + BGP network | Customer prefix |
| R4 | 172.20.4.0/24 | eBGP network | External prefix to AS 65100 |
| R4 | 172.20.5.0/24 | eBGP network | External prefix (filtered at R1 inbound) |
| XR1 | 172.16.11.0/24 | IS-IS L1 (via RPL filter) + BGP network | XR customer prefix |
| R2 | 10.2.1.0/24 | OSPF area 1 (stub) | ABR demo prefix — filtered from area 0 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| XR1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| XR2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames on all 6 devices
- Interface IP addressing on all routed links and loopbacks (lab-02 full addressing)
- `no ip domain-lookup` on all IOS routers
- OSPF area 0 on R1, R2, R3 (point-to-point network type on all links; R1/R3 redistribution of connected routes into OSPF)
- IS-IS process SP on all 6 routers, level-2-only, metric-style wide — all interfaces active except Loopback0 (passive)
- iBGP full mesh in AS 65100 across R1, R2, R3, XR1, XR2 (peer-groups / neighbor-groups, Loopback0 source; `next-hop-self` on R1 and R3 only — XR1 and XR2 have no eBGP peers)
- eBGP sessions R1↔R4 (10.1.14.0/24) and R3↔R4 (10.1.34.0/24)
- Lab-02 route-maps: FILTER_R4_IN on R1, FILTER_R4_ASPATH on R3, OSPF_TO_ISIS and ISIS_TO_OSPF on R2/R3 (with tag-based loop-prevention)
- XR1 and XR2 RPL named sets (P_CUSTOMER, P_TRANSIT, C_SP_PREF) and policies (PASS, FILTER_BOGONS, IBGP_IN, EBGP_IN, CLASSIFY_PREFIXES)
- R2-IS-IS redistribution from OSPF (OSPF_TO_ISIS) and R3 bidirectional redistribution

**IS NOT pre-loaded** (student configures during this lab):

- OSPF distribute-list to filter a specific prefix from R2's routing table
- OSPF ABR area stub and filter-list on R2 (Loopback1 in area 1 not pre-configured)
- OSPF prefix-suppression on R1's transit interfaces
- IS-IS level-1-2 configuration on R2 and XR1
- IS-IS circuit-type level-1 on the R2↔XR1 link
- IS-IS selective L1-to-L2 route leaking on R2 (LEAK_L1_TO_L2 route-map)
- RPL policy definitions on XR1 (ISIS_L1_FILTER_PARENT/CHILD, P_XR1_LOOPBACKS) and `advertise passive-only` under IS-IS AF
- Metric-type internal and tag 300 on OSPF external redistribution into IS-IS (R2's OSPF_TO_ISIS update)

---

## 5. Lab Challenge: Core Implementation

### Task 1: OSPF Distribute-List — RIB Filtering on R2

- On R2, create a named prefix-list called `BLOCK_MGMT` that denies the customer prefix
  172.16.1.0/24 and permits all other prefixes.
- Apply this prefix-list as an inbound distribute-list on R2's OSPF process.
- After applying, confirm that 172.16.1.0/24 is absent from R2's OSPF-learned routes in the
  RIB but is still present in R2's OSPF LSDB as a Type 5 (external) LSA — the key distinction
  between distribute-list and filter-list.
- Note that the route *may still appear* via IS-IS on R2 (as `i L2`). This is because R2
  redistributes OSPF into IS-IS, R3 learns it via OSPF and re-redistributes it into IS-IS,
  and R2 receives it back from R3's IS-IS LSP. This is expected and does not mean the
  distribute-list failed — what matters is that the **OSPF** route is blocked.
- R1 and R3 must still have 172.16.1.0/24 in their routing tables (as OSPF E1).

**Verification:** `show ip route 172.16.1.0` on R2 must NOT show an OSPF route (it may show
IS-IS `i L2`). Use `show ip route ospf | include 172.16.1.0` to confirm the OSPF route is
blocked. `show ip ospf database external 172.16.1.0` on R2 must still show the LSA.
`show ip route 172.16.1.0` on R1 and R3 must still show the route.

---

### Task 2: OSPF ABR Filter-List — Inter-Area Type 3 LSA Suppression on R2

- Add Loopback1 to R2 with address 10.2.1.2/24 and place it in OSPF area 1.
- Configure area 1 as a stub area on R2's OSPF process (R2 is the only ABR).
- Create a prefix-list named `FILTER_TRANSIT` that denies 10.2.1.0/24 and permits
  everything else.
- Apply this prefix-list as an `area 0 filter-list in` on R2's OSPF process. This should
  prevent R2 from flooding the Type 3 summary LSA for 10.2.1.0/24 into area 0.
- Verify that no other routers in area 0 (R1, R3) have a Type 3 LSA or route for 10.2.1.0/24.

**Verification:** `show ip ospf database summary` on R1 and R3 must show no entry for 10.2.1.0/24. `show ip route 10.2.1.0` on R1 and R3 must return no result. `show ip route 10.2.1.0` on R2 must show the directly connected route.

---

### Task 3: OSPF Prefix Suppression on R1's Transit Interfaces

- On R1, apply `ip ospf prefix-suppression` to both transit interfaces: Gi0/0 (to R2) and
  Gi0/2 (to R3). Do not apply it to Loopback0 or Loopback1 or the eBGP interface Gi0/1.
- Verify that OSPF adjacencies on both interfaces remain fully established.
- Verify that the transit subnets 10.1.12.0/24 and 10.1.13.0/24 are no longer present in
  R1's own Type 1 Router LSA but are still reachable via IS-IS (which is still advertising them).

**Verification:** `show ip ospf database router 10.0.0.1` must not list 10.1.12.0/24 or 10.1.13.0/24 as link stubs. `show ip ospf neighbor` on R1 must still show R2 and R3 as FULL. `show ip route 10.1.12.0` on R2 must still show the subnet (via IS-IS).

---

### Task 4: IS-IS Level Boundary — R2 as L1-L2 ABR with XR1

- Change R2's IS-IS process from level-2-only to level-1-2.
- On R2's Gi0/2 interface (link to XR1), restrict the IS-IS circuit to level-1 only so that
  only a Level 1 adjacency forms on that link.
- Change XR1's IS-IS process from level-2-only to level-1-2 and configure GigabitEthernet0/0/0/0
  (link to R2) as level-1 circuit-type. GigabitEthernet0/0/0/1 (to XR2) should remain at its
  default level (Level 2).
- On XR1, add Loopback1 (172.16.11.0/24) to the IS-IS process as a passive interface so that
  both XR1 loopbacks are candidates for IS-IS advertisement.
- Verify that exactly one Level 1 adjacency exists: R2↔XR1 on the 10.1.25.0/24 link.
  Verify that R2's Level 2 adjacencies to R1 and R3 remain intact.
- Verify that XR1's Level 2 adjacency to XR2 on L8 remains intact.

**Verification:** `show isis neighbors` on R2 must show R1 and R3 as L2, and XR1 as L1. `show isis neighbors` on XR1 must show R2 as L1 and XR2 as L2. Note: XR1's loopbacks 10.0.0.5/32 and 172.16.11.0/24 will be visible on R3 via
  XR2 (10.1.36.6) even before Task 5 — this is because IOS XRv 6.3.1 advertises loopback
  prefixes in both L1 and L2 by default. The L1-to-L2 leak in Task 5 adds a **second
  path** via R2 (10.1.23.2), which is the key verification of the leak.

---

### Task 5: IS-IS Selective L1-to-L2 Route Leaking on R2

- Create a prefix-list named `LEAK_FROM_L1` that permits XR1's two loopback addresses:
  10.0.0.5/32 and 172.16.11.0/24.
- Create a route-map named `LEAK_L1_TO_L2` with a single permit sequence that matches this
  prefix-list. (The implicit deny at the end blocks all other L1 prefixes from reaching L2.)
- On R2's IS-IS process, add a statement that redistributes IS-IS level-1 IP routes into
  level-2 using the `LEAK_L1_TO_L2` route-map: `redistribute isis ip level-1 into level-2
  route-map LEAK_L1_TO_L2`. The `ip` keyword is required on IOSv to target IPv4 routes.
- **Platform note (XRv 6.3.1):** Because IOS XRv 6.3.1 floods XR1's loopbacks into both L1
  and L2 LSPs by default, R3 redistributes them into OSPF (tag 200) before Task 5. R2 then
  learns them via OSPF (AD 110), which beats IS-IS L1 (AD 115). This prevents
  `redistribute isis ip level-1 into level-2` from seeing them as L1 routes. Fix: add
  `distance 109 ip` under R2's `router isis SP` to lower the IS-IS IP AD below OSPF.
- Verify that 10.0.0.5/32 and 172.16.11.0/24 now appear in the IS-IS L2 routing table on R3
  and XR2 (both prefixes are permitted by LEAK_FROM_L1). Before the leak, XR1's loopbacks
  were visible on R3 via XR2 only; after the leak, a **second path via R2 (10.1.23.2)**
  appears on R3 — this is the key confirmation that the L1-to-L2 leak is working. XR2 will
  show both prefixes but via the direct L2 path from XR1 (metric 10), not via R3 — this is
  correct because XR1↔XR2 direct metric is lower than the leaked path. Confirm that no other
  L1-only prefixes are leaked — the implicit deny at the end of LEAK_L1_TO_L2 blocks anything
  not explicitly permitted.

**Verification:** `show ip route isis` on R3 must include 10.0.0.5/32 and 172.16.11.0/24 with a second IS-IS L2 path via R2 (10.1.23.2) in addition to the existing path via XR2. `show route ipv4 isis` on XR2 must include both prefixes — they will appear via the direct L2 path from XR1 (10.1.56.5, metric 10), not via R3, since the direct path has lower metric. `show isis database level-2 R2.00-00 detail` on R2 must confirm the L2 LSP for R2 now carries 10.0.0.5/32 and 172.16.11.0/24.

---

### Task 6: XR1 IS-IS Advertisement Restriction

> **Platform note:** This lab runs IOS XRv 6.3.1 (classic). The `route-policy <name> out`
> knob under `router isis / address-family ipv4 unicast` is not present in this version —
> it requires XRv 9000 6.5+. The functional equivalent on 6.3.1 is `advertise passive-only`.
> The RPL policies below are defined as a conceptual exercise to demonstrate the `apply`
> pattern (same as lab-02 BGP), but they are **not attached to IS-IS** in this lab.

- On XR1, define a `prefix-set` named `P_XR1_LOOPBACKS` containing 10.0.0.5/32 and
  172.16.11.0/24.
- Write a child route-policy named `ISIS_L1_FILTER_CHILD` that passes prefixes matching
  `P_XR1_LOOPBACKS` and drops everything else.
- Write a parent route-policy named `ISIS_L1_FILTER_PARENT` that calls `ISIS_L1_FILTER_CHILD`
  via the `apply` statement. Verify the policy exists and the `apply` line is present — this
  is the pattern from lab-02, now shown in an IS-IS context to demonstrate reusability.
- On XR1's IS-IS process address-family, configure `advertise passive-only`. This restricts
  IS-IS to advertising only prefixes belonging to passive interfaces (Loopback0 and Loopback1),
  suppressing active-interface subnets (10.1.25.0/24, 10.1.56.0/24). Contrast with the IOS
  equivalent (`distribute-list prefix-list X out` under `router isis`).
- Verify that XR1's IS-IS LSDB entries show only 10.0.0.5/32 and 172.16.11.0/24 as originated
  by XR1; link subnets are no longer present in XR1's LSPs.

**Verification:** `show isis database detail XR1.00-00` on R2 (Level-1 LSDB) must show only
10.0.0.5/32 and 172.16.11.0/24 — no link subnets. `show rpl policy ISIS_L1_FILTER_PARENT`
on XR1 must show the `apply ISIS_L1_FILTER_CHILD` statement (confirming the policy is defined).
`show run formal router isis SP` on XR1 must include `advertise passive-only`.

---

### Task 7: OSPF External Redistribution into IS-IS — Metric-Type Internal and Tag 300

- Update R2's `OSPF_TO_ISIS` route-map to set `metric-type internal` and `tag 300` on OSPF
  external type-1 and type-2 routes being redistributed into IS-IS.
  Internal OSPF routes should continue to receive tag 100 (unchanged from lab-02).
  Ensure the loop-prevention deny clause for tag 200 remains as sequence 10.
- Verify on R3 that OSPF external prefixes redistributed from R2 (e.g., 172.16.1.0/24) now
  appear in IS-IS with metric-type internal (the IS-IS route metric will be set rather than
  shown as an external metric).
- Verify on XR2 that the same routes appear via IS-IS L2.

**Verification:** `show ip route isis` on R3 and `show route ipv4 isis` on XR2 must show 172.16.1.0/24 with an IS-IS L2 metric (not an external IS-IS metric). `show isis topology` on R3 must show the path through R2 for XR1-originated prefixes. `show route-map OSPF_TO_ISIS` on R2 must show sequence 20 and 30 with both `set tag 300` and `set metric-type internal`.

---

## 6. Verification & Analysis

### Task 1 — OSPF Distribute-List Verification

```
R2# show ip route 172.16.1.0
! The OSPF E1 route is blocked by BLOCK_MGMT distribute-list.
! The route may still appear via IS-IS (i L2) due to R3's OSPF-to-ISIS
! redistribution loop:
!   i L2  172.16.1.0/24 [115/20] via 10.1.23.3, GigabitEthernet0/1
!
! To verify the OSPF route specifically is blocked:
R2# show ip route ospf | include 172.16.1.0
! ← no output — OSPF route is absent from RIB

R2# show ip ospf database external 172.16.1.0
            OSPF Router with ID (10.0.0.2) (Process ID 1)
                Type-5 AS External Link States
  LS age: 42
  Options: (No TOS-capability, DC)
  LS Type: AS External Link
  Link State ID: 172.16.1.0 (External Network Number )
  Advertising Router: 10.0.0.1                 ! ← LSA still in LSDB from R1
  ...
  External Route Tag: 0

R1# show ip route 172.16.1.0 255.255.255.0
O E1  172.16.1.0/24 [110/20] via ...           ! ← R1 still has the route (not affected)
```

### Task 2 — OSPF ABR Filter-List Verification

```
R1# show ip ospf database summary
            OSPF Router with ID (10.0.0.1) (Process ID 1)
                Summary Net Link States (Area 0)
! ← 10.2.1.0/24 must NOT appear here; filter-list blocks the Type 3 LSA

R2# show ip ospf database summary
            ...
  LS Type: Summary Links(Network)
  Link State ID: 10.2.1.0 (Summary Network Number)    ! ← Type 3 LSA exists on ABR R2
  Advertising Router: 10.0.0.2
! R2 generates it but does NOT flood into area 0 due to area 0 filter-list in
```

### Task 3 — OSPF Prefix Suppression Verification

```
R2# show ip ospf database router 10.0.0.1
            OSPF Router with ID (10.0.0.1) (Process ID 1)
                Router Link States (Area 0)
  ...
  Number of Links: 2                            ! ← only Lo0 and one or two non-suppressed links
  ! 10.1.12.0/24 and 10.1.13.0/24 stub entries must NOT appear here

R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          0   FULL/  -        00:00:34    10.1.12.2       GigabitEthernet0/0  ! ← adjacency FULL
10.0.0.3          0   FULL/  -        00:00:38    10.1.13.3       GigabitEthernet0/2  ! ← adjacency FULL
```

### Task 4 — IS-IS Level Boundary Verification

```
R2# show isis neighbors
System Id      Type Interface   IP Address      State Holdtime Circuit Id
R1             L2   Gi0/0       10.1.12.1       UP    23       ...         ! ← R1 is L2
R3             L2   Gi0/1       10.1.23.3       UP    26       ...         ! ← R3 is L2
XR1            L1   Gi0/2       10.1.25.5       UP    21       ...         ! ← XR1 is L1 only

RP/0/0/CPU0:XR1# show isis neighbors
System Id      Intf            SNPA              State  Holdtime Type IETF-NSF
R2             Gi0/0/0/0       *PtoP*            Up     24       L1   Capable ! ← R2 is L1
XR2            Gi0/0/0/1       *PtoP*            Up     28       L2   Capable ! ← XR2 is L2
```

### Task 5 — IS-IS Level Leak Verification

```
R3# show ip route isis
! Before Task 5: 10.0.0.5/32 visible via XR2 only
! After Task 5:  second path via R2 appears (R2's L2 LSP now carries leaked L1 prefixes)
i L2  10.0.0.5/32 [115/20] via 10.1.23.2, GigabitEthernet0/0   ! ← new path via R2 leak
i L2  10.0.0.5/32 [115/20] via 10.1.36.6, GigabitEthernet0/3   ! ← existing path via XR2
! 10.2.1.0/24 (R2's area-1 loopback) must NOT appear here via IS-IS

RP/0/0/CPU0:XR2# show route ipv4 isis
i L2  10.0.0.5/32 [115/10] via 10.1.56.5, GigabitEthernet0/0/0/1   ! ← direct L2 path from XR1 wins (metric 10)
i L2  172.16.11.0/24 [115/10] via 10.1.56.5, GigabitEthernet0/0/0/1 ! ← leaked path via R3 has metric 30; XR2 prefers direct
```

### Task 6 — XR1 IS-IS Advertisement Restriction Verification

```
RP/0/0/CPU0:XR1# show rpl policy ISIS_L1_FILTER_PARENT
route-policy ISIS_L1_FILTER_PARENT
  apply ISIS_L1_FILTER_CHILD                  ! ← hierarchical apply defined (not applied to IS-IS on 6.3.1)
end-policy

RP/0/0/CPU0:XR1# show run formal router isis SP | include advertise
router isis SP address-family ipv4 unicast advertise passive-only
! ← advertise passive-only is the 6.3.1 equivalent of route-policy out

R2# show isis database detail XR1.00-00
IS-IS SP (Level-1) Link State Database:
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime  ATT/P/OL
XR1.00-00             0x0000000c   0x3c2a        1197          1/0/0
  ...
  Metric: 0          IP 10.0.0.5/32       ! ← Lo0 (passive) — advertised
  Metric: 0          IP 172.16.11.0/24    ! ← Lo1 (passive) — advertised
  ! 10.1.25.0/24 and 10.1.56.0/24 no longer present (active interfaces suppressed)
```

### Task 7 — OSPF-to-IS-IS Redistribution Verification

```
R2# show route-map OSPF_TO_ISIS
route-map OSPF_TO_ISIS, deny, sequence 10
  Match clauses:
    tag 200                               ! ← loop-prevention intact
  Set clauses:
route-map OSPF_TO_ISIS, permit, sequence 20
  Match clauses:
    route-type external type-1
  Set clauses:
    tag 300                               ! ← tag 300 on external type-1
    metric-type internal                  ! ← IS-IS metric-type internal
route-map OSPF_TO_ISIS, permit, sequence 30
  Match clauses:
    route-type external type-2
  Set clauses:
    tag 300                               ! ← tag 300 on external type-2
    metric-type internal
route-map OSPF_TO_ISIS, permit, sequence 40
  Match clauses:
    route-type internal
  Set clauses:
    tag 100                               ! ← internal routes get tag 100

R3# show ip route isis 172.16.1.0
i L2  172.16.1.0/24 [115/20] via 10.1.23.2, GigabitEthernet0/0 ! ← IS-IS internal metric
```

---

## 7. Verification Cheatsheet

### OSPF Route Filtering

```
! Task 1 — distribute-list
router ospf 1
  distribute-list prefix <name> in

! Task 2 — ABR filter-list
router ospf 1
  area <N> stub
  area 0 filter-list prefix <name> in | out

! Task 3 — prefix-suppression (interface level)
interface <type><num>
  ip ospf prefix-suppression
```

| Command | Purpose |
|---------|---------|
| `show ip route <prefix>` | Confirm prefix absent from RIB (distribute-list effect) |
| `show ip ospf database external <prefix>` | Confirm LSA still in LSDB despite RIB filter |
| `show ip ospf database summary` | Confirm Type 3 LSA not flooded (filter-list effect) |
| `show ip ospf database router <router-id>` | Confirm suppressed interface absent from Type 1 LSA |
| `show ip ospf neighbor` | Confirm adjacencies remain FULL after prefix suppression |

> **Exam tip:** `distribute-list in` on OSPF does NOT affect the LSDB — the LSA is still
> present and flooded. The route is simply not installed in the local RIB. This is a
> frequent exam distractor.

---

### IS-IS Level Boundary and Route Leaking

```
! IOS — level-1-2 boundary router
router isis SP
  is-type level-1-2

! IOS — circuit-type per interface
interface <type><num>
  isis circuit-type level-1

! IOS — selective L1-to-L2 leak (ip keyword required on IOSv for IPv4)
router isis SP
  redistribute isis ip level-1 into level-2 route-map <name>
  distance 109 ip   ! lower IS-IS AD below OSPF when bidirectional redistribution is active

! XR — level-1-2 and circuit-type
router isis SP
  is-type level-1-2
  interface Gi0/0/0/0
    circuit-type level-1

! XR — selective L1-to-L2 leak
router isis SP
  address-family ipv4 unicast
    redistribute isis level 1 route-policy <name>
```

| Command | Purpose |
|---------|---------|
| `show isis neighbors` | Verify adjacency level (L1 vs L2) per peer |
| `show isis database detail <hostname>` | Confirm which prefixes appear in L1 vs L2 LSPs |
| `show ip route isis` | Verify leaked L1 prefixes present in L2 routing table |
| `show route ipv4 isis` (XR) | Same on XR nodes |

> **Exam tip:** A missing `route-map` on `redistribute isis ip level-1 into level-2` means ALL L1
> routes leak to L2. A route-map with only specific `permit` sequences means everything else
> hits the implicit deny and is blocked — the most common source of "routes missing in L2."
> On IOSv with bidirectional OSPF↔IS-IS redistribution, also verify that IS-IS L1 routes
> are winning in the RIB (`show ip route <prefix>` shows `i L1`); if OSPF wins (AD 110 < 115),
> add `distance 109 ip` under `router isis` to allow L1 routes to install.

---

### XR IS-IS Advertisement Control

```
! IOS XRv 6.3.1 — restrict IS-IS to passive-interface prefixes only
router isis SP
  address-family ipv4 unicast
    advertise passive-only

! IOS XRv 9000 (6.5+) — route-policy applied to IS-IS address-family
router isis SP
  address-family ipv4 unicast
    route-policy ISIS_FILTER_PARENT out   ! not available on XRv classic 6.3.x
```

```
! RPL apply pattern (define-only exercise on 6.3.1; functional for BGP on all versions)
prefix-set P_FILTER
  <prefixes>
end-set

route-policy ISIS_FILTER_CHILD
  if destination in P_FILTER then
    pass
  else
    drop
  endif
end-policy

route-policy ISIS_FILTER_PARENT
  apply ISIS_FILTER_CHILD
end-policy
```

| Command | Purpose |
|---------|---------|
| `show run formal router isis SP \| include advertise` | Confirm `advertise passive-only` configured |
| `show rpl policy <name>` | Confirm `apply` statement present in parent policy |
| `show rpl policy <name> detail` | Show child policy expansion inline |
| `show isis database detail <node>` | Verify which prefixes appear in IS-IS LSDB from this router |

---

### OSPF Redistribution into IS-IS — Metric-Type Internal

```
route-map OSPF_TO_ISIS deny 10
  match tag 200        ! loop-prevention: block IS-IS→OSPF→IS-IS
!
route-map OSPF_TO_ISIS permit 20
  match route-type external type-1
  set tag 300
  set metric-type internal
!
route-map OSPF_TO_ISIS permit 30
  match route-type external type-2
  set tag 300
  set metric-type internal
!
route-map OSPF_TO_ISIS permit 40
  match route-type internal
  set tag 100
```

| Command | Purpose |
|---------|---------|
| `show route-map OSPF_TO_ISIS` | Verify all four sequences present with correct set clauses |
| `show ip route isis <prefix>` | Verify redistributed external shows IS-IS metric not external metric |
| `show isis topology` | Confirm redistribution paths through R2 |

> **Exam tip:** Without `set metric-type internal`, redistributed routes appear in IS-IS with
> the IS-IS external metric type and may be preferred differently at remote routers. The
> implicit deny at the end of a route-map silently drops all unmatched routes — always
> verify with `show route-map` that every route-type you expect to match has a permit sequence.

---

### Verification Commands Summary

| Command | What to Look For |
|---------|-----------------|
| `show ip route <pfx>` | Route absent (distribute-list) or present (leak succeeded) |
| `show ip ospf database external` | LSA present despite RIB filter |
| `show ip ospf database summary` | Type 3 absent (filter-list) |
| `show ip ospf database router <rid>` | Transit prefixes absent (prefix-suppression) |
| `show ip ospf neighbor` | Adjacency FULL despite prefix-suppression |
| `show isis neighbors` | L1 vs L2 adjacency type per peer |
| `show isis database detail` | Per-router prefix list in IS-IS LSDB |
| `show ip route isis` / `show route ipv4 isis` | Leaked L1 prefixes in L2 table |
| `show rpl policy <name>` (XR) | `apply` statement present in parent policy |
| `show route-map OSPF_TO_ISIS` | All sequences with correct match and set clauses |

### Common IS-IS Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| L1 adjacency not forming with R2 | XR1 interface not set to `circuit-type level-1` |
| XR1 loopbacks missing from L2 routing table on R3 | `redistribute isis ip level-1 into level-2` missing or route-map implicit deny; or `distance 109 ip` missing (OSPF superseding IS-IS L1) |
| Leaked prefixes present on R3 but not on XR2 | XR1-XR2 L8 adjacency broken — check XR1 is level-1-2, not level-1-only |
| 172.16.1.0/24 missing from IS-IS on R3 | OSPF_TO_ISIS missing permit for external type-1 (implicit deny) |
| R2 still sees 172.16.1.0/24 as an OSPF route (`O E1`) in routing table | `distribute-list prefix BLOCK_MGMT in` not applied under `router ospf 1` |
| Type 3 LSA for 10.2.1.0/24 visible on R1 | `area 0 filter-list prefix FILTER_TRANSIT in` not configured or R2 not ABR |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: OSPF Distribute-List

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip prefix-list BLOCK_MGMT seq 5 deny 172.16.1.0/24
ip prefix-list BLOCK_MGMT seq 10 permit 0.0.0.0/0 le 32
!
router ospf 1
  distribute-list prefix BLOCK_MGMT in
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R2# show ip route 172.16.1.0 | include O E1|i L2
! expect: IS-IS route (i L2) may appear via R3 redistribution — this is normal
! expect: OSPF route (O E1) must NOT appear in the output
! To confirm the OSPF route is specifically blocked:

R2# show ip ospf database external 172.16.1.0
! expect: Type-5 LSA for 172.16.1.0 with Advertising Router 10.0.0.1

R1# show ip route 172.16.1.0
! expect: O E1 172.16.1.0/24 (still present on R1)
```

</details>

---

### Task 2: OSPF ABR Filter-List

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface Loopback1
  ip address 10.2.1.2 255.255.255.0
  ip ospf 1 area 1
!
ip prefix-list FILTER_TRANSIT seq 5 deny 10.2.1.0/24
ip prefix-list FILTER_TRANSIT seq 10 permit 0.0.0.0/0 le 32
!
router ospf 1
  area 1 stub
  area 0 filter-list prefix FILTER_TRANSIT in
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R1# show ip ospf database summary
! expect: no entry for 10.2.1.0/24

R2# show ip route 10.2.1.0
! expect: C 10.2.1.0/24 directly connected (R2 itself can reach it)

R1# show ip route 10.2.1.0
! expect: % Network not in table
```

</details>

---

### Task 3: OSPF Prefix Suppression

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
interface GigabitEthernet0/0
  ip ospf prefix-suppression
!
interface GigabitEthernet0/2
  ip ospf prefix-suppression
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R1# show ip ospf neighbor
! expect: R2 and R3 both FULL

R2# show ip ospf database router 10.0.0.1
! expect: 10.1.12.0 and 10.1.13.0 NOT listed as stub link entries in R1's LSA
```

</details>

---

### Task 4: IS-IS Level Boundary

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router isis SP
  is-type level-1-2
!
interface GigabitEthernet0/2
  isis circuit-type level-1
```

</details>

<details>
<summary>Click to view XR1 Configuration</summary>

```bash
! XR1
router isis SP
  is-type level-1-2
  interface Loopback0
   passive
   address-family ipv4 unicast
   exit
  exit
  interface Loopback1
   passive
   address-family ipv4 unicast
   exit
  exit
  interface GigabitEthernet0/0/0/0
    circuit-type level-1
  exit
exit
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R2# show isis neighbors
! expect: R1=L2, R3=L2, XR1=L1

XR1# show isis neighbors
! expect: R2=L1, XR2=L2
```

</details>

---

### Task 5: IS-IS Selective L1-to-L2 Leak

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip prefix-list LEAK_FROM_L1 seq 5 permit 10.0.0.5/32
ip prefix-list LEAK_FROM_L1 seq 10 permit 172.16.11.0/24
!
route-map LEAK_L1_TO_L2 permit 10
  match ip address prefix-list LEAK_FROM_L1
!
router isis SP
  redistribute isis ip level-1 into level-2 route-map LEAK_L1_TO_L2
  distance 109 ip
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R3# show ip route isis
! expect: i L2 10.0.0.5/32 and i L2 172.16.11.0/24 both present via BOTH:
!   10.1.36.6 (XR2 — existing path) AND 10.1.23.2 (R2 — new leaked path)

XR2# show route ipv4 isis
! expect: both prefixes present via 10.1.56.5 (XR1 direct L2 — metric 10)
! XR2 does NOT show the leaked path via R3 (metric 30) — direct path wins
```

</details>

---

### Task 6: XR1 IS-IS Advertisement Restriction

<details>
<summary>Click to view XR1 Configuration</summary>

```bash
! XR1 — Step 1: define RPL policies (conceptual apply exercise; not applied to IS-IS on 6.3.1)
prefix-set P_XR1_LOOPBACKS
  10.0.0.5/32,
  172.16.11.0/24
end-set
!
route-policy ISIS_L1_FILTER_CHILD
  if destination in P_XR1_LOOPBACKS then
    pass
  else
    drop
  endif
end-policy
!
route-policy ISIS_L1_FILTER_PARENT
  apply ISIS_L1_FILTER_CHILD
end-policy
!
! XR1 — Step 2: restrict IS-IS advertisement to passive interfaces only (6.3.1 mechanism)
router isis SP
  address-family ipv4 unicast
    advertise passive-only
  exit
exit
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
XR1# show rpl policy ISIS_L1_FILTER_PARENT
! expect: "apply ISIS_L1_FILTER_CHILD" visible in body (policy defined, not applied to IS-IS)

XR1# show run formal router isis SP | include advertise
! expect: router isis SP address-family ipv4 unicast advertise passive-only

R2# show isis database detail XR1.00-00
! expect: only 10.0.0.5/32 and 172.16.11.0/24 in XR1's L1 LSP; no link subnets
```

</details>

---

### Task 7: OSPF-to-IS-IS Redistribution with Metric-Type Internal

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — update existing OSPF_TO_ISIS permit sequences (deny seq 10 keeps tag-200 loop prevention)
no route-map OSPF_TO_ISIS permit 20
no route-map OSPF_TO_ISIS permit 30
no route-map OSPF_TO_ISIS permit 40
!
route-map OSPF_TO_ISIS permit 20
  match route-type external type-1
  set tag 300
  set metric-type internal
!
route-map OSPF_TO_ISIS permit 30
  match route-type external type-2
  set tag 300
  set metric-type internal
!
route-map OSPF_TO_ISIS permit 40
  match route-type internal
  set tag 100
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R2# show route-map OSPF_TO_ISIS
! expect: seq 20/30 both show "set tag 300" and "set metric-type internal"

R3# show ip route isis 172.16.1.0
! expect: i L2 172.16.1.0/24 [115/20] via 10.1.23.2 (IS-IS internal metric)
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix
using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip> # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore
```

---

### Ticket 1 — R2's Routing Table is Missing Routes That Should Be Present After OSPF Filtering

A colleague applied a distribute-list to R2 to block the management prefix. After the change,
network monitoring shows that R2 is not forwarding some traffic it should be routing normally,
and `show ip route` on R2 shows several unexpected gaps in the table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R2's routing table contains 172.16.1.0/24 and all expected 10.0.0.x/32
loopback routes. Only 172.16.1.0/24 should be blocked (the intended management prefix — which
is 192.168.x.x in a real network, but 172.16.1.0/24 in this lab).

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check R2's routing table for gaps
R2# show ip route

! 2. Check distribute-list configuration
R2# show ip ospf | include distribute

! 3. Check the prefix-list that is applied
R2# show ip prefix-list BLOCK_MGMT
!    Look for whether the deny range is too broad (e.g., /8 or /16 instead of /24)

! 4. Confirm with ospf database that LSAs still exist
R2# show ip ospf database external
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! The BLOCK_MGMT prefix-list has been changed to deny too broad a range.
! Fix: correct the prefix-list to deny only 172.16.1.0/24
R2# conf t
R2(config)# no ip prefix-list BLOCK_MGMT
R2(config)# ip prefix-list BLOCK_MGMT seq 5 deny 172.16.1.0/24
R2(config)# ip prefix-list BLOCK_MGMT seq 10 permit 0.0.0.0/0 le 32
```

</details>

---

### Ticket 2 — IS-IS Prefixes from XR1 Are Not Appearing in the L2 Domain After Level Boundary Changes

The IS-IS level boundary between R2 and XR1 was recently configured. R3 reports it cannot
reach XR1's Loopback0 (10.0.0.5/32) or Loopback1 (172.16.11.0/24). The Level 1 adjacency
between R2 and XR1 appears to be up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip route isis` on R3 shows both 10.0.0.5/32 and 172.16.11.0/24
as IS-IS L2 routes via R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm L1 adjacency is up on R2
R2# show isis neighbors
! Look for XR1 in state UP as L1

! 2. Verify R2's L1 LSDB — can R2 see XR1's L1 LSP?
R2# show isis database detail level-1
! Look for XR1.00-00 with 10.0.0.5/32 and 172.16.11.0/24

! 3. Check whether R2 is leaking to L2
R2# show isis database detail level-2
! If XR1 prefixes are NOT in R2's L2 LSP, check the route-map

! 4. Check LEAK_FROM_L1 prefix-list
R2# show ip prefix-list LEAK_FROM_L1
! Look for wrong IP (e.g., 10.0.0.50/32 instead of 10.0.0.5/32)

! 5. Trace the route-map
R2# show route-map LEAK_L1_TO_L2
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! LEAK_FROM_L1 prefix-list has a typo — 10.0.0.50/32 instead of 10.0.0.5/32.
! Fix: correct the prefix-list entry.
R2# conf t
R2(config)# no ip prefix-list LEAK_FROM_L1 seq 5
R2(config)# ip prefix-list LEAK_FROM_L1 seq 5 permit 10.0.0.5/32
```

</details>

---

### Ticket 3 — 2 of 5 OSPF External Prefixes Are Missing from IS-IS on Downstream Routers

After a config audit, R3 reports that several prefixes it expects to learn via IS-IS from R2
(redistributed from OSPF) are not appearing in its routing table. The redistribution is
configured, but the results are incomplete.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** All OSPF external prefixes redistributed by R2 into IS-IS appear on
R3 and XR2 with IS-IS metric-type internal and tag 300.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check what IS-IS routes R3 sees from R2
R3# show ip route isis
! Note which prefixes are present and which are absent

! 2. On R2, check the route-map sequence count
R2# show route-map OSPF_TO_ISIS
! Count the number of permit sequences. Should be: deny 10, permit 20, permit 30, permit 40.
! If permit 30 (match route-type external type-2) is missing, E2 routes hit implicit deny.

! 3. Confirm missing routes are OSPF E2 in R2's table
R2# show ip route | include E2
! These are the routes being dropped

! 4. Verify with debug (non-disruptive): check how many routes the route-map is processing
R2# show route-map OSPF_TO_ISIS
! Policy-matches counter on the implicit deny will show non-zero if routes are being dropped
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! OSPF_TO_ISIS route-map is missing the permit sequence for external type-2 routes.
! The implicit deny at the end of the route-map silently drops OSPF E2 routes.
R2# conf t
R2(config)# route-map OSPF_TO_ISIS permit 30
R2(config-route-map)# match route-type external type-2
R2(config-route-map)# set tag 300
R2(config-route-map)# set metric-type internal
R2(config-route-map)# exit
! Trigger soft redistribution to re-evaluate
R2(config)# do clear ip route *
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] Task 1: BLOCK_MGMT prefix-list applied as distribute-list in on R2's OSPF; 172.16.1.0/24 absent from R2's OSPF RIB entries (may still appear via IS-IS), present in LSDB
- [x] Task 2: R2's Loopback1 in area 1 stub; area 0 filter-list blocks Type 3 LSA for 10.2.1.0/24 from R1/R3
- [x] Task 3: R1 Gi0/0 and Gi0/2 have prefix-suppression; adjacencies FULL; transit subnets absent from R1's Type 1 LSA
- [ ] Task 4: R2 is level-1-2; G0/2 is circuit-type level-1; XR1 is level-1-2; XR1 loopbacks have circuit-type level-1 and Loopback1 added to IS-IS (passive); R2↔XR1 L1 adjacency up; R2↔R1/R3 L2 adjacencies intact
- [ ] Task 5: LEAK_FROM_L1 permits only 10.0.0.5/32 and 172.16.11.0/24; LEAK_L1_TO_L2 route-map applied; both prefixes visible on R3 and XR2 via IS-IS L2
- [ ] Task 6: P_XR1_LOOPBACKS prefix-set, ISIS_L1_FILTER_CHILD, and ISIS_L1_FILTER_PARENT defined on XR1 (apply pattern demonstrated); `advertise passive-only` applied under IS-IS AF; XR1 LSDB shows only 10.0.0.5/32 and 172.16.11.0/24 (no link subnets)
- [ ] Task 7: R2 OSPF_TO_ISIS sequences 20/30 have `set tag 300` and `set metric-type internal`; 172.16.1.0/24 appears as IS-IS route on R3

### Troubleshooting

- [ ] Ticket 1: Diagnosed overly broad BLOCK_MGMT deny range; corrected to 172.16.1.0/24 only
- [ ] Ticket 2: Diagnosed LEAK_FROM_L1 typo (10.0.0.50/32); corrected to 10.0.0.5/32; XR1 loopbacks visible on R3
- [ ] Ticket 3: Diagnosed missing OSPF_TO_ISIS permit 30 for external type-2; added sequence; all 5 redistributed prefixes visible on R3

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
