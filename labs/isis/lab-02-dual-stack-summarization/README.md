# IS-IS Lab 02: Dual-Stack Summarization and Route Leaking

Extends the lab-01 two-area IS-IS topology with IPv6 dual-stack (MT-IPv6), route summarization, external redistribution from a non-IS-IS device, and selective L2-to-L1 route leaking.

## Blueprint Coverage

- IS-IS Multi-Topology IPv6 (MT-IPv6, TID 2, TLV 222)
- IS-IS route summarization (`summary-address` for IPv4, `summary-prefix` for IPv6)
- IS-IS external redistribution (static routes into IS-IS)
- IS-IS L2-to-L1 route leaking with prefix-list filtering

## Prerequisites

- Chains from: `isis/lab-01-multilevel-isis` (initial-configs = lab-01 solutions)
- Python 3.8+, `netmiko` library installed
- EVE-NG lab imported and all nodes started

## Quick Start

```bash
# 1. Import the lab into EVE-NG (see topology/README.md)

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook
# Start with Section 4 (Base Configuration) then Section 5 (Tasks)
```

## Files

```
lab-02-dual-stack-summarization/
├── workbook.md                        # Lab guide (11 sections)
├── setup_lab.py                       # Push initial-configs to EVE-NG
├── README.md                          # This file
├── decisions.md                       # Build decisions and rationale
├── meta.yaml                          # Provenance
├── initial-configs/                   # Starting state (= lab-01 solutions for R1-R5)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg  R6.cfg
├── solutions/                         # Full solution configs
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg  R6.cfg
├── topology/
│   ├── topology.drawio                # Draw.io diagram
│   └── README.md                      # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py          # Ticket 1: R4 IPv6 IS-IS disabled
    ├── inject_scenario_02.py          # Ticket 2: R3 redistribution removed
    ├── inject_scenario_03.py          # Ticket 3: R2 route-leak prefix-list wrong
    ├── apply_solution.py              # Restore to known-good state
    └── README.md                      # Ops reference
```
