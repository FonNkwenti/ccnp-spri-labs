# BGP Lab 04 — Route Dampening and Dynamic Neighbors

Configure BGP route dampening on the West PE to suppress unstable external prefixes,
and enable dynamic BGP neighbor provisioning on an East PE for zero-touch customer onboarding.

## Blueprint Coverage

- **1.5.g** — Route dampening
- **1.5.h** — Dynamic neighbors

## Prerequisites

- Lab 03 (Inter-Domain Security) completed — this lab extends that state.
- Python 3.8+ with `netmiko` installed: `pip install netmiko`
- EVE-NG lab `.unl` imported and all nodes started.

## Quick Start

```bash
# 1. Import lab-04-dampening-dynamic.unl via EVE-NG web UI (File > Import)
# 2. Start all nodes, wait ~60 seconds for boot
python3 setup_lab.py --host <eve-ng-ip>
# 3. Open workbook
open workbook.md
```

## Files

```
lab-04-dampening-dynamic/
├── workbook.md              — Lab guide with all tasks and solutions
├── setup_lab.py             — Pushes initial configs to all devices
├── README.md                — This file
├── decisions.md             — Design decisions and model gate record
├── meta.yaml                — Lab metadata
├── initial-configs/         — Starting state (= lab-03 solutions)
│   ├── R1.cfg ... R6.cfg
├── solutions/               — Full solution configs
│   ├── R1.cfg ... R6.cfg
├── topology/
│   ├── topology.drawio      — EVE-NG topology diagram
│   └── README.md            — Import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py — Ticket 1: dampened prefix
    ├── inject_scenario_02.py — Ticket 2: missing listen range
    ├── inject_scenario_03.py — Ticket 3: peer-group not activated in AF
    ├── apply_solution.py     — Restore to known-good state
    └── README.md             — Ops-only inject/restore reference
```
