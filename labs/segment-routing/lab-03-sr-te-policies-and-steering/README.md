# Lab 03: SR-TE Policies, Constraints, and Automated Steering

SR Traffic Engineering on a 4-router IOS-XRv 9000 SP core with two customer edges. Builds dynamic, explicit, and affinity-constrained SR-TE policies; enables color-based automated steering via BGP extended communities.

## Blueprint Coverage

- **4.3.a** — Configure and verify SR-TE policies (dynamic, explicit, affinity constraints)
- **4.3.b** — Implement SR-TE traffic steering (color-based automated steering, ODN)

## Prerequisites

- Completes from: `lab-02-sr-migration-ldp-coexistence` (progressive)
- Python 3.8+ with `netmiko` installed
- EVE-NG server reachable at the target IP; lab `.unl` imported and nodes started

## Quick Start

```bash
# 1. Import the lab topology into EVE-NG (see topology/README.md)

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin Task 1
open workbook.md
```

## Files

```
lab-03-sr-te-policies-and-steering/
├── workbook.md                        # Lab guide — all 11 sections
├── setup_lab.py                       # Push initial-configs to EVE-NG nodes
├── README.md                          # This file
├── decisions.md                       # Design decisions log
├── meta.yaml                          # Build metadata
├── initial-configs/
│   ├── R1.cfg                         # Core with teardown block (removes lab-02 mapping server)
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── CE1.cfg                        # IP-only; student configures BGP
│   └── CE2.cfg                        # IP-only; student configures BGP
├── solutions/
│   ├── R1.cfg                         # SR-TE policies, ODN, BGP
│   ├── R2.cfg                         # Affinity-map, BLUE on L2
│   ├── R3.cfg                         # RP_CE2_IN attaches color:10, BGP
│   ├── R4.cfg                         # Affinity-map, RED on L3
│   ├── CE1.cfg
│   └── CE2.cfg
├── topology/
│   ├── topology.drawio                # EVE-NG visual topology
│   └── README.md                      # EVE-NG import instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py      # Ticket 1: color stripped at R1
        ├── inject_scenario_02.py      # Ticket 2: RED affinity missing on R4
        ├── inject_scenario_03.py      # Ticket 3: color never attached at R3
        ├── apply_solution.py          # Restore solution state
        └── README.md
```
