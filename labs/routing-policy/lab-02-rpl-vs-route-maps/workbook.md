# Lab 02 — RPL vs Route-Maps: Policy Sets and Hierarchical Policies

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

**Exam Objectives:** 3.1 — Implement and troubleshoot routing policy · 3.2.d — RPL named sets · 3.2.j — Hierarchical and parameterized RPL policies

This lab places two IOS-XRv 9000 nodes (XR1, XR2) into the existing IOSv SP core and teaches IOS-XR Routing Policy Language (RPL) by direct comparison with the IOS route-map you built in lab-00. The same filtering policy is expressed in both languages side-by-side so the structural differences are visible immediately.

### Route-Map vs RPL: Core Structural Difference

| Concept | IOS Route-Map | IOS-XR RPL |
|---------|---------------|-----------|
| Match objects | Inline `match ip address prefix-list NAME` | Named `prefix-set`, `community-set`, `as-path-set` — first-class typed objects |
| Policy logic | Sequenced permit/deny with implicit deny at end | `if/elseif/else/endif` block; implicit behavior depends on whether any policy is applied |
| Composition | `continue N` — jumps to a later sequence in the same map | `apply CHILD_POLICY` — calls a separate, independently named policy |
| Reuse | Prefix-lists referenced individually, no reference tracking | Sets are shared across any number of policies; `show rpl prefix-set NAME references` tracks usage |
| Parameterization | Not supported | `route-policy NAME($param)` — instantiate the same logic with different set arguments |

### RPL Implicit Behavior — Critical Exam Point

When **no** route-policy is applied to a BGP session, XR allows all routes (open policy). Once **any** route-policy is applied, all routes that reach the end of the policy without an explicit `pass` or `drop` are **implicitly dropped**. This is the opposite of IOS route-maps (which have an implicit deny only at the *list* end, not per-sequence).

When a child policy called via `apply` ends without `pass`, the drop propagates to the parent — any `pass` in the parent after the `apply` is never reached.

### Named RPL Sets

```
prefix-set P_CUSTOMER
  172.16.0.0/16 le 24
end-set

community-set C_SP_PREF
  65100:100
end-set

as-path-set AS_65200
  ios-regex '_65200$'
end-set
```

Sets are defined once and referenced by name in any number of policies. IOS has no equivalent reference tracking — `ip prefix-list` and `ip community-list` are procedure-local.

### Hierarchical and Parameterized Policies

```
! Child policy
route-policy FILTER_BOGONS
  if destination in P_BOGONS then
    drop
  endif
  pass                           ! explicit pass required
end-policy

! Parent calls child via 'apply'
route-policy EBGP_IN
  apply FILTER_BOGONS
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy

! Parameterized policy
route-policy MATCH_PREFIX_FROM_SET($set_name)
  if destination in $set_name then
    set community (65100:300) additive
    pass
  else
    pass
  endif
end-policy
```

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| XR IS-IS L2 configuration | IOS-XR IS-IS syntax: `address-family` blocks, `passive`, `point-to-point` |
| XR iBGP `neighbor-group` | `use neighbor-group`, `route-policy PASS in/out` scaffolding |
| RPL named sets | Define `prefix-set`, `community-set`, `as-path-set` and verify with `show rpl` |
| RPL policy logic | `if/elseif/else` blocks; `drop` vs `pass`; implicit end-of-policy behavior |
| Hierarchical `apply` | Call child policies from a parent; understand drop propagation |
| Parameterized policies | Define `$param` and instantiate with `apply POLICY(SET_NAME)` |
| RPL vs route-map comparison | Identify three structural differences and the implicit-behavior distinction |

---

## 2. Topology & Scenario

**Scenario:** SP-CORE is evaluating a migration from IOS to IOS-XR on two new nodes. XR1 and XR2 are connected to the existing IOSv SP core via IS-IS L2 adjacencies (L6, L7) and an XR backbone link (L8). Your task is to bring the XR nodes into the IS-IS domain and iBGP full mesh, then implement the same inbound filtering policy that R1 uses — first in RPL on XR1, then extended with hierarchical and parameterized policies that have no IOS route-map equivalent.

