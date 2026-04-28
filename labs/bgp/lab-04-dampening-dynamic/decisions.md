# Design Decisions — BGP Lab 04: Route Dampening and Dynamic Neighbors

## Dynamic Neighbor Demo Link (L8)

Added a new point-to-point link L8 between R1 Gi0/2 (10.99.0.1/30) and R2 Gi0/3
(10.99.0.2/30) to demonstrate dynamic BGP neighbor provisioning. Using R1 as the
"simulated customer" avoids adding a seventh router to the topology. R1 peers from
10.99.0.1 (which falls within R2's listen range 10.99.0.0/24) while its primary
eBGP session via Gi0/0 continues unaffected. This is a valid lab demonstration — in
production, the dynamic peer would be a separate customer CPE.

## Dampening on R5 Only

BGP dampening is configured only on R5 (PE West, CSR1000v) facing R6 (AS 65002).
Dampening on R2 and R3 facing R1 (Customer A) was excluded to maintain clarity:
the lab focuses on eBGP inter-domain stability, and Customer A prefixes are already
controlled via LOCAL_PREF and AS-path prepend from lab-02. Mixing dampening into the
Customer A path would complicate the troubleshooting scenarios.

## IOS Compatibility — New Commands

The following commands were not in `ios-compatibility.yaml` at build time. They are
verified against Cisco IOS release notes as standard 15.x+ features:

- `bgp dampening [params]` — context: router-bgp — pass on IOSv 15.9 and CSR1000v 17.x
- `bgp listen range <prefix> peer-group <name>` — context: router-bgp — pass on IOSv 15.9
- `bgp listen limit <N>` — context: router-bgp — pass on IOSv 15.9 and CSR1000v 17.x

These should be added to `ios-compatibility.yaml` in the next skills submodule update.

## Explicit Dampening Parameters

`bgp dampening 15 750 2000 60` uses the same values as the default, but the explicit
form is used in the lab so students learn the parameter order and can tune them.
The workbook task also asks for explicit configuration to make the `show` outputs
verifiable (the parameters block appears in `show ip bgp dampening parameters`
regardless of whether defaults or explicit values are used).

## Model gate — 2026-04-28
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS
