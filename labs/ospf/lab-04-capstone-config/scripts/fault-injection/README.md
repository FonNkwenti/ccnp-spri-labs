# Fault Injection Scripts — Lab 04: OSPF Full Protocol Mastery - Capstone I

## Prerequisites

- EVE-NG lab imported and all nodes (R1–R6) started
- Python 3.8+ with `netmiko` installed
- EVE-NG server reachable from your workstation
- Lab is in the **solution state** before injecting any scenario

---

## Available Scenarios

### Scenario 01 — R3

Inject:

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

Restore:

```bash
python3 apply_solution.py --host <eve-ng-ip> --node R3
```

---

### Scenario 02 — R3

Inject:

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

Restore:

```bash
python3 apply_solution.py --host <eve-ng-ip> --node R3
```

---

### Scenario 03 — R2

Inject:

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

Restore:

```bash
python3 apply_solution.py --host <eve-ng-ip> --node R2
```

---

## Restore Full Lab (All Devices)

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Add `--reset` to perform a soft-reset (clear running-config state) before pushing solution configs:

```bash
python3 apply_solution.py --host <eve-ng-ip> --reset
```

---

## Optional Arguments

All scripts accept:

| Argument | Description |
|---|---|
| `--host <ip>` | EVE-NG server IP (required) |
| `--lab-path <path>` | Override auto-discovered lab path (e.g. `ospf/lab-04-capstone-config.unl`) |
| `--skip-preflight` | Skip pre-injection state check (inject scripts only) |
| `--node <name>` | Restore a single device (`apply_solution.py` only) |
| `--reset` | Soft-reset device before restore (`apply_solution.py` only) |

---

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state |

---

## Workflow

1. Start all nodes in EVE-NG.
2. Run `apply_solution.py` to ensure the lab is in the known-good state.
3. Run any `inject_scenario_0N.py` to activate a troubleshooting scenario.
4. Troubleshoot the fault using standard IOS `show` and `debug` commands.
5. Run `apply_solution.py` to restore before starting the next scenario.
