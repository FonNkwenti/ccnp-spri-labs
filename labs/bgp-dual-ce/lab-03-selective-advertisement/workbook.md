# Lab 03 — Outbound Policy and Selective Prefix Advertisement

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

**Exam Objectives:** 1.5.d (Multihoming) and 1.5.a (BGP path attributes) — 300-510

Lab-02 closed the loop on inbound traffic engineering with AS-path prepending, giving the
customer deterministic control over which ISP carries the bulk of return traffic. Two more
levers belong to the same toolbox and complete the dual-CE outbound-policy story: the
**LOCAL_PREF** attribute (which controls *outbound* path selection within the customer's
own AS) and **selective prefix advertisement** (which carves a single aggregate into
per-ISP more-specifics so each upstream owns a distinct longest-match path).

This lab applies both. After lab-03 the customer has a primary/backup default route via
each ISP whose preference is set by LOCAL_PREF, and the single 192.168.1.0/24 aggregate is
split into two /25 advertisements that pin half the address space to each upstream as the
preferred entry path.

---

### LOCAL_PREF — The Outbound Steering Attribute

`LOCAL_PREF` (attribute 5) is BGP's per-prefix outbound preference. It is the **second**
step of the decision process (right after weight) and is propagated freely between iBGP
peers. Higher LP wins. An eBGP neighbor that wants its customer to prefer one of two paths
inbound advertises the same prefix down both paths and lets the customer's CEs set
LOCAL_PREF higher on the preferred one — the LP setting is then carried across the
customer's iBGP mesh and every router in AS 65001 makes the same outbound decision.

LOCAL_PREF is **not** an inbound steering tool the way prepending is. AS-path prepend
makes external networks prefer one path *into* AS 65001. LOCAL_PREF makes routers *inside*
AS 65001 prefer one path *out*. The two attributes solve mirror-image problems and a
production dual-CE design uses both.

> **Exam tip:** When you see "primary path inbound" think AS-path prepend on the **backup**
> CE's outbound. When you see "primary path outbound" think LOCAL_PREF higher on the
> **primary** CE's inbound. Different attributes, different directions.

---

### Why a Locally-Originated Prefix Cannot Demonstrate LOCAL_PREF

LOCAL_PREF only matters for prefixes a router has more than one BGP path to. The customer
prefix 192.168.1.0/24 is **locally originated** on both R1 (via Lo1) and R2 (via Null0
static + `network` statement). Locally-originated paths sit at decision-process step 3
("locally-originated wins") — that step fires *before* AS-path length and even before the
eBGP-vs-iBGP tiebreaker. Setting LOCAL_PREF on an inbound advertisement of the customer's
own prefix changes nothing because R1 and R2 each prefer their own local origination of
that prefix anyway, regardless of any LP attached to the iBGP-learned copy from the other
CE.

The right vehicle for observing LOCAL_PREF in this topology is a prefix that:

1. Is **not** locally originated by either R1 or R2.
2. Is learned from **both** ISPs so each CE has competing eBGP and iBGP paths.

The default route 0.0.0.0/0 fits both criteria. R3 originates a default toward R1; R4
originates a default toward R2. R1 then has two paths to 0.0.0.0/0 — eBGP from R3 and
iBGP from R2 (which itself learned it eBGP from R4). LOCAL_PREF on R1's inbound from R3
now decides R1's egress for the default. Mirror on R2.

---

### Selective Prefix Advertisement

A multihomed customer that announces only an aggregate (`192.168.1.0/24` here) is at the
mercy of the upstream ASes' best-path tiebreakers for the inbound split of any address
inside that aggregate. AS-path prepending biases the *whole* aggregate toward one ISP but
leaves no per-subnet control.

Selective advertisement carves the aggregate into more-specific subnets and originates
each more-specific from a different CE. ISP-A receives `192.168.1.0/24` (aggregate) and
`192.168.1.0/25` (the lower half) from R1. ISP-B receives `192.168.1.0/24` (aggregate)
and `192.168.1.128/25` (the upper half) from R2. Any external router selecting a path to,
say, `192.168.1.50` will pick the longest match — the /25 that R1 originated — and enter
the AS via ISP-A. A path to `192.168.1.200` matches `192.168.1.128/25` from R2 and enters
via ISP-B.

The aggregate stays in both advertisements as a backup. If the /25 path from one CE
disappears (link down, route-map mistake, prefix withdrawn), the other ISP's view of the
aggregate is the fallback for the half that lost its longest-match.

---

### Originating a /25 — Two Configuration Paths

A `network 192.168.1.0 mask 255.255.255.128` statement in BGP only injects the prefix into
the BGP table if the **exact** prefix exists in the IP routing table at the moment BGP
checks. Two ways to make that true:

