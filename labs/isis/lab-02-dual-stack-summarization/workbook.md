# IS-IS Lab 02: Dual-Stack Summarization and Route Leaking

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

**Exam Objective:** 300-510 — IS-IS: Multi-topology IPv6, route summarization, inter-area route leaking

This lab extends the two-area IS-IS topology from lab-01 by adding full IPv6 dual-stack support using Multi-Topology IS-IS (MT-IPv6). You will configure route summarization on both L1/L2 border routers to aggregate area prefixes and reduce LSDB size, redistribute external prefixes from a non-IS-IS device into the IS-IS domain, and selectively leak specific L2 routes into L1 areas to provide controlled reachability to external destinations.

### IS-IS Multi-Topology IPv6 (MT-IPv6)

Standard IS-IS for IPv6 (single-topology mode) forces IPv4 and IPv6 to share the same SPF tree, meaning both address families must form identical adjacencies. This breaks in mixed environments where some links carry only IPv4. Multi-topology mode assigns independent TLV 222 topology instances to IPv6, giving each address family its own SPF computation and allowing IPv6 to form adjacencies on different interface sets than IPv4.

Enable MT-IPv6 with the `address-family ipv6` block under `router isis`:

```
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
```

Each interface that participates in IPv6 IS-IS must also have `ipv6 router isis CORE` configured.

> **Key distinction:** `multi-topology` under `address-family ipv6` activates TLV 222. Without it, IS-IS uses TLV 236 (single-topology), which requires all IS-IS neighbors to also support IPv6.

### IS-IS Route Summarization

IS-IS summarization is performed at L1/L2 border routers during the L1→L2 route injection process. A summary replaces the injected specific prefixes with a single aggregate in the L2 LSDB, and the border router installs a Null0 discard route for the summary prefix locally.

**IPv4 summarization** uses `summary-address` directly under `router isis`:
```
router isis CORE
 summary-address 172.16.0.0 255.255.248.0
```

**IPv6 summarization** uses `summary-prefix` inside `address-family ipv6` — the keyword is different:
```
router isis CORE
 address-family ipv6
  summary-prefix 2001:DB8::/45
 exit-address-family
```

The `/45` prefix covers `2001:db8:0000::/48` through `2001:db8:0007::/48`. This includes the Lo1 prefixes (`2001:db8:1::/64`, `2001:db8:4::/64`, `2001:db8:5::/64`) while excluding the transit link prefixes (`2001:db8:12::/64`, `2001:db8:23::/64`, `2001:db8:34::/64`, `2001:db8:35::/64`, `2001:db8:36::/64` — these fall in the `0010`–`0036` range, outside the `/45` boundary).

| Prefix | Covered? | Reason |
|--------|----------|--------|
| 2001:db8:1::/64 | Yes | Third group 0x0001 < 0x0008 |
| 2001:db8:4::/64 | Yes | Third group 0x0004 < 0x0008 |
| 2001:db8:5::/64 | Yes | Third group 0x0005 < 0x0008 |
| 2001:db8:12::/64 | No | Third group 0x0012 ≥ 0x0008 |
| 2001:db8:23::/64 | No | Third group 0x0023 ≥ 0x0008 |

### IS-IS External Redistribution

IS-IS can redistribute static routes (or routes learned via other protocols) into its LSDB using `redistribute static ip` under `router isis`. For IPv6, the equivalent goes inside `address-family ipv6`:

```
router isis CORE
 redistribute static ip
 address-family ipv6
  redistribute static
 exit-address-family
```

Redistributed prefixes appear in the IS-IS LSDB as external (Type 5) TLV entries. On Cisco IOS, the redistributing router generates an LSP carrying these prefixes, which floods normally across the domain.

### IS-IS L2-to-L1 Route Leaking

By default, L2-only routes (inter-area or external) are not visible in L1 areas. The ATT bit provides a default route, but individual L2 prefixes remain hidden. Route leaking explicitly copies selected L2 routes into the L1 LSDB, providing L1 routers with reachability to specific external or inter-area destinations without full L2 participation.

```
router isis CORE
 redistribute isis ip level-2 into level-1 distribute-list prefix LEAK_FROM_L2
```

The `distribute-list prefix <name>` controls which L2 prefixes leak into L1. Note the syntax: it is `distribute-list prefix <prefix-list-name>`, not `distribute-list prefix-list`.

