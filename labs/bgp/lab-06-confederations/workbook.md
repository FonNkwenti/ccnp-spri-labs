# BGP Lab 06 — BGP Confederations

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

**Exam Objective:** 1.4.a — BGP Confederations · 1.5.c — iBGP Scaling

BGP confederations solve the iBGP full-mesh problem by splitting a large autonomous system into smaller sub-autonomous systems, each of which runs iBGP internally and uses a lightweight form of eBGP — called confederation eBGP — between sub-ASes. External peers see only the confederation identifier (the public AS number), never the internal sub-AS structure.

### The iBGP Full-Mesh Problem

iBGP requires a full mesh: every iBGP router must peer with every other iBGP router because iBGP does not propagate routes learned from one iBGP peer to another. In a network with N iBGP routers, this requires N×(N−1)/2 sessions. Route Reflectors (Lab 01) solve this with a hierarchy; confederations solve it by subdivision.

### Confederation Components

| Concept | Description |
|---------|-------------|
| `bgp confederation identifier` | The public AS number shown to all external peers. Hides the internal structure. |
| `bgp confederation peers` | Declares which sub-ASes are confederation members. Required to classify confederation eBGP sessions correctly. |
| Sub-AS | A private AS (often in 64512–65534 range) used only within the confederation. |
| Confederation eBGP | eBGP peering between sub-ASes. Uses AS_CONFED_SEQUENCE instead of AS_PATH. |
| AS_CONFED_SEQUENCE | Path attribute that carries the sub-AS traversal history inside the confederation. Stripped before routes leave the confederation. |

### How Confederation eBGP Differs from Regular eBGP

Confederation eBGP behaves like regular eBGP in most respects:

