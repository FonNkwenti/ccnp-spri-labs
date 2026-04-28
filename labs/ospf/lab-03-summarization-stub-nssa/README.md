# OSPF Lab 03 — Summarization, Stub, and NSSA

Demonstrates OSPF LSA control using inter-area summarization, external summarization,
totally stubby areas, and NSSA with an internal ASBR. Builds on the dual-stack multiarea
topology from Lab 02.

## Blueprint Coverage

- **1.2.b** — OSPF Summarization (inter-area `area range`, external `summary-address`,
  ABR and ASBR roles, Null0 discard route behavior)

## Prerequisites

- Completed Lab 02 (dual-stack multiarea OSPFv2/OSPFv3) or equivalent
- Python 3.x + `netmiko` installed: `pip install netmiko`
- Lab `.unl` imported into EVE-NG (see `topology/README.md`)
- All six nodes started in EVE-NG before running setup

## Quick Start

```bash
# 1. Import the topology .unl into EVE-NG (one-time, via EVE-NG web UI)
#    See topology/README.md for step-by-step instructions

# 2. Start all nodes in EVE-NG, then push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin
open workbook.md
```

## Files

```
lab-03-summarization-stub-nssa/
├── workbook.md              # Student workbook (11 sections)
├── README.md                # This file
├── setup_lab.py             # Pushes initial-configs to all devices
├── decisions.md             # Design decisions and model gate record
├── initial-configs/         # Starting state (chained from Lab 02 + R6 new)
│   ├── R1.cfg               # + Lo2/Lo3 for summarization demo
│   ├── R2.cfg
│   ├── R3.cfg               # + Gi0/3 addressed (no OSPF)
│   ├── R4.cfg
│   ├── R5.cfg               # + Lo2 192.168.55.1/24 (for NSSA redistribution)
│   └── R6.cfg               # New device — IP only, no OSPF
├── solutions/               # Fully configured end state
│   ├── R1.cfg through R6.cfg
├── topology/
│   ├── topology.drawio      # EVE-NG topology diagram
│   └── README.md            # EVE-NG import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # Ticket 1: External route blocked
        ├── inject_scenario_02.py   # Ticket 2: Area 2 type mismatch
        ├── inject_scenario_03.py   # Ticket 3: NSSA translation disabled
        ├── apply_solution.py       # Restore all devices
        └── README.md
```
