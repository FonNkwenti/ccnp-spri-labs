# Lab 01: Multilevel IS-IS and Route Advertisement

Evolves the single-area L1 baseline from lab-00 into a two-area multilevel IS-IS domain
with an L2 backbone adjacency, ATT-bit default routes, and inter-area reachability.

## Blueprint Coverage

- **1.3** — Troubleshoot IS-IS multilevel operations (IPv4 and IPv6)
- **1.3.a** — Route advertisement

## Prerequisites

- lab-00-single-level-isis completed (initial-configs chain from lab-00 solutions)
- Python 3.8+, Netmiko (`pip install netmiko`)
- EVE-NG lab imported and all nodes (R1–R5) started

## Quick Start

```bash
# 1. Import the .unl file in EVE-NG (File > Import)
# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
workbook.md
```

## Files

```
lab-01-multilevel-isis/
├── workbook.md                         # Full lab guide (11 sections)
├── setup_lab.py                        # Push initial configs via EVE-NG REST API
├── README.md                           # This file
├── decisions.md                        # Build decisions and model gate record
├── meta.yaml                           # Lab metadata
├── initial-configs/
│   ├── R1.cfg                          # lab-00 solution (L1, area 49.0001)
│   ├── R2.cfg                          # lab-00 solution (L1, area 49.0001)
│   ├── R3.cfg                          # lab-00 solution + Gi0/1, Gi0/2 IPs
│   ├── R4.cfg                          # IP addressing only (new device)
│   └── R5.cfg                          # IP addressing only (new device)
├── solutions/
│   ├── R1.cfg                          # Unchanged — L1 stub, area 49.0001
│   ├── R2.cfg                          # Promoted to L1/L2, backbone circuit level-2-only
│   ├── R3.cfg                          # Promoted to L1/L2, area 49.0002, two new interfaces
│   ├── R4.cfg                          # Full IS-IS L1 config, area 49.0002
│   └── R5.cfg                          # Full IS-IS L1 config, area 49.0002
├── topology/
│   ├── topology.drawio                 # EVE-NG import topology
│   └── README.md                       # EVE-NG import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py       # Ticket 1: NET area-ID typo on R4
        ├── inject_scenario_02.py       # Ticket 2: is-type level-2-only on R2
        ├── inject_scenario_03.py       # Ticket 3: circuit-type level-1 on R2 Gi0/1
        ├── apply_solution.py           # Restore all devices to solution config
        └── README.md                   # Ops-only inject/restore instructions
```
