# Build Decisions — isis/lab-00-single-level-isis

## Model gate — 2026-04-28

- Difficulty: Foundation
- Running model: claude-opus-4-7
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS (Opus is allowed for the Foundation tier; the policy lists Sonnet as the
  recommended model — Opus is over-tier here but not prohibited)

## Decision 1 — All three routers placed in area 49.0001 (override of topic-wide baseline)

`labs/isis/baseline.yaml` defines a topic-wide topology in which R3 sits in area `49.0002`
with `is-type level-1-2`, and link L2 (R2↔R3) is L2-only. Lab-00's first objective,
however, says "Configure NET addressing and L1-only IS-IS across R1, R2, R3 (all in area
49.0001 temporarily — labs 01+ move R3 to 49.0002)." The lab-specific objective wins for
lab-00:

- R1, R2, R3 all use NETs of the form `49.0001.0000.0000.000X.00`
- All three routers run `is-type level-1`
- Both Ethernet links operate as L1 broadcast circuits with DIS election

Lab-01 will perform the move (NET on R3 → `49.0002.…`, promote R2/R3 to `level-1-2`,
turn L2 into an L2-only adjacency). The next builder should NOT "fix" lab-00 to match
the baseline — the override is intentional and pedagogically required so a single LSDB
can be examined without L2 / ATT-bit noise.

## Decision 2 — IPv4-only in lab-00 (no multi-topology, no IPv6)

The baseline includes IPv6 NETs and v6 subnets for every device, but lab-00's
objectives say nothing about IPv6 and lab-02 introduces multi-topology IS-IS for the
first time. Keeping lab-00 IPv4-only:

- Lets students focus on NET semantics and the L1 LSDB without v6 SPF noise
- Matches the OSPF-topic counterpart (lab-00 there is OSPFv2 only; OSPFv3 starts in
  lab-02)
- Preserves a clean migration path: lab-02 simply adds `ipv6 unicast-routing` and
  `address-family ipv6 multi-topology` on top of these solutions

`metric-style wide` is configured in lab-00 even though the metrics produced in this
lab still fit in narrow form, because mixing narrow and wide LSPs across the topic
breaks lab-02. This is a one-line choice with zero downside in lab-00.

## Decision 3 — Three pedagogically distinct fault scenarios

The baseline does not specify lab-00's fault scenarios. Selected three faults that map
1:1 to the three core IS-IS-specific concepts in the lab and that produce visibly
different symptoms — so a student cannot fix one ticket and accidentally clear another:

| Ticket | Concept | Fault | Symptom |
|--------|---------|-------|---------|
| 1 | NET addressing | Area-ID typo on R3 (`49.0099` instead of `49.0001`) | R3 stuck in INIT on R2; routes vanish |
| 2 | IIH mechanics | `isis hello-interval 1` + `hello-multiplier 2` on R1 Gi0/0 | R1↔R2 adjacency flaps continuously |
| 3 | is-type | `is-type level-2-only` planted on R2 | R2 has zero neighbours; both R1 and R3 stuck in INIT |

Avoided scenarios that better fit later labs:

- `metric-style narrow` mismatch — exclusively lab-02 territory (multi-topology IPv6
  needs wide metrics; introducing narrow here pre-empts that lesson)
- ATT-bit / L1/L2 leak issues — lab-01 territory (lab-00 has no L1/L2 routers)
- MTU mismatches on the Ethernet circuit — lab-04 (capstone troubleshooting)

## Decision 4 — Single process tag `CORE` across all routers

The IS-IS process tag is locally significant; using the same tag (`CORE`) on every
router carries no protocol-level meaning but improves operational consistency for
copy-paste verification commands and for the troubleshooting tickets, which can refer
to `router isis CORE` unambiguously. This matches the convention established in
`labs/ospf/lab-00` (`router ospf 1`).
