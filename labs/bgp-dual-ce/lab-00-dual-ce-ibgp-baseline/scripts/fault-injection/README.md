# Fault Injection -- BGP Dual-CE Lab 00: Dual-CE iBGP Architecture and Baseline

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)

## Workflow

1. Start the lab and bring it to a known-good full state:

   ```bash
   python3 setup_lab.py --host <eve-ng-ip>          # configure interfaces only
   python3 apply_solution.py --host <eve-ng-ip>      # push full solution configs
   ```

2. Inject one fault to begin a troubleshooting ticket:

   ```bash
   python3 inject_scenario_NN.py --host <eve-ng-ip>
   ```

3. Diagnose using the show commands listed in the workbook ticket.

4. Restore between tickets:

   ```bash
   python3 apply_solution.py --host <eve-ng-ip>
   ```

## Available Scenarios

### Ticket 1

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

Target device: R1

### Ticket 2

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

Target device: R1

### Ticket 3

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

Target device: R1

## Ticket Summary

| Ticket | Target | Symptom | Diagnosis Hint |
|--------|--------|---------|----------------|
| 1 | R1 | iBGP session between R1 and R2 stays in Active state permanently | Check `show bgp neighbors 10.0.0.2` on R2; verify update-source config on R1 |
| 2 | R1 | R1-R3 eBGP session Established but R3 BGP table has no prefixes from R1 | Check `show bgp neighbors 10.1.13.2` on R1 for negotiated address families; inspect address-family ipv4 activation |
| 3 | R1 | R2 BGP table shows eBGP-learned prefix with unresolvable next-hop | Run `show ip bgp` on R2; compare next-hop against R2 routing table; check next-hop-self on R1 |

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

# Soft-reset first (default interface + no router), then restore -- use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node R1

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node R1
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed -- lab not in expected state (inject scripts only) |