- **Next-hop handling — platform-dependent:** RFC 5065 specifies that confederation eBGP should rewrite the next-hop to the peering interface address, just like regular eBGP. However, **Cisco IOS does not do this automatically** when the prefix was originally received from an external eBGP peer. The original external next-hop (e.g. the customer's interface IP) is preserved across the confederation boundary unless `next-hop-self` is explicitly configured. Always configure `next-hop-self` on confederation eBGP sessions where external next-hops need to be resolved by downstream routers.
- **BGP loop prevention** uses AS_CONFED_SEQUENCE (sub-AS numbers) rather than the AS_PATH. When the route leaves the confederation, the entire AS_CONFED_SEQUENCE is stripped and only the confederation identifier appears in the AS_PATH visible to external peers.
- **TTL is set to 1** by default (same as regular eBGP) — direct connections only unless `ebgp-multihop` is configured.

### next-hop-self Placement

| Session Type | next-hop-self needed? | Reason |
|---|---|---|
| Confederation eBGP (inter-sub-AS) | **Yes — on the PE advertising an external prefix** | Cisco IOS does NOT auto-rewrite the next-hop on confederation eBGP sessions. An external next-hop (e.g. 10.1.12.1) is preserved and becomes inaccessible to downstream sub-AS routers. |
| iBGP within sub-AS (full mesh) | Yes — on the PE facing the external eBGP peer | iBGP does NOT rewrite next-hop. Routers inside the sub-AS cannot resolve an external next-hop that is not in OSPF. |

In this lab:
- R2 and R3 each have `next-hop-self` toward each other (iBGP within sub-AS 65101) — so each PE sees the other's eBGP next-hop as a loopback, not as R1's IP
- **R2 has `next-hop-self` toward R4 (confederation eBGP)** — without it, R4 sees 172.16.1.0/24 with next-hop 10.1.12.1 (R1's interface IP, not in OSPF)
- **R3 has `next-hop-self` toward R4 (confederation eBGP)** — same reason; R4 would see next-hop 10.1.13.1 otherwise
- R4 has `next-hop-self` toward R5 (iBGP within sub-AS 65102) — so R5 sees R6's prefix with a reachable next-hop
- R5 has `next-hop-self` toward R4 — so R4 can resolve R6's prefix (10.1.56.6 is NOT in OSPF)

### AS-Path Behavior — What External Peers See

An external router (R1 or R6) sees only the confederation identifier 65100 in the AS_PATH, regardless of how many sub-ASes a route traversed. A route from R6 → R5 (65102) → R4 (65102) → R2 (65101) → R1 would show simply `65100` in R1's BGP table — the same result as a traditional single-AS SP.

```
R1# show ip bgp 172.16.6.0/24
  65100                     ← only the confederation identifier; sub-AS path stripped
```

---

## 2. Topology & Scenario

**Scenario:** Telco-SP "AS 65100" has grown its network and adopted a confederation design to scale iBGP without a full mesh. The SP is subdivided into two sub-ASes: sub-AS 65101 for the East PEs (R2, R3) and sub-AS 65102 for the SP Core and West PE (R4, R5). Customer A (R1, AS 65001) has two CE connections into the East PEs, and an external SP Peer (R6, AS 65002) peers with the West PE (R5). The NOC must build the confederation from scratch.

```
AS 65001                AS 65100 (confederation identifier)
                 ┌─────────────────────────────────────────────────────────┐
                 │  Sub-AS 65101               Sub-AS 65102               │   AS 65002
┌──────────┐ L1  │ ┌──────────┐           ┌──────────┐                   │
│    R1    ├─────┼─┤    R2    │  L3 confed│    R4    │  L5 iBGP          │
│  CE      │     │ │ PE East-1│ eBGP ─────┤ SP Core  ├────────────────┐  │
│ AS 65001 │     │ │ 10.0.0.2 ├─────────► │ 10.0.0.4 │                │  │
│ Lo1:     │     │ └────┬─────┘           └─────┬────┘                │  │
│172.16.1.1│     │      │ L6 iBGP               │ L4 confed eBGP      │  │
│          │  L2 │      │                        │                     │  │
└────┬─────┤─────┼─┐   ▼                         ▼                ┌───┴──┴───┐ L7  ┌──────────┐
     │     │     │ │ ┌──────────┐           ┌──────────┐          │    R5    ├─────┤    R6    │
     │     │     │ └►│    R3    │ L4 confed │    R4    │          │ PE West  │     │ Ext-SP   │
     │     │     │   │ PE East-2│ eBGP ─────►          │          │ 10.0.0.5 │     │ AS 65002 │
     │     │     │   │ 10.0.0.3 │           └──────────┘          │ CSR1000v │     │ 10.0.0.6 │
     └─────┘     │   └──────────┘                                 └──────────┘     │ Lo1:     │
  (L1 primary,   │   Sub-AS 65101                                 Sub-AS 65102     │172.16.6.1│
   L2 backup)    └─────────────────────────────────────────────────────────────────┘└─────────┘
```

**Session summary:**

| Session | Routers | Type | Link Used |
|---------|---------|------|-----------|
| L1 | R1 ↔ R2 | External eBGP (AS65001 ↔ AS65100) | 10.1.12.0/24 direct |
| L2 | R1 ↔ R3 | External eBGP (AS65001 ↔ AS65100) | 10.1.13.0/24 direct |
| L3 | R2 ↔ R4 | Confederation eBGP (65101 ↔ 65102) | 10.1.24.0/24 direct |
| L4 | R3 ↔ R4 | Confederation eBGP (65101 ↔ 65102) | 10.1.34.0/24 direct |
| L5 | R4 ↔ R5 | iBGP within sub-AS 65102 | Loopbacks via OSPF |
| L6 | R2 ↔ R3 | iBGP within sub-AS 65101 | Loopbacks via OSPF |
| L7 | R5 ↔ R6 | External eBGP (AS65100 ↔ AS65002) | 10.1.56.0/24 direct |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | AS / Sub-AS | Platform | Image |
|--------|------|-------------|----------|-------|
| R1 | Customer A CE | AS 65001 (external) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 | Sub-AS 65101 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 | Sub-AS 65101 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | SP Core | Sub-AS 65102 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West | Sub-AS 65102 | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer | AS 65002 (external) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A advertised prefix |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, iBGP peering source |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP peering source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id |
| R6 | Loopback1 | 172.16.6.1/24 | External SP peer prefix |

### Cabling Table

| Link | Source | Destination | Subnet | Purpose |
|------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | eBGP primary (Customer A) |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.1.13.0/24 | eBGP backup (Customer A) |
| L3 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/24 | Confederation eBGP + OSPF |
| L4 | R3 Gi0/1 | R4 Gi0/1 | 10.1.34.0/24 | Confederation eBGP + OSPF |
| L5 | R4 Gi0/2 | R5 Gi2 | 10.1.45.0/24 | iBGP (loopbacks) + OSPF |
| L6 | R2 Gi0/2 | R3 Gi0/2 | 10.1.23.0/24 | iBGP (loopbacks) + OSPF |
| L7 | R5 Gi3 | R6 Gi0/0 | 10.1.56.0/24 | eBGP (SP Peer) |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP network | Customer A; seen as AS 65001 65100 from R6 |
| R6 | 172.16.6.0/24 | eBGP network | External peer prefix; seen as AS 65100 65002 from R1 |

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
- Hostnames and `no ip domain-lookup` on all routers
- Interface IP addressing on all routed links and loopbacks
- OSPF area 0 on R2, R3, R4, R5 (IGP underlay for loopback reachability)
- R1 and R6 have NO OSPF — they are external to the SP confederation

**IS NOT pre-loaded** (student configures this):
- `router bgp <sub-AS>` and `bgp confederation identifier 65100` on R2, R3, R4, R5
- `bgp confederation peers` declaring the peer sub-AS on all SP routers
- iBGP full mesh within sub-AS 65101: R2↔R3 (loopback-based, `update-source Loopback0`, `next-hop-self`)
- iBGP within sub-AS 65102: R4↔R5 (loopback-based, `update-source Loopback0`, `next-hop-self`)
- Confederation eBGP between sub-ASes: R2↔R4 and R3↔R4 (direct link IPs, remote-as = peer sub-AS)
- External eBGP: R1↔R2, R1↔R3 (R1 uses `remote-as 65100`, the confederation identifier)
- External eBGP: R5↔R6 (R6 uses `remote-as 65100`, the confederation identifier)
- `network` statements to advertise prefixes from R1 and R6

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure Confederation Foundation — Identifier and Sub-AS Membership

On each SP router (R2, R3, R4, R5), configure:
- `router bgp <sub-AS>` — use sub-AS 65101 for R2/R3 and sub-AS 65102 for R4/R5
- `bgp confederation identifier 65100` — the public AS presented to external peers
- `bgp confederation peers <peer-sub-AS>` — declare the other sub-AS as a confederation member

This step alone does not establish any BGP sessions but is the prerequisite for all subsequent tasks. Without `bgp confederation peers`, IOS will treat the cross-sub-AS eBGP sessions as regular eBGP (carrying the sub-AS in the AS_PATH) rather than as confederation eBGP.

**Verification:** No neighbors have been configured at this stage — `show ip bgp summary` will not return any output. This task establishes the confederation foundation only; session verification begins in Task 2.

---

### Task 2: Establish iBGP Full Mesh Within Sub-AS 65101 (R2 ↔ R3)

Configure a loopback-based iBGP session between R2 and R3 (both in sub-AS 65101):
- Use `remote-as 65101` (same sub-AS = iBGP)
- Use `update-source Loopback0` on both sides
- Apply `next-hop-self` on both sides — this is required because iBGP does NOT rewrite the next-hop; R3 would receive R1's external eBGP next-hop (10.1.12.1) as-is, which is not reachable from R3 via OSPF

**Verification:** `show ip bgp neighbors 10.0.0.2 | include BGP state` on R3 must show `Established`; `show ip bgp neighbors 10.0.0.3 | include BGP state` on R2 must show `Established`.

---

### Task 3: Establish Confederation eBGP Between Sub-ASes (R2↔R4, R3↔R4)

Configure confederation eBGP sessions between sub-AS 65101 and sub-AS 65102:
- R2 peer toward R4: `neighbor 10.1.24.4 remote-as 65102` (direct link IP; R4 is in the peer sub-AS)
- R3 peer toward R4: `neighbor 10.1.34.4 remote-as 65102`
- R4 peer toward R2: `neighbor 10.1.24.2 remote-as 65101`
- R4 peer toward R3: `neighbor 10.1.34.3 remote-as 65101`
- **Configure `next-hop-self` on R2 toward R4 and on R3 toward R4.** Cisco IOS does not automatically rewrite the next-hop on confederation eBGP sessions. Without `next-hop-self`, R4 receives Customer A's prefix (172.16.1.0/24) with next-hop 10.1.12.1 (R1's interface IP), which is unreachable in the OSPF topology — R4 marks the route inaccessible and does not advertise it to R5. R4 does not need `next-hop-self` toward R2/R3 because R5 already rewrites the next-hop to its own loopback (10.0.0.5) when advertising toward R4, and that loopback is reachable via OSPF.

Because `bgp confederation peers 65102` is already configured on R2/R3 (Task 1), IOS classifies these as confederation eBGP sessions and uses AS_CONFED_SEQUENCE instead of AS_PATH for loop prevention within the confederation.

**Verification:** `show ip bgp summary` on R4 must show R2 (10.1.24.2) and R3 (10.1.34.3) as Established peers.

---

### Task 4: Establish iBGP Within Sub-AS 65102 (R4 ↔ R5)

Configure a loopback-based iBGP session between R4 and R5 (both in sub-AS 65102):
- Use `remote-as 65102` (same sub-AS = iBGP)
- Use `update-source Loopback0` on both sides
- Apply `next-hop-self` on both sides — R5 is the egress toward R6 (10.1.56.0/24 is NOT in OSPF); without next-hop-self, R4 would receive R6's prefix with next-hop 10.1.56.6, which is unresolvable in the OSPF topology

**Verification:** `show ip bgp neighbors 10.0.0.4 | include BGP state` on R5 must show `Established`.

---

### Task 5: Establish External eBGP and Verify End-to-End Prefix Exchange

Configure the external eBGP sessions:
- R2: `neighbor 10.1.12.1 remote-as 65001` (Customer A primary)
- R3: `neighbor 10.1.13.1 remote-as 65001` (Customer A backup)
- R1: `neighbor 10.1.12.2 remote-as 65100` and `neighbor 10.1.13.3 remote-as 65100` — R1 peers to the **confederation identifier** 65100, not the sub-AS
- R5: `neighbor 10.1.56.6 remote-as 65002`
- R6: `neighbor 10.1.56.5 remote-as 65100` — R6 also peers to the confederation identifier

Advertise prefixes:
- R1: `network 172.16.1.0 mask 255.255.255.0`
- R6: `network 172.16.6.0 mask 255.255.255.0`

**Verification:** Use `show ip bgp 172.16.1.0/24` on R6 (detailed view — AS_PATH appears as the first unlabeled line; table view shows in Path column) to confirm AS_PATH contains only `65001 65100` (sub-AS numbers stripped from external view). Use `show ip bgp 172.16.6.0/24` on R1 to verify AS_PATH shows only `65100 65002` (confederation identifier + external AS).

---

## 6. Verification & Analysis

### Task 1 — Confederation Foundation

No neighbors have been configured yet, so `show ip bgp summary` will not return any output at this stage. There is nothing to verify here — the confederation foundation commands are a prerequisite for subsequent tasks, not an independently observable state.

### Task 2 — iBGP within Sub-AS 65101 (R2 ↔ R3)

```
R2# show ip bgp neighbors 10.0.0.3 | include BGP state
BGP state = Established, up for 00:01:20              ! ← iBGP session up via loopback

R2# show ip bgp neighbors 10.0.0.3 | include next.hop
  Next-hop-self enabled                               ! ← next-hop-self active on iBGP
```

### Task 3 — Confederation eBGP (R2↔R4, R3↔R4)

```
R4# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.24.2       4 65101      12      12        3    0    0 00:02:10        0
10.1.34.3       4 65101      11      11        3    0    0 00:02:05        0
                                                 ! ← Both confederation eBGP peers Established
                                                 ! ← AS shown as 65101 (sub-AS, not 65100)

R2# show ip bgp neighbors 10.1.24.4 | include confederation
  Member of confederation: 65100 sub-AS: 65101
  Neighbor is a confederation external peer  ! ← IOS correctly classifies as conf-eBGP
```

### Task 4 — iBGP within Sub-AS 65102 (R4 ↔ R5)

```
R5# show ip bgp neighbors 10.0.0.4 | include BGP state
BGP state = Established, up for 00:01:45             ! ← iBGP within sub-AS 65102 up

R5# show ip bgp neighbors 10.0.0.4 | include next.hop
  Next-hop-self enabled                              ! ← next-hop-self active
```

### Task 5 — External eBGP and End-to-End Reachability

```
! R6 sees Customer A prefix — AS_PATH shows only confederation identifier, not sub-ASes
R6# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 5
Paths: (1 available, best #1, table default)
  65001
    10.1.56.5 from 10.1.56.5 (10.0.0.5)
      Origin IGP, localpref 100, valid, external, best
      AS_PATH: 65100 65001               ! ← only 65100 visible; sub-AS path stripped

! R1 sees SP Peer prefix — same AS-path hiding
R1# show ip bgp 172.16.6.0/24
  AS_PATH: 65100 65002                   ! ← 65100 is the only confederation hop visible

! Confederation AS_CONFED_SEQUENCE visible WITHIN the SP
R4# show ip bgp 172.16.1.0/24
  65001
    10.1.24.2 from 10.1.24.2 (10.0.0.2)
      AS_PATH: (65101) 65001             ! ← (65101) = AS_CONFED_SEQUENCE; parentheses indicate conf-eBGP hops

R5# show ip bgp 172.16.1.0/24
  65001
    10.0.0.4 (metric 2) from 10.0.0.4 (10.0.0.4)
      AS_PATH: (65101) 65001             ! ← only confed-eBGP hops appear; R4→R5 is iBGP (no prepend)
```

---

## 7. Verification Cheatsheet

### Confederation Configuration Commands

```
router bgp <sub-AS>
 bgp confederation identifier <public-AS>
 bgp confederation peers <peer-sub-AS>
```

| Command | Purpose |
|---------|---------|
| `bgp confederation identifier 65100` | Sets public AS shown to external peers |
| `bgp confederation peers 65102` | Declares 65102 as a confederation member (enables conf-eBGP treatment) |
| `neighbor X remote-as <sub-AS>` | iBGP within sub-AS (same sub-AS number) |
| `neighbor X remote-as <peer-sub-AS>` | Confederation eBGP (different sub-AS, must be in confederation peers) |
| `neighbor X update-source Loopback0` | Required for iBGP over loopbacks |
| `neighbor X next-hop-self` | Required on iBGP sessions where external next-hops are unreachable; also required on confederation eBGP sessions on Cisco IOS where external prefixes are being advertised across sub-AS boundaries |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp summary` | Shows `local AS number <sub-AS>`, `Confederation identifier: 65100`, `Confederation peers: <list>` |
| `show ip bgp neighbors X \| include confederation` | Confirms session classified as `confederation external peer` vs `internal` |
| `show ip bgp <prefix>` (detailed view) | Inside confederation: `AS_PATH: (65101) 65001` shows AS_CONFED_SEQUENCE in parentheses (AS_PATH is first unlabeled line) |
| `show ip bgp <prefix>` (detailed view) | At external peer: `AS_PATH: 65100 65001` — sub-AS numbers stripped, only public ID visible (first unlabeled line) |
| `show ip bgp` (table view) | AS_PATH column shows same values as detailed view; use table view for clearer at-a-glance AS_PATH comparison |
| `show ip bgp neighbors X \| include next.hop` | Confirms `Next-hop-self enabled` on iBGP sessions |

> **Exam tip:** In detailed view (`show ip bgp <prefix>`), AS_PATH appears as the **first unlabeled line** of the path block. In table view (`show ip bgp`), AS_PATH appears in a labeled **Path** column — use table view for rapid verification of AS_PATH values across multiple routes.

### Confederation Session Classification

IOS classifies a BGP session based on the `bgp confederation peers` declaration:

| Condition | Session Type | next-hop behavior | Loop prevention |
|---|---|---|---|
| `remote-as` = own sub-AS | iBGP | Preserved (use next-hop-self) | MED, local-pref |
| `remote-as` in `confederation peers` | Confederation eBGP | **Not auto-rewritten on Cisco IOS** — use `next-hop-self` when advertising external prefixes | AS_CONFED_SEQUENCE |
| `remote-as` not in confederation peers | Regular eBGP | Rewritten to peering IP | AS_PATH |

> **Exam tip:** If `bgp confederation peers` is missing, IOS treats cross-sub-AS sessions as regular eBGP and the sub-AS number leaks into the AS_PATH seen by external peers — this is the most common confederation misconfiguration.

### Common Confederation Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| External peer sees sub-AS (65101/65102) in AS-path | `bgp confederation peers` missing on one or both SP routers |
| External eBGP session to PE is Idle; customer loses primary path but backup path (via another PE) still works | `bgp confederation identifier` missing on the PE — it presents its sub-AS (e.g. 65101) in BGP OPEN; the CE has `remote-as 65100`, causing an AS mismatch and session rejection |
| Confederation eBGP session stuck in Active | `bgp confederation peers` missing; IOS treats it as regular eBGP (TTL=1 still works for direct links, but AS classification is wrong) |
| Route learned via confederation eBGP not forwarded across sub-AS | `bgp confederation identifier` missing on one router |
| R4 shows Customer A prefix with inaccessible next-hop (10.1.12.1 or 10.1.13.1) | `next-hop-self` missing on R2 or R3 toward R4 — confederation eBGP does NOT auto-rewrite next-hop on Cisco IOS; the original external IP leaks across the sub-AS boundary |
| Route received by iBGP peer has unreachable next-hop | `next-hop-self` missing on the PE that faces the external eBGP peer |
| R4 cannot reach R6's prefix (172.16.6.0/24) | `next-hop-self` missing on R5 toward R4 (10.1.56.6 not in OSPF) |
| R3 cannot learn R1's routes | R2↔R3 iBGP session down or `next-hop-self` missing |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Confederation Foundation

<details>
<summary>Click to view R2 Configuration</summary>

```bash
router bgp 65101
 bgp router-id 10.0.0.2
 bgp log-neighbor-changes
 bgp confederation identifier 65100
 bgp confederation peers 65102
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
router bgp 65101
 bgp router-id 10.0.0.3
 bgp log-neighbor-changes
 bgp confederation identifier 65100
 bgp confederation peers 65102
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
router bgp 65102
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 bgp confederation identifier 65100
 bgp confederation peers 65101
```
</details>

<details>
<summary>Click to view R5 Configuration (CSR1000v)</summary>

```bash
router bgp 65102
 bgp router-id 10.0.0.5
 bgp log-neighbor-changes
 bgp confederation identifier 65100
 bgp confederation peers 65101
```
</details>

---

### Task 2: iBGP Full Mesh Within Sub-AS 65101 (R2 ↔ R3)

<details>
<summary>Click to view R2 Configuration</summary>

```bash
router bgp 65101
 neighbor 10.0.0.3 remote-as 65101
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.3 next-hop-self
 !
 address-family ipv4
  neighbor 10.0.0.3 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
router bgp 65101
 neighbor 10.0.0.2 remote-as 65101
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.0.0.2 next-hop-self
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R2# show ip bgp neighbors 10.0.0.3 | include BGP state
R3# show ip bgp neighbors 10.0.0.2 | include BGP state
```
</details>

---

### Task 3: Confederation eBGP Between Sub-ASes (R2↔R4, R3↔R4)

<details>
<summary>Click to view R2 Configuration</summary>

```bash
router bgp 65101
 neighbor 10.1.24.4 remote-as 65102
 neighbor 10.1.24.4 next-hop-self
 !
 address-family ipv4
  neighbor 10.1.24.4 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
router bgp 65101
 neighbor 10.1.34.4 remote-as 65102
 neighbor 10.1.34.4 next-hop-self
 !
 address-family ipv4
  neighbor 10.1.34.4 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
router bgp 65102
 neighbor 10.1.24.2 remote-as 65101
 neighbor 10.1.34.3 remote-as 65101
 !
 address-family ipv4
  neighbor 10.1.24.2 activate
  neighbor 10.1.34.3 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R4# show ip bgp summary
R2# show ip bgp neighbors 10.1.24.4 | include confederation
R3# show ip bgp neighbors 10.1.34.4 | include confederation
```
</details>

---

### Task 4: iBGP Within Sub-AS 65102 (R4 ↔ R5)

<details>
<summary>Click to view R4 Configuration</summary>

```bash
router bgp 65102
 neighbor 10.0.0.5 remote-as 65102
 neighbor 10.0.0.5 update-source Loopback0
 neighbor 10.0.0.5 next-hop-self
 !
 address-family ipv4
  neighbor 10.0.0.5 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
router bgp 65102
 neighbor 10.0.0.4 remote-as 65102
 neighbor 10.0.0.4 update-source Loopback0
 neighbor 10.0.0.4 next-hop-self
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R4# show ip bgp neighbors 10.0.0.5 | include BGP state
R5# show ip bgp neighbors 10.0.0.4 | include BGP state
```
</details>

---

### Task 5: External eBGP Sessions and End-to-End Verification

<details>
<summary>Click to view R1 Configuration</summary>

```bash
router bgp 65001
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65100
 neighbor 10.1.13.3 remote-as 65100
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  neighbor 10.1.12.2 activate
  neighbor 10.1.13.3 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 External eBGP Addition</summary>

```bash
router bgp 65101
 neighbor 10.1.12.1 remote-as 65001
 !
 address-family ipv4
  neighbor 10.1.12.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 External eBGP Addition</summary>

```bash
router bgp 65101
 neighbor 10.1.13.1 remote-as 65001
 !
 address-family ipv4
  neighbor 10.1.13.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 External eBGP Addition</summary>

```bash
router bgp 65102
 neighbor 10.1.56.6 remote-as 65002
 !
 address-family ipv4
  neighbor 10.1.56.6 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R6 Configuration</summary>

```bash
router bgp 65002
 bgp router-id 10.0.0.6
 bgp log-neighbor-changes
 neighbor 10.1.56.5 remote-as 65100
 !
 address-family ipv4
  network 172.16.6.0 mask 255.255.255.0
  neighbor 10.1.56.5 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R6# show ip bgp 172.16.1.0/24    ! AS_PATH must show: 65100 65001 (not 65102 65101 65001)
R1# show ip bgp 172.16.6.0/24    ! AS_PATH must show: 65100 65002
R4# show ip bgp 172.16.1.0/24    ! AS_PATH: (65101) 65001  — AS_CONFED_SEQUENCE in parens
R5# show ip bgp 172.16.1.0/24    ! AS_PATH: (65102 65101) 65001 — both sub-AS hops visible
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                            # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>      # restore
```

---

### Ticket 1 — R1 Loses the Primary Path to External SP Peer (R1↔R2 Session Down)

The NOC reports that Customer A's router (R1) can no longer reach the external SP peer prefix via the primary PE (R2). BGP monitoring shows R1 has only a single path to 172.16.6.0/24, sourced exclusively from R3. The R1↔R2 eBGP session is in Idle.

**Root cause:** When `bgp confederation identifier 65100` is removed from R2, R2 presents itself as AS 65101 in BGP OPEN messages. R1 has `neighbor 10.1.12.2 remote-as 65100` — the AS numbers do not match, so the session is refused and stays Idle. R1 falls back to the single path via R3.

**Symptom:** `show ip bgp summary` on R1 shows neighbor 10.1.12.2 (R2) in `Idle` state; `show ip bgp 172.16.6.0/24` on R1 shows only one path (via 10.1.13.3, R3).

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp summary` on R1 shows 10.1.12.2 as `Established` with `PfxRcd: 1`; `show ip bgp 172.16.6.0/24` on R1 shows two paths (via 10.1.12.2 and 10.1.13.3).

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check R1's session state — which PE session is down?
R1# show ip bgp summary
! Look for Idle in State/PfxRcd — if 10.1.12.2 is Idle, R2 is rejecting the session

! 2. Check how many paths R1 has for 172.16.6.0/24
R1# show ip bgp 172.16.6.0/24
! Only one path (via 10.1.13.3) means R2's eBGP session is not contributing routes

! 3. Determine why R2 is refusing R1 — check what AS R2 is presenting
R2# show ip bgp summary
! Look for: "local AS number 65101" and "Confederation identifier: 65100"
! If "Confederation identifier" line is ABSENT, R2 is presenting itself as AS 65101
! R1 expects remote-as 65100 — AS mismatch → session rejected

! 4. Confirm confederation identifier is missing
R2# show running-config | include confederation identifier
! If no output: bgp confederation identifier 65100 has been removed

! 5. Confirm confederation peers is intact (not the fault, but verify)
R2# show running-config | include confederation peers
! Must show: bgp confederation peers 65102
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: bgp confederation identifier 65100 removed from R2
! Effect: R2 presents itself as AS 65101 in BGP OPEN; R1 expects remote-as 65100
!         AS mismatch → R1↔R2 session stays Idle → R1 loses the primary path

R2(config)# router bgp 65101
R2(config-router)# bgp confederation identifier 65100
R2(config-router)# end

! Verify:
R1# show ip bgp summary
! 10.1.12.2 must now show Established and PfxRcd: 1

R1# show ip bgp 172.16.6.0/24
! Must show two paths: one via 10.1.12.2 (R2) and one via 10.1.13.3 (R3)
```
</details>

---

### Ticket 2 — R3 Cannot Learn Customer A Routes

The NOC reports that PE East-2 (R3) has no entry for 172.16.1.0/24 in its BGP table. R3 has a direct eBGP session with Customer A (R1) via L2, but Customer A's routes that enter the SP via R2 (the primary path) are not visible on R3.

**Symptom:** `show ip bgp 172.16.1.0/24` on R3 shows only the path via R3's own eBGP session (10.1.13.1), NOT the path via R2 (10.0.0.2). `show ip bgp summary` on R3 shows the iBGP session toward R2 as Active or absent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R3 shows two paths: one from 10.1.13.1 (direct eBGP) and one from 10.0.0.2 (iBGP via R2). `show ip bgp summary` on R3 shows R2 (10.0.0.2) as Established.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check whether R3 has an iBGP session toward R2
R3# show ip bgp summary
! Look for 10.0.0.2 in the neighbor list — if absent, neighbor statement was removed

! 2. Check R3's running config for the neighbor declaration
R3# show running-config | section router bgp
! Must include: neighbor 10.0.0.2 remote-as 65101

! 3. If session is present but down, check update-source
R3# show ip bgp neighbors 10.0.0.2 | include source
! Must show: update-source Loopback0

! 4. Confirm Loopback0 is reachable
R3# show ip ospf neighbor
! R2's loopback (10.0.0.2) must be learned via OSPF
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: neighbor 10.0.0.2 removed from R3's router bgp 65101
! Effect: R3 loses the iBGP session to R2; R2's routes (including those received from R1 primary) are invisible to R3

R3(config)# router bgp 65101
R3(config-router)# neighbor 10.0.0.2 remote-as 65101
R3(config-router)# neighbor 10.0.0.2 update-source Loopback0
R3(config-router)# neighbor 10.0.0.2 next-hop-self
R3(config-router)# address-family ipv4
R3(config-router-af)# neighbor 10.0.0.2 activate
R3(config-router-af)# end

! Verify:
R3# show ip bgp neighbors 10.0.0.2 | include BGP state    ! must show Established
R3# show ip bgp 172.16.1.0/24                             ! must show path via 10.0.0.2
```
</details>

---

### Ticket 3 — R4 Cannot Reach R6's Prefix (172.16.6.0/24)

The SP core (R4) has 172.16.6.0/24 in its BGP table but the route shows as invalid (no `>` best marker). Traffic from the SP core toward the external SP peer prefix is black-holing. R5 has a valid eBGP session with R6 and the prefix is in R5's table with a valid next-hop.

**Symptom:** `show ip bgp 172.16.6.0/24` on R4 shows the prefix but next-hop 10.1.56.6 is not reachable (`show ip bgp 172.16.6.0/24` on R4 shows inaccessible next-hop). R5 shows the prefix as valid.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.6.0/24` on R4 shows `>` (best) with next-hop pointing to R5's loopback (10.0.0.5, via OSPF). `show ip bgp 172.16.6.0/24` on R1 shows the prefix via R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check R4's view of 172.16.6.0/24
R4# show ip bgp 172.16.6.0/24
! Look at the next-hop address — if it shows 10.1.56.6, next-hop-self is missing on R5

! 2. Check if 10.1.56.6 is reachable via OSPF
R4# show ip route 10.1.56.6
! Must return: network not in table — 10.1.56.0/24 is NOT advertised into OSPF by R5

! 3. Check R5's iBGP session toward R4
R5# show ip bgp neighbors 10.0.0.4 | include next.hop
! Must show: Next-hop-self enabled
! If absent, next-hop-self was removed

! 4. Confirm R5's BGP config for the R4 neighbor
R5# show running-config | section router bgp
! Must include: neighbor 10.0.0.4 next-hop-self
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: next-hop-self removed from R5's iBGP session toward R4
! Effect: R5 advertises 172.16.6.0/24 to R4 with next-hop = 10.1.56.6 (R6's link address)
! 10.1.56.0/24 is NOT in OSPF, so R4 cannot resolve the next-hop → route is unusable

R5(config)# router bgp 65102
R5(config-router)# neighbor 10.0.0.4 next-hop-self
R5(config-router)# end
R5# clear ip bgp 10.0.0.4 soft out

! Verify:
R4# show ip bgp 172.16.6.0/24
! Next Hop must now be 10.0.0.5 (R5's loopback, reachable via OSPF)
! Route must have > (best) marker
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `bgp confederation identifier 65100` configured on R2, R3, R4, R5
- [ ] `bgp confederation peers 65102` configured on R2 and R3
- [ ] `bgp confederation peers 65101` configured on R4 and R5
- [ ] R2↔R3 iBGP session Established (loopback-based, `next-hop-self` on both)
- [ ] R2↔R4 confederation eBGP session Established (direct link)
- [ ] R3↔R4 confederation eBGP session Established (direct link)
- [ ] R4↔R5 iBGP session Established (loopback-based, `next-hop-self` on both)
- [ ] R1↔R2 external eBGP Established; R1 uses `remote-as 65100`
- [ ] R1↔R3 external eBGP Established; R1 uses `remote-as 65100`
- [ ] R5↔R6 external eBGP Established; R6 uses `remote-as 65100`
- [ ] `show ip bgp 172.16.1.0/24` on R6: AS_PATH shows `65100 65001` (sub-AS stripped)
- [ ] `show ip bgp 172.16.6.0/24` on R1: AS_PATH shows `65100 65002` (sub-AS stripped)
- [ ] `show ip bgp 172.16.1.0/24` on R4: AS_PATH shows `(65101) 65001` (AS_CONFED_SEQUENCE)
- [ ] `show ip bgp 172.16.1.0/24` on R5: AS_PATH shows `(65101) 65001` (R4→R5 is iBGP — no sub-AS prepend)

### Troubleshooting

- [ ] Ticket 1 resolved: `bgp confederation identifier 65100` restored on R2; R1↔R2 session Established; R1 shows two paths to 172.16.6.0/24
- [ ] Ticket 2 resolved: R2↔R3 iBGP restored on R3; R3 sees R2's learned routes
- [ ] Ticket 3 resolved: `next-hop-self` restored on R5 toward R4; R4 can forward to R6's prefix

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure (one or more devices failed) | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed (lab nodes not started) | Inject scripts only |

---

## 12. Appendix: Same Tasks on IOS-XR

This lab boots IOSv only. For the XR equivalent of a BGP confederation
sub-AS member, see:

- `solutions-xr/R3.cfg` — full XR equivalent of `solutions/R3.cfg`
  (sub-AS 65101 boundary router with confed-eBGP toward sub-AS 65102)

Highlights of the XR translation:

- `bgp confederation identifier 65100` and `bgp confederation peers 65102`
  use the **same keywords** as IOS, inside `router bgp <sub-as>`
- `next-hop-self` is **per-AF** in XR (under the neighbor's
  `address-family ipv4 unicast` block), not a global neighbor knob
- Confed-eBGP next-hop behavior matches IOS — XR does **not** auto-rewrite
  next-hop on confed-eBGP, so `next-hop-self` is still required toward the
  other sub-AS
- A `route-policy PASS` is mandatory on every activated AF — XR drops
  prefixes silently without an explicit policy

The XR file is a side-by-side read, **not booted** as part of this lab. To
exercise it on real hardware, see the XR-mixed retrofit of
`bgp/lab-07-capstone-config` or the `xr-bridge` bonus topic.
