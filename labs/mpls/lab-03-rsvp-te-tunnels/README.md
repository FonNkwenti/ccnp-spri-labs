# MPLS Lab 03: RSVP-TE Tunnels with Explicit Paths

RSVP-TE control-plane lab — enable MPLS TE on a four-router diamond core, signal dynamic
and explicit-path tunnels from PE1 to PE2, and steer IS-IS traffic through the tunnels.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 4.1.e | RSVP-TE tunnels (dynamic + explicit path, autoroute, secondary path-option) |

## Prerequisites

- Lab-02 (BGP-Free Core and Unified BGP) must be completed first — this lab continues
  from its solution state (IS-IS + LDP + iBGP + eBGP all running).
- Python 3.10+ with `pip install -r requirements.txt`
- EVE-NG accessible on your network with six IOSv nodes running

## Quick Start

```bash
# 1. Import the .unl file into EVE-NG (File → Import in the web UI)
# 2. Start all nodes and wait ~60 seconds for boot

# 3. Push lab-02 solution state (initial-configs for this lab)
python3 labs/mpls/lab-03-rsvp-te-tunnels/setup_lab.py --host <eve-ng-ip>

# 4. Open the workbook and start with Task 1
open labs/mpls/lab-03-rsvp-te-tunnels/workbook.md
```

## Files

```
lab-03-rsvp-te-tunnels/
├── workbook.md                         # Lab tasks, verification, cheatsheet, troubleshooting
├── setup_lab.py                        # Push initial configs via EVE-NG API
├── README.md                           # This file
├── initial-configs/                    # Lab-02 solution state (pre-loaded by setup_lab.py)
│   ├── PE1.cfg  P1.cfg  P2.cfg  PE2.cfg
│   └── CE1.cfg  CE2.cfg
├── solutions/                          # Complete solution for all tasks
│   ├── PE1.cfg  P1.cfg  P2.cfg  PE2.cfg
│   └── CE1.cfg  CE2.cfg
├── topology/
│   ├── topology.drawio                 # EVE-NG layout reference diagram
│   └── README.md                       # Import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py           # Ticket 1: RSVP bandwidth fault on L4
    ├── inject_scenario_02.py           # Ticket 2: IS-IS TE extensions removed from P2
    ├── inject_scenario_03.py           # Ticket 3: MPLS TE disabled on P1
    ├── apply_solution.py               # Restore all devices to solution state
    └── README.md
```
