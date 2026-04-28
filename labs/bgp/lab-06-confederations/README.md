# BGP Lab 06 — BGP Confederations

BGP confederation design: public AS 65100 subdivided into sub-AS 65101 (East PEs) and
sub-AS 65102 (Core/West PE), with confederation eBGP between sub-ASes, iBGP full mesh
within each sub-AS, and AS-path hiding for external peers.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.4.a | BGP Confederations — identifier, sub-AS membership, confederation peers |
| 1.5.c | iBGP Scaling — full mesh within sub-AS, next-hop-self placement |

## Prerequisites

- Clean-slate lab (standalone, not chained from lab-05)
- Python 3.8+, `netmiko` library
- All 6 nodes (R1–R6) imported into EVE-NG and started

## Quick Start

```bash
# 1. Import the lab topology
#    File > Import > select labs/bgp/lab-06-confederations.unl in EVE-NG UI

# 2. Start all nodes, then push initial configs (OSPF underlay only — no BGP)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open workbook
workbook.md
```

## Confederation Design Summary

| Router | Sub-AS | Role |
|--------|--------|------|
| R1 | AS 65001 (external) | Customer A CE |
| R2 | Sub-AS 65101 | PE East-1 |
| R3 | Sub-AS 65101 | PE East-2 |
| R4 | Sub-AS 65102 | SP Core |
| R5 | Sub-AS 65102 | PE West (CSR1000v) |
| R6 | AS 65002 (external) | External SP Peer |

Public confederation identifier presented to R1 and R6: **AS 65100**

## Files

```
lab-06-confederations/
├── workbook.md              # Student lab guide (11 sections, 5 tasks, 3 tickets)
├── setup_lab.py             # Push initial configs to all 6 nodes
├── README.md                # This file
├── decisions.md             # Design and build decisions
├── initial-configs/         # Pre-loaded state: IP addressing + OSPF only (no BGP)
│   ├── R1.cfg               # External CE (no OSPF)
│   ├── R2.cfg               # PE East-1, OSPF area 0
│   ├── R3.cfg               # PE East-2, OSPF area 0
│   ├── R4.cfg               # SP Core, OSPF area 0
│   ├── R5.cfg               # PE West CSR1000v, OSPF area 0
│   └── R6.cfg               # External SP Peer (no OSPF)
├── solutions/               # Full solution configs with BGP confederation
│   └── R1.cfg … R6.cfg
├── topology/
│   ├── topology.drawio      # EVE-NG topology diagram
│   └── README.md            # EVE-NG import / export instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py  # Ticket 1: confederation identifier removed from R2
        ├── inject_scenario_02.py  # Ticket 2: R3 iBGP session to R2 removed
        ├── inject_scenario_03.py  # Ticket 3: next-hop-self removed from R5 toward R4
        ├── apply_solution.py      # Restore to known-good solution state
        └── README.md              # Run instructions (no spoilers)
```
