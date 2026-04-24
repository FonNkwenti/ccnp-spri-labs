# Lab 00: Single-Area OSPFv2 Foundations

Single-area OSPFv2 baseline on three IOSv routers — adjacency formation,
LSA Types 1 and 2, timer tuning, and OSPF vs IS-IS conceptual contrast.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.1 | Describe OSPF operations and compare with IS-IS |

## Prerequisites

- This is lab-00 — no prior lab in this topic required
- EVE-NG lab imported and nodes started (see `topology/README.md`)
- Python deps: `pip install netmiko requests`

## Quick Start

```bash
# 1. Import topology
#    EVE-NG UI → File → Import → topology/lab-00-single-area-ospfv2.unl

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook
workbook.md
```

## Files

```
lab-00-single-area-ospfv2/
├── workbook.md                  Full lab guide (11 sections)
├── setup_lab.py                 Push initial configs via EVE-NG REST API
├── initial-configs/             IP addressing only — student starts here
│   ├── R1.cfg
│   ├── R2.cfg
│   └── R3.cfg
├── solutions/                   Reference solution configs
│   ├── R1.cfg
│   ├── R2.cfg
│   └── R3.cfg
├── topology/
│   ├── topology.drawio          Visual diagram
│   ├── lab-00-single-area-ospfv2.unl  EVE-NG lab (export from EVE-NG)
│   └── README.md                Import/export guide
└── scripts/fault-injection/     Troubleshooting scenario scripts
    ├── inject_scenario_01.py    Ticket 1
    ├── inject_scenario_02.py    Ticket 2
    ├── inject_scenario_03.py    Ticket 3
    ├── apply_solution.py        Restore known-good state
    └── README.md
```

## Next Lab

`lab-01-multiarea-ospfv2` — starts from this lab's solutions. Do not
remove any config before proceeding.
