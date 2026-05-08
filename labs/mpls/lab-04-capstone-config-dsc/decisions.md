# Lab 04 â€” Capstone I (Config) â€” Decisions

## Model gate â€” 2026-05-04
- Model: deepseek-v4-pro
- Gate: forced (`--force-model` override)
- Note: deepseek-v4-pro is not in the Advanced tier allowed_models list; build proceeded under user override.

## Workbook gate â€” 2026-05-04
- Outcome: PASS-AFTER-FIXES
- Items fixed: 4
- Notes: Device Inventory missing RAM column (added 512 MB per eve-ng-constraints.md), raw IOS syntax in Section 4 IS list (`no ip domain-lookup`, `no shutdown`) and Section 5 Task 2 (`mpls ip`, `mpls mtu override 1508`) replaced with plain English, missing Verification Commands subsection in Section 7 added.
