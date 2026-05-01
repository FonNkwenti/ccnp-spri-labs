# Lab 00 — Route-Maps, Prefix-Lists, and ACL Matching

> Foundation lab for the routing-policy topic. 4 routers. 60 minutes.

## Quick Reference

| Item | Value |
|------|-------|
| Difficulty | Foundation |
| Type | Progressive |
| Devices | R1, R2, R3 (AS 65100); R4 (AS 65200) |
| IGPs | OSPF area 0 + IS-IS L2 (R1/R2/R3) |
| BGP | iBGP full-mesh in AS 65100; eBGP R1↔R4 and R3↔R4 |
| Filter target | 172.20.5.0/24 (R4 Lo2) inbound on R1 |

## Lab Setup

```bash
# Push IP-only baseline (interfaces only, no routing protocols)
python setup_lab.py --host <eve-ng-ip>

# Push complete solution (after working through the workbook)
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

## Files

```
lab-00-route-maps-foundations/
├── README.md                     ← this file
├── workbook.md                   ← the 11-section student workbook
├── decisions.md                  ← build provenance and design notes
├── meta.yaml                     ← provenance stamp
├── setup_lab.py                  ← pushes IP-only initial-configs
├── topology/
│   ├── topology.drawio           ← EVE-NG diagram
│   └── README.md                 ← topology and link reference
├── initial-configs/              ← IP addressing only
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg
├── solutions/                    ← full configs implementing all tasks
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg
└── scripts/fault-injection/
    ├── README.md                 ← fault-injection ops doc
    ├── apply_solution.py         ← restore to clean state
    ├── inject_scenario_01.py     ← implicit-deny silent drop
    ├── inject_scenario_02.py     ← prefix-list ge/le wrong
    └── inject_scenario_03.py     ← route-map applied outbound (wrong direction)
```

## Design Summary

- R1 carries every policy artifact (ACLs, prefix-lists, route-maps) so a single `show route-map` and `show ip prefix-list` walks the whole lab.
- R4's Lo2 (172.20.5.0/24) is the canonical filter target. The same prefix is **still accepted** at R3 — students see the iBGP path survive, which makes the inbound-filter scope crystal clear.
- The triangle (R1-R2-R3) plus the diagonal L5 ensures every iBGP peer has a working IGP next-hop without depending on R4.
