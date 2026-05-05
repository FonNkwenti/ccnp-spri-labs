# Lab 04 — BGP Route Filtering and Traffic Steering

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

**Exam Objective:** 3.3 — Implement and troubleshoot BGP route filtering and traffic steering using route-maps, prefix-lists, and IOS-XR RPL

### BGP Inbound and Outbound Filtering

BGP filtering controls which routes are accepted from a peer and which prefixes are advertised to
a peer. IOS supports three mechanisms that can be applied per-neighbor in either direction:

| Mechanism | Match basis | Applied via |
|-----------|-------------|-------------|
| `ip prefix-list` | Prefix + length (exact, `ge`, `le`) | `neighbor X route-map in/out` with `match ip address prefix-list` |
| `ip as-path access-list` | AS-path regex | `neighbor X filter-list N in/out` or `match as-path N` in route-map |
| `ip community-list` | Community value / well-known keyword | `match community N` in route-map |

**Inbound filtering** runs before best-path selection — a denied route is neither installed nor
re-advertised. **Outbound filtering** runs before sending an UPDATE; denied prefixes are
suppressed but remain in the local BGP table.

**`aggregate-address`** summarizes a block into a single prefix. With `summary-only`, BGP
suppresses all covered more-specific prefixes automatically. Without `summary-only`, both the
aggregate and more-specifics are advertised. In both cases the aggregate always carries the
`atomic-aggregate` attribute (signals that path information was lost by aggregation) and the
`aggregator` attribute (identifies the router-id that created it). A null-route is required as
the covering anchor: IOS will not originate the aggregate unless at least one covered prefix
exists in the routing table.

### BGP Traffic Steering Attributes

| Attribute | Scope | Direction | Effect |
|-----------|-------|-----------|--------|
| `LOCAL_PREF` | AS-wide (iBGP) | Inbound (exit selection) | Highest value wins; set on inbound eBGP, propagated to all iBGP peers |
| `AS-path prepend` | Inter-AS | Outbound (ingress influence at remote AS) | Longer path = less preferred; `set as-path prepend` in outbound route-map |
| `MED` | Adjacent ASes only | Outbound (hint to neighboring AS) | Lowest value wins; only compared when paths come from the same neighbor AS |
| Conditional advertisement | N/A | Outbound | `advertise-map non-exist-map` surfaces a backup prefix when a tracked prefix disappears |

**Key gotcha — LOCAL_PREF on eBGP:** LOCAL_PREF is an iBGP attribute and is stripped
before sending an UPDATE to an eBGP peer. A `set local-preference` in an outbound route-map
toward an eBGP neighbor is silently ignored at the remote AS; only `set as-path prepend` or
`set metric` have cross-AS effect.

### Aggregate with `summary-only` vs. Without

Setting `summary-only` on R3 while R1 does not use it creates a visible asymmetry at R4:
R4 sees only the aggregate from R3 but both the aggregate and more-specifics from R1. This
demonstrates that the two knobs are independent per-router and that BGP aggregate suppression
is a local decision, not a domain-wide flag.

### IOS-XR RPL: Community + Prepend in One Policy

IOS-XR RPL can combine multiple `set` operations in a single `if` block. A single
`route-policy` can set community and prepend AS-path simultaneously — no need for two
separate sequences as in an IOS route-map:

```xr
route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_XR1_ORIGINATE then
    set community (65100:300) additive
    prepend as-path 65100 3
  endif
  pass
end-policy
```

The trailing `pass` is mandatory in RPL — without it, unmatched routes are implicitly dropped
(RPL's default drop is the opposite of IOS route-map's implicit permit-all at the end).

**Community inline vs. named-set:** `set community (65100:300) additive` uses parentheses to
declare an inline community literal. Without parentheses — `set community 65100:300` — IOS XR
parses `65100:300` as a reference to a named `community-set`, and BGP will refuse to attach the
policy with the error *"must be defined before [policy] can be attached"*. Use parentheses for
inline literals; use a bare name for references to a defined `community-set`.

### Conditional Advertisement

`neighbor X advertise-map A non-exist-map B` instructs IOS: send the prefixes matched by `A`
to neighbor X *only when* the prefixes matched by `B` are absent from the BGP table. This
implements primary/backup: while the primary aggregate is present, the backup prefix is
suppressed. If the primary disappears (e.g., R3 goes down), the backup surfaces automatically.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| BGP prefix-list inbound filter | Verify FILTER_R4_IN at R1 blocks direct acceptance of 172.20.5.0/24 from R4 eBGP |
| BGP aggregate origination | `aggregate-address` with and without `summary-only`; null-route anchor |
| LOCAL_PREF steering | Inbound route-map at R3 elevates 172.20.4.0/24 LOCAL_PREF to 200 AS-wide |
| AS-path prepend | Outbound route-map at R1 lengthens AS-path for 172.16.1.0/24 toward R4 |
| MED manipulation | Outbound route-maps at R1 (MED 100) and R3 (MED 50) for 172.16.0.0/16 |
| IOS-XR RPL community + prepend | Single policy combining two `set` operations on XR1 |
| Conditional advertisement | Backup prefix surfaces only when primary aggregate is withdrawn |
| BGP troubleshooting | Diagnose policy misapplication using `show route-map`, `show ip bgp`, soft resets |

---

## 2. Topology & Scenario

**Scenario:** SP-CORE's AS 65100 (R1, R2, R3, XR1, XR2) dual-homes to customer AS 65200 (R4)
via two independent eBGP sessions — R1↔R4 on link L4 and R3↔R4 on link L3. The lab-03 IGP
(OSPF area 0 on R1/R2/R3, IS-IS L2 across the full core) and redistribution policies are
already running. Lab-04 builds BGP filtering and traffic-steering policy on top:

