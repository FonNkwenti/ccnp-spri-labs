# Lab 04 — BGP Dual-CE Full Protocol Mastery (Capstone I)

> **Platform Mix Notice (XR-mixed retrofit, 2026-05-06)**
>
> This capstone runs on a **mixed IOSv + IOS-XRv** topology to expose
> students to the XR-side dual-CE BGP model. Specifically:
>
> | Router | Role | Platform |
> |---|---|---|
> | R1 | Customer CE1 (AS 65001) | **IOS XRv (light, 6.1.x)** |
> | R2 | Customer CE2 (AS 65001) | **IOS XRv (light, 6.1.x)** |
> | R3 | ISP-A PE (AS 65100) | IOSv |
> | R4 | ISP-B PE (AS 65200) | IOSv |
> | R5 | ISP-A internal | IOSv |
> | R6 | ISP-B internal | IOSv |
>
> The CE pair is intentionally on XR — it's where the policy-heavy work
> lives (transit prevention, AS-path prepend, LOCAL_PREF inbound), so XR's
> RPL syntax gets the most exposure. ISP routers stay on IOSv.
>
> **Status:** syntactically translated, **needs EVE-NG verification**.
> See **Appendix B** for the IOS↔XR command map and known gaps.


| Field | Value |
|---|---|
| Topic | bgp-dual-ce |
| Difficulty | Advanced |
| Type | Capstone I (full protocol mastery) |
| Estimated time | 120 minutes |
| Devices | R1, R2, R3, R4, R5, R6 |
| Blueprint | 1.5.a Route advertisement, 1.5.d Multihoming |
| Baseline | clean slate — interfaces and IP addressing only; no BGP, no policy |

## Table of Contents

