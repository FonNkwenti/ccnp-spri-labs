# Fault Injection — OSPF Lab 01: Multiarea OSPFv2

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)

## Available Scenarios

### Scenario 01 — Ticket 1

Target device: R3

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

### Scenario 02 — Ticket 2

Target device: R2

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

> **Note:** Restoration for Scenario 02 requires `--reset` (see Restore section below).

### Scenario 03 — Ticket 3

Target device: R3

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

Optional flags:

| Flag | Description |
|------|-------------|
| `--lab-path <path>` | Override the EVE-NG lab path (default: `ospf/lab-01-multiarea-ospfv2.unl`) |
| `--skip-preflight` | Skip the known-good state check (use only if you know the lab state) |

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
python3 apply_solution.py --host <eve-ng-ip> --reset   # full write-erase + restore
```

Use `--reset` after Scenario 02. It performs a write-erase on the affected device
before pushing the solution config, which is required to cleanly remove policy objects
that cannot be negated by a config push alone.

## Workflow

```bash
python3 apply_solution.py --host <eve-ng-ip>           # ensure known-good state
python3 inject_scenario_01.py --host <eve-ng-ip>       # inject Ticket 1
# ... diagnose and fix using show commands ...
python3 apply_solution.py --host <eve-ng-ip>           # restore before next ticket
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state (inject scripts only) |
