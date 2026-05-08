# Lab 01 — Transit Prevention Policy

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

This lab confronts the single most common operational hazard introduced by the dual-CE
topology built in lab-00: **the customer AS becomes a free transit path between the two
ISPs unless the operator explicitly stops it.** Lab-00 ended with full reachability — both
CEs see both ISPs' prefixes, both ISPs see the customer prefix. That same configuration,
unmodified, also re-advertises ISP-A's prefixes to ISP-B and vice versa, turning the
customer AS into a transit AS for the providers' inter-provider traffic. This lab proves
the leak, then closes it.

---

### Why a Dual-Homed Customer AS Leaks Transit by Default

BGP's default behavior is to re-advertise every best-path prefix to every eBGP neighbor.
That default is correct for an ISP — the entire reason an ISP runs BGP is to redistribute
prefixes between peers. For a customer AS, the default is wrong. Consider the path a
prefix takes through the lab-00 topology:

1. R3 (ISP-A) advertises 10.100.1.0/24 to R1 over eBGP.
2. R1 installs 10.100.1.0/24 with AS-path `65100` and re-advertises it to R2 over iBGP
   (next-hop-self in effect).
3. R2 receives 10.100.1.0/24 with AS-path `65100`. R2 then advertises it over eBGP to R4
   — prepending its own AS, so R4 sees AS-path `65001 65100`.
4. R4 (ISP-B) now has a route to ISP-A's prefix via the customer AS.

If R3 also advertises this prefix to its other ISP-A peers and the path through the
customer AS happens to look attractive, ISP-B's traffic toward 10.100.1.0/24 enters the
customer AS via R2, traverses the iBGP path R2→R1, and exits back into ISP-A. The customer
pays for both transit links and burns its own backbone capacity carrying traffic that has
nothing to do with it. The same leak runs in reverse for 10.200.1.0/24 (ISP-B → ISP-A).

**The fix is policy-based outbound filtering.** The customer must advertise only its own
prefix (192.168.1.0/24) to either ISP. Routes learned from one ISP must not be forwarded
to the other.

---

### Where to Put the Filter — and Why It Matters

A filter that achieves "only the customer prefix leaves AS 65001" can be installed in
several places. The choice has lasting consequences for later labs in this series.

| Filter location | Effect | Trade-off |
|---|---|---|
| Outbound on each eBGP egress (R1→R3, R2→R4) | Blocks ISP-A and ISP-B prefixes from leaving the AS | iBGP table on each CE keeps the full set of routes — **the option this lab uses** |
| Inbound on each eBGP ingress (R1 from R3, R2 from R4) | Drops other-ISP prefixes from the BGP table entirely | Wrong — the customer wants to *use* those prefixes for outbound traffic |
| Outbound on the CE-CE iBGP session | Stops one CE from learning the other ISP's prefixes | Breaks lab-03's LOCAL_PREF objective: each CE must see both ISPs' routes to choose between them for its own outbound traffic |

The third option is the trap the planted Ticket 1 fault demonstrates. It does prevent the
transit leak (the route never reaches the second CE, so it cannot be re-advertised) — but
it also makes each CE blind to the other ISP, which is exactly the routing gap lab-00 set
out to close. The right answer is **outbound on each eBGP session**: keep the full BGP
table on each CE, but refuse to leak it back out to the providers.

---

### Prefix-List vs. Route-Map — Why Both

A simple `neighbor … prefix-list TRANSIT_PREVENT out` would compile and work for the
single-prefix case in this lab. The reason this lab wraps the prefix-list inside a
route-map (`route-map TRANSIT_PREVENT_OUT permit 10` with `match ip address prefix-list
TRANSIT_PREVENT`) is forward-looking:

- Lab-02 will need to **modify** outbound updates (AS-path prepending). `set as-path
  prepend` requires a route-map; it cannot be expressed with a prefix-list directive.
- Lab-04 (capstone) demands a single coherent outbound policy that combines prefix
  filtering, AS-path prepending, and (potentially) community tagging. A route-map can grow
  to all three; a `neighbor … prefix-list … out` directive cannot.

Establishing the route-map skeleton in lab-01 means later labs add `set` clauses to an
existing structure rather than replacing the policy framework mid-progression.