```
ip prefix-list LEAK_FROM_L2 seq 5 permit 192.168.66.0/24
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| MT-IPv6 configuration | Enabling independent IPv4/IPv6 SPF trees in IS-IS |
| IS-IS IPv4 summarization | Aggregating L1 area prefixes at the L1/L2 border |
| IS-IS IPv6 summarization | Using `summary-prefix` under `address-family ipv6` |
| External redistribution | Injecting static routes from non-IS-IS devices into the domain |
| L2-to-L1 route leaking | Selectively advertising L2 prefixes into L1 areas via prefix-lists |
| Summary prefix math | Calculating correct aggregate boundaries to avoid summarizing transit links |

---

## 2. Topology & Scenario

**Scenario:** GlobalSP is extending its IS-IS core to support IPv6 dual-stack across both areas. A new external partner router (R6) has been connected at the area 49.0002 border via R3. Your task is to enable MT-IPv6 across all IS-IS speakers, aggregate area prefixes to reduce LSDB size, redistribute R6's prefixes into IS-IS, and selectively leak R6's reachability into area 49.0001 via the L2 border router.

```
Area 49.0001                        Area 49.0002
┌──────────────────┐    L2 Backbone  ┌──────────────────────────────────────┐
│                  │                 │                                      │
│  ┌───────────┐   │  10.1.23.0/24   │   ┌───────────┐    ┌───────────┐    │
│  │    R1     ├───┤─────────────────┤───┤    R3     ├────┤    R4     │    │
│  │ L1 stub   │   │   (L2-only)     │   │  L1/L2    │    │  L1 stub  │    │
│  │10.0.0.1/32│   │                 │   │10.0.0.3/32│    │10.0.0.4/32│    │
│  └─────┬─────┘   │                 │   └─────┬─────┘    └───────────┘    │
│        │ L1      │                 │         │ L1                        │
│   10.1.12.0/24   │                 │    10.1.35.0/24    ┌───────────┐    │
│        │         │                 │         │           │    R5     │    │
│  ┌─────┴─────┐   │                 │         └───────────┤  L1 stub  │    │
│  │    R2     │   │                 │                     │10.0.0.5/32│    │
│  │  L1/L2    │   │                 │   ┌───────────┐     └───────────┘    │
│  │10.0.0.2/32├───┘                 │   │    R6     │                      │
│  └───────────┘                     │   │ External  │ ← non-IS-IS          │
│                                    │   │10.0.0.6/32│   192.168.66.0/24   │
│                                    │   └─────┬─────┘                      │
│                                    │   10.1.36.0/24 (R3 Gi0/3)           │
└──────────────────┘                 └──────────────────────────────────────┘

IPv6 addressing mirrors IPv4:
  Transit links:  2001:DB8:XY::/64 (XY = two router numbers, e.g. 12, 23, 34, 35, 36)
  Loopback0:      2001:DB8::N/128  (N = router number)
  Loopback1 (Lo1): 2001:DB8:N::/64  (N = router number, e.g. 2001:DB8:1::/64 for R1)
  R6 external:    2001:DB8:66::/64 on Lo1

Route summarization on R3 (area 49.0002 → L2):
  IPv4: 172.16.0.0/21  (covers 172.16.0.0–172.16.7.255, aggregates R4 172.16.4.0/24 + R5 172.16.5.0/24)
  IPv6: 2001:DB8::/45  (covers 2001:db8:0000::/48 to 2001:db8:0007::/48)

