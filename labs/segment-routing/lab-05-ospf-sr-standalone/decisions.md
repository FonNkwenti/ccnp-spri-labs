# Design Decisions — lab-05-ospf-sr-standalone

## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## IOS-XR command compatibility — 2026-04-30

The `ios-compatibility.yaml` reference file does not include an `xrv9k` platform column.
All IOS-XR commands used in this lab (OSPF + SR: `router ospf`, `segment-routing mpls`,
`prefix-sid index N`, `segment-routing global-block`, `network point-to-point`) are
therefore recorded as `unknown` in the compatibility check. They are verified by
cross-reference with labs 00-04 in this same topic, which use the identical IOS-XRv 9000
platform with confirmed working IS-IS SR commands. The OSPF SR command set is well-established
IOS-XR 7.x syntax; no platform substitution was required.

## Standalone lab design — 2026-04-30

Lab-05 is `type: standalone` with `clean_slate: true`. Initial configs are generated from
`baseline.yaml core_topology` IP addressing only — no IS-IS, no LDP, no SR from prior labs.
This is intentional: the pedagogical goal is to prove that OSPF SR works identically to
IS-IS SR in isolation. The end-state of lab-05 does not feed into lab-06 (capstone uses
IS-IS, not OSPF, and regenerates from clean-slate anyway).

## Network type: point-to-point — 2026-04-30

All OSPF core interfaces configured as `network point-to-point` to eliminate DR/BDR election
overhead. This matches SP practice for two-router /24 links. The labs do not require DR/BDR
functionality, and point-to-point adjacency formation is faster and more predictable.
