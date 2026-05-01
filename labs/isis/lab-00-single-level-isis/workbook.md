# Lab 00: Single-Level IS-IS Foundations

**Topic:** IS-IS Routing | **Exam:** 300-510 SPRI | **Blueprint:** 1.3
**Difficulty:** Foundation | **Time:** 45 minutes | **Type:** Progressive (lab-00 of 5)

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

**Exam Objective:** 1.3 — Describe IS-IS operations and compare with OSPF

This lab establishes the IS-IS baseline for the entire IS-IS topic. Three routers
are brought up as Level-1-only neighbours inside a single area, giving you a clean
environment to examine the NET addressing format, IIH (IS-IS Hello) mechanics, the
DIS election on broadcast LANs, and the L1 LSP database before the topology grows in
complexity in labs 01–03.

### IS-IS NET Addressing — How a Router Identifies Itself

Every IS-IS router carries a single CLNS address called the **NET (Network Entity
Title)**. Unlike OSPF, the NET is the only identity an IS-IS router has — there is no
separate router-ID command. The NET combines area, system-ID, and selector fields:

```
49.0001.0000.0000.0001.00
└┬─┘ └─┬┘ └──────┬──────┘ └┬┘
 │    │         │          └── NSEL (NET selector — always 00)
 │    │         └──────────── System ID (6 bytes, must be unique in the area)
 │    └────────────────────── Area ID (variable length, must match for L1)
 └─────────────────────────── AFI (Address Family Identifier — 49 = private)
```

| Field | Meaning | Lab values |
|-------|---------|-----------|
| AFI | Address-family — `49` is the private/local AFI (analogous to RFC1918) | All routers: `49` |
| Area ID | Defines the IS-IS area; **must match** for an L1 adjacency to form | All routers: `0001` |
| System ID | 6 hex bytes, unique per router in the area; conventionally derived from Lo0 | R1=`0000.0000.0001`, R2=`0000.0000.0002`, R3=`0000.0000.0003` |
| NSEL | Always `00` on a router NET | All routers: `00` |

> **Exam tip:** Two routers with different area IDs can never form an L1 adjacency. A
> single-byte typo in the area ID is the most common IS-IS adjacency fault — and you
> will troubleshoot exactly that in Ticket 1 of this lab.

### IS-IS Levels — L1, L2, and L1/L2

IS-IS has only one process per router and supports two routing levels:

| Level | Role | Database | Used in |
|-------|------|----------|---------|
| **Level 1** | Intra-area routing inside one area | L1 LSDB only | This lab — all three routers |
| **Level 2** | Inter-area / backbone routing | L2 LSDB only | Introduced in lab-01 |
| **Level 1/2** | Both — acts as area border | Two separate LSDBs | Introduced in lab-01 |

The router-wide level is set with `is-type {level-1 | level-2-only | level-1-2}`.
This lab uses `is-type level-1` everywhere so you can focus on a single LSDB without
the noise of L2 flooding or the Attached (ATT) bit.

### IIH, DIS, and the L1 LSP Database

IS-IS adjacency formation is simpler than OSPF — there are only three observable
states (DOWN → INIT → UP) and the trigger is the IIH (IS-IS Hello) PDU.

**IIH (IS-IS Hello):**

- Sent every 10 seconds by default on broadcast LAN interfaces
- Carries the sender's system ID, area ID, level, and circuit type
- An adjacency reaches **UP** once both sides see each other's system ID inside the
  Hello's IS-Neighbours TLV
- IIH PDUs are sent directly over the layer-2 frame (no IP) — IS-IS is immune to
  IP-layer misconfiguration

**DIS (Designated Intermediate System):**

- Elected on every broadcast (LAN) circuit — not on point-to-point links
- One DIS per level per LAN: an L1/L2 router can be DIS for L1, L2, or both
- DIS election: highest priority, then highest SNPA (MAC address) — **no router-ID
  tiebreaker** as in OSPF