Route leaking on R2 (L2 → area 49.0001):
  Leaks 192.168.66.0/24 (R6's partner prefix) into area 49.0001
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | L1 Stub Router, area 49.0001 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | L1/L2 Border Router, area 49.0001 side | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | L1/L2 Border Router, area 49.0002 side | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | L1 Stub Router, area 49.0002 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | L1 Stub Router, area 49.0002 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | External Router (non-IS-IS) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Address Table

| Device | Interface | IPv4 Address | IPv6 Address | Purpose |
|--------|-----------|--------------|--------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | 2001:DB8::1/128 | Router ID, IS-IS NET |
| R1 | Loopback1 | 172.16.1.1/24 | 2001:DB8:1::1/64 | Simulated customer prefix |
| R2 | Loopback0 | 10.0.0.2/32 | 2001:DB8::2/128 | Router ID, IS-IS NET |
| R3 | Loopback0 | 10.0.0.3/32 | 2001:DB8::3/128 | Router ID, IS-IS NET |
| R4 | Loopback0 | 10.0.0.4/32 | 2001:DB8::4/128 | Router ID, IS-IS NET |
| R4 | Loopback1 | 172.16.4.1/24 | 2001:DB8:4::1/64 | Simulated customer prefix |
| R5 | Loopback0 | 10.0.0.5/32 | 2001:DB8::5/128 | Router ID, IS-IS NET |
| R5 | Loopback1 | 172.16.5.1/24 | 2001:DB8:5::1/64 | Simulated customer prefix |
| R6 | Loopback0 | 10.0.0.6/32 | 2001:DB8::6/128 | Management |
| R6 | Loopback1 | 192.168.66.1/24 | 2001:DB8:66::1/64 | External partner prefix |

### Cabling Table

| Link | From Device | From Interface | To Device | To Interface | Subnet (IPv4) | Subnet (IPv6) | IS-IS Level |
|------|-------------|----------------|-----------|--------------|---------------|---------------|-------------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | 2001:DB8:12::/64 | L1 (area 49.0001) |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/24 | 2001:DB8:23::/64 | L2 backbone |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 | 10.1.34.0/24 | 2001:DB8:34::/64 | L1 (area 49.0002) |
| L4 | R3 | Gi0/2 | R5 | Gi0/0 | 10.1.35.0/24 | 2001:DB8:35::/64 | L1 (area 49.0002) |
| L5 | R3 | Gi0/3 | R6 | Gi0/0 | 10.1.36.0/24 | 2001:DB8:36::/64 | Non-IS-IS (external) |

### Advertised Prefixes

| Device | Prefix (IPv4) | Prefix (IPv6) | Method | Notes |
|--------|---------------|---------------|--------|-------|
| R3 | 172.16.0.0/21 | 2001:DB8::/45 | IS-IS summary | Aggregate for area 49.0002 Lo1 prefixes |
| R3 | 192.168.66.0/24 | 2001:DB8:66::/64 | IS-IS redistribute static | R6 external partner prefix |
| R2 | 192.168.66.0/24 | — | IS-IS route leak (L2→L1) | Leaked into area 49.0001 |

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
- Hostnames on all routers
- IPv4 interface addressing on all links and loopbacks (all six routers)
- `no ip domain-lookup` on all routers
- IS-IS process CORE with NETs, `is-type`, `metric-style wide`, and `passive-interface` on loopbacks (R1–R5)
- IS-IS circuit-types on all IS-IS interfaces (L1, L2-only, or L1-2 as appropriate)
- `ipv6 unicast-routing` on R6 (external router — pre-configured since R6 has no IS-IS tasks)
- R6 default routes (ip route and ipv6 route pointing to R3)

**IS NOT pre-loaded** (student configures this):
- `ipv6 unicast-routing` on R1–R5
- IPv6 addresses on all interfaces of R1–R5
- IPv6 IS-IS enablement on all R1–R5 IS-IS interfaces (`ipv6 router isis CORE`)
- IS-IS MT-IPv6 (`address-family ipv6 / multi-topology`) on R1–R5
- R3's Gi0/3 interface configuration and static routes to R6's prefixes
- External prefix redistribution (static into IS-IS) on R3
- IPv4 route summarization on R3
- IPv6 route summarization on R2 and R3
- L2-to-L1 route leaking on R2 with a prefix-list

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IPv6 Dual-Stack IS-IS on All Routers

On every IS-IS router (R1 through R5):
- Enable IPv6 routing globally.
- Assign IPv6 addresses to all IS-IS participating interfaces (loopbacks and transit links), using the addressing scheme in the Loopback Address Table and Cabling Table in Section 3.
- Enable IPv6 IS-IS on each interface that already participates in IPv4 IS-IS.
- Enable IS-IS Multi-Topology IPv6 (MT-IPv6) under the IS-IS routing process. This activates a separate SPF calculation for IPv6.

**Verification:** `show isis neighbors` must show adjacencies in both INIT→UP for IPv4 and IPv6 topologies. `show isis topology ipv6` must list all IS-IS routers as reachable. `show ipv6 route isis` on R1 must show IPv6 IS-IS routes for remote loopbacks.

---

### Task 2: Connect R6 and Redistribute External Prefixes

On R3:
- Activate the interface connecting to R6 (using the addressing from the cabling table). This interface does NOT participate in IS-IS.
- Add static routes pointing to R6's two prefixes: its Loopback1 host prefix and its external partner subnet. Use R6's interface address on the L5 link as the next-hop.
- Redistribute the static routes into IS-IS for both IPv4 and IPv6.

**Verification:** `show ip route isis` on R1 must include a redistributed IS-IS external route for 192.168.66.0/24 (or the summary covering it, once Task 3 is complete). `show isis database detail` on R3 must show the external TLV entries in R3's LSP.

---

### Task 3: Configure IPv4 Route Summarization on R3

On R3, configure the IS-IS process to summarize the area 49.0002 Lo1 prefixes (172.16.4.0/24 and 172.16.5.0/24) into a single aggregate when they are injected into the L2 LSDB. Use the smallest correct aggregate that covers both specific prefixes without capturing transit or loopback-0 space.

**Verification:** `show ip route isis` on R2 must show the aggregate (not the two specifics). `show ip route` on R3 must show a Null0 discard route for the aggregate (IS-IS summary routes install a discard to prevent loops). The specific prefixes 172.16.4.0/24 and 172.16.5.0/24 must NOT appear in R2's IS-IS table.

---

### Task 4: Configure IPv6 Route Summarization on R2 and R3

On both border routers (R2 and R3), configure IS-IS to summarize the area Lo1 IPv6 prefixes into the aggregate `2001:DB8::/45` within the IPv6 address family. This aggregate covers the third group range 0x0000–0x0007, which includes all Lo1 prefixes while excluding all transit link subnets (which begin at 0x0012 and above).

**Verification:** `show ipv6 route isis` on R1 must show `2001:DB8::/45` as a single IS-IS route (not the individual /64 prefixes). `show ipv6 route` on R3 must show a Null0 discard for `2001:DB8::/45`. Individual Lo1 prefixes (2001:db8:1::/64, 2001:db8:4::/64, 2001:db8:5::/64) must NOT appear as separate entries in R1's IPv6 IS-IS table.

---

### Task 5: Configure L2-to-L1 Route Leaking on R2

On R2, selectively leak the external partner prefix (192.168.66.0/24) from the L2 LSDB into the area 49.0001 L1 domain. Use a prefix-list to restrict the leak to only this specific prefix — do not leak all L2 routes.

**Verification:** `show ip route isis` on R1 must include 192.168.66.0/24 as an IS-IS L1 route (not a default route). `show isis database detail` on R2 must show the leaked prefix in R2's L1 LSP. Confirm that R4 and R5's Lo1 specifics (172.16.4.0/24, 172.16.5.0/24) do NOT appear in R1's routing table — only the aggregate 172.16.0.0/21 from Task 3.

---

## 6. Verification & Analysis

### Task 1: MT-IPv6 Adjacencies

```
R1# show isis neighbors

System Id      Type Interface   IP Address      State Holdtime Circuit Id
R2             L1   Gi0/0       10.1.12.2       UP    23       R2.01         ! ← R2 must show UP L1 adjacency

R1# show isis topology ipv6

IS-IS TID 2 paths to level-1 routers
System Id            Metric     Next-Hop          Interface     SNPA
R2                   10         R2                Gi0/0         *SNPA*       ! ← R2 reachable via IPv6 topology
R3                   20         R2                Gi0/0         *SNPA*       ! ← inter-area via L2

R1# show ipv6 route isis
I1  2001:DB8::2/128 [115/20] via FE80::..., GigabitEthernet0/0  ! ← R2 loopback via IS-IS
I1  2001:DB8::/45   [115/...]  via FE80::..., GigabitEthernet0/0 ! ← IPv6 summary from area 49.0002
```

### Task 2: External Redistribution

```
R3# show isis database detail R3.00-00

IS-IS Level-2 LSP R3.00-00
...
  IPv4 External Reachability:
    192.168.66.0/24              ! ← redistributed static IPv4 prefix
  IPv6 External Reachability:
    2001:DB8:66::/64             ! ← redistributed static IPv6 prefix

R1# show ip route isis | include 192.168
I L1  192.168.66.0/24 [115/...]  via 10.1.12.2, GigabitEthernet0/0  ! ← leaked to L1 via R2 (Task 5)
```

### Task 3: IPv4 Summarization

```
R2# show ip route isis
...
I L2  172.16.0.0/21 [115/20] via 10.1.23.3, GigabitEthernet0/1   ! ← aggregate, NOT specifics
! The individual 172.16.4.0/24 and 172.16.5.0/24 must NOT appear here

R3# show ip route 172.16.0.0 255.255.248.0
Routing entry for 172.16.0.0/21
  Known via "isis", distance 5, metric 0
  Routing Descriptor Blocks:
  * directly connected, via Null0                                  ! ← Null0 discard confirms summary is active
```

### Task 4: IPv6 Summarization

```
R1# show ipv6 route isis
I L1  2001:DB8::/45 [115/...] via FE80::..., GigabitEthernet0/0  ! ← IPv6 aggregate present
! 2001:DB8:1::/64, 2001:DB8:4::/64, 2001:DB8:5::/64 must NOT appear as individual entries

R3# show ipv6 route 2001:DB8::/45
Routing entry for 2001:DB8::/45
  Known via "isis", distance 5, metric 0
  * directly connected, via Null0                                  ! ← Null0 discard for IPv6 summary
```

### Task 5: Route Leaking

```
R1# show ip route isis
...
I L1  192.168.66.0/24 [115/...]  via 10.1.12.2, GigabitEthernet0/0  ! ← leaked prefix appears as L1
! 172.16.4.0/24 and 172.16.5.0/24 must NOT appear (only 172.16.0.0/21 aggregate should show up)

R2# show isis database detail R2.00-00
...
  IPv4 Internal Reachability:   (L1 LSP)
    192.168.66.0/24              ! ← leaked prefix in R2's L1 LSP
```

---

## 7. Verification Cheatsheet

### IS-IS MT-IPv6 Configuration

```
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
!
interface <if>
 ipv6 router isis CORE
```

| Command | Purpose |
|---------|---------|
| `show isis topology` | IPv4 SPF tree; all IS-IS routers and metrics |
| `show isis topology ipv6` | IPv6 SPF tree (TID 2); confirm separate IPv6 reachability |
| `show isis neighbors` | Adjacency state and levels |
| `show ipv6 route isis` | IPv6 IS-IS routes installed in FIB |

> **Exam tip:** MT-IPv6 uses TID 2 (Type-Length-Value 222). Single-topology uses TLV 236 for IPv6 prefixes. Check `show isis database detail` — MT mode shows separate IPv4 and IPv6 reachability TLVs.

### Route Summarization

```
! IPv4 summary (under router isis)
router isis CORE
 summary-address <network> <mask>

! IPv6 summary (under address-family ipv6)
router isis CORE
 address-family ipv6
  summary-prefix <prefix/len>
 exit-address-family
```

| Command | Purpose |
|---------|---------|
| `show ip route <summary>` | Confirm Null0 discard is installed locally |
| `show ipv6 route <prefix>` | Confirm IPv6 Null0 discard |
| `show ip route isis` | Verify specifics are suppressed; only aggregate visible |

> **Exam tip:** IS-IS `summary-address` and `summary-prefix` only take effect when the border router has at least one more-specific prefix in its L1 LSDB. If the specific routes disappear, the summary also withdraws — no black-hole.

### External Redistribution

```
router isis CORE
 redistribute static ip
 address-family ipv6
  redistribute static
 exit-address-family
```

| Command | Purpose |
|---------|---------|
| `show isis database detail <router>` | Verify external TLV in LSP |
| `show ip route static` | Confirm static routes are present on redistributing router |

### L2-to-L1 Route Leaking

```
ip prefix-list LEAK_FROM_L2 seq 5 permit <prefix/len>
!
router isis CORE
 redistribute isis ip level-2 into level-1 distribute-list prefix LEAK_FROM_L2
```

| Command | Purpose |
|---------|---------|
| `show ip prefix-list LEAK_FROM_L2` | Verify prefix-list content |
| `show isis database detail` | Confirm leaked prefix appears in L1 LSP on leaking router |
| `show ip route isis` on L1 router | Confirm leaked prefix installed with L1 tag |

> **Exam tip:** Use `distribute-list prefix <name>` — NOT `distribute-list prefix-list <name>`. The keyword `prefix-list` is used in OSPF/EIGRP; IS-IS uses `prefix` followed by the prefix-list name.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis neighbors` | All expected adjacencies UP at correct level |
| `show isis topology` | All IS-IS routers reachable via IPv4 SPF |
| `show isis topology ipv6` | All IS-IS routers reachable via separate IPv6 SPF |
| `show isis database detail` | External TLVs for redistributed prefixes; leaked prefixes in L1 LSP |
| `show ip route isis` | Aggregate present; specifics suppressed; leaked prefix in L1 |
| `show ipv6 route isis` | IPv6 aggregate; specifics suppressed |
| `show ip route <aggregate> <mask>` | Null0 discard installed (confirms summary is active) |
| `ping <R6-prefix>` from R1 | End-to-end IPv4 reachability to external prefix |

### Common IS-IS MT-IPv6 Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| IPv6 routes missing, IPv4 fine | `multi-topology` not configured, or `ipv6 router isis` missing on interface |
| Summary not installed as Null0 | No specific more-specific route exists in LSDB; summary withdrawn |
| Leaked prefix not in L1 area | `distribute-list prefix` allows wrong prefix; or `redistribute isis ... level-2 into level-1` missing |
| External prefix not in IS-IS | `redistribute static ip` missing; or static route absent from routing table |
| IPv6 adjacency stuck in INIT | MTU mismatch on link, or `multi-topology` not enabled on both ends |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Enable IPv6 Dual-Stack IS-IS

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8::1/128
 ipv6 router isis CORE
!
interface Loopback1
 ipv6 address 2001:DB8:1::1/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:12::1/64
 ipv6 router isis CORE
!
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8::2/128
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:12::2/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/1
 ipv6 address 2001:DB8:23::2/64
 ipv6 router isis CORE
!
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8::3/128
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:23::3/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/1
 ipv6 address 2001:DB8:34::3/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/2
 ipv6 address 2001:DB8:35::3/64
 ipv6 router isis CORE
!
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 and R5 Configuration</summary>

```bash
! R4
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8::4/128
 ipv6 router isis CORE
!
interface Loopback1
 ipv6 address 2001:DB8:4::1/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:34::4/64
 ipv6 router isis CORE
!
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family

! R5
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8::5/128
 ipv6 router isis CORE
!
interface Loopback1
 ipv6 address 2001:DB8:5::1/64
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:35::5/64
 ipv6 router isis CORE
!
router isis CORE
 address-family ipv6
  multi-topology
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis neighbors
show isis topology ipv6
show ipv6 route isis
```
</details>

---

### Task 2: Connect R6 and Redistribute External Prefixes

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
ip route 192.168.66.0 255.255.255.0 10.1.36.6
ipv6 route 2001:DB8:66::/64 2001:DB8:36::6
!
interface GigabitEthernet0/3
 ip address 10.1.36.3 255.255.255.0
 ipv6 address 2001:DB8:36::3/64
 no shutdown
!
router isis CORE
 redistribute static ip
 address-family ipv6
  redistribute static
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route static
show isis database detail R3.00-00
show ip route isis | include 192.168
show ipv6 route isis | include 2001:DB8:66
```
</details>

---

### Task 3: Configure IPv4 Route Summarization on R3

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router isis CORE
 summary-address 172.16.0.0 255.255.248.0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route 172.16.0.0 255.255.248.0
show ip route isis
! On R2: verify 172.16.0.0/21 present, specifics absent
```
</details>

---

### Task 4: Configure IPv6 Route Summarization on R2 and R3

<details>
<summary>Click to view R2 and R3 Configuration</summary>

```bash
! R2 and R3 (same config on both)
router isis CORE
 address-family ipv6
  summary-prefix 2001:DB8::/45
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 route 2001:DB8::/45
show ipv6 route isis
! On R1: verify 2001:DB8::/45 present, individual /64 Lo1 prefixes absent
```
</details>

---

### Task 5: Configure L2-to-L1 Route Leaking on R2

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip prefix-list LEAK_FROM_L2 seq 5 permit 192.168.66.0/24
!
router isis CORE
 redistribute isis ip level-2 into level-1 distribute-list prefix LEAK_FROM_L2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip prefix-list LEAK_FROM_L2
show isis database detail R2.00-00
! On R1: show ip route isis — 192.168.66.0/24 must appear as I L1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and the fix script for restoration.

### Workflow

```bash
python3 apply_solution.py --host <eve-ng-ip>              # restore to known-good state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>  # Ticket 2
python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>  # Ticket 3
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — R4 Has Full IPv4 Reachability But No IPv6 Routes

The NOC reports that R4's IPv4 routing is intact and its IS-IS adjacency to R3 shows UP, but R4 cannot reach any IPv6 destination in the network. IPv4 pings from R4 to all other routers succeed; IPv6 pings fail entirely.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ipv6 route isis` on R4 shows all expected IPv6 IS-IS routes including the 2001:DB8::/45 summary and 2001:DB8::2/128, 2001:DB8::3/128 loopbacks.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm IPv4 adjacency is still UP
R4# show isis neighbors
! R3 should show UP — L1 adjacency intact

! Step 2: Check IPv6 topology separately
R4# show isis topology ipv6
! R4 likely does not appear — or shows no reachability

! Step 3: Check R4's IS-IS IPv6 interface participation
R4# show isis interface
! Look for IS-IS IPv6 column — interfaces may show "IPv6 disabled"

! Step 4: Check interface-level IS-IS enablement for IPv6
R4# show running-config | section isis
! Look for missing "ipv6 router isis CORE" on interfaces

! Step 5: Verify MT-IPv6 is enabled on R4's process
R4# show isis
! Check for "MT IPv6" in the output — if absent, multi-topology not configured
```

Root cause: `ipv6 router isis CORE` has been removed from R4's IS-IS interfaces, disabling IPv6 IS-IS participation while leaving IPv4 IS-IS intact. The IS-IS adjacency remains up (IPv4 still present) but the IPv6 MT topology (TID 2) has no R4 participation.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
interface Loopback0
 ipv6 router isis CORE
!
interface Loopback1
 ipv6 router isis CORE
!
interface GigabitEthernet0/0
 ipv6 router isis CORE
```

After applying: `show isis topology ipv6` should show R4 reachable. `show ipv6 route isis` on R4 should populate with the domain's IPv6 prefixes.
</details>

---

### Ticket 2 — R6's Partner Prefix Has Disappeared From the Entire IS-IS Domain

An external partner connectivity check has failed. The prefix 192.168.66.0/24 — previously visible in both IS-IS areas — is no longer present in the routing tables of any IS-IS router. IPv4 IS-IS adjacencies are intact and the 172.16.0.0/21 aggregate is still visible. Only R6's partner prefix is missing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip route isis` on R1 must show 192.168.66.0/24 (via the route-leak on R2). `show ip route isis` on R2 must show the prefix as a redistributed IS-IS external route from R3's L2 LSP.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm static routes exist on R3
R3# show ip route static
! If 192.168.66.0/24 static route is absent, redistribution has no source

! Step 2: Check R3's IS-IS database for redistributed prefixes
R3# show isis database detail R3.00-00
! Look for "IPv4 External Reachability" — if 192.168.66.0/24 is absent, redistribution failed

! Step 3: Check R3's IS-IS configuration
R3# show running-config | section router isis
! Look for "redistribute static ip" — if absent, redistribution was removed

! Step 4: Check for unexpected summary-address entries
R3# show running-config | include summary-address
! A broad summary-address (e.g. 192.168.0.0/16) would shadow the specific while the
! specific is still redistributed — but if redistribute static ip is gone, the prefix
! never enters IS-IS at all

! Step 5: Confirm R6 connectivity from R3
R3# ping 192.168.66.1
! If reachable, the static route exists; the problem is in IS-IS redistribution config
```

Root cause: `redistribute static ip` has been removed from R3's IS-IS process. R3's static route to 192.168.66.0/24 still exists in its routing table but is no longer injected into the IS-IS LSDB. Consequently, neither R2 nor any other router sees the prefix in IS-IS.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
router isis CORE
 redistribute static ip
 address-family ipv6
  redistribute static
 exit-address-family
```

After applying: `show isis database detail R3.00-00` should show 192.168.66.0/24 and 2001:DB8:66::/64 in external TLVs. `show ip route isis` on R1 should show the leaked prefix (via Task 5 route-leak on R2).
</details>

---

### Ticket 3 — Area 49.0001 Cannot Reach the External Partner Prefix

The NOC confirms R3 is redistributing 192.168.66.0/24 correctly — it appears in R3's L2 LSP and is visible from R2's L2 routing table. However, R1 in area 49.0001 does not see 192.168.66.0/24 in its routing table. R1's only IS-IS routes are the loopback /32s, the 172.16.0.0/21 aggregate, and the default route from the ATT bit.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip route isis` on R1 shows 192.168.66.0/24 as an IS-IS L1 route installed via R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm the prefix is visible in L2 from R2
R2# show ip route isis
! 192.168.66.0/24 should appear as I L2 — if absent, R3 redistribution is the problem

! Step 2: Check R2's route-leak configuration
R2# show running-config | section router isis
! Look for "redistribute isis ip level-2 into level-1 distribute-list prefix LEAK_FROM_L2"

! Step 3: Check the prefix-list content
R2# show ip prefix-list LEAK_FROM_L2
! If the prefix-list permits the wrong network (e.g. 192.168.0.0/16) or denies 192.168.66.0/24
! the leak filter blocks the specific prefix

! Step 4: Check R2's L1 LSP for the leaked prefix
R2# show isis database detail R2.00-00
! If 192.168.66.0/24 is absent from R2's L1 LSP, the distribute-list is filtering it out

! Step 5: Test from R1
R1# show ip route isis | include 192.168
! Route must be absent to confirm the leak is broken
```

Root cause: The `LEAK_FROM_L2` prefix-list on R2 has been changed to deny 192.168.66.0/24 (or permit a different range). R2's route-leak configuration is still present, but the filter prevents 192.168.66.0/24 from being copied into the L1 LSDB.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
no ip prefix-list LEAK_FROM_L2
ip prefix-list LEAK_FROM_L2 seq 5 permit 192.168.66.0/24
```

After applying: `show ip prefix-list LEAK_FROM_L2` confirms the correct permit. `show isis database detail R2.00-00` should show 192.168.66.0/24 in the L1 LSP. `show ip route isis` on R1 should show the leaked route.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ipv6 unicast-routing` enabled on R1–R5
- [ ] IPv6 addresses assigned on all IS-IS interfaces of R1–R5
- [ ] `ipv6 router isis CORE` on all IS-IS interfaces of R1–R5
- [ ] `address-family ipv6 / multi-topology` configured on R1–R5
- [ ] `show isis topology ipv6` shows all routers reachable
- [ ] R3 Gi0/3 active with IP addressing; R3 static routes to R6 prefixes configured
- [ ] `redistribute static ip` (IPv4) and `redistribute static` (IPv6) configured on R3
- [ ] 192.168.66.0/24 appears in `show isis database detail R3.00-00`
- [ ] `summary-address 172.16.0.0 255.255.248.0` on R3
- [ ] R3 shows Null0 for 172.16.0.0/21; R2 shows aggregate only (no specifics)
- [ ] `summary-prefix 2001:DB8::/45` on R2 and R3 under `address-family ipv6`
- [ ] R1 shows 2001:DB8::/45 as single IS-IS route; individual Lo1 /64s absent
- [ ] `ip prefix-list LEAK_FROM_L2 seq 5 permit 192.168.66.0/24` on R2
- [ ] `redistribute isis ip level-2 into level-1 distribute-list prefix LEAK_FROM_L2` on R2
- [ ] `show ip route isis` on R1 shows 192.168.66.0/24 as I L1

### Troubleshooting

- [ ] Ticket 1 resolved: R4's IPv6 IS-IS re-enabled; `show isis topology ipv6` shows R4
- [ ] Ticket 2 resolved: R3 redistribution restored; 192.168.66.0/24 back in IS-IS LSDB
- [ ] Ticket 3 resolved: R2 prefix-list corrected; 192.168.66.0/24 visible on R1 again

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure (one or more devices failed) | `apply_solution.py` only |
| 2 | `--host` not provided or placeholder detected | All scripts |
| 3 | EVE-NG connectivity or port discovery error | All scripts |
| 4 | Pre-flight check failed (lab not in expected state) | Inject scripts only |
