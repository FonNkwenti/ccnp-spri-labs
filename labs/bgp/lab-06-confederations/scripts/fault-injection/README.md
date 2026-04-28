# Fault Injection Scripts — BGP Lab 06: BGP Confederations

These scripts inject pre-defined faults into the running lab for troubleshooting practice.
Consult `workbook.md` Section 9 for the full scenario descriptions and diagnostic hints.

**No spoilers here.** The README only tells you which device is targeted and how to run the script.

## Prerequisites

- Lab is fully built and in solution state (run `apply_solution.py` to verify)
- Python 3.8+, `netmiko` library installed
- EVE-NG server reachable at `--host <ip>`
- All 6 nodes started

## Workflow

```bash
# 1. Ensure lab is in known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject a fault scenario
python3 inject_scenario_01.py --host <eve-ng-ip>

# 3. Diagnose (see workbook.md Section 9 for hints)

# 4. Restore to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# 5. Repeat for next scenario
```

## Scenarios

| Script | Target Device | Fault Category |
|--------|---------------|----------------|
| `inject_scenario_01.py` | R2 (PE East-1) | Confederation identifier misconfiguration |
| `inject_scenario_02.py` | R3 (PE East-2) | iBGP session removal (full-mesh broken) |
| `inject_scenario_03.py` | R5 (PE West) | next-hop-self misconfiguration |

## Options

```
--host <eve-ng-ip>          EVE-NG server IP address (required)
--lab-path <path>           Lab .unl path override (default: auto-discovered)
--skip-preflight            Skip pre-flight sanity check
```

For `apply_solution.py`:

```
--host <eve-ng-ip>          EVE-NG server IP address (required)
--node <R1|R2|...|R6>       Restore a single device only (default: all)
--reset                     Soft-reset the device config before restoring
```
