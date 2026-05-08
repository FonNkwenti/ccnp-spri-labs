# Fault Injection — SRv6 Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab imported and all 6 nodes started
- `setup_lab.py` run to push known-good initial-configs
- Student has completed all workbook tasks to reach the full solution state
- Python 3.x with `netmiko` and `requests` installed

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>        # all devices
python3 apply_solution.py --host <eve-ng-ip> --node P2   # single device
```
