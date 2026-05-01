# Lab 00 — Decisions and Build Provenance

## Model gate — 2026-04-28

- Difficulty: Foundation
- Running model: claude-opus-4-7
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Lab type and structure

This is the first lab in the routing-policy chapter and uses the **progressive** type.
Per the lab-assembler skill: the first progressive lab ships **IP-only initial-configs**
(no routing protocols), and the workbook walks the student from interfaces-up through the
full topic. Solutions/ contains the complete reference configuration that
`apply_solution.py` can push if a student needs to skip ahead or recover.

## Topology decisions

- The triangle (R1↔R2, R2↔R3, R1↔R3 via L5) gives every iBGP peer a working IGP path
  without any dependency on R4. If R4 (or either eBGP session) goes down, iBGP convergence
  is unaffected — exactly the property a routing-policy lab needs so that policy effects
  are observable in isolation.
- R2 deliberately has no eBGP. Keeping it pure-transit makes the lab's filter
  demonstrations cleaner: only R1 and R3 see R4's prefixes directly; R2's view of those
  prefixes always comes via iBGP.
- Both OSPF area 0 and IS-IS L2 run on the same three core interfaces. The redundancy is
  pedagogical — lab-01 needs OSPF↔IS-IS redistribution, and lab-00 leaves both protocols
  primed and converged so lab-01's first step is a single `redistribute` command, not
  bringing IS-IS up from scratch.

## Policy artifact decisions

All ACLs, prefix-lists, and route-maps live on R1. The reasons:

1. **Visibility** — a single `show route-map` and `show ip prefix-list` on R1 walks
   every artifact in the lab. Splitting them across devices forces students to chase.
2. **Symmetric multihoming** — R3 has an unfiltered eBGP session to R4. When R1 drops
   172.20.5.0/24, students see the prefix is **still installed via R3 over iBGP**. That
   side-by-side is the core teaching moment: filters are scoped, not global.
3. **Implicit deny demo** — keeping all sequences on R1 lets the troubleshooting
   scenario remove a single sequence and produce a clean, single-symptom outage.

The two prefix-lists (`PFX_R4_LE_24` ge/le, `PFX_R4_LO2_EXACT` exact) and the two ACLs
(standard `10`, extended `ACL_EXT_R4_LO2`) are all referenced by either the live
`FILTER_R4_IN` map or the demonstration-only `DEMO_*` maps. None are dead config — every
artifact has either a live application or a workbook task that references it.

## Filter target choice

R4 advertises two prefixes:

- `172.20.4.0/24` — Lo1, **accepted** by R1 (matches `PFX_R4_LE_24`, hits seq 20 permit).
- `172.20.5.0/24` — Lo2, **filtered** by R1 (matches `PFX_R4_LO2_EXACT`, hits seq 10 deny).

Both prefixes are inside `172.20.0.0/16`, so the ge/le prefix-list in seq 20 is a true
catch-all for the /24s — not a coincidence that happens to work. Students who change the
ge/le boundary (inject scenario 02) immediately see the asymmetry.

## Fault-injection design

Three injects, all on R1 only, all reversible by `apply_solution.py --node R1`:

| # | Fault location | Class | Why this fault |
|---|----------------|-------|----------------|
| 1 | route-map FILTER_R4_IN | implicit deny dropping unmatched | Teaches the most common route-map mistake: forgetting the trailing `permit` after a `deny` sequence. |
| 2 | ip prefix-list PFX_R4_LO2_EXACT | ge/le boundary error | Teaches the semantic difference between exact match and `ge X le X`. |
| 3 | neighbor 10.1.14.4 route-map ... | wrong direction (out vs in) | Teaches that `in` and `out` are not interchangeable — wrong direction is silent. |

Each fault produces a distinct symptom on `show ip bgp neighbors 10.1.14.4 routes`. The
scripts are kept on R1 because the topology gives R1 the most policy surface; spreading
faults to R2/R3 would dilute the teaching focus for a Foundation-tier lab.

## Out of scope (deliberate)

- **Communities, set local-pref, set metric** — lab-01 and lab-04 cover these.
- **AS-path regex** — lab-01.
- **RPL** — lab-02.
- **Redistribution between OSPF and IS-IS** — lab-01 (with tag-based loop prevention).
- **MED, prepend, conditional advertisement** — lab-04.

The `DEMO_REDIST` map is *defined* on R1 but **not applied**. The workbook treats it as a
read-only reference that explains the redistribute-vs-neighbor distinction. Applying real
redistribution between BGP and OSPF here would create state churn that lab-01 should
introduce in a controlled way.
