# Design Decisions — BGP Lab 00: eBGP and iBGP Foundations

## Model gate — 2026-04-27
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Command Compatibility Notes — 2026-04-27

Two commands used in solutions are not in `ios-compatibility.yaml` but were accepted
as standard IOS/XE primitives without running `verify_ios_commands.py`:

- `neighbor X update-source Loopback0` (router-bgp context) — fundamental iBGP loopback
  peering command present in IOS since 11.x; passes on ios-classic, ios-xe, and all
  active platforms in this project.
- `neighbor X next-hop-self` (af-ipv4-bgp context) — fundamental iBGP next-hop override;
  same platform coverage. Present in every IOS version in scope.

Both commands are covered by the ios-compatibility.yaml `router bgp` and
`address-family ipv4` pass markers for context; the specific sub-directives are
table stakes for iBGP functionality.

## OSPF Network Type — 2026-04-27

Did not configure `ip ospf network point-to-point` on Ethernet /24 links.
This matches the project convention established in the OSPF labs (lab-00 through lab-04).
DR/BDR election runs on the broadcast links; no functional issue in a point-to-point
physical topology since the "DR" is simply whichever router wins election, and both
speakers form FULL adjacencies.

## passive-interface Not Used — 2026-04-27

No `passive-interface` statements in OSPF configs. The customer-facing links
(R1↔R2 on 10.1.12.0/24, R1↔R3 on 10.1.13.0/24) and external-peer link
(R5↔R6 on 10.1.56.0/24) are not covered by any OSPF `network` statement,
so OSPF hellos are never sent on them. `passive-interface` is unnecessary.