- DIS election is **preemptive**: a higher-priority router that joins later takes over
- The DIS originates a **pseudonode LSP** (LSP-ID with non-zero pseudonode byte) that
  represents the LAN as a virtual node — this is the IS-IS analogue of an OSPF
  Type-2 Network-LSA

**L1 LSP (Link State PDU):**

- Each router floods one or more L1 LSPs describing its links and reachable prefixes
- LSPs are identified by `<system-id>.<pseudonode-byte>-<fragment>` — e.g.
  `0000.0000.0001.00-00` is R1's non-pseudonode LSP fragment 0
- LSPs carry **TLVs** (Type-Length-Value records) — TLV 22 carries IPv4 reachability
  with wide metrics; TLV 2 carries IS neighbours

```
show clns neighbors                    ! Adjacency state (UP/INIT/DOWN)
show isis neighbors detail             ! Holdtime countdown, area address, level, circuit type (not configured hello interval)
show isis database                     ! L1 LSDB summary
show isis database detail              ! TLVs inside each LSP
```

### IS-IS vs OSPF — Architectural Comparison

The 300-510 blueprint requires being able to compare the two IGPs. The table below
maps the most exam-relevant analogues:

| Dimension | IS-IS (this lab) | OSPF (ospf topic) |
|-----------|------------------|--------------------|
| PDU encapsulation | Direct over CLNS / L2 (no IP) | IP protocol 89 |
| Topology unit | LSP (Link State PDU) | LSA (Link State Advertisement) |
| Area boundary router | L1/L2 router (`is-type`) | ABR (per-interface area) |
| Router identity | NET (NSAP — area + system-ID) | Router-ID (32-bit, often Lo0) |
| Designated router on LAN | DIS — one per level, preemptive | DR/BDR — non-preemptive |
| Pseudonode LSA equivalent | Pseudonode LSP (DIS-originated) | Type-2 Network-LSA (DR-originated) |
| Adjacency states | DOWN → INIT → UP | 7 states (DOWN → FULL) |
| Default LAN hello | 10 s / 30 s hold | 10 s / 40 s dead |
| Protocol independence | Multi-topology supports v4 + v6 in one process | OSPFv2 = IPv4 only; OSPFv3 for IPv6 |
| SP deployment preference | Preferred SP core IGP (protocol-independent) | Common at enterprise / CE edge |

The key insight: IS-IS runs **below** IP, which makes it immune to the IP-layer
misconfigurations (wrong IP, missing route, mismatched MTU on IP layer) that would
break an OSPF adjacency. This is why most SP operators run IS-IS as the IGP and use
OSPF only at the CE or enterprise edge.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| NET addressing | Build a syntactically correct NET and decode its three fields |
| IS-IS process configuration | Bring up a Level-1 IS-IS process on IOSv |
| Interface enablement | Apply `ip router isis` per interface (no `network` statement!) |
| LSDB reading | Interpret L1 LSPs, pseudonode LSPs, and the TLVs they carry |
| Adjacency tracing | Use `show clns neighbors` to follow DOWN → INIT → UP |
| DIS election | Predict and verify which router wins DIS on a broadcast LAN |
| Hello-timer tuning | Adjust `isis hello-interval` and observe adjacency reset |
| IS-IS vs OSPF contrast | Map analogous concepts between the two IGPs |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at SP-Core Ltd. The operations team has
asked you to bring up IS-IS on a new three-router segment. All three nodes are
currently IP-addressed only. Your task is to configure NET addressing, enable IS-IS
on the routed interfaces as Level-1, verify the L1 LSDB and DIS election, and
confirm end-to-end loopback reachability before the segment is split into two areas
in lab-01.

> **Design note:** All three routers are placed in area `49.0001` for this lab.
> Starting in lab-01, R3 moves to area `49.0002` and R2/R3 are promoted to L1/L2 so
> the R2↔R3 link becomes an L2-only adjacency. Nothing is removed from this lab's
> solution — lab-01 adds new config on top.

