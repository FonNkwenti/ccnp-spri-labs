# Lab 02 — Inbound Traffic Engineering Across Two ISPs

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

Lab-01 closed the transit leak — only the customer's own prefix now leaves AS 65001. With
that filter in place, both ISPs receive 192.168.1.0/24 with the same AS-path length
(`65001`), and external networks see a tie. BGP breaks the tie with rules that have nothing
to do with the customer's intent — router IDs, peer addresses, default IGP cost. The
practical outcome is unpredictable inbound load distribution: some traffic to the customer
prefix enters via ISP-A, some via ISP-B, and the split shifts whenever an external network's
upstream changes.

This lab takes back control. The customer designates ISP-A as the **primary** inbound path
and ISP-B as the **backup**. Because the two ISPs are in different ASes (65100 vs. 65200),
the only inbound-influence tool that crosses the AS boundary in a useful way is **AS-path
prepending**.

---

### Why MED Doesn't Help Here

`MULTI_EXIT_DISC` (MED, attribute 4) is BGP's per-prefix hint to a directly attached
neighboring AS: "of the multiple links between us, prefer the one with the lower MED."
RFC 4271 §9.1.2.2 specifies that MED is only compared between paths received from the same
neighboring AS. The dual-CE topology has two **different** neighboring ASes upstream
(65100 and 65200), so MED values set on R2's outbound advertisements to R4 are never
compared against MED values set on R1's outbound advertisements to R3 — different ASes,
different decision processes. MED is the right tool for steering inbound traffic between
two links to the **same** upstream ISP. It is the wrong tool for two **different** ISPs.

> **Exam tip:** MED across two different upstream ASes is a classic exam trap. The
> symptom — MED configured but inbound preference unchanged — points at the
> always-compare-MED knob, but the real answer is that the two ASes never compare those
> MEDs against each other. Use AS-path prepending instead.

---

### How AS-Path Prepending Steers Inbound Traffic

AS-path length is the **second** decision-process step (after weight, local-preference,
and locally-originated). When the customer prepends its own AS multiple times on the
outbound advertisement to one ISP, every external router that receives the prefix via
that ISP sees a longer AS-path than via the other ISP. Provided no other earlier
attribute breaks the tie at those external routers, the shorter-path advertisement wins
the BGP best-path selection and inbound traffic enters the customer AS via the unprepended
ISP.

Prepending uses the customer's own AS — never a neighbor's AS, and never a private AS the
customer doesn't own. Prepending with a neighbor's AS triggers BGP loop prevention at the
neighbor (the receiving router sees its own AS in the path and discards the update);
prepending with a foreign AS is a form of AS-path forgery that an alert NOC will flag.

The number of prepends is a tradeoff. One prepend is often invisible because many
backbones see paths several ASes long anyway. Three prepends are a strong signal but raise
suspicion in route-quality scoring at large transit ASes. **Two prepends is the
conventional starting point** and is what this lab uses.

---

### Why Prepend on the Backup, Not the Primary

The intuition "make the primary look better" is wrong for AS-path prepending. There is no
way to make an AS-path **shorter** than the natural length the AS contributes (one entry
per AS hop). Prepending only adds entries. The technique therefore works by making the
**backup** look worse — adding length to its advertisement so that, by elimination, the
primary becomes the shorter path.

In this lab, ISP-A is primary, so the prepend goes on R2's outbound to R4 (ISP-B). R1's
outbound to R3 (ISP-A) keeps the natural length-1 path.

---

### Where the Prepend Goes — Coalescing With the Lab-01 Filter

Lab-01 left a `route-map TRANSIT_PREVENT_OUT` on each CE wrapping the
`TRANSIT_PREVENT` prefix-list. That route-map is the right home for the prepend. Adding
`set as-path prepend 65001 65001` to the existing `permit 10` sequence on R2 means the
single outbound policy on R2's eBGP egress to R4 now does two things in one place:

1. Filters out everything except the customer prefix (lab-01 work).
2. Lengthens the AS-path on what does pass, by two entries.

The route-map name `TRANSIT_PREVENT_OUT` is no longer fully descriptive — the policy
attached to that name has grown beyond transit prevention. The decision to **keep the name**
rather than rename to `EBGP_OUT_R4` is documented in `decisions.md`: continuity with the
lab-01 student work outweighs naming purity. Production deployments often face the same
tradeoff and resolve it the same way.

