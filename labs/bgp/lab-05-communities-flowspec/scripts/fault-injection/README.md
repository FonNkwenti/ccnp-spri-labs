# Fault Injection -- BGP Lab 05: BGP Communities and FlowSpec

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
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Scenarios

### Ticket 1

**Target device:** R4

**Command:**
```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

Refer to workbook.md Section 9, Ticket 1 for the symptom description and diagnosis steps.

---

### Ticket 2

**Target device:** R5

**Command:**
```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

Refer to workbook.md Section 9, Ticket 2 for the symptom description and diagnosis steps.

---

### Ticket 3

**Target device:** R6

**Command:**
```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

Refer to workbook.md Section 9, Ticket 3 for the symptom description and diagnosis steps.

---

## Restore

```bash
# Restore all devices to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# Soft-reset first (default interface + no router), then restore -- use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node R4

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node R6
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed -- lab not in expected state (inject scripts only) |
