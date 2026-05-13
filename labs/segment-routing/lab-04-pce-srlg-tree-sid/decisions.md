# Design Decisions — Lab 04: PCE Path Computation, SRLG, and Tree SID

## Model gate — 2026-04-30

- Difficulty: Advanced
- Running model: claude-sonnet-4-6 (system-prompt declaration)
- Allowed models: claude-opus-4-7
- Recommended: claude-opus-4-7
- Outcome: OVERRIDDEN via --force-model
- Note: User switched runtime to Opus 4.7 mid-session via `/model` and set effort to medium. Policy advises `high` for Advanced; build proceeded balanced per user instruction.

## Initial build — 2026-04-30

### PCE reachability via R2-redistributed static (Option A)
PCE has only one physical link (L6 to R2). Three approaches were considered for PCC↔PCE
connectivity:
- **A. Static on R2 + redistribute into IS-IS (chosen).** R2 owns a `10.0.0.99/32` static
  via 10.1.29.99 and redistributes only that prefix into IS-IS via a route-policy that
  matches a one-entry prefix-set. This keeps PCE strictly out of IS-IS while letting all
  core routers route to it. PCE has a `10.0.0.0/24` static via 10.1.29.2 covering all
  core loopbacks.
- **B. Run IS-IS L2 on PCE's Lo0 + L6.** Cleaner ASIC-level, but contradicts the spec
  decision: "PCE is a peer, not a core router. The PCE runs BGP-LS with R2 only - it does
  not participate in IS-IS." Rejected.
- **C. Static on every core router pointing at R2's L1/L4/L5 next-hop.** Brittle, doesn't
  scale, and fails closed when an R1↔R2 link goes down. Rejected.

### Disjoint-path constraint type: link (not srlg)
Lab uses `disjoint-path group-id 1 type link` for the color-40/41 pair, not `type srlg`.
Reason: with five core links and only ~5 SRLG groups (one per link), `type srlg` collapses
to `type link` anyway in this small topology - both produce identical results. `type link`
keeps the workbook's "what is being constrained" pedagogy clear before the SRLG concept
is introduced as a separate Task 5. The capstone (lab-06) exercises `type link-or-srlg`
on a more complex topology.

### Tree SID xrv9k caveat
Per spec Section "Tree SID (4.3.e) configured with a behavioral-gap caveat", the workbook
documents that xrv9k 24.3.1 converges Tree SID control plane (PCEP delegation, p2mp policy
state) but does not perform ASIC-level P2MP packet replication in QEMU. Verification stops
at `show segment-routing traffic-eng p2mp policy`. A short callout box in Section 5 Task 7
makes this explicit so students don't waste time hunting for non-existent data-plane state.

### No teardown block needed
Lab-04 chains progressively from lab-03 with surgical additions only:
- R2 gets a new physical interface (Gi0/0/0/2 = L6, IP-only) - additive, no negation needed.
- PCE is a brand-new node with IP-only stub initial-config - no prior state to remove.
- R1, R3, R4 carry forward their lab-03 solutions verbatim and add PCC/SRLG blocks.
Lab-03's mapping-server teardown block already removed the lab-02 fiction; nothing else
in lab-03's solution conflicts with lab-04's objectives.

### Three troubleshooting tickets aligned to objective failure modes
- **Ticket 1 (R2 metric-style narrow)**: Targets the "incomplete TE attribute" failure
  mode the spec calls out as the primary 4.3.c trap. BGP-LS still flows, but TE/SRLG
  sub-TLVs are absent, so any disjoint or TE-metric policy fails.
- **Ticket 2 (R1 PCC pointing at 10.0.0.98)**: One-character typo, simulating a
  copy-paste bug. The PCC stays in TCP-connect retry and the color-30 policy never
  computes. Diagnosed by walking `show segment-routing traffic-eng pcc ipv4 peer` on R1
  vs `show pce session` on PCE.
- **Ticket 3 (R2 L1 SRLG mismatched)**: Tests SRLG group-naming hygiene. R2 advertises
  Gi0/0/0/0 as SRLG_L4 instead of SRLG_L1; PCE sees an asymmetric link and cannot satisfy
  any disjoint computation. Distinct from a "missing SRLG" fault - the group exists, just
  with the wrong name on one endpoint.

### Section 9 prerequisite
Same pattern as labs 01-03: fault scripts assume the lab is in solution state. The
workflow shown at the top of Section 9 reset-to-initial first via `setup_lab.py`, then
`apply_solution.py` to bring the lab up to lab-04 solution state, then inject. Between
tickets, `apply_solution.py` restores cleanly without needing a full reset.
