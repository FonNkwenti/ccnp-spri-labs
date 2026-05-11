# Fast Convergence Lab 02 — IS-IS LFA and IP Fast Reroute

Builds on lab-01 (NSF + BGP GR + NSR) and adds sub-50 ms IP convergence using
IS-IS Loop-Free Alternate (LFA) and Remote LFA with MPLS LDP tunnels. Covers
per-prefix LFA, R-LFA, PQ-node analysis, and LFA coverage verification.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.7.f | LFA / IP-FRR |

## Prerequisites

- lab-01 (NSF and NSR) completed — initial-configs for this lab are lab-01 solutions
- Python 3.8+ with Netmiko installed (`pip install netmiko`)
- EVE-NG server running with IOSv image available
- Lab `.unl` imported into EVE-NG and all nodes started

## Quick Start

```bash
# 1. Import topology into EVE-NG
#    File > Import > lab-02-lfa-ip-fast-reroute.unl

# 2. Push initial configurations (lab-01 solutions — BFD + timers + NSF + BGP GR + NSR pre-loaded)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md
```

## Files

```
lab-02-lfa-ip-fast-reroute/
├── workbook.md                          # Student workbook (11 sections)
├── README.md                            # This file
├── setup_lab.py                         # Initial config automation
├── initial-configs/                     # lab-01 solutions (BFD + timers + NSF + BGP GR + NSR pre-loaded)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── solutions/                           # Full solution configs (adds LFA + R-LFA + MPLS LDP)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── topology/
│   └── README.md                        # EVE-NG import/export instructions
├── scripts/fault-injection/
│   ├── inject_scenario_01.py            # Ticket 1 — R1 LFA broken prefix-list
│   ├── inject_scenario_02.py            # Ticket 2 — R2 MPLS LDP missing on L2
│   ├── inject_scenario_03.py            # Ticket 3 — R3 LFA removed entirely
│   ├── apply_solution.py                # Restores known-good state
│   └── README.md                        # Fault injection ops reference
└── meta.yaml                            # Provenance tracking
```
