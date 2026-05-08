# Design Decisions — Lab 01: TI-LFA

## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Initial build — 2026-04-30

### Progressive chain
Initial configs are exact copies of `lab-00-sr-foundations-and-srgb/solutions/` (IS-IS L2 +
SR-MPLS, SRGB 16000-23999, prefix SIDs 16001-16004). No teardown block needed: TI-LFA and BFD
are purely additive config on top of the existing IS-IS structure; no prior stanzas need to
be removed before the student begins.

### TI-LFA IOS-XR syntax
Two knobs required per IS-IS interface af: `fast-reroute per-prefix` (enables per-prefix FRR)
and `fast-reroute per-prefix ti-lfa` (elevates to TI-LFA mode). Both must be present; omitting
the first while keeping only the second is not valid on IOS-XRv 9000 7.x.

### BFD configuration placement
BFD parameters (`bfd minimum-interval 50`, `bfd multiplier 3`) are placed at the IS-IS
interface level (not under the address-family). `bfd fast-detect` is placed under the
address-family. This matches IOS-XR 7.x CLI hierarchy exactly.

### L5 diagonal repair path
L5 (R1↔R3, Gi0/0/0/2) is the key PQ-node anchor for R2→R3 protection. When L2 (R2↔R3)
fails, R1 is the PQ-node: reachable from R2 via L1 without crossing L2; reaches R3 via L5
without crossing L2. Repair label stack = {16001, 16003}. Without L5, the only repair path
goes via R4 (longer, potentially 3+ labels). Ticket 3 exercises this coverage degradation.

### Topology diagram
Uses bare `<mxGraphModel background="#1a1a2e">` format (not wrapped `<mxfile>`), matching the
project's drawio tooling requirement established when lab-00's `<mxfile>` format failed to
open. Diagonal link L5 is drawn as a straight edge from R1 (top-left) to R3 (bottom-right).