- R1 filters R4's 172.20.5.0/24 inbound (verify only — already in place from lab-03)
- Both R1 and R3 originate the 172.16.0.0/16 aggregate; R3 demonstrates `summary-only`
- R3 sets LOCAL_PREF 200 for 172.20.4.0/24, making every AS 65100 router prefer R3 as exit
- R1 prepends AS-path 3× for 172.16.1.0/24 outbound, causing R4 to prefer R3 for that prefix
- R1 (MED 100) and R3 (MED 50) signal R4 to prefer R3 for the 172.16.0.0/16 aggregate
- XR1 demonstrates the RPL equivalent: community + prepend in one compact policy
- R1 conditionally advertises 172.16.100.0/24 to R4 only when R3's aggregate is absent

```
                         ┌──────────────────────┐
                         │         R4           │
                         │    AS 65200          │
                         │  Lo0: 10.0.0.4/32    │
                         │  Lo1: 172.20.4.1/24  │
                         │  Lo2: 172.20.5.1/24  │
                         └────┬──────────┬──────┘
                              │          │
              L4 10.1.14.0/24 │          │ L3 10.1.34.0/24
              eBGP R1↔R4      │          │ eBGP R3↔R4
                              │          │
          ┌───────────────────┘          └───────────────────┐
          │                                                   │
┌─────────┴──────────────┐                   ┌───────────────┴─────────┐
│           R1            │                   │            R3           │
│   AS 65100 eBGP edge    │                   │    AS 65100 eBGP edge   │
│   Lo0: 10.0.0.1/32      │                   │    Lo0: 10.0.0.3/32     │
│   Lo1: 172.16.1.1/24    │                   │                         │
└────┬────────────────────┘                   └───────┬────────────┬────┘
     │  L1 10.1.12.0/24    L5 10.1.13.0/24            │            │
     │  R1-R2              R1-R3 diagonal              │ L2         │ L7
     │                     ┌───────────────────────────┘ 10.1.23   │ 10.1.36
     │                     │                                        │ R3-XR2
┌────┴────────────────────┴──────┐
│              R2                │                ┌────────────────┐
│     AS 65100 OSPF ABR          │                │      XR2       │
│     IS-IS L1-L2 boundary       │                │  IOS XRv 6.3.1 │
│     Lo0: 10.0.0.2/32           │                │  Lo0: 10.0.0.6 │
└────────────────┬───────────────┘                └───────┬────────┘
                 │ L6 10.1.25.0/24 R2-XR1                 │
                 │                                L8 10.1.56.0/24
          ┌──────┴──────────┐                     XR1-XR2 │
          │      XR1        ├─────────────────────────────┘
          │  IOS XRv 6.3.1  │
          │  Lo0: 10.0.0.5  │
          │  Lo1: 172.16.11.1/24
          └─────────────────┘
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | AS |
|--------|------|----------|----|
| R1 | SP core / eBGP edge to R4 | IOSv | 65100 |
| R2 | SP core / OSPF ABR / IS-IS L1-L2 boundary | IOSv | 65100 |
| R3 | SP core / eBGP edge to R4 | IOSv | 65100 |
| R4 | External AS edge / dual-homed CE | IOSv | 65200 |
| XR1 | IOS-XR RPL node / IS-IS L1-2 | IOS XRv (classic) 6.3.1 | 65100 |
| XR2 | IOS-XR RPL node / IS-IS L2 | IOS XRv (classic) 6.3.1 | 65100 |

### Loopback Address Table

| Device | Interface | Address | Purpose |
|--------|-----------|---------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id / iBGP source |
| R1 | Loopback1 | 172.16.1.1/24 | BGP `network` statement; AS-path prepend target |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id |
| R2 | Loopback1 | 10.2.1.2/24 | OSPF area 1 ABR demo (lab-03) |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id |
| R4 | Loopback1 | 172.20.4.1/24 | External prefix 1 — accepted inbound at R1 |
| R4 | Loopback2 | 172.20.5.1/24 | External prefix 2 — filtered inbound at R1 |
| XR1 | Loopback0 | 10.0.0.5/32 | BGP router-id |
| XR1 | Loopback1 | 172.16.11.1/24 | RPL community + prepend demo prefix |
| XR2 | Loopback0 | 10.0.0.6/32 | BGP router-id |

### Cabling Table

| Link | Interface A | Interface B | Subnet | Purpose |
|------|-------------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | Core (OSPF/IS-IS) |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | Core (OSPF/IS-IS) |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | eBGP R3↔R4 |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | eBGP R1↔R4 |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | Core diagonal (OSPF/IS-IS) |
| L6 | R2 Gi0/2 | XR1 Gi0/0/0/0 | 10.1.25.0/24 | IS-IS L1 (R2-XR1) |
| L7 | R3 Gi0/3 | XR2 Gi0/0/0/0 | 10.1.36.0/24 | IS-IS L2 (R3-XR2) |
| L8 | XR1 Gi0/0/0/1 | XR2 Gi0/0/0/1 | 10.1.56.0/24 | XR backbone (IS-IS L2) |

### BGP Prefixes in Play

| Prefix | Origin AS | Advertised by | Lab-04 Treatment |
|--------|-----------|---------------|-----------------|
| 172.16.1.0/24 | 65100 | R1 | AS-path prepend 3× outbound to R4 (Task 4) |
| 172.16.11.0/24 | 65100 | XR1 | RPL community 65100:300 + prepend 3× (Task 6) |
| 172.16.0.0/16 | 65100 | R1, R3 | Aggregate; MED 100 at R1, MED 50 at R3 (Task 5) |
| 172.16.100.0/24 | 65100 | R1 | Conditional backup advertisement (Task 7) |
| 172.20.4.0/24 | 65200 | R4 | Accepted; LOCAL_PREF 200 at R3 (Task 3) |
| 172.20.5.0/24 | 65200 | R4 | Filtered inbound at R1 (Task 1 — verify only) |

### Console Access

| Device | EVE-NG Node Name | Telnet Port |
|--------|------------------|-------------|
| R1 | R1 | auto-discovered by setup_lab.py |
| R2 | R2 | auto-discovered by setup_lab.py |
| R3 | R3 | auto-discovered by setup_lab.py |
| R4 | R4 | auto-discovered by setup_lab.py |
| XR1 | XR1 | auto-discovered by setup_lab.py |
| XR2 | XR2 | auto-discovered by setup_lab.py |

---

## 4. Base Configuration

### IS (pre-loaded from lab-03 solutions)

- OSPFv2 area 0 on R1, R2, R3 (core links L1, L2, L5)
- IS-IS Level-2 across all SP core routers; IS-IS Level-1 on R2↔XR1 (L6)
- Redistribution between OSPF and IS-IS on R2 and R3, tag-based loop prevention
- OSPF ABR filter-list and distribute-list on R2 (area 1 prefix isolation)
- iBGP full mesh in AS 65100 (R1, R2, R3, XR1, XR2) using Loopback0 as source
- eBGP sessions: R1↔R4 (10.1.14.0/24) and R3↔R4 (10.1.34.0/24)
- R1: `FILTER_R4_IN` route-map applied inbound on R4 neighbor — denies 172.20.5.0/24,
  permits 172.20.4.0/24 with community 65100:100 and LOCAL_PREF 150
- R3: `FILTER_R4_ASPATH` route-map applied inbound on R4 neighbor — accepts only
  routes originated in AS 65200 (`_65200$` regex), denies all others
- XR1: `SET_LOCAL_PREF_BY_COMMUNITY` route-policy applied inbound on IBGP neighbor-group —
  matches community 65100:200 and sets local-preference 120

### IS NOT (not yet configured — your tasks)

- No `aggregate-address` on R1 or R3
- No outbound route-maps on R1 or R3 toward R4
- No `STEER_R4_IN` on R3 (LOCAL_PREF 200 for 172.20.4.0/24)
- No AS-path prepend on R1's advertisement to R4
- No MED set on either eBGP outbound session
- No `SET_COMMUNITY_AND_PREPEND` policy on XR1
- No conditional advertisement on R1

---

## 5. Lab Challenge: Core Implementation

### Task 1 — Verify Inbound Prefix-List Filtering at R1

The lab-03 initial config already has `FILTER_R4_IN` applied inbound on R1's R4 neighbor.
Before building anything new, verify the filter is operating correctly.

- On R1, enable soft-reconfiguration inbound on the R4 neighbor so the pre-policy
  Adj-RIB-In is stored locally.
- Run `show ip bgp neighbors 10.1.14.4 received-routes` — both 172.20.4.0/24 and
  172.20.5.0/24 must appear (R4 sends both; this is the raw pre-filter view).
- Run `show ip bgp neighbors 10.1.14.4 routes` — only 172.20.4.0/24 must appear;
  `FILTER_R4_IN` seq 10 denies 172.20.5.0/24 before it enters R1's BGP table.
- Note that `show ip bgp` will still contain 172.20.5.0/24 via next-hop 10.0.0.3 — this
  is expected. R3's inbound filter checks AS-path only, so R3 accepts both prefixes and
  iBGP-propagates them to all AS 65100 peers. The filter governs R1's eBGP session with
  R4 only, not what R3 chooses to accept.
- On R3, run `show ip bgp neighbors 10.1.34.4 routes` to confirm both prefixes are
  accepted there.

**Verification:** `show ip bgp neighbors 10.1.14.4 received-routes` on R1 must show both 172.20.4.0/24 and 172.20.5.0/24 (pre-filter). `show ip bgp neighbors 10.1.14.4 routes` on R1 must show only 172.20.4.0/24 (post-filter). `show ip bgp neighbors 10.1.34.4 routes` on R3 must show both prefixes (R3's AS-path filter does not restrict on prefix).

---

### Task 2 — Originate 172.16.0.0/16 Aggregate on R1 and R3

- On R1, install a null-route for 172.16.0.0/16 pointing to Null0. IOS will not originate
  an aggregate unless at least one covered prefix exists in the routing table.
- Originate the 172.16.0.0/16 aggregate on R1. Do not use `summary-only` — both the
  aggregate and 172.16.1.0/24 should remain visible to R4 from this peer.
- On R3, install the same null-route anchor for 172.16.0.0/16.
- Originate the same 172.16.0.0/16 aggregate on R3, this time with `summary-only`.
  This suppresses all covered more-specific prefixes from R3's advertisements to R4.
- Soft-reset outbound on both peers toward R4 to trigger the advertisement.
- Verify the `summary-only` effect at R4 (see Verification below), then remove `summary-only`
  from R3's aggregate. This is required for Tasks 4 and 5 to produce observable results at R4.

**Verification (with summary-only on R3):** `show ip bgp` on R4 must show 172.16.0.0/16 from both R1 and R3, but only R1 also advertises 172.16.1.0/24 alongside the aggregate. `show ip bgp 172.16.0.0` on R4 must show `atomic-aggregate` on both paths (this is normal for any aggregate) and the `aggregator` attribute identifying each originating router-id. **After removing summary-only:** `show ip bgp` on R4 must show 172.16.1.0/24 visible from both peers.

---

### Task 3 — Set LOCAL_PREF 200 for 172.20.4.0/24 at R3

- On R3, create prefix-list `PFX_PREFER_172_20_4` matching 172.20.4.0/24 exactly.
- Create an AS-path access-list matching routes originated in AS 65200.
- Create route-map `STEER_R4_IN` with three sequences:
  - Seq 10: match prefix-list `PFX_PREFER_172_20_4` → set LOCAL_PREF 200 and community 65100:200
  - Seq 20: match the AS 65200 AS-path ACL → set community 65100:200
  - Seq 30: explicit deny (blocks anything not matched above — i.e., non-AS-65200 routes)
- Replace R3's existing inbound route-map on the R4 neighbor with `STEER_R4_IN`.
- Soft-reset inbound on R3's R4 neighbor.

> **Note — community display format:** IOS renders community values in AA:NN format (e.g.,
> `65100:200`) only when `ip bgp-community new-format` is configured globally. Without it,
> the same value appears as a 32-bit decimal integer (e.g., `4259840200`). This command is
> pre-loaded in the initial configs. If you see decimal values, verify with
> `show running-config | include bgp-community`.

**Verification:** `show ip bgp 172.20.4.0` on R1 must show the best path (`*>i`) with LOCAL_PREF 200 via next-hop 10.0.0.3, and a non-best path via 10.0.0.1 (R1's own eBGP, LOCAL_PREF 150). `show ip bgp 172.20.4.0` on R2 and XR1 must also show the best path via 10.0.0.3. `show route-map STEER_R4_IN` on R3 must show non-zero match counters on the LOCAL_PREF sequence after a soft-reset.

---

### Task 4 — AS-Path Prepend 3× Outbound on R1

- On R1, create prefix-list `PFX_16_1_EXACT` matching 172.16.1.0/24 exactly.
- Create route-map `R1_TO_R4_OUT` with two sequences:
  - Seq 10: match prefix-list `PFX_16_1_EXACT` → prepend AS 65100 three times
  - Seq 30: permit with no match clause (passes all other prefixes unchanged)
- Apply `R1_TO_R4_OUT` outbound on R1's R4 neighbor.
- Soft-reset outbound toward R4.

**Verification:** `show ip bgp 172.16.1.0` on R4 must show the R3 path (`*>`) with AS-path `65100` and the R1 path (`*`) with AS-path `65100 65100 65100 65100`. `show ip bgp neighbors 10.1.14.4 advertised-routes` on R1 must confirm 172.16.1.0/24 is being sent to R4. `show route-map R1_TO_R4_OUT` on R1 must show non-zero match count on seq 10 after the soft-reset.

---

### Task 5 — MED Manipulation for the Aggregate

- On R1, create prefix-list `PFX_16_0_AGGREGATE` matching 172.16.0.0/16 exactly.
- Add a new sequence to the existing `R1_TO_R4_OUT` route-map:
  - Seq 20: match prefix-list `PFX_16_0_AGGREGATE` → set MED 100
- On R3, create route-map `R3_TO_R4_OUT` with two sequences:
  - Seq 10: match prefix-list `PFX_16_0_AGGREGATE` → set MED 50
  - Seq 20: permit with no match clause (passes all other prefixes unchanged)
- Apply `R3_TO_R4_OUT` outbound on R3's R4 neighbor.
- Soft-reset outbound on both R1 and R3 toward R4.

**Verification:** `show ip bgp 172.16.0.0` on R4 must show the R3 path (`*>`) with metric 50 and the R1 path (`*`) with metric 100. `show route-map R1_TO_R4_OUT` on R1 and `show route-map R3_TO_R4_OUT` on R3 must each show non-zero match counts on the MED sequence after soft-resets.

---

### Task 6 — RPL Community + Prepend on XR1

- On XR1, define a prefix-set `P_XR1_ORIGINATE` containing 172.16.11.0/24.
- Create `route-policy SET_COMMUNITY_AND_PREPEND` with the following logic:
  - If destination in `P_XR1_ORIGINATE`: set community `(65100:300)` additive and prepend
    AS 65100 three times. The parentheses are required — `set community (65100:300)` is
    an inline literal; without them XR treats `65100:300` as a named community-set reference
    and will reject the policy attachment with "must be defined before ... can be attached".
  - Trailing `pass` statement — mandatory in RPL; without it, unmatched routes are
    implicitly dropped (the opposite of IOS route-map's implicit permit-all).
- Replace the existing outbound policy on XR1's iBGP neighbor-group with
  `SET_COMMUNITY_AND_PREPEND`.
- Commit the configuration.

> **Note — community display on IOS observers:** XR1 uses AA:NN community format by default.
> IOS routers (R2, R1, R3) require `ip bgp-community new-format` to display the same format —
> without it, `65100:300` appears as a decimal integer. This command is pre-loaded in the
> initial configs.

**Verification:** `show ip bgp 172.16.11.0` on R2 must show community `65100:300` and AS-path `65100 65100 65100 65100` for the path from XR1 (next-hop 10.0.0.5). `show bgp ipv4 unicast neighbors <ibgp-peer> advertised-routes` on XR1 must confirm 172.16.11.0/24 is being sent with the community and prepend attributes.

---

### Task 7 — Conditional Advertisement on R1

- On R1, install a null-route for 172.16.100.0/24 pointing to Null0.
- Originate 172.16.100.0/24 into BGP via a network statement.
- Create prefix-list `PFX_16_100_EXACT` matching 172.16.100.0/24 exactly.
- Create route-map `BACKUP_ADV` with a single permit sequence matching `PFX_16_100_EXACT`.
- Create route-map `TRACK_PRIMARY` with a single permit sequence matching
  `PFX_16_0_AGGREGATE` (172.16.0.0/16 — the prefix that R3's aggregate satisfies).
- Configure conditional advertisement on R1's R4 neighbor: `BACKUP_ADV` as the
  advertise-map and `TRACK_PRIMARY` as the non-exist-map.
- Verify the suppression behavior: while R3's aggregate is present in R1's BGP table,
  172.16.100.0/24 must not appear at R4.
- Test failover: remove R3's aggregate temporarily and confirm 172.16.100.0/24 surfaces
  at R4. Restore R3's aggregate after verification.

**Verification:** `show ip bgp` on R4 must NOT contain 172.16.100.0/24 while R3's aggregate is active. `show ip bgp neighbors 10.1.14.4 advertised-routes` on R1 must also not list 172.16.100.0/24 at this point. After removing R3's aggregate, `show ip bgp` on R4 must show 172.16.100.0/24 learned from R1. Re-add R3's aggregate and confirm 172.16.100.0/24 disappears from R4 again.

---

### Task 8 — Troubleshooting: BGP Policy Faults

Run any one of the three fault scenarios and diagnose the anomaly without reading the solution.
The faults all target BGP policy behavior:

```
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>
```

Primary tools: `show ip bgp <prefix>`, `show route-map <name>`, `show ip bgp neighbors <x>
routes`, `show ip bgp neighbors <x> advertised-routes`, `debug ip bgp <neighbor> updates`.

Restore with: `python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>`

---

## 6. Verification & Analysis

### Task 1 — Inbound Filter at R1

```ios
! On R1: enable soft-reconfiguration to see pre-filter received routes
show ip bgp neighbors 10.1.14.4 received-routes
! ← Both 172.20.4.0/24 and 172.20.5.0/24 appear here (R4 sends both; pre-policy view)

