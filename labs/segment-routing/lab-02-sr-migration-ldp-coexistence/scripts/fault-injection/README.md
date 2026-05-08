# Fault Injection — Segment Routing Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)
- The lab must be in the **solution state** before injecting a fault:
  run `apply_solution.py` to reach that state

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 — targets R3
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 — targets R2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 — targets R4
```

## Restore

```bash
# Restore all devices to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# Soft-reset first (default interface + no router), then restore — use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node R1

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node R1
```

## Workflow

```
apply_solution.py          # bring lab to solution state
inject_scenario_01.py      # inject Ticket 1
  ... diagnose and fix ...
apply_solution.py          # restore before next ticket
inject_scenario_02.py      # inject Ticket 2
  ... diagnose and fix ...
apply_solution.py          # restore before next ticket
inject_scenario_03.py      # inject Ticket 3
  ... diagnose and fix ...
apply_solution.py          # final restore
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state (inject scripts only) |
