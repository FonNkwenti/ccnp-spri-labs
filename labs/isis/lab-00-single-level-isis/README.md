# Lab 00: Single-Level IS-IS Foundations

Single-level (L1-only) IS-IS baseline on three IOSv routers — NET addressing,
IIH adjacency formation, DIS election on broadcast LANs, the L1 LSP database,
hello-timer tuning, and IS-IS vs OSPF conceptual contrast.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.3 | Describe IS-IS operations and compare with OSPF |

## Prerequisites

- This is lab-00 — no prior lab in this topic required
- EVE-NG lab imported and nodes started (see `topology/README.md`)
- Python deps: `pip install netmiko requests`

## Quick Start

```bash
# 1. Import topology
#    EVE-NG UI → File → Import → topology/lab-00-single-level-isis.unl

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook
workbook.md
```

## Files

```
lab-00-single-level-isis/
├── workbook.md                  Full lab guide (11 sections)
├── setup_lab.py                 Push initial configs via EVE-NG REST API
├── initial-configs/             IP addressing only — student starts here
│   ├── R1.cfg
│   ├── R2.cfg
│   └── R3.cfg
├── solutions/                   Reference solution configs (L1 IS-IS)
│   ├── R1.cfg
│   ├── R2.cfg
│   └── R3.cfg
├── topology/
│   ├── topology.drawio          Visual diagram
│   ├── lab-00-single-level-isis.unl   EVE-NG lab (export from EVE-NG)
│   └── README.md                Import/export guide
└── scripts/fault-injection/     Troubleshooting scenario scripts
    ├── inject_scenario_01.py    Ticket 1 — NET area-ID typo on R3
    ├── inject_scenario_02.py    Ticket 2 — hello-timer mismatch on R1 Gi0/0
    ├── inject_scenario_03.py    Ticket 3 — is-type level-2-only on R2
    ├── apply_solution.py        Restore known-good state
    └── README.md
```

## Next Lab

`lab-01-multilevel-isis` — starts from this lab's solutions. Do not
remove any config before proceeding; lab-01 promotes R2/R3 to L1/L2 and
moves R3 to area `49.0002`, building on top of this baseline.
