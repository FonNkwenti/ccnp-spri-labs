# MPLS Lab 04 — Full Mastery Capstone I (Pi Build)

Build the complete SP MPLS stack from bare IP addressing: IS-IS L2 underlay,
MPLS LDP, iBGP with BGP-LU, eBGP to CEs, and an RSVP-TE tunnel with redundant
path options.

## Blueprint Coverage

- **4.1** Troubleshoot MPLS (all sub-bullets)
- **4.1.a** LDP
- **4.1.b** LSP verification
- **4.1.c** Unified BGP (BGP Labeled-Unicast)
- **4.1.d** BGP-free core
- **4.1.e** RSVP-TE tunnels

## Prerequisites

- Lab 00–03 MPLS (progressive chain knowledge — this capstone starts clean-slate)
- Python 3.8+, Netmiko, EVE-NG REST API access
- Lab `.unl` imported into EVE-NG and all nodes started

## Quick Start

```bash
# 1. Import the lab .unl into EVE-NG and start all nodes
# 2. Push initial IP configurations
python3 setup_lab.py --host <eve-ng-ip>
# 3. Open the workbook and begin
```

## Files

```
lab-04-capstone-config-pi/
├── workbook.md              # Full lab workbook (11 sections)
├── README.md                # This file
├── setup_lab.py             # Push initial configs via EVE-NG
├── decisions.md             # Build decisions and gate outcomes
├── meta.yaml                # Build provenance metadata
├── initial-configs/         # Pre-loaded IP-only configs
│   ├── PE1.cfg, P1.cfg, P2.cfg, PE2.cfg
│   └── CE1.cfg, CE2.cfg
├── solutions/               # Complete MPLS stack configs
│   ├── PE1.cfg, P1.cfg, P2.cfg, PE2.cfg
│   └── CE1.cfg, CE2.cfg
├── topology/
│   ├── topology.drawio      # Network diagram
│   └── README.md            # EVE-NG import/export guide
└── scripts/
    └── fault-injection/     # Troubleshooting ticket injectors
        ├── inject_scenario_01.py
        ├── inject_scenario_02.py
        ├── inject_scenario_03.py
        ├── apply_solution.py
        └── README.md
```
