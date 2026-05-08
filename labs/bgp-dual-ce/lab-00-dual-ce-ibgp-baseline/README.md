# BGP Dual-CE Lab 00 — Dual-CE iBGP Architecture and Baseline

Foundation lab establishing the dual-CE topology used throughout the bgp-dual-ce series:
two CEs in AS 65001, each peering with a different upstream ISP (AS 65100, AS 65200),
joined by a CE-CE iBGP session on Loopback0.

## Blueprint Coverage

- **1.5.d** — Multihoming (dual-CE, dual-provider variant)

## Prerequisites

- Python 3.8+, `netmiko` installed
- EVE-NG lab imported and all nodes started
- Recommended: completion of `bgp/lab-00-ebgp-ibgp-foundations` for general BGP fluency
  (not strictly required — this lab re-introduces the relevant concepts)

## Quick Start

```bash
# 1. Import the .unl into EVE-NG (File > Import in the web UI)
#    Reference: topology/topology.drawio

# 2. Push initial configuration (interfaces + IP addressing only)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and start Phase 1
open workbook.md
```

## Files

```
lab-00-dual-ce-ibgp-baseline/
├── workbook.md              # Full lab guide (11 sections)
├── setup_lab.py             # Initial config deployment script
├── README.md                # This file
├── decisions.md             # Design decisions and model gate record
├── meta.yaml                # Provenance
├── initial-configs/         # Pre-loaded: IP addressing + hostnames only
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/               # Complete solution configs (all tasks)
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── topology/
│   ├── topology.drawio      # EVE-NG layout reference diagram
│   └── README.md            # Import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # Ticket 1 fault
        ├── inject_scenario_02.py   # Ticket 2 fault
        ├── inject_scenario_03.py   # Ticket 3 fault
        ├── apply_solution.py       # Restore to known-good (full solution)
        └── README.md
```
