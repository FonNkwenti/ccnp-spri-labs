# Lab 00 — Dual-CE iBGP Architecture and Baseline

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

**Exam Objective:** 1.5.d — Multihoming (300-510)

This lab establishes the architectural foundation for the entire dual-CE topic series. The
existing BGP topic (labs 00-08) covers a single CE with two uplinks into one provider — a
common pattern, but not the only one. When a customer deploys **two CE routers in the same
AS**, each peering with a **different upstream ISP**, several requirements emerge that are
not present in the single-CE model. This lab builds the minimum viable dual-CE topology and
proves the most fundamental of those requirements: **CE-to-CE iBGP is mandatory.**

---

### The Dual-CE Problem

Consider the customer perspective. R1 and R2 sit in AS 65001. R1 peers eBGP with ISP-A
(R3 in AS 65100); R2 peers eBGP with ISP-B (R4 in AS 65200). Without anything else,
each CE only learns the prefixes from its own upstream:

| CE  | Learns from eBGP                          | Does NOT see                           |
|-----|-------------------------------------------|----------------------------------------|
| R1  | 10.100.1.0/24 (from R3, ISP-A)            | 10.200.1.0/24 (only known to R2)       |
| R2  | 10.200.1.0/24 (from R4, ISP-B)            | 10.100.1.0/24 (only known to R1)       |

If a host sitting behind R1 tries to reach 10.200.1.0/24, R1 has no BGP route for it. The
packet is dropped or sent out a default — neither acceptable for a customer paying for
two transit links. The customer AS is internally fragmented.

**The solution is iBGP between R1 and R2.** Each CE re-advertises its eBGP-learned prefixes
to its peer over an internal session, so both CEs converge on a complete BGP table.

---

### Why iBGP Loopback Peering on a Single Link

R1 and R2 share exactly one direct link (10.1.12.0/30). A student's first instinct is to
peer iBGP using those interface IPs — it works, the session comes up, and there is no IGP
to configure. The problem is **session identity is bound to the interface**: if Gi0/1 on
R1 flaps, the iBGP session drops even when the router is otherwise fine. More importantly,
this lab builds a foundation that the rest of the dual-CE series extends; in real
multi-link CE deployments and in lab-04's capstone, the customer site grows to multiple
inter-CE paths and the session must survive any single link failure.

Loopback-based peering decouples session identity from physical-interface state. Loopback0
is always Up/Up while the router is powered. The session terminates on a stable address
that does not change when interfaces are added, removed, or fail. This is the universal
SP convention, and it is the convention this series teaches from lab-00 onward.

The cost is one piece of plumbing: each CE needs a route to the peer's Loopback0. Because
this lab introduces no IGP — the CEs will run BGP only — that route is supplied by a
single static entry per CE pointing the peer's loopback at the directly connected
interface IP.

---

### Why next-hop-self on the iBGP Session

When R1 receives 10.100.1.0/24 from R3 (ISP-A) over eBGP, the BGP next-hop attribute is
set to R3's interface address on the shared subnet: 10.1.13.2. R1 then advertises that
route over iBGP to R2. By default, **iBGP does not change the next-hop attribute** — R2
receives 10.100.1.0/24 with next-hop 10.1.13.2.

R2 has no route to 10.1.13.2. That subnet is on the ISP-A side of R1, completely outside
the customer AS. The route enters R2's BGP table but cannot be installed in the RIB
because the next-hop is unresolvable. R2 cannot forward to 10.100.1.0/24.

The fix is `neighbor 10.0.0.2 next-hop-self` on R1's iBGP configuration. R1 rewrites the
next-hop to its own Loopback0 (10.0.0.1) when advertising over iBGP. R2 has a static
route to 10.0.0.1 (the loopback peering plumbing), so the route resolves and installs.
The same fix is applied on R2 for its eBGP-learned ISP-B prefixes advertised back to R1.

---

### How This Lab Differs From `bgp/lab-00`