1. **Null0 discard route:** `ip route 192.168.1.0 255.255.255.128 Null0`. The router
   installs the /25 in its RIB pointing at Null0; BGP sees an exact-match RIB entry and
   originates. Traffic to the /25 that arrives at the originating router is dropped at
   Null0, but in this lab the originating CE also has the more-specific Lo1
   (`192.168.1.1/24` covers the /25 already as a connected route — the static is redundant
   from a forwarding standpoint and exists purely as the BGP origination hook).
2. **Aggregate-address with summary-only:** This lab does **not** use `aggregate-address`
   because the aggregate is already originated by `network 192.168.1.0 mask 255.255.255.0`
   plus a Null0 static, which is the lab-01/02 mechanism. Adding aggregate-address machinery
   on top would conflict.

The Null0-static-plus-network pattern is the standard technique and is what this lab uses.

---

### Tightening the Egress Filter

Lab-01's `TRANSIT_PREVENT` prefix-list permitted `192.168.1.0/24 le 32` — anything at or
below the /24 was free to leave the CE. With selective advertisement that is too permissive:
R1 should send the /24 aggregate and the /25-low only, **not** the /25-high (which belongs
to R2's egress). Likewise R2 should send the /24 and the /25-high but not the /25-low.

The fix is to replace the `le 32` clause with explicit per-prefix permits:

- R1's `TRANSIT_PREVENT`: permit `192.168.1.0/24` and `192.168.1.0/25`
- R2's `TRANSIT_PREVENT`: permit `192.168.1.0/24` and `192.168.1.128/25`

The route-map structure (`TRANSIT_PREVENT_OUT permit 10` with `match` and, on R2, `set
as-path prepend`) is unchanged. Only the prefix-list entries are tightened.

---

### Skills This Lab Develops

| Skill | Description |
|---|---|
| LOCAL_PREF inbound policy | `set local-preference 200` on a route-map applied inbound on an eBGP neighbor |
| Default-route origination | `ip route 0.0.0.0 0.0.0.0 Null0` plus `network 0.0.0.0` to inject a default into BGP |
| Selective advertisement | Originating a /25 alongside an aggregate /24 from a different CE |
| Tightening egress prefix-lists | Replacing `le 32` with explicit per-prefix permits to restrict per-CE egress |
| Designing an LP observability path | Recognizing why locally-originated prefixes hide LP and engineering a shared prefix to expose it |
| Reading the BGP decision-process order | Distinguishing weight, LP, locally-originated, AS-path, origin, MED, eBGP-vs-iBGP, IGP cost, router-id |

---

## 2. Topology & Scenario

**Scenario:** Lab-02's prepending design works — external traffic now favors ISP-A as the
primary inbound path. The customer's NOC is now turning attention to **outbound**: today
each CE picks its own ISP for any destination outside AS 65001, with no coordination
between R1 and R2 about which is preferred when both have a path. The team wants ISP-A as
the primary outbound path too, with ISP-B as backup, and they want this preference encoded
once and propagated automatically through iBGP.

A second, separate concern from the customer-services side: certain hosts on
`192.168.1.0/25` should be reached via ISP-A as their primary entry point, and hosts on
`192.168.1.128/25` should be reached via ISP-B. This cannot be expressed by a single /24
advertisement and prepending; it requires per-half longest-match advertisements from
distinct CEs.

You will configure LOCAL_PREF=200 inbound on both R1 (from R3) and R2 (from R4), originate
a default route from each ISP edge so LP is observable, originate /25 more-specifics from
each CE, and tighten the egress filter so each CE sends only its own /25.

```
       AS 65100 (ISP-A)              AS 65001 (Customer)              AS 65200 (ISP-B)
   ┌───────────────────┐    ┌─────────────────────────────┐    ┌───────────────────┐
   │   ┌────┐  iBGP    │    │  ┌────┐    iBGP    ┌────┐   │    │   iBGP   ┌────┐  │
   │   │ R5 ├──────────┤    ├──┤ R1 ├────────────┤ R2 ├───┤    ├──────────┤ R6 │  │
   │   │Lo1=│  L4      │ L1 │  │CE1 │     L3     │CE2 │ L2│    │  L5      │Lo1=│  │
   │   │.100│   ┌────┐ │    │  │Lo1=│            │    │   │    │  ┌────┐  │.200│  │
   │   │.2.0│   │ R3 ├─┤    ├──┤.168│            │    │   ├────┤  │ R4 │  │.2.0│  │
   │   │/24 │   │PE-A│ │    │  │.1.0│            │Null│   │    │  │PE-B│  │/24 │  │
   │   └────┘   │Lo1=│ │    │  │/24 │            │.1.0│   │    │  │Lo1=│  └────┘  │
   │            │.100│ │    │  │.1.0│            │/24 │   │    │  │.200│          │
   │            │.1.0│ │    │  │/25 │            │.128│   │    │  │.1.0│          │
   │            │/24 │ │    │  │Null│            │/25 │   │    │  │/24 │          │
   │            │+def│ │    │  └────┘            └────┘   │    │  │+def│          │
   │            │ault│ │    │   LP_FROM_R3        LP_FROM_R4   │  │ault│          │
   │            └────┘ │    │   (in, set 200)     (in, set 200)│  └────┘          │
   │                   │    │   TRANSIT_PREV_OUT  TRANSIT_PREV_OUT                │
   │                   │    │   (/24 + /25-low)   (/24 + /25-high                 │
   │                   │    │                      + prepend ×2)                  │
   └───────────────────┘    └─────────────────────────────┘    └──────────────────┘
```

**Key relationships for lab-03:**

- R3 and R4 each originate a default route (`0.0.0.0/0`) toward the customer. This is the
  shared prefix that makes LP observable; the customer-originated /24 and /25s would not
  expose LP because they are locally originated on the CEs.
- R1 originates `192.168.1.0/25` (Null0) in addition to the /24; R2 originates
  `192.168.1.128/25` (Null0) in addition to the /24. Both /25s reach the iBGP peer over
  the L3 link; only the local /25 leaves on each eBGP egress.
- Each CE's `TRANSIT_PREVENT` prefix-list is tightened to permit only the /24 plus its
  own /25. R2's route-map still adds `set as-path prepend 65001 65001` (lab-02 work
  preserved); the prepend now also applies to the /25-high on R2's egress.