```
           ┌──────────────────────────────────────────────────────────────┐
           │                          AS 65100                             │
           │                                                               │
           │    ┌────┐   L1 10.1.12.0/24   ┌────┐   L6 10.1.25.0/24     │
           │    │ R1 ├────────────────────┤ R2 ├───────────────────────►│XR1│
           │    └──┬─┘  OSPF/IS-IS/iBGP    └──┬─┘  IS-IS L2 only        └──┬┘
           │       │ L5 10.1.13.0/24       L2 │ 10.1.23.0/24               │
           │       │                          │                          L8 │ 10.1.56.0/24
           │    ┌──┴────────────────────────┴──┐   L7 10.1.36.0/24     ┌──┴┐
           │    │              R3              ├───────────────────────►│XR2│
           │    └──────────────────────────────┘  IS-IS L2 only         └───┘
           └──────────────────────────────────────────────────────────────┘
               │ L4 (eBGP)               │ L3 (eBGP)
           10.1.14.0/24             10.1.34.0/24
               └──────── R4 ────────────┘
                       AS 65200
                  Lo1: 172.20.4.0/24
                  Lo2: 172.20.5.0/24
```

**Key relationships:**

- **IOSv core** (R1/R2/R3): runs OSPF area 0, IS-IS L2, and iBGP full-mesh — pre-loaded from lab-01 solutions. R4 (AS65200) has eBGP sessions to R1 (L4) and R3 (L3).
- **XR1** connects to R2 via L6 (IS-IS L2 only — not OSPF). XR1's Lo1 `172.16.11.0/24` is its demo customer prefix.
- **XR2** connects to R3 via L7 (IS-IS L2 only) and to XR1 via L8 (IS-IS L2 backbone link between the two XR nodes).
- **iBGP full mesh** spans all five AS65100 routers: R1, R2, R3, XR1, XR2.
- L6/L7/L8 carry **IS-IS L2 only** — these links are not added to OSPF.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP Core / eBGP Edge | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | SP Core / iBGP Transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | SP Core / eBGP Edge | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | External Peer | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| XR1 | IOS-XR RPL Node | IOS-XRv 9000 | xrv9k-fullk9.iso (7.x) |
| XR2 | IOS-XR RPL Node | IOS-XRv 9000 | xrv9k-fullk9.iso (7.x) |

> **Boot note:** XRv9k nodes take 5–10 minutes to fully boot. Wait for the `RP/0/0/CPU0:XR1#` prompt before running setup or connecting.

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router-ID, iBGP source |
| R1 | Loopback1 | 172.16.1.0/24 | Customer prefix in BGP |
| R2 | Loopback0 | 10.0.0.2/32 | Router-ID, iBGP source |
| R3 | Loopback0 | 10.0.0.3/32 | Router-ID, iBGP source |
| R4 | Loopback0 | 10.0.0.4/32 | Router-ID |
| R4 | Loopback1 | 172.20.4.0/24 | External prefix #1 (accepted on R1) |
| R4 | Loopback2 | 172.20.5.0/24 | External prefix #2 (filtered on R1) |
| XR1 | Loopback0 | 10.0.0.5/32 | Router-ID, iBGP source |
| XR1 | Loopback1 | 172.16.11.0/24 | RPL match demo prefix |
| XR2 | Loopback0 | 10.0.0.6/32 | Router-ID, iBGP source |

### Cabling

