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

This lab establishes the architectural foundation for the entire dual-CE topic series. Five
core concepts drive the implementation. Each concept appears as a named grouping in the Lab
Challenge (Section 5), in the Verification (Section 6), and in the Cheatsheet (Section 7)
so you can trace every task back to its concept and every concept back to the exam
blueprint.

---

### Concept 1 — The Dual-CE Architecture

A customer who deploys **two CE routers in the same AS**, each peering with a **different
upstream ISP**, operates in a fundamentally different architecture than the single-CE model
covered in the `bgp` topic series (labs 00–08).

In single-CE dual-homing (two uplinks to one SP), prefix visibility is never in question —
the CE sees everything its single SP sends it. Convergence problems are about link
failover, not about information scope.

In dual-CE dual-provider multihoming, information scope becomes the dominant problem.
Each CE only learns the prefixes from its own upstream by default. The customer AS
becomes internally fragmented — R1 knows ISP-A's world, R2 knows ISP-B's world, and
neither knows both. Traffic from behind R1 to an ISP-B destination hits a routing dead-end.
The fragmentation is invisible at the eBGP level (each session looks healthy) and only
surfaces as reachability failures.

**Why this matters on the exam:** Blueprint bullet 1.5.d tests whether you understand
that multihoming topology dictates BGP session architecture. A topology with two CEs
to two ISPs demands CE-CE iBGP; the single-CE topology does not. The exam draws this
distinction explicitly.

**Manifests in:** Concept 2 (routing gap), Concept 4 (iBGP), Concept 5 (next-hop-self).

---

### Concept 2 — The Routing Gap (Why iBGP Is Mandatory)

When R1 peers eBGP with ISP-A and R2 peers eBGP with ISP-B, and no iBGP exists between
R1 and R2, the following state exists on each CE:

| CE  | Learns from eBGP                          | Does NOT see                           |
|-----|-------------------------------------------|----------------------------------------|
| R1  | 10.100.1.0/24 (from R3, ISP-A)            | 10.200.1.0/24 (only known to R2)       |
| R2  | 10.200.1.0/24 (from R4, ISP-B)            | 10.100.1.0/24 (only known to R1)       |

Each CE has a partial BGP table. The gap is not a failure — BGP is working correctly,
redistributing only what each eBGP session receives. The gap is a consequence of the
topology. Closing it requires a CE-to-CE iBGP session that carries each eBGP-learned
prefix to the other CE.

**Pedagogical note:** This lab deliberately splits implementation into two stages. You
will first bring up eBGP only and **observe the gap** in the BGP tables (Concept 2
verification). Then you will configure iBGP and **close the gap** (Concepts 3–5). The
intent is to make the gap concrete — seeing it in `show ip bgp` output is more memorable
than reading about it.

**Why this matters on the exam:** The 300-510 exam expects you to recognize a dual-CE
gap scenario from partial BGP table output and identify iBGP as the fix. The gap
symptom — "R1 has ISP-A routes, R2 has ISP-B routes, neither has both" — is a classic
multihoming diagnostic pattern.

**Manifests in:** Task 4 (observe the gap), Task 6–7 (close the gap with iBGP).

---

### Concept 3 — eBGP Multihoming to Two Distinct ISP ASes

The two eBGP sessions in this lab differ from the `bgp` topic series in two ways:

1. **Different remote ASes.** R1 peers with AS 65100 (ISP-A); R2 peers with AS 65200
   (ISP-B). They are not both peering into the same SP. Each is a fully independent
   eBGP relationship with its own policy domain.

2. **No shared IGP underlay.** The CEs run BGP only. There is no OSPF or IS-IS in the
   customer AS. Loopback reachability for the CE-CE iBGP session is supplied by static
   routes (Concept 4), not by an IGP.

Each CE originates the same customer PI prefix (192.168.1.0/24) into BGP so that both
ISPs receive a route to the customer network from an independent CE — the redundancy
pattern. R2 demonstrates the Null0 + `network` method (Concept 6) because it has no
local Loopback1 anchoring the /24.

**Why this matters on the exam:** The blueprint tests understanding that multi-ISP
multihoming means multiple independent eBGP policies. AS-path prepend on one session
affects only one ISP's view of the customer prefix — a property exploited in lab-02 for
inbound traffic engineering.

