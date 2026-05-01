# Lab 04 — BGP Route Filtering and Traffic Steering

**Chapter:** Routing Policy | **Exam:** 300-510 | **Difficulty:** Intermediate | **Time:** 90 min

---

## Section 1 — Theory

### 1.1 BGP Route Filtering

BGP filtering controls which routes are installed in the BGP table and which prefixes are
advertised to peers. IOS supports three filtering mechanisms that can be applied inbound or
outbound on a neighbor:

| Mechanism | Match basis | Applied via |
|-----------|-------------|-------------|
| `ip prefix-list` | Prefix + length (exact, ge, le) | `neighbor X route-map in/out` with `match ip address prefix-list` |
| `ip as-path access-list` | AS-path regex | `neighbor X filter-list N in/out` or `match as-path N` in route-map |
| `ip community-list` | Community value / regex | `match community N` in route-map |

**Inbound filtering** runs before the BGP best-path selection algorithm. A denied prefix is
not installed and not re-advertised. **Outbound filtering** runs before sending an UPDATE to
a peer; denied prefixes are suppressed from the advertisement but remain in the local BGP
table.

**`aggregate-address`** summarizes a block into a single prefix. With `summary-only`, BGP
automatically suppresses all covered more-specific prefixes. Without `summary-only`, both
the aggregate and the more-specifics are advertised — the aggregate carries atomic-aggregate
and aggregator attributes.

### 1.2 Traffic Steering Attributes

| Attribute | Scope | Direction | Controlled by |
|-----------|-------|-----------|---------------|
| `LOCAL_PREF` | AS-wide (iBGP) | Inbound (ingress selection) | Applied on inbound eBGP; propagated to all iBGP peers |
| `AS-path prepend` | Inter-AS | Outbound (egress influence at remote AS) | `set as-path prepend` in outbound route-map |
| `MED` | Between adjacent ASes | Outbound (hint to neighboring AS) | `set metric` in outbound route-map |
| Conditional advertisement | N/A | Outbound | `advertise-map non-exist-map` on neighbor |

**LOCAL_PREF tie-breaking:** BGP selects the path with the *highest* LOCAL_PREF. Setting
LOCAL_PREF 200 on routes received at R3 while R1's default is 150 makes every router in
AS 65100 prefer R3 as the exit for those destinations.

**MED tie-breaking:** BGP selects the path with the *lowest* MED, but only when comparing
paths from the same neighbor AS. Setting MED 50 at R3 and MED 100 at R1 signals to AS 65200
that the R3 path is preferred for inbound traffic.

**AS-path prepend** artificially lengthens the AS-path advertised to eBGP peers. A longer
path is less preferred by default BGP path selection (fewer AS hops = better). Prepending
3× on R1's advertisement of 172.16.1.0/24 causes R4 to prefer the R3 path for that prefix.

### 1.3 RPL Equivalents on XR

IOS-XR RPL uses `set as-path prepend` and `set community` just like route-maps but in a
structured if/elseif/else block. A single route-policy can combine both operations:

```
route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_XR1_ORIGINATE then
    set community (65100:300) additive
    set as-path prepend 65100 65100 65100
  endif
  pass
end-policy
```

The equivalent IOS route-map would require two separate `set` lines within one sequence
(which also works in IOS) but the RPL form is more readable for complex conditional logic.

### 1.4 Conditional Advertisement

`neighbor X advertise-map BACKUP non-exist-map TRACK` tells IOS: send the prefixes matched
by `BACKUP` to neighbor X *only when* the prefixes matched by `TRACK` are absent from the
BGP table. This implements a primary/backup model: the backup route is suppressed while the
primary (tracked) aggregate is present, and surfaces automatically if the primary disappears.

---

## Section 2 — Scenario

AS 65100 (the SP core: R1, R2, R3, XR1, XR2) dual-homes to AS 65200 (R4) via two eBGP
sessions — R1↔R4 on L4 and R3↔R4 on L3. The IGP (OSPF area 0, IS-IS L2) and redistribution
policies from lab-03 are already in place.

Lab-04 tasks build BGP filtering and steering on top of the running lab-03 state:

- Inbound filtering at R1 denies one of R4's two Lo prefixes
- R3 advertises only the 172.16.0.0/16 aggregate outbound (Task 2 demo), then reverts to
  also allowing specifics (final state) so prepend and MED can be observed
- Traffic engineering with LOCAL_PREF, AS-path prepend, and MED makes R3 the preferred
  ingress/egress for 172.20.4.0/24 and 172.16.x/24
