# BGP Lab 02 — eBGP Multihoming and Traffic Engineering

Activates Customer A's backup eBGP session to PE East-2 (R3) and applies
LOCAL_PREF, AS-path prepending, and MED to establish deterministic primary/backup
path selection across the dual-homed design.

## Blueprint Coverage

- **1.5.d** — Troubleshoot BGP multihoming

## Prerequisites

- Lab 01 (`lab-01-route-reflectors`) must be complete — this lab chains directly from it
- Python 3.8+, `netmiko` installed (`pip install -r requirements.txt`)
- EVE-NG lab `.unl` imported and all nodes started

## Quick Start

```bash
# 1. Import the topology into EVE-NG (see topology/README.md)
# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>
# 3. Open the workbook
open workbook.md
```

## Files

```
lab-02-ebgp-multihoming/
├── workbook.md                      Lab guide — 11 sections, 5 tasks, 3 tickets
├── setup_lab.py                     Pushes initial-configs/ to all 6 nodes
├── README.md                        This file
├── decisions.md                     Design decisions and model gate record
├── meta.yaml                        Build provenance
├── initial-configs/                 Lab-01 solutions — student starting point
│   └── R1.cfg … R6.cfg
├── solutions/                       Verified solution configs
│   └── R1.cfg … R6.cfg
├── topology/
│   ├── topology.drawio              Draw.io visual diagram
│   └── README.md                    EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py        Ticket 1: remove next-hop-self on R3
    ├── inject_scenario_02.py        Ticket 2: remove LOCAL_PREF route-map on R2
    ├── inject_scenario_03.py        Ticket 3: remove AS-path prepend on R1
    ├── apply_solution.py            Restore all 6 devices to solution state
    └── README.md                    Inject/restore usage reference
```
