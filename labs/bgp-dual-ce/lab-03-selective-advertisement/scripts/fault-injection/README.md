# Fault Injection -- BGP Dual-CE Lab 03: Selective Prefix Advertisement

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- The lab `.unl` file must already be **imported** into EVE-NG
- All six nodes (R1-R6) must be **started** in EVE-NG
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

### Ticket 1 -- LP Route-Map Direction Wrong on R1

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

R1's `LOCAL_PREF_FROM_R3` is unbound from inbound and rebound outbound on neighbor
10.1.13.2. The eBGP path to 0.0.0.0/0 from R3 stays at LP=100; the iBGP-learned default
from R2 carries LP=200 (R2's inbound policy is still correct). R1's best-path for the
default flips to ISP-B via iBGP -- the opposite of the design intent.

### Ticket 2 -- /25 Visible at R3 But Absent From R5

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

R3 gains an outbound prefix-list `ONLY_AGGREGATE` on its iBGP session to R5 that permits
only `192.168.1.0/24` exact. R3 still has the /25 (`192.168.1.0/25`) in its BGP table from
R1, but the new filter strips the more-specific from advertisements to R5. Symptom: R5
sees only the aggregate and cannot make the longest-match selection inside ISP-A.

### Ticket 3 -- /25-High Missing From R4

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

The `ip route 192.168.1.128 255.255.255.128 Null0` static is removed from R2. Without an
exact RIB entry, the BGP `network 192.168.1.128 mask 255.255.255.128` statement cannot
install the prefix into the BGP table. R2's BGP table loses the /25-high entirely, R4
never receives it, and ISP-B loses its longest-match path into the upper half of the
customer's address space.

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Pushes the full solution configs from `solutions/` to all six devices.
