# Lab 04: PCE Path Computation, SRLG, and Tree SID

Centralized SR-TE path computation via PCEP and BGP-LS. Adds a dedicated PCE controller (10.0.0.99) peered with R2, configures SRLG-disjoint primary+backup pairs, and provisions a P2MP Tree SID rooted at R1 with leaves R3 and R4.

## Blueprint Coverage

- **4.3.c** - PCE-based path calculation (BGP-LS topology feed, PCEP delegation)
- **4.3.d** - SRLG (Shared Risk Link Groups) for disjoint-path constraints
- **4.3.e** - Tree SID (SR-MPLS P2MP, configuration + behavioral caveat)

## Prerequisites

- Completes from: `lab-03-sr-te-policies-and-steering` (progressive)
- Python 3.8+ with `netmiko` installed
- EVE-NG server reachable at the target IP; lab `.unl` imported and all nodes (including PCE) started

## Quick Start

```bash
# 1. Import the lab topology into EVE-NG (see topology/README.md)

# 2. Push initial configs (chained from lab-03 + new PCE node + L6 IP-only on R2)
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and begin Task 1
open workbook.md
```

## Files

```
lab-04-pce-srlg-tree-sid/
|-- workbook.md                        # Lab guide - all 11 sections
|-- setup_lab.py                       # Push initial-configs to EVE-NG nodes
|-- README.md                          # This file
|-- decisions.md                       # Design decisions log
|-- meta.yaml                          # Build metadata
|-- initial-configs/
|   |-- R1.cfg                         # Lab-03 R1 solution (PCC config = student task)
|   |-- R2.cfg                         # Lab-03 R2 solution + L6 IP-only
|   |-- R3.cfg                         # Lab-03 R3 solution
|   |-- R4.cfg                         # Lab-03 R4 solution
|   |-- CE1.cfg
|   |-- CE2.cfg
|   `-- PCE.cfg                        # IP-only stub (Lo0 + L6)
|-- solutions/
|   |-- R1.cfg                         # PCC + SRLG + COLOR_30/COLOR_40 disjoint
|   |-- R2.cfg                         # BGP-LS to PCE, static redist, SRLG
|   |-- R3.cfg                         # PCC + SRLG (Tree SID leaf)
|   |-- R4.cfg                         # PCC + SRLG (Tree SID leaf)
|   |-- CE1.cfg
|   |-- CE2.cfg
|   `-- PCE.cfg                        # BGP-LS, PCE process, Tree SID policy
|-- topology/
|   |-- topology.drawio                # EVE-NG visual topology (7 nodes, L1-L8)
|   `-- README.md                      # EVE-NG import instructions
`-- scripts/
    `-- fault-injection/
        |-- inject_scenario_01.py      # Ticket 1: BGP-LS topology drift
        |-- inject_scenario_02.py      # Ticket 2: PCEP session unreachable
        |-- inject_scenario_03.py      # Ticket 3: SRLG group collision
        |-- apply_solution.py          # Restore solution state
        `-- README.md
```