| Link ID | Source | Interface | Target | Interface | Subnet | Protocols |
|---------|--------|-----------|--------|-----------|--------|-----------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | OSPF area 0 / IS-IS L2 / iBGP |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/24 | OSPF area 0 / IS-IS L2 / iBGP |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 | 10.1.34.0/24 | eBGP only |
| L4 | R1 | Gi0/1 | R4 | Gi0/1 | 10.1.14.0/24 | eBGP only |
| L5 | R1 | Gi0/2 | R3 | Gi0/2 | 10.1.13.0/24 | OSPF area 0 / IS-IS L2 / iBGP |
| L6 | R2 | Gi0/2 | XR1 | Gi0/0/0/0 | 10.1.25.0/24 | IS-IS L2 only |
| L7 | R3 | Gi0/3 | XR2 | Gi0/0/0/0 | 10.1.36.0/24 | IS-IS L2 only |
| L8 | XR1 | Gi0/0/0/1 | XR2 | Gi0/0/0/1 | 10.1.56.0/24 | IS-IS L2 only |

### Console Access

| Device | Port | Connection |
|--------|------|------------|
| R1–R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| XR1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| XR2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded on R1/R2/R3/R4 (from lab-01 solutions):**
- OSPF area 0, IS-IS L2 (SP instance), and iBGP full-mesh on R1/R2/R3
- eBGP sessions R1↔R4 (L4) and R3↔R4 (L3); `FILTER_R4_IN` on R1; `FILTER_R4_ASPATH` on R3
- Community lists, tag-based redistribution loop prevention, R1 Lo1 and R4 Lo1/Lo2 in BGP
- R2 and R3: interface IP addresses on Gi0/2 and Gi0/3 (L6, L7 links) but IS-IS **not yet enabled** on those interfaces

**IS pre-loaded on XR1 and XR2 (initial-configs = IPs only):**
- Hostnames, Loopback0/Loopback1 IP addresses, core link IPs

**IS NOT pre-loaded (student configures this):**
- IS-IS on R2 Gi0/2 (L6) and R3 Gi0/3 (L7)
- XR1 and XR2 IS-IS L2 process and interface assignments
- `route-policy PASS` scaffolding on XR1 and XR2 (required before BGP session activation)
- XR1 and XR2 iBGP sessions (neighbor-group IBGP)
- R1/R2/R3 iBGP sessions to 10.0.0.5 and 10.0.0.6
- All RPL policies, named sets, and hierarchical/parameterized policies on XR1

---

## 5. Lab Challenge: Core Implementation

### Task 1: Activate XR1 and XR2 in IS-IS and iBGP

Bring XR1 and XR2 into the IS-IS L2 domain and iBGP full mesh:

- On **R2**: add Gi0/2 (L6) to IS-IS SP — `ip router isis SP`, `isis network point-to-point`. Do **not** add to OSPF.
- On **R3**: add Gi0/3 (L7) to IS-IS SP — same. Do not add to OSPF.
- On **XR1**: configure IS-IS SP (`is-type level-2-only`, NET `49.0001.0000.0000.0005.00`). Include Loopback0 (passive), Gi0/0/0/0 (L6, point-to-point), and Gi0/0/0/1 (L8, point-to-point). Note XR IS-IS uses `address-family ipv4 unicast` blocks per interface and `metric-style wide` under the process AF block.
- On **XR2**: same structure, NET `49.0001.0000.0000.0006.00`, interfaces Loopback0, Gi0/0/0/0 (L7), Gi0/0/0/1 (L8).
- On **XR1 and XR2**: define `route-policy PASS` with a single `pass` statement **before** configuring any BGP. This is the XR scaffolding policy that prevents implicit drop when a policy is first applied.
- On **XR1**: configure iBGP AS 65100 with `neighbor-group IBGP` (`remote-as 65100`, `update-source Loopback0`, `next-hop-self`, `route-policy PASS in/out`). Add neighbors 10.0.0.1, 10.0.0.2, 10.0.0.3, 10.0.0.6. Advertise `network 172.16.11.0/24`.
- On **XR2**: same neighbor-group structure, neighbors 10.0.0.1, 10.0.0.2, 10.0.0.3, 10.0.0.5. No network statement.
- On **R1, R2, R3**: add neighbors 10.0.0.5 and 10.0.0.6 to the existing IBGP peer-group.

