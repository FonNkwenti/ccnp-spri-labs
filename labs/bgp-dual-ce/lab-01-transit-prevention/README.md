# BGP Dual-CE Lab 01 — Transit Prevention Policy

Builds on lab-00 by adding outbound route-map filtering on each eBGP session. Without
this filter the customer AS becomes a free transit path between ISP-A and ISP-B.

## Blueprint Coverage

- **1.5.d** — Multihoming (transit prevention, dual-CE variant)

## Prerequisites

- Python 3.8+, `netmiko` installed
- EVE-NG lab imported and all nodes started
- **Required:** completion of `bgp-dual-ce/lab-00-dual-ce-ibgp-baseline`. This lab's
  initial-configs are the lab-00 solution state.

## Quick Start

```bash
# 1. Import the .unl into EVE-NG (File > Import in the web UI)
#    Reference: topology/topology.drawio

# 2. Push initial configuration (lab-00 solution state — eBGP + iBGP working)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and start Task 1
open workbook.md
```

## Files

```
lab-01-transit-prevention/
├── workbook.md              # Full lab guide (11 sections)
├── setup_lab.py             # Initial config deployment script
├── README.md                # This file
├── decisions.md             # Design decisions and model gate record
├── meta.yaml                # Provenance
├── initial-configs/         # Pre-loaded: lab-00 solution state
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/               # Complete solution configs (lab-00 + transit-prevent filter)
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── topology/
│   ├── topology.drawio      # EVE-NG layout reference diagram
│   └── README.md            # Import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # Filter on wrong session (iBGP)
        ├── inject_scenario_02.py   # Route-map exists but not bound to neighbor
        ├── inject_scenario_03.py   # Route-map bound inbound instead of outbound
        ├── apply_solution.py       # Restore to known-good (full solution)
        └── README.md
```
