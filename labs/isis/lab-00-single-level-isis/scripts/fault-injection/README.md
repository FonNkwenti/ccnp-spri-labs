# Fault Injection — IS-IS Lab 00: Single-Level IS-IS Foundations

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes (R1, R2, R3) must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 — NET area-ID typo on R3
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 — IIH timer mismatch on R1 Gi0/0
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 — is-type level-2-only on R2
```

## Restore

```bash
# Restore all devices to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# Soft-reset first (default interfaces + no router isis), then restore — use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node R3

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node R2
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state (inject scripts only) |