```
                    ┌──────────────────────────┐
                    │            R1            │
                    │      (L1 router —        │
                    │       area 49.0001)      │
                    │   NET: 49.0001....0001.00│
                    │   Lo0: 10.0.0.1/32       │
                    │   Lo1: 172.16.1.1/24     │
                    └────────────┬─────────────┘
                                 │ GigabitEthernet0/0
                                 │ 10.1.12.1/24
                                 │
                                 │ 10.1.12.2/24
                                 │ GigabitEthernet0/0
                    ┌────────────┴─────────────┐
                    │            R2            │
                    │     (L1 router —         │
                    │  future L1/L2 in lab-01) │
                    │   NET: 49.0001....0002.00│
                    │   Lo0: 10.0.0.2/32       │
                    └────────────┬─────────────┘
                                 │ GigabitEthernet0/1
                                 │ 10.1.23.2/24
                                 │
                                 │ 10.1.23.3/24
                                 │ GigabitEthernet0/0
                    ┌────────────┴─────────────┐
                    │            R3            │
                    │      (L1 router —        │
                    │  moves to 49.0002 in     │
                    │       lab-01)            │
                    │   NET: 49.0001....0003.00│
                    │   Lo0: 10.0.0.3/32       │
                    └──────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │              Area 49.0001 (single-level)                 │
    │       All three routers — temporary single-area          │
    └──────────────────────────────────────────────────────────┘
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | L1 router (future L1 in area 49.0001) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R2 | L1 router (future L1/L2 ABR in lab-01) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| R3 | L1 router (future L1/L2 in area 49.0002) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |

### Cabling

| Link | Source | Interface | Target | Interface | Subnet |
|------|--------|-----------|--------|-----------|--------|
| L1 | R1 | GigabitEthernet0/0 | R2 | GigabitEthernet0/0 | 10.1.12.0/24 |
| L2 | R2 | GigabitEthernet0/1 | R3 | GigabitEthernet0/0 | 10.1.23.0/24 |

### IP Address Reference

| Device | Interface | IP Address | Mask | NET |
|--------|-----------|------------|------|-----|
| R1 | Loopback0 | 10.0.0.1 | /32 | 49.0001.0000.0000.0001.00 |
| R1 | Loopback1 | 172.16.1.1 | /24 | (same NET — one per router) |
| R1 | GigabitEthernet0/0 | 10.1.12.1 | /24 | |
| R2 | Loopback0 | 10.0.0.2 | /32 | 49.0001.0000.0000.0002.00 |
| R2 | GigabitEthernet0/0 | 10.1.12.2 | /24 | |
| R2 | GigabitEthernet0/1 | 10.1.23.2 | /24 | |
| R3 | Loopback0 | 10.0.0.3 | /32 | 49.0001.0000.0000.0003.00 |
| R3 | GigabitEthernet0/0 | 10.1.23.3 | /24 | |

### Console Access

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial-configs and discover ports automatically.

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames (R1, R2, R3)
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all routers

**IS NOT pre-loaded** (student configures this):

- IS-IS routing process and its NET
- `is-type` (forces Level-1 on all three routers)
- `metric-style wide` (required for modern IS-IS deployments)
- Per-interface `ip router isis` enablement
- `passive-interface` for loopbacks
- Hello-interval modifications (Task 4)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure NET Addressing and Bring Up IS-IS Level-1

- Start an IS-IS routing process named `CORE` on each router (the tag is locally significant).
- Assign each router its NET: R1 uses `49.0001.0000.0000.0001.00`, R2 uses `49.0001.0000.0000.0002.00`, R3 uses `49.0001.0000.0000.0003.00`.
- Force the router-wide level to Level-1 with `is-type level-1`.
- Apply `metric-style wide` so wide metrics (modern, supports >63) are used in LSPs.
- Enable IS-IS on every IPv4 interface that should participate (transit links **and** loopbacks) with `ip router isis CORE` and constrain to L1 with `isis circuit-type level-1` on the interface.
- Make every loopback **passive** for IS-IS so it is advertised but does not send Hellos.

**Verification:** `show clns neighbors` on R2 must show both R1 and R3 in state UP. `show ip route isis` on R1 must show IS-IS-learned routes (i prefix) to R2 and R3 loopbacks.

---

### Task 2: Decode an LSP and Identify the Pseudonode

- Use the IS-IS database commands to find each router's L1 LSP and the pseudonode LSP for each broadcast segment.
- Record which router is the DIS on the 10.1.12.0/24 and 10.1.23.0/24 segments. Explain how DIS was elected (priority + SNPA — no router-ID tiebreaker).
- Confirm the pseudonode LSP-ID has the form `<dis-system-id>.<non-zero-byte>-00` and that the non-zero pseudonode byte distinguishes it from the DIS's own LSP.

**Verification:** `show isis database` on R2 must list four LSPs in the L1 database — three router LSPs (one per system ID, pseudonode byte = 00) and one or more pseudonode LSPs (pseudonode byte ≠ 00). `show clns interface GigabitEthernet0/0` on R1 must clearly identify the DIS for L1 on that segment.

---

### Task 3: Observe the IS-IS Adjacency State Machine

- Shut down R1's GigabitEthernet0/0 to drive the R1↔R2 adjacency to DOWN, then bring it back up and watch the rebuild from DOWN → INIT → UP using debug output.
- Record the three state transitions and the trigger that caused each (no Hello → Hello received → Hello with own system-ID echoed).
- Confirm the adjacency returns to UP within 30 seconds (default hold time is 30 s — three Hellos at 10 s each).

**Verification:** After bringing the interface back up, `show clns neighbors` on R2 must show R1 in state Up. Run `undebug all` before proceeding.

---

### Task 4: Tune the IS-IS Hello Interval

- On the 10.1.12.0/24 link (R1 Gi0/0 and R2 Gi0/0), change the IS-IS hello-interval to 3 seconds and the hello-multiplier to 4 on both sides simultaneously (hold = hello × multiplier = 12 s).
- Verify the new timers using `show running-config interface GigabitEthernet0/0` and confirm the negotiated hold time decreases with `show clns neighbors detail`.
- Intentionally mismatch the hello-multiplier by reverting **only R1** to defaults while leaving R2 at the fast values. Observe what happens (IS-IS tolerates timer mismatches better than OSPF — adjacency stays up because the **hold** time is advertised in each Hello, not negotiated).
- Restore both sides to default timers before moving to Task 5.

**Verification:** `show running-config interface GigabitEthernet0/0` on R2 must show `isis hello-interval 3` and `isis hello-multiplier 4` while the fast timers are applied. `show clns neighbors detail` should show Holdtime near 12 s (3 × 4). After restoring defaults, the two `isis hello-*` lines must be absent from the running config on both routers, and Holdtime should return to ~30 s.

---

### Task 5: IS-IS vs OSPF Conceptual Comparison

- Review the IS-IS vs OSPF comparison table in Section 1 and answer the following without configuration:
  - What is the IS-IS equivalent of an OSPF Type-1 Router-LSA? Of a Type-2 Network-LSA?
  - Why can an IS-IS adjacency form even when the two interface IPs are in different subnets — and would OSPF tolerate the same condition?
  - On a broadcast LAN, what is the most important behavioural difference between OSPF DR election and IS-IS DIS election?

**Verification:** No verification commands — answers are documented in your lab notes.

---

## 6. Verification & Analysis

### Adjacency State

```
R2# show clns neighbors

