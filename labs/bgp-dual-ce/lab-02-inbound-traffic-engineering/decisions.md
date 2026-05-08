## Model gate — 2026-04-28
- Difficulty: Intermediate
- Running model: claude-opus-4-7
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions

### Fault-2 substitution: planted fault is on R2's egress, not on the iBGP session
Baseline.yaml objective 6 reads: "Planted fault: prepend applied on R2 toward R2 (CE-CE
iBGP) instead of toward R4 — ISP-B sees no prepend, ISP-A sees double prepend, path
selection inverts."

The described effect is internally inconsistent. If R2's prepend is mis-applied to the
CE-CE iBGP session toward R1, the prepended path would arrive at R1 over iBGP — but R1
already locally-originates 192.168.1.0/24 with the standard weight 32768, which beats any
iBGP-learned path during BGP best-path selection regardless of AS-path length. R1 therefore
keeps advertising its own copy of the prefix to R3 with AS-path `65001` (length 1) and the
"ISP-A sees double prepend" claim does not hold.

After advisor consultation, this lab substitutes a planted fault that produces the
described **observable behavior** (preference inversion) cleanly:

- **Ticket 1**: prepend applied on **R1's eBGP egress to R3** instead of on R2's eBGP
  egress to R4. Result: R3 sees AS-path length 3, R4 sees length 1, inbound preference
  flips to ISP-B — exactly the symptom the baseline aimed for.

The iBGP-prepend variant is reserved for `lab-05-capstone-troubleshooting`, where the
capstone fault catalogue can include "no observable effect because of weight/local-pref
override" as a teaching point. Here, the lab's goal is to teach the **decision** of where
to apply prepend (primary vs. backup, eBGP vs. iBGP) — Ticket 1 lands that point with a
fault that does invert preference.

### Route-map name retained: `TRANSIT_PREVENT_OUT`
Adding `set as-path prepend` to `route-map TRANSIT_PREVENT_OUT` makes the name no longer
fully descriptive — the policy now does both transit prevention and AS-path prepending.
The alternative considered was renaming the route-map to `EBGP_OUT_R4` (or splitting into
two route-maps `TRANSIT_PREVENT_FILTER` and `EBGP_OUT_PREPEND`).

The name is **kept** for two reasons:

1. **Continuity with the lab-01 student**: the workbook explicitly shows adding a `set`
   directive to the existing `permit 10` sequence, mirroring the production reality of
   policies that grow over time without renames. Renaming the map every time it gains a
   `set` clause is operational churn that real networks rarely tolerate.
2. **Capstone composition**: lab-04 (capstone-config) layers further policy onto the same
   structure — community tagging, conditional prepending. A single named map that grows is
   easier to teach as a single policy artifact than three separately-named maps that the
   student must remember to coordinate.

This decision is documented prominently in workbook Section 1 ("Where the Prepend Goes")
and revisited in the Section 5 Task 4 wording, so students notice the naming asymmetry
deliberately rather than mistaking it for a workbook error.

### Two prepends, not three or one
The convention `set as-path prepend 65001 65001` (two prepends, total AS-path length 3
including the natural origin) is the most-used starting point in production. One prepend
(length 2) is often invisible because many backbones see paths several ASes long anyway;
three prepends raise suspicion in route-quality scoring at large transit ASes. The
workbook discusses the tradeoff in Section 1 ("How AS-Path Prepending Steers Inbound
Traffic"); the solution and verification cheatsheet use two prepends throughout.

### Static (not IGP) for ISP-internal loopback reachability
The new L4 (R3↔R5) and L5 (R4↔R6) links inside the ISPs need a way for the iBGP loopback
sessions (10.0.0.3↔10.0.0.5 and 10.0.0.4↔10.0.0.6) to come up. This lab uses **static
routes** (`ip route 10.0.0.5/32 via 10.1.35.2`, etc.), the same pattern lab-00 used for
the CE-CE iBGP underlay. An IGP (OSPF inside each ISP) would be more realistic but adds
configuration weight that is orthogonal to the inbound-TE objective. Static keeps the
ISP-internal-iBGP plumbing minimal and lets the workbook focus on prepend direction and
verification.

### Three faults — one per concept this lab introduces
The three planted faults map to the three new operational risks lab-02 introduces:

1. **Wrong egress for prepend** (Ticket 1) — preference inverts because the prepend was
   added to the primary path's egress instead of the backup's.
2. **Wrong AS in prepend value** (Ticket 2) — neighbor's AS used in the prepend, so
   eBGP loop-prevention at the receiver discards the update entirely; customer prefix
   disappears from ISP-B's BGP table.
3. **Missing next-hop-self on iBGP** (Ticket 3) — R5 sees the prefix in its BGP table
   but it never becomes best-path because the eBGP next-hop is unreachable from inside
   ISP-A.

Faults that depend on later-lab features (community-based steering, MED-with-internal-BGP,
LOCAL_PREF interplay) are deferred to their own labs.