The `permit 192.168.1.0/24 le 32` form (rather than just `permit 192.168.1.0/24`) is also
deliberate. Lab-03 will originate two more-specifics — `192.168.1.0/25` from R1 and
`192.168.1.128/25` from R2 — to split inbound traffic across the two ISPs. The `le 32`
qualifier permits the /24 plus any longer prefix within it, so the lab-03 more-specifics
will pass through the lab-01 filter without further modification.

---

### Skills This Lab Develops

| Skill | Description |
|---|---|
| Transit-leak diagnosis | Reading AS-path on the receiving ISP's BGP table to confirm the customer AS is acting as transit |
| `ip prefix-list` syntax | Permitting an exact prefix and a contiguous range with `le` |
| `route-map` outbound policy | Wrapping a `match ip address prefix-list` in a route-map for extensibility |
| Outbound filter placement | Choosing the eBGP egress over iBGP to preserve full BGP tables on each CE |
| BGP soft-reconfiguration | Refreshing an outbound policy without resetting the session (`clear ip bgp <peer> out` / `soft out`) |
| Negative verification | Proving a prefix is *absent* from a neighbor's BGP table after a filter is applied |

---

## 2. Topology & Scenario

**Scenario:** The dual-CE topology from lab-00 is in production. Both ISPs have completed
internal monitoring and the ISP-B NOC has just escalated an unusual finding: 10.100.1.0/24
— ISP-A's prefix — is appearing in R4's BGP table with the customer AS in the AS-path.
ISP-A's NOC has independently noticed the mirror image: 10.200.1.0/24 reachable through
AS 65001. Neither ISP wants to use the customer AS as a transit path, and the customer
contract explicitly prohibits providing transit. Your job is to confirm the leak, define
a transit-prevention policy, and apply it without disrupting the customer's own
reachability through both providers.

```
       AS 65100                 AS 65001 (Customer)                AS 65200
   ┌────────────┐    ┌───────────────────────────────────┐    ┌────────────┐
   │     R3     │L1──┤   ┌────────┐  L3   ┌────────┐     ├─L2─┤     R4     │
   │ ISP-A PE   │    │   │   R1   ├───────┤   R2   │     │    │ ISP-B PE   │
   │ 10.100.1.0 │    │   │  CE1   │ iBGP  │  CE2   │     │    │ 10.200.1.0 │
   └────────────┘    │   │ Lo1=   │       │(no Lo1)│     │    └────────────┘
                     │   │192.168.│       │        │     │
                     │   │ 1.0/24 │       │        │     │
                     │   └───┬────┘       └───┬────┘     │
                     │       │                │          │
                     │   route-map         route-map     │
                     │   TRANSIT_PREVENT_OUT TRANSIT_PREVENT_OUT
                     │   applied to        applied to    │
                     │   neighbor 10.1.13.2 neighbor 10.1.24.2
                     │   (eBGP to R3)      (eBGP to R4)  │
                     └───────────────────────────────────┘
```

**Key relationships for lab-01:**

- The leak path is bidirectional: R3 → R1 → R2 → R4 (ISP-A prefix to ISP-B), and R4 → R2
  → R1 → R3 (ISP-B prefix to ISP-A).
- The filter is installed at the **eBGP egress** on each CE: R1 toward 10.1.13.2 (R3),
  R2 toward 10.1.24.2 (R4). The CE-CE iBGP session is left unfiltered so each CE retains
  the full BGP table — needed for path selection in later labs.