**Verification:** `show isis neighbors` on R2, R3, XR1, XR2 — all show Level-2 Up adjacencies. `show bgp ipv4 unicast summary` on XR1 — four neighbors (10.0.0.1/2/3/6) all Established. `ping 10.0.0.5 source Loopback0` from R1 succeeds.

---

### Task 2: RPL Side-by-Side with R1's Route-Map

Write an RPL policy on XR1 that achieves the same outcome as R1's `FILTER_R4_IN` route-map: accept `172.20.4.0/24`, deny `172.20.5.0/24`, set community 65100:100 and local-preference 150 on accepted routes.

First define the named sets:

```
prefix-set P_CUSTOMER
  172.16.0.0/16 le 24
end-set

prefix-set P_BOGONS
  0.0.0.0/0 le 7,
  127.0.0.0/8 le 32,
  169.254.0.0/16 le 32,
  192.0.2.0/24 le 32,
  198.51.100.0/24 le 32,
  203.0.113.0/24 le 32
end-set

community-set C_SP_PREF
  65100:100
end-set

as-path-set AS_65200
  ios-regex '_65200$'
end-set
```

Then define `RPL_FILTER_EBGP_EQUIV` using `if/elseif/else`:

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
```

Observe the contrast: IOS route-map uses sequential `deny 10` / `permit 20` sequences with separate prefix-lists. RPL expresses the same logic as a single structured conditional with the match inline.

**Verification:** `show rpl route-policy RPL_FILTER_EBGP_EQUIV` — full policy text displayed. `show rpl prefix-set P_CUSTOMER` — set contents confirmed. Compare with R1's `show route-map FILTER_R4_IN` and `show ip prefix-list`.

---

### Task 3: RPL Named Sets and Reuse

Define a second policy `IBGP_CUSTOMER_TAG` on XR1 that reuses `P_CUSTOMER`:

```
route-policy IBGP_CUSTOMER_TAG
  if destination in P_CUSTOMER then
    set community (65100:400) additive
    pass
  else
    pass
  endif
end-policy
```

Verify that `P_CUSTOMER` is referenced by both policies:

```
show rpl prefix-set P_CUSTOMER references
```

IOS has no equivalent — `ip prefix-list` has no reference tracking. Document the key operational value: on XR, changing `P_CUSTOMER` once updates the behavior of every policy that references it simultaneously.

Compare `as-path-set AS_65200` (XR) with R3's `ip as-path access-list 1 permit _65200$` (IOS). Same regex engine, different object model: the XR named set is typed, trackable, and composable; the IOS ACL is a flat sequential list with a number or name.

**Verification:** `show rpl prefix-set P_CUSTOMER references` lists at least two policies. `show rpl as-path-set AS_65200` shows the `ios-regex` entry.

---

### Task 4: Hierarchical RPL

Build a parent policy `EBGP_IN` that calls two independent child policies:

```
route-policy FILTER_BOGONS
  if destination in P_BOGONS then
    drop
  endif
  pass                    ! <-- explicit pass required; omitting this causes implicit drop
end-policy

route-policy SET_LOCAL_PREF_BY_COMMUNITY
  if community matches-any C_SP_PREF then
    set local-preference 150
  elseif community matches-any (65100:200) then
    set local-preference 120
  endif
  pass
end-policy

route-policy IBGP_IN
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy

route-policy EBGP_IN
  apply FILTER_BOGONS
  apply SET_LOCAL_PREF_BY_COMMUNITY
  pass
end-policy
```

Apply `IBGP_IN` as the inbound policy on XR1's neighbor-group (replacing `PASS`):
```
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy IBGP_IN in
```

Then test drop propagation: temporarily modify `FILTER_BOGONS` to just `drop` (no conditions). Observe that XR1's BGP table empties — the child's drop propagates through the parent. Restore the correct `FILTER_BOGONS` and verify the table repopulates.

**Verification:** `show rpl policy EBGP_IN detail` — `apply` calls expand inline. `show bgp ipv4 unicast 172.20.4.0/24` on XR1 after restoring — local-preference 150 applied via `SET_LOCAL_PREF_BY_COMMUNITY`.

---

### Task 5: Parameterized RPL

Define a parameterized policy and a second prefix-set for transit prefixes:

```
prefix-set P_TRANSIT
  172.20.0.0/16 le 24
