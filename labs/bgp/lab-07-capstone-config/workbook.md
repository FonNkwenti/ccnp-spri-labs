# BGP Lab 07 — Full Protocol Mastery (Capstone I)

> **Platform Mix Notice (XR-mixed capstone):** R3 (PE East-2 multihome) and
> R4 (P-router / Route Reflector) run **IOS XRv (light, 6.1.x)**; R1, R2, R6
> remain IOSv; R5 and R7 remain CSR1000v. This retrofit exposes you to XR's
> route-reflector configuration model (cluster-id under AF, neighbor-group
> abstraction), mandatory route-policies on every BGP session, and the
> RPL-based community/SOO/extcommunity machinery. IOS commands shown
> throughout still apply on R1/R2/R5/R6/R7; for the XR equivalents on R3 and
> R4, see [Appendix B: XR-side Command Reference](#appendix-b-xr-side-command-reference).
> Status: configs are syntactically translated and need EVE-NG verification.

| Field | Value |
|-------|-------|
| Exam | 300-510 SPRI |
| Chapter | BGP |
| Difficulty | Advanced |
| Estimated Time | 120 minutes |
| Devices | R1, R2, R3, R4, R5, R6, R7 (7 total) |
| Type | Capstone I — configuration from scratch |
| Prerequisites | Labs 00–05 (BGP foundations through communities/FlowSpec) |
| Baseline | Clean slate — interfaces and IP addresses only |

---

## 1. Lab Overview

This is the BGP configuration capstone. You will build a complete production
service-provider control plane that integrates **every BGP feature** from the
preceding labs in this topic. The lab does not walk you through individual
tasks; it presents nine operational scenarios drawn from real-world SP
engineering and you implement the design that satisfies each one.

The clean-slate baseline gives you only IP addressing on each router.
Everything else — OSPF, BGP, route reflection, multihoming, peer hardening,
communities, dampening, dynamic neighbors, and FlowSpec address-family
peering — you build.

---

## 2. Topology

```
                        AS 65001 (Customer A)
                              ┌────────┐
                              │   R1   │
                              │  CE    │
                              └────────┘
                       L1 │   L2 │   L8 │
              10.1.12.0/24│ 10.1.13.0/24│ 10.99.0.0/30
                          │      │      │ (dynamic-neighbor)
                          ▼      ▼      ▼
              ┌──────────────────────────────────────────┐
              │              AS 65100 (SP Core)          │
              │                                          │
              │  ┌────────┐                  ┌────────┐  │
              │  │   R2   │                  │   R3   │  │
              │  │ PE-E1  │── L6 (10.1.23) ──│ PE-E2  │  │
              │  │primary │  OSPF area 0     │backup  │  │
              │  └────┬───┘                  └────┬───┘  │
              │   L3  │ 10.1.24.0/24    10.1.34.0│  L4  │
              │       │   OSPF/iBGP   OSPF/iBGP  │      │
              │       ▼                          ▼      │
              │           ┌────────────────────┐        │
              │           │         R4         │        │
              │           │ P-router / RR      │        │
              │           │ cluster-id 10.0.0.4│        │
              │           └─────────┬──────────┘        │
              │                  L5 │ 10.1.45.0/24      │
              │                     │ OSPF/iBGP         │
              │                     ▼                   │
              │                 ┌────────┐              │
              │                 │   R5   │              │
              │                 │ PE-W   │              │
              │                 │+dampen │              │
              │                 └─┬────┬─┘              │
              └───────────────────┼────┼────────────────┘
                          L7      │    │      L8
                          10.1.56 │    │ 10.1.57
                                  ▼    ▼
                              ┌─────┐ ┌─────┐
                              │ R6  │ │ R7  │
                              │SP   │ │FlowS│
                              │peer │ │pec  │
                              └─────┘ └─────┘
                              AS65002 AS65003
```

**Roles**

- **R1** — Customer-A CE, AS 65001, dual-homed to R2 (primary) and R3 (backup); also originates the dynamic-neighbor session toward R2 over L8.
- **R2** — PE-East-1 in AS 65100. Customer-A primary, dynamic-neighbor listener, RR client of R4.
- **R3** — PE-East-2 in AS 65100. Customer-A backup, RR client of R4.
- **R4** — P-router / route reflector for AS 65100. `cluster-id 10.0.0.4`. No external sessions.
- **R5** — PE-West in AS 65100. Two external peerings (R6, R7), global dampening, FlowSpec AF, RR client of R4.
- **R6** — External SP peer, AS 65002. Originates `172.16.6.0/24` with `no-export`.
- **R7** — Specialty external peer, AS 65003. Originates `172.16.7.0/24` with `no-advertise`. Also a FlowSpec AF peer (origination is IOS-XR-only; R5 enforces, R7 peers).

**Link key**

- **L1** R1↔R2 — eBGP primary
- **L2** R1↔R3 — eBGP backup
- **L3** R2↔R4 — OSPF + iBGP (RR client)
- **L4** R3↔R4 — OSPF + iBGP (RR client)
- **L5** R4↔R5 — OSPF + iBGP (RR client)
- **L6** R2↔R3 — OSPF only (intra-AS IGP path)
- **L7** R5↔R6 — eBGP, MD5, TTL-security
- **L8** R5↔R7 — eBGP, MD5, TTL-security, FlowSpec AF
- **L8 (R1↔R2 second link)** — dynamic-neighbor session inside `10.99.0.0/24` listen range

---

## 3. Addressing Table

IPv4 only. Interface naming reflects the EVE-NG/CSR1000v image as deployed.

| Device | Interface | Address | Role |
|--------|-----------|---------|------|
| R1 | Loopback0 | 10.0.0.1/32 | Router-ID |
| R1 | Loopback1 | 172.16.1.1/24 | Customer-A prefix |
| R1 | Gi0/0 | 10.1.12.1/24 | L1 — eBGP primary to R2 |
| R1 | Gi0/1 | 10.1.13.1/24 | L2 — eBGP backup to R3 |
| R1 | Gi0/2 | 10.99.0.1/30 | L8 — dynamic-neighbor session to R2 |
| R2 | Loopback0 | 10.0.0.2/32 | Router-ID, iBGP source |
| R2 | Gi0/0 | 10.1.12.2/24 | L1 — eBGP to R1 |
| R2 | Gi0/1 | 10.1.24.2/24 | L3 — OSPF + iBGP to R4 |
| R2 | Gi0/2 | 10.1.23.2/24 | L6 — OSPF to R3 |
| R2 | Gi0/3 | 10.99.0.2/30 | L8 — dynamic-neighbor listener |
| R3 | Loopback0 | 10.0.0.3/32 | Router-ID, iBGP source |
| R3 | Gi0/0 | 10.1.13.3/24 | L2 — eBGP backup to R1 |
| R3 | Gi0/1 | 10.1.34.3/24 | L4 — OSPF + iBGP to R4 |
| R3 | Gi0/2 | 10.1.23.3/24 | L6 — OSPF to R2 |
| R4 | Loopback0 | 10.0.0.4/32 | Router-ID, iBGP source, cluster-id |
| R4 | Gi0/0 | 10.1.24.4/24 | L3 — OSPF + iBGP to R2 |
| R4 | Gi0/1 | 10.1.34.4/24 | L4 — OSPF + iBGP to R3 |
| R4 | Gi0/2 | 10.1.45.4/24 | L5 — OSPF + iBGP to R5 |
| R5 | Loopback0 | 10.0.0.5/32 | Router-ID, iBGP source |
| R5 | Gi2 | 10.1.45.5/24 | L5 — OSPF + iBGP to R4 |
| R5 | Gi3 | 10.1.56.5/24 | L7 — eBGP to R6 |
| R5 | Gi4 | 10.1.57.5/24 | L8 — eBGP + FlowSpec to R7 |
| R6 | Loopback0 | 10.0.0.6/32 | Router-ID |
| R6 | Loopback1 | 172.16.6.1/24 | Originated prefix |
| R6 | Gi0/0 | 10.1.56.6/24 | L7 — eBGP to R5 |
| R7 | Loopback0 | 10.0.0.7/32 | Router-ID |
| R7 | Loopback1 | 172.16.7.1/24 | Originated prefix |
| R7 | Gi1 | 10.1.57.7/24 | L8 — eBGP + FlowSpec to R5 |

---

## 4. Prerequisites

- EVE-NG lab imported and all 7 nodes started.
- Initial configs loaded:

```bash
python labs/bgp/lab-07-capstone-config/setup_lab.py --host <eve-ng-ip>
```

- L2 connectivity verified before BGP work begins:

```
R1# ping 10.1.12.2
R1# ping 10.1.13.3
R2# ping 10.1.24.4
R2# ping 10.1.23.3
R3# ping 10.1.34.4
R4# ping 10.1.45.5
R5# ping 10.1.56.6
R5# ping 10.1.57.7
R1# ping 10.99.0.2
```

All pings must succeed before continuing.

---

## 5. Lab Challenge: Full Protocol Mastery

You have **120 minutes**. There is no step-by-step task list. Each scenario
below presents a **Situation**, **Constraints**, and **Acceptance criteria**.
Translate each scenario into configuration on the relevant routers. The
verification matrix in §7 is your contract.

### Scenario A — Customer-A dual-homed with deterministic primary/backup

**Situation.** Customer A (R1, AS 65001) is dual-homed to AS 65100 via R2
(primary, L1) and R3 (backup, L2). The customer's only prefix is
`172.16.1.0/24`. Both providers and the customer must agree that R2 is
preferred in both directions.

**Constraints.**

- AS 65100 must prefer the path via R2 inbound (R2 raises LOCAL_PREF on the customer prefix).
- AS 65001 must prefer return via R2 (R1 sets MED 10 outbound to R2 and MED 50 outbound to R3, plus AS-path prepend `65001 65001` on the R3 path).

**Acceptance criteria.**

1. On R5, `show ip bgp 172.16.1.0/24` lists exactly one best path with `next hop 10.0.0.2` and `LOCAL_PREF 200`.
2. With L1 up, R1 installs `172.16.6.0/24` via 10.1.12.2 (R2), not 10.1.13.3 (R3).

---

### Scenario B — Scale the AS 65100 iBGP control plane

**Situation.** AS 65100 has four iBGP speakers today (R2, R3, R4, R5) and is
expected to grow. A flat full mesh costs `N(N-1)/2` sessions and does not scale.

**Constraints.**

- R4 is the route reflector. `bgp cluster-id 10.0.0.4`.
- R2, R3, R5 are RR clients only — **no client-to-client iBGP sessions**.
- Every iBGP session uses Loopback0 as update-source.
- Every RR client sets `next-hop-self` toward R4 so eBGP-learned next hops are reachable cluster-wide via the IGP.
- `send-community both` on every iBGP session (standard + extended communities must propagate, including SoO from Scenario I).

**Acceptance criteria.**

3. On R4, `show ip bgp summary` lists exactly three iBGP peers (R2, R3, R5), all Established, prefix counts non-zero.
4. On R5, `show ip bgp 172.16.1.0/24` shows `ORIGINATOR_ID 10.0.0.2` and `CLUSTER_LIST 10.0.0.4` (proves reflection through R4).

---

### Scenario C — Harden every external peering

**Situation.** Every eBGP session crosses an administrative boundary and must
be protected from spoofing, off-path injection, and prefix flooding.

**Constraints.**

- TTL-security `hops 1` on **both ends** of every directly connected eBGP session (R1↔R2, R1↔R3, R5↔R6, R5↔R7).
- MD5 password `CISCO_SP` on R5↔R6 and R5↔R7 (both ends).
- `maximum-prefix 100 75 restart 5` on every eBGP session — warn at 75%, hard-stop at 100, auto-restart after 5 minutes.

**Acceptance criteria.**

5. On R5, `show ip bgp neighbors 10.1.56.6` shows TTL-security enabled (incoming TTL ≥ 254), `Connection: Authenticated`, max-prefix 100/75 with restart 5 minutes.
6. The R1↔R2 session does **not** establish if either side's TTL-security is removed (verify by inspection of running-configs; do not deliberately break the lab).

---

### Scenario D — Contain Customer-B routes inside the SP core

**Situation.** R6 (AS 65002) is a peer that advertises `172.16.6.0/24`. The
prefix should reach all SP-internal speakers but must not be re-advertised to
any other external AS.

**Constraints.**

- R6 outbound to R5: set `community no-export` on `172.16.6.0/24` via route-map.
- R5 inbound from R6 may add `no-export additive` defensively (belt-and-suspenders).
- `send-community` must be enabled on R5↔R6 and on every iBGP session that touches the prefix.

**Acceptance criteria.**

7. On R4 (RR), `show ip bgp 172.16.6.0/24` shows the prefix with the `no-export` community attached.
8. On R1 (external to AS 65100), `show ip bgp 172.16.6.0/24` shows the prefix is **not present** (no-export blocked the eBGP advertisement).

---

### Scenario E — Specialty peer R7, consumed once and discarded

**Situation.** R7 (AS 65003) is a one-shot peer whose prefix `172.16.7.0/24`
must be installed at R5 only and never propagated further inside AS 65100 or
to any other peer.

**Constraints.**

- R7 outbound to R5: set `community no-advertise` on `172.16.7.0/24` via route-map.
- `send-community` enabled on R5↔R7.

**Acceptance criteria.**

9. On R5, `show ip bgp 172.16.7.0/24` shows the prefix with the `no-advertise` community.
10. On R4 (one iBGP hop away), `show ip bgp 172.16.7.0/24` shows the prefix is **not present** (no-advertise blocked propagation past R5).

---

### Scenario F — Survive a flapping external prefix

**Situation.** An external prefix on R6 is suspected of frequent up/down
transitions. Repeated SPF and BGP best-path runs across the SP core are
unacceptable.

**Constraints.**

- Apply `bgp dampening 15 750 2000 60` on R5 (router-global → applies to both R5↔R6 and R5↔R7 eBGP-learned prefixes).
- Use defaults: half-life 15 min, reuse 750, suppress 2000, max-suppress 60 min.

**Acceptance criteria.**

11. On R5, `show ip bgp dampening flap-statistics` returns successfully (empty initially).
12. After flapping `interface Loopback1` on R6 five times in 60 s, `show ip bgp dampening dampened-paths` on R5 lists `172.16.6.0/24` as suppressed.

---

### Scenario G — Onboard a new Customer-A site without operator action

**Situation.** Customer A is bringing up a second link toward R2 (the L8 link
in `10.99.0.0/30`). The SP wants the session to come up automatically when
Customer A initiates it — no per-neighbor configuration on R2.

**Constraints.**

- R2 (passive listener): `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` with `remote-as 65001`, `bgp listen limit 10`.
- R1 (active side): static `neighbor 10.99.0.2 remote-as 65100`.
- The `DYN_CUST` peer-group inherits the same inbound policy as Scenario A's primary path.

**Acceptance criteria.**

13. On R2, `show ip bgp peer-group DYN_CUST` lists the dynamic peer `*10.99.0.1` (the asterisk denotes a dynamically-learned member).
14. On R2, `show ip bgp summary` shows the dynamic neighbor in Established state.

---

### Scenario H — FlowSpec peering, ready for future BGP-driven mitigation

**Situation.** R7 will become a future FlowSpec rule originator. R5 must be
ready to receive and enforce FlowSpec NLRI from R7.

> **IOS-XE 17.3.x platform note.** `class-map type traffic` and
> `policy-map type traffic` exist only on IOS-XR; CSR1000v 17.3.x cannot
> originate FlowSpec rules. The deliverable here is **AF peering plus
> enforcement readiness on R5** — `flowspec address-family ipv4 / local-install
> interface-all` in global config. R7 peers in the AF but does not enforce.

**Constraints.**

- Activate `address-family ipv4 flowspec` on R5↔R7 (both sides). Add `neighbor activate` and `send-community both` in the AF.
- On R5 only: enable `flowspec` global submode → `address-family ipv4` → `local-install interface-all`.
- R7 omits `local-install` (does not enforce locally).

**Acceptance criteria.**

15. On R5, `show bgp ipv4 flowspec summary` lists R7 (10.1.57.7) as Established with 0 prefixes.
16. On R5, `show running-config | section flowspec` shows `local-install interface-all` under `flowspec address-family ipv4`.

---

### Scenario I — Site-of-Origin loop guard for Customer A

**Situation.** Customer A is dual-homed; without protection, a route learned
from R1 via L1 could leak back to R1 via L2 (or vice-versa) and cause routing
loops or churn.

**Constraints.**

- R2 inbound from R1: `set extcommunity soo 65001:1` on the Customer-A prefix.
- R3 inbound from R1: `set extcommunity soo 65001:1` on the Customer-A prefix.
- Tag with standard community: R2 sets `65100:100 additive`, R3 sets `65100:200 additive`.

> **Community format note.** On modern IOS-XE 17.3 the `ASN:value` colon
> notation is the default. `ip bgp-community new-format` is **not required**
> globally — it only matters for routers that match community-lists in
> route-maps. The reference solutions configure it on R2 and R3 defensively;
> R5/R6/R7 work fine without it.

**Acceptance criteria.**

17. On R5, `show ip bgp 172.16.1.0/24` shows `LOCAL_PREF 200`, community `65100:100`, and extcommunity `SoO:65001:1` (path via R2).
18. On R1, the customer prefix is never re-advertised back to itself by either R2 or R3 (verified by route-maps; R1 does not see `172.16.1.0/24` from R2 or R3 in `show ip bgp`).

---

## 6. Blueprint Coverage

| Blueprint Ref | Topic | Scenario(s) |
|---------------|-------|-------------|
| 2.1 | BGP path attributes & best-path selection | A (LOCAL_PREF, MED, AS-path), B (ORIGINATOR_ID, CLUSTER_LIST) |
| 2.2 | iBGP scaling — route reflection | B |
| 2.3 | eBGP peer hardening — TTL-security, MD5, max-prefix | C |
| 2.4 | BGP communities — standard & extended | D, E, I |
| 2.5 | Site-of-Origin (SoO) | I |
| 2.6 | BGP route flap dampening | F |
| 2.7 | BGP dynamic neighbors | G |
| 2.8 | BGP FlowSpec — AF peering & enforcement | H |

---

## 7. Verification

### 7.0 Verification Matrix (summary checklist)

| # | Device | Command | Expected |
|---|--------|---------|----------|
| 1 | R4 | `show ip ospf neighbor` | 3 FULL adjacencies (R2, R3, R5) |
| 2 | R4 | `show ip bgp summary` | 3 iBGP peers Established; prefix counts non-zero |
| 3 | R4 | `show ip bgp 172.16.1.0/24` | `ORIGINATOR_ID 10.0.0.2`; `CLUSTER_LIST 10.0.0.4` |
| 4 | R5 | `show ip bgp 172.16.1.0/24` | `LOCAL_PREF 200`; community `65100:100`; SoO `65001:1` |
| 5 | R5 | `show ip bgp neighbors 10.1.56.6` | TTL=254 in, MD5 enabled, max-prefix 100/75 restart 5 |
| 6 | R5 | `show ip bgp dampening flap-statistics` | Empty initially; populates after a flap |
| 7 | R2 | `show ip bgp peer-group DYN_CUST` | Dynamic peer `*10.99.0.1` listed |
| 8 | R1 | `show ip bgp 172.16.6.0/24` | Not present (no-export blocked it at R5/AS-edge) |
| 9 | R5 | `show bgp ipv4 flowspec summary` | R7 Established, 0 prefixes (origination is IOS-XR) |
| 10 | R5 | `show bgp ipv4 flowspec` | Empty table on IOS-XE 17.3.x |
| 11 | R5 | `show running-config \| section flowspec` | `local-install interface-all` present |
| 12 | R1 | `show ip bgp 172.16.6.0/24` | Best path via R2 (LOCAL_PREF / MED preferred) |

### 7.1 OSPF Adjacencies (IGP for iBGP next-hop reachability)

```
R4# show ip ospf neighbor
```

Expected: three FULL adjacencies — R2 on Gi0/0, R3 on Gi0/1, R5 on Gi0/2.

```
R5# show ip route ospf
```

Expected: `O 10.0.0.2/32`, `O 10.0.0.3/32`, `O 10.0.0.4/32` (RR clients reach
each other's loopbacks, which is what makes `next-hop-self` over RR work).

### 7.2 iBGP Route Reflection

```
R4# show ip bgp summary
```

Expected: three iBGP peers (10.0.0.2, 10.0.0.3, 10.0.0.5), all Established,
prefix counts non-zero.

```
R5# show ip bgp 172.16.1.0/24
```

Expected output includes:

```
  Refresh Epoch 1
  65001
    10.0.0.2 (metric 3) from 10.0.0.4 (10.0.0.4)
      Origin IGP, metric 10, localpref 200, valid, internal, best
      Originator: 10.0.0.2, Cluster list: 0A:00:00:04
      Community: 65100:100
      Extended Community: SoO:65001:1
```

The `Originator` and `Cluster list` lines prove the path was reflected by R4.

### 7.3 Multihoming — LOCAL_PREF, MED, AS-path

```
R5# show ip bgp 172.16.1.0/24
R3# show ip bgp 172.16.1.0/24
```

Expected: R3's local view shows the same prefix with `LOCAL_PREF 100`
(default) and AS-path `65001 65001 65001` (one origin + two prepends from R1)
— marked **not** best because R2's path with LOCAL_PREF 200 wins on R4 and is
reflected to R3.

```
R1# show ip bgp 172.16.6.0/24
```

Expected: best path via 10.1.12.2 (R2). The R3 alternate carries MED 50 (set
by R3 outbound? — note: R6's prefix only enters AS 65100 via R5; R1 sees it
through whichever AS-65100 path wins, which is via R2 as primary).

### 7.4 eBGP Hardening — TTL-Security and MD5

```
R5# show ip bgp neighbors 10.1.56.6
```

Expected fragments:

```
  BGP neighbor is 10.1.56.6,  remote AS 65002, external link
  Neighbor sessions:
    1 active, is multisession capable
  Connection state is ESTAB, ... Connection is ECN Disabled
  ... Connection is authenticated using MD5
  ... Maximum prefixes allowed 100 (warning-only is OFF)
  ... Threshold for warning message 75%
  ... Restart in 5 minutes
  ... Minimum incoming TTL 254, Outgoing TTL 255
```

The `Minimum incoming TTL 254` line confirms TTL-security `hops 1` is active.
`authenticated using MD5` confirms the password.

### 7.5 Dampening

```
R5# show ip bgp dampening flap-statistics
```

Expected: header row only, no entries (no flaps yet).

Then trigger a flap on R6:

```
R6# configure terminal
R6(config)# interface Loopback1
R6(config-if)# shutdown
R6(config-if)# no shutdown
! repeat 4 more times within 60 seconds
```

```
R5# show ip bgp dampening dampened-paths
```

Expected: `172.16.6.0/24` listed as suppressed with a non-zero penalty above
the suppress threshold (2000).

### 7.6 Dynamic Neighbors

```
R2# show ip bgp peer-group DYN_CUST
```

Expected: peer-group `DYN_CUST` listed; member `*10.99.0.1` (asterisk = dynamic).

```
R2# show ip bgp summary
```

Expected: a row for `*10.99.0.1` in Established state, AS 65001.

### 7.7 Communities and SoO

```
R4# show ip bgp 172.16.6.0/24
```

Expected: prefix present with community `no-export`. (R4 still installs it;
the `no-export` only prevents AS-external advertisement, not iBGP propagation.)

```
R1# show ip bgp 172.16.6.0/24
```

Expected: **not present** — `no-export` stopped AS 65100 from re-advertising
this prefix back to AS 65001.

```
R4# show ip bgp 172.16.7.0/24
```

Expected: **not present** — `no-advertise` stopped R5 from sending it on iBGP.

```
R5# show ip bgp 172.16.1.0/24
```

Expected: shows `Community: 65100:100`, `Extended Community: SoO:65001:1`.

### 7.8 FlowSpec AF

```
R5# show bgp ipv4 flowspec summary
```

Expected: R7 (10.1.57.7) Established, 0 prefixes received.

```
R5# show running-config | section flowspec
```

Expected:

```
flowspec
 address-family ipv4
  local-install interface-all
 exit-address-family
```

Empty FlowSpec NLRI table is correct on this platform — R7 cannot originate.

---

## 8. Solutions

The reference configurations are inlined below. Resist peeking until you have
attempted each scenario.

<details>
<summary>R1 — Customer-A CE (AS 65001)</summary>

```
hostname R1
!
no ip domain lookup
!
interface Loopback0
 ip address 10.0.0.1 255.255.255.255
 no shutdown
!
interface Loopback1
 ip address 172.16.1.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/0
 description Link to R2 PE-East-1 (L1 eBGP primary)
 ip address 10.1.12.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Link to R3 PE-East-2 (L2 eBGP backup)
 ip address 10.1.13.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Dynamic-Neighbor demo link to R2 (L8)
 ip address 10.99.0.1 255.255.255.252
 no shutdown
!
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24
!
route-map TO-R2-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set metric 10
!
route-map TO-R2-PRIMARY permit 20
!
route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set metric 50
 set as-path prepend 65001 65001
!
route-map TO-R3-BACKUP permit 20
!
router bgp 65001
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65100
 neighbor 10.1.12.2 description PE-East-1-R2-eBGP-primary
 neighbor 10.1.12.2 ttl-security hops 1
 neighbor 10.1.13.3 remote-as 65100
 neighbor 10.1.13.3 description PE-East-2-R3-eBGP-backup
 neighbor 10.1.13.3 ttl-security hops 1
 neighbor 10.99.0.2 remote-as 65100
 neighbor 10.99.0.2 description R2-DynamicRange-listen-port
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  neighbor 10.1.12.2 activate
  neighbor 10.1.12.2 route-map TO-R2-PRIMARY out
  neighbor 10.1.13.3 activate
  neighbor 10.1.13.3 route-map TO-R3-BACKUP out
  neighbor 10.99.0.2 activate
 exit-address-family
!
end
```

</details>

<details>
<summary>R2 — PE-East-1 / Customer-A primary / dynamic-neighbor listener (AS 65100)</summary>

```
hostname R2
!
no ip domain lookup
!
ip bgp-community new-format
!
interface Loopback0
 ip address 10.0.0.2 255.255.255.255
 no shutdown
!
interface GigabitEthernet0/0
 description Link to R1 Customer-A-CE (L1 eBGP primary)
 ip address 10.1.12.2 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Link to R4 P-router/RR (L3 OSPF/iBGP)
 ip address 10.1.24.2 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Link to R3 PE-East-2 (L6 OSPF IGP)
 ip address 10.1.23.2 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/3
 description Dynamic-Customer range link to R1 (L8)
 ip address 10.99.0.2 255.255.255.252
 no shutdown
!
router ospf 1
 router-id 10.0.0.2
 network 10.0.0.2 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.23.0 0.0.0.255 area 0
!
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24
!
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1
!
route-map FROM-CUST-A-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set local-preference 200
 set community 65100:100 additive
 set extcommunity soo 65001:1
!
route-map FROM-CUST-A-PRIMARY permit 20
!
router bgp 65100
 bgp router-id 10.0.0.2
 bgp log-neighbor-changes
 bgp listen limit 10
 bgp listen range 10.99.0.0/24 peer-group DYN_CUST
 neighbor DYN_CUST peer-group
 neighbor DYN_CUST remote-as 65001
 neighbor DYN_CUST description Dynamic-Customer-AS65001
 neighbor 10.1.12.1 remote-as 65001
 neighbor 10.1.12.1 description Customer-A-CE-R1
 neighbor 10.1.12.1 ttl-security hops 1
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor DYN_CUST activate
  neighbor DYN_CUST route-map FROM-CUST-A-PRIMARY in
  neighbor 10.1.12.1 activate
  neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in
  neighbor 10.1.12.1 maximum-prefix 100 75 restart 5
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.4 send-community both
 exit-address-family
!
end
```

</details>

<details>
<summary>R3 — PE-East-2 / Customer-A backup (AS 65100)</summary>

```
hostname R3
!
no ip domain lookup
!
ip bgp-community new-format
!
interface Loopback0
 ip address 10.0.0.3 255.255.255.255
 no shutdown
!
interface GigabitEthernet0/0
 description Link to R1 Customer-A-CE (L2 eBGP backup)
 ip address 10.1.13.3 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Link to R4 P-router/RR (L4 OSPF/iBGP)
 ip address 10.1.34.3 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Link to R2 PE-East-1 (L6 OSPF IGP)
 ip address 10.1.23.3 255.255.255.0
 no shutdown
!
router ospf 1
 router-id 10.0.0.3
 network 10.0.0.3 0.0.0.0 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 10.1.23.0 0.0.0.255 area 0
!
ip prefix-list CUST-A-BACKUP seq 5 permit 172.16.1.0/24
!
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1
!
route-map FROM-CUST-A-BACKUP permit 10
 match ip address prefix-list CUST-A-BACKUP
 set community 65100:200 additive
 set extcommunity soo 65001:1
!
route-map FROM-CUST-A-BACKUP permit 20
!
router bgp 65100
 bgp router-id 10.0.0.3
 bgp log-neighbor-changes
 neighbor 10.1.13.1 remote-as 65001
 neighbor 10.1.13.1 description Customer-A-CE-R1-backup
 neighbor 10.1.13.1 ttl-security hops 1
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.1.13.1 activate
  neighbor 10.1.13.1 route-map FROM-CUST-A-BACKUP in
  neighbor 10.1.13.1 maximum-prefix 100 75 restart 5
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.4 send-community both
 exit-address-family
!
end
```

</details>

<details>
<summary>R4 — P-router / Route Reflector (AS 65100, cluster-id 10.0.0.4)</summary>

```
hostname R4
!
no ip domain lookup
!
interface Loopback0
 ip address 10.0.0.4 255.255.255.255
 no shutdown
!
interface GigabitEthernet0/0
 description Link to R2 PE-East-1 (L3 OSPF/iBGP)
 ip address 10.1.24.4 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Link to R3 PE-East-2 (L4 OSPF/iBGP)
 ip address 10.1.34.4 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Link to R5 PE-West (L5 OSPF/iBGP)
 ip address 10.1.45.4 255.255.255.0
 no shutdown
!
router ospf 1
 router-id 10.0.0.4
 network 10.0.0.4 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 10.1.45.0 0.0.0.255 area 0
!
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 bgp cluster-id 10.0.0.4
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 description iBGP-RR-client-R2
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 description iBGP-RR-client-R3
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.5 remote-as 65100
 neighbor 10.0.0.5 description iBGP-RR-client-R5
 neighbor 10.0.0.5 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 route-reflector-client
  neighbor 10.0.0.2 send-community both
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 route-reflector-client
  neighbor 10.0.0.3 send-community both
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.5 route-reflector-client
  neighbor 10.0.0.5 send-community both
 exit-address-family
!
end
```

</details>

<details>
<summary>R5 — PE-West / dampening / FlowSpec enforcer (AS 65100)</summary>

```
hostname R5
!
no ip domain lookup
!
interface Loopback0
 ip address 10.0.0.5 255.255.255.255
 no shutdown
!
interface GigabitEthernet2
 description Link to R4 P-router/RR (L5 OSPF/iBGP)
 ip address 10.1.45.5 255.255.255.0
 no shutdown
!
interface GigabitEthernet3
 description Link to R6 External-SP-Peer (L7 eBGP)
 ip address 10.1.56.5 255.255.255.0
 no shutdown
!
interface GigabitEthernet4
 description Link to R7 External-Peer-AS65003 (L8 eBGP FlowSpec)
 ip address 10.1.57.5 255.255.255.0
 no shutdown
!
router ospf 1
 router-id 10.0.0.5
 network 10.0.0.5 0.0.0.0 area 0
 network 10.1.45.0 0.0.0.255 area 0
!
ip prefix-list EXT-PEER-R6 seq 5 permit 172.16.6.0/24
!
route-map FROM-R6-APPLY-NOEXP permit 10
 match ip address prefix-list EXT-PEER-R6
 set community no-export additive
!
route-map FROM-R6-APPLY-NOEXP permit 20
!
router bgp 65100
 bgp router-id 10.0.0.5
 bgp log-neighbor-changes
 bgp dampening 15 750 2000 60
 neighbor 10.1.56.6 remote-as 65002
 neighbor 10.1.56.6 description External-SP-Peer-R6
 neighbor 10.1.56.6 ttl-security hops 1
 neighbor 10.1.56.6 password CISCO_SP
 neighbor 10.1.57.7 remote-as 65003
 neighbor 10.1.57.7 description External-Peer-R7-AS65003-FlowSpec
 neighbor 10.1.57.7 ttl-security hops 1
 neighbor 10.1.57.7 password CISCO_SP
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 description iBGP-RR-R4
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.1.56.6 activate
  neighbor 10.1.56.6 route-map FROM-R6-APPLY-NOEXP in
  neighbor 10.1.56.6 maximum-prefix 100 75 restart 5
  neighbor 10.1.56.6 send-community both
  neighbor 10.1.57.7 activate
  neighbor 10.1.57.7 maximum-prefix 100 75 restart 5
  neighbor 10.1.57.7 send-community both
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.4 send-community both
 exit-address-family
 !
 address-family ipv4 flowspec
  neighbor 10.1.57.7 activate
  neighbor 10.1.57.7 send-community both
 exit-address-family
!
flowspec
 address-family ipv4
  local-install interface-all
 exit-address-family
!
end
```

</details>

<details>
<summary>R6 — External SP peer (AS 65002, no-export)</summary>

```
hostname R6
!
no ip domain lookup
!
interface Loopback0
 ip address 10.0.0.6 255.255.255.255
 no shutdown
!
interface Loopback1
 ip address 172.16.6.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/0
 description Link to R5 PE-West (L7 eBGP)
 ip address 10.1.56.6 255.255.255.0
 no shutdown
!
ip prefix-list R6-PREFIX seq 5 permit 172.16.6.0/24
!
route-map TO-R5-NOEXPORT permit 10
 match ip address prefix-list R6-PREFIX
 set community no-export
!
route-map TO-R5-NOEXPORT permit 20
!
router bgp 65002
 bgp router-id 10.0.0.6
 bgp log-neighbor-changes
 neighbor 10.1.56.5 remote-as 65100
 neighbor 10.1.56.5 description SP-Core-PE-West-R5
 neighbor 10.1.56.5 ttl-security hops 1
 neighbor 10.1.56.5 password CISCO_SP
 !
 address-family ipv4
  network 172.16.6.0 mask 255.255.255.0
  neighbor 10.1.56.5 activate
  neighbor 10.1.56.5 route-map TO-R5-NOEXPORT out
  neighbor 10.1.56.5 maximum-prefix 100 75 restart 5
  neighbor 10.1.56.5 send-community
 exit-address-family
!
end
```

</details>

<details>
<summary>R7 — Specialty external peer (AS 65003, no-advertise + FlowSpec AF)</summary>

```
hostname R7
!
no ip domain lookup
!
interface Loopback0
 ip address 10.0.0.7 255.255.255.255
 no shutdown
!
interface Loopback1
 ip address 172.16.7.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet1
 description Link to R5 PE-West AS65100 (L8 eBGP FlowSpec)
 ip address 10.1.57.7 255.255.255.0
 no shutdown
!
ip prefix-list R7-PREFIX seq 5 permit 172.16.7.0/24
!
route-map TO-R5-NOADVERTISE permit 10
 match ip address prefix-list R7-PREFIX
 set community no-advertise
!
route-map TO-R5-NOADVERTISE permit 20
!
! Note: class-map/policy-map type traffic do not exist on IOS-XE 17.3.x (IOS-XR only).
! R7 establishes FlowSpec AF peering only. No local rule origination or enforcement.
router bgp 65003
 bgp router-id 10.0.0.7
 bgp log-neighbor-changes
 neighbor 10.1.57.5 remote-as 65100
 neighbor 10.1.57.5 description PE-West-R5-AS65100
 neighbor 10.1.57.5 ttl-security hops 1
 neighbor 10.1.57.5 password CISCO_SP
 !
 address-family ipv4 unicast
  network 172.16.7.0 mask 255.255.255.0
  neighbor 10.1.57.5 activate
  neighbor 10.1.57.5 route-map TO-R5-NOADVERTISE out
  neighbor 10.1.57.5 maximum-prefix 100 75 restart 5
  neighbor 10.1.57.5 send-community both
 exit-address-family
 !
 address-family ipv4 flowspec
  neighbor 10.1.57.5 activate
  neighbor 10.1.57.5 send-community both
 exit-address-family
!
end
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
R6# copy running-config startup-config
R7# copy running-config startup-config
```

In EVE-NG: stop nodes, then export the lab to save all node states.

To reset to the clean-slate baseline between full repeats:

```bash
python labs/bgp/lab-07-capstone-config/setup_lab.py --host <eve-ng-ip>
```

The script overwrites running-config on every device with the contents of
`initial-configs/`.

---

## 10. Troubleshooting Scenarios

Three pre-built fault scripts in `scripts/fault-injection/` exercise diagnosis
skills after the build. Each script injects one fault on one device;
`apply_solution.py` resets to the clean solution.

### Scenario 1 — iBGP routes not best at R5 (RR client next-hop unreachable)

```bash
python scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
```

**Symptom.** R5 has BGP routes for `172.16.1.0/24` but they are not installed
as best paths. `show ip bgp 172.16.1.0/24` shows the path but no `>` (best)
flag. `show ip route 172.16.1.0` returns no match.

**Hint.** A reflected eBGP route arrives at the client with the **eBGP next
hop** (the customer's interface address). Without `next-hop-self` somewhere in
the path, the client cannot resolve that next hop. Look at R4's iBGP
configuration toward R5 — what attribute should be present on every reflected
eBGP path so the client always has a reachable next hop?

**Restore.**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

### Scenario 2 — Customer-A community lost between R2 and the rest of AS 65100

```bash
python scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
```

**Symptom.** `show ip bgp 172.16.1.0/24` on R4 (RR) and R5 no longer shows
`Community: 65100:100` on the Customer-A path. LOCAL_PREF and SoO are also
missing.

**Hint.** Communities (standard and extended) are **not** carried over an
iBGP session by default. One specific neighbor command must be present on the
sending side of every session that the community traverses. Check R2's iBGP
configuration toward R4 — what flavor of `send-community` is required when
both standard and extended communities (e.g., SoO) must propagate?

**Restore.**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

### Scenario 3 — R5↔R7 session bounces and stays down (max-prefix triggered)

```bash
python scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>
```

**Symptom.** `show ip bgp summary` on R5 shows R7 (10.1.57.7) cycling between
Idle and Active, never reaching Established. Logs show `%BGP-3-MAXPFXEXCEED`.

**Hint.** Max-prefix has two thresholds — a warning percentage and a hard
limit. When the hard limit is exceeded, the session is torn down and only
restarts if `restart <minutes>` is configured. What value of
`maximum-prefix` would cause this on a peer that originates one or more
prefixes? Check R5's `address-family ipv4` configuration for the
`10.1.57.7` neighbor.

**Restore.**

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

## 11. Further Reading

- Cisco IOS BGP Command Reference (15.x M&T)
- Cisco IOS-XE BGP Configuration Guide 17.3 — *FlowSpec* chapter
- RFC 4271 §9 — BGP Path Attributes
- RFC 4360 — BGP Extended Communities (Site-of-Origin)
- RFC 4456 — BGP Route Reflection
- RFC 2439 — BGP Route Flap Damping
- RFC 5575 / RFC 8955 — Dissemination of Flow Specification Rules
- RFC 7311 — AIGP (informational; not used here but mentioned in the topic)
- CCNP SPRI Official Cert Guide — Chapter 3 (BGP Path Control and Advanced Features)

---

## Appendix B: XR-side Command Reference

R3 (PE East-2) and R4 (P-router / RR) run **IOS XRv (light)** in this
capstone. The IOS show/config commands referenced earlier in the workbook
do not exist on XR — use the equivalents below when working on R3 or R4.
R1, R2, R5 (CSR), R6, and R7 (CSR) are unchanged.

### Why XR here

BGP is platform-agnostic in the 300-510 blueprint, but XR's BGP config model
differs structurally from IOS in three ways CCIE SP candidates must know:
(1) **mandatory route-policies** on every activated AF session — XR drops
silently otherwise; (2) **RPL-based community/extcommunity sets** instead of
IOS `ip community-list` and `route-map set community additive`; (3)
**neighbor-group** as the cleaner replacement for IOS `peer-group`. See
`memory/xr-coverage-policy.md` §2 (XR-mixed posture).

### XR commit model (one-time orientation)

XR uses **candidate / running** with two-stage commit. `commit` applies;
`abort` discards. `show configuration` shows uncommitted diff. `!` is a
comment (use `exit` or `root`).

### IOS → XR command equivalents (R3 / R4 only)

| Purpose | IOS (R1, R2, R5, R6, R7) | IOS XR (R3, R4) |
|---|---|---|
| BGP summary | `show ip bgp summary` | `show bgp ipv4 unicast summary` |
| BGP neighbor detail | `show ip bgp neighbors X.X.X.X` | `show bgp ipv4 unicast neighbors X.X.X.X` |
| BGP table | `show ip bgp` | `show bgp ipv4 unicast` |
| BGP routes from neighbor | `show ip bgp neighbors X received-routes` | `show bgp ipv4 unicast neighbors X received-routes` |
| BGP routes advertised | `show ip bgp neighbors X advertised-routes` | `show bgp ipv4 unicast neighbors X advertised-routes` |
| BGP communities | `show ip bgp community 65100:200` | `show bgp ipv4 unicast community 65100:200` |
| Inspect route-map | `show route-map FROM-CUST-A-BACKUP` | `show route-policy FROM-CUST-A-BACKUP` |
| Inspect community-list | `show ip community-list` | `show rpl community-set` |
| Inspect prefix-list | `show ip prefix-list` | `show rpl prefix-set` |
| Inspect extcommunity | `show ip extcommunity-list` | `show rpl extcommunity-set` |
| RR cluster info | `show ip bgp` (look for cluster-list) | `show bgp ipv4 unicast` (CLUSTER_LIST shown inline) |
| Save | `write memory` | `commit` (auto-persists) |

### IOS → XR config-block equivalents

| Purpose | IOS line | XR equivalent |
|---|---|---|
| Cluster ID | `bgp cluster-id 10.0.0.4` (router level) | `bgp cluster-id 10.0.0.4` (under `router bgp`) |
| RR client | `neighbor X.X.X.X route-reflector-client` (under AF) | `route-reflector-client` (under per-neighbor AF) |
| Send community | `neighbor X send-community both` | (default — communities forwarded unless policy strips them) |
| Set community additive | `route-map: set community 65100:200 additive` | `set community CUST-A-BACKUP-COM additive` (community-set required) |
| Set SOO extcommunity | `route-map: set extcommunity soo 65001:1` | `set extcommunity soo SOO_CUSTA` (extcommunity-set required) |
| Maximum-prefix | `neighbor X maximum-prefix 100 75 restart 5` | `maximum-prefix 100 75 restart 5` (under AF) |
| TTL security | `neighbor X ttl-security hops 1` | `ttl-security` (single hop default) |
| Peer-group / template | `neighbor PG peer-group` | `neighbor-group RR-CLIENTS` |
| Mandatory in/out policy | (not required) | `route-policy PASS in / route-policy PASS out` per AF |

### RPL primer (XR-only concept)

XR replaces IOS `route-map` with **Routing Policy Language** (RPL). Three
named-set types are referenced from policies:

```
prefix-set CUST-A-BACKUP            community-set CUST-A-COM
  172.16.1.0/24                       65100:200
end-set                             end-set

extcommunity-set soo SOO_CUSTA
  65001:1
end-set
```

Sets are referenced by name in `route-policy`:

```
route-policy FROM-CUST-A-BACKUP
  if destination in CUST-A-BACKUP then
    set community CUST-A-COM additive
    set extcommunity soo SOO_CUSTA
  endif
  pass
end-policy
```

The implicit terminal action of a route-policy is **drop** unless `pass` is
the last statement. This is the #1 cause of "BGP session up but no routes"
on XR.

### Verification flow on R3 / R4 (XR-side)

```
RP/0/0/CPU0:R4# show bgp ipv4 unicast summary
RP/0/0/CPU0:R4# show bgp ipv4 unicast neighbors 10.0.0.3
RP/0/0/CPU0:R4# show bgp ipv4 unicast | i CLUSTER_LIST

RP/0/0/CPU0:R3# show bgp ipv4 unicast neighbors 10.1.13.1
RP/0/0/CPU0:R3# show bgp ipv4 unicast neighbors 10.1.13.1 received-routes
RP/0/0/CPU0:R3# show route-policy FROM-CUST-A-BACKUP
RP/0/0/CPU0:R3# show bgp ipv4 unicast 172.16.1.0/24
RP/0/0/CPU0:R3# show rpl community-set CUST-A-BACKUP-COM
```

### Known gaps

- This appendix gives commands, not full per-task XR rewrites.
- The fault-injection scripts (`inject_scenario_*.py`) target IOS syntax for
  R3/R4 — they need translating before the troubleshooting tickets that
  affect R3/R4 will inject on XR. Tickets targeting other devices are
  unaffected.
- XRv (light) does not support BGP FlowSpec controller mode; that role
  remains on R5/R7 (CSR1000v) by design.
- Configs are syntactically translated from the IOS sibling solution but
  have **not yet been verified in EVE-NG**. Expect minor adjustments after
  first boot.
