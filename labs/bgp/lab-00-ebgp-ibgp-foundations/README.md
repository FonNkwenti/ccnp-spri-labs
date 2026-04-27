# BGP Lab 00 — eBGP and iBGP Foundations

Foundation lab establishing the three-AS SP topology, OSPF underlay, and minimal iBGP mesh used throughout the BGP chapter.

## Blueprint Coverage

- **1.4** — Describe BGP scalability and performance (full-mesh scaling problem stated)
- **1.5 / 1.5.a** — Troubleshoot BGP route advertisement

## Prerequisites

- Python 3.8+, `netmiko` installed
- EVE-NG lab imported and all nodes started
- No previous lab required — this is the first lab in the BGP chapter

## Quick Start

```bash
# 1. Import the .unl into EVE-NG (File > Import in the web UI)
#    File: topology/topology.drawio (use as layout reference; .unl created in EVE-NG)

# 2. Push initial configuration to all devices
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and start Task 1
open workbook.md
```

## Files

```
lab-00-ebgp-ibgp-foundations/
├── workbook.md              # Full lab guide (11 sections)
├── setup_lab.py             # Initial config deployment script
├── README.md                # This file
├── initial-configs/         # Pre-loaded: IP addressing + hostnames only
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── solutions/               # Complete solution configs (all tasks)
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── topology/
│   ├── topology.drawio      # EVE-NG layout reference diagram
│   └── README.md            # Import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # Ticket 1 fault
        ├── inject_scenario_02.py   # Ticket 2 fault
        ├── inject_scenario_03.py   # Ticket 3 fault
        ├── apply_solution.py       # Restore to known-good
        └── README.md
```
