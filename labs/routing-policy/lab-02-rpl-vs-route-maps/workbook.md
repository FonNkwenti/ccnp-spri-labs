# Lab 02 — RPL vs Route-Maps: Policy Sets and Hierarchical Policies

**Exam:** 300-510 SPRI | **Blueprint:** 3.1, 3.2.d, 3.2.j | **Time:** 90 min

---

## Section 1 — Overview

This lab introduces IOS-XR Routing Policy Language (RPL) by placing two XRv9k routers
(XR1, XR2) into the SP core you built across labs 00 and 01. The IOSv core (R1/R2/R3)
continues to run route-maps; XR1 and XR2 carry the same policies expressed in RPL.

By the end of this lab you will have:
- Brought XR1 and XR2 into the IS-IS L2 domain and iBGP full mesh
- Written the same inbound filtering policy in both route-map (R1) and RPL (XR1) syntax
- Built RPL named sets (`prefix-set`, `community-set`, `as-path-set`)
- Constructed a hierarchical parent policy that calls child policies with `apply`
- Written and instantiated a parameterized RPL policy
- Documented three fundamental differences between RPL and route-maps

---

## Section 2 — Topology Quick Reference

```
         AS 65100
┌────┐  L1  ┌────┐  L6 10.1.25.0/24 ┌──────┐
│ R1 ├──────┤ R2 ├─── Gi0/2 ─────── │ XR1  │ 10.0.0.5
└─┬──┘      └──┬─┘                   │Lo0   │ Lo1 172.16.11.0/24
  │L5          │L2                   └──┬───┘
  │            │                        │ L8 10.1.56.0/24
┌─┴──┐      ┌──┴─┐  L7 10.1.36.0/24 ┌──┴───┐
│ R3 ├──────┤    │                   │ XR2  │ 10.0.0.6
└─┬──┘ L3   └────┘                   └──────┘
  ├───── R4 (AS 65200)
  │  L4 ── R1:Gi0/1
```

| Link | Subnet          | Endpoints                  |
|------|-----------------|----------------------------|
| L1   | 10.1.12.0/24   | R1:Gi0/0 — R2:Gi0/0        |
| L2   | 10.1.23.0/24   | R2:Gi0/1 — R3:Gi0/0        |
| L3   | 10.1.34.0/24   | R3:Gi0/1 — R4:Gi0/0        |
| L4   | 10.1.14.0/24   | R1:Gi0/1 — R4:Gi0/1        |
| L5   | 10.1.13.0/24   | R1:Gi0/2 — R3:Gi0/2        |
| L6   | 10.1.25.0/24   | R2:Gi0/2 — XR1:Gi0/0/0/0   |
| L7   | 10.1.36.0/24   | R3:Gi0/3 — XR2:Gi0/0/0/0   |
| L8   | 10.1.56.0/24   | XR1:Gi0/0/0/1 — XR2:Gi0/0/0/1 |

---

## Section 3 — Starting State

**What is pre-loaded on R1/R2/R3/R4 (initial-configs = lab-01 solutions):**
- OSPF area 0, IS-IS L2, iBGP full mesh (R1/R2/R3 only)
- eBGP R1↔R4 (L4), eBGP R3↔R4 (L3) with FILTER_R4_IN and FILTER_R4_ASPATH
- Tag-based redistribution loop prevention (OSPF↔IS-IS via R2/R3)
- Community lists COMM_65100_100/1XX/2XX on all three SP routers
- R1 Lo1 (172.16.1.0/24) advertised into BGP; R4 Lo1/Lo2 (172.20.4.0/24, 172.20.5.0/24) in BGP

**What is NOT pre-loaded (student task):**
- XR1 and XR2 IS-IS and BGP config (initial-configs have IPs only)
- R2 Gi0/2 and R3 Gi0/3 IS-IS configuration (XR-facing links)
- XR1/XR2 iBGP sessions on R1/R2/R3
- All RPL policies on XR1 and XR2

