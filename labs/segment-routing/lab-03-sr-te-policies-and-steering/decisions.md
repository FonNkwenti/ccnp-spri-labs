# Design Decisions — Lab 03: SR-TE Policies, Constraints, and Automated Steering

## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Initial build — 2026-04-30

### Mapping server teardown (Option A)
Lab-02's R1 had a mapping server advertising index 50 for 192.0.2.0/24 — a fiction because
no real router owned that prefix. Lab-03 introduces CE1 (AS 65101) as the real owner of
192.0.2.0/24, advertising it via eBGP. Keeping the mapping server would create a conflict:
two SID advertisement sources for the same prefix. Per SKILL.md teardown rules, R1's
initial-config includes `no mapping-server` under `segment-routing` and removes
`segment-routing prefix-sid-map advertise-local` from IS-IS. The teardown is applied at
initial-config time, not via a separate script, because it is always required before any
lab-03 task can proceed.

### Color community source: R3 attaches, not CE2
IOSv 15.9 does not support `set extcommunity color` (RFC 9012 type 0x030B). This command
is an SR-TE-specific IOS-XR extension. CE2 is IOSv, so the color community must be
attached by R3 (IOS-XR) via RPL. R3's `RP_CE2_IN` policy applies
`set extcommunity color COLOR_10 additive` to all prefixes received from CE2. This means
the community is added at the PE as a local policy action — exactly how real SP deployments
work (CEs typically do not participate in SR-TE color signaling). The workbook explains
this as the standard operational model.

### IOS-XR TE metric syntax
baseline.yaml objective text references `mpls traffic-eng / interface X / administrative-weight N`
which is IOS-XE syntax. On IOS-XR 7.x (xrv9k), the correct syntax for SR-TE CSPF TE metric
override is `segment-routing / traffic-eng / interface X / metric N`. This sets the metric
used by local CSPF when `dynamic metric type te` is configured. The workbook uses the
IOS-XR syntax in all examples and solution blocks. A callout note explains the syntax
difference for students who have IOS-XE background.

### Affinity scheme
Two affinities are defined (consistent across all routers via affinity-map):
- `RED` (bit-position 0): applied to L3 (R3↔R4) on both endpoints — R3 Gi0/0/0/1 and R4 Gi0/0/0/0
- `BLUE` (bit-position 1): applied to L2 (R2↔R3) on both endpoints — R2 Gi0/0/0/1 and R3 Gi0/0/0/0

COLOR_20 uses `exclude-any RED` to avoid the R4 transit path (L4+L3). The default IGP
shortest path R1→R3 uses L5 (direct) or L1+L2. With exclude-any RED, R1→R4→R3 is always
disallowed regardless of IGP metric. This demonstrates the intent of affinity constraints:
policy-driven path avoidance independent of metric topology.

### Segment-list EXPLICIT_R4_R3
The explicit SID list uses node SIDs (loopback addresses) not adjacency SIDs. IOS-XR CSPF
resolves `address ipv4 10.0.0.4` to label 16004 (prefix SID index 4) and
`address ipv4 10.0.0.3` to label 16003 (prefix SID index 3). This forces the path
R1 → R4 → R3 regardless of IGP metrics. Node SIDs are preferred over adjacency SIDs in
segment-lists because they survive individual link failures (ECMP and TI-LFA still apply
within the forced R4→R3 hop).

### ODN template alongside static policies
Both a static `policy COLOR_10` (for tasks 2-3) and an `on-demand color 10` template (for
task 6) are present in the solution. When a BGP prefix arrives with color:10 and
next-hop 10.0.0.3, IOS-XR matches the static policy first (same color + endpoint). The ODN
template serves as the dynamic instantiation path if a different endpoint is steered via
color 10. This dual presence is intentional and does not cause conflicts.

### Troubleshooting ticket design
Three tickets with distinct fault categories:

- **Ticket 1 (R1 RP_R3_IN strips color:10)**: Tests automated-steering diagnosis.
  `delete extcommunity in COLOR_10` is added to RP_R3_IN. Result: 198.51.100.0/24 arrives
  at R1 without color community → BGP next-hop resolution uses IGP path, not SR-TE policy.
  Student diagnoses via `show bgp 198.51.100.0/24` (no color community in extended-community
  attribute) and fixes by removing the delete action.

- **Ticket 2 (R4 Gi0/0/0/0 missing RED affinity)**: Tests affinity-constraint diagnosis.
  Without RED on R4's L3 endpoint, CSPF cannot consistently enforce the exclude-any RED
  constraint — R4's side of L3 looks affinity-free, so CSPF may route through it.
  Student diagnoses via `show segment-routing traffic-eng policy color 20` (SID list includes
  R4) vs expected SID list, traces back to missing affinity on R4, and fixes.

- **Ticket 3 (R3 RP_CE2_IN missing set extcommunity action)**: Tests color-attachment
  diagnosis. Without the `set extcommunity color COLOR_10 additive` action, 198.51.100.0/24
  propagates to R1 without any color community. Functionally identical symptom to Ticket 1
  but the fault is at R3 inbound from CE2, not R1 inbound from iBGP. Student must distinguish
  between "color stripped at R1" vs "color never attached at R3" using `show bgp` on both
  routers to localize the fault.

### Section 9 prerequisite
Same pattern as lab-01 and lab-02: fault injection scripts require the solution state
(SR-TE policies up, BGP sessions established, color community attached by R3).
Initial-configs have none of this. Section 9 uses `apply_solution.py` as the reset
command. `setup_lab.py --reset` restores initial-configs only.

## Rebuild — 2026-04-30

### Reason for rebuild
Previous build had major structural violations in workbook.md: incorrect section names
(Overview, Topology, Prerequisites, Lab Setup instead of the required Concepts & Skills
Covered, Topology & Scenario, Hardware & Environment Specifications, Base Configuration),
missing Table of Contents, and missing Device Inventory + Loopback Address tables in
Section 3. All lab files were deleted and rebuilt from scratch following lab-assembler
SKILL.md exactly.

## Model gate — 2026-04-30 (rebuild)
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS
