# Lab 08: BGP Comprehensive Troubleshooting — Capstone II

**Exam:** 300-510 SPRI
**Chapter:** BGP
**Difficulty:** Advanced
**Estimated Time:** 120 minutes
**Type:** Capstone II — Troubleshooting

---

## Table of Contents

1. Lab Overview
2. Topology
3. Addressing Table
4. Prerequisites
5. Lab Challenge: Comprehensive Troubleshooting
6. Blueprint Coverage
7. Verification
8. Reference Solutions
9. Fault Tickets
10. Grading Criteria
11. Key Takeaways

---

## 1. Lab Overview

You inherit a 7-router service-provider BGP topology that was modified by a junior engineer
prior to a planned customer cut-over. The cut-over has been postponed because the network
no longer behaves the way it did during the design review.

The topology integrates every BGP feature from this chapter — eBGP/iBGP, route reflection,
multihoming with LOCAL_PREF and AS-path prepend, MD5 + TTL-security, maximum-prefix,
communities + extended communities (SoO), dynamic neighbors, route dampening, and FlowSpec.

Six concurrent faults are present. They span different devices and different fault classes.
Some symptoms appear immediately; others surface only after diagnostic traffic is generated.

**Approach:** Establish a baseline first. The solution configuration is documented below —
know what the correctly-functioning topology looks like before issuing any `no` commands.
Document each fault before fixing it.

---

## 2. Topology

```
                               AS 65100 (SP Core, OSPF area 0, R4 = RR)
                ┌───────────────────────────────────────────────────────────────┐
                │                                                               │
AS 65001        │   ┌────┐ L3   ┌────┐ L5   ┌────┐                              │
┌──────┐  L1    │   │ R2 ├──────┤ R4 ├──────┤ R5 │   L7   ┌──────┐              │
│  R1  ├────────┼───┤PE-E1│      │ RR │      │PE-W├────────┤  R6  │ AS 65002    │
│  CE  │        │   └─┬──┘      └─┬──┘      └─┬──┘        └──────┘              │
└──┬───┘  L2    │     │ L6        │ L4        │ L8                              │
   │            │   ┌─┴──┐       │           │                                  │
   └────────────┼───┤ R3 ├───────┘           │   ┌──────┐ AS 65003              │
                │   │PE-E2│                  └───┤  R7  │ FlowSpec               │
                │   └────┘                       └──────┘ originator             │
                └───────────────────────────────────────────────────────────────┘
   L8 (10.99.0.0/30 dynamic-neighbor range): R1 Gi0/2 ↔ R2 Gi0/3
```

| Zone | Devices | ASN |
|------|---------|-----|
| Customer A | R1 | 65001 |
| SP Core (East PEs) | R2, R3 | 65100 |
| SP Core (P/RR) | R4 | 65100 |
| SP Core (West PE) | R5 | 65100 |
| External SP Peer | R6 | 65002 |
| External FlowSpec Originator | R7 | 65003 |

R5 and R7 are CSR1000v (IOS-XE 17.3) for FlowSpec SAFI support; the rest are IOSv 15.9.

---

## 3. Addressing Table

| Device | Interface | Address | Role |
|--------|-----------|---------|------|
| R1 | Lo0 | 10.0.0.1/32 | Customer A router-id |
| R1 | Lo1 | 172.16.1.0/24 | Customer A advertised prefix |
| R1 | Gi0/0 | 10.1.12.1/24 | eBGP to R2 (primary) |
| R1 | Gi0/1 | 10.1.13.1/24 | eBGP to R3 (backup) |
| R1 | Gi0/2 | 10.99.0.1/30 | Dynamic-neighbor link to R2 |
| R2 | Lo0 | 10.0.0.2/32 | iBGP / OSPF router-id |
| R2 | Gi0/0 | 10.1.12.2/24 | eBGP to R1 |
| R2 | Gi0/1 | 10.1.24.2/24 | OSPF + iBGP to R4 |
| R2 | Gi0/2 | 10.1.23.2/24 | OSPF to R3 |
| R2 | Gi0/3 | 10.99.0.2/30 | Dynamic-neighbor listen |
| R3 | Lo0 | 10.0.0.3/32 | iBGP / OSPF router-id |
| R3 | Gi0/0 | 10.1.13.3/24 | eBGP to R1 |
| R3 | Gi0/1 | 10.1.34.3/24 | OSPF + iBGP to R4 |
| R3 | Gi0/2 | 10.1.23.3/24 | OSPF to R2 |
| R4 | Lo0 | 10.0.0.4/32 | RR cluster-id |
| R4 | Gi0/0 | 10.1.24.4/24 | OSPF + iBGP to R2 |
| R4 | Gi0/1 | 10.1.34.4/24 | OSPF + iBGP to R3 |
| R4 | Gi0/2 | 10.1.45.4/24 | OSPF + iBGP to R5 |
| R5 | Lo0 | 10.0.0.5/32 | iBGP / OSPF router-id |
| R5 | Gi2 | 10.1.45.5/24 | OSPF + iBGP to R4 |
| R5 | Gi3 | 10.1.56.5/24 | eBGP to R6 + FlowSpec apply |
| R5 | Gi4 | 10.1.57.5/24 | eBGP to R7 (FlowSpec SAFI) |
| R6 | Lo0 | 10.0.0.6/32 | router-id |
| R6 | Lo1 | 172.16.6.0/24 | External SP advertised prefix |
| R6 | Gi0/0 | 10.1.56.6/24 | eBGP to R5 |
| R7 | Lo0 | 10.0.0.7/32 | router-id |
| R7 | Lo1 | 172.16.7.0/24 | FlowSpec originator advertised prefix |
| R7 | Gi1 | 10.1.57.7/24 | eBGP to R5 (FlowSpec SAFI) |