end-set

route-policy MATCH_PREFIX_FROM_SET($set_name)
  if destination in $set_name then
    set community (65100:300) additive
    pass
  else
    pass
  endif
end-policy

route-policy CLASSIFY_PREFIXES
  apply MATCH_PREFIX_FROM_SET(P_CUSTOMER)
  apply MATCH_PREFIX_FROM_SET(P_TRANSIT)
  pass
end-policy
```

Temporarily apply `CLASSIFY_PREFIXES` outbound toward XR2 to observe community marking:
```
router bgp 65100
 neighbor 10.0.0.6
  address-family ipv4 unicast
   route-policy CLASSIFY_PREFIXES out
```

On XR2: verify routes in `P_CUSTOMER` and `P_TRANSIT` ranges carry community 65100:300.

Restore the PASS policy on XR1 outbound to XR2 after verification.

**Verification:** `show rpl policy CLASSIFY_PREFIXES detail` — two parameterized instantiations visible, each showing the `$set_name` argument resolved. IOS has no equivalent — two separate route-map sequences would be required.

---

### Task 6: Document RPL vs Route-Map Differences

After completing Tasks 2–5, complete this comparison table in your lab notes:

| Behavior | IOS Route-Map | IOS-XR RPL |
|----------|--------------|------------|
| Implicit end-of-policy | Implicit deny — unmatched routes dropped | Implicit drop once any policy applied; explicit `pass` required |
| Match object scope | Inline per-sequence; no reference tracking | Named typed sets; `show rpl X references` tracks usage |
| Composition | `continue N` — same flat list | `apply CHILD` — separate, independently testable policy |
| Parameterization | Not supported | `$param` in policy signature; instantiated with `apply P(SET)` |

Additional finding from Task 4: a child policy that ends without `pass` propagates a drop through the parent — no IOS route-map analog exists because sequences share a flat list.

---

## 6. Verification & Analysis

### Task 1: IS-IS and iBGP Activation

```
R2# show isis neighbors

System Id      Type Interface   IP Address      State Holdtime
R1             L2   Gi0/0       10.1.12.1       UP    23
R3             L2   Gi0/1       10.1.23.3       UP    24
XR1            L2   Gi0/2       10.1.25.5       UP    25    ! ← XR1 IS-IS L2 up on L6
```

```
RP/0/0/CPU0:XR1# show bgp ipv4 unicast summary

Neighbor        Spk  AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.0.0.1          0 65100      12      12        5    0    0 00:04:11          3
10.0.0.2          0 65100      11      11        5    0    0 00:04:09          3
10.0.0.3          0 65100      12      12        5    0    0 00:04:10          3
10.0.0.6          0 65100      10      10        5    0    0 00:03:55          3    ! ← XR2 iBGP
```

### Task 2: RPL Policy and Named Sets

```
RP/0/0/CPU0:XR1# show rpl route-policy RPL_FILTER_EBGP_EQUIV

route-policy RPL_FILTER_EBGP_EQUIV
  if destination in (172.20.5.0/24) then
    drop                                    ! ← inline destination match; drop explicit
  elseif destination in (172.20.0.0/16 le 24) then
    set community (65100:100) additive
    set local-preference 150
    pass
  else
    pass
  endif
end-policy
```

### Task 3: Named Set Reference Tracking

```
RP/0/0/CPU0:XR1# show rpl prefix-set P_CUSTOMER references

Prefix-set P_CUSTOMER referenced by:
  route-policy: RPL_FILTER_EBGP_EQUIV
  route-policy: IBGP_CUSTOMER_TAG            ! ← same set used by two policies