- LOCAL_PREF=200 is set inbound on each CE's eBGP from its directly-attached PE. The LP
  attribute crosses iBGP so R1 sees R2's LP=200 on the default route from ISP-B and vice
  versa. Each CE still picks its own ISP for default (eBGP-over-iBGP at LP-tie) until that
  ISP's eBGP fails — then the iBGP-carried LP=200 from the surviving CE wins.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer CE1 (AS 65001) — originates /24 + 192.168.1.0/25 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Customer CE2 (AS 65001) — originates /24 + 192.168.1.128/25 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | ISP-A edge (AS 65100) — originates default toward customer | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | ISP-B edge (AS 65200) — originates default toward customer | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | ISP-A internal (AS 65100) — unchanged from lab-02 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | ISP-B internal (AS 65200) — unchanged from lab-02 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### No new physical links or loopbacks vs. lab-02

The lab-03 changes are entirely in policy and originated prefixes. Cabling, IP addressing,
and loopback inventory are identical to lab-02.

### Advertised Prefixes (after lab-03 policy applied)

| Source | Prefix | Reaches | Notes |
|---|---|---|---|
| R1 (Lo1, network) | 192.168.1.0/24 | R3 (eBGP), R2 (iBGP) | Aggregate, unchanged from lab-02 |
| R1 (Null0, network) | **192.168.1.0/25** | R3 (eBGP), R2 (iBGP) | New in lab-03 |
| R2 (Null0, network) | 192.168.1.0/24 | R4 (eBGP), R1 (iBGP) | Aggregate, unchanged; AS-path prepended ×2 on R4 |
| R2 (Null0, network) | **192.168.1.128/25** | R4 (eBGP), R1 (iBGP) | New in lab-03; AS-path prepended ×2 on R4 |
| R3 (network) | **0.0.0.0/0** | R1 (eBGP), R5 (iBGP) | New in lab-03 — exposes LP |
| R3 (Lo1) | 10.100.1.0/24 | unchanged from lab-02 | |
| R4 (network) | **0.0.0.0/0** | R2 (eBGP), R6 (iBGP) | New in lab-03 — exposes LP |
| R4 (Lo1) | 10.200.1.0/24 | unchanged from lab-02 | |
| R5 (Lo1) | 10.100.2.0/24 | unchanged from lab-02 | |
| R6 (Lo1) | 10.200.2.0/24 | unchanged from lab-02 | |

> The /25 advertisements inherit lab-02's prepend on R2's egress to R4. This is
> intentional — the /25-high entering ISP-B then has AS-path `65001 65001 65001` on R4
> while the /25-low entering ISP-A has `65001` on R3. Combined with the longest-match
> rule, every external router prefers the /25 path that matches the destination half
> *and* avoids the prepended ISP for the aggregate.

---

## 4. Base Configuration

The starting point is **the solution state of lab-02** — both ISPs receiving the customer
prefix (with R4 seeing the prepended copy), R5 and R6 active inside their ISPs, all iBGP
sessions Established with `next-hop-self`. No LP, no /25 origination, no default-route
origination.

**IS pre-loaded:**
- All lab-02 solution work (R1-R6 BGP, transit-prevent + prepend, R5/R6 origination)
- `TRANSIT_PREVENT` on R1 and R2 still has the lab-01/02 form: `permit 192.168.1.0/24 le 32`

