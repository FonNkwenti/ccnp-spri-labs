# BGP Lab 03: Inter-Domain Security and Maximum-Prefix

Hardens all eBGP sessions in the three-AS SP topology with GTSM, MD5 authentication,
and maximum-prefix enforcement.

## Blueprint Coverage

- 1.5.e — TTL Security (GTSM) on eBGP sessions
- 1.5.f — BGP MD5 authentication and maximum-prefix enforcement

## Prerequisites

- Lab 02 (eBGP Multihoming) solutions loaded — this lab chains from that state
- Python 3.8+, Netmiko: `pip install netmiko requests`
- EVE-NG lab imported and all nodes started

## Quick Start

```bash
# 1. Import topology into EVE-NG via File > Import (.unl not provided — build in EVE-NG UI)

# 2. Push initial configs (lab-02 solutions)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook and complete the tasks
open workbook.md
```

## Files

```
lab-03-interdomain-security/
├── workbook.md               ← Full lab guide (11 sections)
├── setup_lab.py              ← Pushes initial-configs via EVE-NG REST API
├── README.md                 ← This file
├── initial-configs/          ← Pre-loaded state (lab-02 solutions, no security)
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── solutions/                ← Complete solution with all security controls
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   └── R6.cfg
├── scripts/fault-injection/  ← Three troubleshooting tickets
│   ├── inject_scenario_01.py ← Ticket 1: GTSM missing on R1 toward R3
│   ├── inject_scenario_02.py ← Ticket 2: MD5 password mismatch
│   ├── inject_scenario_03.py ← Ticket 3: Max-prefix silent shutdown
│   ├── apply_solution.py     ← Restore to solution state
│   └── README.md
└── topology/
    ├── topology.drawio        ← Draw.io topology diagram
    └── README.md              ← EVE-NG import/export instructions
```