**Manifests in:** Tasks 1–3.

---

### Concept 4 — Loopback-Based iBGP Peering (Session Identity Decoupling)

R1 and R2 share one direct link (10.1.12.0/30 on L3). A student's first instinct is to
peer iBGP using those interface IPs. It works — the session comes up. The problem is
that **session identity is bound to the interface**: if Gi0/1 flaps on R1, the iBGP
session drops even when the router is otherwise healthy.

Loopback-based peering decouples session identity from physical-interface state.
Loopback0 is always Up/Up while the router is powered. The session terminates on a
stable address that does not change when interfaces are added, removed, or fail. This
is the universal SP convention.

The cost is one piece of plumbing: each CE needs a route to the peer's Loopback0.
Because no IGP runs in the customer AS, that route is supplied by a single static /32
per CE pointing the peer's Loopback0 at the directly connected interface IP on link L3.

The `update-source Loopback0` directive tells BGP to source the TCP connection from
Loopback0 rather than the physical interface. Without it, the TCP session sources from
the outgoing physical interface IP — which does not match the remote `neighbor`
statement (which targets the loopback address), so the session never establishes.
Symptom: peer stuck in `Active`.

**Why this matters on the exam:** Loopback peering is the universal SP BGP convention.
The exam expects you to recognize the `update-source Loopback0` requirement and
diagnose its absence (peer stuck in Active despite reachability to the loopback).

**Manifests in:** Task 5 (static plumbing), Task 6 (iBGP config with update-source).

---

### Concept 5 — next-hop-self on the iBGP Session

When R1 receives 10.100.1.0/24 from R3 over eBGP, the BGP next-hop attribute is set to
R3's interface address: 10.1.13.2. R1 then advertises that route over iBGP to R2. By
default, **iBGP does not change the next-hop attribute** — R2 receives 10.100.1.0/24
with next-hop 10.1.13.2.

R2 has no route to 10.1.13.2. That subnet is on the ISP-A side, completely outside
the customer AS. The route enters R2's BGP table but **cannot be installed in the RIB**
because the next-hop is unresolvable. R2 has the prefix but cannot forward to it. The
BGP table will show the `(inaccessible)` marker on the next-hop.

The fix is `neighbor <peer-loopback> next-hop-self` on R1's iBGP configuration. R1
rewrites the next-hop to its own Loopback0 (10.0.0.1) when advertising over iBGP. R2
has a static route to 10.0.0.1 (the Concept 4 plumbing), so the route resolves and
installs. The same fix applies symmetrically on R2 for ISP-B prefixes.

**Critical distinction:** `next-hop-self` is required on **both** CEs in this
topology. R1 rewrites ISP-A prefixes for R2; R2 rewrites ISP-B prefixes for R1. A
single-sided `next-hop-self` closes the gap in one direction and leaves the other
broken.

**Why this matters on the exam:** The unresolvable-next-hop problem is a classic BGP
troubleshooting scenario. The exam gives you `show ip bgp` output showing a valid
route with a next-hop the router cannot reach, and asks what command fixes it. The
answer is `next-hop-self` on the advertising iBGP peer.

**Manifests in:** Task 6 (next-hop-self config), Task 7 (verification of rewritten
next-hops).

---

### Concept 6 — Dual Origination of the Customer Prefix

Both CEs must originate the customer PI prefix 192.168.1.0/24 into BGP for redundancy.
If only R1 originates it and R1 fails, both ISPs lose their route to the customer —
even though R2 is healthy and connected to ISP-B.

R1 anchors the /24 on Loopback1 (a real interface — `connected` route). R2 has no
Loopback1. Instead, R2 installs a Null0 static (`ip route 192.168.1.0 255.255.255.0
Null0`) so the BGP `network` statement has an exact RIB match to install. This is the
standard PI-prefix origination pattern when no local interface holds the prefix.

Both ISPs receive 192.168.1.0/24 with AS-path `65001` from their respective CEs. The
AS-path is identical regardless of which CE originated it, because both CEs are in AS
65001 and the iBGP session does not prepend AS-path.

**Why this matters on the exam:** The Null0 + `network` pattern is the correct way to
originate a prefix in BGP when the prefix is not bound to a local interface. The exam
expects you to recognize that an `ip route … Null0` is required as a precondition for
the `network` statement to take effect.

