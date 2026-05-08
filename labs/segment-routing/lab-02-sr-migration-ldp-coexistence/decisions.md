# Design Decisions — Lab 02: SR Migration — LDP Coexistence, Mapping Server, SR-Prefer

## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Initial build — 2026-04-30

### Progressive chain — no teardown needed
Initial configs are exact copies of `lab-01-ti-lfa/solutions/` (IS-IS L2 + SR-MPLS + TI-LFA + BFD).
LDP and the SR mapping server are purely additive config; no prior stanzas need to be removed
before the student starts. IOS-XR config application is additive — enabling `mpls ldp` and
`segment-routing mapping-server` does not conflict with or require removal of any existing block.

### LDP interface scope
LDP is enabled on all five core links (L1-L5). R1 participates in L1 (Gi0/0/0/0), L4 (Gi0/0/0/1),
and L5 (Gi0/0/0/2). R2 participates in L1 and L2. R3 participates in L2, L3, and L5. R4
participates in L3 and L4. This matches the IS-IS adjacency scope exactly — LDP and IS-IS run
on identical interface sets.

### Mapping server SID allocation
R1's mapping server allocates index 50 with range 100 for 192.0.2.0/24. Index 50 gives absolute
label 16050 (SRGB_base 16000 + 50), which is within the full SRGB 16000-23999. The range of 100
covers individual /32s within the /24 for future use. The /24 itself gets index 50.

### Troubleshooting ticket design
Three tickets were chosen to cover one concept each:
- Ticket 1 (R3 SRGB shrink): SRGB conflict is the most common mapping-server failure mode.
  Shrinking R3's SRGB to 16000-16049 puts the mapping entry label 16050 out of range.
  Prefix SIDs 16001-16004 remain within 16000-16049 so IS-IS adjacencies are unaffected —
  the fault is isolated to the mapping server functionality.
- Ticket 2 (R2 sr-prefer removed): Directly exercises the sr-prefer behavioral difference.
  Without sr-prefer, LDP label is used for the mapping-server prefix; with it, SR wins.
- Ticket 3 (R4 LDP interface missing): Models a common operator error where an interface
  was accidentally removed from the LDP process during a change window.

### Section 9 workflow prerequisite
Same pattern as lab-01: inject scripts require the solution state (LDP running, mapping server
configured, sr-prefer active). The initial-configs have none of these. Section 9 uses
`apply_solution.py` as the reset command, not `setup_lab.py`.
