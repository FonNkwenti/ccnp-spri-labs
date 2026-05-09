# Fast Convergence Lab 01 — Nonstop Forwarding (NSF) and Nonstop Routing (NSR)

Builds on lab-00 (BFD + fast timers) and adds the HA layer that lets a restarting router's neighbors cooperate in minimising routing disruption. Covers IS-IS Graceful Restart (NSF), BGP Graceful Restart, IS-IS NSR, and BGP NSR.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.7.b | Nonstop Forwarding (NSF) |
| 1.7.c | Nonstop Routing (NSR) |

## Prerequisites

- lab-00 (BFD and Fast Timers) completed — initial-configs for this lab are lab-00 solutions
- Python 3.8+ with Netmiko installed (`pip install netmiko`)
- EVE-NG server running with IOSv image available
- Lab `.unl` imported into EVE-NG and all nodes started

## Quick Start

```bash
# 1. Import topology into EVE-NG
#    File > Import > lab-01-nsf-and-nsr.unl

# 2. Push initial configurations (lab-00 solutions — BFD + timers pre-loaded)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md
```

## Files

```
lab-01-nsf-and-nsr/
├── workbook.md                          # Student workbook (11 sections)
├── README.md                            # This file
├── setup_lab.py                         # Initial config automation
├── initial-configs/                     # lab-00 solutions (BFD + timers pre-loaded)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── solutions/                           # Full solution configs (adds NSF + BGP GR + NSR)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── topology/
│   ├── topology.drawio                  # Cisco19-icon EVE-NG diagram
│   └── README.md                        # EVE-NG import/export instructions
├── scripts/fault-injection/
│   ├── inject_scenario_01.py            # Ticket 1 — R1 missing nsf ietf
│   ├── inject_scenario_02.py            # Ticket 2 — R5 missing bgp graceful-restart
│   ├── inject_scenario_03.py            # Ticket 3 — R4 missing nsf ietf
│   ├── apply_solution.py                # Restores known-good state
│   └── README.md                        # Fault injection ops reference
└── meta.yaml                            # Provenance tracking
```
