# BGP Lab 07 — Full Protocol Mastery Capstone I (Pi Build)

Build a complete production BGP SP topology across three autonomous systems:
OSPF area 0 underlay, iBGP route reflection, dual-homed eBGP multihoming with
LOCAL_PREF/MED/AS-path prepend, inter-domain security, route dampening, dynamic
neighbors, BGP communities, and FlowSpec between two CSR1000v peers.

## Blueprint Coverage

- **1.4** BGP scalability and performance (full-mesh → RR)
- **1.4.a** BGP confederations
- **1.4.b** Route reflectors
- **1.5.a** Route advertisement
- **1.5.b** Route reflectors
- **1.5.d** Multihoming
- **1.5.e** TTL security and inter-domain security
- **1.5.f** Maximum prefix
- **1.5.g** Route dampening
- **1.5.h** Dynamic neighbors
- **1.5.i** Communities
- **1.5.j** FlowSpec

## Prerequisites

- Lab 00–06 BGP (progressive chain knowledge — this capstone starts clean-slate)
- Python 3.8+, Netmiko, EVE-NG REST API access
- Lab `.unl` imported into EVE-NG and all nodes started
- R5 and R7 must run CSR1000v images (FlowSpec requires IOS-XE)

## Quick Start

```bash
# 1. Import the lab .unl into EVE-NG and start all nodes
# 2. Push initial IP configurations
python3 setup_lab.py --host <eve-ng-ip>
# 3. Open the workbook and begin
```

## Files

```
lab-07-capstone-config-pi/
├── workbook.md              # Full lab workbook (11 sections)
├── README.md                # This file
├── setup_lab.py             # Push initial configs via EVE-NG
├── decisions.md             # Build decisions and gate outcomes
├── meta.yaml                # Build provenance metadata
├── initial-configs/         # Pre-loaded IP-only configs (R1–R7)
├── solutions/               # Complete BGP production configs (R1–R7)
├── topology/
│   ├── topology.drawio      # Network diagram
│   └── README.md            # EVE-NG import/export guide
└── scripts/
    └── fault-injection/     # Troubleshooting ticket injectors
        ├── inject_scenario_01.py, 02.py, 03.py
        ├── apply_solution.py
        └── README.md
```
