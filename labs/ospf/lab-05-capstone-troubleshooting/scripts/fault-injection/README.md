# Lab 05 — Fault-Injection Scripts

**For operators and instructors only.** Students do not need these scripts.

---

## Overview

Lab 05 is a troubleshooting capstone. The pre-broken topology is loaded directly by `setup_lab.py`
at the lab root — there are no separate inject scripts. All 5 faults are baked into the
`initial-configs/` configs pushed during lab setup.

---

## apply_solution.py

Restores all 6 devices to the clean known-good state after the troubleshooting exercise.

```bash
# Restore all devices
python3 apply_solution.py --host <eve-ng-ip>

# Restore with soft-reset first (clears stale OSPF state)
python3 apply_solution.py --host <eve-ng-ip> --reset

# Restore a single device
python3 apply_solution.py --host <eve-ng-ip> --node R3

# Single device with soft-reset
python3 apply_solution.py --host <eve-ng-ip> --reset --node R3
```

---

## Planted Faults Reference

| # | Device | Location | Fault | Symptom |
|---|--------|----------|-------|---------|
| 1 | R3 | Gi0/1 | `ip ospf dead-interval 80` (R4 default = 40) | R3-R4 adjacency never reaches FULL; Area 2 unreachable |
| 2 | R5 | ip prefix-list NSSA_EXTERNAL_PREFIX | `permit 192.168.55.0/25` (wrong /25, should be /24) | No Type-7 LSA originated at R5; 192.168.55.0/24 absent from all routers |
| 3 | R2 | router ospf 1 | `area 1 range 172.16.0.0 255.255.254.0` (wrong /23) | 172.16.2.0/24 and 172.16.3.0/24 leak as individual Type-3 LSAs |
| 4 | R5 | Gi0/0 | `ospfv3 1 ipv6 area 3` missing | OSPFv3 adjacency absent; IPv4 works, IPv6 Area-3 routes missing |
| 5 | R3 | router ospf 1 | `distribute-list prefix BLOCK_EXT out static` | 192.168.66.0/24 not redistributed; no route to R6 Lo1 |

---

## Solution Config Location

`../../solutions/R{1-6}.cfg`