```

### Task 4: Hierarchical Policy Expansion

```
RP/0/0/CPU0:XR1# show rpl policy EBGP_IN detail

route-policy EBGP_IN
  # apply FILTER_BOGONS expanded:
  if destination in P_BOGONS then
    drop
  endif
  pass
  # apply SET_LOCAL_PREF_BY_COMMUNITY expanded:
  if community matches-any C_SP_PREF then
    set local-preference 150
  elseif community matches-any (65100:200) then
    set local-preference 120
  endif
  pass
  pass                                        ! ← EBGP_IN's own pass
end-policy
```

### Task 5: Parameterized Policy

```
RP/0/0/CPU0:XR1# show rpl policy CLASSIFY_PREFIXES detail

route-policy CLASSIFY_PREFIXES
  # apply MATCH_PREFIX_FROM_SET(P_CUSTOMER) expanded:
  if destination in P_CUSTOMER then           ! ← $set_name resolved to P_CUSTOMER
    set community (65100:300) additive
    pass
  else
    pass
  endif
  # apply MATCH_PREFIX_FROM_SET(P_TRANSIT) expanded:
  if destination in P_TRANSIT then            ! ← $set_name resolved to P_TRANSIT
    set community (65100:300) additive
    pass
  else
    pass
  endif
  pass
end-policy
```

---

## 7. Verification Cheatsheet

### XR IS-IS Configuration Skeleton

```
router isis SP
 is-type level-2-only
 net 49.0001.0000.0000.000X.00
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/N
  point-to-point
  address-family ipv4 unicast
  !
 !
!
commit
```

### XR BGP with Neighbor-Group Skeleton

```
! Define PASS policy first — always before BGP config
route-policy PASS
  pass
end-policy
commit

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
 neighbor 10.0.0.X
  use neighbor-group IBGP
 !
!
commit
```

### RPL Quick Reference

| Command | What to Look For |
|---------|-----------------|
| `show rpl route-policy NAME` | Full policy text |
| `show rpl route-policy NAME detail` | Inline-expanded `apply` calls |
| `show rpl prefix-set NAME` | Prefix entries in the set |
| `show rpl prefix-set NAME references` | Policies using this set |
| `show rpl community-set NAME` | Community values in the set |
| `show rpl as-path-set NAME` | AS-path regex entries |
| `show bgp ipv4 unicast summary` | Neighbor state and received prefix counts |
| `show bgp ipv4 unicast` | Full BGP table (XR) |
| `show bgp ipv4 unicast X.X.X.X/M` | Per-prefix detail, LOCAL_PREF, community |

### Common RPL Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| BGP table empty after applying any policy | Child or parent policy ends without `pass`; implicit drop |
| `apply CHILD` drop not expected | Child policy reached `drop` — this propagates through `apply`; parent's subsequent `pass` is not reached |
| Named set change has no effect | `commit` not executed after set modification |
| XR neighbor not coming up | `route-policy PASS` not defined before activating the BGP session; XR requires a policy to be present |
| IOS neighbor sees XR routes with wrong attributes | RPL `set community` requires `additive` flag to append; without it, existing community is replaced |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS and iBGP Activation

<details>
<summary>Click to view R2 IS-IS on Gi0/2</summary>

```
interface GigabitEthernet0/2
 ip router isis SP
 isis network point-to-point
```
</details>

<details>
<summary>Click to view R3 IS-IS on Gi0/3</summary>

```
interface GigabitEthernet0/3
 ip router isis SP
 isis network point-to-point
