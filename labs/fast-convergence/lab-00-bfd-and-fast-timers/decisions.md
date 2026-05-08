## Model gate — 2026-05-05
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Workbook gate — 2026-05-05
- Outcome: PASS-AFTER-FIXES
- Items fixed: 1
- Notes: Task 9 body contained a show command reference and raw IOS syntax (`bfd interval 150 min_rx 150 multiplier 3`); rewritten to plain-language description per Section 5 contract

## Advisor review — 2026-05-05
- Outcome: FIXES APPLIED
- Items fixed: 4
- Notes:
  1. solutions/R1.cfg — `next-hop-self` moved from eBGP neighbor (10.0.0.5) to iBGP neighbors (10.0.0.2, 10.0.0.3, 10.0.0.4); applying it to the eBGP peer rewrites the next-hop in updates sent TO R5 (no effect) rather than inward to iBGP peers
  2. solutions/R3.cfg — same fix: `next-hop-self` moved from 10.0.0.5 to iBGP neighbors (10.0.0.1, 10.0.0.2, 10.0.0.4)
  3. workbook.md Task 2 body — rewritten to clarify that `next-hop-self` applies on iBGP neighbors, not the eBGP peer
  4. workbook.md Section 8 Task 2 R1 solution + Section 7 cheatsheet — updated `address-family ipv4` blocks to show `next-hop-self` on iBGP neighbors (10.0.0.2/3/4), not on 10.0.0.5