System Id      Interface     SNPA                State  Holdtime  Type Protocol
R1             Gi0/0         5000.0001.0000      Up     27        L1   IS-IS
R3             Gi0/1         5000.0003.0000      Up     28        L1   IS-IS
! ← Both neighbours in state Up — L1 LSDB is synchronised
! ← Type L1 confirms is-type level-1 is in effect on both ends
! ← Holdtime counts down from ~30 s; reset on each received Hello
```

### Detailed Neighbour View

```
R2# show isis neighbors detail

System Id      Type Interface     IP Address      State Holdtime Circuit Id
R1             L1   Gi0/0         10.1.12.1       UP    27       R2.01
  Area Address(es): 49.0001
  SNPA: 5000.0001.0000
  IPv4 Address(es):  10.1.12.1
  Hello Interval: 10 s, Hello Multiplier: 3
! ← Area Address must match for L1 — both are 49.0001
! ← Circuit Id R2.01 = the LAN's pseudonode ID (DIS = R2, pseudonode byte 01)
```

### LSDB — L1 Database

> **Note:** All three routers carry the default L1 priority of 64, so DIS is decided by
> the highest SNPA (MAC). EVE-NG IOSv MAC addresses are not deterministic across lab
> rebuilds — the example output below assumes R2 won DIS on both LANs (pseudonode
> LSP-IDs `R2.01-00` and `R2.02-00`). If your `show clns interface` reports R1 or R3
> as DIS instead, the pseudonode LSP-ID prefix changes accordingly. The protocol
> behaviour is identical either way.

```
R2# show isis database

