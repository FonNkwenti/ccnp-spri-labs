# Lab 01 — Topology-Independent Loop-Free Alternate (TI-LFA)

Sub-50ms SR-MPLS fast-reroute on a 4-router ring with a diagonal repair path.

## Blueprint Coverage

- **4.2.c** — Describe and configure TI-LFA (Topology-Independent Loop-Free Alternate)

## Prerequisites

- Lab 00 (`lab-00-sr-foundations-and-srgb`) completed — initial configs are lab-00's solutions
- Python 3.9+, Netmiko, requests (`pip install netmiko requests`)
- EVE-NG lab `.unl` imported and all nodes started; wait ~10 min for IOS-XRv 9000 boot

## Quick Start

```bash
# 1. Import lab topology into EVE-NG (manual — use the EVE-NG web UI)
#    See topology/README.md for step-by-step instructions

# 2. Push initial configs (IS-IS + SR-MPLS baseline, no TI-LFA yet)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin
workbook.md
```

## Files

```
lab-01-ti-lfa/
├── README.md                          # this file
├── workbook.md                        # lab guide (11 sections)
├── setup_lab.py                       # pushes initial-configs/ via EVE-NG REST + Netmiko
├── initial-configs/                   # lab-00 solutions — IS-IS L2 + SR-MPLS, no TI-LFA
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/                         # full TI-LFA + BFD solution per router
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── topology/
│   ├── topology.drawio                # draw.io diagram (square ring + L5 diagonal)
│   └── README.md                      # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py          # Ticket 1 fault
    ├── inject_scenario_02.py          # Ticket 2 fault
    ├── inject_scenario_03.py          # Ticket 3 fault
    ├── apply_solution.py              # restore to known-good state
    └── README.md                      # inject/restore workflow (no spoilers)
```
