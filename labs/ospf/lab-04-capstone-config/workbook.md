# Lab 04: OSPF Full Protocol Mastery — Capstone I

> **Platform Mix Notice (XR-mixed capstone):** R2 (ABR) and R3 (triple ABR +
> ASBR) run **IOS XRv (light, 6.1.x)**; R1, R4, R5, R6 remain IOSv. This
> retrofit exposes you to XR's per-area OSPF stanza, mandatory route-policies
> for redistribution, and the OSPFv3 address-family model — production SP
> reality without changing exam coverage. IOS commands shown throughout still
> apply on R1/R4/R5/R6; for the XR equivalents on R2 and R3, see
> [Appendix B: XR-side Command Reference](#appendix-b-xr-side-command-reference).
> Status: configs are syntactically translated and need EVE-NG verification.

**Exam:** 300-510 SPRI  
**Chapter:** OSPF  
**Difficulty:** Advanced  
**Estimated Time:** 120 minutes  
**Type:** Capstone I — Configuration

---

## 1. Lab Overview

This capstone integrates every OSPF technique from labs 01–03 into a single build-from-scratch
exercise. You are given a clean network — interfaces are up and IP addresses are configured.
Your task is to design and configure the complete dual-stack (OSPFv2 + OSPFv3) multiarea OSPF
domain, choosing the correct area types, redistribution strategy, and summarization parameters.

No step-by-step tasks are provided. Use the topology, addressing table, and objectives below
to guide your work.

---

## 2. Topology

```
              ┌──────────────────────────────────────────────────┐
              │                   Area 0 (Backbone)              │
              │                                                   │
  ┌────────┐  │  ┌────────┐  10.1.23.0/24  ┌────────────────┐  │
  │   R1   ├──┼──┤   R2   ├───────────────┤       R3       ├──┼──┐
  │Area 1  │  │  │ABR 0/1 │               │ABR 0/2/3 ASBR  │  │  │
  └────────┘  │  └────────┘               └───────┬──┬─────┘  │  │
    Area 1    │      ABR                          │  │         │  │
10.1.12.0/24  └──────────────────────────────────┼──┼─────────┘  │
              Area 1 summary:                     │  │            │
              172.16.0.0/21 (IPv4)     10.1.34.0 │  │ 10.1.35.0  │
              2001:db8:1::/48 (IPv6)         /24  │  │    /24     │
                                              ▼   │  ▼           │
                                         ┌──────┐ │ ┌──────┐    │
                                         │  R4  │ │ │  R5  │    │
                                         │Area 2│ │ │Area 3│    │
                                         │Totally│ │ │ NSSA │    │
                                         │Stubby │ │ │+ASBR │    │
                                         └──────┘ │ └──────┘    │
                                         Area 2   │  Area 3      │
                                                  │              │
                               10.1.36.0/24       │              │
                                         ┌──────┐ │              │
                                         │  R6  ├─┘              │
                                         │Ext AS│                │
                                         └──────┘                │
External: 192.168.66.0/24 → redistributed via R3 (ASBR)
          summarized to 192.168.0.0/16 (IPv4 Type-5)
          2001:db8:66::/48 summary (IPv6)
```

---

## 3. Addressing Table

### IPv4

| Device | Interface  | Address         | Area / Role          |
|--------|-----------|-----------------|----------------------|
| R1     | Lo0       | 10.0.0.1/32     | Area 1               |
| R1     | Lo1       | 172.16.1.1/24   | Area 1               |
| R1     | Lo2       | 172.16.2.1/24   | Area 1               |
| R1     | Lo3       | 172.16.3.1/24   | Area 1               |
| R1     | Gi0/0     | 10.1.12.1/24    | Area 1               |
| R2     | Lo0       | 10.0.0.2/32     | Area 0               |
| R2     | Gi0/0     | 10.1.12.2/24    | Area 1 (ABR side)    |
| R2     | Gi0/1     | 10.1.23.2/24    | Area 0               |
| R3     | Lo0       | 10.0.0.3/32     | Area 0               |
| R3     | Gi0/0     | 10.1.23.3/24    | Area 0               |
| R3     | Gi0/1     | 10.1.34.3/24    | Area 2 (ABR side)    |
| R3     | Gi0/2     | 10.1.35.3/24    | Area 3 (ABR side)    |
| R3     | Gi0/3     | 10.1.36.3/24    | External (no OSPF)   |
| R4     | Lo0       | 10.0.0.4/32     | Area 2               |
| R4     | Lo1       | 172.16.4.1/24   | Area 2               |
| R4     | Gi0/0     | 10.1.34.4/24    | Area 2               |
| R5     | Lo0       | 10.0.0.5/32     | Area 3               |
| R5     | Lo1       | 172.16.5.1/24   | Area 3               |
| R5     | Lo2       | 192.168.55.1/24 | External (NSSA ASBR) |
| R5     | Gi0/0     | 10.1.35.5/24    | Area 3               |
| R6     | Lo0       | 10.0.0.6/32     | External AS          |
| R6     | Lo1       | 192.168.66.1/24 | External AS          |
| R6     | Gi0/0     | 10.1.36.6/24    | External AS          |

### IPv6

| Device | Interface  | Address              | Area / Role          |
|--------|-----------|----------------------|----------------------|
| R1     | Lo0       | 2001:db8::1/128      | Area 1               |
| R1     | Lo1       | 2001:db8:1::1/64     | Area 1               |
| R1     | Lo2       | 2001:db8:1:2::1/64   | Area 1               |
| R1     | Lo3       | 2001:db8:1:3::1/64   | Area 1               |
| R1     | Gi0/0     | 2001:db8:12::1/64    | Area 1               |
| R2     | Lo0       | 2001:db8::2/128      | Area 0               |
| R2     | Gi0/0     | 2001:db8:12::2/64    | Area 1 (ABR side)    |
| R2     | Gi0/1     | 2001:db8:23::2/64    | Area 0               |
| R3     | Lo0       | 2001:db8::3/128      | Area 0               |
| R3     | Gi0/0     | 2001:db8:23::3/64    | Area 0               |
| R3     | Gi0/1     | 2001:db8:34::3/64    | Area 2 (ABR side)    |
| R3     | Gi0/2     | 2001:db8:35::3/64    | Area 3 (ABR side)    |
| R3     | Gi0/3     | 2001:db8:36::3/64    | External (no OSPF)   |
| R4     | Lo0       | 2001:db8::4/128      | Area 2               |
| R4     | Lo1       | 2001:db8:4::1/64     | Area 2               |
| R4     | Gi0/0     | 2001:db8:34::4/64    | Area 2               |
| R5     | Lo0       | 2001:db8::5/128      | Area 3               |
| R5     | Lo1       | 2001:db8:5::1/64     | Area 3               |
| R5     | Gi0/0     | 2001:db8:35::5/64    | Area 3               |
| R6     | Lo0       | 2001:db8::6/128      | External AS          |
| R6     | Lo1       | 2001:db8:66::1/64    | External AS          |
| R6     | Gi0/0     | 2001:db8:36::6/64    | External AS          |

---

## 4. Prerequisites

- EVE-NG lab imported and all nodes started
- Initial configs loaded via `setup_lab.py`
- Connectivity verified: ping each adjacent interface before starting

```
R1# ping 10.1.12.2
R2# ping 10.1.23.3
R3# ping 10.1.34.4
R3# ping 10.1.35.5
R3# ping 10.1.36.6
```

---

## 5. Lab Challenge: Full Protocol Mastery

You have a clean network — interfaces are up and IP addresses are configured.
Build the complete dual-stack multiarea OSPF domain from scratch.

**Design requirements:**

- Run OSPF process 1 for OSPFv2 (IPv4) and OSPFv3 process 1 for OSPFv3 (IPv6)
- Use each router's Lo0 address (e.g., `10.0.0.1`) as its OSPF router-id
- Use the same router-id value for both OSPFv2 and OSPFv3

**Area assignments:**

- Area 1: R1 (all interfaces), R2 Gi0/0, R2 Lo0 in Area 0
- Area 0: R2 Gi0/1, R3 Lo0, R3 Gi0/0
- Area 2: R3 Gi0/1, R4 (all interfaces) — configure as **totally stubby**
- Area 3: R3 Gi0/2, R5 Lo0, Lo1, Gi0/0 — configure as **NSSA**
- R3 Gi0/3 is external-facing — do NOT place it in OSPF

**Redistribution (R3 as ASBR):**

- Add static routes on R3: `192.168.66.0/24` and `2001:db8:66::/64` via R6 (10.1.36.6 / 2001:db8:36::6)
- Redistribute static routes into OSPFv2 and OSPFv3
- Apply external IPv4 summary: `192.168.0.0/16` (collapses the /24 into one Type-5 LSA)
- Apply external IPv6 summary: `2001:db8:66::/48`

**NSSA redistribution (R5 as NSSA ASBR):**

- Redistribute R5's Lo2 (192.168.55.0/24) into OSPF as NSSA external
- Use a route-map to redistribute Lo2 only — not Lo0 or Lo1
- R5 Lo2 has no IPv6 address; no IPv6 redistribution required from R5

**Inter-area summarization (R2 as ABR):**

- IPv4: summarize Area 1 routes with `area 1 range 172.16.0.0 255.255.248.0`
- IPv6: summarize Area 1 routes with `area 1 range 2001:db8:1::/48` (under OSPFv3 address-family)

**Verification objectives:**

1. All OSPF neighbors reach FULL state across all areas
2. R1 receives a single `172.16.0.0/21` Type-3 LSA (not three individual /24s)
3. R4's routing table contains only: intra-area routes (Area 2) + one default route; no specific inter-area routes
4. R5's `192.168.55.0/24` appears as a Type-5 LSA on R1, R2, and R4 (translated by R3 from Type-7)
5. R1 can ping R6's Lo1 (`192.168.66.1`) and the IPv6 equivalent (`2001:db8:66::1`)
6. `show ip ospf database` on R3 shows the Null0 discard route for `192.168.0.0/16`

---

## 6. Blueprint Coverage

| Blueprint Ref | Topic | Where Tested |
|---------------|-------|--------------|
| 1.1 | OSPF vs IS-IS design comparison | Area-type selection rationale (totally stubby vs NSSA vs standard) |
| 1.2 | OSPF multiarea operations | Area 0/1/2/3 adjacencies, ABR/ASBR roles |
| 1.2.a | Route advertisement | Type-1/2/3/5/7 LSA propagation and filtering (totally stubby, NSSA) |
| 1.2.b | Summarization | Inter-area (R2 ABR, IPv4+IPv6) and external (R3 ASBR, IPv4+IPv6) |

---

## 7. Verification

### 7.1 OSPF Neighbor State

```
R1# show ip ospf neighbor
R2# show ip ospf neighbor
R3# show ip ospf neighbor
```

Expected: all adjacencies in FULL state. R2 shows neighbors on Gi0/0 (R1, Area 1) and Gi0/1 (R3, Area 0). R3 shows three neighbors: R2 (Area 0), R4 (Area 2), R5 (Area 3).

```
R2# show ospfv3 neighbor
R3# show ospfv3 neighbor
```

### 7.2 Area 1 Summarization

```
R3# show ip route 172.16.0.0 255.255.248.0
```

Expected: `O IA 172.16.0.0/21 [110/x] via 10.1.23.2` — single summary, not three /24s.

```
R3# show ipv6 route 2001:db8:1::/48
```

Expected: OSPFv3 inter-area route for the /48 summary.

```
R2# show ip ospf database summary
```

Expected: one Type-3 LSA for 172.16.0.0/21 (not three separate /24 entries for 172.16.1-3.0).

### 7.3 Area 2 Totally Stubby

```
R4# show ip route
```

Expected: intra-area routes only (10.0.0.4/32, 172.16.4.0/24, 10.1.34.0/24) plus one default route `O*IA 0.0.0.0/0`. No 172.16.x.0/24 Type-3 routes, no external routes.

```
R4# show ip ospf database
```

Expected: only Type-1 and Type-2 LSAs within Area 2, plus a single Type-3 LSA for the default route from R3.

### 7.4 NSSA — R5 Redistribution and Type-7 Translation

```
R5# show ip ospf database nssa-external
```

Expected: Type-7 LSA for 192.168.55.0/24 (forwarding address = R5's connected IP).

```
R1# show ip route 192.168.55.0
```

Expected: `O E2 192.168.55.0/24` — Type-5 LSA generated by R3 from R5's Type-7.

```
R3# show ip ospf database external
```

Expected: two Type-5 LSAs — 192.168.0.0/16 (summarized from R6, with Null0 discard) and 192.168.55.0/24 (translated from R5's Type-7).

### 7.5 External Redistribution Summary

```
R1# show ip route 192.168.0.0 255.255.0.0
```

Expected: `O E2 192.168.0.0/16` — the /24 collapsed into the /16 summary.

```
R3# show ip route 192.168.0.0 255.255.0.0
```

Expected: `O 192.168.0.0/16 is a summary, Null0` — discard route installed by OSPF to prevent loops.

```
R1# ping 192.168.66.1 source 10.0.0.1
R1# ping 2001:db8:66::1 source 2001:db8::1
```

Expected: success.

### 7.6 OSPFv3 Dual-Stack

```
R2# show ospfv3 database
R3# show ospfv3 database
```

Expected: LSA entries for IPv6 prefixes in each area. Verify the Area 3 nssa setting:

```
R5# show ospfv3 1 ipv6
```

Expected: shows `Area 3` configured as NSSA.

---

## 8. Solutions

<details>
<summary>R1 — Area 1 Internal Router</summary>

```
hostname R1
!
no ip domain-lookup
ipv6 unicast-routing
!
interface Loopback0
 ip address 10.0.0.1 255.255.255.255
 ipv6 address 2001:DB8::1/128
 ospfv3 1 ipv6 area 1
!
interface Loopback1
 ip address 172.16.1.1 255.255.255.0
 ipv6 address 2001:DB8:1::1/64
 ospfv3 1 ipv6 area 1
!
interface Loopback2
 ip address 172.16.2.1 255.255.255.0
 ipv6 address 2001:DB8:1:2::1/64
 ospfv3 1 ipv6 area 1
!
interface Loopback3
 ip address 172.16.3.1 255.255.255.0
 ipv6 address 2001:DB8:1:3::1/64
 ospfv3 1 ipv6 area 1
!
interface GigabitEthernet0/0
 ip address 10.1.12.1 255.255.255.0
 ipv6 address 2001:DB8:12::1/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 1
!
router ospf 1
 router-id 10.0.0.1
 network 10.0.0.1 0.0.0.0 area 1
 network 10.1.12.1 0.0.0.0 area 1
 network 172.16.1.1 0.0.0.0 area 1
 network 172.16.2.1 0.0.0.0 area 1
 network 172.16.3.1 0.0.0.0 area 1
!
router ospfv3 1
 router-id 10.0.0.1
 !
 address-family ipv6 unicast
 exit-address-family
```

</details>

<details>
<summary>R2 — ABR (Area 0 / Area 1) with Inter-Area Summarization</summary>

```
hostname R2
!
no ip domain-lookup
ipv6 unicast-routing
!
interface Loopback0
 ip address 10.0.0.2 255.255.255.255
 ipv6 address 2001:DB8::2/128
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/0
 ip address 10.1.12.2 255.255.255.0
 ipv6 address 2001:DB8:12::2/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 1
!
interface GigabitEthernet0/1
 ip address 10.1.23.2 255.255.255.0
 ipv6 address 2001:DB8:23::2/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 0
!
router ospf 1
 router-id 10.0.0.2
 network 10.0.0.2 0.0.0.0 area 0
 network 10.1.12.2 0.0.0.0 area 1
 network 10.1.23.2 0.0.0.0 area 0
 area 1 range 172.16.0.0 255.255.248.0
!
router ospfv3 1
 router-id 10.0.0.2
 !
 address-family ipv6 unicast
  area 1 range 2001:DB8:1::/48
 exit-address-family
```

</details>

<details>
<summary>R3 — Triple ABR + ASBR (Area 0 / Area 2 / Area 3, External Redistribution)</summary>

```
hostname R3
!
no ip domain-lookup
ipv6 unicast-routing
!
ip route 192.168.66.0 255.255.255.0 10.1.36.6
ipv6 route 2001:DB8:66::/64 2001:DB8:36::6
!
interface Loopback0
 ip address 10.0.0.3 255.255.255.255
 ipv6 address 2001:DB8::3/128
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/0
 ip address 10.1.23.3 255.255.255.0
 ipv6 address 2001:DB8:23::3/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/1
 ip address 10.1.34.3 255.255.255.0
 ipv6 address 2001:DB8:34::3/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 2
!
interface GigabitEthernet0/2
 ip address 10.1.35.3 255.255.255.0
 ipv6 address 2001:DB8:35::3/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 3
!
interface GigabitEthernet0/3
 ip address 10.1.36.3 255.255.255.0
 ipv6 address 2001:DB8:36::3/64
 duplex full
 no shutdown
!
router ospf 1
 router-id 10.0.0.3
 network 10.0.0.3 0.0.0.0 area 0
 network 10.1.23.3 0.0.0.0 area 0
 network 10.1.34.3 0.0.0.0 area 2
 network 10.1.35.3 0.0.0.0 area 3
 area 2 stub no-summary
 area 3 nssa
 redistribute static subnets
 summary-address 192.168.0.0 255.255.0.0
!
router ospfv3 1
 router-id 10.0.0.3
 !
 address-family ipv6 unicast
  area 2 stub no-summary
  area 3 nssa
  redistribute static
  summary-prefix 2001:DB8:66::/48
 exit-address-family
```

</details>

<details>
<summary>R4 — Area 2 Internal Router (Totally Stubby)</summary>

```
hostname R4
!
no ip domain-lookup
ipv6 unicast-routing
!
interface Loopback0
 ip address 10.0.0.4 255.255.255.255
 ipv6 address 2001:DB8::4/128
 ospfv3 1 ipv6 area 2
!
interface Loopback1
 ip address 172.16.4.1 255.255.255.0
 ipv6 address 2001:DB8:4::1/64
 ospfv3 1 ipv6 area 2
!
interface GigabitEthernet0/0
 ip address 10.1.34.4 255.255.255.0
 ipv6 address 2001:DB8:34::4/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 2
!
router ospf 1
 router-id 10.0.0.4
 network 10.0.0.4 0.0.0.0 area 2
 network 172.16.4.1 0.0.0.0 area 2
 network 10.1.34.4 0.0.0.0 area 2
 area 2 stub
!
router ospfv3 1
 router-id 10.0.0.4
 !
 address-family ipv6 unicast
  area 2 stub
 exit-address-family
```

</details>

<details>
<summary>R5 — Area 3 NSSA Internal Router + ASBR</summary>

```
hostname R5
!
no ip domain-lookup
ipv6 unicast-routing
!
ip prefix-list NSSA_EXTERNAL_PREFIX seq 5 permit 192.168.55.0/24
!
route-map NSSA_EXTERNAL permit 10
 match ip address prefix-list NSSA_EXTERNAL_PREFIX
!
interface Loopback0
 ip address 10.0.0.5 255.255.255.255
 ipv6 address 2001:DB8::5/128
 ospfv3 1 ipv6 area 3
!
interface Loopback1
 ip address 172.16.5.1 255.255.255.0
 ipv6 address 2001:DB8:5::1/64
 ospfv3 1 ipv6 area 3
!
interface Loopback2
 ip address 192.168.55.1 255.255.255.0
!
interface GigabitEthernet0/0
 ip address 10.1.35.5 255.255.255.0
 ipv6 address 2001:DB8:35::5/64
 duplex full
 no shutdown
 ospfv3 1 ipv6 area 3
!
router ospf 1
 router-id 10.0.0.5
 network 10.0.0.5 0.0.0.0 area 3
 network 172.16.5.1 0.0.0.0 area 3
 network 10.1.35.5 0.0.0.0 area 3
 area 3 nssa
 redistribute connected subnets route-map NSSA_EXTERNAL
!
router ospfv3 1
 router-id 10.0.0.5
 !
 address-family ipv6 unicast
  area 3 nssa
 exit-address-family
```

</details>

<details>
<summary>R6 — External AS Router (No OSPF)</summary>

```
hostname R6
!
no ip domain-lookup
ipv6 unicast-routing
!
ip route 0.0.0.0 0.0.0.0 10.1.36.3
ipv6 route ::/0 2001:DB8:36::3
!
interface Loopback0
 ip address 10.0.0.6 255.255.255.255
 ipv6 address 2001:DB8::6/128
!
interface Loopback1
 ip address 192.168.66.1 255.255.255.0
 ipv6 address 2001:DB8:66::1/64
!
interface GigabitEthernet0/0
 ip address 10.1.36.6 255.255.255.0
 ipv6 address 2001:DB8:36::6/64
 duplex full
 no shutdown
```

</details>

---

## 9. Lab Teardown

Save configurations before shutdown to preserve your work:

```
R1# copy running-config startup-config
R2# copy running-config startup-config
R3# copy running-config startup-config
R4# copy running-config startup-config
R5# copy running-config startup-config
```

In EVE-NG: stop nodes, then export the lab to save all node states.

---

## 10. Troubleshooting Scenarios

Load a fault scenario, diagnose and resolve without looking at the solution.
Scripts are in `scripts/fault-injection/`.

### Scenario 1 — Area 2 receives inter-area routes (totally stubby misconfiguration)

```bash
python scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
```

**Symptom:** R4 receives multiple Type-3 inter-area LSAs (172.16.x.x, external summaries)
instead of only a single default route.

**Hint:** Verify the `area 2 stub` configuration on R3 and compare it to R4.

**Restore:**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

### Scenario 2 — R5's 192.168.55.0/24 not visible beyond Area 3 (NSSA translation disabled)

```bash
python scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
```

**Symptom:** `show ip route 192.168.55.0` on R1, R2, and R4 returns no match.
R5 shows the Type-7 LSA locally but R3 does not translate it to Type-5.

**Hint:** Check R3's Area 3 NSSA configuration. Which command on an NSSA ABR controls
whether Type-7 LSAs are translated to Type-5?

**Restore:**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

### Scenario 3 — Three /24s from Area 1 instead of single /21 summary

```bash
python scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>
```

**Symptom:** `show ip route` on R3, R4, and R5 shows three separate routes
(172.16.1.0/24, 172.16.2.0/24, 172.16.3.0/24) instead of 172.16.0.0/21.

**Hint:** Check R2's OSPF ABR configuration for Area 1 route aggregation.

**Restore:**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

## 11. Further Reading

- RFC 2328 — OSPF Version 2 (Sections 12–14: LSA types and flooding)
- RFC 3101 — OSPF Not-So-Stubby Area (NSSA)
- RFC 5340 — OSPF for IPv6 (OSPFv3)
- Cisco IOS documentation: `area range`, `summary-address`, OSPF redistribution
- CCNP SPRI Official Cert Guide — Chapter 2 (OSPF Multiarea and Summarization)

---

## Appendix B: XR-side Command Reference

R2 and R3 run **IOS XRv (light)** in this capstone. The IOS show/config
commands referenced earlier in the workbook do not exist on XR — use the
equivalents below when working on R2 or R3. R1, R4, R5, R6 are still IOSv;
their commands are unchanged.

### Why XR here

OSPF is platform-agnostic in the 300-510 blueprint, but XR is the production
SP edge platform and has a meaningfully different OSPF config model: per-area
stanza (instead of `network` statements), mandatory route-policies for
redistribution, and a separate `router ospfv3` AF block for OSPFv3. See
`memory/xr-coverage-policy.md` §2 (XR-mixed posture).

### XR commit model (one-time orientation)

XR uses a **candidate / running** config split. Changes you type are staged
and do not take effect until you `commit`. `abort` discards the candidate;
`show configuration` displays the diff. `!` is a comment in XR (not a
sub-mode exit) — use `exit` or `root`.

### IOS → XR command equivalents (R2 / R3 only)

| Purpose | IOS (R1, R4, R5, R6) | IOS XR (R2, R3) |
|---|---|---|
| Show interface IPv4 | `show ip interface brief` | `show ipv4 interface brief` |
| Show interface IPv6 | `show ipv6 interface brief` | `show ipv6 interface brief` |
| OSPF neighbors | `show ip ospf neighbor` | `show ospf neighbor` |
| OSPFv3 neighbors | `show ospfv3 neighbor` | `show ospfv3 neighbor` |
| OSPF interface | `show ip ospf interface GigE0/0` | `show ospf interface GigE0/0/0/0` |
| OSPF database | `show ip ospf database` | `show ospf database` |
| OSPF DB summary (Type 3) | `show ip ospf database summary` | `show ospf database summary` |
| OSPF DB external (Type 5) | `show ip ospf database external` | `show ospf database external` |
| OSPF DB NSSA (Type 7) | `show ip ospf database nssa-external` | `show ospf database nssa-external` |
| Route table | `show ip route ospf` | `show route ospf` |
| Inspect route-policy | (n/a, uses route-maps: `show route-map`) | `show route-policy REDIST_STATIC` |
| Save running config | `write memory` | `commit` (auto-persists) |

### IOS → XR config-block equivalents

| Purpose | IOS line | XR equivalent |
|---|---|---|
| Per-interface area assignment | `ip ospf 1 area 0` (under int) | `area 0\n interface Gig0/0/0/X` (under `router ospf 1`) |
| Inter-area summary | `area 1 range A.B.C.D MASK` | `area 1\n range A.B.C.D/PFX` |
| External summary | `summary-address A.B.C.D MASK` | `summary-prefix A.B.C.D/PFX` |
| Totally stubby area | `area N stub no-summary` | `area N\n stub no-summary` |
| NSSA area | `area N nssa` | `area N\n nssa` |
| Redistribute static | `redistribute static subnets` | `redistribute static route-policy POLICY_NAME` (policy MANDATORY) |
| Distribute-list out | `distribute-list prefix LIST out static` | (use route-policy `if destination in SET then drop endif pass`) |
| Hello/Dead per int | `ip ospf hello-interval N` (under int) | `interface GigE0/0/0/X\n  hello-interval N` (under area) |
| OSPFv3 area | (per int: `ospfv3 1 ipv6 area 0`) | `router ospfv3 1\n area 0\n  interface GigE0/0/0/X` |

### Verification flow on R2 / R3 (XR-side)

```
RP/0/0/CPU0:R2# show ospf neighbor
RP/0/0/CPU0:R2# show ospfv3 neighbor
RP/0/0/CPU0:R2# show ospf database summary
RP/0/0/CPU0:R2# show route ospf

RP/0/0/CPU0:R3# show ospf neighbor
RP/0/0/CPU0:R3# show ospf database external
RP/0/0/CPU0:R3# show ospf interface GigabitEthernet0/0/0/1
RP/0/0/CPU0:R3# show route-policy REDIST_STATIC
```

### Known gaps

- This appendix gives commands, not full per-task XR rewrites. Workbook
  sections that print expected IOS output are illustrative — translate the
  command per the table and the show fields will be very close (XR may add
  extra columns).
- XR does not support `network` statements under `router ospf`; if a fault
  ticket asks you to "fix the OSPF network statement," the corresponding XR
  fix is to add an `interface GigE0/0/0/X` line under the appropriate `area`.
- Configs are syntactically translated from the IOS sibling solution but
  have **not yet been verified in EVE-NG**. Expect minor adjustments after
  first boot.