- XR1 demonstrates the RPL equivalent of community + prepend in one compact policy
- Conditional advertisement on R1 surfaces a backup prefix only when R3's aggregate withdraws

```
        AS 65200
           R4
          / \
    L4  /   \ L3
       /     \
      R1-----R3      AS 65100
       \     /
    L1  \   / L2
         R2
        /  \
      L6    L7
      XR1--XR2
         L8
```

---

## Section 3 — Inventory

### 3.1 Device Table

| Device | Role | Platform | AS |
|--------|------|----------|----|
| R1 | SP core / eBGP edge to R4 | IOSv | 65100 |
| R2 | SP core / OSPF ABR / IS-IS L1-L2 | IOSv | 65100 |
| R3 | SP core / eBGP edge to R4 | IOSv | 65100 |
| R4 | External AS edge | IOSv | 65200 |
| XR1 | IOS-XR RPL node / IS-IS L1-2 | XRv9k | 65100 |
| XR2 | IOS-XR RPL node / IS-IS L2 | XRv9k | 65100 |

### 3.2 Loopback Table

| Device | Loopback0 | Loopback1 | Purpose |
|--------|-----------|-----------|---------|
| R1 | 10.0.0.1/32 | 172.16.1.1/24 | BGP network statement prefix |
| R2 | 10.0.0.2/32 | 10.2.1.2/24 | OSPF area-1 ABR demo (lab-03) |
| R3 | 10.0.0.3/32 | — | |
| R4 | 10.0.0.4/32 | 172.20.4.1/24 | External prefix 1 (accepted inbound) |
| R4 | | 172.20.5.1/24 (Lo2) | External prefix 2 (filtered at R1) |
| XR1 | 10.0.0.5/32 | 172.16.11.1/24 | RPL match demo prefix |
| XR2 | 10.0.0.6/32 | — | |

### 3.3 Cabling Table

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | Core (OSPF/IS-IS) |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | Core (OSPF/IS-IS) |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | eBGP R3↔R4 |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | eBGP R1↔R4 |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | Core diagonal (OSPF/IS-IS) |
| L6 | R2 Gi0/2 | XR1 Gi0/0/0/0 | 10.1.25.0/24 | IS-IS L1 (lab-03) |
| L7 | R3 Gi0/3 | XR2 Gi0/0/0/0 | 10.1.36.0/24 | IS-IS L2 |
| L8 | XR1 Gi0/0/0/1 | XR2 Gi0/0/0/1 | 10.1.56.0/24 | XR backbone (IS-IS L2) |

### 3.4 BGP Prefixes in Play

| Prefix | Origin | Advertised by | Lab-04 Treatment |
|--------|--------|---------------|-----------------|
| 172.16.1.0/24 | AS 65100 | R1 | AS-path prepend 3× outbound to R4 (Task 4) |
| 172.16.11.0/24 | AS 65100 | XR1 | RPL community + prepend demo (Task 6) |
| 172.16.0.0/16 | AS 65100 | R1, R3 | Aggregate; MED 100 at R1, MED 50 at R3 (Task 5) |
| 172.16.100.0/24 | AS 65100 | R1 | Backup conditional advertisement (Task 7) |
| 172.20.4.0/24 | AS 65200 | R4 | Accepted; LOCAL_PREF 200 at R3 (Task 3) |
| 172.20.5.0/24 | AS 65200 | R4 | Filtered inbound at R1 (Task 1) |

---

## Section 4 — Pre-lab State

### IS (pre-loaded from lab-03 solutions)

- OSPF area 0 running on R1/R2/R3; IS-IS L2 across all SP core routers
- Redistribution between OSPF and IS-IS with tag-based loop prevention
- R2: IS-IS L1-L2 boundary with XR1; selective L1→L2 leak; OSPF distribute-list and ABR
  filter-list in place
- iBGP full mesh in AS 65100; eBGP sessions R1↔R4 and R3↔R4 established
- R1: FILTER_R4_IN denies 172.20.5.0/24 and accepts 172.20.4.0/24 with community/LOCAL_PREF
- R3: FILTER_R4_ASPATH accepts only AS 65200 originated routes inbound

### IS NOT (not yet configured)

- No aggregate-address on R1 or R3
- No outbound route-maps on R1 or R3 toward R4
- No LOCAL_PREF 200 for 172.20.4.0/24 at R3
- No AS-path prepend on R1's advertisement to R4
- No MED on either eBGP session
- No SET_COMMUNITY_AND_PREPEND policy on XR1
- No conditional advertisement on R1

