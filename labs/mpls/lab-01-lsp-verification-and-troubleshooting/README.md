# MPLS Lab 01 â€” LSP Verification with MPLS OAM

Verifies and troubleshoots Label Switched Paths using `ping mpls`, `trace mpls`, LIB/LFIB inspection, PHP analysis, MPLS MTU correction, and ECMP validation across a four-router IOSv SP core.

## Blueprint Coverage

- **4.1.b** â€” LSP verification: MPLS ping/traceroute, PHP, MTU, ECMP

## Prerequisites

- Lab 00 (LDP Foundations) must be completed â€” this lab chains from its solutions
- EVE-NG lab `.unl` imported and all nodes started
- Python 3 with `netmiko`, `pyyaml`, `requests` installed

## Quick Start

```bash
# 1. Import the lab topology into EVE-NG (File > Import > select topology/topology.drawio or .unl)
# 2. Start all nodes and wait for boot (~60s for IOSv)
# 3. Push initial configs:
python3 setup_lab.py --host <eve-ng-ip>
# 4. Open the lab guide:
#    workbook.md
```

## Files

```
lab-01-lsp-verification-and-troubleshooting/
â”œâ”€â”€ workbook.md                          # Full lab guide (11 sections)
â”œâ”€â”€ setup_lab.py                         # Push initial-configs to all nodes
â”œâ”€â”€ README.md                            # This file
â”œâ”€â”€ initial-configs/
â”‚   â”œâ”€â”€ PE1.cfg                          # IS-IS + LDP (from lab-00)
â”‚   â”œâ”€â”€ P1.cfg
â”‚   â”œâ”€â”€ P2.cfg
â”‚   â””â”€â”€ PE2.cfg
â”œâ”€â”€ solutions/
â”‚   â”œâ”€â”€ PE1.cfg                          # IS-IS + LDP + mpls mtu override 1508
â”‚   â”œâ”€â”€ P1.cfg
â”‚   â”œâ”€â”€ P2.cfg
â”‚   â””â”€â”€ PE2.cfg
â”œâ”€â”€ topology/
â”‚   â”œâ”€â”€ topology.drawio                  # Draw.io diagram for EVE-NG import
â”‚   â””â”€â”€ README.md                        # EVE-NG import/export instructions
â””â”€â”€ scripts/fault-injection/
    â”œâ”€â”€ inject_scenario_01.py            # Ticket 1: no mpls ip on P1 Gi0/2
    â”œâ”€â”€ inject_scenario_02.py            # Ticket 2: missing mpls mtu override 1508
    â”œâ”€â”€ apply_solution.py                # Restore to known-good state
    â””â”€â”€ README.md                        # Fault injection usage
```
