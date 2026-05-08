# Fault Injection -- BGP Dual-CE Lab 01: Transit Prevention Policy

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG
- All nodes must be **started** in EVE-NG
- Python 3.x and `netmiko` installed (`pip install netmiko`)

## Workflow

1. Bring the lab to known-good solution state:

   ```bash
   python3 setup_lab.py --host <eve-ng-ip>
   python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
   ```

2. Inject one fault to begin a ticket:

   ```bash
   python3 scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip>
   ```

3. Diagnose using the show commands in the workbook ticket.

4. Restore between tickets:

   ```bash
   python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
   ```

## Available Scenarios

### Ticket 1 -- Transit Filter Applied to the Wrong Session

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

On R2: filter is removed from eBGP egress (toward R4) and bound to the iBGP session
toward R1. Symptom: R1 loses 10.200.1.0/24 from its BGP table; the leak to R4 persists.

### Ticket 2 -- Route-Map Defined But Not Bound to Neighbor

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

On R1: prefix-list and route-map remain defined, but the
`neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out` directive is missing.
Symptom: 10.200.1.0/24 still leaks to R3 with AS-path `65001 65200`.

### Ticket 3 -- Route-Map Bound Inbound Instead of Outbound

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

On R2: the route-map is bound `in` instead of `out` on the eBGP session to R4.
Symptom: leak to R4 persists; R2 also loses 10.200.1.0/24 from its BGP table because
the inbound filter drops everything except the customer prefix.

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Pushes the full solution configs from `solutions/` to all four devices.
