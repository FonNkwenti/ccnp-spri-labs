# Lab 02 — SR Migration: LDP Coexistence, Mapping Server, and SR-Prefer

Phased LDP-to-SR migration on a 4-router SP core: run LDP and SR concurrently, configure an SR mapping server for a legacy customer prefix, and control label-source preference with sr-prefer.

## Blueprint Coverage

- **4.2.d** — Describe SR migration from LDP, including LDP coexistence, SR mapping server, and SR-prefer

## Prerequisites

- Lab 01 (`lab-01-ti-lfa`) completed — initial configs are lab-01's solutions (IS-IS L2 + SR-MPLS + TI-LFA)
- Python 3.9+, Netmiko, requests (`pip install netmiko requests`)
- EVE-NG lab `.unl` imported and all nodes started; wait ~10 min for IOS-XRv 9000 boot

## Quick Start

```bash
# 1. Import lab topology into EVE-NG (manual — use the EVE-NG web UI)
#    See topology/README.md for step-by-step instructions

# 2. Push initial configs (IS-IS + SR-MPLS + TI-LFA baseline, no LDP)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin
workbook.md
```

## Files

```
lab-02-sr-migration-ldp-coexistence/
├── README.md                          # this file
├── workbook.md                        # lab guide (11 sections)
├── setup_lab.py                       # pushes initial-configs/ via EVE-NG REST + Netmiko
├── initial-configs/                   # lab-01 solutions — IS-IS L2 + SR-MPLS + TI-LFA, no LDP
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/                         # full LDP + mapping server + sr-prefer solution per router
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
