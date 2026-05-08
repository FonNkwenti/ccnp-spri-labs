# Fault Injection — MPLS Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
```

## Verify Your Fix

```bash
python3 verify_scenario_01.py --host <eve-ng-ip>   # reports: LDP session stable
python3 verify_scenario_02.py --host <eve-ng-ip>   # reports: LDP bindings symmetric
```

## Restore

```bash
# Restore all affected devices to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# Soft-reset first (default interface + no router), then restore — use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node P1
python3 apply_solution.py --host <eve-ng-ip> --node P2

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node P1
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state (inject scripts only) |
| 5 | Verifier check failed — fix not confirmed (verify scripts only) |
