# Lab 03 (3-Node Variant): SR-TE Policies, Constraints, and Automated Steering

Resource-constrained variant of the standard lab-03. Three IOS-XRv 9000 routers (R1, R3, R4) form an SR-TE MPLS core with two IOSv customer edges (CE1, CE2). R2 is removed; all 7 tasks and every 4.3.a/4.3.b exam objective are preserved.

Builds dynamic, explicit, and affinity-constrained SR-TE policies; enables color-based automated steering via BGP extended communities.

## Blueprint Coverage

- **4.3.a** — Configure and verify SR-TE policies (dynamic, explicit, affinity constraints)
- **4.3.b** — Implement SR-TE traffic steering (color-based automated steering, ODN)

## Prerequisites

- Python 3.8+ with `netmiko` installed
- EVE-NG server reachable at the target IP; lab `.unl` imported and nodes started

## Quick Start

```bash
# 1. Import the lab topology into EVE-NG (see topology/README.md)

# 2. Push initial configs
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin Task 1
open workbook.md
```

## Files

```
lab-03-sr-te-3node/
├── workbook.md                        # Lab guide — all 11 sections
├── setup_lab.py                       # Push initial-configs to EVE-NG nodes
├── README.md                          # This file
├── decisions.md                       # Design decisions log
├── meta.yaml                          # Build metadata
├── initial-configs/
│   ├── R1.cfg                         # Core with IS-IS, SR-MPLS, BFD, TI-LFA
│   ├── R3.cfg                         # Core with IS-IS, SR-MPLS, BFD, TI-LFA
│   ├── R4.cfg                         # Core with IS-IS, SR-MPLS, BFD, TI-LFA
│   ├── CE1.cfg                        # IP-only; student configures BGP
│   └── CE2.cfg                        # IP-only; student configures BGP
├── solutions/
│   ├── R1.cfg                         # SR-TE policies, ODN, BGP, TE metric override
│   ├── R3.cfg                         # RP_CE2_IN attaches color:10, RED affinity, BGP
│   ├── R4.cfg                         # RED affinity on L3
│   ├── CE1.cfg
│   └── CE2.cfg
├── topology/
│   ├── topology.drawio                # EVE-NG visual topology (3 core + 2 CE)
│   └── README.md                      # EVE-NG import instructions
└── scripts/
    └── fault-injection/
        ├── inject_scenario_01.py      # Ticket 1: color stripped at R1
        ├── inject_scenario_02.py      # Ticket 2: RED affinity missing on R4
        ├── inject_scenario_03.py      # Ticket 3: color never attached at R3
        ├── apply_solution.py          # Restore solution state
        └── README.md
```

## Differences from Standard lab-03

| Aspect | Standard (4-node) | 3-Node Variant |
|--------|-------------------|----------------|
| Core routers | R1, R2, R3, R4 | R1, R3, R4 |
| RAM required | ~66 GB guest | ~49 GB guest |
| L5 IS-IS metric | 10 (default) | **30** (forces IGP via R4) |
| Affinities | RED (L3), BLUE (L2) | RED (L3) only |
| TE metric override | R1 Gi0/0/0/0 (L1→R2) | R1 Gi0/0/0/1 (L4→R4) |
| LDP coexistence | Yes (from lab-02) | No (standalone variant) |
| All 7 tasks | ✓ | ✓ |
| All 4.3.a/4.3.b objectives | ✓ | ✓ |
