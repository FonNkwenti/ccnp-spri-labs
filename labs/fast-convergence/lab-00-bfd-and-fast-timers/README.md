# Fast Convergence Lab 00 — BFD and Fast Timer Tuning

Foundation lab for the Fast Convergence topic. Builds the IS-IS L2 underlay and iBGP/eBGP overlay, then progressively reduces failure detection from 30 s to sub-500 ms using BFD single-hop (IS-IS) and BFD multi-hop (loopback-sourced eBGP).

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.7 | Implement fast convergence (umbrella) |
| 1.7.a | Bidirectional Forwarding Detection (BFD) — single-hop and multi-hop |
| 1.7.d | Timers — IS-IS hello/hold, SPF/PRC throttle, BGP keepalive/hold |

## Prerequisites

- This is the first lab in the topic (no prior lab to chain from)
- Python 3.8+ with Netmiko installed (`pip install netmiko`)
- EVE-NG server running with CSR1000v image available
- Lab `.unl` imported into EVE-NG and all nodes started

## Quick Start

```bash
# 1. Import topology into EVE-NG
#    File > Import > lab-00-bfd-and-fast-timers.unl

# 2. Push initial configurations
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md
```

## Files

```
lab-00-bfd-and-fast-timers/
├── workbook.md                          # Student workbook (11 sections)
├── README.md                            # This file
├── setup_lab.py                         # Initial config automation
├── initial-configs/                     # IP-only baseline (pre-loaded by setup_lab.py)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── solutions/                           # Full solution configs
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── topology/
│   ├── topology.drawio                  # Cisco19-icon EVE-NG diagram
│   └── README.md                        # EVE-NG import/export instructions
├── scripts/fault-injection/
│   ├── inject_scenario_01.py            # Ticket 1 fault injector
│   ├── inject_scenario_02.py            # Ticket 2 fault injector
│   ├── inject_scenario_03.py            # Ticket 3 fault injector
│   ├── apply_solution.py                # Restores known-good state
│   └── README.md                        # Fault injection ops reference
└── meta.yaml                            # Provenance tracking
```