---

## Section 5 — Lab Challenge

### Task 1 — Verify Inbound Prefix-List Filtering at R1 (already in place)

The initial-config for this lab (lab-03 solutions) already has FILTER_R4_IN on R1 denying
172.20.5.0/24 inbound from R4. Verify the filter is operational before proceeding.

Confirm that R1 accepts 172.20.4.0/24 but has no entry for 172.20.5.0/24. Confirm R3
accepts both 172.20.4.0/24 and 172.20.5.0/24. This baseline asymmetry is intentional.

### Task 2 — Originate 172.16.0.0/16 Aggregate

On both R1 and R3, install a null-route for 172.16.0.0/16 and configure BGP to originate
the 172.16.0.0/16 aggregate. Use `summary-only` on R3 first to demonstrate complete
more-specific suppression, then verify at R4. After verification, remove `summary-only` from
R3 so that specific prefixes remain advertised (required for Tasks 4 and 5 to function).

The null route (`ip route 172.16.0.0 255.255.0.0 Null0`) is required: IOS will not
originate the aggregate unless at least one covered prefix is in the routing table.

### Task 3 — Set LOCAL_PREF 200 for 172.20.4.0/24 at R3

On R3, replace FILTER_R4_ASPATH with a new inbound route-map `STEER_R4_IN` that:
1. Matches 172.20.4.0/24 exactly (prefix-list) and sets LOCAL_PREF 200 plus community
   65100:200
2. Matches remaining AS 65200 originated routes (as-path ACL 1) and sets community 65100:200
3. Denies everything else (explicit deny at the end)

After applying, verify that R1, R2, XR1, and XR2 all select R3 as the exit for 172.20.4.0/24
by checking that the best-path next-hop resolves to R3's Loopback0 (10.0.0.3).

### Task 4 — AS-Path Prepend 3× Outbound on R1

On R1, create outbound route-map `R1_TO_R4_OUT` and apply it to the neighbor 10.1.14.4
session. The route-map should match 172.16.1.0/24 exactly and prepend AS 65100 three times.
Permit all other prefixes unchanged.

After applying, verify at R4: `show ip bgp 172.16.1.0` should show two paths —
the R3 path with AS-path `65100` (length 1) and the R1 path with AS-path `65100 65100 65100 65100`
(length 4). The R3 path should be best.

### Task 5 — MED Manipulation

Extend `R1_TO_R4_OUT` on R1 to also match 172.16.0.0/16 (the aggregate) and set metric 100.
On R3, create outbound route-map `R3_TO_R4_OUT` and apply it to the neighbor 10.1.34.4
session. Match 172.16.0.0/16 and set metric 50.

Verify at R4: `show ip bgp 172.16.0.0/16` should show two paths — R3 with MED 50 marked
as best, R1 with MED 100. MED comparison is valid here because both paths come from the
same neighbor AS (65100).

### Task 6 — RPL Equivalent on XR1

On XR1, create route-policy `SET_COMMUNITY_AND_PREPEND`. The policy should:
- Match prefixes in `P_XR1_ORIGINATE` (172.16.11.0/24)
- Set community (65100:300) additive
- Prepend AS 65100 three times
- Pass everything else unchanged

Apply it as the outbound policy on the IBGP neighbor-group (replacing PASS). Verify on
R2 that 172.16.11.0/24 arrives with community 65100:300 and AS-path `65100 65100 65100 65100`.
Compare the RPL policy syntax to R1's R1_TO_R4_OUT route-map — same outcome, different
structure.

### Task 7 — Conditional Advertisement on R1

On R1, add `network 172.16.100.0 mask 255.255.255.0` and install `ip route 172.16.100.0
255.255.255.0 Null0` so the prefix is BGP-reachable. Then configure conditional advertisement
on the R4 neighbor:

- `advertise-map BACKUP_ADV` matches 172.16.100.0/24
- `non-exist-map TRACK_PRIMARY` matches 172.16.0.0/16 (the primary aggregate)