```
</details>

<details>
<summary>Click to view XR1 IS-IS + PASS + iBGP</summary>

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
!
route-policy PASS
  pass
end-policy
commit
!
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
<summary>Click to view XR2 IS-IS + PASS + iBGP</summary>

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
!
route-policy PASS
  pass
end-policy
commit
!
router bgp 65100
 bgp router-id 10.0.0.6
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
</details>

<details>
<summary>Click to view R1/R2/R3 — add XR neighbors</summary>

```
! On R1, R2, and R3 (same two lines each):
router bgp 65100
 neighbor 10.0.0.5 peer-group IBGP
 neighbor 10.0.0.6 peer-group IBGP
 !
 address-family ipv4
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.6 activate
```
</details>

---

### Tasks 2 & 3: Named Sets and RPL_FILTER_EBGP_EQUIV

<details>
<summary>Click to view XR1 named sets and RPL_FILTER_EBGP_EQUIV</summary>

```
prefix-set P_CUSTOMER
  172.16.0.0/16 le 24
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
!
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
!
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
</details>

---

### Task 4: Hierarchical EBGP_IN

<details>
<summary>Click to view XR1 hierarchical policies and iBGP application</summary>

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
!
router bgp 65100
 neighbor-group IBGP
  address-family ipv4 unicast
   route-policy IBGP_IN in
  !
 !
!
commit
```
</details>

---

### Task 5: Parameterized MATCH_PREFIX_FROM_SET

<details>
<summary>Click to view XR1 parameterized policy and CLASSIFY_PREFIXES</summary>

```
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

---

## 9. Troubleshooting Scenarios

Each ticket targets a real RPL or IS-IS misconfiguration. Inject the fault, diagnose with `show` commands, then restore.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore
```

---

### Ticket 1 — "XR1 BGP Table Is Empty"

The NOC reports that after a policy change on XR1, the BGP table is completely empty. All four iBGP neighbors show Established state and send Updates, but no routes are installed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show bgp ipv4 unicast` on XR1 shows all expected prefixes. `show bgp ipv4 unicast 172.20.4.0/24` shows local-preference 150.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On XR1: `show bgp ipv4 unicast summary` — all neighbors Established, but PfxRcd shows 0 for all.
2. On XR1: `show bgp ipv4 unicast neighbors 10.0.0.2 routes` — no routes listed despite active session.
3. On XR1: `show running-config formal | include route-policy IBGP` — look for the inbound policy name applied to the neighbor-group.
4. On XR1: `show rpl policy IBGP_IN_BROKEN detail` — look for the missing `pass` at the end of the child policy or the top-level policy.
5. Root cause: a new policy `IBGP_IN_BROKEN` was swapped in as the neighbor-group inbound policy. It calls `SET_LOCAL_PREF_BY_COMMUNITY` via `apply` but ends without `pass`. Every route reaching the end of the policy hits an implicit drop.
</details>

<details>
<summary>Click to view Fix</summary>

On XR1: restore the original `IBGP_IN` policy as the inbound policy.

```
RP/0/0/CPU0:XR1# conf t
RP/0/0/CPU0:XR1(config)# router bgp 65100
RP/0/0/CPU0:XR1(config-bgp)# neighbor-group IBGP
RP/0/0/CPU0:XR1(config-bgp-nbr-grp)# address-family ipv4 unicast
RP/0/0/CPU0:XR1(config-bgp-nbr-grp-af)# route-policy IBGP_IN in
RP/0/0/CPU0:XR1(config-bgp-nbr-grp-af)# commit
```

Verify: `show bgp ipv4 unicast` repopulates with all expected routes within seconds.
</details>

---

### Ticket 2 — "XR1 IS-IS Adjacency with R2 Is Down"

