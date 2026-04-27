# BGP Lab 01 — iBGP Route Reflectors and Cluster IDs

Migrates a minimal iBGP mesh to a Route Reflector architecture. R4 becomes the RR
for AS 65100; R3 joins the iBGP fabric as a client for the first time.

## Blueprint Coverage

- **1.4.b** — Route reflectors
- **1.5.b** — Troubleshoot BGP route reflectors

## Prerequisites

- Builds on **lab-00-ebgp-ibgp-foundations** (initial-configs = lab-00 solutions)
- Python 3.8+ and Netmiko: `pip install netmiko`
- Lab imported into EVE-NG and all six nodes started

## Quick Start

```bash
# 1. Import lab topology in EVE-NG UI (topology/topology.drawio as reference)
# 2. Start all nodes

# 3. Reset to lab-00 baseline (lab-01 starting state)
python3 setup_lab.py --host <eve-ng-ip>

# 4. Open the workbook and begin
open workbook.md
```

## Files

```
lab-01-route-reflectors/
├── workbook.md               — Student workbook (11 sections)
├── setup_lab.py              — Push initial configs (lab-00 solutions) to all devices
├── README.md                 — This file
├── initial-configs/          — Lab-00 solution configs (starting state)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   └── R4.cfg  R5.cfg  R6.cfg
├── solutions/                — Lab-01 complete solution configs
│   ├── R1.cfg  R2.cfg  R3.cfg
│   └── R4.cfg  R5.cfg  R6.cfg
├── topology/
│   ├── topology.drawio       — EVE-NG lab diagram
│   └── README.md             — EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py — Ticket 1: missing route-reflector-client on R4 for R3
    ├── inject_scenario_02.py — Ticket 2: missing update-source on R3
    ├── inject_scenario_03.py — Ticket 3: missing next-hop-self on R2
    ├── apply_solution.py     — Restore lab-01 solution state
    └── README.md             — Fault injection quick reference
```
