# Fast Convergence Lab 03 — BGP PIC Edge/Core and Additional Paths

Builds on lab-02 (LFA + R-LFA + MPLS LDP) and adds BGP Prefix-Independent
Convergence (PIC) for edge and core routers with BGP Add-Paths for multi-path
advertisement. Covers add-paths configuration, PIC backup selection, edge/core
failure testing, and path identifier inspection.

All five routers run CSR1000v (IOS-XE 17.03.05) with GigabitEthernet1/2/3/4
interface naming.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 1.7.e | BGP PIC (edge and core) |
| 1.7.g | BGP additional and backup path |

## Prerequisites

- lab-02 (IS-IS LFA and IP FRR) completed — initial-configs for this lab are lab-02 solutions
- Python 3.8+ with Netmiko installed (`pip install netmiko`)
- EVE-NG server running with CSR1000v image available
- Lab `.unl` imported into EVE-NG and all nodes started

## Quick Start

```bash
# 1. Import topology into EVE-NG
#    File > Import > lab-03-bgp-pic-and-addpaths.unl

# 2. Push initial configurations (lab-02 solutions — BFD + timers + IS-IS NSF + BGP GR + LFA + R-LFA + MPLS LDP pre-loaded)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook
#    workbook.md
```

## Files

```
lab-03-bgp-pic-and-addpaths/
├── workbook.md                          # Student workbook (11 sections)
├── README.md                            # This file
├── setup_lab.py                         # Initial config automation
├── initial-configs/                     # lab-02 solutions (LFA + R-LFA + MPLS LDP pre-loaded)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── solutions/                           # Full solution configs (adds BGP PIC + Add-Paths)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg
├── topology/
│   └── README.md                        # EVE-NG import/export instructions
├── scripts/fault-injection/
│   ├── inject_scenario_01.py            # Ticket 1 — R2↔R3 additional-paths receive missing
│   ├── inject_scenario_02.py            # Ticket 2 — R2 select backup missing
│   ├── inject_scenario_03.py            # Ticket 3 — R4↔R1 add-paths config omitted
│   ├── apply_solution.py                # Restores known-good state
│   └── README.md                        # Fault injection ops reference
└── meta.yaml                            # Provenance tracking
```