The NOC reports that XR1 shows no IS-IS Level-2 neighbor on Gi0/0/0/0 (the L6 link to R2). XR2's adjacency to XR1 on L8 is still Up. BGP sessions that depend on R2's loopback as next-hop are failing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show isis neighbors` on R2 shows XR1 (10.1.25.5) in Up state. `show isis neighbors` on XR1 shows R2 in Up state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On XR1: `show isis neighbors` — Gi0/0/0/0 adjacency absent or in Init state.
2. On R2: `show isis neighbors` — XR1 absent.
3. On R2: `show interface GigabitEthernet0/2` — look at line protocol status. If "administratively down," the interface was shut.
4. On R2: `show isis interface GigabitEthernet0/2` — IS-IS process is configured but the interface is down, so no hellos are sent.
5. Root cause: R2's Gi0/2 (L6) was administratively shut. IS-IS configuration is intact but hellos cannot be sent on a down interface, so the adjacency times out.
</details>

<details>
<summary>Click to view Fix</summary>

On R2: bring Gi0/2 back up.

```
R2(config)# interface GigabitEthernet0/2
R2(config-if)# no shutdown
```

Verify: `show isis neighbors` on R2 shows XR1 returning to Up state within 30 seconds.
</details>

---

### Ticket 3 — "172.20.5.0/24 Is Being Marked as a Customer Route on XR1"

The NOC reports that `172.20.5.0/24` (R4's external Lo2, which should be treated as transit) is arriving on XR1 with community 65100:400 — the community reserved for customer prefixes. The `IBGP_CUSTOMER_TAG` policy is over-matching.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show bgp ipv4 unicast 172.20.5.0/24` on XR1 shows community 65100:400 absent.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On XR1: `show bgp ipv4 unicast 172.20.5.0/24` — community 65100:400 unexpectedly present.
2. On XR1: `show rpl policy IBGP_CUSTOMER_TAG detail` — policy matches `destination in P_CUSTOMER`.
3. On XR1: `show rpl prefix-set P_CUSTOMER` — check the entry. If it shows `172.0.0.0/8 le 24` instead of `172.16.0.0/16 le 24`, the set has been widened to cover the entire 172/8 space, which includes R4's 172.20.x.x prefixes.
4. Root cause: `P_CUSTOMER` was changed from `172.16.0.0/16 le 24` (SP customer range only) to `172.0.0.0/8 le 24` (entire 172/8). This matches R4's external prefix 172.20.5.0/24, causing it to receive the customer community.
</details>

<details>
<summary>Click to view Fix</summary>

On XR1: restore `P_CUSTOMER` to the correct, narrower range.

```
RP/0/0/CPU0:XR1# conf t
RP/0/0/CPU0:XR1(config)# prefix-set P_CUSTOMER
RP/0/0/CPU0:XR1(config-pfx)#   172.16.0.0/16 le 24
RP/0/0/CPU0:XR1(config-pfx)# end-set
RP/0/0/CPU0:XR1(config)# commit
```

Verify: `show bgp ipv4 unicast 172.20.5.0/24` on XR1 — community 65100:400 absent. `show rpl prefix-set P_CUSTOMER` shows `172.16.0.0/16 le 24`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R2: IS-IS L2 adjacency with XR1 (10.1.25.5) Up on Gi0/2
- [ ] R3: IS-IS L2 adjacency with XR2 (10.1.36.6) Up on Gi0/3
- [ ] XR1: IS-IS adjacencies with R2 and XR2 both Up
- [ ] XR2: IS-IS adjacencies with R3 and XR1 both Up
- [ ] XR1: iBGP full-mesh — four neighbors (10.0.0.1/2/3/6) all Established
- [ ] XR1: `show bgp ipv4 unicast` shows 172.20.4.0/24 with local-preference 150
- [ ] XR1: `show rpl prefix-set P_CUSTOMER references` lists at least two policies
- [ ] XR1: `show rpl policy EBGP_IN detail` expands both `apply` call sites inline
- [ ] XR1: `show rpl policy CLASSIFY_PREFIXES detail` shows two parameterized instantiations
- [ ] Task 4 drop-propagation test completed — BGP table emptied and then restored

### Troubleshooting

- [ ] Ticket 1 diagnosed (IBGP_IN_BROKEN missing `pass`) and resolved — BGP table repopulated
- [ ] Ticket 2 diagnosed (R2 Gi0/2 administratively down) and resolved — XR1 IS-IS adjacency restored
- [ ] Ticket 3 diagnosed (P_CUSTOMER too broad) and resolved — 172.20.5.0/24 no longer tagged as customer

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error or node not found | All scripts |
| 4 | Pre-flight check failed — run `apply_solution.py` first | Inject scripts only |
