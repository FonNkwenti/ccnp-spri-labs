# Lab 08 — Fault-Injection Scripts

**For operators and instructors only.** Students do not need these scripts.

---

## Overview

Lab 08 is a troubleshooting capstone. The pre-broken topology is loaded directly by
`setup_lab.py` at the lab root — there are no separate inject scripts. All 6 faults are
baked into the `initial-configs/` configs pushed during lab setup.

---

## apply_solution.py

Restores all 7 devices to the clean known-good state (identical to the lab-07 solution)
after the troubleshooting exercise.

```bash
# Restore all devices
python3 apply_solution.py --host <eve-ng-ip>

# Restore with soft-reset first (clears stale BGP/OSPF state)
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device
python3 apply_solution.py --host <eve-ng-ip> --node R5

# Single device with soft-reset
python3 apply_solution.py --host <eve-ng-ip> --reset --node R5
```

---

## Planted Faults Reference

| # | Device | Location | Fault | Symptom |
|---|--------|----------|-------|---------|
| 1 | R5 | router bgp 65100 / af ipv4 | `neighbor 10.0.0.4 next-hop-self` removed | RR-clients on East side cannot install R6/R7 prefixes (NH unreachable) |
| 2 | R2 | neighbor 10.1.12.1 / af ipv4 | route-map FROM-CUST-A-PRIMARY direction `out` instead of `in` | Customer-A prefix arrives without LP=200, community 65100:100, SoO 65001:1 |
| 3 | R6 | neighbor 10.1.56.5 | password `WRONG_PASS` instead of `CISCO_SP` | R5↔R6 session never reaches Established (TCP MD5 reject) |
| 4 | R2 | neighbor 10.1.12.1 / af ipv4 | `maximum-prefix 1 75 restart 5` (limit too low) | R2↔R1 session bounces every 5 min (max-pfx loop) |
| 5 | R2 | neighbor 10.0.0.4 / af ipv4 | `send-community both` removed | R4 (RR) and R5 do not see community 65100:100 on Customer-A's prefix |
| 6 | R7 | router bgp 65003 / af ipv4 flowspec | `neighbor 10.1.57.5 activate` removed (only inside flowspec AFI) | FlowSpec SAFI never negotiated; `show bgp ipv4 flowspec` empty on R5 |

Each fault is on a different device-pair so faults do not mask each other during diagnosis.
The two faults that share R2 (faults 2 and 4) target different layers (RIB-IN policy vs.
session control-plane) and produce divergent symptoms.

---

## Solution Config Location

`../../solutions/R{1-7}.cfg`
