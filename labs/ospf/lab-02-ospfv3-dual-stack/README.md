# Lab 02: OSPFv3 Dual-Stack Multiarea

Adds IPv6 addressing and OSPFv3 to the four-area OSPF topology from lab-01. Runs OSPFv2 and OSPFv3 in parallel with matching area structure; exercises OSPFv3 LSA types (Type-8 Link, Type-9 Intra-Area Prefix).

## Blueprint Coverage

- **1.1** — OSPFv3 operation
- **1.2** — Multiarea OSPFv3
- **1.2.a** — OSPFv3 LSA types; dual-stack adjacency; comparison with OSPFv2

## Prerequisites

- Lab 01 (`lab-01-multiarea-ospfv2`) completed — initial configs chain from its solutions
- Python 3.9+ and `netmiko` installed (`pip install netmiko`)
- EVE-NG running with five IOSv nodes (same topology as lab-01)

## Quick Start

```bash
# 1. Import or reuse the lab topology in EVE-NG (see topology/README.md)

# 2. Start all nodes and wait ~90s for boot

# 3. Push initial configs (OSPFv2 multiarea, no IPv6)
python3 setup_lab.py --host <eve-ng-ip>

# 4. Open the workbook
open workbook.md
```

## Files

```
lab-02-ospfv3-dual-stack/
├── workbook.md                          # Lab guide (all 11 sections)
├── setup_lab.py                         # Pushes initial-configs to EVE-NG
├── README.md                            # This file
├── initial-configs/                     # Pre-loaded: OSPFv2 multiarea (from lab-01 solutions)
│   └── R1.cfg  R2.cfg  R3.cfg  R4.cfg  R5.cfg
├── solutions/                           # Full dual-stack solution (OSPFv2 + OSPFv3)
│   └── R1.cfg  R2.cfg  R3.cfg  R4.cfg  R5.cfg
├── topology/
│   ├── topology.drawio                  # Cisco-style dual-stack diagram
│   └── README.md                        # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py            # Ticket 1: missing ospfv3 area on R4 Gi0/0
    ├── inject_scenario_02.py            # Ticket 2: missing ospfv3 area on R5 Gi0/0
    ├── inject_scenario_03.py            # Ticket 3: R2 Gi0/0 area 0 instead of area 1
    ├── apply_solution.py                # Restore known-good state
    └── README.md
```
