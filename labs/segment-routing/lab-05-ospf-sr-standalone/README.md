# Lab 05 — OSPF Segment Routing Extensions (Standalone)

OSPF SR extensions on a four-router IOS-XRv 9000 core. Proves that SR forwarding
is IGP-agnostic: same label plane, same SID indices, same MPLS traceroute as the
IS-IS labs (00-04) — different IGP control plane.

## Blueprint Coverage

- **4.2.a** — Routing protocol extensions: OSPF (`segment-routing mpls`, prefix SID
  allocation via Opaque LSA type-7/8, SRGB 16000-23999)

## Prerequisites

- **Type:** Standalone (clean slate — no dependency on previous labs)
- Python 3.9+, `netmiko`, `requests` (`pip install netmiko requests`)
- EVE-NG lab imported and all four XRv9k nodes started (8-12 min boot time)

## Quick Start

```bash
# 1. Import the topology into EVE-NG
#    File > Import > select topology/lab-05-ospf-sr-standalone.unl
#    Start all nodes; wait for RP/0/0/CPU0 prompts (~10 min)

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
workbook.md
```

## Files

```
lab-05-ospf-sr-standalone/
├── workbook.md                        Full lab guide (11 sections)
├── setup_lab.py                       Pushes initial configs via EVE-NG API
├── README.md                          This file
├── initial-configs/
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg Interface addressing only
├── solutions/
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg Full OSPF SR solution
├── topology/
│   ├── topology.drawio                Draw.io diagram
│   └── README.md                      EVE-NG import/export guide
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py      Ticket 1 fault
        ├── inject_scenario_02.py      Ticket 2 fault
        ├── inject_scenario_03.py      Ticket 3 fault
        ├── apply_solution.py          Restore to known-good
        └── README.md                  Run instructions only
```