IS-IS Level-1 Link State Database:
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime  ATT/P/OL
R1.00-00              0x00000003   0x1F2A        1100          0/0/0
R2.00-00              0x00000004   0x82B5        1180          0/0/0
R2.01-00              0x00000002   0x6CC1        1175          0/0/0   ← Pseudonode LSP for 10.1.12.0/24
R2.02-00              0x00000002   0x4DE3        1178          0/0/0   ← Pseudonode LSP for 10.1.23.0/24
R3.00-00              0x00000002   0xA044        1170          0/0/0

! Three router LSPs (suffix .00-00) — one per router
! Two pseudonode LSPs (suffix .01-00 and .02-00) — one per LAN with a DIS
! ATT bit = 0 (no L1/L2 attachment yet — that arrives in lab-01)
```

> **DIS election on each LAN:**
> On Gi0/0 (R1↔R2): both have priority 64 (default L1) → highest SNPA wins. R2 is DIS
> if its MAC is higher; otherwise R1 is. The pseudonode LSPID `R2.01-00` confirms R2
> is the DIS on this segment in this lab. On Gi0/1 (R2↔R3) `R2.02-00` again names R2
> as DIS. **No router-ID tiebreaker exists in IS-IS.**

### LSP Detail — Decoding the TLVs

```
R2# show isis database R1.00-00 detail

R1.00-00            0x00000003   0x1F2A        1100          0/0/0
  Area Address: 49.0001                            ! ← TLV 1 — area
  NLPID:        0xCC                               ! ← TLV 129 — IPv4 only
  Hostname:     R1                                 ! ← TLV 137 — dynamic hostname
  IP Address:   10.0.0.1                           ! ← TLV 132 — Lo0 advertised
  Metric: 10        IP-Extended 10.1.12.0/24       ! ← TLV 135 (wide metric)
  Metric: 10        IP-Extended 172.16.1.0/24      ! ← Lo1 advertised by R1
  Metric: 10        IP-Extended 10.0.0.1/32        ! ← Lo0 advertised by R1
  Metric: 10        IS-Extended R2.01              ! ← TLV 22 — neighbour via pseudonode R2.01
```

### Routing Table on R1

```
R1# show ip route isis

      10.0.0.0/8 is variably subnetted
i L1     10.0.0.2/32 [115/20] via 10.1.12.2, GigabitEthernet0/0   ! ← R2 loopback learned
i L1     10.0.0.3/32 [115/30] via 10.1.12.2, GigabitEthernet0/0   ! ← R3 loopback via R2
i L1     10.1.23.0/24 [115/20] via 10.1.12.2, GigabitEthernet0/0  ! ← R2-R3 transit link

