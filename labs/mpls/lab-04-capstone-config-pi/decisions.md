# Build Decisions — MPLS Lab 04 Capstone I (Pi Build)

## Model gate — 2026-05-01
- Difficulty: Advanced
- Running model: pi (coding agent harness)
- Allowed models: claude-opus-4-7
- Outcome: MANUAL OVERRIDE — Building as Pi agent per user request for comparison purposes. The model-gate is designed for Claude Code; this build runs on Pi.

## Workbook gate — 2026-05-01
- Outcome: PASS-AFTER-FIXES
- Items fixed: 1
- Notes: Moved cabling table from Section 2 to Section 3 per lab-assembler contract.

## Compatibility notes — 2026-05-01
- MPLS-specific commands (`mpls label protocol ldp`, `mpls ldp router-id`, `mpls ip`,
  `mpls mtu`, `mpls traffic-eng tunnels`, `ip rsvp bandwidth`, `tunnel mode mpls traffic-eng`,
  `send-label`, `ip explicit-path`, `isis network point-to-point`, `mpls traffic-eng level-2`)
  are marked `unknown` in ios-compatibility.yaml but **verified working** on IOSv 15.9(3)M6
  in labs 00-03. No platform changes required.
- All BGP, IS-IS, and interface commands are `pass` on ios-classic.

## Design decisions — 2026-05-01
- **Capstone I (clean_slate: true).** Initial configs are IP-only from baseline.yaml
  core_topology. No protocol config pre-loaded — student builds everything from scratch.
- **Both explicit paths created** (PE1-via-P1 and PE1-via-P2) in the solution config so
  the student can observe which P router dynamic CSPF picks and select the opposite path
  for the secondary path-option.
- **Three troubleshooting tickets** mapped to 4.1.a (LDP router-id), 4.1.d (next-hop-self),
  and 4.1.e (RSVP bandwidth mismatch).
- **Drawio uses cisco19 shapes** with embedded HTML labels and dark canvas background
  per the current drawio/SKILL.md revision. MPLS domain zone (AS 65100), AS 65101, and
  AS 65102 drawn as dashed semi-transparent regions.
- **Fault injection scripts use find_open_lab()** for auto-discovery — no hardcoded
  DEFAULT_LAB_PATH. PREFLIGHT_FAULT_MARKER for Ticket 2 uses a non-matching UUID string
  because the fault (missing next-hop-self) doesn't produce a positive marker — detection
  relies on SOLUTION_MARKER absence check.