show ip bgp neighbors 10.1.14.4 routes
! ← Only 172.20.4.0/24 appears here (post-inbound-filter; FILTER_R4_IN deny is effective)

show ip bgp
! ← 172.20.4.0/24 present via 10.1.14.4 (R4 eBGP, LOCAL_PREF 150)
! ← 172.20.5.0/24 present via 10.0.0.3 (R3 iBGP, LOCAL_PREF 100) — this is expected.
!    R3 accepts both prefixes and iBGP-propagates them to all AS 65100 peers.
!    The filter controls R1's eBGP session with R4 only — not iBGP from R3.

! On R3: both prefixes accepted (FILTER_R4_ASPATH matches on AS-path, not prefix)
show ip bgp neighbors 10.1.34.4 routes
! ← Both 172.20.4.0/24 and 172.20.5.0/24 present
```

### Task 2 — Aggregate at R4

```ios
! At R4 (while R3 summary-only is active):
show ip bgp
! ← From R3: only 172.16.0.0/16 visible (more-specifics suppressed)
! ← From R1: 172.16.0.0/16 AND 172.16.1.0/24 both visible

show ip bgp 172.16.0.0
! ← Both paths carry atomic-aggregate — this is normal for any aggregate regardless
!    of summary-only. atomic-aggregate signals that path info was lost during aggregation.
! ← The aggregator attribute differs: R1's path shows "aggregated by 65100 10.0.0.1",
!    R3's path shows "aggregated by 65100 10.0.0.3". This identifies who created each aggregate.
! ← summary-only effect is visible in the routing table (above), not in atomic-aggregate:
!    R3 only advertises the /16; R1 advertises both the /16 and 172.16.1.0/24.

