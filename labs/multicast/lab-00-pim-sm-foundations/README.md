# Lab 00 — PIM-SM Foundations

Enables PIM-SM throughout a four-router IS-IS L2 domain, configures a static RP, and verifies a live UDP multicast stream from SRC1 to RCV1 including IGMP signaling, shared-tree state, and SPT switchover.

## Blueprint Coverage

| Objective | Description |
|-----------|-------------|
| 2.1 | Implement IP multicast in a service provider network |
| 2.1.a | PIM-SM operations: DR election, RP, shared tree, source tree |
| 2.1.b | PIM register and register-stop messages |
| 2.2.a | IP multicast to Layer-2 MAC address mapping |
| 2.2.c | IGMP operations |
| 2.2.f | Multicast distribution trees: RPT and SPT |
| 2.3 | Verify PIM-SM operations |
| 2.4.a | Troubleshoot multicast routing |

## Prerequisites

- This is the first lab in the multicast topic (no chain dependency)
- EVE-NG running on Dell Latitude 5540 with IOSv image available
- Python 3.8+ with `netmiko` installed (`pip install netmiko`)
- `labs/common/tools/eve_ng.py` present (shared EVE-NG library)

## Quick Start

```bash
# 1. Import topology into EVE-NG (see topology/README.md)

# 2. Start all nodes, then push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin
open workbook.md
```

## Files

```
lab-00-pim-sm-foundations/
├── workbook.md                        # Full lab guide (11 sections)
├── setup_lab.py                       # Pushes initial-configs to R1-R4
├── README.md                          # This file
├── decisions.md                       # Build provenance and gate outcomes
├── initial-configs/
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg # IP-only baseline (no IS-IS, no PIM)
├── solutions/
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg # Full solution configs
├── topology/
│   ├── topology.drawio                # Draw.io diagram for EVE-NG layout
│   └── README.md                      # EVE-NG import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py          # Ticket 1 fault injector
    ├── inject_scenario_02.py          # Ticket 2 fault injector
    ├── inject_scenario_03.py          # Ticket 3 fault injector
    ├── apply_solution.py              # Restore known-good state
    └── README.md                      # Ops guide (no spoilers)
```
