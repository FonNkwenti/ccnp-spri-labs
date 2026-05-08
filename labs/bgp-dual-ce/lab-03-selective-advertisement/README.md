# BGP Dual-CE Lab 03 — Outbound Policy and Selective Prefix Advertisement

Builds on lab-02 by adding LOCAL_PREF inbound on each CE for ISP-side primary/backup
selection and splitting the customer's /24 into per-CE /25 advertisements so each upstream
owns a distinct longest-match path. R3 and R4 each originate a default route so LP is
observable on a non-locally-originated prefix.

## Blueprint Coverage

- **1.5.d** — Multihoming (outbound steering with LOCAL_PREF; selective advertisement)
- **1.5.a** — BGP path attributes (LOCAL_PREF, AS-path interaction with longest-match)

## Prerequisites

- Python 3.8+, `netmiko` installed
- EVE-NG lab imported and all six nodes started
- **Required:** completion of `bgp-dual-ce/lab-02-inbound-traffic-engineering`. This lab's
  initial-configs are the lab-02 solution state for all six devices.

## Quick Start

```bash
# 1. Import the .unl into EVE-NG (File > Import in the web UI)
#    Reference: topology/topology.drawio

# 2. Push initial configuration (lab-02 solution baseline)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and start Task 1
open workbook.md
```

## Files

```
lab-03-selective-advertisement/
├── workbook.md              # Full lab guide (11 sections)
├── setup_lab.py             # Initial config deployment script
├── README.md                # This file
├── decisions.md             # Design decisions and model gate record
├── meta.yaml                # Provenance
├── initial-configs/         # Pre-loaded: lab-02 solution state for all six devices
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── solutions/               # Complete solution configs
│   ├── R1.cfg               # adds LP_FROM_R3 inbound, /25-low origination, tightened filter
│   ├── R2.cfg               # adds LP_FROM_R4 inbound, /25-high origination, tightened filter
│   ├── R3.cfg               # adds default-route origination
│   ├── R4.cfg               # adds default-route origination
│   ├── R5.cfg               # unchanged from lab-02
│   └── R6.cfg               # unchanged from lab-02
├── topology/
│   ├── topology.drawio      # EVE-NG layout reference diagram
│   └── README.md            # Import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # LP route-map applied outbound instead of inbound on R1
        ├── inject_scenario_02.py   # Overly-tight iBGP egress filter on R3 hides /25 from R5
        ├── inject_scenario_03.py   # Missing Null0 static for /25-high on R2 (origination fails)
        ├── apply_solution.py       # Restore to known-good (full solution)
        └── README.md
```
