# MPLS Lab 02 — BGP-Free Core and Unified BGP (Labeled Unicast)

Extends the LDP underlay from labs 00/01 to carry customer traffic across a BGP-free core
using eBGP PE–CE sessions, iBGP PE–PE with next-hop-self, and BGP Labeled-Unicast (send-label).

## Blueprint Coverage

| Bullet | Topic |
|--------|-------|
| 4.1.c | Unified BGP (BGP labeled-unicast) |
| 4.1.d | BGP-free core |

## Prerequisites

- Lab 01 (LSP Verification with MPLS OAM) completed — this lab's initial configs chain from lab-01 solutions.
- Python 3.8+, `netmiko` package installed.
- EVE-NG lab `.unl` imported and all nodes started.

## Quick Start

```bash
# 1. Import topology into EVE-NG
#    EVE-NG UI → File → Import → select topology/topology.drawio-derived .unl

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
open workbook.md   # or view in VS Code / any Markdown viewer
```

## Files

```
lab-02-bgp-free-core-and-unified-bgp/
├── workbook.md                          # Lab guide (11 sections)
├── setup_lab.py                         # Pushes initial configs via EVE-NG API
├── README.md                            # This file
├── initial-configs/                     # Pre-loaded state (IS-IS+LDP, no BGP)
│   ├── PE1.cfg  PE2.cfg  P1.cfg  P2.cfg
│   ├── CE1.cfg  CE2.cfg
├── solutions/                           # Complete configs for all tasks
│   ├── PE1.cfg  PE2.cfg  P1.cfg  P2.cfg
│   ├── CE1.cfg  CE2.cfg
├── topology/
│   ├── topology.drawio                  # EVE-NG topology diagram
│   └── README.md                        # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py            # Ticket 1: next-hop-self removed
    ├── inject_scenario_02.py            # Ticket 2: BGP added to P1
    ├── inject_scenario_03.py            # Ticket 3: send-label removed from PE2
    ├── apply_solution.py                # Restore to known-good state
    └── README.md
```
