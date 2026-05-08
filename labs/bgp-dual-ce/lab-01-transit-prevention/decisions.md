## Model gate — 2026-04-28
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions

### Filter on eBGP egress, not on CE-CE iBGP
Baseline.yaml objective 3 reads: "Implement outbound route-maps on R1 (toward R2) and R2
(toward R4) permitting only customer-originated prefixes." The first half ("R1 toward R2")
appears to be a baseline-authoring slip — applying the filter outbound on the iBGP session
from R1 toward R2 would prevent ISP-A's prefixes from reaching R2, which restores the
exact routing gap lab-00 was built to close.

After advisor consultation, this lab applies the transit-prevention filter outbound on
each **eBGP** session: R1 toward R3 (10.1.13.2) and R2 toward R4 (10.1.24.2). Reasons:

- **Lab-03 dependency**: lab-03 sets LOCAL_PREF on each CE so each CE prefers its own ISP
  for outbound traffic. For LOCAL_PREF to mean anything, each CE must *see* both ISPs'
  prefixes. Filtering iBGP would strip ISP-A's prefixes from R2's BGP table (and ISP-B's
  from R1's), making the lab-03 path-selection objective impossible.
- **Operational correctness**: the customer's commercial obligation is "do not act as
  transit between providers." The cleanest expression of that policy is at the eBGP egress
  — the boundary where the customer AS hands routes to a provider. Filtering at the
  iBGP session prevents the *symptom* (a route the second CE could re-advertise) but does
  not articulate the *policy* at the right layer.
- **Ticket 1 demonstrates the trap**: the planted fault places the filter on the iBGP
  session and shows the resulting routing gap on R1. The lab's troubleshooting section
  reinforces the design choice.

The original baseline objective wording is preserved as Ticket 1's planted fault: when a
student builds the filter on the iBGP session, they reproduce the baseline-text mistake
and observe its consequences. The lab's correct answer (eBGP egress) is the
operational reality.

### `permit 192.168.1.0/24 le 32`, not the exact /24
Lab-03 originates 192.168.1.0/25 and 192.168.1.128/25 as more-specifics for selective
prefix advertisement. A `permit 192.168.1.0/24` (without `le 32`) accepts only the exact
/24 and would silently drop the lab-03 more-specifics, breaking the inbound-TE objective
without any visible filter mismatch in the configuration.

The `le 32` qualifier permits the /24 plus any longer prefix within it. Lab-03's /25s pass
through the lab-01 filter unchanged. This is a forward-compatibility choice made now to
avoid a confusing failure mode mid-lab-03.

### Route-map (not bare prefix-list) outbound
A simple `neighbor 10.1.13.2 prefix-list TRANSIT_PREVENT out` would work for lab-01 and is
strictly less typing. The lab uses `route-map TRANSIT_PREVENT_OUT permit 10` with a
`match ip address prefix-list` clause because:

- Lab-02 adds `set as-path prepend 65001` to outbound updates from R2 toward R4. `set
  as-path prepend` requires a route-map; it cannot be expressed as a prefix-list directive.
- Lab-04 (capstone) layers prefix filtering, AS-path prepending, and LOCAL_PREF setting
  into a single coherent outbound policy. Building the route-map skeleton in lab-01 means
  later labs add `set` clauses to an existing structure rather than replacing the policy
  framework.

### Three faults — all about filter placement and direction
The fault catalogue is bounded by the things this lab introduces: a prefix-list, a
route-map, and the binding directive (`route-map … out`). The three planted faults
exercise the three operationally common filter-placement mistakes:

1. **Filter applied to the wrong session** (Ticket 1) — bound to iBGP instead of eBGP.
2. **Route-map exists but not bound** (Ticket 2) — the policy framework is correct, but
   never attached to the neighbor.
3. **Bound in the wrong direction** (Ticket 3) — `in` instead of `out`, so outbound
   updates are unfiltered and the leak persists while inbound updates are stripped.

Faults that depend on later-lab features (AS-path prepend direction, LOCAL_PREF
mis-direction) are deferred to their own labs.