! After removing summary-only from R3:
show ip bgp
! ← Both aggregate and 172.16.1.0/24 now visible from both R1 and R3
```

### Task 3 — LOCAL_PREF 200 at R1 and R2

```ios
! At R1:
show ip bgp 172.20.4.0
! ←  *>i 172.20.4.0/24  10.0.0.3     ...  200  0  65200 i   (best — via R3, LP 200)
! ←  * i                10.0.0.1     ...  150  0  65200 i   (not best — R1's own, LP 150)

! At XR1 (iBGP propagated; community 65100:200 triggers SET_LOCAL_PREF_BY_COMMUNITY):
show bgp ipv4 unicast 172.20.4.0/24
! ← best path via 10.0.0.3; local preference 120 (set by XR1's RPL on community 65100:200)
! ← R1's path has local preference 150 but XR1's RPL re-maps it — R3 still wins at 120 vs default
```

### Task 4 — AS-Path Prepend at R4

```ios
! At R4:
show ip bgp 172.16.1.0
! ←  *>  172.16.1.0/24  10.1.34.3  ...  65100             (best — R3, AS-path length 1)
! ←  *   172.16.1.0/24  10.1.14.1  ...  65100 65100 65100 65100  (R1, AS-path length 4)

show ip bgp neighbors 10.1.14.1 routes
! ← R1's advertisement shows extended AS-path in Path column
```

### Task 5 — MED at R4

```ios
! At R4:
show ip bgp 172.16.0.0
! ←  *>  172.16.0.0/16  10.1.34.3   0  50  65100   (best — R3, MED 50)
! ←  *   172.16.0.0/16  10.1.14.1   0 100  65100   (R1, MED 100)
! ← MED comparison valid because both paths come from AS 65100 (same neighbor AS)
```

### Task 6 — RPL on R2

```ios
! At R2 (iBGP peer of XR1):
show ip bgp 172.16.11.0
! ← community: 65100:300 visible
! ← AS-path: 65100 65100 65100 65100  (prepend 3× → total 4 AS hops)

! On XR1 — confirm policy is active:
show rpl route-policy SET_COMMUNITY_AND_PREPEND
show bgp neighbors 10.0.0.2 advertised-routes
! ← 172.16.11.0/24 should appear with the community and extended AS-path
```

### Task 7 — Conditional Advertisement

```ios
! At R4 (while R3's aggregate is present in R1's BGP table):
show ip bgp 172.16.100.0
! ← Network not in table — BACKUP_ADV is suppressed

! After removing R3's aggregate (no aggregate-address on R3):
! Wait 60 seconds for conditional-advertisement scanner (default 60 s interval)
show ip bgp 172.16.100.0
! ← 172.16.100.0/24  10.1.14.1  ...  65100  (backup now advertised from R1)

! Restore R3's aggregate — 172.16.100.0/24 should withdraw from R4 again
```

---

## 7. Verification Cheatsheet

### Key Configuration Skeleton

```ios
! ─── R1 ───────────────────────────────────────────────────
ip prefix-list PFX_16_1_EXACT seq 5 permit 172.16.1.0/24
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16
ip prefix-list PFX_BACKUP_COND seq 5 permit 172.16.100.0/24
ip prefix-list PFX_TRACK_AGGREGATE seq 5 permit 172.16.0.0/16

ip route 172.16.0.0 255.255.0.0 Null0
ip route 172.16.100.0 255.255.255.0 Null0

route-map R1_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_1_EXACT
 set as-path prepend 65100 65100 65100
route-map R1_TO_R4_OUT permit 20
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 100
route-map R1_TO_R4_OUT permit 30

route-map BACKUP_ADV permit 10
 match ip address prefix-list PFX_BACKUP_COND
route-map TRACK_PRIMARY permit 10
 match ip address prefix-list PFX_TRACK_AGGREGATE

router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0
  network 172.16.100.0 mask 255.255.255.0
  neighbor 10.1.14.4 route-map R1_TO_R4_OUT out
  neighbor 10.1.14.4 advertise-map BACKUP_ADV non-exist-map TRACK_PRIMARY

! ─── R3 ───────────────────────────────────────────────────
ip prefix-list PFX_PREFER_172_20_4 seq 5 permit 172.20.4.0/24
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16
ip as-path access-list 1 permit _65200$

ip route 172.16.0.0 255.255.0.0 Null0

route-map STEER_R4_IN permit 10
 match ip address prefix-list PFX_PREFER_172_20_4
 set local-preference 200
 set community 65100:200
route-map STEER_R4_IN permit 20
 match as-path 1
 set community 65100:200
route-map STEER_R4_IN deny 30

route-map R3_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 50
route-map R3_TO_R4_OUT permit 20

router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0
  no neighbor 10.1.34.4 route-map FILTER_R4_ASPATH in
  neighbor 10.1.34.4 route-map STEER_R4_IN in
  neighbor 10.1.34.4 route-map R3_TO_R4_OUT out

! ─── XR1 ──────────────────────────────────────────────────
prefix-set P_XR1_ORIGINATE
  172.16.11.0/24
end-set
route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_XR1_ORIGINATE then
    set community (65100:300) additive
    prepend as-path 65100 3
  endif
  pass
end-policy
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy SET_COMMUNITY_AND_PREPEND out
```

### Diagnostic Command Reference

| Command | Router | What to look for |
|---------|--------|-----------------|
| `show ip bgp neighbors 10.1.14.4 received-routes` | R1 | Pre-filter: both 172.20.4 and 172.20.5 present |
| `show ip bgp neighbors 10.1.14.4 routes` | R1 | Post-filter: only 172.20.4 |
| `show ip bgp 172.20.4.0` | R1, R2, XR1 | LOCAL_PREF 200 on R3 path (via 10.0.0.3) |
| `show ip bgp 172.16.1.0` | R4 | R3 path: `65100` (best); R1 path: `65100 65100 65100 65100` |
| `show ip bgp 172.16.0.0` | R4 | R3 path: MED 50 (best); R1 path: MED 100 |
| `show ip bgp 172.16.11.0` | R2 | community 65100:300; AS-path length 4 |
| `show ip bgp 172.16.100.0` | R4 | absent (primary up) / present (primary withdrawn) |
| `show route-map <name>` | R1, R3 | Hit count on each sequence — zero means no match |
| `show ip bgp neighbors <x> advertised-routes` | R1, R3 | Confirm outbound policy applied before sending |
| `show rpl route-policy SET_COMMUNITY_AND_PREPEND` | XR1 | Policy body content |
| `debug ip bgp <neighbor> updates` | R1, R3 | UPDATE trace — see set attributes in outbound |

### Common Failure Causes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 172.20.5.0/24 visible at R1 | FILTER_R4_IN not applied or wrong direction | Verify `neighbor 10.1.14.4 route-map FILTER_R4_IN in` |
| Aggregate not advertised | No null-route anchor | Add `ip route 172.16.0.0 255.255.0.0 Null0` |
| LOCAL_PREF 200 not propagated AS-wide | STEER_R4_IN not applied inbound (applied outbound by mistake) | Check direction: `show ip bgp neighbors 10.1.34.4 policy` |
| AS-path prepend not visible at R4 | `set as-path prepend` in wrong direction (inbound instead of outbound) | `R1_TO_R4_OUT` must be applied `out` on neighbor 10.1.14.4 |
| MED 50 not set at R4 for R3 path | `R3_TO_R4_OUT` applied on iBGP neighbor instead of eBGP 10.1.34.4 | Re-apply to correct eBGP neighbor |
| LOCAL_PREF set outbound to eBGP (common mistake) | Confusing LP (iBGP only) with AS-path prepend (inter-AS) | LP is stripped on eBGP; use `set as-path prepend` for cross-AS influence |
| Conditional advertisement never triggers | Tracked prefix still in BGP table | Remove R3's aggregate first; wait 60 s for scanner |
| XR1 RPL implicit drop | Missing `pass` at end of route-policy | All unmatched routes dropped without `pass` |

---

## 8. Solutions (Spoiler Alert!)

<details>
<summary>Task 1 — Enable soft-reconfiguration and verify FILTER_R4_IN on R1</summary>

```ios
! R1
router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 soft-reconfiguration inbound

clear ip bgp 10.1.14.4 soft in

show ip bgp neighbors 10.1.14.4 received-routes
! Both 172.20.4.0/24 and 172.20.5.0/24 appear

show ip bgp neighbors 10.1.14.4 routes
! Only 172.20.4.0/24 passes FILTER_R4_IN
```

FILTER_R4_IN (from lab-03) structure for reference:

```ios
ip prefix-list PL_DENY_172_20_5 seq 5 deny 172.20.5.0/24
ip prefix-list PL_DENY_172_20_5 seq 10 permit 0.0.0.0/0 le 32

route-map FILTER_R4_IN deny 10
 match ip address prefix-list PL_DENY_172_20_5
route-map FILTER_R4_IN permit 20
 set community 65100:100
 set local-preference 150
```

</details>

---

<details>
<summary>Task 2 — Aggregate 172.16.0.0/16 on R1 and R3</summary>

**R1:**

```ios
ip route 172.16.0.0 255.255.0.0 Null0

router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0
```

**R3 (transient `summary-only` demo):**

```ios
ip route 172.16.0.0 255.255.0.0 Null0

router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0 summary-only
```

After verifying that R4 sees only 172.16.0.0/16 from R3, remove `summary-only`:

```ios
router bgp 65100
 address-family ipv4
  no aggregate-address 172.16.0.0 255.255.0.0 summary-only
  aggregate-address 172.16.0.0 255.255.0.0
```

</details>

---

<details>
<summary>Task 3 — STEER_R4_IN on R3 (LOCAL_PREF 200 for 172.20.4.0/24)</summary>

```ios
! R3
ip prefix-list PFX_PREFER_172_20_4 seq 5 permit 172.20.4.0/24
ip as-path access-list 1 permit _65200$

route-map STEER_R4_IN permit 10
 match ip address prefix-list PFX_PREFER_172_20_4
 set local-preference 200
 set community 65100:200
route-map STEER_R4_IN permit 20
 match as-path 1
 set community 65100:200
route-map STEER_R4_IN deny 30

router bgp 65100
 address-family ipv4
  no neighbor 10.1.34.4 route-map FILTER_R4_ASPATH in
  neighbor 10.1.34.4 route-map STEER_R4_IN in

clear ip bgp 10.1.34.4 soft in
```

</details>

---

<details>
<summary>Task 4 — AS-path prepend 3× on R1 outbound to R4</summary>

```ios
! R1
ip prefix-list PFX_16_1_EXACT seq 5 permit 172.16.1.0/24

route-map R1_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_1_EXACT
 set as-path prepend 65100 65100 65100
route-map R1_TO_R4_OUT permit 30

router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 route-map R1_TO_R4_OUT out

clear ip bgp 10.1.14.4 soft out
```

</details>

---

<details>
<summary>Task 5 — MED 100/50 for 172.16.0.0/16 on R1 and R3</summary>

**R1 — extend R1_TO_R4_OUT with seq 20:**

```ios
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16

route-map R1_TO_R4_OUT permit 20
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 100

clear ip bgp 10.1.14.4 soft out
```

**R3 — create R3_TO_R4_OUT:**

```ios
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16

route-map R3_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 50
route-map R3_TO_R4_OUT permit 20

router bgp 65100
 address-family ipv4
  neighbor 10.1.34.4 route-map R3_TO_R4_OUT out

clear ip bgp 10.1.34.4 soft out
```

</details>

---

<details>
<summary>Task 6 — RPL SET_COMMUNITY_AND_PREPEND on XR1</summary>

```xr
! XR1
prefix-set P_XR1_ORIGINATE
  172.16.11.0/24
end-set

route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_XR1_ORIGINATE then
    set community (65100:300) additive
    prepend as-path 65100 3
  endif
  pass
end-policy

router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy SET_COMMUNITY_AND_PREPEND out
  !
 !
!
```

Verify on R2:

```ios
show ip bgp 172.16.11.0
! community 65100:300; AS-path 65100 65100 65100 65100
```

</details>

---

<details>
<summary>Task 7 — Conditional advertisement on R1</summary>

```ios
! R1
ip route 172.16.100.0 255.255.255.0 Null0

ip prefix-list PFX_BACKUP_COND seq 5 permit 172.16.100.0/24
ip prefix-list PFX_TRACK_AGGREGATE seq 5 permit 172.16.0.0/16

route-map BACKUP_ADV permit 10
 match ip address prefix-list PFX_BACKUP_COND
route-map TRACK_PRIMARY permit 10
 match ip address prefix-list PFX_TRACK_AGGREGATE

router bgp 65100
 address-family ipv4
  network 172.16.100.0 mask 255.255.255.0
  neighbor 10.1.14.4 advertise-map BACKUP_ADV non-exist-map TRACK_PRIMARY
```

**Test:** On R3: `no aggregate-address 172.16.0.0 255.255.0.0` → wait up to 60 seconds
(conditional advertisement scanner interval) → `show ip bgp 172.16.100.0` at R4 should show
the prefix from R1.

Restore: `aggregate-address 172.16.0.0 255.255.0.0` on R3.

</details>

---

## 9. Troubleshooting Scenarios

### Troubleshooting Workflow

```
Anomaly observed (wrong best path / missing prefix / MED not set)
        │
        ▼
show ip bgp <prefix>  ←── Check LOCAL_PREF, MED, AS-path on each path
        │
        ├── Attribute missing or wrong value?
        │         │
        │         ▼
        │   show route-map <name>  ←── Hit count = 0 means route-map not matching
        │         │
        │         ├── Zero hits → check match clause (prefix-list, direction)
        │         └── Non-zero hits → check set clause (wrong attribute set)
        │
        └── Attribute present but on wrong neighbor?
                  │
                  ▼
            show ip bgp neighbors <x> policy
            show run | section router bgp  ←── Confirm neighbor + direction
                  │
                  └── Reapply to correct neighbor, then:
                      clear ip bgp <neighbor> soft in/out
```

---

### Ticket 1 — 172.20.4.0/24 Not Preferred via R3 (LOCAL_PREF Not Elevated)

**Symptom:** `show ip bgp 172.20.4.0` on R1 shows R1's own path (via 10.1.14.4, next-hop
10.0.0.1) as best instead of R3's path (next-hop 10.0.0.3). Both paths are present but
neither has LOCAL_PREF 200.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

<details>
<summary>Diagnosis steps</summary>

1. At R1: `show ip bgp 172.20.4.0` — compare LOCAL_PREF on both paths
2. If neither path has LP 200, the issue is in `STEER_R4_IN` on R3 — seq 10 is not matching
3. At R3: `show route-map STEER_R4_IN` — check hit count on sequence 10
4. If seq 10 hit count is 0, `PFX_PREFER_172_20_4` is not matching 172.20.4.0/24
5. At R3: `show ip prefix-list PFX_PREFER_172_20_4` — inspect the configured prefix and length
6. If the prefix-list shows `/25` instead of `/24`, the route received from R4 (`/24`) is not
   matched — the seq 10 deny-by-mismatch falls through to seq 20 which only sets community,
   not LOCAL_PREF

</details>

<details>
<summary>Fix</summary>

```ios
! R3 — correct the prefix-list from /25 back to /24
no ip prefix-list PFX_PREFER_172_20_4 seq 5 permit 172.20.4.0/25
ip prefix-list PFX_PREFER_172_20_4 seq 5 permit 172.20.4.0/24

clear ip bgp 10.1.34.4 soft in
```

Verify: `show ip bgp 172.20.4.0` at R1 now shows LP 200 on the R3 path (next-hop 10.0.0.3).

</details>

---

### Ticket 2 — R4 Not Preferring R3 Path for 172.16.0.0/16 (MED Missing)

**Symptom:** `show ip bgp 172.16.0.0/16` at R4 shows no MED difference between R1 and R3
paths, or shows R1 as best. MED 50 from R3 is not present.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

<details>
<summary>Diagnosis steps</summary>

1. At R4: `show ip bgp 172.16.0.0` — note MED values; if both show 0, outbound policy issue on R3
2. At R3: `show route-map R3_TO_R4_OUT` — check hit count on seq 10
3. If seq 10 hit count is 0, R3_TO_R4_OUT is not being applied to the R4 eBGP session
4. At R3: `show ip bgp neighbors 10.1.34.4 policy` — check outbound policy assignment
5. If no outbound policy shown for 10.1.34.4, `R3_TO_R4_OUT` was likely applied to the wrong neighbor
6. At R3: `show run | section router bgp` — look for `route-map R3_TO_R4_OUT out` under an iBGP
   neighbor (e.g., `neighbor 10.0.0.1`) instead of the eBGP neighbor (10.1.34.4)

</details>

<details>
<summary>Fix</summary>

```ios
! R3 — move R3_TO_R4_OUT from the wrong iBGP neighbor to the correct eBGP neighbor
router bgp 65100
 address-family ipv4
  no neighbor 10.0.0.1 route-map R3_TO_R4_OUT out
  neighbor 10.1.34.4 route-map R3_TO_R4_OUT out

clear ip bgp 10.1.34.4 soft out
```

Verify: `show ip bgp 172.16.0.0` at R4 shows MED 50 on R3 path (best) and MED 100 on R1 path.

</details>

---

### Ticket 3 — AS-Path Prepend Has No Effect at R4

**Symptom:** `show ip bgp 172.16.1.0` at R4 shows R1 and R3 paths with equal AS-path length
(both `65100`), or R1 path is best. AS-path prepend from R1 is not visible.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

<details>
<summary>Diagnosis steps</summary>

1. At R4: `show ip bgp 172.16.1.0` — compare AS-path column for R1 (10.1.14.1) and R3 (10.1.34.3)
   paths; if both show `65100` (length 1), prepend is absent from R1's advertisement
2. At R1: `show route-map R1_TO_R4_OUT` — check hit count on seq 10
3. If seq 10 hit count is non-zero, the `set` clause is executing but having no effect
4. At R1: `show route-map R1_TO_R4_OUT` — look at the `set` clause in seq 10
5. If you see `set local-preference 200` instead of `set as-path prepend`, this is the fault:
   LOCAL_PREF is an iBGP attribute and is stripped before R1 sends the UPDATE to eBGP peer R4
6. Confirm: at R4 `show ip bgp 172.16.1.0` — the LOCAL_PREF column for R1's path will show
   0 or missing, proving the attribute was stripped at the eBGP boundary

</details>

<details>
<summary>Fix</summary>

```ios
! R1 — replace the incorrect set local-preference with set as-path prepend in seq 10
route-map R1_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_1_EXACT
 no set local-preference 200
 set as-path prepend 65100 65100 65100

clear ip bgp 10.1.14.4 soft out
```

Verify: `show ip bgp 172.16.1.0` at R4 now shows R1 path with AS-path
`65100 65100 65100 65100` (length 4) — R3 path `65100` (length 1) is best.

</details>

---

## 10. Lab Completion Checklist

- [x] R1 BGP table: 172.20.5.0/24 absent; 172.20.4.0/24 present with community 65100:100
- [x] All AS 65100 routers: best path to 172.20.4.0/24 exits via R3 (next-hop 10.0.0.3,
  LOCAL_PREF 200)
- [x] R4 BGP table: `show ip bgp 172.16.0.0` — R3 path has aggregate with summary-only
  (transient) and then reverts to both aggregate + specifics
- [x] R4 BGP table: `show ip bgp 172.16.1.0` — R3 path best (AS-path `65100`); R1 path
  has AS-path `65100 65100 65100 65100`
- [ ] R4 BGP table: `show ip bgp 172.16.0.0` — R3 path MED 50 (best), R1 path MED 100
- [ ] R2 BGP table: `show ip bgp 172.16.11.0` — community 65100:300; AS-path length 4
- [ ] R4: 172.16.100.0/24 absent while R3's aggregate is present
- [ ] R4: 172.16.100.0/24 appears within 60 s after R3's aggregate is withdrawn
- [ ] `show route-map` on R1 and R3 show non-zero hit counts on all active sequences
- [ ] After any route-map change: `clear ip bgp <neighbor> soft` applied and output re-verified

---

## 11. Appendix: Script Exit Codes

| Script | Exit 0 | Exit 1 | Exit 3 | Exit 4 |
|--------|--------|--------|--------|--------|
| `inject_scenario_01.py` | Fault injected on R3 | Command error | Lab/node not found | Pre-flight check failed |
| `inject_scenario_02.py` | Fault injected on R3 | Command error | Lab/node not found | Pre-flight check failed |
| `inject_scenario_03.py` | Fault injected on R1 | Command error | Lab/node not found | Pre-flight check failed |
| `apply_solution.py` | Solution applied to all devices | One or more devices failed | Lab/node not found | N/A |
