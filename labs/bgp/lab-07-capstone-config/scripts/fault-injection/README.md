# Fault Injection Scripts — BGP Lab 07: BGP Capstone Configuration

These scripts inject pre-defined faults into the running lab for troubleshooting practice.
Consult `workbook.md` Section 9 for the full scenario descriptions and diagnostic hints.

**No spoilers here.** The README only tells you which device is targeted and how to run the script.

## Prerequisites

- Lab is fully built and in solution state (run `apply_solution.py` to verify)
- Python 3.8+, `netmiko` library installed
- EVE-NG server reachable at `--host <ip>`
- All 7 nodes started (R1-R6 IOSv, R5/R7 CSR1000v IOS-XE)

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
| `inject_scenario_01.py` | R4 (Route Reflector) | next-hop-self misconfiguration on RR client session |
| `inject_scenario_02.py` | R2 (PE) | send-community removed on iBGP session to RR |
| `inject_scenario_03.py` | R5 (PE, IOS-XE) | maximum-prefix limit causes session to continuously flap |

## Diagnostic Show Commands

### Scenario 01

```
show ip bgp 172.16.1.0/24          ! on R5 — check next-hop and best/installed markers
show ip route 172.16.1.0           ! on R5 — confirm prefix absent from RIB
show ip bgp neighbors 10.0.0.5     ! on R4 — review advertised attributes
```

### Scenario 02

```
show ip bgp 172.16.1.0/24          ! on R5 — verify Communities line is absent
show ip bgp 172.16.1.0/24          ! on R4 — compare community presence vs. R5
show ip bgp neighbors 10.0.0.4 advertised-routes  ! on R2 — check outbound attributes
```

### Scenario 03

```
show ip bgp summary                 ! on R5 — watch R7 neighbor state cycling
show log                            ! on R5 — look for BGP max-prefix notifications
show ip bgp neighbors 10.1.57.7     ! on R5 — check max-prefix configuration
show ip bgp 172.16.7.0/24          ! on R5 — confirm prefix never stabilises
```

## Resetting to Known-Good State

```bash
# Restore all devices
python3 apply_solution.py --host <eve-ng-ip>

# Restore a single device
python3 apply_solution.py --host <eve-ng-ip> --node R4

# Soft-reset before restore (clears running-config fragments)
python3 apply_solution.py --host <eve-ng-ip> --reset
```

## Options

```
--host <eve-ng-ip>          EVE-NG server IP address (required)
--lab-path <path>           Lab .unl path override (default: auto-discovered)
--skip-preflight            Skip pre-flight sanity check
```

For `apply_solution.py`:

```
--host <eve-ng-ip>          EVE-NG server IP address (required)
--node <R1|R2|...|R7>       Restore a single device only (default: all)
--reset                     Soft-reset the device config before restoring
--lab-path <path>           Lab .unl path override (default: ccnp-spri/bgp/lab-07-capstone-config.unl)
```
