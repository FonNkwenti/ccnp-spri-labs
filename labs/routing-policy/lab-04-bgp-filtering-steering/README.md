# Lab 04 — BGP Route Filtering and Traffic Steering

BGP inbound/outbound filtering, aggregate-address, LOCAL_PREF, AS-path prepend, MED,
conditional advertisement, and XR RPL community+prepend equivalence.

## Blueprint Coverage

- 3.4 — Troubleshoot route manipulation for BGP
- 3.4.a — Route filtering (prefix-list, as-path, community, RPL)
- 3.4.b — Traffic steering (LOCAL_PREF, MED, AS-path prepend, conditional advertisement)

## Prerequisites

- Lab 03 (`lab-03-igp-route-manipulation`) must be completed — this lab chains from its solutions.
- Python 3.9+, `netmiko` installed (`pip install netmiko`)
- EVE-NG lab imported and all 6 nodes started (XR1/XR2 need ~10 min boot time)

## Quick Start

```bash
# 1. Import the EVE-NG topology
#    File → Import → select topology/topology.drawio (export .unl from EVE-NG UI first)

# 2. Push initial configs (lab-03 solutions as baseline)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md — start at Section 5 (Lab Challenge)
```

## Files

```
lab-04-bgp-filtering-steering/
├── workbook.md              — full lab guide (all 11 sections)
├── setup_lab.py             — pushes initial-configs/ to all 6 devices
├── README.md                — this file
├── initial-configs/         — lab-03 solutions (starting state for lab-04)
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg  XR1.cfg  XR2.cfg
├── solutions/               — lab-04 full solution configs
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