! AD = 115 for IS-IS (vs 110 for OSPF)
! L1 marker confirms the prefix was learned from the L1 LSDB
! Metric = sum of wide metrics along the path (default 10 per Ethernet hop)
```

### End-to-End Reachability

```
R1# ping 10.0.0.3 source 10.0.0.1 repeat 5
!!!!!          ! ← Five exclamation marks = 100% success
               ! ← Source Loopback0 (10.0.0.1) → destination R3 Loopback0 (10.0.0.3)
```

---

## 7. Verification Cheatsheet

### IS-IS Process Configuration

```
router isis CORE
 net 49.0001.0000.0000.000X.00
 is-type level-1
 metric-style wide
 passive-interface Loopback0
```

| Command | Purpose |
|---------|---------|
| `router isis CORE` | Start IS-IS process tagged `CORE` (tag is locally significant) |
| `net 49.0001.0000.0000.000X.00` | Set the router's NET — area, system-ID, NSEL=00 |
| `is-type level-1` | Restrict the router to L1; suppresses L2 LSDB and Hellos |
| `metric-style wide` | Use wide metrics (modern, supports values > 63) |
| `passive-interface Loopback0` | Advertise the loopback into IS-IS but suppress Hello PDUs on it |

> **Exam tip:** IS-IS does **not** have a `network` statement like OSPF. Interfaces
> are enabled per-interface with `ip router isis <tag>` — forgetting this is the most
> common reason a prefix is missing from the LSDB even when the router process is up.

### Per-Interface Enablement

```
interface GigabitEthernet0/0
 ip router isis CORE
 isis circuit-type level-1
```

| Command | Purpose |
|---------|---------|
| `ip router isis CORE` | Enable IS-IS on this interface, tied to the named process |
| `isis circuit-type level-1` | Restrict the circuit to L1 Hellos (matches `is-type` here) |
| `isis hello-interval 3` | Set IIH to 3 s on this interface (default 10 s on LAN) |
| `isis hello-multiplier 4` | Hold time = hello × multiplier (here 12 s; default mult = 3) |

> **Exam tip:** `isis circuit-type` is per-interface; `is-type` is process-wide. They
> can disagree — for example a process-wide `level-1-2` router can run `level-1` only
> on a specific interface. Always check both when troubleshooting level mismatches.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | State must be Up; type column shows L1/L2/L1L2 |
| `show isis neighbors detail` | Area Address, IPv4 address, Holdtime (countdown), SNPA |
| `show clns interface Gi0/0` | DIS for each level on this circuit; circuit type; SNPA |
| `show running-config interface Gi0/0` | Configured `isis hello-interval` and `isis hello-multiplier` values |
| `show isis database` | List of LSPs; pseudonode LSPs (suffix non-`.00`) per LAN |
| `show isis database detail` | TLVs inside each LSP — area, hostname, IP prefixes, IS neighbours |
| `show ip route isis` | IS-IS-learned routes (i prefix, AD=115) |
| `ping X.X.X.X source Lo0` | End-to-end loopback reachability |

### NET Quick Reference

| NET | Decoded |
|-----|---------|
| `49.0001.0000.0000.0001.00` | AFI=49, area=0001, system-ID=0000.0000.0001, NSEL=00 |
| `49.0001.aaaa.bbbb.cccc.00` | Same area; system-ID can be any 6 unique bytes |
| `49.0002.0000.0000.0001.00` | **Different area** — would not form L1 with the routers above |

### Common IS-IS Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Stuck in INIT (Hellos seen but not UP) | Area ID in NET differs between neighbours (L1 only) — fix the NET |
| Adjacency never forms | `is-type` mismatch — e.g. one router is `level-2-only`, the other `level-1` |
| Adjacency never forms | `ip router isis` missing on the interface (not on every interface!) |
| Prefix missing from LSDB | Loopback or transit interface lacks `ip router isis` |
| MTU mismatch on LAN | LSP fragmentation problems — `show isis interface` reports the failure |
| Pseudonode LSP missing | Circuit configured as point-to-point (`isis network point-to-point`) — no DIS election on P2P |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS Process and Per-Interface Configuration

<details>
<summary>Click to view R1 configuration</summary>

```
router isis CORE
 net 49.0001.0000.0000.0001.00
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
<summary>Click to view R2 configuration</summary>

