# Fault Injection -- Routing-Policy Lab 04: BGP Filtering and Steering

Each script injects one fault into the BGP filtering and steering lab. Work
through the corresponding ticket in `workbook.md` Section 9 before looking at
the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG (one-time manual step via EVE-NG web UI)
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)
- Run `python3 apply_solution.py --host <eve-ng-ip>` to confirm the lab starts from a known-good state

## Inject a Fault

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```
# Restore all devices to known-good state
python3 apply_solution.py --host <eve-ng-ip>

# Soft-reset first (default interface + no router), then restore -- use when a fault
# leaves stale running-config state that a plain config push cannot undo
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device only (faster for targeted fixes)
python3 apply_solution.py --host <eve-ng-ip> --node R3

# Soft-reset + restore a single device
python3 apply_solution.py --host <eve-ng-ip> --reset --node R3
```

Note: `--reset` is applied only to IOS devices (R1-R4). XR1 and XR2 are always
restored via config push only.

## Available Scenarios

| Script                 | Ticket   | Target | Fault Description                                      |
|------------------------|----------|--------|--------------------------------------------------------|
| `inject_scenario_01.py` | Ticket 1 | R3     | PFX_PREFER_172_20_4 has wrong prefix length (/25 instead of /24) |
| `inject_scenario_02.py` | Ticket 2 | R3     | R3_TO_R4_OUT applied to iBGP peer 10.0.0.1 instead of eBGP peer 10.1.34.4 |
| `inject_scenario_03.py` | Ticket 3 | R1     | R1_TO_R4_OUT uses set local-preference 200 instead of set as-path prepend |

## Scenario Details

### Scenario 01 -- PFX_PREFER_172_20_4 Wrong Prefix Length (R3)

The prefix-list entry for 172.20.4.0/24 is changed to 172.20.4.0/25. Route-map
STEER_R4_IN seq 10 matches this list, and is applied inbound on R3 from R4
(10.1.34.4). Because the /25 never matches the /24 prefix R4 advertises, the
`set local-preference 200` action is never executed. All AS 65100 routers lose
the elevated LOCAL_PREF signal on 172.20.4.0/24 and revert to default
best-path selection for that prefix.

Diagnosis: Check `show ip prefix-list PFX_PREFER_172_20_4` on R3 and compare
against `show ip bgp 172.20.4.0/24` LOCAL_PREF values on R3 and R1.
See workbook.md Section 9, Ticket 1 for the full diagnosis walkthrough.

### Scenario 02 -- R3_TO_R4_OUT Applied to Wrong Neighbor (R3)

Route-map R3_TO_R4_OUT (which sets MED 50 for the 172.16.0.0/16 aggregate) is
removed from eBGP neighbor 10.1.34.4 and mistakenly applied to iBGP neighbor
10.0.0.1. MED is only meaningful on eBGP updates, so the route-map on the iBGP
peer has no useful effect. R4 receives 172.16.0.0/16 from R3 with the default
MED (0 or absent), and the intended MED-based traffic steering is lost.

Diagnosis: Check `show ip bgp neighbors 10.1.34.4 advertised-routes` and
`show ip bgp neighbors 10.0.0.1 advertised-routes` on R3. Verify MED on R4
with `show ip bgp 172.16.0.0`.
See workbook.md Section 9, Ticket 2 for the full diagnosis walkthrough.

### Scenario 03 -- R1_TO_R4_OUT Wrong Attribute: LOCAL_PREF Instead of AS-Path Prepend (R1)

Route-map R1_TO_R4_OUT seq 10 is configured to `set local-preference 200`
instead of `set as-path prepend 65100 65100 65100`. LOCAL_PREF is a well-known
discretionary attribute that is stripped before sending eBGP updates. R4 never
receives the LOCAL_PREF value, so R1's AS path for 172.16.1.0/24 remains one
hop (65100) -- the same length as R3's path. R4 falls back to tie-breaking
(lowest router-ID or MED) rather than preferring R3 via a shorter AS path.

Diagnosis: Check `show ip bgp 172.16.1.0/24` on R4 and inspect the AS_PATH
attribute for R1's and R3's paths. Verify route-map content on R1 with
`show route-map R1_TO_R4_OUT`.
See workbook.md Section 9, Ticket 3 for the full diagnosis walkthrough.

## Exit Codes

| Code | Meaning                                                         |
|------|-----------------------------------------------------------------|
| 0    | Success                                                         |
| 1    | Partial restore failure (`apply_solution.py` only)             |
| 2    | `--host` not provided (placeholder value detected)             |
| 3    | EVE-NG connectivity or port discovery error                     |
| 4    | Pre-flight check failed -- lab not in expected state (inject scripts only) |
