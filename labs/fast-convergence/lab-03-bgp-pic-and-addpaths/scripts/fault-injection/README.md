# Fault Injection — Fast Convergence Lab 03

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)
- Apply the full solution configuration first (student has completed Tasks 1–7)

## Scenarios

### Ticket 1

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

Target devices: R2 and R3 — removes `additional-paths receive` on the
R2↔R3 iBGP session, breaking add-paths capability negotiation between
these peers. R2 only receives one path for 192.0.2.0/24 from R1.

### Ticket 2

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

Target device: R2 — removes `bgp additional-paths select backup` globally.
Two paths still appear in the BGP table but CEF shows no backup next-hop
because the PIC backup selection directive is missing.

### Ticket 3

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

Target device: R4 — removes both `advertise additional-paths best 2` and
`additional-paths receive` for neighbor 10.0.0.1 (R1). All other iBGP
sessions on R4 work correctly — only the R4↔R1 session is broken.

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
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