```
router isis CORE
 net 49.0001.0000.0000.0002.00
 is-type level-1
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis circuit-type level-1
```

</details>

<details>
<summary>Click to view R3 configuration</summary>

```
router isis CORE
 net 49.0001.0000.0000.0003.00
 is-type level-1
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
 isis circuit-type level-1
!
interface GigabitEthernet0/0
 ip router isis CORE
 isis circuit-type level-1
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show clns neighbors
show isis database
show isis database detail
show ip route isis
ping 10.0.0.3 source 10.0.0.1
```

</details>

### Task 4: Hello-Timer Tuning Solution

<details>
<summary>Click to view fast-timer and revert commands</summary>

```
! Apply fast timers on both sides simultaneously (R1 Gi0/0 and R2 Gi0/0):
interface GigabitEthernet0/0
 isis hello-interval 3
 isis hello-multiplier 4

! Revert to defaults:
interface GigabitEthernet0/0
 no isis hello-interval
 no isis hello-multiplier
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and
fix using only show commands and your knowledge of IS-IS.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                      # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>         # restore
```

---

### Ticket 1 — R3 Cannot Form an IS-IS Neighbour with R2

The NOC has alerted that 10.0.0.3/32 has disappeared from R1's routing table after a
maintenance window. R2 reports an IS-IS adjacency to R1 in state Up — but R3 is
nowhere to be seen on R2's neighbour list. R3 itself believes its IS-IS process is
up and is sending Hellos.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R2 shows R3 in state Up. `show ip
route isis` on R1 shows 10.0.0.3/32 via 10.1.12.2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R2# show clns neighbors
! R3 is missing or stuck in INIT — Hellos are arriving but the adjacency never reaches UP

R3# show clns neighbors
! Same view from R3 — R2 may be in INIT here too

R2# show isis neighbors detail
! Look at the Area Address(es) line for any partial neighbour entry
! INIT means the Hello passed Layer-2 checks but failed L1 area validation

R3# show running-config | section router isis
! Inspect the NET — is the area ID still 49.0001?
! L1 Hellos require an **exact** area-ID match. A single hex digit is enough to break it.
```

The fault is on **R3**: its NET was changed during maintenance and now reads
`49.0099.0000.0000.0003.00`. With a different area ID, R3 still sends and receives
Hellos but neither side can move the adjacency past INIT — L1 strictly requires
matching area addresses.
</details>

<details>
<summary>Click to view Fix</summary>

On R3:

```
router isis CORE
 no net 49.0099.0000.0000.0003.00
 net 49.0001.0000.0000.0003.00
```

Verify:

```
R3# show clns neighbors                  ! R2 reaches Up within ~30 s
R2# show clns neighbors                  ! R3 is now visible in state Up
R1# show ip route isis                   ! 10.0.0.3/32 reappears
```

</details>

---

### Ticket 2 — R1↔R2 Adjacency Flaps Continuously

The on-call engineer reports that the R1↔R2 adjacency keeps cycling between Up and
Init. The R2↔R3 adjacency is stable. The link itself is up at Layer 2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R2 shows R1 in state Up with stable
holdtime. `show isis neighbors detail` shows hello-interval 10 / hello-multiplier 3
on both sides of the R1↔R2 link.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R2# show clns neighbors
! R1 oscillates between Up and Init faster than the default 30 s hold

R2# show running-config interface GigabitEthernet0/0
! Look for isis hello-interval and isis hello-multiplier lines
! Absent lines = IOS defaults (10 s / multiplier 3) — check R1 too

R1# show running-config interface GigabitEthernet0/0
! If hello-interval or hello-multiplier differs from R2, the **hold time** advertised
! in R1's Hello becomes very short — R2's neighbour entry expires before the next Hello
```

