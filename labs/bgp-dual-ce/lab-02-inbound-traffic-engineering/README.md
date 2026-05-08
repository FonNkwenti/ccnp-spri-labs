# BGP Dual-CE Lab 02 — Inbound Traffic Engineering Across Two ISPs

Builds on lab-01 by adding ISP-internal hosts (R5, R6) and using AS-path prepending on R2's
eBGP egress to make ISP-A the primary inbound path and ISP-B the backup. Demonstrates why
MED is not the right tool when the two upstream ISPs are in different ASes.

## Blueprint Coverage

- **1.5.d** — Multihoming (inbound traffic engineering, dual-CE variant)

## Prerequisites

- Python 3.8+, `netmiko` installed
- EVE-NG lab imported and all six nodes started
- **Required:** completion of `bgp-dual-ce/lab-01-transit-prevention`. This lab's
  initial-configs are the lab-01 solution state plus the new R5/R6 baseline.

## Quick Start

```bash
# 1. Import the .unl into EVE-NG (File > Import in the web UI)
#    Reference: topology/topology.drawio

# 2. Push initial configuration (lab-01 solution + R5/R6 baseline interfaces)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and start Task 1
open workbook.md
```

## Files

```
lab-02-inbound-traffic-engineering/
├── workbook.md              # Full lab guide (11 sections)
├── setup_lab.py             # Initial config deployment script
├── README.md                # This file
├── decisions.md             # Design decisions and model gate record
├── meta.yaml                # Provenance
├── initial-configs/         # Pre-loaded: lab-01 solution + R5/R6 interfaces only
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── solutions/               # Complete solution configs
│   ├── R1.cfg               # unchanged from lab-01
│   ├── R2.cfg               # adds set as-path prepend 65001 65001
│   ├── R3.cfg               # adds iBGP to R5 with next-hop-self
│   ├── R4.cfg               # adds iBGP to R6 with next-hop-self
│   ├── R5.cfg               # iBGP to R3, originates 10.100.2.0/24
│   └── R6.cfg               # iBGP to R4, originates 10.200.2.0/24
├── topology/
│   ├── topology.drawio      # EVE-NG layout reference diagram
│   └── README.md            # Import/export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py   # Prepend on wrong egress (R1→R3 instead of R2→R4)
        ├── inject_scenario_02.py   # Prepend value is the neighbor's AS (loop-prevention drop)
        ├── inject_scenario_03.py   # Missing next-hop-self on R3 toward R5
        ├── apply_solution.py       # Restore to known-good (full solution)
        └── README.md
```
