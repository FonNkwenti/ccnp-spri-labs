# BGP Lab 05 — BGP Communities and FlowSpec

BGP community tagging, well-known communities, SoO loop prevention, and BGP FlowSpec
traffic engineering across a 7-router three-AS SP topology.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.5.i | BGP Communities — standard, well-known, extended (SoO) |
| 1.5.j | BGP FlowSpec — NLRI propagation, IOS-XE enforcement |

## Prerequisites

- Completed lab-04 (Route Dampening and Dynamic Neighbors) or loaded from initial-configs
- Python 3.8+, `netmiko` library
- R7 (CSR1000v) imported into EVE-NG and started

## Quick Start

```bash
# 1. Import the lab topology
#    File > Import > select labs/bgp/lab-05-communities-flowspec.unl in EVE-NG UI

# 2. Start all nodes, then push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook
workbook.md
```

## Files

```
lab-05-communities-flowspec/
├── workbook.md              # Student lab guide (11 sections)
├── setup_lab.py             # Push initial configs to all 7 nodes
├── README.md                # This file
├── decisions.md             # Design and build decisions
├── initial-configs/         # Pre-loaded state (chained from lab-04 + R7 IP baseline)
│   ├── R1.cfg … R6.cfg      # IOSv nodes (R1–R4, R6) — lab-04 solutions
│   ├── R5.cfg               # CSR1000v + GigabitEthernet4 added for R7 link
│   └── R7.cfg               # CSR1000v — IP addressing only
├── solutions/               # Full lab-05 solution configs (all 7 devices)
├── topology/
│   ├── topology.drawio      # EVE-NG topology diagram
│   └── README.md            # EVE-NG import / export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py  # Ticket 1: send-community stripped by R4
        ├── inject_scenario_02.py  # Ticket 2: FlowSpec AF not activated on R5
        ├── inject_scenario_03.py  # Ticket 3: no-export community stripped by R6
        ├── apply_solution.py      # Restore to known-good solution state
        └── README.md              # Run instructions (no spoilers)
```