The `bgp` series uses a single SP with multiple PEs, an OSPF underlay, and one customer CE.
This series uses **two separate ISP ASes**, **no IGP** (CEs run BGP only), and **two CEs in
the same customer AS**. Both patterns satisfy blueprint bullet 1.5.d (Multihoming), but the
operational implications diverge sharply from this point on:

- This series will require **transit prevention** (lab-01) — the customer AS is
  topologically between two providers and will leak transit by default.
- **MED is useless across two ISP ASes** (lab-02) — AS-path prepend is the only inbound TE
  lever.
- **Selective prefix advertisement** (lab-03) splits the customer /24 into two /25s, one
  per ISP — a pattern impossible with a single CE.

This lab plants the seed: the iBGP session, the loopback peering, the next-hop-self. Every
subsequent lab in this series builds on it.

**Skills this lab develops:**

| Skill | Description |
|---|---|
| Dual-CE eBGP bring-up | Configuring two independent customer-to-ISP eBGP sessions in the same AS |
| Loopback reachability via static | Establishing peer loopback reachability without an IGP |
| iBGP loopback peering | Using `update-source Loopback0` between two CEs on a single direct link |
| next-hop-self on CE-CE iBGP | Replacing eBGP next-hops so the peer CE can resolve forwarding addresses |
| Customer prefix origination from two CEs | Advertising 192.168.1.0/24 from R1 (Lo1) and R2 (Null0 + network) |
| Routing-gap diagnosis | Recognizing the symptom of missing CE-CE iBGP before fixing it |

---

## 2. Topology & Scenario

**Scenario:** You have just been hired by a regional enterprise that runs a small customer
AS (65001) connected to two upstream ISPs for redundancy. R1 (CE1) is cabled to ISP-A's
edge router (R3, AS 65100). R2 (CE2) is cabled to ISP-B's edge router (R4, AS 65200). The
two CEs are also directly cabled to each other on link L3. The previous engineer brought
up the eBGP sessions and proved each CE has a route to its own ISP's representative
prefix — but reports came in that hosts behind R1 could not reach destinations on
ISP-B's network, and vice versa. Your job is to diagnose the routing gap, then close it
by configuring CE-to-CE iBGP with proper loopback peering and next-hop handling.

```
       AS 65100                AS 65001 (Customer)                AS 65200
   ┌────────────┐    ┌───────────────────────────────────┐    ┌────────────┐
   │     R3     │    │   ┌────────┐  L3   ┌────────┐     │    │     R4     │
   │ ISP-A PE   │L1──┼───┤   R1   ├───────┤   R2   ├─────┼─L2─┤ ISP-B PE   │
   │ AS 65100   │    │   │  CE1   │       │  CE2   │     │    │ AS 65200   │
   │ Lo0:10.0.0.3│    │   │AS 65001│       │AS 65001│     │    │Lo0:10.0.0.4│
   │ Lo1:        │    │   │Lo0:    │       │Lo0:    │     │    │ Lo1:        │
   │ 10.100.1.0  │    │   │10.0.0.1│       │10.0.0.2│     │    │ 10.200.1.0  │
   └────────────┘    │   │ Lo1:   │       │(no Lo1)│     │    └────────────┘
                     │   │192.168.│       │        │     │
                     │   │ 1.0/24 │       │        │     │
                     │   └────────┘       └────────┘     │
                     └───────────────────────────────────┘
```

**Key relationships for lab-00:**

- R1↔R3 (L1, 10.1.13.0/30): eBGP AS 65001 ↔ AS 65100 — CE1 to ISP-A.
- R2↔R4 (L2, 10.1.24.0/30): eBGP AS 65001 ↔ AS 65200 — CE2 to ISP-B.
- R1↔R2 (L3, 10.1.12.0/30): The single direct link between the two CEs. Used for two
  things: (1) static-route plumbing to reach each peer's Loopback0, and (2) the iBGP TCP
  session, which is sourced from Loopback0 on each end.