Verify that 172.16.100.0/24 is suppressed at R4 while R3's aggregate is present. Then
simulate R3 failure (shut down R3's eBGP session or remove the aggregate) and verify that
172.16.100.0/24 now appears at R4 from R1.

### Task 8 — Troubleshooting Scenario

Inject fault scenario 3 (`python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`).
Diagnose and repair the faults without looking at the solution configs. The fault targets
BGP policy behavior — use `show ip bgp`, `show route-map`, `debug ip bgp <neighbor> updates`
to trace the anomaly.

---

## Section 6 — Verification

```ios
! ── Task 1 — Inbound filter on R1 ──
! R1 must not have 172.20.5.0/24 in BGP table
show ip bgp
! Expected: no entry for 172.20.5.0/24

show ip bgp neighbors 10.1.14.4 received-routes
! Expected: both 172.20.4.0/24 and 172.20.5.0/24 shown (soft-reconfiguration must be enabled)

show ip bgp neighbors 10.1.14.4 routes
! Expected: only 172.20.4.0/24 passes the inbound filter

! ── Task 2 — Aggregate ──
! At R4: both aggregate and specifics should appear after removing summary-only
show ip bgp
! Expected: 172.16.0.0/16 with atomic-aggregate attribute; 172.16.1.0/24 visible too

! ── Task 3 — LOCAL_PREF 200 at R3 ──
! At R1: best path to 172.20.4.0/24 should have LOCAL_PREF 200 via R3
show ip bgp 172.20.4.0
! Expected: * i 172.20.4.0/24  10.0.0.3  ... 200  ...  65200  (best)
!           *                  10.0.0.1  ... 150  ...  65200

! At XR1: verify RPL community-based LOCAL_PREF elevates R3 path
show bgp ipv4 unicast 172.20.4.0/24
! Expected: best path via 10.0.0.3 with local preference 200 (community 65100:200 → LP 120
!   from RPL SET_LOCAL_PREF_BY_COMMUNITY; note: 200 at R3 is set on R3 and propagated via iBGP)

! ── Task 4 — AS-path prepend at R4 ──
! At R4: R1 path has 4-element AS-path, R3 path has 1-element AS-path
show ip bgp 172.16.1.0
! Expected: * 172.16.1.0/24  10.1.34.3  ...  65100  (best, 1 AS)
!           *                10.1.14.1  ...  65100 65100 65100 65100  (not best)

! ── Task 5 — MED comparison at R4 ──
show ip bgp 172.16.0.0/16
! Expected: R3 path MED=50 (best); R1 path MED=100

! ── Task 6 — RPL community+prepend at R2 ──
show ip bgp 172.16.11.0
! Expected: community 65100:300; AS-path 65100 65100 65100 65100

! ── Task 7 — Conditional advertisement ──
! While R3 is up: 172.16.100.0/24 absent from R4
show ip bgp 172.16.100.0
! Expected: network not in table

! After R3 aggregate withdrawn: 172.16.100.0/24 appears at R4 from R1
show ip bgp 172.16.100.0
! Expected: 172.16.100.0/24  10.1.14.1  ...  65100
```

---

## Section 7 — Cheatsheet

### 7.1 IOS BGP Filtering

```ios
! Inbound prefix-list filter
ip prefix-list PL_DENY_LO2 seq 5 deny 172.20.5.0/24
ip prefix-list PL_DENY_LO2 seq 10 permit 0.0.0.0/0 le 32
route-map RM_IN deny 10
 match ip address prefix-list PL_DENY_LO2
route-map RM_IN permit 20
neighbor 10.x.x.x route-map RM_IN in

! Aggregate with null route anchor
ip route 172.16.0.0 255.255.0.0 Null0
router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0 summary-only
```

### 7.2 Traffic Steering

```ios
! LOCAL_PREF — inbound from eBGP peer
route-map STEER_IN permit 10
 match ip address prefix-list PL_PREFER
 set local-preference 200
neighbor 10.x.x.x route-map STEER_IN in

! AS-path prepend — outbound to eBGP peer
route-map PREPEND_OUT permit 10
 match ip address prefix-list PL_SPECIFIC
 set as-path prepend 65100 65100 65100

! MED — outbound to eBGP peer
route-map MED_OUT permit 10
 match ip address prefix-list PL_AGGREGATE
 set metric 50

! Conditional advertisement
neighbor 10.x.x.x advertise-map BACKUP_ADV non-exist-map TRACK_PRIMARY
```

### 7.3 XR RPL Community + Prepend

```xr
prefix-set P_ORIGINATE
  172.16.11.0/24
end-set
route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_ORIGINATE then
    set community (65100:300) additive
    set as-path prepend 65100 65100 65100
  endif
  pass
end-policy
```

### 7.4 Diagnostic Commands

```
! IOS
show ip bgp                            — full BGP table
show ip bgp <prefix>                   — detailed path info (LOCAL_PREF, MED, AS-path)
show ip bgp neighbors <x> routes      — accepted routes (post-filter)
show ip bgp neighbors <x> advertised-routes  — what we send
show route-map <name>                  — policy hit counts
debug ip bgp <neighbor> updates       — UPDATE trace

! XR
show bgp ipv4 unicast                  — BGP table
show bgp ipv4 unicast <prefix>        — path detail
show rpl route-policy <name>          — RPL policy content
show bgp neighbors <x> advertised-routes
```

---

## Section 8 — Solutions

<details>
<summary>Task 1 — R1 inbound filter verification</summary>

R1's FILTER_R4_IN (from lab-03) already denies 172.20.5.0/24 and permits 172.20.4.0/24.
Enable soft-reconfiguration to see received routes before filter:

```
router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 soft-reconfiguration inbound
```

Then: `show ip bgp neighbors 10.1.14.4 received-routes` shows both.
`show ip bgp neighbors 10.1.14.4 routes` shows only 172.20.4.0/24.

</details>

<details>
<summary>Task 2 — Aggregate on R1 and R3</summary>

**R1:**
```
ip route 172.16.0.0 255.255.0.0 Null0
router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0
```

**R3:**
```
ip route 172.16.0.0 255.255.0.0 Null0
router bgp 65100
 address-family ipv4
  aggregate-address 172.16.0.0 255.255.0.0 summary-only   ! transient demo
```

After verification, remove `summary-only` from R3.

</details>

<details>
<summary>Task 3 — STEER_R4_IN on R3</summary>

```
ip prefix-list PFX_PREFER_172_20_4 seq 5 permit 172.20.4.0/24
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16
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
```

</details>

<details>
<summary>Task 4 — AS-path prepend on R1</summary>

```
ip prefix-list PFX_16_1_EXACT seq 5 permit 172.16.1.0/24

route-map R1_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_1_EXACT
 set as-path prepend 65100 65100 65100
route-map R1_TO_R4_OUT permit 30

router bgp 65100
 address-family ipv4
  neighbor 10.1.14.4 route-map R1_TO_R4_OUT out
```

</details>

<details>
<summary>Task 5 — MED on R1 and R3</summary>

**R1 — extend R1_TO_R4_OUT:**
```
ip prefix-list PFX_16_0_AGGREGATE seq 5 permit 172.16.0.0/16

route-map R1_TO_R4_OUT permit 20
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 100
```

**R3 — add R3_TO_R4_OUT:**
```
route-map R3_TO_R4_OUT permit 10
 match ip address prefix-list PFX_16_0_AGGREGATE
 set metric 50
route-map R3_TO_R4_OUT permit 20

router bgp 65100
 address-family ipv4
  neighbor 10.1.34.4 route-map R3_TO_R4_OUT out
```

</details>

<details>
<summary>Task 6 — RPL SET_COMMUNITY_AND_PREPEND on XR1</summary>

```
prefix-set P_XR1_ORIGINATE
  172.16.11.0/24
end-set
route-policy SET_COMMUNITY_AND_PREPEND
  if destination in P_XR1_ORIGINATE then
    set community (65100:300) additive
    set as-path prepend 65100 65100 65100
  endif
  pass
end-policy

router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy SET_COMMUNITY_AND_PREPEND out
```

</details>

<details>
<summary>Task 7 — Conditional advertisement on R1</summary>

```
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

To test: on R3 do `no aggregate-address 172.16.0.0 255.255.0.0` — observe 172.16.100.0/24
appearing at R4. Restore with `aggregate-address 172.16.0.0 255.255.0.0`.

</details>

---

## Section 9 — Troubleshooting Tickets

### Ticket 1 — 172.20.4.0/24 Not Preferred via R3

**Symptom:** `show ip bgp 172.20.4.0` on R1 shows the R1 path (via 10.1.14.4) as best
instead of R3 (via 10.0.0.3). Both paths are present but R3 is not winning.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Diagnosis path:**
1. Check LOCAL_PREF on both paths: `show ip bgp 172.20.4.0` at R1
2. If LOCAL_PREF is the same (both 150 or both 0), the issue is in STEER_R4_IN on R3
3. Check: `show route-map STEER_R4_IN` at R3 — look for zero matches on sequence 10
4. Check: `show ip prefix-list PFX_PREFER_172_20_4` — verify the prefix-list entry
5. Check: `show ip bgp neighbors 10.1.34.4 routes` at R3 — confirm 172.20.4.0/24 passes inbound filter

<details>
<summary>Fault and fix</summary>

The fault is `PFX_PREFER_172_20_4` having a wrong prefix (e.g., 172.20.4.0/25 instead of
172.20.4.0/24). Fix: correct the prefix-list entry, then `clear ip bgp 10.1.34.4 soft in`.

</details>

### Ticket 2 — R4 Not Preferring R3 Path for 172.16.0.0/16

**Symptom:** `show ip bgp 172.16.0.0/16` at R4 shows R1 path as best (or no MED
difference). MED 50 / MED 100 distinction is absent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Diagnosis path:**
1. Check: `show ip bgp 172.16.0.0/16` at R4 — note MED values in output
2. If both paths show MED 0, the outbound route-maps are not applied or not matching
3. At R3: `show route-map R3_TO_R4_OUT` — check hit count on seq 10
4. At R3: `show ip bgp neighbors 10.1.34.3 advertised-routes` — confirm 172.16.0.0/16 is in outbound updates
5. At R1: same checks on R1_TO_R4_OUT seq 20

<details>
<summary>Fault and fix</summary>

The fault is `R3_TO_R4_OUT` applied on the wrong neighbor (e.g., `neighbor 10.0.0.1
route-map R3_TO_R4_OUT out` instead of `neighbor 10.1.34.4`). Fix: apply to the correct
eBGP neighbor and `clear ip bgp 10.1.34.4 soft out`.

</details>

### Ticket 3 — AS-path Prepend Has No Effect at R4

**Symptom:** `show ip bgp 172.16.1.0` at R4 shows R1 path as best or with AS-path length
equal to R3's path. Prepend is not visible.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Diagnosis path:**
1. At R4: `show ip bgp 172.16.1.0` — compare AS-path lengths on R1 and R3 paths
2. If R1 path AS-path is `65100` (not prepended), R1_TO_R4_OUT seq 10 is not matching
3. At R1: `show route-map R1_TO_R4_OUT` — check hit count on seq 10
4. At R1: `show ip prefix-list PFX_16_1_EXACT` — verify the /24 match
5. At R1: `show ip bgp neighbors 10.1.14.4 advertised-routes` — confirm 172.16.1.0/24 is in updates

<details>
<summary>Fault and fix</summary>

The fault is LOCAL_PREF applied outbound instead of AS-path prepend (e.g., `set local-preference
200` in R1_TO_R4_OUT seq 10 instead of `set as-path prepend 65100 65100 65100`). LOCAL_PREF
is stripped on eBGP sessions and has zero effect at R4. Fix: correct the `set` clause and
`clear ip bgp 10.1.14.4 soft out`.

</details>

---

## Section 10 — Checklists

### Core Checklist

- [ ] R1 BGP table: 172.20.5.0/24 absent; 172.20.4.0/24 present with community 65100:100
- [ ] All AS 65100 routers: best path to 172.20.4.0/24 resolves via R3 (LOCAL_PREF 200)
- [ ] R4 BGP table: R3 path to 172.16.1.0/24 best (R1 path has 4-element AS-path)
- [ ] R4 BGP table: 172.16.0.0/16 R3 path MED=50 (best), R1 path MED=100
- [ ] R4 BGP table: 172.16.100.0/24 absent while R3 is up
- [ ] R2 BGP table: 172.16.11.0/24 has community 65100:300 and AS-path length 4

### Troubleshooting Checklist

- [ ] `show route-map <name>` shows non-zero hit counts on intended sequences
- [ ] `show ip bgp neighbors <x> advertised-routes` used to verify outbound policy effect
- [ ] `show ip bgp neighbors <x> routes` used to verify inbound policy effect
- [ ] After any route-map change: `clear ip bgp <neighbor> soft` applied
- [ ] LOCAL_PREF verified end-to-end with `show ip bgp <prefix>` across multiple routers
- [ ] MED comparison confirmed on R4 where both paths are from the same peer AS

---

## Section 11 — Script Exit Codes

| Script | Exit 0 | Exit 1 |
|--------|--------|--------|
| inject_scenario_01.py | Fault injected successfully | Connection failure or command error |
| inject_scenario_02.py | Fault injected successfully | Connection failure or command error |
| inject_scenario_03.py | Fault injected successfully | Connection failure or command error |
| apply_solution.py | Solution applied to all devices | One or more devices failed |