**IS NOT pre-loaded** (student configures this):
- `route-map LOCAL_PREF_FROM_R3 permit 10` with `set local-preference 200` on R1, applied
  inbound on neighbor 10.1.13.2
- `route-map LOCAL_PREF_FROM_R4 permit 10` with `set local-preference 200` on R2, applied
  inbound on neighbor 10.1.24.2
- `ip route 0.0.0.0 0.0.0.0 Null0` and `network 0.0.0.0` under address-family ipv4 on R3
- Mirror default-route origination on R4
- `ip route 192.168.1.0 255.255.255.128 Null0` and `network 192.168.1.0 mask
  255.255.255.128` on R1
- `ip route 192.168.1.128 255.255.255.128 Null0` and `network 192.168.1.128 mask
  255.255.255.128` on R2
- Tightened `TRANSIT_PREVENT` prefix-lists on both CEs (per-CE /24 + own /25 only)
- Inbound and outbound soft refreshes after the route-map changes

---

## 5. Lab Challenge: Core Implementation

### Task 1: Originate a Default Route from R3 and R4

Add a discard route for 0.0.0.0/0 toward Null0 on R3, and add `network 0.0.0.0` under
address-family ipv4. Mirror on R4. After this step R1's BGP table will contain a default
from R3 (eBGP) and from R2 (iBGP — R2 learned it eBGP from R4 and re-advertised over iBGP
with next-hop-self). R2's BGP table will be the mirror.

**Verification:** `show ip bgp 0.0.0.0` on R1 lists two paths — eBGP via 10.1.13.2 and
iBGP via 10.0.0.2. The eBGP path is best (eBGP-over-iBGP at LP-tie before lab work).
Default localpref on both paths is 100. Same picture on R2 with the ASes swapped.

---

### Task 2: Apply LOCAL_PREF Inbound on Each CE

On R1, create `route-map LOCAL_PREF_FROM_R3 permit 10` with `set local-preference 200` and
apply it inbound on neighbor 10.1.13.2 under address-family ipv4. Trigger an inbound soft
refresh on the eBGP session so R1 re-evaluates the default with the new policy.

Mirror on R2 with `LOCAL_PREF_FROM_R4` on neighbor 10.1.24.2.

**Verification:** `show ip bgp 0.0.0.0` on R1 — the eBGP path from 10.1.13.2 now shows
`localpref 200`. The iBGP path from R2 also shows `localpref 200` (R2 set LP=200 on its
inbound from R4 and propagated it across iBGP). LP is now equal on both R1's paths;
eBGP-over-iBGP still selects R3 as best on R1. Mirror on R2.

---

### Task 3: Originate the /25 More-Specifics

On R1 add `ip route 192.168.1.0 255.255.255.128 Null0` and `network 192.168.1.0 mask
255.255.255.128` under address-family ipv4. On R2 add the symmetric statements for
`192.168.1.128/25`.

**Verification:** `show ip bgp` on R1 lists `192.168.1.0/24` (locally originated, weight
32768) and `192.168.1.0/25` (locally originated, weight 32768). R1's iBGP-learned copy of
`192.168.1.128/25` from R2 is also present (next-hop 10.0.0.2, internal). Mirror on R2 for
its own /25-high plus iBGP-learned /25-low. R3 still has only the prefixes it had before
this task, because the egress filter on R1 has not yet been adjusted to permit the /25.

---

### Task 4: Tighten the Egress Filter on Both CEs

On R1, replace the lab-01/02 prefix-list:

```
no ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24
ip prefix-list TRANSIT_PREVENT seq 10 permit 192.168.1.0/25
```

Mirror on R2 with `192.168.1.0/24` and `192.168.1.128/25`.

Outbound soft refresh on each CE's eBGP toward its respective ISP.

**Verification:** `show ip bgp` on R3 shows two customer prefixes: `192.168.1.0/24` and
`192.168.1.0/25`, both with AS-path `65001`. `show ip bgp` on R4 shows `192.168.1.0/24`
and `192.168.1.128/25`, both with AS-path `65001 65001 65001`. Crucially, R3 does **not**
have `192.168.1.128/25` and R4 does **not** have `192.168.1.0/25` — the per-CE filters
strip each CE's egress to only the /24 and its own /25.

---

### Task 5: Confirm LP Propagation and Failover Behavior

Look at how LP behaves end to end:

- On R1 and R2, the local CE's eBGP path to 0.0.0.0/0 is best (LP=200, eBGP-over-iBGP).
  The iBGP-learned default from the other CE also carries LP=200, so failover is
  preference-preserving — when R1's eBGP to R3 drops, R1's only remaining default is the
  iBGP path from R2, with LP=200 unchanged.
- Optional: shut R1's Gi0/0 (eBGP to R3). Verify R1's default flips to the iBGP path via
  R2. `no shut` Gi0/0 to restore.
