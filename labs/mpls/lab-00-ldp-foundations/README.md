# MPLS Lab 00 — LDP Foundations and Label Distribution

> **Difficulty:** Foundation · **Time:** 75 min · **Devices:** 4
> (PE1, P1, P2, PE2) · **Blueprint refs:** 4.1, 4.1.a · **Type:**
> progressive (chain root for the MPLS topic)

This is the foundation lab for the MPLS topic. You will:

1. Bring up IS-IS L2 across a four-router diamond core.
2. Enable MPLS LDP globally and per-interface.
3. Inspect the LIB, the LFIB, LDP discovery and sessions, and the
   `implicit-null` PHP advertisement.
4. Diagnose two control-plane faults — a flapping LDP session caused
   by an unreachable router-id, and an asymmetric LDP bindings table
   caused by a missing `mpls ip`.

## Quick start

```bash
# 1. Import the lab into EVE-NG (see topology/README.md).
# 2. Push the IP-only baseline:
python3 setup_lab.py --host <eve-ng-ip>

# 3. Open the workbook and follow Tasks 1..8:
$EDITOR workbook.md

# 4. When you reach Section 9 (Troubleshooting Tickets):
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
# diagnose + fix Ticket 1
python3 scripts/fault-injection/verify_scenario_01.py --host <eve-ng-ip>

python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
# diagnose + fix Ticket 2
python3 scripts/fault-injection/verify_scenario_02.py --host <eve-ng-ip>
```

## Files

| Path                                       | Purpose                                         |
|--------------------------------------------|-------------------------------------------------|
| `workbook.md`                              | Step-by-step lab guide with all 11 sections     |
| `topology/topology.drawio`                 | Editable diagram (Draw.io, dark navy theme)     |
| `topology/README.md`                       | Devices/links table + EVE-NG import steps       |
| `initial-configs/*.cfg`                    | IP-only baseline (loaded by `setup_lab.py`)     |
| `solutions/*.cfg`                          | Reference end-state per device                  |
| `scripts/fault-injection/inject_*.py`      | Plant Ticket 1 / Ticket 2 faults                |
| `scripts/fault-injection/verify_*.py`      | Confirm a ticket is fixed                       |
| `setup_lab.py`                             | Push initial configs via EVE-NG REST + console  |
| `meta.yaml`                                | Lab manifest (CI/index)                         |
| `decisions.md`                             | Build-time provenance + model-gate audit log    |

## Exit codes

`setup_lab.py` and the fault scripts share `eve_ng.py` exit codes:
0 success, 1 generic, 2 EVE-NG unreachable, 3 lab not found, 4 node
not found, 5 verifier failed, 6 fault injection failed.