---

## 4. Prerequisites

- EVE-NG lab imported and all 7 nodes started.
- Pre-broken configs loaded via `setup_lab.py`.
- Layer 2 connectivity verified — ping each adjacent interface pair before starting:

```
R1#  ping 10.1.12.2
R1#  ping 10.1.13.3
R5#  ping 10.1.56.6
R5#  ping 10.1.57.7
R4#  ping 10.0.0.2 source Lo0
R4#  ping 10.0.0.3 source Lo0
R4#  ping 10.0.0.5 source Lo0
```

All pings should succeed — the faults are in the BGP control plane, not in IP addressing,
interface state, or OSPF.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

The network is pre-broken. Your job is to find and fix every fault.

**You are NOT told how many faults exist or which devices they are on.**

Treat this as a real incident. Open a mental (or written) ticket for each symptom you observe.
Isolate root causes before applying fixes. Verify each fix before moving on.

**End-state objectives — achieve all of the following:**

1. R4 has all 3 iBGP peers (R2, R3, R5) up with non-zero received prefix counts.
2. R5 receives 172.16.1.0/24 with `LOCAL_PREF 200`, community `65100:100`, and SoO `65001:1`.
3. R5↔R6 eBGP session is up and stable; `show ip bgp neighbors 10.1.56.6` shows MD5 active.
4. R5↔R7 eBGP session is up and stable; `show ip bgp summary` does not show flapping.
5. R4 (RR) and R5 see community `65100:100` on `172.16.1.0/24` — not just R2.
6. R5 receives at least one FlowSpec NLRI from R7 in `show bgp ipv4 flowspec`.
7. From R1, the path to 172.16.6.0/24 prefers AS-path via R2, not R3.
8. R2's `show ip bgp summary` shows neighbor `10.1.12.1` in `Established` (not idle, not in
   max-prefix shutdown).

**Recommended diagnostic commands:**

```
show ip bgp summary
show ip bgp 172.16.1.0/24
show ip bgp 172.16.6.0/24
show ip bgp neighbors <ip>
show ip bgp neighbors <ip> received-routes
show ip bgp neighbors <ip> advertised-routes
show ip bgp neighbors <ip> | include password|TTL|state|max
show bgp ipv4 flowspec
show bgp all neighbors <ip> | include flowspec
show ip ospf neighbor
show route-map
debug ip bgp updates
debug ip bgp <ip> events
```

---

## 6. Blueprint Coverage

| Blueprint Ref | Topic | Fault Class Exercised |
|---------------|-------|-----------------------|
| 2.2 | iBGP next-hop reachability | Missing `next-hop-self` on RR client |
| 2.3 | Multihoming / path selection | Route-map applied in wrong direction |
| 2.4 | Inter-domain security | MD5 password mismatch |
| 2.5 | Maximum-prefix safety | Excessively low max-prefix triggers session bounce |
| 2.6 | Community propagation | Missing `send-community both` on iBGP neighbor |
| 2.7 | FlowSpec SAFI negotiation | Missing `activate` under address-family ipv4 flowspec |

---

## 7. Verification

### 7.1 iBGP / RR sessions

```
R4# show ip bgp summary
```

Expected: 3 iBGP peers (10.0.0.2, 10.0.0.3, 10.0.0.5) all in `Established` with non-zero
prefix counts in the received column.

### 7.2 Customer-A primary path attributes