- iBGP R1↔R2 (10.0.0.1 ↔ 10.0.0.2): The session that closes the routing gap. Each side
  applies next-hop-self so eBGP-learned next-hops are rewritten to the local Loopback0.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer CE1 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Customer CE2 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | ISP-A PE (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | ISP-B PE (AS 65200) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id, iBGP peering source |
| R1 | Loopback1 | 192.168.1.1/24 | Customer PI prefix (physical representation) |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id |
| R3 | Loopback1 | 10.100.1.1/24 | ISP-A representative prefix |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id |
| R4 | Loopback1 | 10.200.1.1/24 | ISP-B representative prefix |

R2 has no Loopback1 — the customer /24 is originated from a `Null0` static + `network`
statement, demonstrating the standard PI-prefix advertisement pattern when no local
interface anchors the prefix.

### Cabling Table

| Link ID | Source | Interface | Target | Interface | Subnet |
|---------|--------|-----------|--------|-----------|--------|
| L1 | R1 | Gi0/0 | R3 | Gi0/0 | 10.1.13.0/30 |
| L2 | R2 | Gi0/0 | R4 | Gi0/0 | 10.1.24.0/30 |
| L3 | R1 | Gi0/1 | R2 | Gi0/1 | 10.1.12.0/30 |

### Advertised Prefixes

| Device | Prefix | Source | Notes |
|--------|--------|--------|-------|
| R1 | 192.168.1.0/24 | Lo1 (connected) | Customer PI; physically represented on R1 |
| R2 | 192.168.1.0/24 | Null0 static | Customer PI; same prefix originated for redundancy |
| R3 | 10.100.1.0/24 | Lo1 (connected) | ISP-A representative prefix |
| R4 | 10.200.1.0/24 | Lo1 (connected) | ISP-B representative prefix |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames (R1, R2, R3, R4)
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all devices

**IS NOT pre-loaded** (student configures this):
- eBGP sessions: R1↔R3 (AS 65001 ↔ AS 65100) and R2↔R4 (AS 65001 ↔ AS 65200)
- BGP prefix advertisements: 192.168.1.0/24 from R1 and R2; 10.100.1.0/24 from R3;
  10.200.1.0/24 from R4
- Null0 static on R2 (so the BGP `network` statement can install the customer /24)
- Static routes for iBGP loopback reachability (10.0.0.1/32 and 10.0.0.2/32 between
  the two CEs)
- iBGP session R1↔R2 with `update-source Loopback0` and `next-hop-self`

---

## 5. Lab Challenge: Core Implementation

This lab is structured in two phases. Phase 1 brings up eBGP only and asks you to
**observe the routing gap** between the two CEs. Phase 2 closes the gap by configuring
CE-to-CE iBGP. The point of the split is pedagogical: the gap is the reason iBGP is
mandatory in this architecture, and seeing it in `show ip bgp` output is more memorable
than reading about it.

### Phase 1 — Establish the eBGP Sessions and Originate Prefixes

#### Task 1: Bring Up eBGP — R1 ↔ R3 (CE1 to ISP-A)

Establish the eBGP session between R1 (AS 65001) and R3 (AS 65100) using their directly
connected addresses on the 10.1.13.0/30 subnet. On each router, set the BGP router-id to
the Loopback0 address and enable neighbor state-change logging. Use `no bgp default
ipv4-unicast` and explicit `neighbor … activate` under `address-family ipv4` so that
address-family activation is intentional and visible in the running-config.

**Verification:** `show ip bgp summary` on R1 must show 10.1.13.2 (R3) in state `Estab`.
`show ip bgp summary` on R3 must show 10.1.13.1 (R1) in state `Estab`.

---

#### Task 2: Bring Up eBGP — R2 ↔ R4 (CE2 to ISP-B)

Establish the eBGP session between R2 (AS 65001) and R4 (AS 65200) using their directly
connected addresses on the 10.1.24.0/30 subnet. Apply the same BGP defaults (router-id
from Loopback0, `no bgp default ipv4-unicast`, explicit `neighbor … activate`) as in
Task 1.

**Verification:** `show ip bgp summary` on R2 must show 10.1.24.2 (R4) in state `Estab`.
`show ip bgp summary` on R4 must show 10.1.24.1 (R2) in state `Estab`.

---

#### Task 3: Originate the Representative Prefixes

Configure R3 to advertise its ISP-A representative prefix 10.100.1.0/24 (Loopback1) into
BGP. Configure R4 to advertise its ISP-B representative prefix 10.200.1.0/24 (Loopback1)
into BGP. Configure R1 to advertise the customer PI prefix 192.168.1.0/24 (Loopback1)
into BGP. Configure R2 to advertise the same customer PI prefix 192.168.1.0/24 — but
because R2 has no local interface representing the /24, R2 must first install a `Null0`
static for 192.168.1.0/24 so the BGP `network` statement has an exact RIB match.

**Verification:** `show ip bgp` on R1 must show 10.100.1.0/24 (received from R3). `show
ip bgp` on R2 must show 10.200.1.0/24 (received from R4). `show ip bgp` on R3 must show
192.168.1.0/24 with AS-path `65001`. `show ip bgp` on R4 must show 192.168.1.0/24 with
AS-path `65001`.

---

#### Task 4: Observe the Routing Gap

Without making any further configuration changes, run the following on R1:

- `show ip bgp` — does R1 see 10.200.1.0/24 (ISP-B's representative prefix)?
- `show ip route 10.200.1.0` — does R1 have a forwarding entry for it?

Run the equivalent on R2 for 10.100.1.0/24 (ISP-A's representative prefix). Document what
each CE can and cannot see, and write one sentence explaining why. The routing gap you
observe here is the motivation for Phase 2.

**Verification:** R1's BGP table must contain 192.168.1.0/24 (local) and 10.100.1.0/24
(from R3) — but not 10.200.1.0/24. R2's BGP table must contain 192.168.1.0/24 (local)
and 10.200.1.0/24 (from R4) — but not 10.100.1.0/24. Both gaps documented.

---

### Phase 2 — Close the Gap with CE-to-CE iBGP

#### Task 5: Provide Loopback Reachability for the iBGP Session

Before iBGP can come up on Loopback0 endpoints, each CE must have a route to the peer's
Loopback0. Because there is no IGP in this lab, install a single static route on each
CE pointing the peer's Loopback0 at the directly connected interface on link L3
(10.1.12.0/30). This is the minimum plumbing required for loopback peering.

**Verification:** `show ip route 10.0.0.2` on R1 must return a static entry via 10.1.12.2.
`show ip route 10.0.0.1` on R2 must return a static entry via 10.1.12.1. Both CEs must
be able to ping the peer's Loopback0.

---

#### Task 6: Configure the iBGP Session with update-source and next-hop-self

Configure a direct iBGP session between R1 and R2 using their Loopback0 addresses (10.0.0.1
and 10.0.0.2). Both routers are in AS 65001. Configure both sides to source the TCP
connection from Loopback0 — without this, the session sources from the physical interface
and the remote side rejects it. Configure both sides so that the next-hop advertised to
the iBGP peer is the advertising router's own Loopback0, not the original eBGP next-hop.

**Verification:** `show ip bgp summary` on R1 must show 10.0.0.2 in state `Estab`. `show
ip bgp summary` on R2 must show 10.0.0.1 in state `Estab`.

---

#### Task 7: Verify the Gap Is Closed and Both ISPs See the Customer Prefix

Re-run the same checks from Task 4. R1 must now see 10.200.1.0/24 (learned from R2 via
iBGP) with next-hop 10.0.0.2. R2 must now see 10.100.1.0/24 (learned from R1 via iBGP)
with next-hop 10.0.0.1. Confirm the next-hop on each iBGP-learned prefix is the peer
CE's Loopback0 — not the original eBGP next-hop on the ISP side. This is `next-hop-self`
in action.

Separately, confirm that both ISPs receive the customer prefix from both CEs: `show ip
bgp 192.168.1.0` on R3 must list R1 as the eBGP-advertising neighbor; the same command
on R4 must list R2.

**Verification:** R1's BGP table contains both 10.100.1.0/24 (eBGP from R3) and
10.200.1.0/24 (iBGP from R2 with next-hop 10.0.0.2). R2's table contains both
10.200.1.0/24 (eBGP from R4) and 10.100.1.0/24 (iBGP from R1 with next-hop 10.0.0.1).
R3's BGP table shows 192.168.1.0/24 with AS-path `65001`. R4's BGP table shows
192.168.1.0/24 with AS-path `65001`.

---

## 6. Verification & Analysis

### Phase 1 Verification — eBGP Sessions Up, Routing Gap Visible

```
R1# show ip bgp summary
BGP router identifier 10.0.0.1, local AS number 65001
...
Neighbor        V    AS  MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down  State/PfxRcd
10.1.13.2       4  65100      14       14       3    0     0  00:05:42        1   ! ← R3 Established, 1 prefix
```

```
R1# show ip bgp
BGP table version is 3, local router ID is 10.0.0.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
Origin codes: i - IGP, e - EGP, ? - incomplete

   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    10.1.13.2                0             0 65100 i   ! ← from R3 (ISP-A)
*> 192.168.1.0/24   0.0.0.0                  0         32768 i         ! ← locally originated
                                                                       ! ← 10.200.1.0/24 ABSENT — the gap
```

```
R2# show ip bgp
BGP table version is 3, local router ID is 10.0.0.2
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.200.1.0/24    10.1.24.2                0             0 65200 i   ! ← from R4 (ISP-B)
*> 192.168.1.0/24   0.0.0.0                  0         32768 i         ! ← locally originated
                                                                       ! ← 10.100.1.0/24 ABSENT — the gap
```

### Phase 2 Verification — iBGP Up, Gap Closed, next-hop-self Confirmed

```
R1# show ip bgp summary
...
Neighbor        V    AS  MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down  State/PfxRcd
10.0.0.2        4  65001       8        8       5    0     0  00:01:20        2   ! ← R2 iBGP Established, 2 prefixes
10.1.13.2       4  65100      14       14       5    0     0  00:05:42        1
```

```
R1# show ip bgp
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    10.1.13.2                0             0 65100 i
*>i10.200.1.0/24    10.0.0.2                 0    100      0 65200 i   ! ← from R2 via iBGP; next-hop = R2 Lo0 (next-hop-self)
*> 192.168.1.0/24   0.0.0.0                  0         32768 i
*>i192.168.1.0/24   10.0.0.2                 0    100      0 i         ! ← also received from R2 over iBGP
```

```
R1# show ip bgp 10.200.1.0
BGP routing table entry for 10.200.1.0/24
Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65200
    10.0.0.2 from 10.0.0.2 (10.0.0.2)         ! ← next-hop is R2's loopback, not R4's interface IP
      Origin IGP, metric 0, localpref 100, valid, internal, best
```

```
R3# show ip bgp 192.168.1.0
BGP routing table entry for 192.168.1.0/24
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001                                       ! ← AS-path: just AS 65001 (the customer)
    10.1.13.1 from 10.1.13.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, external, best
```

---

## 7. Verification Cheatsheet

### eBGP Session Configuration Pattern

```
router bgp <local-as>
 bgp router-id <loopback-ip>
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor <peer-ip> remote-as <remote-as>
 neighbor <peer-ip> description <label>
 address-family ipv4
  network <prefix> mask <mask>
  neighbor <peer-ip> activate
 exit-address-family
```

| Command | Purpose |
|---|---|
| `show ip bgp summary` | Session state, prefix counts |
| `show ip bgp neighbors <ip>` | Full session detail, timers, counters |
| `show ip bgp` | Table view — quick scan of all prefixes with AS-path in Path column |
| `show ip bgp <prefix>` | Detailed view — best-path selection and full attribute set |

> **Exam tip:** `show ip bgp` (table view) is best for scanning many prefixes; `show ip bgp
> <prefix>` (detailed view) is best for reading attributes like next-hop and AS-path. The
> AS-path appears in the **Path** column in the table view, and as the **first unlabeled
> line** in the detailed view.

### iBGP Loopback Peering Pattern

```
ip route <peer-loopback>/32 <next-hop-on-direct-link>

router bgp <same-as>
 neighbor <peer-loopback-ip> remote-as <same-as>
 neighbor <peer-loopback-ip> update-source Loopback0
 address-family ipv4
  neighbor <peer-loopback-ip> activate
  neighbor <peer-loopback-ip> next-hop-self
 exit-address-family
```

| Command | Purpose |
|---|---|
| `show ip route <peer-loopback>` | Confirm the peer loopback is reachable (precondition) |
| `show ip bgp neighbors <ip>` | Confirm `Update source` shows Loopback0 |
| `show ip bgp <prefix>` | Verify next-hop is the iBGP peer's loopback (not the eBGP next-hop) |
| `show tcp brief` | Confirm TCP session sourced from Loopback0 IP |

> **Exam tip:** Without `update-source Loopback0`, the TCP session sources from the
> outgoing physical interface. The remote `neighbor` statement points to the loopback IP,
> so the source address does not match — the session never establishes. Symptom: peer
> stuck in Active.

### next-hop-self — Why and When

| Scenario | Without next-hop-self | With next-hop-self |
|---|---|---|
| eBGP-learned prefix re-advertised over iBGP | Next-hop = original eBGP peer interface (likely unreachable from the iBGP peer) | Next-hop = local Loopback0 (reachable via the static plumbing) |
| Locally originated prefix advertised over iBGP | Next-hop = 0.0.0.0 by default → rewritten to local IP automatically | Same — the directive is harmless |

> **Exam tip:** Apply `next-hop-self` to any iBGP neighbor that will receive eBGP-learned
> routes from this router. In the dual-CE design, both R1 and R2 receive eBGP routes from
> their own ISP and re-advertise them over the CE-CE iBGP, so both sides need it.

### Common Failure Causes in This Lab

| Symptom | Likely Cause |
|---|---|
| eBGP session in Active | Wrong remote-as on either end, or the peer interface is shut/wrong subnet |
| eBGP Established, prefix not advertised | `network` statement does not exactly match the prefix in the RIB (mask mismatch on R2's `Null0` static) |
| iBGP session in Active | `update-source Loopback0` missing; static route to peer Lo0 missing; loopback unreachable |
| iBGP Established, but peer can't forward to the prefix | `next-hop-self` missing — peer has the route but cannot resolve the next-hop |
| ISP receives the prefix but with wrong AS-path length | `network` originated on the wrong CE, or routes leaking via iBGP without intended filtering (relevant in lab-01) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Phase 1 — eBGP and Prefix Origination

<details>
<summary>Click to view R1 Phase 1 Configuration (eBGP to R3 + customer prefix)</summary>

```bash
! R1
router bgp 65001
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.1.13.2 remote-as 65100
 neighbor 10.1.13.2 description eBGP to R3 (ISP-A)
 address-family ipv4
  network 192.168.1.0 mask 255.255.255.0
  neighbor 10.1.13.2 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Phase 1 Configuration (eBGP to R4 + customer prefix via Null0)</summary>

```bash
! R2
ip route 192.168.1.0 255.255.255.0 Null0

router bgp 65001
 bgp router-id 10.0.0.2
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.1.24.2 remote-as 65200
 neighbor 10.1.24.2 description eBGP to R4 (ISP-B)
 address-family ipv4
  network 192.168.1.0 mask 255.255.255.0
  neighbor 10.1.24.2 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration (ISP-A — eBGP to R1 + 10.100.1.0/24)</summary>

```bash
! R3
router bgp 65100
 bgp router-id 10.0.0.3
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.1.13.1 remote-as 65001
 neighbor 10.1.13.1 description eBGP to R1 (CE1, AS 65001)
 address-family ipv4
  network 10.100.1.0 mask 255.255.255.0
  neighbor 10.1.13.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration (ISP-B — eBGP to R2 + 10.200.1.0/24)</summary>

```bash
! R4
router bgp 65200
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.1.24.1 remote-as 65001
 neighbor 10.1.24.1 description eBGP to R2 (CE2, AS 65001)
 address-family ipv4
  network 10.200.1.0 mask 255.255.255.0
  neighbor 10.1.24.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Phase 1 Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp
show ip route 10.200.1.0     ! on R1 — should be absent at this stage
show ip route 10.100.1.0     ! on R2 — should be absent at this stage
```
</details>

---

### Phase 2 — iBGP Plumbing and CE-to-CE Session

<details>
<summary>Click to view R1 Phase 2 Additions (static + iBGP to R2)</summary>

```bash
! R1
ip route 10.0.0.2 255.255.255.255 10.1.12.2

router bgp 65001
 neighbor 10.0.0.2 remote-as 65001
 neighbor 10.0.0.2 description iBGP to R2 (CE2)
 neighbor 10.0.0.2 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Phase 2 Additions (static + iBGP to R1)</summary>

```bash
! R2
ip route 10.0.0.1 255.255.255.255 10.1.12.1

router bgp 65001
 neighbor 10.0.0.1 remote-as 65001
 neighbor 10.0.0.1 description iBGP to R1 (CE1)
 neighbor 10.0.0.1 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.1 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view Phase 2 Verification Commands</summary>

```bash
show ip route 10.0.0.2                       ! on R1 — must be /32 static via 10.1.12.2
show ip bgp summary                          ! 10.0.0.2 (or 10.0.0.1) must reach Estab
show ip bgp                                  ! both ISP prefixes now visible on each CE
show ip bgp 10.200.1.0                       ! on R1 — next-hop must be 10.0.0.2
show ip bgp 10.100.1.0                       ! on R2 — next-hop must be 10.0.0.1
show ip bgp 192.168.1.0                      ! on R3 and R4 — both must show AS-path 65001
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix
using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good (interfaces only)
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # bring lab to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — R1 Cannot Reach ISP-B's Prefix

The customer reports that hosts behind R1 (CE1) lose connectivity to 10.200.1.0/24 — the
ISP-B representative prefix that they were able to reach yesterday. Both ISPs confirm
their eBGP sessions are up and they are advertising prefixes normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R1's BGP table shows 10.200.1.0/24 received from 10.0.0.2 (R2)
with next-hop 10.0.0.2 (R2's Loopback0).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R1 — the eBGP session to R3 is up and exchanging prefixes,
   but the iBGP entry for 10.0.0.2 is in Active state (or absent entirely).
2. `show ip bgp neighbors 10.0.0.2 | include source` on R1 — confirm `update-source` is
   set to Loopback0. If this directive is missing, the TCP session sources from the
   physical interface and R2 rejects it.
3. `show ip route 10.0.0.2` on R1 — confirm the static route to R2's Loopback0 is still
   present. If the static is gone, the iBGP session has no underlay and cannot form.
4. `show running-config | section router bgp` on R1 — read the actual configuration to
   identify the missing or removed directive.
</details>

<details>
<summary>Click to view Fix</summary>

Restore the missing iBGP plumbing. The exact fix depends on which piece is missing —
either the `update-source Loopback0` directive on the iBGP neighbor, or the static
route to the peer's Loopback0. Apply the missing piece and verify the session reaches
`Estab` within ~30 seconds.

```bash
! Example fix if update-source is missing:
router bgp 65001
 neighbor 10.0.0.2 update-source Loopback0
```
</details>

---

### Ticket 2 — R3 Does Not Receive the Customer Prefix from R1

ISP-A's NOC reports that 192.168.1.0/24 has stopped appearing in R3's BGP table. The
eBGP session from R1 is up and stable. R1 itself shows 192.168.1.0/24 in its own BGP
table with the `>` (best) marker.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** R3's BGP table shows 192.168.1.0/24 with AS-path `65001` and
next-hop 10.1.13.1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp summary` on R1 — the session to 10.1.13.2 (R3) shows Established but
   `PfxSnd` to that neighbor is 0.
2. `show ip bgp neighbors 10.1.13.2 advertised-routes` on R1 — output is empty.
3. `show ip bgp` on R1 — 192.168.1.0/24 is present with the `>` marker, so the prefix is
   in BGP.
4. `show running-config | section router bgp` on R1 — examine the address-family ipv4
   block. The neighbor exists at the global level but is not activated under
   `address-family ipv4`. Without activation, the neighbor cannot exchange IPv4 unicast
   NLRIs even though the session is up.
</details>

<details>
<summary>Click to view Fix</summary>

Re-activate the neighbor in the IPv4 address-family on R1:

```bash
router bgp 65001
 address-family ipv4
  neighbor 10.1.13.2 activate
 exit-address-family
```

R3's BGP table updates within seconds. Verify on R3 with `show ip bgp 192.168.1.0`.
</details>

---

### Ticket 3 — R2 Sees 10.100.1.0/24 in BGP But Cannot Forward to It

A junior engineer reports that R2 has the ISP-A prefix in its BGP table now (so iBGP
must be working), but `ping 10.100.1.1` from R2 fails. The BGP table entry exists, but
the route is not in the RIB.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 10.100.1.0` on R2 shows next-hop 10.0.0.1 (R1's
Loopback0), and `show ip route 10.100.1.0` returns a BGP-installed entry. Ping from
R2 to 10.100.1.1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 10.100.1.0` on R2 — the prefix is present, but its next-hop is not
   10.0.0.1 (R1's Loopback0). Instead, the next-hop is the original eBGP next-hop
   between R1 and R3 — an address that R2 has no route to.
2. `show ip route 10.1.13.2` on R2 — no route. R2 has no way to reach the ISP-A side of
   R1, so the BGP next-hop is unresolvable and the route cannot be installed.
3. `show ip bgp 10.100.1.0` should display the unresolvable next-hop with the
   `(inaccessible)` marker.
4. The diagnosis points to R1: `show running-config | section router bgp` on R1 reveals
   that the `next-hop-self` directive on the iBGP neighbor 10.0.0.2 is missing.
</details>

<details>
<summary>Click to view Fix</summary>

On R1, restore `next-hop-self` for the CE-CE iBGP neighbor:

```bash
router bgp 65001
 address-family ipv4
  neighbor 10.0.0.2 next-hop-self
 exit-address-family
```

R1 re-advertises 10.100.1.0/24 to R2 with next-hop 10.0.0.1 (its own Loopback0), which
R2 can resolve via its static route. The route installs, ping succeeds.
</details>

---

## 10. Lab Completion Checklist

### Phase 1 — eBGP Up, Routing Gap Documented

- [ ] `show ip bgp summary` on R1 shows 10.1.13.2 (R3) in `Estab`
- [ ] `show ip bgp summary` on R2 shows 10.1.24.2 (R4) in `Estab`
- [ ] `show ip bgp` on R3 shows 192.168.1.0/24 with AS-path `65001`
- [ ] `show ip bgp` on R4 shows 192.168.1.0/24 with AS-path `65001`
- [ ] R1's BGP table contains 10.100.1.0/24 but not 10.200.1.0/24 — gap observed
- [ ] R2's BGP table contains 10.200.1.0/24 but not 10.100.1.0/24 — gap observed

### Phase 2 — iBGP Up, Gap Closed

- [ ] `show ip route 10.0.0.2` on R1 returns a static `/32` via 10.1.12.2
- [ ] `show ip route 10.0.0.1` on R2 returns a static `/32` via 10.1.12.1
- [ ] `show ip bgp summary` on R1 shows 10.0.0.2 in `Estab`
- [ ] `show ip bgp 10.200.1.0` on R1 shows next-hop 10.0.0.2 (next-hop-self in effect)
- [ ] `show ip bgp 10.100.1.0` on R2 shows next-hop 10.0.0.1 (next-hop-self in effect)
- [ ] R1 can ping 10.200.1.1; R2 can ping 10.100.1.1

### Troubleshooting

- [ ] Ticket 1 resolved — iBGP session restored after fixing `update-source` plumbing
- [ ] Ticket 2 resolved — R3 receives 192.168.1.0/24 after re-activating the neighbor
- [ ] Ticket 3 resolved — R2 forwards to 10.100.1.0/24 after restoring `next-hop-self` on R1

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