- `prefix-list TRANSIT_PREVENT` permits 192.168.1.0/24 with `le 32`, so the /24 and any
  more-specifics (introduced in lab-03) pass; everything else is implicitly denied.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer CE1 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Customer CE2 (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | ISP-A PE (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | ISP-B PE (AS 65200) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback and Cabling

Identical to lab-00. See `topology/README.md` for the full table.

### Advertised Prefixes (after lab-01 filter applied)

| Source | Prefix | Goes to | Notes |
|---|---|---|---|
| R1 (Lo1) | 192.168.1.0/24 | R3 (ISP-A) via eBGP, R2 via iBGP | Customer PI |
| R2 (Null0) | 192.168.1.0/24 | R4 (ISP-B) via eBGP, R1 via iBGP | Customer PI (dual origination) |
| R3 (Lo1) | 10.100.1.0/24 | R1 only — **must not** reach R4 | ISP-A representative prefix |
| R4 (Lo1) | 10.200.1.0/24 | R2 only — **must not** reach R3 | ISP-B representative prefix |

---

## 4. Base Configuration

The starting point for this lab is **the solution state of lab-00** — eBGP up on both
sides, iBGP up between the CEs, customer prefix advertised from both, both ISPs reachable
from both CEs. `setup_lab.py` pushes that full state, not just the interface addressing.

**IS pre-loaded:**
- Hostnames, interface IP addressing, loopbacks, `no ip domain-lookup`
- Full lab-00 BGP solution: eBGP R1↔R3, eBGP R2↔R4, iBGP R1↔R2 with `update-source
  Loopback0` and `next-hop-self`, customer 192.168.1.0/24 originated from both CEs

**IS NOT pre-loaded** (student configures this):
- `ip prefix-list TRANSIT_PREVENT` permitting 192.168.1.0/24 with `le 32`
- `route-map TRANSIT_PREVENT_OUT permit 10` matching the prefix-list
- `neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out` on R1
- `neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out` on R2

---

## 5. Lab Challenge: Core Implementation

### Task 1: Confirm the Transit Leak Exists

Before configuring anything, prove the problem. On R4, run `show ip bgp` and look for
`10.100.1.0/24`. On R3, run `show ip bgp` and look for `10.200.1.0/24`. For each, capture
the AS-path. The AS-path will reveal that the route originated in the other ISP and
reached this ISP **through AS 65001** — the signature of a transit leak.

**Verification:** R4's BGP table contains `10.100.1.0/24` with AS-path beginning `65001
65100`. R3's BGP table contains `10.200.1.0/24` with AS-path beginning `65001 65200`.
Document both AS-paths exactly as shown.

---

### Task 2: Define the Permit Set with a Prefix-List

Configure an `ip prefix-list` named `TRANSIT_PREVENT` on both R1 and R2 that permits
192.168.1.0/24 and any more-specifics (lab-03 will originate /25 longer matches; the
filter must allow them through without modification later).

**Verification:** `show ip prefix-list TRANSIT_PREVENT` on each CE returns one entry,
sequence 5, permitting 192.168.1.0/24 with `le 32`.

---

### Task 3: Wrap the Prefix-List in a Route-Map

On both R1 and R2, create a `route-map TRANSIT_PREVENT_OUT permit 10` whose only `match`
clause references `ip address prefix-list TRANSIT_PREVENT`. The route-map adds no `set`
actions in this lab — its sole job is to permit the customer prefix and (by the implicit
deny at the end of every route-map) drop everything else. Lab-02 will add a `set as-path
prepend` clause; the route-map skeleton put in place here is the structure that grows.

**Verification:** `show route-map TRANSIT_PREVENT_OUT` on each CE returns one sequence
(10, permit) with one match clause referencing `ip address prefix-list TRANSIT_PREVENT`
and no set clauses.

---

### Task 4: Apply the Filter Outbound on Each eBGP Session

On R1, apply `route-map TRANSIT_PREVENT_OUT` outbound on the eBGP neighbor 10.1.13.2 (R3,
ISP-A) under `address-family ipv4`. On R2, apply the same route-map outbound on neighbor
10.1.24.2 (R4, ISP-B). **Do not** apply the filter on the iBGP session between the CEs —
that would break each CE's view of the other ISP's prefixes (Ticket 1 demonstrates this
mistake).

After applying, trigger an outbound soft refresh so the policy takes effect without
resetting the eBGP session: `clear ip bgp 10.1.13.2 soft out` on R1 and `clear ip bgp
10.1.24.2 soft out` on R2.

**Verification:** `show ip bgp neighbors 10.1.13.2 | include route-map` on R1 returns
`Outgoing update network filter list is route-map TRANSIT_PREVENT_OUT`. Same on R2 for
10.1.24.2.

---

### Task 5: Verify the Leak Is Closed and Customer Reachability Is Intact

On R4, re-run `show ip bgp` and confirm `10.100.1.0/24` is **absent**. On R3, confirm
`10.200.1.0/24` is **absent**. Both ISPs must still see `192.168.1.0/24` with AS-path
`65001` (no leak removed the legitimate customer advertisement). On both CEs, confirm
that `10.100.1.0/24` and `10.200.1.0/24` are still present in the local BGP table — the
filter affects what is sent, not what is received.

**Verification:**
- R4's BGP table shows 192.168.1.0/24 (AS-path `65001`) and 10.200.1.0/24 (local) — no
  10.100.1.0/24.
- R3's BGP table shows 192.168.1.0/24 (AS-path `65001`) and 10.100.1.0/24 (local) — no
  10.200.1.0/24.
- R1's BGP table contains both 10.100.1.0/24 (eBGP) and 10.200.1.0/24 (iBGP, unchanged).
- R2's BGP table contains both 10.200.1.0/24 (eBGP) and 10.100.1.0/24 (iBGP, unchanged).

---

## 6. Verification & Analysis

### Before Filtering — The Leak Is Visible

```
R4# show ip bgp
BGP table version is 5, local router ID is 10.0.0.4
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
Origin codes: i - IGP, e - EGP, ? - incomplete

   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    10.1.24.1                              0 65001 65100 i   ! ← LEAK: ISP-A prefix via customer AS
*> 10.200.1.0/24    0.0.0.0                  0         32768 i
*> 192.168.1.0/24   10.1.24.1                              0 65001 i
```

```
R3# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    0.0.0.0                  0         32768 i
*> 10.200.1.0/24    10.1.13.1                              0 65001 65200 i   ! ← LEAK: ISP-B prefix via customer AS
*> 192.168.1.0/24   10.1.13.1                              0 65001 i
```

### After Filtering — Leak Closed, Customer Prefix Intact

```
R4# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.200.1.0/24    0.0.0.0                  0         32768 i
*> 192.168.1.0/24   10.1.24.1                              0 65001 i         ! ← only the customer prefix arrives
                                                                              ! ← 10.100.1.0/24 is gone
```

```
R3# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    0.0.0.0                  0         32768 i
*> 192.168.1.0/24   10.1.13.1                              0 65001 i         ! ← only the customer prefix arrives
                                                                              ! ← 10.200.1.0/24 is gone
```

### Customer-Side BGP Table — Unchanged by the Outbound Filter

```
R1# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*> 10.100.1.0/24    10.1.13.2                0             0 65100 i         ! ← still present (eBGP from R3)
*>i10.200.1.0/24    10.0.0.2                 0    100      0 65200 i         ! ← still present (iBGP from R2)
*> 192.168.1.0/24   0.0.0.0                  0         32768 i
*>i192.168.1.0/24   10.0.0.2                 0    100      0 i
```

### Outbound View — What R1 Is Actually Sending to R3

```
R1# show ip bgp neighbors 10.1.13.2 advertised-routes
BGP table version is 7, local router ID is 10.0.0.1
   Network          Next Hop            Metric LocPrf Weight Path
*> 192.168.1.0/24   0.0.0.0                  0         32768 i               ! ← only the customer prefix
                                                                              ! ← 10.200.1.0/24 not advertised — filtered out
```

---

## 7. Verification Cheatsheet

### Transit Prevention Configuration Pattern

```
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32

route-map TRANSIT_PREVENT_OUT permit 10
 match ip address prefix-list TRANSIT_PREVENT

router bgp 65001
 address-family ipv4
  neighbor <ebgp-peer> route-map TRANSIT_PREVENT_OUT out
 exit-address-family

! Apply without resetting the session:
clear ip bgp <ebgp-peer> soft out
```

| Command | Purpose |
|---|---|
| `show ip prefix-list TRANSIT_PREVENT` | Confirm the prefix-list contents |
| `show route-map TRANSIT_PREVENT_OUT` | Confirm the route-map structure and match clauses |
| `show ip bgp neighbors <peer> \| include route-map` | Confirm the route-map is bound outbound on the session |
| `show ip bgp neighbors <peer> advertised-routes` | The outbound view — what this router actually sends to that peer |
| `show ip bgp neighbors <peer> received-routes` | Requires `soft-reconfiguration inbound`; not used in this lab |
| `clear ip bgp <peer> soft out` | Re-run outbound policy on the existing session without tearing it down |

> **Exam tip:** `advertised-routes` is the authoritative outbound view. If the prefix you
> intended to filter is still listed there, the route-map is not bound, the prefix-list is
> wrong, or `clear ip bgp soft out` was not issued. Don't trust an empty BGP table on the
> peer until you have confirmed your own router stopped sending the prefix.

### Reading AS-Path to Detect a Transit Leak

A prefix originated by ISP-X with the customer AS in its AS-path on ISP-Y's table is the
unambiguous signature of a transit leak. The receiving ISP sees the originator's AS *after*
the customer AS — which means the route walked through the customer AS on its way in.

| AS-path on R4 for 10.100.1.0/24 | Interpretation |
|---|---|
| (prefix absent) | No leak — the desired post-fix state |
| `65001 65100` | Leak — R4 received the prefix via R2, who received it from R1, who received it from R3 |
| `65100` (only) | Direct ISP-A-to-ISP-B peering (not in this topology — would not involve the customer) |

> **Exam tip:** When a leak is suspected, look at the AS-path on the *receiving* ISP, not
> at the customer's BGP table. The customer is supposed to have those routes — that's
> the point of multihoming. The leak only manifests downstream.

### Outbound Filter Pitfalls

| Symptom | Likely Cause |
|---|---|
| Filter committed but the prefix still appears on the peer | Forgot `clear ip bgp <peer> soft out` |
| `prefix-list … le 32` works for /24 but lab-03 /25 fails | `permit 192.168.1.0/24` (without `le 32`) accepts only the exact /24 |
| Customer AS now sees only its own routes | Filter accidentally applied **inbound** (or applied to the iBGP session) — Ticket 1 |
| Both ISPs lost the customer prefix entirely | Route-map's first sequence is `deny 10` instead of `permit 10`; or no `match` clause means deny-all |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

<details>
<summary>Click to view R1 Configuration (transit-prevention filter on eBGP to R3)</summary>

```bash
! R1
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32

route-map TRANSIT_PREVENT_OUT permit 10
 match ip address prefix-list TRANSIT_PREVENT

router bgp 65001
 address-family ipv4
  neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.1.13.2 soft out
```
</details>

<details>
<summary>Click to view R2 Configuration (transit-prevention filter on eBGP to R4)</summary>

```bash
! R2
ip prefix-list TRANSIT_PREVENT seq 5 permit 192.168.1.0/24 le 32

route-map TRANSIT_PREVENT_OUT permit 10
 match ip address prefix-list TRANSIT_PREVENT

router bgp 65001
 address-family ipv4
  neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.1.24.2 soft out
```
</details>

<details>
<summary>Click to view R3 and R4 (no changes)</summary>

R3 and R4 retain their lab-00 configuration. The transit-prevention work is entirely on
the customer side; ISP routers are not modified.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R3 and R4 — confirm the leak is gone:
show ip bgp
show ip bgp 10.100.1.0      ! on R4 — should report "Network not in table"
show ip bgp 10.200.1.0      ! on R3 — should report "Network not in table"

! On R1 and R2 — confirm the outbound filter is bound:
show ip bgp neighbors 10.1.13.2 | include route-map
show ip bgp neighbors 10.1.24.2 | include route-map
show ip bgp neighbors 10.1.13.2 advertised-routes
show ip bgp neighbors 10.1.24.2 advertised-routes

! On R1 and R2 — confirm full BGP table is intact (filter affects sent, not received):
show ip bgp
```
</details>

---

## 9. Troubleshooting Scenarios

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to lab-00 solution state
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # bring lab to lab-01 solution
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

---

### Ticket 1 — The Transit Filter Was Applied to the Wrong Session

The customer's NOC reports that R1 now has a much smaller BGP table than expected — it
only sees its own customer prefix and ISP-A's representative prefix. The 10.200.1.0/24
prefix from ISP-B has disappeared from R1's table. ISP-B confirms its eBGP session to R2
is healthy. The transit-prevention work was applied earlier today.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R1's BGP table once again contains 10.200.1.0/24 (iBGP from R2)
*and* the original transit leak (10.100.1.0/24 reaching R4) is still suppressed.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp` on R1 — 10.200.1.0/24 is missing.
2. `show ip bgp neighbors 10.0.0.2 | include route-map` on R1 — reveals
   `Outgoing update network filter list is route-map TRANSIT_PREVENT_OUT` on the iBGP
   session. The transit filter is mis-applied: it was bound to the **iBGP** neighbor
   instead of the eBGP neighbor 10.1.13.2.
3. The route-map permits only 192.168.1.0/24 outbound, so when R2 sends 10.200.1.0/24 to
   R1 over iBGP, R2's outbound filter strips it. Wait — but it's R2 *sending*. Re-check
   whose route-map is mis-applied: `show ip bgp neighbors 10.0.0.1 | include route-map`
   on R2 confirms the issue is on R2 — the outbound filter toward R1's iBGP session is
   the one stripping non-customer prefixes.
4. The eBGP session R2→R4 has no outbound filter; the transit leak is still occurring on
   that session. `show ip bgp` on R4 confirms 10.100.1.0/24 is still present with
   AS-path `65001 65100` — the leak was never closed.
</details>

<details>
<summary>Click to view Fix</summary>

Two corrections are needed: remove the misplaced filter from the iBGP session, and apply
it to the correct eBGP session.

```bash
! R2
router bgp 65001
 address-family ipv4
  no neighbor 10.0.0.1 route-map TRANSIT_PREVENT_OUT out
  neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.0.0.1 soft out
clear ip bgp 10.1.24.2 soft out
```

After the fix, R1 sees 10.200.1.0/24 again (iBGP from R2 with next-hop 10.0.0.2), and R4's
BGP table no longer contains 10.100.1.0/24.
</details>

---

### Ticket 2 — Filter Committed But Leak Persists

After the transit-prevention work, ISP-A's NOC still reports 10.200.1.0/24 visible in R3's
BGP table with AS-path `65001 65200`. The on-call engineer confirms the route-map and
prefix-list both exist on R1 and look correct.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** R3's BGP table no longer contains 10.200.1.0/24.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip prefix-list TRANSIT_PREVENT` on R1 — present and correct.
2. `show route-map TRANSIT_PREVENT_OUT` on R1 — present and correct.
3. `show ip bgp neighbors 10.1.13.2 | include route-map` on R1 — output is empty. The
   route-map exists but is **not bound** to the eBGP session.
4. `show running-config | section router bgp` confirms no `route-map TRANSIT_PREVENT_OUT
   out` directive under address-family ipv4 for neighbor 10.1.13.2.
</details>

<details>
<summary>Click to view Fix</summary>

Bind the route-map and trigger the outbound refresh:

```bash
! R1
router bgp 65001
 address-family ipv4
  neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.1.13.2 soft out
```
</details>

---

### Ticket 3 — Filter Bound, Wrong Direction

ISP-B reports that 10.100.1.0/24 is still leaking through to R4. R2's running-config shows
the route-map is referenced on neighbor 10.1.24.2 — but the leak persists.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R4's BGP table no longer contains 10.100.1.0/24. R2's BGP table is
unchanged (full set of prefixes still received).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp neighbors 10.1.24.2 | include route-map` on R2 — reveals
   `Inbound update network filter list is route-map TRANSIT_PREVENT_OUT`. The route-map is
   bound **inbound** rather than outbound.
2. The inbound binding has no effect on what R2 sends to R4 — outbound updates are not
   filtered, so 10.100.1.0/24 still leaks. Worse, if the inbound policy actively dropped
   ISP-B's routes, R2 would also lose 10.200.1.0/24 — but the route-map happens to permit
   only 192.168.1.0/24, so most of ISP-B's prefixes are also being dropped on receipt.
3. `show running-config | section router bgp` on R2 reveals the typo: `neighbor 10.1.24.2
   route-map TRANSIT_PREVENT_OUT in` instead of `out`.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
router bgp 65001
 address-family ipv4
  no neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT in
  neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out
 exit-address-family

clear ip bgp 10.1.24.2 soft in
clear ip bgp 10.1.24.2 soft out
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Pre-fix verification: 10.100.1.0/24 visible on R4 with AS-path `65001 65100`
- [ ] Pre-fix verification: 10.200.1.0/24 visible on R3 with AS-path `65001 65200`
- [ ] `ip prefix-list TRANSIT_PREVENT` configured on R1 and R2 with `le 32`
- [ ] `route-map TRANSIT_PREVENT_OUT permit 10` configured on R1 and R2
- [ ] Route-map applied **outbound** on R1 toward 10.1.13.2 (R3)
- [ ] Route-map applied **outbound** on R2 toward 10.1.24.2 (R4)
- [ ] Soft outbound refresh issued on both eBGP sessions
- [ ] Post-fix: R4's BGP table does NOT contain 10.100.1.0/24
- [ ] Post-fix: R3's BGP table does NOT contain 10.200.1.0/24
- [ ] Post-fix: R3 and R4 both still see 192.168.1.0/24 with AS-path `65001`
- [ ] Post-fix: R1 still sees both 10.100.1.0/24 (eBGP) and 10.200.1.0/24 (iBGP)
- [ ] Post-fix: R2 still sees both 10.200.1.0/24 (eBGP) and 10.100.1.0/24 (iBGP)

### Troubleshooting

- [ ] Ticket 1 resolved — filter moved from iBGP session to correct eBGP session
- [ ] Ticket 2 resolved — route-map bound to neighbor and outbound refresh applied
- [ ] Ticket 3 resolved — direction corrected from `in` to `out`

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