```
R5# show ip bgp 172.16.1.0/24
```

Expected output includes:

```
  Local-Pref: 200
  Community: 65100:100
  Extended Community: SoO:65001:1
  Originator: 10.0.0.2
  Cluster list: 10.0.0.4
```

### 7.3 R5↔R6 MD5

```
R5# show ip bgp neighbors 10.1.56.6 | include password|TTL
```

Expected: `Connection is ESTAB, Option Flags: ... password`, TTL hops 1.

### 7.4 R5↔R7 stability and FlowSpec

```
R5# show ip bgp summary | include 10.1.57
```

Expected: `Established` with non-zero uptime and stable received-prefix count for the
unicast SAFI.

```
R5# show bgp ipv4 flowspec
```

Expected: at least one NLRI matching destination 172.16.1.0/24, protocol TCP, dest-port 22.

### 7.5 R1 outbound path selection

```
R1# show ip bgp 172.16.6.0/24
```

Expected: best path is `via 10.1.12.2` (via R2 — primary), not via R3.

### 7.6 R2's eBGP to R1

```
R2# show ip bgp summary | include 10.1.12.1
```

Expected: `Established`, not stuck in max-prefix shutdown nor flapping.

---

## 8. Reference Solutions

The full clean-state configurations for all 7 devices live in `solutions/`. Run
`scripts/fault-injection/apply_solution.py --host <eve-ng-ip>` to push them. The summary
of what each device should be doing is in `topology/README.md` and `decisions.md`.

A condensed snapshot of the most-relevant correct lines per device:

```
R5  router bgp 65100
      neighbor 10.0.0.4  next-hop-self     <-- required for RR-learned paths
      address-family ipv4 flowspec
        bgp flowspec local-install interface-all
        neighbor 10.1.57.7 activate

R2  router bgp 65100
      address-family ipv4
        neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in     <-- direction = in
        neighbor 10.1.12.1 maximum-prefix 100 75 restart 5      <-- limit = 100
        neighbor 10.0.0.4 send-community both                   <-- both std + ext

R6  router bgp 65002
      neighbor 10.1.56.5 password CISCO_SP                      <-- shared key

R7  router bgp 65003
      address-family ipv4 flowspec
        neighbor 10.1.57.5 activate                             <-- AFI must be activated
```

---

## 9. Fault Tickets

Each ticket below describes only the **observed symptom**. The fault type and target device
are not labelled — that is the diagnosis. Resolve each ticket end to end.

<details>
<summary>Ticket 1 — R5 has no best paths for SP-Core-learned eBGP prefixes</summary>

**Symptom:** On R5, `show ip bgp 172.16.1.0/24` (detailed view — shows prefix attributes as labeled lines) displays the prefix learned via 10.0.0.4 (the RR) but the path is not marked best (no `>` indicator). R5 cannot reach 172.16.1.0/24. R2/R3/R4 all show the prefix as best on their side.

**Investigation starting point:**
```
R5# show ip bgp 172.16.1.0/24
R5# show ip route 10.1.12.0
R5# show ip route 10.1.13.0
```
Why is the iBGP-learned next-hop unreachable on R5 but reachable on R3/R4?

