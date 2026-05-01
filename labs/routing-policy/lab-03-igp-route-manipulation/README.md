# Lab 03 — Route Manipulation for IS-IS and OSPF

OSPF distribute-list, ABR filter-list, prefix-suppression, IS-IS level boundary
and selective L1-to-L2 leaking, XR RPL hierarchical IS-IS filtering.

## Blueprint Coverage

- 3.3 — Troubleshoot route manipulation for IGPs
- 3.3.a — IS-IS (level boundary, selective leaking, RPL distribute-list equivalent)
- 3.3.b — OSPF (distribute-list, filter-list, prefix-suppression)

## Prerequisites

- Lab 02 (`lab-02-rpl-vs-route-maps`) must be completed — this lab chains from its solutions.
- Python 3.9+, `netmiko` installed (`pip install netmiko`)
- EVE-NG lab imported and all 6 nodes started (XR1/XR2 need ~10 min boot time)

## Quick Start

```bash
# 1. Import the EVE-NG topology
#    File → Import → select topology/topology.drawio (export .unl from EVE-NG UI first)

# 2. Push initial configs (lab-02 solutions as baseline)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md — start at Section 5 (Lab Challenge)
```

## Files

```
lab-03-igp-route-manipulation/
├── workbook.md              — full lab guide (all 11 sections)
├── setup_lab.py             — pushes initial-configs/ to all 6 devices
├── README.md                — this file
├── initial-configs/         — lab-02 solutions (starting state for lab-03)
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg  XR1.cfg  XR2.cfg
├── solutions/               — lab-03 full solution configs
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg  XR1.cfg  XR2.cfg
├── topology/
│   ├── topology.drawio      — EVE-NG topology diagram
│   └── README.md            — EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py
    ├── inject_scenario_02.py
    ├── inject_scenario_03.py
    ├── apply_solution.py
    └── README.md
```