**Manifests in:** Task 3 (R2's Null0 static + network).

---

### Concept-to-Task Map

| Concept | Section 5 Tasks | Verification (Section 6) | Cheatsheet Block |
|---|---|---|---|
| 1 — Dual-CE Architecture | (context) | — | — |
| 2 — The Routing Gap | Task 4 | Phase A: Routing Gap | Gap Diagnosis |
| 3 — eBGP Multihoming | Tasks 1–3 | Phase B: eBGP Convergence | eBGP Session Pattern |
| 4 — Loopback Peering | Tasks 5–6 | Phase C: Loopback Reachability + iBGP | iBGP Loopback Pattern |
| 5 — next-hop-self | Tasks 6–7 | Phase D: next-hop-self | next-hop-self Table |
| 6 — Dual Origination | Task 3 | Phase B: eBGP Convergence | Null0 Pattern |

### Skills This Lab Develops

| Skill | Description | Concept |
|---|---|---|
| Dual-CE eBGP bring-up | Configuring two independent customer-to-ISP eBGP sessions in the same AS | 3 |
| Loopback reachability via static | Establishing peer loopback reachability without an IGP | 4 |
| iBGP loopback peering | Using `update-source Loopback0` between two CEs on a single direct link | 4 |
| next-hop-self on CE-CE iBGP | Replacing eBGP next-hops so the peer CE can resolve forwarding addresses | 5 |
| Customer prefix origination from two CEs | Advertising 192.168.1.0/24 from R1 (Lo1) and R2 (Null0 + network) | 6 |
| Routing-gap diagnosis | Recognizing the symptom of missing CE-CE iBGP before fixing it | 2 |

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

> **Structure note:** Tasks are grouped by concept, not by configuration phase. Concepts
> 3 and 6 (eBGP + dual origination) come first because the gap cannot be observed without
> working eBGP sessions and advertised prefixes. Concept 2 (routing gap) is observed
> immediately after — the visible gap motivates Concepts 4 and 5 (loopback peering +
> next-hop-self) that close it.

---

### ▸ Concept 3 — eBGP Multihoming & Concept 6 — Dual Prefix Origination

Establish two independent eBGP sessions (one per ISP) and originate all four
representative prefixes into BGP. These tasks establish the baseline routing state that
Concept 2's routing gap will become visible within.

---

#### Task 1: Bring Up eBGP — R1 ↔ R3 (CE1 to ISP-A)

Establish the eBGP session between R1 (AS 65001) and R3 (AS 65100) using their directly
connected addresses on the 10.1.13.0/30 subnet. On each router, set the BGP router-id to
the Loopback0 address and enable neighbor state-change logging. Use `no bgp default
ipv4-unicast` and explicit `neighbor … activate` under `address-family ipv4` so that
address-family activation is intentional and visible in the running-config.

> **Concept 3 anchor:** This is one half of the dual-CE eBGP foundation. Each CE peers
> with a *different* ISP AS — not two PEs in the same AS. The two eBGP sessions share
> no policy relationship. R1's session to R3 and R2's session to R4 are configured
> identically in structure but with different remote-AS values.

**Verification:** `show ip bgp summary` on R1 must show 10.1.13.2 (R3) in state `Estab`.
`show ip bgp summary` on R3 must show 10.1.13.1 (R1) in state `Estab`.

---

#### Task 2: Bring Up eBGP — R2 ↔ R4 (CE2 to ISP-B)

Establish the eBGP session between R2 (AS 65001) and R4 (AS 65200) using their directly
connected addresses on the 10.1.24.0/30 subnet. Apply the same BGP defaults (router-id
from Loopback0, `no bgp default ipv4-unicast`, explicit `neighbor … activate`) as in
Task 1.

> **Concept 3 anchor:** The remote-AS differs from Task 1 (65200 vs 65100). Both CEs are
> in AS 65001, but they peer with different ASes — this is the defining property of
> dual-CE dual-provider multihoming.

**Verification:** `show ip bgp summary` on R2 must show 10.1.24.2 (R4) in state `Estab`.
`show ip bgp summary` on R4 must show 10.1.24.1 (R2) in state `Estab`.

---

#### Task 3: Originate the Representative Prefixes

Configure R3 to advertise its ISP-A representative prefix 10.100.1.0/24 (Loopback1) into
BGP. Configure R4 to advertise its ISP-B representative prefix 10.200.1.0/24 (Loopback1)
into BGP.

Configure R1 to advertise the customer PI prefix 192.168.1.0/24 (Loopback1) into BGP.

Configure R2 to advertise the same customer PI prefix 192.168.1.0/24 — but because R2 has
no local interface representing the /24, R2 must first install a `Null0` static for
192.168.1.0/24 so the BGP `network` statement has an exact RIB match.

> **Concept 6 anchor:** The Null0 + `network` pattern is the standard PI-prefix
> origination technique. The `ip route … Null0` creates a RIB entry that the BGP
> `network` statement can match. Without the Null0 static, the `network
> 192.168.1.0 mask 255.255.255.0` command silently does nothing — the prefix never
> enters the BGP table. Both CEs originate the same /24 for redundancy; neither ISP
> depends on a single CE for customer reachability.

**Verification:** `show ip bgp` on R1 must show 10.100.1.0/24 (received from R3). `show
ip bgp` on R2 must show 10.200.1.0/24 (received from R4). `show ip bgp` on R3 must show
192.168.1.0/24 with AS-path `65001`. `show ip bgp` on R4 must show 192.168.1.0/24 with
AS-path `65001`.

---

### ▸ Concept 2 — The Routing Gap

With eBGP sessions up and prefixes originated, the customer AS is internally fragmented.
Each CE has a valid BGP table — but only for the ISP it directly peers with. This task
asks you to observe the fragmentation before fixing it.

---

#### Task 4: Observe the Routing Gap

Without making any further configuration changes, run the following on R1:

- `show ip bgp` — does R1 see 10.200.1.0/24 (ISP-B's representative prefix)?
- `show ip route 10.200.1.0` — does R1 have a forwarding entry for it?

Run the equivalent on R2 for 10.100.1.0/24 (ISP-A's representative prefix). Document
what each CE can and cannot see, and write one sentence explaining why.

> **Concept 2 anchor:** The gap is not a misconfiguration — BGP is operating correctly.
> R1 peers eBGP with R3 and receives 10.100.1.0/24 from it. R1 has no eBGP relationship
> with R4 and therefore never receives 10.200.1.0/24. The gap is a direct consequence
> of the dual-CE, dual-provider topology. Closing it requires CE-to-CE iBGP — the
> objective of Tasks 5–7.

**Verification:** R1's BGP table must contain 192.168.1.0/24 (local) and 10.100.1.0/24
(from R3) — but not 10.200.1.0/24. R2's BGP table must contain 192.168.1.0/24 (local)
and 10.200.1.0/24 (from R4) — but not 10.100.1.0/24. Both gaps documented.

---

### ▸ Concept 4 — Loopback-Based iBGP Peering

Before the iBGP session can form on Loopback0 endpoints, each CE must be able to reach
the peer's Loopback0. Because no IGP runs in the customer AS, this reachability is
supplied by static /32 routes.

---

#### Task 5: Provide Loopback Reachability for the iBGP Session

Before iBGP can come up on Loopback0 endpoints, each CE must have a route to the peer's
Loopback0. Because there is no IGP in this lab, install a single static route on each
CE pointing the peer's Loopback0 at the directly connected interface on link L3
(10.1.12.0/30). This is the minimum plumbing required for loopback peering.

> **Concept 4 anchor:** Loopback peering requires an underlay route to the peer's
> loopback. In a full SP deployment this underlay is an IGP (OSPF/IS-IS). In this
> two-CE lab, a single /32 static on each CE achieves the same with zero IGP overhead.
> The static route points at the directly connected L3 interface — no recursive
> resolution, no dependency on any other protocol.

**Verification:** `show ip route 10.0.0.2` on R1 must return a static entry via 10.1.12.2.
`show ip route 10.0.0.1` on R2 must return a static entry via 10.1.12.1. Both CEs must
be able to ping the peer's Loopback0.

---

#### Task 6: Configure the iBGP Session with update-source and next-hop-self

Configure a direct iBGP session between R1 and R2 using their Loopback0 addresses (10.0.0.1
and 10.0.0.2). Both routers are in AS 65001.

Configure both sides to source the TCP connection from Loopback0 — without this, the
session sources from the physical interface and the remote side rejects it.

Configure both sides with `next-hop-self` so that the next-hop advertised to the iBGP
peer is the advertising router's own Loopback0, not the original eBGP next-hop.

> **Concept 4 anchor (update-source):** The `update-source Loopback0` directive is what
> makes the TCP session terminate on the loopback address. Without it, BGP sources the
> TCP SYN from the outgoing physical interface (Gi0/1 on L3, 10.1.12.1 or .2). The remote
> `neighbor` statement specifies the loopback address, so the source IP of the incoming
> SYN does not match — TCP never establishes. Symptom: peer stays in `Active`.
>
> **Concept 5 anchor (next-hop-self):** eBGP-learned routes carry a next-hop that is
> outside the customer AS (the ISP's interface address). iBGP preserves this next-hop
> by default, making it unresolvable by the iBGP peer. `next-hop-self` rewrites the
> next-hop to the advertising router's Loopback0, which the peer can resolve via the
> Concept 4 static route. Both CEs need this directive because both re-advertise
> eBGP-learned prefixes over the iBGP session.

**Verification:** `show ip bgp summary` on R1 must show 10.0.0.2 in state `Estab`. `show
ip bgp summary` on R2 must show 10.0.0.1 in state `Estab`.

---

### ▸ Concept 5 — End-to-End Verification

Confirm that the routing gap from Concept 2 is closed and that `next-hop-self` is
operating correctly on both iBGP directions.

---

#### Task 7: Verify the Gap Is Closed and Both ISPs See the Customer Prefix

Re-run the same checks from Task 4. R1 must now see 10.200.1.0/24 (learned from R2 via
iBGP) with next-hop 10.0.0.2. R2 must now see 10.100.1.0/24 (learned from R1 via iBGP)
with next-hop 10.0.0.1. Confirm the next-hop on each iBGP-learned prefix is the peer
CE's Loopback0 — not the original eBGP next-hop on the ISP side. This is `next-hop-self`
in action.

> **Concept 5 anchor:** The `i` flag in `show ip bgp` output indicates an iBGP-learned
> route. The next-hop column should show the peer CE's Loopback0 (10.0.0.1 or 10.0.0.2),
> not the original eBGP next-hop (10.1.13.2 or 10.1.24.2). If the next-hop still shows
> the ISP interface address, `next-hop-self` is missing on the advertising CE.

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

The verification is organized by concept — start with the routing gap (Concept 2), then
confirm eBGP convergence (Concept 3), then verify loopback peering and iBGP (Concepts 4–5).

---

### Phase A — Verify the Routing Gap (Concept 2)

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

> **Concept 2 — What to look for:** R1's BGP table has exactly two prefixes: the ISP-A
> prefix (via eBGP) and the customer prefix (local). ISP-B's 10.200.1.0/24 is absent.
> This is the gap — R1 has no path to ISP-B's network. The table on R2 shows the mirror
> image: 10.200.1.0/24 present, 10.100.1.0/24 absent.

```
R2# show ip bgp
BGP table version is 3, local router ID is 10.0.0.2
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.200.1.0/24    10.1.24.2                0             0 65200 i   ! ← from R4 (ISP-B)
*> 192.168.1.0/24   0.0.0.0                  0         32768 i         ! ← locally originated
                                                                       ! ← 10.100.1.0/24 ABSENT — the gap
```

---

### Phase B — Verify eBGP Convergence (Concepts 3 & 6)

Both eBGP sessions must show `Estab` with one prefix received (the ISP's representative
prefix). Each CE must show the customer prefix as locally originated (next-hop 0.0.0.0,
weight 32768). Each ISP must see the customer prefix with AS-path `65001`.

```
R3# show ip bgp
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    0.0.0.0                  0         32768 i         ! ← ISP-A local
*> 192.168.1.0/24   10.1.13.1                0             0 65001 i   ! ← from R1 (CE1)
```

```
R4# show ip bgp
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.200.1.0/24    0.0.0.0                  0         32768 i         ! ← ISP-B local
*> 192.168.1.0/24   10.1.24.1                0             0 65001 i   ! ← from R2 (CE2)
```

> **Concept 6 — What to look for:** The AS-path for the customer prefix on both ISPs is
> `65001` — a single AS hop. Both ISPs receive the same prefix from different CEs in the
> same AS. The Null0 static on R2 is invisible to the ISPs; they only see the BGP
> advertisement. If the AS-path were longer or differed between ISPs, that would indicate
> an upstream AS-path prepend policy — the subject of lab-02.

---

### Phase C — Verify Loopback Reachability & iBGP Session (Concept 4)

```
R1# show ip route 10.0.0.2
Routing entry for 10.0.0.2/32
  Known via "static", distance 1, metric 0
  Routing Descriptor Blocks:
  * 10.1.12.2
      Route metric is 0, traffic share count is 1
```

> **Concept 4 — What to look for:** The route to the peer's Loopback0 must be a /32
> static pointing at the directly connected L3 interface. The administrative distance is
> 1 (static). Without this route, the iBGP TCP session cannot reach the peer's loopback
> and the neighbor stays in `Active`.

```
R1# show ip bgp summary
...
Neighbor        V    AS  MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down  State/PfxRcd
10.0.0.2        4  65001       8        8       5    0     0  00:01:20        2   ! ← R2 iBGP Established, 2 prefixes
10.1.13.2       4  65100      14       14       5    0     0  00:05:42        1
```

> **Concept 4 — What to look for:** The iBGP neighbor appears with AS `65001` (same as
> local). `PfxRcd` should be 2 (the ISP-B prefix + the customer prefix from R2's
> origination). If the iBGP neighbor is in `Active`, either the static route is missing,
> `update-source Loopback0` is missing, or the loopback itself is unreachable. Use
> `show tcp brief` to confirm the TCP session sources from the correct address.

---

### Phase D — Verify next-hop-self (Concept 5)

```
R1# show ip bgp
...
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    10.1.13.2                0             0 65100 i
*>i10.200.1.0/24    10.0.0.2                 0    100      0 65200 i   ! ← from R2 via iBGP; next-hop = R2 Lo0
*> 192.168.1.0/24   0.0.0.0                  0         32768 i
*>i192.168.1.0/24   10.0.0.2                 0    100      0 i         ! ← also received from R2 over iBGP
```

> **Concept 5 — What to look for:** The iBGP-learned ISP-B prefix (`>i`) shows next-hop
> `10.0.0.2` — R2's Loopback0. This is the result of `next-hop-self` on R2. If the
> next-hop were `10.1.24.2` (R4's interface), the route would be present in the BGP
> table but unresolvable (no `>` marker, `(inaccessible)` annotation) — the exact
> symptom of missing `next-hop-self`.

```
R1# show ip bgp 10.200.1.0
BGP routing table entry for 10.200.1.0/24
Paths: (1 available, best #1, table default)
  Refresh Epoch 1
  65200
    10.0.0.2 from 10.0.0.2 (10.0.0.2)         ! ← next-hop = R2's loopback, not R4's interface IP
      Origin IGP, metric 0, localpref 100, valid, internal, best
```

> **Concept 5 — What to look for:** The detailed view confirms the next-hop (`10.0.0.2`)
> and shows `localpref 100` (iBGP default) and `internal` (iBGP-learned). The AS-path
> `65200` is from ISP-B — AS 65001 was not prepended because this is an iBGP update.

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

Commands grouped by concept — use the concept that matches what you are debugging.

---

### Concept 3 — eBGP Session Configuration Pattern

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
| `show ip bgp summary` | Session state, prefix counts per neighbor |
| `show ip bgp neighbors <ip>` | Full session detail, timers, counters |
| `show ip bgp` | Table view — quick scan of all prefixes with AS-path in Path column |
| `show ip bgp <prefix>` | Detailed view — best-path selection and full attribute set |

> **Exam tip:** `show ip bgp` (table view) is best for scanning many prefixes; `show ip bgp
> <prefix>` (detailed view) is best for reading attributes like next-hop and AS-path. The
> AS-path appears in the **Path** column in the table view, and as the **first unlabeled
> line** in the detailed view.

---

### Concept 2 — Routing Gap Diagnosis

| Command | What It Confirms |
|---|---|
| `show ip bgp \| include 10.200` on R1 | ISP-B prefix absent → gap confirmed |
| `show ip bgp \| include 10.100` on R2 | ISP-A prefix absent → gap confirmed |
| `show ip route 10.200.1.0` on R1 | No RIB entry → cannot forward to ISP-B through this CE |

> **Exam tip:** A prefix present in `show ip bgp` but absent in `show ip route` means
> the BGP next-hop is unresolvable — a different problem from a routing gap (where the
> prefix is absent from BGP entirely). The gap (Concept 2) means the prefix was never
> received; unresolvable next-hop (Concept 5) means it was received but cannot be used.

---

### Concept 4 — iBGP Loopback Peering Pattern

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
> stuck in `Active`.

---

### Concept 5 — next-hop-self: Why and When

| Scenario | Without next-hop-self | With next-hop-self |
|---|---|---|
| eBGP-learned prefix re-advertised over iBGP | Next-hop = original eBGP peer interface (unreachable from iBGP peer) | Next-hop = local Loopback0 (reachable via static plumbing) |
| Locally originated prefix advertised over iBGP | Next-hop = 0.0.0.0 → rewritten to local IP automatically | Same — directive is harmless |

> **Exam tip:** Apply `next-hop-self` to any iBGP neighbor that will receive eBGP-learned
> routes from this router. In the dual-CE design, both R1 and R2 receive eBGP routes from
> their own ISP and re-advertise them over the CE-CE iBGP, so both sides need it.

---

### Concept 6 — Null0 Static for Prefix Origination

```
ip route <prefix> <mask> Null0
!
router bgp <as>
 address-family ipv4
  network <prefix> mask <mask>
 exit-address-family
```

| Command | Purpose |
|---|---|
| `show ip route <prefix>` | Confirm the Null0 static is in the RIB (precondition for `network`) |
| `show ip bgp <prefix>` | Confirm the prefix appears as locally originated (next-hop 0.0.0.0, weight 32768) |

> **Exam tip:** The `network` statement in BGP does *not* originate a route from thin air.
> It installs a prefix into the BGP table only if that exact prefix exists in the RIB. The
> Null0 static provides that RIB entry when no local interface anchors the prefix. If the
> mask in the `network` statement does not match the mask in the RIB entry, the prefix
> silently fails to appear in BGP.

---

### Common Failure Causes by Concept

| Symptom | Likely Cause | Concept |
|---|---|---|
| eBGP session in Active | Wrong remote-as, peer interface shut/wrong subnet | 3 |
| eBGP Established, prefix not advertised | `network` mask mismatch with RIB (R2's Null0 static) | 6 |
| iBGP session in Active | `update-source Loopback0` missing; static route to peer Lo0 missing | 4 |
| Prefix in BGP but not in RIB | `next-hop-self` missing — next-hop unresolvable | 5 |
| ISP receives prefix with wrong AS-path | `network` originated on wrong CE | 3 |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Concept 3 — eBGP Sessions & Concept 6 — Prefix Origination

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
<summary>Click to view Concept 2–3 Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp
show ip route 10.200.1.0     ! on R1 — should be absent at this stage (the gap)
show ip route 10.100.1.0     ! on R2 — should be absent at this stage (the gap)
```
</details>

---

### Concepts 4–5 — iBGP Loopback Peering and next-hop-self

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
<summary>Click to view Concept 4–5 Verification Commands</summary>

```bash
show ip route 10.0.0.2                       ! on R1 — must be /32 static via 10.1.12.2
show ip bgp summary                          ! 10.0.0.2 (or 10.0.0.1) must reach Estab
show ip bgp                                  ! both ISP prefixes now visible on each CE
show ip bgp 10.200.1.0                       ! on R1 — next-hop must be 10.0.0.2 (next-hop-self)
show ip bgp 10.100.1.0                       ! on R2 — next-hop must be 10.0.0.1 (next-hop-self)
show ip bgp 192.168.1.0                      ! on R3 and R4 — both must show AS-path 65001
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault tied to a specific concept. Inject the fault
first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good (interfaces only)
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # bring lab to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — R1 Cannot Reach ISP-B's Prefix (Concept 4: Loopback Peering Failure)

The customer reports that hosts behind R1 (CE1) lose connectivity to 10.200.1.0/24 — the
ISP-B representative prefix that they were able to reach yesterday. Both ISPs confirm
their eBGP sessions are up and they are advertising prefixes normally.

**Concept tested:** Concept 4 — Loopback-based iBGP peering. The iBGP session cannot form
because either the static route to the peer's Loopback0 was removed or `update-source
Loopback0` was removed. The eBGP session (Concept 3) is healthy — confirming eBGP is up
excludes ISP failure and focuses the diagnosis on the CE-CE path.

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

### Ticket 2 — R3 Does Not Receive the Customer Prefix from R1 (Concept 3: eBGP Activation)

ISP-A's NOC reports that 192.168.1.0/24 has stopped appearing in R3's BGP table. The
eBGP session from R1 is up and stable. R1 itself shows 192.168.1.0/24 in its own BGP
table with the `>` (best) marker.

**Concept tested:** Concept 3 — eBGP multihoming. The eBGP session is established at the
global BGP level but the neighbor is not activated under `address-family ipv4`. Without
activation, the session exchanges keepalives but no NLRI — the peer relationship is
technically "up" but functionally useless.

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

### Ticket 3 — R2 Sees 10.100.1.0/24 in BGP But Cannot Forward to It (Concept 5: next-hop-self)

A junior engineer reports that R2 has the ISP-A prefix in its BGP table now (so iBGP
must be working), but `ping 10.100.1.1` from R2 fails. The BGP table entry exists, but
the route is not in the RIB.

**Concept tested:** Concept 5 — next-hop-self. The iBGP session is up (Concept 4
plumbing is intact) and prefixes are being exchanged — but `next-hop-self` is missing
on R1. R2 receives 10.100.1.0/24 with next-hop 10.1.13.2 (R3's interface), which R2
has no route to. The route enters the BGP table but is unresolvable; RIB installation
fails and forwarding is impossible.

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

Organized by concept — check off each concept's verification items before moving to the
next.

### Concept 3 — eBGP Multihoming

- [ ] `show ip bgp summary` on R1 shows 10.1.13.2 (R3) in `Estab`
- [ ] `show ip bgp summary` on R2 shows 10.1.24.2 (R4) in `Estab`
- [ ] `show ip bgp` on R3 shows 10.100.1.0/24 locally originated
- [ ] `show ip bgp` on R4 shows 10.200.1.0/24 locally originated

### Concept 6 — Dual Customer Prefix Origination

- [ ] `show ip bgp` on R3 shows 192.168.1.0/24 with AS-path `65001` (from R1)
- [ ] `show ip bgp` on R4 shows 192.168.1.0/24 with AS-path `65001` (from R2)
- [ ] On R2: `show ip route 192.168.1.0` shows a static Null0 route

### Concept 2 — Routing Gap (Observed Before iBGP)

- [ ] R1's BGP table contains 10.100.1.0/24 but **not** 10.200.1.0/24 — gap confirmed
- [ ] R2's BGP table contains 10.200.1.0/24 but **not** 10.100.1.0/24 — gap confirmed
- [ ] `show ip route 10.200.1.0` on R1 returns `% Network not in table`
- [ ] `show ip route 10.100.1.0` on R2 returns `% Network not in table`

### Concept 4 — Loopback Peering

- [ ] `show ip route 10.0.0.2` on R1 returns a static `/32` via 10.1.12.2
- [ ] `show ip route 10.0.0.1` on R2 returns a static `/32` via 10.1.12.1
- [ ] R1 can ping 10.0.0.2; R2 can ping 10.0.0.1
- [ ] `show ip bgp summary` on R1 shows 10.0.0.2 in `Estab`

### Concept 5 — next-hop-self

- [ ] `show ip bgp 10.200.1.0` on R1 shows next-hop 10.0.0.2 (not 10.1.24.2)
- [ ] `show ip bgp 10.100.1.0` on R2 shows next-hop 10.0.0.1 (not 10.1.13.2)
- [ ] R1 can ping 10.200.1.1; R2 can ping 10.100.1.1

### Troubleshooting

- [ ] Ticket 1 resolved — iBGP session restored after fixing loopback peering plumbing (Concept 4)
- [ ] Ticket 2 resolved — R3 receives 192.168.1.0/24 after re-activating the neighbor (Concept 3)
- [ ] Ticket 3 resolved — R2 forwards to 10.100.1.0/24 after restoring `next-hop-self` on R1 (Concept 5)

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
