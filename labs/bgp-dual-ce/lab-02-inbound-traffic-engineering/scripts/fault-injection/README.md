# Fault Injection -- BGP Dual-CE Lab 02: Inbound Traffic Engineering

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

### Ticket 1 -- Prepend on the Wrong eBGP Egress

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
```

The `set as-path prepend 65001 65001` clause is moved from R2's route-map (toward R4)
to R1's route-map (toward R3). Symptom: R3 sees AS-path length 3, R4 sees length 1 --
inbound preference inverts so ISP-B becomes the primary path instead of ISP-A.

### Ticket 2 -- Prepend Value Uses the Neighbor's AS

```bash
python3 inject_scenario_02.py --host <eve-ng-ip>
```

R2's prepend value is changed from `65001 65001` (self-AS) to `65200 65200`
(neighbor-AS, ISP-B). R4's eBGP loop prevention discards the update because its own
AS appears in the path. Symptom: 192.168.1.0/24 disappears entirely from R4's BGP table;
R3 still sees it normally.

### Ticket 3 -- Missing next-hop-self on R3's iBGP to R5

```bash
python3 inject_scenario_03.py --host <eve-ng-ip>
```

R3's iBGP advertisement to R5 stops rewriting the next-hop. R5 receives 192.168.1.0/24
with next-hop 10.1.13.1 (R1's eBGP-facing address), which is not reachable from inside
ISP-A. The BGP path becomes inaccessible -- present in the table but unusable for
forwarding.

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Pushes the full solution configs from `solutions/` to all six devices.
