# Lab 05: OSPF Comprehensive Troubleshooting — Capstone II

> **Platform Mix Notice (XR-mixed capstone):** R2 (ABR) and R3 (triple ABR +
> ASBR) run **IOS XRv (light, 6.1.x)**; R1, R4, R5, R6 remain IOSv. Two of the
> injected faults live on the XR side and require XR-syntax fixes:
>  - **R2 fault:** wrong Type 3 summary mask (`range 172.16.0.0/23` — should be
>    `/21` to cover the full Area 1 prefix set).
>  - **R3 fault A:** OSPF `dead-interval 80` on Area 2 link — Hello/Dead
>    mismatch with R4. **R3 fault B:** REDIST_STATIC route-policy drops the
>    192.168.66.0/24 external — Type 5 LSA missing.
>
> See [Appendix B: XR-side Command Reference](#appendix-b-xr-side-command-reference)
> for command equivalents. The IOS troubleshooting workflow described in this
> workbook still applies on R1/R4/R5/R6; on R2/R3 you must use the XR
> equivalents. Status: configs are syntactically translated and need EVE-NG
> verification.

**Exam:** 300-510 SPRI  
**Chapter:** OSPF  
**Difficulty:** Advanced  
**Estimated Time:** 120 minutes  
**Type:** Capstone II — Troubleshooting

---

## 1. Lab Overview

You inherit a dual-stack multiarea OSPF domain that was recently modified by a junior engineer.
The network has degraded in several ways that the engineer cannot explain. Your task is to
diagnose and repair all faults — without being told how many there are or where they live.

Five concurrent faults are present. They span different devices and different fault classes:
adjacency parameters, LSA propagation control, summarization accuracy, IPv6 parity, and
redistribution filtering. Some faults are independent; others share a device.

**Approach:** Establish a baseline first. Know what the correctly functioning topology looks
like before issuing any `no` commands. Document each fault before fixing it.

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
NSSA:     192.168.55.0/24 → redistributed via R5 (NSSA ASBR)
          Type-7 LSA inside Area 3, translated to Type-5 by R3
```

---

## 3. Addressing Table

### IPv4

| Device | Interface | Address           | Area / Role          |
|--------|-----------|-------------------|----------------------|
| R1     | Lo0       | 10.0.0.1/32       | Area 1               |
| R1     | Lo1       | 172.16.1.1/24     | Area 1               |
| R1     | Lo2       | 172.16.2.1/24     | Area 1               |
| R1     | Lo3       | 172.16.3.1/24     | Area 1               |
| R1     | Gi0/0     | 10.1.12.1/24      | Area 1               |
| R2     | Lo0       | 10.0.0.2/32       | Area 0               |
| R2     | Gi0/0     | 10.1.12.2/24      | Area 1 (ABR side)    |
| R2     | Gi0/1     | 10.1.23.2/24      | Area 0               |
| R3     | Lo0       | 10.0.0.3/32       | Area 0               |
| R3     | Gi0/0     | 10.1.23.3/24      | Area 0               |
| R3     | Gi0/1     | 10.1.34.3/24      | Area 2 (ABR side)    |
| R3     | Gi0/2     | 10.1.35.3/24      | Area 3 (ABR side)    |
| R3     | Gi0/3     | 10.1.36.3/24      | External (no OSPF)   |
| R4     | Lo0       | 10.0.0.4/32       | Area 2               |
| R4     | Lo1       | 172.16.4.1/24     | Area 2               |
| R4     | Gi0/0     | 10.1.34.4/24      | Area 2               |
| R5     | Lo0       | 10.0.0.5/32       | Area 3               |
| R5     | Lo1       | 172.16.5.1/24     | Area 3               |
| R5     | Lo2       | 192.168.55.1/24   | External (NSSA ASBR) |
| R5     | Gi0/0     | 10.1.35.5/24      | Area 3               |
| R6     | Lo0       | 10.0.0.6/32       | External AS          |
| R6     | Lo1       | 192.168.66.1/24   | External AS          |
| R6     | Gi0/0     | 10.1.36.6/24      | External AS          |

### IPv6

| Device | Interface | Address                | Area / Role          |
|--------|-----------|------------------------|----------------------|
| R1     | Lo0       | 2001:db8::1/128        | Area 1               |
| R1     | Lo1       | 2001:db8:1::1/64       | Area 1               |
| R1     | Lo2       | 2001:db8:1:2::1/64     | Area 1               |
| R1     | Lo3       | 2001:db8:1:3::1/64     | Area 1               |
| R1     | Gi0/0     | 2001:db8:12::1/64      | Area 1               |
| R2     | Lo0       | 2001:db8::2/128        | Area 0               |
| R2     | Gi0/0     | 2001:db8:12::2/64      | Area 1 (ABR side)    |
| R2     | Gi0/1     | 2001:db8:23::2/64      | Area 0               |
| R3     | Lo0       | 2001:db8::3/128        | Area 0               |
| R3     | Gi0/0     | 2001:db8:23::3/64      | Area 0               |
| R3     | Gi0/1     | 2001:db8:34::3/64      | Area 2 (ABR side)    |
| R3     | Gi0/2     | 2001:db8:35::3/64      | Area 3 (ABR side)    |
| R3     | Gi0/3     | 2001:db8:36::3/64      | External (no OSPF)   |
| R4     | Lo0       | 2001:db8::4/128        | Area 2               |
| R4     | Lo1       | 2001:db8:4::1/64       | Area 2               |
| R4     | Gi0/0     | 2001:db8:34::4/64      | Area 2               |
| R5     | Lo0       | 2001:db8::5/128        | Area 3               |
| R5     | Lo1       | 2001:db8:5::1/64       | Area 3               |
| R5     | Gi0/0     | 2001:db8:35::5/64      | Area 3               |
| R6     | Lo0       | 2001:db8::6/128        | External AS          |
| R6     | Lo1       | 2001:db8:66::1/64      | External AS          |
| R6     | Gi0/0     | 2001:db8:36::6/64      | External AS          |

---

## 4. Prerequisites

- EVE-NG lab imported and all nodes started
- Pre-broken configs loaded via `setup_lab.py`
- Layer 2 connectivity verified: ping each adjacent interface pair before starting

```
R1# ping 10.1.12.2
R2# ping 10.1.23.3
R3# ping 10.1.34.4
R3# ping 10.1.35.5
R3# ping 10.1.36.6
```

All pings should succeed — the faults are in the OSPF control plane and redistribution policy,
not in IP addressing or interface state.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

The network is pre-broken. Your job is to find and fix every fault.

**You are NOT told how many faults exist or which devices they are on.**

Treat this as a real incident. Open a mental (or written) ticket for each symptom you observe.
Isolate root causes before applying fixes. Verify each fix before moving on.

**End-state objectives — achieve all of the following:**

1. All OSPFv2 neighbors reach FULL state across all areas
2. All OSPFv3 neighbors reach FULL state across all areas
3. R4's routing table contains only intra-area routes + one default route (no specific inter-area or external routes)
4. R3's routing table shows `172.16.0.0/21` as a single inter-area summary (not individual /24s)
5. R5's `192.168.55.0/24` is visible as a Type-5 LSA on R1 and R2 (translated from Type-7 at R3)
6. R1 can ping `192.168.66.1` and `2001:db8:66::1` (R6 Loopback1) via IPv4 and IPv6
7. R1 can ping `2001:db8:5::1` (R5 Lo1) via IPv6

**Recommended diagnostic commands:**

```
show ip ospf neighbor
show ospfv3 neighbor
show ip route
show ipv6 route
show ip ospf database
show ospfv3 database
show ip ospf database nssa-external
show ip ospf database external
show ip ospf database summary
show ospfv3 database inter-prefix
show ip ospf interface <intf>
show ip prefix-list
show route-map
show ip ospf redistribute
debug ip ospf adj
```

---

## 6. Blueprint Coverage

| Blueprint Ref | Topic | Fault Class Exercised |
|---------------|-------|-----------------------|
| 1.2 | OSPF multiarea operations | Timer mismatch (adjacency), NSSA ABR translation |
| 1.2.a | Route advertisement | NSSA redistribution origination filtering |
| 1.2.b | Summarization | Wrong range mask, suppress leak |
| 1.1 | IPv6 dual-stack parity | OSPFv3 interface omission |
| 1.2 | Redistribution | Distribute-list filtering external prefix |

---

## 7. Verification

### 7.1 OSPF Neighbor State

```
R3# show ip ospf neighbor
```

Expected: R2 (Area 0, FULL), R4 (Area 2, FULL), R5 (Area 3, FULL)

```
R3# show ospfv3 neighbor
```

Expected: R2 (Area 0, FULL), R4 (Area 2, FULL), R5 (Area 3, FULL)

```
R5# show ip ospf neighbor
R5# show ospfv3 neighbor
```

Expected: R3 in FULL state for both OSPFv2 and OSPFv3.

### 7.2 Area 1 Summarization

```
R3# show ip route 172.16.0.0
```

Expected: `O IA 172.16.0.0/21 [110/x] via 10.1.23.2` — one summary, not three /24s.

```
R2# show ip ospf database summary
```

Expected: one Type-3 LSA for 172.16.0.0/21.

### 7.3 Area 2 Totally Stubby

```
R4# show ip route
```

Expected: only intra-area routes + `O*IA 0.0.0.0/0`. No 172.16.x.0/24 entries, no external routes.

### 7.4 NSSA Type-7 Translation

```
R5# show ip ospf database nssa-external
```

Expected: Type-7 LSA for 192.168.55.0/24.

```
R1# show ip route 192.168.55.0
```

Expected: `O E2 192.168.55.0/24` — Type-5 LSA translated at R3.

### 7.5 External Redistribution (R6 Reachability)

```
R1# show ip route 192.168.66.0
```

Expected: `O E2 192.168.66.0/24` or `O E2 192.168.0.0/16` (summary).

```
R1# ping 192.168.66.1
R1# ping 2001:db8:66::1
```

Both pings should succeed with 5/5 replies.

### 7.6 IPv6 Area 3 Reachability

```
R1# ping 2001:db8:5::1
```

Expected: 5/5 replies from R5 Lo1.

```
R1# show ipv6 route ospf
```

Expected: OSPFv3 inter-area prefix for `2001:db8:5::/64`.

---

## 8. Reference Solutions

<details>
<summary>R1 — Solution Config</summary>

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
<summary>R2 — Solution Config</summary>

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
<summary>R3 — Solution Config</summary>

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
<summary>R4 — Solution Config</summary>

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
<summary>R5 — Solution Config</summary>

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
<summary>R6 — Solution Config</summary>

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

## 9. Fault Tickets

Five tickets are open. Each describes a reported symptom. Resolve all five.

<details>
<summary>Ticket 1 — Area 2 unreachable: R3 cannot reach R4</summary>

**Symptom:** `show ip ospf neighbor` on R3 shows no neighbor on Gi0/1, or R4 is stuck in
INIT/EXSTART. R4's routing table has no inter-area routes — it appears isolated.

**Investigation starting point:**
```
R3# show ip ospf interface GigabitEthernet0/1
R4# show ip ospf interface GigabitEthernet0/0
```
Compare the Dead interval values on each side. They must match for adjacency to form.

**Root cause:** OSPF dead-interval mismatch between R3 Gi0/1 and R4 Gi0/0.

**Fix:**
```
R3(config)# interface GigabitEthernet0/1
R3(config-if)# no ip ospf dead-interval
```

**Verify:**
```
R3# show ip ospf neighbor
```
R4 should reach FULL within one dead-interval cycle after the fix.

</details>

<details>
<summary>Ticket 2 — R5 NSSA external prefix never appears in any router's routing table</summary>

**Symptom:** `192.168.55.0/24` on R5's Lo2 should be redistributed into Area 3 as a Type-7 NSSA
external LSA. But `show ip ospf database nssa-external` on R5 itself shows **no LSA for this prefix**.
The prefix is completely absent — R3, R1, R2, and R4 all return no match for `show ip route 192.168.55.0`.

**Investigation starting point:**

The fact that R5's own LSDB has no Type-7 means the fault is at the redistribution source, not at
the ABR translation stage. Start on R5:
```
R5# show ip ospf database nssa-external
R5# show running-config | section ospf
R5# show ip prefix-list NSSA_EXTERNAL_PREFIX
R5# show route-map NSSA_EXTERNAL
```
Check whether the prefix-list actually matches the Lo2 connected route.

**Root cause:** `ip prefix-list NSSA_EXTERNAL_PREFIX seq 5 permit 192.168.55.0/25` uses a /25 mask.
The connected Lo2 route `192.168.55.0/24` does not match — IOS prefix-list matching requires an
exact length match unless `ge`/`le` qualifiers are present. The route-map denies Lo2, redistribution
is skipped, and no Type-7 LSA is originated at R5.

**Fix:**
```
R5(config)# no ip prefix-list NSSA_EXTERNAL_PREFIX seq 5
R5(config)# ip prefix-list NSSA_EXTERNAL_PREFIX seq 5 permit 192.168.55.0/24
```

**Verify:**
```
R5# show ip ospf database nssa-external
R1# show ip route 192.168.55.0
```
Expected: Type-7 LSA present on R5; `O E2 192.168.55.0/24` on R1 (via Type-5 translated by R3).

</details>

<details>
<summary>Ticket 3 — Area 1 routes leaking as individual /24s instead of /21 summary</summary>

**Symptom:** `show ip route` on R3, R4, or R5 shows three entries for 172.16.x.0/24 subnets
instead of a single `172.16.0.0/21` inter-area summary. R2's LSDB has three Type-3 LSAs for
Area 1 /24 prefixes.

**Investigation starting point:**
```
R2# show ip ospf database summary
R2# show running-config | section ospf
```
Check the `area 1 range` statement. Verify the prefix and mask.

**Root cause:** `area 1 range 172.16.0.0 255.255.254.0` on R2 uses a /23 mask.
172.16.2.0/24 and 172.16.3.0/24 fall outside the /23 boundary and leak as individual LSAs.

**Fix:**
```
R2(config)# router ospf 1
R2(config-router)# area 1 range 172.16.0.0 255.255.248.0
```

**Verify:**
```
R3# show ip route 172.16.0.0
```
Expected: one `O IA 172.16.0.0/21` entry.

</details>

<details>
<summary>Ticket 4 — R5 IPv6 routes missing; IPv4 reachability to R5 works, IPv6 does not</summary>

**Symptom:** `ping 10.0.0.5` from R1 succeeds. `ping 2001:db8::5` from R1 fails. `show ipv6 route ospf`
on R1 shows no prefixes from Area 3. `show ospfv3 neighbor` on R3 shows no entry for R5.

**Investigation starting point:**
```
R5# show ospfv3 interface
R5# show ospfv3 neighbor
```
Compare the interfaces participating in OSPFv3 vs OSPFv2.

**Root cause:** `ospfv3 1 ipv6 area 3` is missing from R5's GigabitEthernet0/0. OSPFv3 has
no adjacency because R5's transit interface is not in the process.

**Fix:**
```
R5(config)# interface GigabitEthernet0/0
R5(config-if)# ospfv3 1 ipv6 area 3
```

**Verify:**
```
R5# show ospfv3 neighbor
R1# ping 2001:db8:5::1
```

</details>

<details>
<summary>Ticket 5 — R6 Lo1 (192.168.66.1) unreachable from all OSPF routers</summary>

**Symptom:** `show ip route 192.168.66.0` on R1 returns no match. `show ip ospf database external`
on R1 shows no Type-5 LSA for 192.168.66.x or 192.168.0.0/16. But `show ip route static` on R3
confirms the static route to 192.168.66.0/24 via R6 is present.

**Investigation starting point:**
```
R3# show ip ospf redistribute
R3# show ip prefix-list
R3# show running-config | section distribute-list
```
A prefix-list or distribute-list may be filtering the route during redistribution.

**Root cause:** `distribute-list prefix BLOCK_EXT out static` on R3 drops 192.168.66.0/24
before it enters the OSPF LSDB. The static route exists at the IP layer but is suppressed
at the OSPF redistribution point.

**Fix:**
```
R3(config)# router ospf 1
R3(config-router)# no distribute-list prefix BLOCK_EXT out static
R3(config-router)# exit
R3(config)# no ip prefix-list BLOCK_EXT
```

**Verify:**
```
R1# show ip ospf database external
R1# ping 192.168.66.1
R1# ping 2001:db8:66::1
```

</details>

---

## 10. Grading Criteria

| Check | Points |
|-------|--------|
| All OSPFv2 adjacencies FULL (R1-R2, R2-R3, R3-R4, R3-R5) | 20 |
| All OSPFv3 adjacencies FULL (same pairs) | 20 |
| `172.16.0.0/21` appears as single summary on R3 | 15 |
| `192.168.55.0/24` Type-5 LSA visible on R1 | 15 |
| R1 ping to 192.168.66.1 succeeds | 15 |
| R1 ping to 2001:db8:5::1 succeeds | 15 |
| **Total** | **100** |

---

## 11. Key Takeaways

- **Dead-interval mismatches** are silent until the adjacency drops — Hellos still transmit,
  but each side counts down its own timer independently.
- **NSSA prefix-list filtering at the ASBR** blocks Type-7 LSA generation at the source; if no
  Type-7 is originated, no Type-5 translation is possible anywhere — `show ip ospf database
  nssa-external` on the ASBR itself is always the first diagnostic step.
- **`area N range`** mask errors create partial summaries — subnets outside the mask boundary
  leak individually, and the summary covers only the correct portion.
- **OSPFv3 interface commands** are required per-interface; enabling `router ospfv3` globally
  and configuring loopbacks does not automatically enable OSPFv3 on transit interfaces.
- **`distribute-list ... out <protocol>`** filters at the redistribution boundary, not in the
  routing table — the static route still appears in `show ip route`, but the LSA is never generated.

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