**XR node boot note:** XRv9k nodes take 5–10 minutes to complete the boot sequence after
EVE-NG starts them. Wait for the `RP/0/0/CPU0:XR1#` prompt to appear on the console before
running setup or connecting via netmiko.

---

## Section 4 — Task 1: Activate XR1 and XR2

**Objective:** Bring XR1 and XR2 into the IS-IS L2 domain and iBGP full mesh in AS 65100.
Verify IS-IS adjacency with R2/R3 and full-mesh iBGP across all 5 AS 65100 routers.

**Estimated time:** 20 minutes

### Step 1.1 — Configure R2's Gi0/2 for IS-IS (IOS)

On R2, add Gi0/2 (L6 link to XR1) to the IS-IS SP process:

```
interface GigabitEthernet0/2
 description L6 to XR1 (IS-IS L2 adjacency)
 ip address 10.1.25.2 255.255.255.0
 ip router isis SP
 isis network point-to-point
 no shutdown
```

> Note: This link is NOT added to OSPF. XR1 and XR2 run IS-IS only, not OSPF.

### Step 1.2 — Configure R3's Gi0/3 for IS-IS (IOS)

On R3, add Gi0/3 (L7 link to XR2) to the IS-IS SP process:

```
interface GigabitEthernet0/3
 description L7 to XR2 (IS-IS L2 adjacency)
 ip address 10.1.36.3 255.255.255.0
 ip router isis SP
 isis network point-to-point
 no shutdown
```

### Step 1.3 — Configure XR1 IS-IS (XR)

On XR1, bring up IS-IS L2. Note that XR IS-IS syntax differs from IOS:
- `metric-style wide` is under `address-family ipv4 unicast` (not top-level)
- Each interface requires an explicit `address-family ipv4 unicast` block

```
router isis SP
 is-type level-2-only
 net 49.0001.0000.0000.0005.00
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
  !
 !
!
commit
```

### Step 1.4 — Configure XR2 IS-IS (XR)

On XR2, same structure but different NET and interfaces:

```
router isis SP
 is-type level-2-only
 net 49.0001.0000.0000.0006.00
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
  !
 !
!
commit
```

### Step 1.5 — Verify IS-IS adjacency

On R2: `show isis neighbors`
Expected: XR1 appears as a Level-2 IS-IS neighbor in state **Up** on Gi0/2.

On XR1: `show isis neighbors`
Expected: R2 and XR2 both appear as Level-2 neighbors in state **Up**.

On XR2: `show isis neighbors`
Expected: R3 and XR1 both appear as Level-2 neighbors in state **Up**.

Verify XR1 loopback is reachable from R1:
```
! On R1:
ping 10.0.0.5 source Loopback0 repeat 5
```
Expected: all 5 probes succeed via IS-IS.

### Step 1.6 — Configure RPL scaffolding PASS policy (XR)

**Before** configuring any BGP session on XR, define the PASS policy. Without it, once you
apply any policy to a neighbor-group, all unmatched routes are silently dropped.

On XR1 and XR2 (both):
```
route-policy PASS
  pass
end-policy
commit
```

### Step 1.7 — Configure iBGP on XR1 (XR)

```
router bgp 65100
 bgp router-id 10.0.0.5
 !
 address-family ipv4 unicast
  network 172.16.11.0/24
 !
 neighbor-group IBGP
  remote-as 65100
  update-source Loopback0
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
   next-hop-self
  !
 !
 neighbor 10.0.0.1
  use neighbor-group IBGP
 !
 neighbor 10.0.0.2
  use neighbor-group IBGP
 !
 neighbor 10.0.0.3
  use neighbor-group IBGP
 !
 neighbor 10.0.0.6
  use neighbor-group IBGP
 !
!
commit
```

### Step 1.8 — Configure iBGP on XR2 (XR)

Same structure as XR1 but no Lo1 network (XR2 has no customer prefix):