**Root cause:** When R2 advertises 172.16.1.0/24 to R4 (the RR), the next-hop is R2's eBGP
peer address 10.1.12.1 (R1's side of the L1 link). R4 reflects this to R5 unchanged
(reflection does not modify next-hop). R5 needs the next-hop to be reachable via OSPF —
but 10.1.12.0/24 is not in OSPF (only the SP-core links and loopbacks are). R5 should
have set `next-hop-self` on its iBGP session toward R4, **but it does not**, so when R4
tries to send updates back to R5 it cannot resolve. The configuration is missing
`neighbor 10.0.0.4 next-hop-self` on R5 inside `address-family ipv4 unicast`.

**Fix:**
```
R5(config)# router bgp 65100
R5(config-router)# address-family ipv4 unicast
R5(config-router-af)# neighbor 10.0.0.4 next-hop-self
```

**Verify:**
```
R5# show ip bgp 172.16.1.0/24
```
Expected: best path marked, next-hop reachable via OSPF.

</details>

<details>
<summary>Ticket 2 — R5 sees Customer-A prefix without LOCAL_PREF, community, or SoO</summary>

**Symptom:** `show ip bgp 172.16.1.0/24` on R5 (detailed view — Local-Pref, Community, and Extended Community appear as labeled lines) shows the prefix but with `Local-Pref 100` (default) — no `200`. Missing `Community: 65100:100`. Missing SoO extended community. R3 shows the same plain prefix (no LP, no community). The customer's primary-path tagging is missing entirely.

**Investigation starting point:**
```
R2# show ip bgp 172.16.1.0/24
R2# show running-config | section route-map FROM-CUST-A-PRIMARY
R2# show ip bgp neighbors 10.1.12.1 | include map
```
The route-map exists. Is it applied where you expect it?

**Root cause:** On R2, `route-map FROM-CUST-A-PRIMARY` is correctly defined (sets
`local-preference 200`, `community 65100:100 additive`, `extcommunity soo 65001:1`) but it
is applied **outbound** (`route-map FROM-CUST-A-PRIMARY out`) toward R1 instead of
**inbound** (`in`). Outbound route-maps shape what R2 advertises to R1; they do not modify
prefixes received from R1. The Customer-A prefix arrives at R2 untagged.

**Fix:**
```
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4 unicast
R2(config-router-af)# no neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY out
R2(config-router-af)# neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in
R2(config-router-af)# do clear ip bgp 10.1.12.1 soft in
```

**Verify:**
```
R5# show ip bgp 172.16.1.0/24
```
Expected: Local-Pref 200, community 65100:100, extended community SoO:65001:1.

</details>

<details>
<summary>Ticket 3 — R5↔R6 eBGP session never reaches Established</summary>

**Symptom:** `show ip bgp summary` on R5 shows neighbor 10.1.56.6 oscillating between
`Active` and `Idle`, never reaching `Established`. Console logs show `%TCP-6-BADAUTH:
Invalid MD5 digest from 10.1.56.6`. R6 logs the mirror image. ICMP between 10.1.56.5 and
10.1.56.6 succeeds.

**Investigation starting point:**
```
R5# show ip bgp neighbors 10.1.56.6 | include password|TTL|state
R6# show ip bgp neighbors 10.1.56.5 | include password|TTL|state
R6# show running-config | include neighbor 10.1.56.5
```

**Root cause:** R6's BGP config has `neighbor 10.1.56.5 password WRONG_PASS` instead of the
shared key `CISCO_SP`. R5's side has the correct password. The MD5 digests do not match,
the TCP session is rejected, and BGP never opens.

**Fix:**
```
R6(config)# router bgp 65002
R6(config-router)# no neighbor 10.1.56.5 password
R6(config-router)# neighbor 10.1.56.5 password CISCO_SP
R6(config-router)# do clear ip bgp 10.1.56.5
```

**Verify:**
```
R5# show ip bgp summary | include 10.1.56.6
R5# show ip bgp neighbors 10.1.56.6 | include password
```
Expected: `Established`, password active.

</details>

<details>
<summary>Ticket 4 — R2's eBGP session to R1 keeps bouncing every few minutes</summary>

**Symptom:** `show ip bgp summary` on R2 shows neighbor 10.1.12.1 alternating between
`Established` and `Idle (PfxCt)`. Console log on R2:
```
%BGP-4-MAXPFX: No. of prefix received from 10.1.12.1 reaches 1, max 1
%BGP-3-NOTIFICATION: sent to neighbor 10.1.12.1 ... Maximum Number of Prefixes Reached
```
After 5 minutes the session re-establishes, accepts one prefix, and shuts down again.

**Investigation starting point:**
```
R2# show ip bgp neighbors 10.1.12.1 | include max
R2# show running-config | section router bgp
```

**Root cause:** `neighbor 10.1.12.1 maximum-prefix 1 75 restart 5` sets a hard limit of
**1** prefix. R1 advertises 172.16.1.0/24 — that's the first prefix, which trips the limit
immediately. `restart 5` brings the session back after 5 minutes, but the same prefix
arrives again, so the session bounces in a loop. The intended limit is 100 (per design).

**Fix:**
```
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4 unicast
R2(config-router-af)# no neighbor 10.1.12.1 maximum-prefix 1 75 restart 5
R2(config-router-af)# neighbor 10.1.12.1 maximum-prefix 100 75 restart 5
R2(config-router-af)# do clear ip bgp 10.1.12.1
```

**Verify:**
```
R2# show ip bgp summary | include 10.1.12.1
R2# show ip bgp neighbors 10.1.12.1 | include max
```
Expected: stable `Established`, max-prefix shows `100, 75`.

</details>

<details>
<summary>Ticket 5 — R4 (RR) and R5 do not see community 65100:100 on Customer-A's prefix</summary>

**Symptom:** After fixing tickets 1–2 above, R5 still does not see the standard community
`65100:100` on `172.16.1.0/24`. The route-map applies it inbound at R2 — `show ip bgp
172.16.1.0/24` on R2 confirms the community is attached locally. But R4 and R5 receive the
prefix without the community.

**Investigation starting point:**
```
R2# show ip bgp 172.16.1.0/24
R4# show ip bgp 172.16.1.0/24
R2# show ip bgp neighbors 10.0.0.4 | include community
R2# show running-config | section router bgp
```
Communities are non-transitive across BGP unless explicitly enabled.

**Root cause:** R2's iBGP neighbor 10.0.0.4 (the RR) is missing
`neighbor 10.0.0.4 send-community both`. The community is set locally by the inbound
route-map on R2 but not propagated to the RR — and therefore not reflected to R5.

**Fix:**
```
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4 unicast
R2(config-router-af)# neighbor 10.0.0.4 send-community both
R2(config-router-af)# do clear ip bgp 10.0.0.4 soft out
```

**Verify:**
```
R4# show ip bgp 172.16.1.0/24
R5# show ip bgp 172.16.1.0/24
```
Expected: community `65100:100` and ext-community `SoO:65001:1` visible on both.

</details>

<details>
<summary>Ticket 6 — No FlowSpec NLRIs on R5; R7 shows no FlowSpec peers</summary>

**Symptom:** `show bgp ipv4 flowspec` on R5 returns no entries. R5↔R7 eBGP unicast session
is `Established` and exchanging IPv4 unicast routes normally — but the FlowSpec SAFI was
never negotiated. `show bgp all neighbors 10.1.57.5 | include flowspec` on R7 shows no
flowspec capability advertised.

**Investigation starting point:**
```
R5# show bgp ipv4 flowspec summary
R7# show bgp ipv4 flowspec summary
R7# show running-config | section router bgp
```

**Root cause:** On R7, the `address-family ipv4 flowspec` block exists but is missing the
per-neighbor activate: `neighbor 10.1.57.5 activate`. Without `activate` inside the
flowspec AFI, R7 does not negotiate the FlowSpec SAFI with R5 during OPEN. The unicast
session works because the unicast AFI is activated separately. R5's side is configured
correctly; the missing line is on R7 only.

**Fix:**
```
R7(config)# router bgp 65003
R7(config-router)# address-family ipv4 flowspec
R7(config-router-af)# neighbor 10.1.57.5 activate
R7(config-router-af)# do clear ip bgp 10.1.57.5
```

**Verify:**
```
R7# show bgp ipv4 flowspec summary
R5# show bgp ipv4 flowspec
R5# show bgp ipv4 flowspec detail | include Local install
```
Expected: FlowSpec session up; at least one NLRI matching dst 172.16.1.0/24 / TCP / port 22;
local install yes on R5.

</details>

---

## 10. Grading Criteria

| Check | Points |
|-------|--------|
| All 3 RR-client iBGP sessions Established with non-zero prefix counts | 15 |
| 172.16.1.0/24 on R5 shows LOCAL_PREF 200 + community 65100:100 + SoO 65001:1 | 20 |
| R5↔R6 session Established with MD5 active | 15 |
| R2↔R1 session stable (no max-prefix bounce loop) | 15 |
| R4 and R5 receive community 65100:100 on Customer-A's prefix | 15 |
| FlowSpec NLRI present on R5 for dst 172.16.1.0/24 / TCP / port 22 | 20 |
| **Total** | **100** |

---

## 11. Key Takeaways

- **`next-hop-self` is required wherever an eBGP-learned next-hop is not in the IGP.**
  Route reflection does not change the next-hop; the originating client must rewrite it
  before sending to the RR, otherwise downstream RR clients see an unreachable next-hop.
- **Inbound vs outbound route-map direction matters.** `in` modifies what the local router
  stores in its RIB-IN before best-path; `out` shapes what the local router advertises to
  the neighbor. Tag-on-ingress design requires `in`.
- **MD5 mismatches are TCP-layer, not BGP-layer.** The BGP session never reaches OPEN; the
  TCP socket itself is rejected. `%TCP-6-BADAUTH` is the diagnostic giveaway.
- **`maximum-prefix N restart M` will cycle the session indefinitely** when N is below the
  steady-state prefix count. The session re-establishes, immediately exceeds the limit, and
  shuts down again every M minutes.
- **`send-community both` is per-neighbor and per-direction-of-propagation.** Setting a
  community inbound from one neighbor does not automatically propagate it to other neighbors.
- **Per-AFI `activate` is required for every non-unicast SAFI.** A peer can be Established
  for IPv4 unicast yet completely inactive for FlowSpec, MVPN, EVPN, etc., if `activate` is
  missing inside that address-family block.
