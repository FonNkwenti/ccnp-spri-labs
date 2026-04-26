# Lab 01: Multiarea OSPFv2 and LSA Propagation

Migrates a single-area OSPF domain to four areas, introduces two ABRs, and exercises LSA Type-3 inter-area propagation across a five-router topology.

## Blueprint Coverage

- **1.2** — Implement and troubleshoot multiarea OSPF
- **1.2.a** — LSA types, inter-area route propagation, ABR behaviour

## Prerequisites

- Lab 00 (`lab-00-single-area-ospfv2`) completed — initial configs chain from its solutions
- Python 3.9+ and `netmiko` installed (`pip install netmiko`)
- EVE-NG running with five IOSv nodes imported from `lab-01-multiarea-ospfv2.unl`

## Quick Start

```bash
# 1. Import the lab topology into EVE-NG (see topology/README.md)

# 2. Start all nodes and wait ~90s for boot

# 3. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 4. Open the workbook
open workbook.md
```

## Files

```
lab-01-multiarea-ospfv2/
├── workbook.md                          # Lab guide (all 11 sections)
├── setup_lab.py                         # Pushes initial-configs to EVE-NG
├── README.md                            # This file
├── initial-configs/                     # Pre-loaded state (R1-R5)
│   ├── R1.cfg  R2.cfg  R3.cfg           # From lab-00 solutions (Area 0)
│   ├── R4.cfg                           # IP addressing only (new device)
│   └── R5.cfg                           # IP addressing only (new device)
├── solutions/                           # Verified full solution (R1-R5)
│   └── R1.cfg  R2.cfg  R3.cfg  R4.cfg  R5.cfg
├── topology/
│   ├── topology.drawio                  # Cisco-style diagram
│   └── README.md                        # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py            # Ticket 1: area-mismatch on L3
    ├── inject_scenario_02.py            # Ticket 2: missing network stmt on R5
    ├── inject_scenario_03.py            # Ticket 3: R2 ABR designation lost
    ├── apply_solution.py                # Restore known-good state
    └── README.md
```