```
router bgp 65100
 bgp router-id 10.0.0.6
 !
 address-family ipv4 unicast
 !
 neighbor-group IBGP
  remote-as 65100
  update-source Loopback0
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
   next-hop-self
  !
 !
 neighbor 10.0.0.1
  use neighbor-group IBGP
 !
 neighbor 10.0.0.2
  use neighbor-group IBGP
 !
 neighbor 10.0.0.3
  use neighbor-group IBGP
 !
 neighbor 10.0.0.5
  use neighbor-group IBGP
 !
!
commit
```

### Step 1.9 — Expand iBGP full mesh on R1/R2/R3

On R1, add XR1 and XR2 to the IBGP peer-group:
```
router bgp 65100
 neighbor 10.0.0.5 peer-group IBGP
 neighbor 10.0.0.6 peer-group IBGP
 !
 address-family ipv4
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.6 activate
```

Repeat on R2 and R3 (same two neighbor statements each).

### Step 1.10 — Verify full-mesh iBGP

On R1: `show bgp summary | include 10.0.0`
Expected: 10.0.0.2, 10.0.0.3, 10.0.0.5, 10.0.0.6 all showing BGP state Established.

On XR1: `show bgp summary`
Expected: 4 neighbors (10.0.0.1/2/3/6) all Established.

On XR1, verify BGP routes are received:
```
show bgp ipv4 unicast
```
Expected: 172.16.1.0/24 (R1), 172.20.4.0/24 (R4, via R1/R3 iBGP), 172.20.5.0/24 filtered on R1 but visible via R3.

---

## Section 5 — Task 2: Side-by-Side Comparison (R1 Route-Map vs XR1 RPL)

**Objective:** Write a policy on XR1 (RPL) that achieves the same outcome as R1's FILTER_R4_IN
route-map. Both policies should: accept 172.20.4.0/24, deny 172.20.5.0/24, set community
65100:100, set local-preference 150 on accepted routes.

**Estimated time:** 15 minutes

### Step 2.1 — Review R1's existing IOS route-map (reference)

On R1: `show route-map FILTER_R4_IN`

The IOS approach:
- seq 10: inline `match ip address prefix-list PFX_R4_LO2_EXACT` → deny
- seq 20: inline `match ip address prefix-list PFX_R4_LE_24` → permit + set community + set local-pref
- Prefix-lists defined separately, referenced inline

### Step 2.2 — Build the RPL equivalent on XR1

Define the named sets first (RPL separates match objects from policy logic):
```
prefix-set P_CUSTOMER
  172.16.0.0/16 le 24
end-set
!
prefix-set P_XR1_CUSTOMER
  172.16.11.0/24
end-set
!
prefix-set P_BOGONS
  0.0.0.0/0 le 7,
  127.0.0.0/8 le 32,
  169.254.0.0/16 le 32,
  192.0.2.0/24 le 32,
  198.51.100.0/24 le 32,
  203.0.113.0/24 le 32
end-set
!
community-set C_SP_PREF
  65100:100
end-set
!
as-path-set AS_65200
  ios-regex '_65200$'
end-set
!
commit
```

