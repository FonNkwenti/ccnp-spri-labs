# MPLS Lab 04: Full Mastery — Capstone I

Capstone build lab — every MPLS blueprint bullet (4.1.a–4.1.e) integrated into a single
end-to-end build. Start from interfaces-only configs and stack IS-IS L2, MPLS LDP, iBGP
with BGP labeled-unicast, eBGP to two CEs, MPLS-TE, and a Tunnel10 with primary dynamic +
secondary explicit path-option (PE1-via-P2). End-state proof: CE1 → CE2 ping over a
labeled core with BGP-free P routers.

## Blueprint Coverage

| Bullet | Description |
|--------|-------------|
| 4.1.a | LDP discovery, session establishment, label distribution |
| 4.1.b | LSP verification (LIB/LFIB inspection, PHP) |
| 4.1.c | Unified BGP (BGP labeled-unicast over iBGP) |
| 4.1.d | BGP-free core architecture (P routers run no BGP) |
| 4.1.e | RSVP-TE tunnels (dynamic + explicit path, autoroute, secondary path-option) |

## Prerequisites

- Read labs 00–03 first — this capstone consolidates their content but does not re-explain
  it. Difficulty is **Advanced**.
- Python 3.10+ with `pip install -r requirements.txt`
- EVE-NG accessible on your network with six IOSv nodes running

## Quick Start

```bash
# 1. Import the .unl file into EVE-NG (File → Import in the web UI)
# 2. Start all nodes and wait ~60 seconds for boot

# 3. Push interfaces-only baseline (clean_slate — no protocols pre-configured)
python3 labs/mpls/lab-04-capstone-config/setup_lab.py --host <eve-ng-ip>

# 4. Open the workbook and start with Task 1
open labs/mpls/lab-04-capstone-config/workbook.md
```

## Files

```
lab-04-capstone-config/
├── workbook.md                         # Capstone tasks, verification, cheatsheet, troubleshooting
├── setup_lab.py                        # Push IP-only initial configs via EVE-NG API
├── README.md                           # This file
├── decisions.md                        # Build decisions and gate outcomes
├── initial-configs/                    # IP addressing only (clean_slate)
│   ├── PE1.cfg  P1.cfg  P2.cfg  PE2.cfg
│   └── CE1.cfg  CE2.cfg
├── solutions/                          # Complete capstone solution
│   ├── PE1.cfg  P1.cfg  P2.cfg  PE2.cfg
│   └── CE1.cfg  CE2.cfg
├── topology/
│   ├── topology.drawio                 # EVE-NG layout reference diagram
│   └── README.md                       # Import/export instructions
└── scripts/fault-injection/
    ├── inject_scenario_01.py           # Ticket 1: TE globally missing on a P router
    ├── inject_scenario_02.py           # Ticket 2: send-label missing on PE2
    ├── inject_scenario_03.py           # Ticket 3: RSVP bandwidth misconfigured on a core link
    ├── apply_solution.py               # Restore all devices to solution state
    └── README.md
```
