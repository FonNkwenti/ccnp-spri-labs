# decisions.md — multicast/lab-00-pim-sm-foundations

## Model gate — 2026-05-05
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-haiku-4-5-20251001
- Outcome: PASS

## Workbook gate — 2026-05-05
- Outcome: PASS-AFTER-FIXES
- Items fixed: 5
- Notes: (1) Task 1 wording changed from "do not enable IS-IS on stub segments" to correct passive-interface approach; (2) Section 8 Obj 1 R2 IS-IS block added passive-interface GigabitEthernet0/2 and ip router isis 1 on Gi0/2; (3) Section 8 Obj 1 R4 IS-IS block added passive-interface GigabitEthernet0/1 and ip router isis 1 on Gi0/1; (4) Ticket 1 completely rewritten — fault changed from R3 IS-IS metric inflation (invalid: R3 not on forwarding path) to removal of ip pim sparse-mode from R1 Loopback0 (valid: silently drops inbound PIM Joins to RP); (5) Section 10 Ticket 1 checklist item updated to match new ticket.
