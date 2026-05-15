# Design Decisions — Lab 03 (3-Node Variant): SR-TE Policies, Constraints, and Automated Steering

## Model gate — 2026-05-14
- Difficulty: Intermediate
- Running model: claude-opus-4-7
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Variant Design — 2026-05-14

### R2 removal and topology compression (Option A — spec-driven)
The standard lab-03 requires 4× XRv 9000 (64 GB guest RAM) which exceeds a 48 GB EVE-NG
VM. Removing R2 reduces the core to 3× XRv 9000 (48 GB) — the maximum that fits within the
VM. L1 (R1↔R2) and L2 (R2↔R3) are deleted along with R2. L3, L4, L5, L7, and L8 are
unchanged from the original. The reduction from 7 links to 5 links simplifies the topology
without removing any path-decision capability: L4+L3 (R4 transit) and L5 (direct) provide
two distinct R1→R3 paths, which is the minimum needed for SR-TE to be meaningful.

### IS-IS metric 30 on L5 (spec-driven)
The spec mandates L5 IS-IS metric = 30 while L3 and L4 remain at the default 10. This
produces IGP shortest path R1→R3 = R1→R4→R3 (10+10=20) rather than R1→R3 via L5 direct
(30). Without this metric rebalancing, the IGP would prefer the diagonal L5 (metric 10)
and Task 4's affinity constraint would have no visible effect — both IGP shortest and
CSPF-with-constraint would select L5 direct, eliminating the before/after comparison that
is the core learning objective.

Applied under `address-family ipv4 unicast` on both R1 Gi0/0/0/2 and R3 Gi0/0/0/2.

### LDP removal (standalone variant)
The standard lab-03 chains from lab-02 and carries LDP for SR↔LDP coexistence. The 3-node
variant is standalone — it does not chain from lab-02, and the spec's pre-loaded list
does not include LDP. Removing LDP simplifies the configs without losing any 4.3.a/4.3.b
blueprint coverage. `segment-routing mpls sr-prefer` is also removed (it is a no-op
without LDP).

### BLUE affinity removal
R2 and L2 are gone, so BLUE affinity (originally on L2 R2↔R3) has no link to tag. Per the
spec, BLUE is removed entirely from the affinity-map. Only RED remains — tagged on L3
(R3↔R4) at both endpoints. The affinity-map on all nodes defines only `RED bit-position 0`.
This keeps the config minimal while still demonstrating the full affinity workflow.

### TE metric 1000 on R1 Gi0/0/0/1 (not Gi0/0/0/0)
The standard lab applies TE metric 1000 to R1's L1 interface (Gi0/0/0/0 toward R2). In the
variant, R1 has no Gi0/0/0/0. Per spec, the TE metric is applied to R1 Gi0/0/0/1 (L4
toward R4). This produces the same pedagogical outcome: COLOR_30 using TE metric avoids
the high-cost link, while COLOR_10 using IGP metric still prefers it. The specific
numbers differ (TE cost L4=1000 vs IGP cost L4=10) but the contrast is preserved.

### Color community source: R3 attaches, not CE2
Identical reasoning to the standard lab. IOSv 15.9 (CE2) has no `set extcommunity color`
support. R3 (IOS-XR) attaches the color:10 extended community via its `RP_CE2_IN` inbound
route policy. This follows the standard SP operational model where color communities are
a PE function, not a CE function.

### Segment-list EXPLICIT_R4_R3
Uses node SIDs (`index N mpls label XXXXX`), not `address ipv4` syntax. Verified on
XRv 9000 24.3.1: `index N address ipv4 X.X.X.X` is rejected. The SID list `[16004, 16003]`
is unchanged from the standard lab — R4 still exists as a waypoint.

### BFD at interface level, not inside address-family
Verified on XRv 9000 24.3.1: `bfd fast-detect` inside IS-IS interface address-family is
not supported. BFD is configured at the IS-IS interface level:
```
interface GigabitEthernet0/0/0/1
 point-to-point
 bfd minimum-interval 50
 bfd multiplier 3
```

### Troubleshooting ticket design
Three tickets with distinct fault categories, all adapted to the 3-node topology:

- **Ticket 1 (R1 RP_R3_IN strips color:10)**: Identical to standard lab. `delete extcommunity
  in COLOR_10` is injected into RP_R3_IN. Pre-flight validates the policy is in known-good
  state by checking for `pass`. Target: R1.

- **Ticket 2 (R4 Gi0/0/0/0 missing RED affinity)**: Identical mechanism to standard lab
  but without the BLUE context. `no affinity` removes the RED tag from R4's L3 endpoint.
  Pre-flight checks `show segment-routing traffic-eng interface GigabitEthernet0/0/0/0`
  for `name RED`. Target: R4.

- **Ticket 3 (R3 RP_CE2_IN missing set extcommunity)**: Identical to standard lab. The
  `set extcommunity color COLOR_10 additive` line is removed. Pre-flight checks for
  `set extcommunity color`. Target: R3.

### ODN template alongside static policies
Same design as standard lab. Both a static `policy COLOR_10` and an `on-demand color 10`
template exist in R1's solution config. When a BGP prefix arrives with color:10 and
next-hop 10.0.0.3, the static policy (same color + endpoint) matches first. The ODN
template provides the dynamic instantiation path.

### File structure
Identical to `lab-03-sr-te-policies-and-steering/`. Every file from the standard lab
has a 3-node counterpart. The only file absent is `initial-configs/R2.cfg` and
`solutions/R2.cfg` — R2 has no role in this variant.