- On R5 and R6, the customer prefixes are now received as `192.168.1.0/24` plus a /25.
  R5 sees `192.168.1.0/25` (AS-path `65001`); R6 sees `192.168.1.128/25` (AS-path `65001
  65001 65001`). External routers seeing both /25s pick the longest match for any
  destination inside 192.168.1.0/24 — half via ISP-A, half via ISP-B.

**Verification:** Per the bullets above. The completion checklist in Section 10 enumerates
the specific commands and expected outputs.

---

## 6. Verification & Analysis

### LOCAL_PREF on the Default Route

```
R1# show ip bgp 0.0.0.0
BGP routing table entry for 0.0.0.0/0, version 7
Paths: (2 available, best #1, table default)
  Refresh Epoch 1
  65100                                             ! ← from R3 via eBGP
    10.1.13.2 from 10.1.13.2 (10.0.0.3)
      Origin IGP, metric 0, localpref 200, valid, external, best
  Refresh Epoch 1
  65200                                             ! ← from R2 via iBGP (R2 learned from R4)
    10.0.0.2 (metric 0) from 10.0.0.2 (10.0.0.2)
      Origin IGP, metric 0, localpref 200, valid, internal
```

Both paths now carry LP=200. The local eBGP path remains best because eBGP-over-iBGP fires
later in the decision process than LP. The point of LP=200 here is **failover**: if the
eBGP session to R3 drops, the iBGP-learned path is the only one left, and it still has
LP=200 to defend against any other lower-LP default that might arrive from a third source.

### Selective Advertisement on the Receiver Side

```
R3# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 0.0.0.0          0.0.0.0                  0         32768 i
*> 10.100.1.0/24    0.0.0.0                  0         32768 i
*> 192.168.1.0/24   10.1.13.1                0             0 65001 i      ! ← aggregate
*> 192.168.1.0/25   10.1.13.1                0             0 65001 i      ! ← /25-low only
```

```
R4# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 0.0.0.0          0.0.0.0                  0         32768 i
*> 10.200.1.0/24    0.0.0.0                  0         32768 i
*> 192.168.1.0/24   10.1.24.1                0             0 65001 65001 65001 i   ! ← aggregate, prepended
*> 192.168.1.128/25 10.1.24.1                0             0 65001 65001 65001 i   ! ← /25-high only, prepended
```

R3 has `192.168.1.0/25` but **not** `192.168.1.128/25`. R4 has `192.168.1.128/25` but
**not** `192.168.1.0/25`. The per-CE egress filter is doing its job.

### iBGP Carries Both /25s Across the CE-CE Link

```
R1# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 0.0.0.0          10.1.13.2                0    200      0 65100 i
* i                 10.0.0.2                 0    200      0 65200 i
*> 192.168.1.0/24   0.0.0.0                  0         32768 i
*> 192.168.1.0/25   0.0.0.0                  0         32768 i
* i192.168.1.128/25 10.0.0.2                 0    100      0 i        ! ← from R2 over iBGP
```

R1's iBGP-learned `192.168.1.128/25` is present in the BGP table even though it is not
re-advertised back out to R3 (the egress filter blocks it). This is a desirable property
of the design — the iBGP table stays informative for show commands, and the eBGP-egress
filter is the only place where the per-CE scoping is enforced.

### Outbound Decision-Process Trace for an Internal Router

For an external router in some other AS that has paths to `192.168.1.50` via both ISP-A
and ISP-B, the decision goes:

1. Weight: equal (default 0).
2. LOCAL_PREF: irrelevant — only meaningful inside an AS.
3. Locally originated: neither path is.
4. AS-path length: via ISP-A is `65100 65001` (length 2); via ISP-B's view of the /24 is
   `65200 65001 65001 65001` (length 4); via ISP-B's view of the /25-high is
   `65200 65001 65001 65001` *but only for destinations in 192.168.1.128/25*.
5. **Longest match wins before the decision process is even consulted.** The external
   router matches `192.168.1.50` against `192.168.1.0/25` (the most-specific available
   for that destination) and selects the path via ISP-A. AS-path is then irrelevant
   because there is only one /25 candidate.

Selective advertisement is therefore a **stronger** inbound steering tool than prepending —
prepending biases best-path selection at a fixed prefix length; longest-match changes
which prefix is even being selected.

---

## 7. Verification Cheatsheet

### LOCAL_PREF Configuration Pattern

```
route-map LOCAL_PREF_FROM_R3 permit 10
 set local-preference 200

router bgp 65001
 address-family ipv4
  neighbor 10.1.13.2 route-map LOCAL_PREF_FROM_R3 in
 exit-address-family

clear ip bgp 10.1.13.2 soft in                    ! re-evaluate inbound updates
```

### Selective Advertisement Configuration Pattern