1. [Lab Overview](#1-lab-overview)
2. [Topology](#2-topology)
3. [Addressing](#3-addressing)
4. [Prerequisites](#4-prerequisites)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Blueprint Coverage](#6-blueprint-coverage)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions](#8-solutions)
9. [Troubleshooting](#9-troubleshooting)
10. [Lab Teardown](#10-lab-teardown)
11. [Further Reading](#11-further-reading)

---

## 1. Lab Overview

This is the dual-CE multihoming capstone. You will build a complete dual-CE / dual-ISP
BGP topology from a clean slate where only interface addressing has been pre-loaded.
A single customer AS (65001) connects to two unrelated upstream providers — ISP-A
(AS 65100) and ISP-B (AS 65200) — through two separate customer edge routers (R1 and
R2). The two CEs run iBGP between themselves so each CE has full visibility into the
other ISP's routes.

By the end of the lab the customer AS must:

- exchange routes with both ISPs over eBGP and run iBGP across the CE-CE link,
- never act as transit between ISP-A and ISP-B,
- prefer ISP-A for inbound traffic to the 192.168.1.0/24 aggregate by lengthening the
  AS-path advertised toward ISP-B,
- have each CE locally prefer its directly-connected ISP for outbound traffic by
  raising LOCAL_PREF on inbound advertisements,
- distribute traffic between the two ISPs by selectively advertising 192.168.1.0/25
  toward ISP-A and 192.168.1.128/25 toward ISP-B in addition to the /24 aggregate.

This capstone exercises every dual-CE skill drilled in labs 00–03 in a single sitting.
There are no walkthrough hints inside the task list — each task names the outcome and
points you at a verification line. If you get stuck, the cheatsheet in Section 7 lists
the show commands that prove each behavior, and Section 8 contains complete reference
configurations.

## 2. Topology

```
┌────────────────────┐           ┌────────────────────┐
│   ISP-A (AS 65100) │           │   ISP-B (AS 65200) │
│ ┌────┐    ┌────┐   │           │   ┌────┐    ┌────┐ │
│ │ R5 │iBGP│ R3 │   │           │   │ R4 │iBGP│ R6 │ │
│ │Lo1 │────│Lo1 │   │           │   │Lo1 │────│Lo1 │ │
│ └────┘    └─┬──┘   │           │   └─┬──┘    └────┘ │
└─────────────┼──────┘           └─────┼──────────────┘
              │ eBGP                   │ eBGP
              │ AS 65100↔65001         │ AS 65200↔65001
              │                        │
              ▼                        ▼
┌──────────────────────────────────────────────────┐
│        Customer AS 65001 — PI 192.168.1.0/24     │
│ ┌──────┐                              ┌──────┐   │
│ │  R1  │◄───────── iBGP ─────────────►│  R2  │   │
│ │ CE1  │           Lo0↔Lo0            │ CE2  │   │
│ │Lo1=  │        next-hop-self         │      │   │
│ │.1/24 │                              │      │   │
│ └──────┘                              └──────┘   │
└──────────────────────────────────────────────────┘
```

Key relationships:

- R1 and R2 are in the same customer AS (65001) and run iBGP using their loopbacks as
  source. Each CE sets `next-hop-self` so the other CE can reach iBGP-learned external
  prefixes without depending on an IGP that carries the eBGP peer subnet.
- R3 and R5 are inside ISP-A (AS 65100); R4 and R6 are inside ISP-B (AS 65200). The
  PE-internal iBGP sessions exist so that the inner ISP routers (R5, R6) advertise
  their representative prefixes back into the customer-facing PE.
- There is no link between ISP-A and ISP-B. The only path between them in this lab is
  through the customer AS — which the transit-prevention policy must close.

## 3. Addressing

### Loopbacks

| Device | Lo0 (router-id) | Lo1 (representative prefix) |
|---|---|---|
| R1 | 10.0.0.1/32 | 192.168.1.1/24 (customer prefix, physical Lo) |
| R2 | 10.0.0.2/32 | (none — /24 originated via Null0 + `network`) |
| R3 | 10.0.0.3/32 | 10.100.1.1/24 |
| R4 | 10.0.0.4/32 | 10.200.1.1/24 |
| R5 | 10.0.0.5/32 | 10.100.2.1/24 |
| R6 | 10.0.0.6/32 | 10.200.2.1/24 |

### Point-to-point links

| Link | Endpoints | Subnet | Purpose |
|---|---|---|---|
| L1 | R1 Gi0/0 ↔ R3 Gi0/0 | 10.1.13.0/30 | eBGP customer↔ISP-A |
| L2 | R2 Gi0/0 ↔ R4 Gi0/0 | 10.1.24.0/30 | eBGP customer↔ISP-B |
| L3 | R1 Gi0/1 ↔ R2 Gi0/1 | 10.1.12.0/30 | CE-CE iBGP |
| L4 | R3 Gi0/1 ↔ R5 Gi0/0 | 10.1.35.0/30 | ISP-A internal iBGP |
| L5 | R4 Gi0/1 ↔ R6 Gi0/0 | 10.1.46.0/30 | ISP-B internal iBGP |

The lower-numbered router in each link owns `.1`; the higher-numbered owns `.2`.

## 4. Prerequisites

### Is pre-loaded for you

- Hostnames on every device (R1 through R6).
- All physical interfaces brought up with the IP addresses listed in Section 3.
- Loopback0 (router-id) and the representative loopback (Lo1) addressed and up on
  every device that has one.
- `no ip domain-lookup` so mistyped commands do not stall the console.
- A small set of host static routes that allow the loopbacks of iBGP peers to be
  reached over the directly-connected link they share. These are present so you do
  not need to deploy an IGP to make iBGP `update-source Loopback0` work.

### Is NOT pre-loaded — you must configure

- Any `router bgp …` process on any device.
- Any BGP neighbor relationship — eBGP or iBGP.
- The `network` statement that originates 192.168.1.0/24 on R1.
- The `ip route 192.168.1.0/24 Null0` aggregate-anchor on R2 (R2 has no Lo1).
- The two Null0 anchors on R1 and R2 for the /25 selective advertisements.
- Any prefix list, route-map, or BGP attribute manipulation.
- The `network` statements on R3, R4, R5, R6 that originate the ISP representative
  prefixes.

## 5. Lab Challenge: Full Protocol Mastery

Build the dual-CE BGP topology from scratch. Tasks are listed in the order that will
let you verify each layer before moving to the next — do not skip ahead, because a
broken iBGP session in Task 1 will mask outcomes in every later task.

### Task 1 — Bring up the customer-internal iBGP session

On R1 and R2, configure the BGP process for AS 65001 and establish an iBGP session
between them. The session must use each router's Loopback0 as the BGP source address
and advertise the next-hop as self when readvertising eBGP-learned prefixes to the
peer. Disable the default IPv4-unicast neighbor activation behavior so neighbors are
explicitly activated under the address-family.

**Verification.** `show bgp ipv4 unicast summary` on either CE shows the iBGP peer
in `Established` state with a non-zero uptime.

### Task 2 — Bring up both eBGP edges

Configure the eBGP session R1↔R3 (between AS 65001 and AS 65100) and the eBGP session
R2↔R4 (between AS 65001 and AS 65200). Use the directly-connected interface address
as the neighbor on both ends — do not use loopbacks for eBGP in this lab.

**Verification.** Both CEs show one iBGP peer plus one eBGP peer in `Established`
state. R3 and R4 each show one eBGP peer to the customer AS.

### Task 3 — Bring up the ISP-internal iBGP sessions

On R3↔R5 (inside AS 65100) and on R4↔R6 (inside AS 65200), configure iBGP using
Loopback0 as source on both ends and `next-hop-self` from the PE (R3, R4) toward the
internal peer.

**Verification.** R3 has two BGP neighbors in `Established` — one eBGP to R1 and one
iBGP to R5. R4 has two — one eBGP to R2 and one iBGP to R6.

### Task 4 — Originate the customer aggregate from both CEs

On R1, originate 192.168.1.0/24 into BGP using a `network` statement matched against
the existing Loopback1. On R2, originate the same /24 prefix using a `network`
statement matched against a Null0 static route you must add.

**Verification.** R3 (`show bgp ipv4 unicast 192.168.1.0/24`) sees the prefix from
R1 with AS-path `65001`. R4 sees it from R2 with the same AS-path. Both ISPs receive
the customer aggregate.

### Task 5 — Originate the ISP representative prefixes

On R3, R4, R5, R6, originate the relevant Lo1 representative prefix listed in
Section 3 into BGP using `network` statements.

**Verification.** Both CEs (R1 and R2) see all four ISP-side prefixes — 10.100.1.0/24
and 10.100.2.0/24 from ISP-A, 10.200.1.0/24 and 10.200.2.0/24 from ISP-B — in their
BGP table. R1 receives the ISP-A prefixes via eBGP and the ISP-B prefixes via iBGP
from R2; R2 sees the mirror image.

### Task 6 — Block transit through the customer AS

The customer must never carry traffic between ISP-A and ISP-B. Build outbound
filtering on R1 (toward R2, the iBGP peer) and on R2 (toward R4, the eBGP peer) so
that only the customer-owned 192.168.1.0/24 prefix and its more-specifics may leave
the customer AS in either direction. Use a prefix list referenced from a route-map
applied outbound on the relevant neighbor.

**Verification.** From R4, `show bgp ipv4 unicast` does not show any 10.100.0.0/16
prefixes received from R2. From R3, the same view does not show any 10.200.0.0/16
prefixes received from R1.

### Task 7 — Bias inbound traffic toward ISP-A

On R2, modify the outbound policy toward R4 (built in Task 6) so that the customer
prefixes leave R2 with one extra copy of AS 65001 prepended to the AS-path. ISP-A
remains unmodified.

**Verification.** From R4, the customer aggregate received from R2 has AS-path
`65200 65001 65001`. From R3, the same prefix received from R1 has AS-path
`65100 65001`. ISP-A's path is shorter, so any router in either ISP that hears both
copies (notably R5 and R6 once routes propagate beyond this lab boundary in
production) will prefer the path through ISP-A.

### Task 8 — Bias outbound traffic locally on each CE

On R1, build an inbound route-map from R3 that sets LOCAL_PREF to 200 on every prefix
received. On R2, build the same construction inbound from R4. Apply these route-maps
under the IPv4 unicast address-family of each eBGP neighbor.

**Verification.** On R1, `show bgp ipv4 unicast 10.100.1.0/24` shows two paths — one
via R3 with LOCAL_PREF 200, one via R2 (the iBGP path) with the default 100; R1
selects the eBGP path through R3. On R2, the mirror image holds for 10.200.1.0/24:
the eBGP path via R4 wins on LOCAL_PREF.

### Task 9 — Selectively advertise /25 halves

On R1, originate 192.168.1.0/25 in addition to the /24 aggregate. On R2, originate
192.168.1.128/25 in addition to the /24 aggregate. In both cases, anchor the /25
with a Null0 static route, add a `network` statement with the matching mask, and
extend the existing outbound prefix list so the more-specific /25 is permitted out.

**Verification.** R3 has the /25 192.168.1.0/25 in its BGP table (received from R1)
in addition to the /24. R4 has the /25 192.168.1.128/25 (received from R2) in
addition to the /24. The opposite /25 does not appear at the opposite ISP — that is
the load-distribution effect this task produces.

### Task 10 — End-to-end verification

Confirm every behavior the lab requires using the cheatsheet in Section 7. The lab
is complete when:

- All BGP sessions are `Established` (4 sessions on the customer side, 2 on each ISP).
- Every CE has reachability to every Lo1 representative prefix.
- The customer AS does not transit between ISP-A and ISP-B (Task 6 holds in both
  directions).
- AS-path on the /24 received at R4 is one longer than the AS-path on the /24
  received at R3 (Task 7 holds).
- LOCAL_PREF 200 is visible on inbound prefixes on R1 (from R3) and R2 (from R4),
  and each CE's chosen best-path egress is its directly connected ISP for any
  prefix where the eBGP path competes with an iBGP path (Task 8 holds).
- Each ISP receives only the /25 half assigned to it, in addition to the /24
  aggregate (Task 9 holds).

## 6. Blueprint Coverage

| Blueprint bullet | Where in this lab |
|---|---|
| 1.5.a — Route advertisement | Tasks 4, 5, 9 (`network` statement, aggregate vs. more-specific, selective per-neighbor advertisement via outbound prefix list) |
| 1.5.d — Multihoming | Tasks 1–3 (CE-CE iBGP plus dual eBGP edges), Task 6 (transit prevention), Task 7 (AS-path prepend inbound TE), Task 8 (LOCAL_PREF outbound TE), Task 9 (selective /25 split for load distribution) |

## 7. Verification Cheatsheet

The commands below are organized by what they prove. Run them in order — earlier
checks gate later ones.

### 7.1 Session state

| Goal | Where to run | Command |
|---|---|---|
| All BGP sessions on this device are up | every device | `show bgp ipv4 unicast summary` |
| One specific neighbor's session detail | any device | `show bgp ipv4 unicast neighbors <peer-ip>` |
| Confirm capability negotiation succeeded | any device | `show bgp ipv4 unicast neighbors <peer-ip> | include capability` |

Expected counts:

- R1 — 2 neighbors (iBGP to 10.0.0.2, eBGP to 10.1.13.2)
- R2 — 2 neighbors (iBGP to 10.0.0.1, eBGP to 10.1.24.2)
- R3 — 2 neighbors (eBGP to 10.1.13.1, iBGP to 10.0.0.5)
- R4 — 2 neighbors (eBGP to 10.1.24.1, iBGP to 10.0.0.6)
- R5 — 1 neighbor  (iBGP to 10.0.0.3)
- R6 — 1 neighbor  (iBGP to 10.0.0.4)

### 7.2 Prefix advertisement and reception

| Goal | Where to run | Command |
|---|---|---|
| What is the local BGP table? | any device | `show bgp ipv4 unicast` |
| What did this device send to neighbor X? | any device | `show bgp ipv4 unicast neighbors <peer-ip> advertised-routes` |
| What did this device receive from neighbor X? | any device | `show bgp ipv4 unicast neighbors <peer-ip> received-routes` (requires soft-reconfig inbound) or `… routes` for accepted set |
| Is a specific prefix in the table and what attributes? | any device | `show bgp ipv4 unicast 192.168.1.0/24` |

### 7.3 Transit prevention

| Goal | Where to run | Command |
|---|---|---|
| ISP-B receives no ISP-A prefixes through customer | R4 | `show bgp ipv4 unicast | include 10.100.` (must return nothing) |
| ISP-A receives no ISP-B prefixes through customer | R3 | `show bgp ipv4 unicast | include 10.200.` (must return nothing) |
| Outbound filter on R2 is being hit | R2 | `show ip prefix-list CUSTOMER-OUT detail` (counter increments after a session refresh) |

### 7.4 Inbound TE (AS-path prepend)

| Goal | Where to run | Command |
|---|---|---|
| AS-path on customer /24 received from R1 | R3 | `show bgp ipv4 unicast 192.168.1.0/24` — path `65001` |
| AS-path on customer /24 received from R2 | R4 | `show bgp ipv4 unicast 192.168.1.0/24` — path `65001 65001` |

### 7.5 Outbound TE (LOCAL_PREF)

| Goal | Where to run | Command |
|---|---|---|
| LOCAL_PREF on prefixes received from ISP-A | R1 | `show bgp ipv4 unicast 10.100.1.0/24` — `localpref 200` |
| LOCAL_PREF on prefixes received from ISP-B | R2 | `show bgp ipv4 unicast 10.200.1.0/24` — `localpref 200` |
| Best-path goes to local ISP, not via iBGP peer | each CE | `show ip route bgp` — `10.100.x` next-hop is R3 on R1; `10.200.x` next-hop is R4 on R2 |

### 7.6 Selective /25 advertisement

| Goal | Where to run | Command |
|---|---|---|
| ISP-A sees the lower /25 only | R3 | `show bgp ipv4 unicast 192.168.1.0/25` (present); `show bgp ipv4 unicast 192.168.1.128/25` (absent) |
| ISP-B sees the upper /25 only | R4 | `show bgp ipv4 unicast 192.168.1.128/25` (present); `show bgp ipv4 unicast 192.168.1.0/25` (absent) |

### 7.7 Reachability

| Goal | Where to run | Command |
|---|---|---|
| End-to-end customer→ISP-A | R1 | `ping 10.100.2.1 source 192.168.1.1` |
| End-to-end customer→ISP-B | R2 | `ping 10.200.2.1 source 10.0.0.2` |
| Cross-ISP reachability blocked | R5 | `ping 10.200.2.1 source 10.100.2.1` (must fail — no transit) |

## 8. Solutions

Reference configurations for every device. Open the `<details>` block to view the
device you want to compare against. Configurations are also available on disk in
`solutions/{R1..R6}.cfg`.

<details>
<summary>R1 — CE1, AS 65001 (eBGP to ISP-A, iBGP to R2)</summary>

See `solutions/R1.cfg`. Highlights:

- iBGP `neighbor 10.0.0.2` with `update-source Loopback0` and `next-hop-self`.
- eBGP `neighbor 10.1.13.2 remote-as 65100`.
- `network 192.168.1.0 mask 255.255.255.0` (matches Lo1) and
  `network 192.168.1.0 mask 255.255.255.128` (matches Null0 anchor).
- `route-map CUSTOMER-TO-IBGP out` toward R2 and `CUSTOMER-TO-ISPA out` toward R3 —
  both reference prefix-list `CUSTOMER-OUT`.
- `route-map FROM-ISPA-IN in` toward R3 sets `local-preference 200`.
</details>

<details>
<summary>R2 — CE2, AS 65001 (eBGP to ISP-B, iBGP to R1)</summary>

See `solutions/R2.cfg`. Highlights:

- iBGP `neighbor 10.0.0.1` with `update-source Loopback0` and `next-hop-self`.
- eBGP `neighbor 10.1.24.2 remote-as 65200`.
- `ip route 192.168.1.0 255.255.255.0 Null0` and `ip route 192.168.1.128 255.255.255.128 Null0`
  to anchor the `network` statements.
- `route-map CUSTOMER-TO-ISPB out` matches `CUSTOMER-OUT` and `set as-path prepend 65001` —
  this single route-map enforces both transit prevention and inbound TE.
- `route-map FROM-ISPB-IN in` toward R4 sets `local-preference 200`.
</details>

<details>
<summary>R3 — ISP-A PE, AS 65100 (eBGP to R1, iBGP to R5)</summary>

See `solutions/R3.cfg`. Standard PE configuration: one eBGP customer neighbor, one
iBGP neighbor to the ISP-internal router with `next-hop-self`, originate
10.100.1.0/24 with a `network` statement.
</details>

<details>
<summary>R4 — ISP-B PE, AS 65200 (eBGP to R2, iBGP to R6)</summary>

See `solutions/R4.cfg`. Mirror image of R3.
</details>

<details>
<summary>R5 — ISP-A internal, AS 65100</summary>

See `solutions/R5.cfg`. Single iBGP neighbor (R3); originates 10.100.2.0/24.
</details>

<details>
<summary>R6 — ISP-B internal, AS 65200</summary>

See `solutions/R6.cfg`. Mirror of R5.
</details>

## 9. Troubleshooting

This is Capstone I — full-build, no planted faults. Practice diagnosing dual-CE
failure modes in the paired Capstone II:
[`labs/bgp-dual-ce/lab-05-capstone-troubleshooting`](../lab-05-capstone-troubleshooting/).

If you got stuck during this lab, the most common self-inflicted issues are:

- iBGP between R1 and R2 stuck `Idle`/`Active`: the static host route to the peer's
  Lo0 is missing on one side, or `update-source Loopback0` is configured on only one
  end of the session.
- iBGP-learned routes unreachable: `next-hop-self` not configured, so the receiving
  CE is trying to recurse on the eBGP peer's interface address that it has no route
  to.
- ISP-A still seeing 10.200/16 prefixes: the outbound route-map on R1 toward R2 is
  permitting iBGP-learned ISP-B prefixes to come back into R2's table and onward to
  R4. Check that the outbound filter on R1→R2 is set, not just on R2→R4.
- AS-path prepend not visible at R4: the prepend was applied inbound on R2 instead
  of outbound, or it was applied to the iBGP neighbor instead of the eBGP neighbor.

## 10. Lab Teardown

To cleanly remove the work done in this lab and return to the interfaces-only
baseline:

```text
no router bgp 65001          ! on R1, R2
no router bgp 65100          ! on R3, R5
no router bgp 65200          ! on R4, R6
no route-map CUSTOMER-TO-IBGP
no route-map CUSTOMER-TO-ISPA
no route-map CUSTOMER-TO-ISPB
no route-map FROM-ISPA-IN
no route-map FROM-ISPB-IN
no ip prefix-list CUSTOMER-OUT
no ip prefix-list FROM-ISP-A
no ip prefix-list FROM-ISP-B
no ip route 192.168.1.0 255.255.255.0 Null0
no ip route 192.168.1.0 255.255.255.128 Null0
no ip route 192.168.1.128 255.255.255.128 Null0
```

## 11. Further Reading

- RFC 4271 — A Border Gateway Protocol 4 (BGP-4)
- RFC 7454 — BGP operations and security (filtering recommendations)
- Cisco IOS BGP Configuration Guide, Release 15M&T — Configuring BGP and Implementing BGP routing policies chapters
- IRR best current practice — RPKI ROA / origin validation as the modern alternative to manual prefix-list filtering for production deployments

### Appendix — setup_lab.py exit codes

| Exit code | Meaning |
|---|---|
| 0 | All initial-configs loaded successfully |
| 1 | EVE-NG API unreachable or authentication failed |
| 2 | Lab not found on the EVE-NG host (check `--lab-path`) |
| 3 | One or more device config pushes failed (see traceback) |
| 4 | Pre-flight check failed (missing initial-configs/ files) |

---

## Appendix B: IOS-XR Equivalents (R1, R2)

R1 and R2 run IOS XRv. This appendix maps the IOS commands you see in
the workbook tasks to their XR equivalents so you can drive the XR CEs
through the same exercises.

### B.1 XR commit-model orientation

XR uses a two-stage commit. Configuration is staged in a candidate buffer
and only takes effect after `commit`:

```
RP/0/0/CPU0:R1# configure
RP/0/0/CPU0:R1(config)# router bgp 65001
RP/0/0/CPU0:R1(config-bgp)# ...
RP/0/0/CPU0:R1(config-bgp)# commit
RP/0/0/CPU0:R1(config-bgp)# end
```

`abort` discards the candidate. `show configuration` shows pending changes.

### B.2 IOS ↔ XR show command equivalents

| IOS | IOS-XR |
|---|---|
| `show ip interface brief` | `show ipv4 interface brief` |
| `show ip route` | `show route ipv4` |
| `show ip bgp summary` | `show bgp ipv4 unicast summary` |
| `show ip bgp` | `show bgp ipv4 unicast` |
| `show ip bgp neighbors <ip>` | `show bgp ipv4 unicast neighbors <ip>` |
| `show ip bgp neighbors <ip> advertised-routes` | `show bgp ipv4 unicast neighbors <ip> advertised-routes` |
| `show ip bgp neighbors <ip> received-routes` | `show bgp ipv4 unicast neighbors <ip> routes` |
| `show route-map` | `show rpl route-policy` |
| `show ip prefix-list` | `show rpl prefix-set` |
| `show ip bgp regexp <re>` | `show bgp ipv4 unicast regexp <re>` |

### B.3 IOS ↔ XR config-block equivalents

| IOS construct | XR equivalent |
|---|---|
| `ip prefix-list NAME ... permit X` | `prefix-set NAME / X / end-set` |
| `route-map NAME permit N / match / set` | `route-policy NAME / if ... then set ... endif / pass / end-policy` |
| `set local-preference 200` | `set local-preference 200` (same keyword inside RPL) |
| `set as-path prepend 65001` | `prepend as-path 65001 1` |
| `neighbor X route-map M in` | `neighbor X / address-family ipv4 unicast / route-policy M in` |
| `neighbor X next-hop-self` | per-AF: `neighbor X / address-family ipv4 unicast / next-hop-self` |
| `neighbor X send-community` | implicit on XR; communities propagate by default |
| `network X mask Y` | `network X/Y` (slash form, under address-family) |
| `ip route X Y NH` | `router static / address-family ipv4 unicast / X/Y NH` |
| `ip route X Y Null0` | `router static / address-family ipv4 unicast / X/Y Null0` |

### B.4 XR-specific gotchas exercised here

- **Mandatory route-policy on every activated AF.** XR drops prefixes
  silently if a neighbor's AF lacks an `in` or `out` route-policy. The
  R1/R2 solutions install policies explicitly on every AF.
- **Implicit terminal drop.** A route-policy without a final `pass`
  drops everything that didn't match an explicit `pass` clause. Use
  `pass` deliberately.
- **`prepend as-path` syntax.** XR's prepend is `prepend as-path <asn>
  <count>`, not `set as-path prepend <asn>`.
- **Per-AF `next-hop-self`.** Not a global neighbor knob in XR.

### B.5 Known gaps

- This retrofit is **syntactically translated**, not yet EVE-NG verified.
  Boot the lab and report failures so configs can be corrected.
- ISP-side routers (R3, R4, R5, R6) remain IOSv — XR side covers the
  policy-rich CE work; XR-PE behavior is exercised in `bgp/lab-07-capstone-config`.
