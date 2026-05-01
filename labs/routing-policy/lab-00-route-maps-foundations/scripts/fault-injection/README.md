# Fault Injection -- Routing Policy Lab 00: Route-Maps Foundations

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

## Scenario Index

### Ticket 1

- **Target device:** R1
- **Inject:** `python3 inject_scenario_01.py --host <eve-ng-ip>`
- **Restore:** `python3 apply_solution.py --host <eve-ng-ip>`

**Symptom:** R1's BGP table shows 0 prefixes received from R4 (10.1.14.4).
Both 172.20.4.0/24 and 172.20.5.0/24 are absent.

**Diagnosis path:**
1. `show ip bgp neighbors 10.1.14.4 routes` -- confirm 0 entries
2. `show route-map FILTER_R4_IN` -- note which sequences are present
3. `show ip bgp neighbors 10.1.14.4` -- confirm neighbor is Established

### Ticket 2

- **Target device:** R1
- **Inject:** `python3 inject_scenario_02.py --host <eve-ng-ip>`
- **Restore:** `python3 apply_solution.py --host <eve-ng-ip>`

**Symptom:** R1's BGP table shows 0 prefixes received from R4 (10.1.14.4).
Both R4 loopback prefixes are absent even though the route-map has both
a deny and a permit sequence.

**Diagnosis path:**
1. `show ip bgp neighbors 10.1.14.4 routes` -- confirm 0 entries
2. `show route-map FILTER_R4_IN` -- check match clause details in seq 10
3. `show ip prefix-list PFX_R4_LO2_EXACT` -- inspect the prefix boundary

### Ticket 3

- **Target device:** R1
- **Inject:** `python3 inject_scenario_03.py --host <eve-ng-ip>`
- **Restore:** `python3 apply_solution.py --host <eve-ng-ip>`

**Symptom:** R1's BGP table now shows BOTH R4 prefixes (filter not applied
on inbound). R4 may no longer receive 172.16.1.0/24 from R1.

**Diagnosis path:**
1. `show ip bgp neighbors 10.1.14.4 routes` -- note both prefixes present
2. `show ip bgp neighbors 10.1.14.4` -- confirm route-map direction
3. Compare expected vs. actual filter application direction

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed -- lab not in expected state (inject scripts only) |
