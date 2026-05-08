# Lab 00 — Static IPv6-in-IPv4 and 6to4 Tunnels

Establish IPv6 reachability across an IPv4-only provider core using manual tunnels and automatic 6to4. The core routers (R2, R3) remain IPv4-only throughout.

## Blueprint Coverage

- **1.6** — Describe IPv6 tunneling mechanisms
- **1.6.a** — Static IPv6-in-IPv4 tunnels
- **1.6.b** — Dynamic 6to4 tunnels

## Prerequisites

- This is the first lab in the `ipv6-transition` topic — no prior lab dependency.
- Python 3.8+, `netmiko` library installed.
- EVE-NG running with four IOSv nodes imported and started.

## Quick Start

```bash
# 1. Import the lab topology in EVE-NG (File > Import lab-00-manual-and-6to4-tunnels.unl)
# 2. Start all nodes and wait ~90s for boot
python3 setup_lab.py --host <eve-ng-ip>
# 3. Open the workbook
open workbook.md
```

## Files

```
lab-00-manual-and-6to4-tunnels/
├── workbook.md                          # Full lab guide (11 sections)
├── setup_lab.py                         # Push initial configs to EVE-NG
├── README.md                            # This file
├── decisions.md                         # Build decisions and gate log
├── initial-configs/                     # Pre-loaded IP addressing
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/                           # Complete solution configs
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── topology/
│   ├── topology.drawio                  # EVE-NG topology diagram
│   └── README.md                        # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py            # Ticket 1 fault
    ├── inject_scenario_02.py            # Ticket 2 fault
    ├── inject_scenario_03.py            # Ticket 3 fault
    ├── apply_solution.py                # Restore to known-good state
    └── README.md                        # Fault injection usage
```