The fault is on **R1**: the Gi0/0 interface has `isis hello-interval 1` and
`isis hello-multiplier 2` left over from a junior engineer's optimisation attempt.
The 2-second hold is shorter than the round-trip processing budget, so R2 sees
R1's neighbour entry expire just as the next Hello arrives — endless flap.
</details>

<details>
<summary>Click to view Fix</summary>

On R1:

```
interface GigabitEthernet0/0
 no isis hello-interval
 no isis hello-multiplier
```

Verify:

```
R1# show running-config interface GigabitEthernet0/0   ! no isis hello-interval / isis hello-multiplier lines (defaults restored)
R2# show clns neighbors                               ! R1 stays in state Up, holdtime resets near 30 s
```

</details>

---

### Ticket 3 — R2 Has Lost Both IS-IS Adjacencies

After a configuration push from the orchestration team, R2 is reporting zero IS-IS
neighbours. R1 and R3 are still configured correctly — they each show the other
side stuck in INIT. Layer-2 connectivity is fine and the IS-IS process on R2 is
running.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show clns neighbors` on R2 shows both R1 and R3 in state Up.
`show ip route isis` on R1 shows 10.0.0.3/32 again.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R2# show clns neighbors
! Empty — no neighbours at all

R2# show clns interface | include CLNS|level
! Are the interfaces still IS-IS-enabled? Check for "IS-IS is active" line

R2# show running-config | section router isis
! Look at is-type — has it been set to level-2-only?

R1# show clns neighbors
! R2 is in INIT here — Hellos arrive but the level field does not match
```

The fault is on **R2**: a configuration push set `is-type level-2-only` at the
process level. R2 now sends only L2 Hellos. R1 and R3 are L1-only, so the levels
never match and the adjacencies never leave INIT.
</details>

<details>
<summary>Click to view Fix</summary>

On R2:

```
router isis CORE
 is-type level-1
```

Verify:

```
R2# show clns neighbors                ! Both R1 and R3 reach state Up within ~30 s
R1# show ip route isis                 ! 10.0.0.3/32 returns via 10.1.12.2
R3# ping 10.0.0.1 source 10.0.0.3      ! End-to-end reachability restored
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] IS-IS process `CORE` with `is-type level-1` and `metric-style wide` active on R1, R2, and R3
- [x] R2 shows both R1 and R3 in state Up under `show clns neighbors`
- [x] `show isis database` lists three router LSPs and a pseudonode LSP for each broadcast LAN
- [x] DIS for each LAN identified and reasoning recorded (priority + SNPA, no router-ID tiebreaker)
- [x] `show ip route isis` on R1 shows 10.0.0.2/32, 10.0.0.3/32, and 10.1.23.0/24 (AD = 115)
- [x] `ping 10.0.0.3 source 10.0.0.1` succeeds from R1 (end-to-end loopback reachability)
- [x] All IIH timers restored to defaults (10 s / multiplier 3) before proceeding to lab-01

### Troubleshooting

- [x] Ticket 1 diagnosed and fixed (NET area-ID typo on R3)
- [ ] Ticket 2 diagnosed and fixed (hello-interval / hello-multiplier mismatch on R1 Gi0/0)
- [ ] Ticket 3 diagnosed and fixed (`is-type level-2-only` planted on R2)
- [ ] `apply_solution.py` run to confirm clean state before next lab

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success — all devices configured or restored | All scripts |
| 1 | Partial failure — one or more devices failed | `apply_solution.py` only |
| 2 | `--host` not provided (placeholder value detected) | All scripts |
| 3 | EVE-NG connectivity or port discovery error | All scripts |