```
ip route 192.168.1.0 255.255.255.128 Null0        ! /25 origination hook

ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24
ip prefix-list TRANSIT_PREVENT seq 10 permit 192.168.1.0/25

router bgp 65001
 address-family ipv4
  network 192.168.1.0 mask 255.255.255.128
 exit-address-family

clear ip bgp 10.1.13.2 soft out
```

| Command | Purpose |
|---|---|
| `show ip bgp <prefix>` | **Detailed view.** Per-path LP and AS-path on the unlabeled first line of each path |
| `show ip bgp` | **Table view.** LP in the `LocPrf` column, AS-path in the rightmost `Path` column |
| `show ip bgp neighbors <peer> received-routes` | What this neighbor sent us (requires `soft-reconfiguration inbound`) |
| `show ip bgp neighbors <peer> routes` | What this neighbor sent us, post-inbound-policy |
| `show ip bgp neighbors <peer> advertised-routes` | What we are sending to this neighbor (post-outbound-policy) |
| `show route-map <name>` | Confirms the `set local-preference` clause is attached |
| `show ip prefix-list <name>` | Confirms the per-CE filter scope |
| `clear ip bgp <peer> soft in` | Re-runs inbound policy (LP changes need this) |
| `clear ip bgp <peer> soft out` | Re-runs outbound policy (filter / prepend changes need this) |

> **Exam tip:** LP changes need a **soft in** refresh on the eBGP session that received the
> update. Filter changes on the egress need a **soft out** on the eBGP session that sends
> the update. Wrong direction = no change observed.

### Decision-Process Order Refresher

| Step | Attribute | Direction |
|---|---|---|
| 1 | Weight | Cisco-local |
| 2 | LOCAL_PREF | Outbound steering, propagates iBGP |
| 3 | Locally-originated | Self-originated wins |
| 4 | AS-path length | Inbound steering target |
| 5 | Origin code | IGP < EGP < incomplete |
| 6 | MED | Same upstream AS only |
| 7 | eBGP over iBGP | External wins over internal |
| 8 | IGP cost to next-hop | Closer next-hop wins |
| 9 | Router-ID | Lowest wins |

LP and AS-path live on opposite sides of "locally-originated." That is why LP only matters
for prefixes the router did **not** originate, and why prepending the customer's own
prefix has no effect on the customer's own outbound decisions.

### Selective-Advertisement Pitfalls

