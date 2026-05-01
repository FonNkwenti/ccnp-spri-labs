# Fault Injection Scripts — RPL vs Route-Maps (lab-02-rpl-vs-route-maps)

Ops-only reference. These scripts inject troubleshooting scenarios into the live
lab environment for exam-style practice. Do not share scenario details with students
before they attempt to diagnose the fault.

## Prerequisites

- EVE-NG lab imported and all nodes started (R1, R2, R3, R4, XR1, XR2)
- Python 3.8+ with `netmiko` and `requests` installed:
  ```
  pip install netmiko requests
  ```
- Network connectivity from your workstation to the EVE-NG server

## Workflow

1. Restore the lab to the known-good state (always do this before injecting):
   ```
   python3 apply_solution.py --host <eve-ng-ip>
   ```
2. Inject a scenario:
   ```
   python3 inject_scenario_0N.py --host <eve-ng-ip>
   ```
3. Have the student diagnose and resolve the fault.
4. Restore the lab again when done:
   ```
   python3 apply_solution.py --host <eve-ng-ip>
   ```

---

## Scenario 01

**Target device:** XR1

**Inject:**
```
python3 inject_scenario_01.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Scenario 02

**Target device:** R2

**Inject:**
```
python3 inject_scenario_02.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Scenario 03

**Target device:** XR1

**Inject:**
```
python3 inject_scenario_03.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Additional Options

All inject scripts support:

| Flag | Description |
|---|---|
| `--host <ip>` | EVE-NG server IP (required) |
| `--lab-path <path>` | Override auto-discovery with a specific .unl path |
| `--skip-preflight` | Bypass pre-injection state check (use with caution) |

`apply_solution.py` additionally supports:

| Flag | Description |
|---|---|
| `--reset` | Soft-reset IOS devices before restoring (clears stale interface/routing config) |
| `--node <name>` | Restore a single device only (e.g. `--node R2`) |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed -- lab not in expected state |