R1's `TRANSIT_PREVENT_OUT` on the eBGP session to R3 stays untouched — only filter, no
prepend. The asymmetry is the entire point.

---

### What the Topology Adds: R5 and R6

Lab-00 and lab-01 had four nodes — R1, R2 (customer) and R3, R4 (ISP edge). Inbound TE
verification needs at least one external host per ISP whose own decision process depends
on what its ISP edge advertises. **R5** is added inside ISP-A as an iBGP peer of R3, and
**R6** is added inside ISP-B as an iBGP peer of R4. Each of R5 and R6 originates an
internal prefix (`10.100.2.0/24` and `10.200.2.0/24` respectively) that the labs from this
point forward use as "external customer" representatives.

For the inbound TE test to work, R5 must learn 192.168.1.0/24 from R3 over iBGP with a
reachable next-hop and the customer-AS path attached. The standard tool is `next-hop-self`
on R3's iBGP advertisement to R5 — without it, R5 receives the prefix with next-hop
10.1.13.1 (R1's eBGP-facing address), which R5 has no route to inside ISP-A. R3 must also
re-advertise the prefix (eBGP-learned routes are advertised to iBGP peers by default —
nothing extra is needed there beyond `next-hop-self` and an `activate`). The same setup
mirrors on R4 → R6.

The link between the lab-01 work and the new R5/R6 hosts is what makes this lab
**progressive**: the inbound TE verification is "where does R5 send traffic to
192.168.1.0/24" and "where does R6 send traffic to 192.168.1.0/24." If both R5 and R6
choose the route via R3, ISP-A is the inbound primary. If R5 picks R3 but R6 picks R4
(via the cross-ISP path), the prepend isn't doing its job.

---

### Skills This Lab Develops

| Skill | Description |
|---|---|
| AS-path prepending | Adding `set as-path prepend <self-AS> <self-AS>` to a route-map and applying outbound on eBGP |
| Choosing prepend count | Two prepends as the conventional starting point; tradeoffs of one vs. three |
| Inbound TE verification | Confirming AS-path length at the receiving ISP and tracing best-path selection at remote internal hosts |
| MED-vs-prepend reasoning | Recognizing why MED does not work across two different upstream ASes |
| `next-hop-self` on iBGP edge | Making eBGP-learned next-hops reachable inside the ISP for iBGP peers |
| Coalescing policy on a route-map | Adding `set` clauses to an existing structure rather than creating a parallel route-map |

---

## 2. Topology & Scenario

**Scenario:** With the transit leak from lab-01 closed, the customer's BGP team has begun
measuring inbound traffic. The flow is roughly 50/50 across ISP-A and ISP-B — and the
distribution shifts from week to week as external paths change. Capacity planning is
impossible while the inbound split is non-deterministic. The customer has decided to
designate **ISP-A as the primary inbound path** (their ISP-A circuit is larger and cheaper)
and to keep ISP-B as a passive backup that takes traffic only if ISP-A becomes unreachable.

You will use AS-path prepending on R2's eBGP egress to make ISP-B's view of the customer
prefix two AS hops longer than ISP-A's view. The verification target is that two new ISP
internal routers — R5 inside ISP-A and R6 inside ISP-B — both choose the path via ISP-A
when sending traffic to 192.168.1.0/24.

```
       AS 65100 (ISP-A)              AS 65001 (Customer)              AS 65200 (ISP-B)
   ┌───────────────────┐    ┌─────────────────────────────┐    ┌───────────────────┐
   │   ┌────┐  iBGP    │    │  ┌────┐    iBGP    ┌────┐   │    │   iBGP   ┌────┐  │
   │   │ R5 ├──────────┤    ├──┤ R1 ├────────────┤ R2 ├───┤    ├──────────┤ R6 │  │
   │   │Lo1=│  L4      │ L1 │  │CE1 │     L3     │CE2 │ L2│    │  L5      │Lo1=│  │
   │   │.100│   ┌────┐ │    │  │Lo1=│            │    │   │    │  ┌────┐  │.200│  │
   │   │.2.0│   │ R3 ├─┤    ├──┤.168│            │    │   ├────┤  │ R4 │  │.2.0│  │
   │   │/24 │   │PE-A│ │    │  │.1.0│            │    │   │    │  │PE-B│  │/24 │  │
   │   └────┘   │Lo1=│ │    │  │/24 │            │    │   │    │  │Lo1=│  └────┘  │
   │            │.100│ │    │  └────┘            └────┘   │    │  │.200│          │
   │            │.1.0│ │    │     │                  │    │    │  │.1.0│          │
   │            │/24 │ │    │  ROUTE-MAP        ROUTE-MAP │    │  │/24 │          │
   │            └────┘ │    │  TRANSIT_         TRANSIT_  │    │  └────┘          │
   │                   │    │  PREVENT_OUT      PREVENT_OUT     │                  │
   └───────────────────┘    │  (filter only)    (filter +       │                  │
                            │                    prepend ×2)    │
                            └─────────────────────────────┘
```

**Key relationships for lab-02:**

- L4 (R3↔R5, 10.1.35.0/30) and L5 (R4↔R6, 10.1.46.0/30) are new physical links inside the
  two ISPs. Each ISP edge runs iBGP to its internal peer with `next-hop-self`.
- The asymmetry: R1's `TRANSIT_PREVENT_OUT` on neighbor 10.1.13.2 still has only a
  filter; R2's same-named route-map on neighbor 10.1.24.2 now also adds `set as-path
  prepend 65001 65001`.
- Verification depends on **four** observation points: AS-path length on R3, AS-path
  length on R4, and best-path selection on R5 and R6 for 192.168.1.0/24.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer CE1 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Customer CE2 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | ISP-A edge (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | ISP-B edge (AS 65200) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | ISP-A internal (AS 65100) — new in lab-02 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | ISP-B internal (AS 65200) — new in lab-02 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback and Cabling Additions (lab-02)

| Link | Endpoints | Subnet |
|---|---|---|
| L4 | R3 Gi0/1 ↔ R5 Gi0/0 | 10.1.35.0/30 |
| L5 | R4 Gi0/1 ↔ R6 Gi0/0 | 10.1.46.0/30 |

| Loopback | Device | Address |
|---|---|---|
| Lo0 | R5 | 10.0.0.5/32 |
| Lo1 | R5 | 10.100.2.1/24 |
| Lo0 | R6 | 10.0.0.6/32 |
| Lo1 | R6 | 10.200.2.1/24 |

### Advertised Prefixes (after lab-02 prepend applied)

| Source | Prefix | Reaches | AS-path on receiver |
|---|---|---|---|
| R1 (Lo1) | 192.168.1.0/24 | R3 (eBGP) → R5 (iBGP) | `65001` (length 1) |
| R2 (Null0) | 192.168.1.0/24 | R4 (eBGP) → R6 (iBGP) | `65001 65001 65001` (length 3, two prepends + origin) |
| R3 (Lo1) | 10.100.1.0/24 | R1 (eBGP), R5 (iBGP, originated by R3) | unchanged from lab-01 |
| R4 (Lo1) | 10.200.1.0/24 | R2 (eBGP), R6 (iBGP, originated by R4) | unchanged from lab-01 |
| R5 (Lo1) | 10.100.2.0/24 | R3 (iBGP) → R1 (eBGP) | `65100` on R1 |
| R6 (Lo1) | 10.200.2.0/24 | R4 (iBGP) → R2 (eBGP) | `65200` on R2 |

> The customer prefix's AS-path on the **R5** path is 1 because R3 sends it eastbound
> over iBGP without modifying the AS-path. The customer prefix's AS-path on the **R6**
> path is 3 because R2 prepends twice on outbound to R4 *before* R4 then sends to R6 over
> iBGP (iBGP does not add to AS-path either). Length 1 vs. length 3 is the tie-breaker
> that drives R5 and R6 to prefer the path via ISP-A.

---

## 4. Base Configuration

The starting point is **the solution state of lab-01** — eBGP up, iBGP up, customer prefix
filtered to a single advertisement per ISP, transit leak closed — plus the new R5 and R6
nodes with bare interface configuration only (no BGP, no iBGP yet).

**IS pre-loaded:**
- All lab-01 solution work (R1-R4 BGP, transit-prevention filter on both eBGP egresses)
- R3's new Gi0/1 to R5 (10.1.35.1/30) and R4's new Gi0/1 to R6 (10.1.46.1/30), interfaces up
- R5 with Lo0, Lo1, and Gi0/0 to R3 (10.1.35.2/30); no BGP on R5
- R6 with Lo0, Lo1, and Gi0/0 to R4 (10.1.46.2/30); no BGP on R6

**IS NOT pre-loaded** (student configures this):
- iBGP between R3 and R5 with `update-source Loopback0` and `next-hop-self`
- iBGP between R4 and R6 with `update-source Loopback0` and `next-hop-self`
- Static loopback reachability between R3↔R5 and R4↔R6 (no IGP in this topology)
- BGP origination of 10.100.2.0/24 on R5 and 10.200.2.0/24 on R6
- `set as-path prepend 65001 65001` added to R2's existing `route-map TRANSIT_PREVENT_OUT`
  permit-10 sequence
- Outbound soft refresh on R2 toward R4 to push the new AS-path attribute

---

## 5. Lab Challenge: Core Implementation

### Task 1: Activate R5 Inside ISP-A

On R3, configure an iBGP neighbor to R5's loopback (10.0.0.5) sourced from Loopback0,
activated under address-family ipv4 with `next-hop-self`. Add a static route on R3 for
10.0.0.5/32 via 10.1.35.2 so R3 can reach R5's loopback for the iBGP TCP session. On R5,
do the symmetric work: BGP AS 65100, neighbor 10.0.0.3 update-source Loopback0,
next-hop-self under address-family ipv4, static route to 10.0.0.3/32 via 10.1.35.1, and a
network statement for 10.100.2.0/24 (whose Lo1 must be present).

**Verification:** `show ip bgp summary` on R3 lists 10.0.0.5 as Established. R5's BGP
table contains 192.168.1.0/24 with AS-path `65001`, next-hop 10.0.0.3, and 10.100.1.0/24
with AS-path empty (locally-originated by R3).

---

### Task 2: Activate R6 Inside ISP-B

Mirror Task 1 on the ISP-B side. R4 ↔ R6 iBGP with update-source Loopback0 and
next-hop-self; static loopback reachability over the new L5 link; R6 originates
10.200.2.0/24.

**Verification:** `show ip bgp summary` on R4 lists 10.0.0.6 as Established. R6's BGP
table contains 192.168.1.0/24 with AS-path `65001`, next-hop 10.0.0.4, and 10.200.1.0/24
with AS-path empty (locally-originated by R4). At this point, **before any prepending
work**, both R5 and R6 see the customer prefix with the same AS-path length 1.

---

### Task 3: Confirm the Inbound Split Is Indeterminate Today

Before adding the prepend, document what happens without it. On R5 and R6, look at the
AS-path on 192.168.1.0/24. Both should show length 1 (`65001`). The choice between paths
at any external router transiting the global Internet would fall to later tie-breakers
(origin code, MED, eBGP-vs-iBGP, IGP cost, peer router-id) — none of which the customer
controls. This is the state lab-01 left behind: filter correct, but no inbound preference.

**Verification:** `show ip bgp 192.168.1.0` on R5 — AS-path is `65001`. Same on R6 —
AS-path is `65001`. Document the symmetry; it is the problem this lab solves.

---

### Task 4: Add AS-Path Prepend to R2's Outbound Route-Map

R2 already has `route-map TRANSIT_PREVENT_OUT permit 10` from lab-01 — currently with one
`match` clause and no `set` clauses. Edit the existing sequence to add a single `set`
directive that prepends the customer's own AS twice. Do not create a new route-map; do not
add a second permit sequence. The single coalesced policy now does filter + prepend on the
same outbound advertisement.

**Verification:** `show route-map TRANSIT_PREVENT_OUT` on R2 returns one sequence (10,
permit) with one match clause (`ip address prefix-list TRANSIT_PREVENT`) and one set
clause (`as-path prepend 65001 65001`).

---

### Task 5: Refresh the Outbound Policy and Verify the AS-Path Asymmetry

Trigger an outbound soft refresh on R2's eBGP session to R4 so the new AS-path takes
effect without resetting the session. Then walk the verification chain end to end:

- On R4, confirm 192.168.1.0/24 arrives with AS-path `65001 65001 65001`. R3, by
  contrast, still receives it with AS-path `65001`.
- On R5, confirm `show ip bgp 192.168.1.0` shows AS-path `65001` (the prefix R3 sent over
  iBGP, which does not add AS entries).
- On R6, confirm `show ip bgp 192.168.1.0` shows AS-path `65001 65001 65001` (the
  prefix R4 sent over iBGP, which also does not add entries).
- Best-path selection at any router that peers with both ISPs (not present in this lab
  but the design target) would now prefer the via-ISP-A path because length 1 < length 3.

**Verification:** AS-path on R3 and R5 is `65001`; AS-path on R4 and R6 is `65001 65001
65001`. R5 and R6 each have only one path to 192.168.1.0/24 (their respective ISP edge),
so best-path selection inside each ISP is trivial — but the asymmetry has been built into
the inter-AS advertisements and is what an external peer would see.

---

## 6. Verification & Analysis

### Before Prepending — Symmetric AS-Path Length

```
R3# show ip bgp 192.168.1.0
BGP routing table entry for 192.168.1.0/24, version 4
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65001                                           ! ← AS-path length 1
    10.1.13.1 from 10.1.13.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, external, best
```

```
R4# show ip bgp 192.168.1.0
BGP routing table entry for 192.168.1.0/24, version 4
Paths: (1 available, best #1, table default)
  65001                                           ! ← AS-path length 1 — symmetric
    10.1.24.1 from 10.1.24.1 (10.0.0.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
```

### After Prepending — Asymmetric AS-Path Length (Two Hops Longer via ISP-B)

```
R3# show ip bgp 192.168.1.0
  65001                                           ! ← still length 1
    10.1.13.1 from 10.1.13.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, external, best
```

```
R4# show ip bgp 192.168.1.0
  65001 65001 65001                               ! ← length 3 — two prepends added
    10.1.24.1 from 10.1.24.1 (10.0.0.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
```

### Inside the ISPs — iBGP Carries the AS-Path Unchanged

```
R5# show ip bgp 192.168.1.0
  65001                                           ! ← from R3 over iBGP, AS-path unchanged
    10.0.0.3 (metric 0) from 10.0.0.3 (10.0.0.3)
      Origin IGP, metric 0, localpref 100, valid, internal, best
```

```
R6# show ip bgp 192.168.1.0
  65001 65001 65001                               ! ← from R4 over iBGP, AS-path unchanged
    10.0.0.4 (metric 0) from 10.0.0.4 (10.0.0.4)
      Origin IGP, metric 0, localpref 100, valid, internal, best
```

### Outbound View — What R2 Actually Sends to R4

```
R2# show ip bgp neighbors 10.1.24.2 advertised-routes
   Network          Next Hop            Metric LocPrf Weight Path
*> 192.168.1.0/24   0.0.0.0                  0         32768 65001 65001 i  ! ← prepend in effect
                                                                              ! ← (origin AS suppressed in summary;
                                                                              !    received as 65001 65001 65001)
```

Cisco's summary `show ip bgp neighbors … advertised-routes` output does not always include
the origin AS in the Path column for locally-originated prefixes — the receiving router
is the authoritative observation point. The detailed `show ip bgp 192.168.1.0` on R4 is
where the full, prepended AS-path is unambiguous.

---

## 7. Verification Cheatsheet

### AS-Path Prepending Configuration Pattern

```
route-map TRANSIT_PREVENT_OUT permit 10
 match ip address prefix-list TRANSIT_PREVENT
 set as-path prepend 65001 65001                  ! prepend self-AS twice

router bgp 65001
 address-family ipv4
  neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.1.24.2 soft out                   ! push the new attribute
```

| Command | Purpose |
|---|---|
| `show ip bgp <prefix>` | **Detailed view.** AS-path is the unlabeled first line of each path; this is the authoritative receiver-side check |
| `show ip bgp` | **Table view.** AS-path is the rightmost `Path` column; quick to scan many prefixes at once |
| `show route-map <name>` | Confirms the `set as-path prepend` clause is attached to the right sequence |
| `show ip bgp neighbors <peer> advertised-routes` | Sender-side view; useful for confirming what is leaving this router |
| `clear ip bgp <peer> soft out` | Re-runs outbound policy on the existing session without tearing it down |

> **Exam tip:** `show ip bgp <prefix>` is the cleanest way to read AS-path. The first
> unlabeled line is always the AS-path. `show ip bgp` (no prefix) puts AS-path in the last
> column on a single line — fine for many prefixes at a glance, but on a wide AS-path it
> can wrap or get truncated.

### Inbound TE Decision Tree

| Goal | Tool |
|---|---|
| Steer inbound between two links to the **same** upstream AS | MED |
| Steer inbound between two **different** upstream ASes | AS-path prepend |
| Steer inbound by community signaling (ISP-defined LOCAL_PREF actions) | BGP communities (lab-04) |
| Steer inbound at a single chosen peer only (selective announcement) | Selective advertisement / partial advertisement (lab-03) |

### AS-Path Prepend Pitfalls

| Symptom | Likely Cause |
|---|---|
| Prepend committed but R4's AS-path still shows length 1 | Forgot `clear ip bgp <peer> soft out` after editing the route-map |
| 192.168.1.0/24 disappears from R4's BGP table entirely | Prepend value is the **neighbor's** AS (e.g., `set as-path prepend 65200 65200`) — receiver loop-prevention drops the update |
| ISP-A traffic still takes the wrong inbound path | Prepend was added to R1's route-map (toward R3) instead of R2's (toward R4) — primary lengthened, backup unchanged, preference inverts |
| AS-path on R6 is `65001 65001` (length 2) instead of `65001 65001 65001` (length 3) | One prepend instead of two; or the customer prefix is being received from both R4 and via the iBGP path, and BGP is choosing the unprepended one |
| 10.100.2.0/24 reaches R1 but R5 cannot reach 192.168.1.0/24 in its RIB | `next-hop-self` missing on R3's iBGP advertisement to R5 — BGP path is in the table but the next-hop is unreachable |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

<details>
<summary>Click to view R3 Configuration (iBGP to R5, next-hop-self)</summary>

```bash
! R3
ip route 10.0.0.5 255.255.255.255 10.1.35.2

router bgp 65100
 neighbor 10.0.0.5 remote-as 65100
 neighbor 10.0.0.5 description iBGP to R5 (ISP-A internal)
 neighbor 10.0.0.5 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.5 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration (iBGP to R6, next-hop-self)</summary>

```bash
! R4
ip route 10.0.0.6 255.255.255.255 10.1.46.2

router bgp 65200
 neighbor 10.0.0.6 remote-as 65200
 neighbor 10.0.0.6 description iBGP to R6 (ISP-B internal)
 neighbor 10.0.0.6 update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.6 activate
  neighbor 10.0.0.6 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 Configuration (iBGP to R3, originate 10.100.2.0/24)</summary>

```bash
! R5
interface Loopback0
 ip address 10.0.0.5 255.255.255.255
interface Loopback1
 ip address 10.100.2.1 255.255.255.0
interface GigabitEthernet0/0
 ip address 10.1.35.2 255.255.255.252
 no shutdown

ip route 10.0.0.3 255.255.255.255 10.1.35.1

router bgp 65100
 bgp router-id 10.0.0.5
 no bgp default ipv4-unicast
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 update-source Loopback0
 address-family ipv4
  network 10.100.2.0 mask 255.255.255.0
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R6 Configuration (iBGP to R4, originate 10.200.2.0/24)</summary>

```bash
! R6
interface Loopback0
 ip address 10.0.0.6 255.255.255.255
interface Loopback1
 ip address 10.200.2.1 255.255.255.0
interface GigabitEthernet0/0
 ip address 10.1.46.2 255.255.255.252
 no shutdown

ip route 10.0.0.4 255.255.255.255 10.1.46.1

router bgp 65200
 bgp router-id 10.0.0.6
 no bgp default ipv4-unicast
 neighbor 10.0.0.4 remote-as 65200
 neighbor 10.0.0.4 update-source Loopback0
 address-family ipv4
  network 10.200.2.0 mask 255.255.255.0
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration (add AS-path prepend to existing route-map)</summary>

```bash
! R2 — extend the lab-01 route-map; do not create a new one
route-map TRANSIT_PREVENT_OUT permit 10
 set as-path prepend 65001 65001

clear ip bgp 10.1.24.2 soft out
```

R1 is unchanged from lab-01: filter only on the route-map toward R3, no prepend.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R3 and R4 — confirm AS-path length asymmetry:
show ip bgp 192.168.1.0     ! R3 → AS-path 65001 (length 1)
show ip bgp 192.168.1.0     ! R4 → AS-path 65001 65001 65001 (length 3)

! On R5 and R6 — confirm internal hosts inherit the asymmetry:
show ip bgp 192.168.1.0     ! R5 → AS-path 65001
show ip bgp 192.168.1.0     ! R6 → AS-path 65001 65001 65001

! On R2 — confirm the route-map structure:
show route-map TRANSIT_PREVENT_OUT
show ip bgp neighbors 10.1.24.2 advertised-routes

! Reachability sanity:
ping 192.168.1.1 source loopback1   ! from R5 → must transit ISP-A → CE1 → R1
ping 192.168.1.1 source loopback1   ! from R6 → must transit ISP-B → CE2 → R2
```
</details>

---

## 9. Troubleshooting Scenarios

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to lab-01 solution + R5/R6 baseline
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # bring lab to lab-02 solution
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — Inbound Preference Inverted

The customer's BGP team configured AS-path prepending as part of the inbound-TE design.
ISP-A is supposed to be the primary inbound path. Post-change measurements show external
traffic to 192.168.1.0/24 is now preferring ISP-B instead of ISP-A — the opposite of the
intent. The route-map and prefix-list look correct on inspection, and the policy is bound
outbound on an eBGP session.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R3's view of 192.168.1.0/24 has AS-path length 1; R4's view has
length 3. R6 prefers the path via ISP-A.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 192.168.1.0` on R3 — AS-path is `65001 65001 65001` (length 3).
2. `show ip bgp 192.168.1.0` on R4 — AS-path is `65001` (length 1).
3. The asymmetry is present but **inverted**. The prepend was applied on the wrong egress.
4. `show ip bgp neighbors 10.1.13.2 | include route-map` on R1 reveals
   `Outgoing update network filter list is route-map TRANSIT_PREVENT_OUT`. That alone is
   correct — the surprise is that R1's `TRANSIT_PREVENT_OUT` now contains a `set as-path
   prepend 65001 65001` clause it was never supposed to have.
5. `show route-map TRANSIT_PREVENT_OUT` on R2 confirms R2's route-map has only the
   filter — no prepend. The prepend was added to the wrong CE.
</details>

<details>
<summary>Click to view Fix</summary>

Remove the prepend from R1 and add it to R2 (the policy belongs on the **backup** path's
egress).

```bash
! R1
route-map TRANSIT_PREVENT_OUT permit 10
 no set as-path prepend 65001 65001

clear ip bgp 10.1.13.2 soft out

! R2
route-map TRANSIT_PREVENT_OUT permit 10
 set as-path prepend 65001 65001

clear ip bgp 10.1.24.2 soft out
```

After the fix, R3 sees AS-path length 1 and R4 sees length 3 — primary preference restored.
</details>

---

### Ticket 2 — Customer Prefix Vanished From ISP-B

Following the inbound-TE rollout, the ISP-B NOC reports that 192.168.1.0/24 is **missing
entirely** from R4's BGP table. The eBGP session R2↔R4 is Established. R2's outbound
policy is in place. ISP-A is still receiving the prefix normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** R4's BGP table contains 192.168.1.0/24 with AS-path `65001 65001
65001`. R6 has a best-path entry for 192.168.1.0/24.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 192.168.1.0` on R4 — `% Network not in table`.
2. `show ip bgp neighbors 10.1.24.2 advertised-routes` on R2 — 192.168.1.0/24 is listed
   as advertised. R2 is sending it; R4 is dropping it.
3. `show ip bgp neighbors 10.1.24.2 received-routes` on R4 (or `debug ip bgp updates in`
   briefly) reveals updates being denied with reason `as-path contains our own AS`.
4. `show route-map TRANSIT_PREVENT_OUT` on R2 — `set as-path prepend 65200 65200`.
   The prepend value is the **neighbor's** AS (ISP-B), not the customer's own AS. R4
   sees its own AS (65200) in the AS-path of an incoming update and applies the standard
   eBGP loop-prevention rule, discarding it.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
route-map TRANSIT_PREVENT_OUT permit 10
 no set as-path prepend 65200 65200
 set as-path prepend 65001 65001

clear ip bgp 10.1.24.2 soft out
```

Loop prevention is unforgiving — even one occurrence of the receiver's AS in an inbound
update is enough to discard it. Always prepend with **the customer's own AS**, never with
a neighbor's or any AS the customer does not own.
</details>

---

### Ticket 3 — R5 Sees the Customer Prefix But Cannot Reach It

ISP-A's NOC reports that R5 has 192.168.1.0/24 in its BGP table, but the prefix is **not
marked as best path** and is missing from R5's RIB. Pings from Lo1 (10.100.2.1) to
192.168.1.1 fail. The eBGP session R3↔R1 is healthy; the iBGP session R3↔R5 is
Established.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R5 can ping 192.168.1.1 from Lo1. The BGP path on R5 for
192.168.1.0/24 has next-hop 10.0.0.3 (R3's loopback) and shows status `valid, internal,
best` with `>` in the table view.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 192.168.1.0` on R5 — the path is present in the BGP table but the next-hop
   reads `10.1.13.1` (R1's eBGP-facing address) instead of `10.0.0.3` (R3's loopback).
   The detailed output shows `Inaccessible`; the table view (`show ip bgp`) shows no `>`
   marker beside the prefix because the next-hop reachability check failed.
2. `show ip route 10.1.13.1` on R5 — `% Network not in table`. ISP-A internal has no
   route to the customer-facing eBGP transit subnet 10.1.13.0/30, which is exactly the
   point of `next-hop-self` on the ISP edge: the eBGP transit subnet is not redistributed
   into the ISP's IGP/static plumbing and must be hidden from internal peers.
3. `show ip bgp neighbors 10.0.0.5 advertised-routes` on R3 — 192.168.1.0/24 is listed
   as sent. `show ip bgp 192.168.1.0` on R3 shows next-hop 10.1.13.1, and R3 is forwarding
   the **received** next-hop unchanged to its iBGP peer instead of rewriting it to its
   own loopback.
4. `show running-config | section router bgp` on R3 reveals the missing
   `neighbor 10.0.0.5 next-hop-self` directive under address-family ipv4. iBGP defaults
   to preserving the eBGP-learned next-hop; that default works only when the iBGP peer
   has reachability to that next-hop — ISP-A internal does not.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.5 next-hop-self
 exit-address-family

clear ip bgp 10.0.0.5 soft out
```

After the fix, R5's BGP entry for 192.168.1.0/24 shows next-hop 10.0.0.3, the path becomes
`valid, internal, best`, and the ping from Lo1 succeeds (recursive lookup: 10.0.0.3 →
10.1.35.1 via static, then onward to R1 via the customer eBGP path).
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R3 ↔ R5 iBGP Established with `update-source Loopback0` and `next-hop-self`
- [ ] R4 ↔ R6 iBGP Established with `update-source Loopback0` and `next-hop-self`
- [ ] R5 originates 10.100.2.0/24 and R6 originates 10.200.2.0/24
- [ ] Pre-prepend: AS-path on R3 and R4 for 192.168.1.0/24 is symmetric (both length 1)
- [ ] `set as-path prepend 65001 65001` added to R2's existing `TRANSIT_PREVENT_OUT permit 10`
- [ ] R1's `TRANSIT_PREVENT_OUT` is **unchanged** from lab-01 (no prepend)
- [ ] Outbound soft refresh issued on R2 toward 10.1.24.2
- [ ] Post-prepend: AS-path on R3 for 192.168.1.0/24 is `65001` (length 1)
- [ ] Post-prepend: AS-path on R4 for 192.168.1.0/24 is `65001 65001 65001` (length 3)
- [ ] Post-prepend: AS-path on R5 mirrors R3 (length 1) and AS-path on R6 mirrors R4 (length 3)
- [ ] Reachability: R5 pings 192.168.1.1 (sourced Lo1); R6 pings 192.168.1.1 (sourced Lo1)

### Troubleshooting

- [ ] Ticket 1 resolved — prepend moved from R1 to R2 (preference no longer inverted)
- [ ] Ticket 2 resolved — prepend value corrected from neighbor-AS to self-AS
- [ ] Ticket 3 resolved — `next-hop-self` added on R3's iBGP to R5

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