Define the policy that matches R4 externals (compare with R1's FILTER_R4_IN):
```
route-policy RPL_FILTER_EBGP_EQUIV
  if destination in (172.20.5.0/24) then
    drop
  elseif destination in (172.20.0.0/16 le 24) then
    set community (65100:100) additive
    set local-preference 150
    pass
  else
    pass
  endif
end-policy
commit
```

### Step 2.3 — Inspect via show commands

On XR1:
```
show rpl route-policy RPL_FILTER_EBGP_EQUIV
show rpl prefix-set P_CUSTOMER
show rpl prefix-set P_BOGONS
show rpl community-set C_SP_PREF
show rpl as-path-set AS_65200
```

On R1 (IOS equivalent):
```
show route-map FILTER_R4_IN
show ip prefix-list PFX_R4_LE_24
show ip prefix-list PFX_R4_LO2_EXACT
show ip community-list COMM_65100_100
show ip as-path-access-list 1
```

**Discussion:** Notice the RPL approach defines named, reusable objects (`prefix-set P_BOGONS`)
that can be referenced by any number of policies. The IOS approach uses inline match clauses
or procedural lists that must be duplicated or chained if used in multiple route-maps.

---

## Section 6 — Task 3: RPL Named Sets

**Objective:** Demonstrate that RPL sets are reusable, composable, and inspectable as first-class
objects — contrast with IOS `ip prefix-list` / `ip community-list` which are procedural.

**Estimated time:** 10 minutes

### Step 3.1 — Reference the same prefix-set from two policies

Define a second policy on XR1 that reuses `P_CUSTOMER`:
```
route-policy IBGP_CUSTOMER_TAG
  if destination in P_CUSTOMER then
    set community (65100:400) additive
    pass
  else
    pass
  endif
end-policy
commit
```

On XR1:
```
show rpl prefix-set P_CUSTOMER references
```
Expected: both `RPL_FILTER_EBGP_EQUIV` and `IBGP_CUSTOMER_TAG` appear as references.
IOS has no equivalent — `ip prefix-list` has no reference tracking.

### Step 3.2 — Compare `as-path-set` with IOS `ip as-path access-list`

IOS R3 uses: `ip as-path access-list 1 permit _65200$`

XR1 equivalent:
```
as-path-set AS_65200
  ios-regex '_65200$'
end-set
```

On XR1: `show rpl as-path-set AS_65200`

Key difference: On IOS, `ip as-path access-list` is numbered or named but always a flat
sequential list. On XR, `as-path-set` is a named, typed object that can be composed into
hierarchical policies without duplication.

---

## Section 7 — Task 4: Hierarchical RPL

**Objective:** Build a parent policy `EBGP_IN` that calls two child policies in sequence.
The child policies are independent, reusable, and maintainable separately.

**Estimated time:** 15 minutes

### Step 4.1 — Build the child policies

On XR1:
```
route-policy FILTER_BOGONS
  if destination in P_BOGONS then
    drop
  endif
  pass
end-policy
!
route-policy SET_LOCAL_PREF_BY_COMMUNITY
  if community matches-any C_SP_PREF then
    set local-preference 150
  elseif community matches-any (65100:200) then
    set local-preference 120
  endif
  pass
end-policy
!
commit
```

> **Critical:** Both child policies end with `pass`. If a child policy ends without `pass`,
> XR treats the route as **implicitly dropped** at the end of that child, regardless of what
> the parent policy does next. This is a common misconfig on the 300-510 exam.

### Step 4.2 — Build the parent policy

```
route-policy EBGP_IN
  apply FILTER_BOGONS
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy
commit
```

### Step 4.3 — Inspect the hierarchical structure

```
show rpl policy EBGP_IN
show rpl policy EBGP_IN detail
```

The `detail` output expands the `apply` calls — you see the full effective policy inline.
This is equivalent to what an exam question might show you as a troubleshooting artifact.

### Step 4.4 — Verify `apply` semantics (drop propagation)

Temporarily modify FILTER_BOGONS to drop ALL routes (simulating a misconfiguration):
```
route-policy FILTER_BOGONS
  drop
end-policy
commit
```

On XR1: `show bgp ipv4 unicast`
Expected: no routes in the BGP table (FILTER_BOGONS drops all, parent EBGP_IN never reaches pass).

Restore the correct FILTER_BOGONS:
```
route-policy FILTER_BOGONS
  if destination in P_BOGONS then
    drop
  endif
  pass
end-policy
commit
```

Verify routes return: `show bgp ipv4 unicast`

**This is the exam-critical behavior:** An `apply` child that drops a route terminates the
parent policy at that point — `pass` statements in the parent after the `apply` are not reached.

### Step 4.5 — Apply IBGP_IN (uses the SET_LOCAL_PREF_BY_COMMUNITY child)

Update XR1's neighbor-group to use the more specific inbound policy:
```
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy IBGP_IN in
  !
 !
!
commit
```

Where IBGP_IN calls SET_LOCAL_PREF_BY_COMMUNITY:
```
route-policy IBGP_IN
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy
commit
```

On XR1: `show bgp ipv4 unicast 172.20.4.0/24 detail`
Expected: local-preference 150 (set by SET_LOCAL_PREF_BY_COMMUNITY via community 65100:100
that R1/R3 set on R4's route inbound — and propagated via iBGP to XR1).

---

## Section 8 — Task 5: Parameterized RPL

**Objective:** Write a parameterized RPL policy `MATCH_PREFIX_FROM_SET($set_name)` and
instantiate it twice in a parent policy with different `$set_name` arguments.

**Estimated time:** 10 minutes

### Step 5.1 — Define the second prefix-set for P_TRANSIT

```
prefix-set P_TRANSIT
  172.20.0.0/16 le 24
end-set
commit
```

### Step 5.2 — Write the parameterized policy

```
route-policy MATCH_PREFIX_FROM_SET($set_name)
  if destination in $set_name then
    set community (65100:300) additive
    pass
  else
    pass
  endif
end-policy
commit
```

### Step 5.3 — Write the parent that instantiates it twice

```
route-policy CLASSIFY_PREFIXES
  apply MATCH_PREFIX_FROM_SET(P_CUSTOMER)
  apply MATCH_PREFIX_FROM_SET(P_TRANSIT)
  pass
end-policy
commit
```

### Step 5.4 — Inspect

On XR1:
```
show rpl policy CLASSIFY_PREFIXES
show rpl policy CLASSIFY_PREFIXES detail
```

The `detail` output expands the instantiated `apply` calls, showing which `$set_name` argument
each invocation uses. IOS has no equivalent — to match two prefix-lists with different set
actions you need two separate route-map sequences, both with separate `match ip address prefix-list`
clauses.

### Step 5.5 — Apply CLASSIFY_PREFIXES to XR2's outbound iBGP

Temporarily apply the policy on XR1's iBGP outbound toward XR2 to observe community marking:
```
router bgp 65100
 neighbor 10.0.0.6
  address-family ipv4 unicast
   route-policy CLASSIFY_PREFIXES out
  !
 !
!
commit
```

On XR2: `show bgp ipv4 unicast`
Routes in P_CUSTOMER or P_TRANSIT ranges should have community 65100:300 added.

Restore the PASS policy on XR2 outbound:
```
router bgp 65100
 neighbor 10.0.0.6
  address-family ipv4 unicast
   route-policy PASS out
  !
 !
!
commit
```

---

## Section 9 — Troubleshooting Scenarios

Three exam-style troubleshooting tickets. Each describes a symptom. Your task is to isolate
the fault using show commands and fix it. **Do not read the solution until you have
diagnosed the fault.**

---

### Scenario 01 — XR1 Silent Route Drop

**Target device:** XR1
**Symptom:** After reconfiguring XR1's iBGP neighbor-group, XR1's BGP table is empty.
No neighbors show any received routes. The neighbors themselves show Established state.

**Allowed commands (diagnosis):**
```
show bgp ipv4 unicast summary
show bgp ipv4 unicast neighbors 10.0.0.2 routes
show rpl policy IBGP_IN detail
show rpl policy IBGP_IN_BROKEN detail
```

**Fault description (do not read until diagnosed):**
A misconfigured `IBGP_IN_BROKEN` child policy that ends without `pass` causes implicit drop
on all inbound routes. The neighbor-group's `route-policy IBGP_IN_BROKEN in` is applied,
replacing the working `IBGP_IN`.

**Commands to inject (injected by `inject_scenario_01.py`):**
```
route-policy IBGP_IN_BROKEN
  apply SET_LOCAL_PREF_BY_COMMUNITY
end-policy
commit
!
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy IBGP_IN_BROKEN in
  !
 !
!
commit
```

**Fix:**
Replace `IBGP_IN_BROKEN` with a corrected policy that includes `pass` at the end, or restore
the original `IBGP_IN` policy:
```
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy IBGP_IN in
  !
 !
!
commit
```

---

### Scenario 02 — IS-IS Adjacency Down on L6

**Target device:** R2
**Symptom:** XR1's IS-IS L2 adjacency to R2 drops. XR1 reports `show isis neighbors` shows
no neighbors on Gi0/0/0/0. XR2 adjacency to XR1 (L8) is still Up.

**Allowed commands (diagnosis):**
```
show isis neighbors                          ! on R2 and XR1
show isis interface GigabitEthernet0/2       ! on R2
show isis interface GigabitEthernet0/0/0/0   ! on XR1
show interface GigabitEthernet0/2            ! on R2
```

**Fault description (do not read until diagnosed):**
R2's Gi0/2 interface is shut down. The IS-IS process is still configured but the link
is down, so no hello packets are sent and the adjacency times out.

**Commands to inject (injected by `inject_scenario_02.py`):**
```
interface GigabitEthernet0/2
 shutdown
```

**Fix:** On R2:
```
interface GigabitEthernet0/2
 no shutdown
```
Verify: `show isis neighbors` on R2 shows XR1 back in Up state within 30 seconds.

---

### Scenario 03 — RPL Prefix-Set Too Broad

**Target device:** XR1
**Symptom:** XR1 is marking 172.20.5.0/24 (R4's second external prefix, which should be
treated as transit) with community 65100:400 via IBGP_CUSTOMER_TAG. This community marks
it as a customer route, bypassing the intended R4 external treatment.

**Allowed commands (diagnosis):**
```
show bgp ipv4 unicast 172.20.5.0/24 detail  ! on XR1
show rpl prefix-set P_CUSTOMER
show rpl policy IBGP_CUSTOMER_TAG detail
```

**Fault description (do not read until diagnosed):**
`P_CUSTOMER` is incorrectly widened to `172.0.0.0/8 le 24`, which inadvertently matches
R4's external 172.20.5.0/24. The intended scope is 172.16.0.0/16 le 24 (SP customer range only).

**Commands to inject (injected by `inject_scenario_03.py`):**
```
prefix-set P_CUSTOMER
  172.0.0.0/8 le 24
end-set
commit
```

**Fix:**
```
prefix-set P_CUSTOMER
  172.16.0.0/16 le 24
end-set
commit
```
Verify: `show bgp ipv4 unicast 172.20.5.0/24 detail` on XR1 — community 65100:400 absent.

---

## Section 10 — RPL vs Route-Map Differences

**Objective 6:** Document three fundamental behavioral differences. Fill in the table based
on what you observed during this lab.

| Behavior | IOS Route-Map | IOS-XR RPL |
|----------|--------------|------------|
| Implicit end-of-policy | Implicit deny (unmatched routes dropped) | Implicit pass (unapplied session) **or** implicit drop (once any policy applied to that session) |
| Match object scope | Inline `match ip address prefix-list NAME` — list is procedure-local | Named `prefix-set NAME` — defined once, reused across any number of policies |
| Hierarchical composition | `continue N` — jumps to a later sequence in the same route-map | `apply CHILD_POLICY` — calls a separate, named, independently testable policy |

**Additional difference to note from Task 4.4:**
When a called child policy ends with `drop`, the drop propagates to the parent — the parent's
`pass` after the `apply` is never reached. Route-map `continue` cannot produce this effect
since all sequences are in the same flat list.

---

## Section 11 — Verification Checklist

Before marking this lab complete, confirm each item:

- [ ] R2: `show isis neighbors` shows XR1 (10.1.25.5) as L2 Up on Gi0/2
- [ ] R3: `show isis neighbors` shows XR2 (10.1.36.6) as L2 Up on Gi0/3
- [ ] XR1: `show isis neighbors` shows R2 and XR2 both as L2 Up
- [ ] XR2: `show isis neighbors` shows R3 and XR1 both as L2 Up
- [ ] R1: `show bgp summary` shows 10.0.0.5 and 10.0.0.6 as Established
- [ ] XR1: `show bgp summary` shows 4 iBGP neighbors Established
- [ ] XR1: `show bgp ipv4 unicast 172.20.4.0/24` shows local-preference 150
- [ ] XR1: `show rpl prefix-set P_CUSTOMER references` lists at least 2 policies
- [ ] XR1: `show rpl policy EBGP_IN detail` expands the two `apply` call sites
- [ ] XR1: `show rpl policy CLASSIFY_PREFIXES detail` shows parameterized instantiation
- [ ] After fault recovery in Task 4.4: XR1 BGP table repopulated with all expected routes

---

## Section 12 — Solutions

<details>
<summary>Task 1 — R2 Gi0/2 IS-IS</summary>

```cisco
interface GigabitEthernet0/2
 description L6 to XR1 (IS-IS L2 adjacency)
 ip address 10.1.25.2 255.255.255.0
 ip router isis SP
 isis network point-to-point
 no shutdown
```
</details>

<details>
<summary>Task 1 — R3 Gi0/3 IS-IS</summary>

```cisco
interface GigabitEthernet0/3
 description L7 to XR2 (IS-IS L2 adjacency)
 ip address 10.1.36.3 255.255.255.0
 ip router isis SP
 isis network point-to-point
 no shutdown
```
</details>

<details>
<summary>Task 1 — XR1 complete IS-IS + BGP base config</summary>

```xr
! IS-IS
router isis SP
 is-type level-2-only
 net 49.0001.0000.0000.0005.00
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
  !
 !
!
commit
!
! PASS scaffolding (required before any BGP policy config)
route-policy PASS
  pass
end-policy
commit
!
! BGP
router bgp 65100
 bgp router-id 10.0.0.5
 address-family ipv4 unicast
  network 172.16.11.0/24
 !
 neighbor-group IBGP
  remote-as 65100
  update-source Loopback0
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
   next-hop-self
  !
 !
 neighbor 10.0.0.1
  use neighbor-group IBGP
 !
 neighbor 10.0.0.2
  use neighbor-group IBGP
 !
 neighbor 10.0.0.3
  use neighbor-group IBGP
 !
 neighbor 10.0.0.6
  use neighbor-group IBGP
 !
!
commit
```
</details>

<details>
<summary>Task 4 — Hierarchical EBGP_IN on XR1 (full set)</summary>

```xr
route-policy FILTER_BOGONS
  if destination in P_BOGONS then
    drop
  endif
  pass
end-policy
!
route-policy SET_LOCAL_PREF_BY_COMMUNITY
  if community matches-any C_SP_PREF then
    set local-preference 150
  elseif community matches-any (65100:200) then
    set local-preference 120
  endif
  pass
end-policy
!
route-policy IBGP_IN
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy
!
route-policy EBGP_IN
  apply FILTER_BOGONS
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy
commit
```
</details>

<details>
<summary>Task 5 — Parameterized MATCH_PREFIX_FROM_SET</summary>

```xr
prefix-set P_TRANSIT
  172.20.0.0/16 le 24
end-set
!
route-policy MATCH_PREFIX_FROM_SET($set_name)
  if destination in $set_name then
    set community (65100:300) additive
    pass
  else
    pass
  endif
end-policy
!
route-policy CLASSIFY_PREFIXES
  apply MATCH_PREFIX_FROM_SET(P_CUSTOMER)
  apply MATCH_PREFIX_FROM_SET(P_TRANSIT)
  pass
end-policy
commit
```
</details>