| Symptom | Likely Cause |
|---|---|
| `network 192.168.1.0 mask 255.255.255.128` configured but the /25 is missing from the BGP table | No exact RIB match — Null0 static missing |
| LP=200 set on neighbor, but `show ip bgp 0.0.0.0` still shows LP=100 | Direction wrong (`out` instead of `in`), or `clear ip bgp <peer> soft in` not issued |
| /25-high appears on R3 (ISP-A) — leak | R1's `TRANSIT_PREVENT` was not tightened; still has `le 32` permitting all more-specifics |
| /25 in R3's BGP table but absent from R5 | R3's outbound-to-R5 policy filtered it (or, in lab-03's Ticket 2, filter is too strict — accepts only `192.168.1.0/24` exact) |
| Default route from ISP not propagating to R2 over iBGP | `no bgp default ipv4-unicast` is set, but the iBGP neighbor was activated under address-family ipv4 only — confirm the activate; otherwise check whether the local CE installed the default in BGP at all (RIB → `network 0.0.0.0` → activate sequence) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

<details>
<summary>Click to view R3 Configuration (default-route origination)</summary>

```bash
! R3
ip route 0.0.0.0 0.0.0.0 Null0

router bgp 65100
 address-family ipv4
  network 0.0.0.0
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration (default-route origination)</summary>

```bash
! R4
ip route 0.0.0.0 0.0.0.0 Null0

router bgp 65200
 address-family ipv4
  network 0.0.0.0
 exit-address-family
```
</details>

<details>
<summary>Click to view R1 Configuration (LP inbound, /25 origination, tightened filter)</summary>

```bash
! R1
ip route 192.168.1.0 255.255.255.128 Null0

no ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24
ip prefix-list TRANSIT_PREVENT seq 10 permit 192.168.1.0/25

route-map LOCAL_PREF_FROM_R3 permit 10
 set local-preference 200

router bgp 65001
 address-family ipv4
  network 192.168.1.0 mask 255.255.255.128
  neighbor 10.1.13.2 route-map LOCAL_PREF_FROM_R3 in
 exit-address-family

clear ip bgp 10.1.13.2 soft in
clear ip bgp 10.1.13.2 soft out
```
</details>

<details>
<summary>Click to view R2 Configuration (LP inbound, /25 origination, tightened filter)</summary>

```bash
! R2
ip route 192.168.1.128 255.255.255.128 Null0

no ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24
ip prefix-list TRANSIT_PREVENT seq 10 permit 192.168.1.128/25

route-map LOCAL_PREF_FROM_R4 permit 10
 set local-preference 200

router bgp 65001
 address-family ipv4
  network 192.168.1.128 mask 255.255.255.128
  neighbor 10.1.24.2 route-map LOCAL_PREF_FROM_R4 in
 exit-address-family

clear ip bgp 10.1.24.2 soft in
clear ip bgp 10.1.24.2 soft out
```

R2's existing `TRANSIT_PREVENT_OUT` route-map (with `set as-path prepend 65001 65001`)
is unchanged — the prepend continues to apply to both the /24 and the /25-high.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R1 — LP applied inbound, /25 originated
show ip bgp 0.0.0.0                                  ! both paths LP=200
show ip bgp                                          ! /24 + /25-low locally; /25-high via iBGP

! On R3 — receives /24 + /25-low from R1, plus its own default
show ip bgp                                          ! check 192.168.1.0/24 and 192.168.1.0/25; no /25-high
show ip bgp 192.168.1.0/25                           ! AS-path 65001 (length 1)

! On R4 — receives /24 + /25-high from R2 (prepended); no /25-low
show ip bgp
show ip bgp 192.168.1.128/25                         ! AS-path 65001 65001 65001 (length 3)

! On R5 / R6 — internal hosts inherit the per-half view
show ip bgp 192.168.1.0/25                           ! R5: present, AS-path 65001
show ip bgp 192.168.1.128/25                         ! R6: present, AS-path 65001 65001 65001
```
</details>

---

## 9. Troubleshooting Scenarios

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to lab-02 solution + lab-03 baseline
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # bring lab to lab-03 solution
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — LOCAL_PREF Direction Wrong on R1

The customer's BGP team applied LOCAL_PREF=200 on R1 to make ISP-A the primary outbound
default. After deployment, traffic measurements show R1 is sending its default-bound
traffic out to **ISP-B** (via R2 over iBGP) instead of directly to ISP-A. The route-map
exists, the prefix-list exists, the eBGP session is up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 0.0.0.0` on R1 shows the eBGP path from 10.1.13.2 with
`localpref 200` and the `best` flag.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 0.0.0.0` on R1 — eBGP path from R3 has `localpref 100`, iBGP path from
   R2 has `localpref 200`. R2's path wins.
2. `show running-config | section router bgp` on R1 reveals
   `neighbor 10.1.13.2 route-map LOCAL_PREF_FROM_R3 out` instead of `... in`. The policy
   is being applied as the **outbound** policy (which sets LP on advertisements *to* R3,
   irrelevant for inbound steering — and the eBGP neighbor strips LP across the AS
   boundary anyway).
3. The mirror still works on R2 because R2's policy is correctly bound `in`. R2 receives
   the default from R4 with LP=200, propagates it to R1 with LP=200 over iBGP. R1's eBGP
   path has the default LP=100. iBGP path wins on R1.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
router bgp 65001
 address-family ipv4
  no neighbor 10.1.13.2 route-map LOCAL_PREF_FROM_R3 out
  neighbor 10.1.13.2 route-map LOCAL_PREF_FROM_R3 in
 exit-address-family

clear ip bgp 10.1.13.2 soft in
```

LOCAL_PREF must be set on **inbound** updates on the eBGP neighbor whose path you want to
prefer. Outbound LP is meaningful only on iBGP advertisements (and even there, it is the
*sender's* `set local-preference` that propagates — not a receiver-side handle).
</details>

---

### Ticket 2 — /25 Visible at R3 But Absent From R5

ISP-A's NOC reports that R5's BGP table is missing `192.168.1.0/25`. R3 has the /25 in its
BGP table — it is being received from R1 normally over eBGP. But R5 only sees the /24
aggregate. The iBGP session R3↔R5 is Established and was healthy in lab-02.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 192.168.1.0/25` on R5 returns the prefix with next-hop
10.0.0.3, AS-path `65001`, and best-path flag.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 192.168.1.0/25` on R5 — `% Network not in table`.
2. `show ip bgp 192.168.1.0/25` on R3 — present, AS-path `65001`, valid/external/best.
   R3 has it; R5 does not.
3. `show ip bgp neighbors 10.0.0.5 advertised-routes` on R3 — only `192.168.1.0/24` and
   `0.0.0.0/0` are listed. The /25 is being suppressed on advertisement.
4. `show running-config | section router bgp` on R3 reveals
   `neighbor 10.0.0.5 prefix-list ONLY_AGGREGATE out`. The prefix-list permits
   `192.168.1.0/24` (exact) but not the /25, and it has no `permit any` at the bottom.
5. `show ip prefix-list ONLY_AGGREGATE` confirms the scope is too tight — exact-match /24
   only, no /25, no default route.
</details>

<details>
<summary>Click to view Fix</summary>

The cleanest fix is to remove the policy entirely — R3 has no business filtering iBGP
traffic to its internal peer, and the lab-02 solution had no such filter. R5 should
receive everything R3 has.

```bash
! R3
router bgp 65100
 address-family ipv4
  no neighbor 10.0.0.5 prefix-list ONLY_AGGREGATE out
 exit-address-family

clear ip bgp 10.0.0.5 soft out
```

After the fix, R5's BGP table contains `192.168.1.0/24`, `192.168.1.0/25`, `0.0.0.0/0`,
and the ISP-A internal prefixes. R5 can now select `192.168.1.0/25` as best for any
destination in the lower-half of the customer's address space, and outbound traffic from
R5 to those destinations follows the longest-match path through ISP-A → CE1.
</details>

---

### Ticket 3 — /25-High Missing From R4

The customer-services team reports that ISP-B is no longer receiving `192.168.1.128/25`.
R4's BGP table contains the aggregate `192.168.1.0/24` (with the lab-02 prepend) but the
/25-high is gone. The eBGP session R2↔R4 is Established. R2's `TRANSIT_PREVENT` prefix-list
permits both the /24 and the /25-high. R2 is configured to originate the /25-high.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 192.168.1.128/25` on R4 returns the prefix with AS-path
`65001 65001 65001`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 192.168.1.128/25` on R4 — `% Network not in table`.
2. `show ip bgp 192.168.1.128/25` on R2 — `% Network not in table`. The prefix is missing
   on R2 itself, not just on the advertisement.
3. `show ip bgp` on R2 lists `192.168.1.0/24` and `192.168.1.0/25` (the latter learned
   from R1 over iBGP) but no `192.168.1.128/25` originated locally.
4. `show running-config | section router bgp` on R2 confirms the
   `network 192.168.1.128 mask 255.255.255.128` statement is present under
   address-family ipv4. The configuration is right, so why isn't BGP installing the /25?
5. `show ip route 192.168.1.128` on R2 — `% Subnet not in table`. The exact /25 prefix
   is not in the RIB. The Null0 static `ip route 192.168.1.128 255.255.255.128 Null0`
   is missing. BGP `network` requires the **exact** prefix in the RIB before it will
   inject — the /24 covering route does not satisfy this.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
ip route 192.168.1.128 255.255.255.128 Null0

clear ip bgp 10.1.24.2 soft out
```

After the static is restored, BGP sees `192.168.1.128/25` in the RIB, the `network`
statement injects it into the BGP table, and R2 advertises it to R4 (where the per-CE
filter on R2's egress permits it and the prepend ×2 applies). R6 inherits it across the
ISP-B iBGP mesh.

This pattern — `network` statement without a matching RIB entry — is one of the most
common origination failures in production BGP. The fix is always to provide a RIB source:
a static, an IGP-learned route, or `aggregate-address` machinery.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R3 originates 0.0.0.0/0 (Null0 static + `network 0.0.0.0` in AF)
- [ ] R4 originates 0.0.0.0/0 (Null0 static + `network 0.0.0.0` in AF)
- [ ] R1 has `route-map LOCAL_PREF_FROM_R3 permit 10` with `set local-preference 200`,
      applied **inbound** on neighbor 10.1.13.2
- [ ] R2 has `route-map LOCAL_PREF_FROM_R4 permit 10` with `set local-preference 200`,
      applied **inbound** on neighbor 10.1.24.2
- [ ] `show ip bgp 0.0.0.0` on R1 — eBGP path LP=200, iBGP path LP=200
- [ ] `show ip bgp 0.0.0.0` on R2 — eBGP path LP=200, iBGP path LP=200
- [ ] R1 originates 192.168.1.0/25 (Null0 static + `network ... mask 255.255.255.128`)
- [ ] R2 originates 192.168.1.128/25 (Null0 static + `network ... mask 255.255.255.128`)
- [ ] R1's `TRANSIT_PREVENT` prefix-list now permits 192.168.1.0/24 + 192.168.1.0/25 only
- [ ] R2's `TRANSIT_PREVENT` prefix-list now permits 192.168.1.0/24 + 192.168.1.128/25 only
- [ ] R3 has 192.168.1.0/24 + 192.168.1.0/25 in BGP table (no /25-high)
- [ ] R4 has 192.168.1.0/24 + 192.168.1.128/25 in BGP table, both with AS-path length 3
- [ ] R5 sees 192.168.1.0/25; R6 sees 192.168.1.128/25
- [ ] Reachability: R5 pings 192.168.1.50 (sourced Lo1) — succeeds via ISP-A
- [ ] Reachability: R6 pings 192.168.1.200 (sourced Lo1) — succeeds via ISP-B

### Troubleshooting

- [ ] Ticket 1 resolved — LP route-map direction corrected from `out` to `in` on R1
- [ ] Ticket 2 resolved — overly-tight iBGP egress filter removed on R3
- [ ] Ticket 3 resolved — Null0 static for 192.168.1.128/25 restored on R2

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
