# Lab 04: OSPF Full Protocol Mastery — Capstone I

**Exam:** 300-510 SPRI | **Chapter:** OSPF | **Difficulty:** Advanced | **Time:** 120 min

## What You Build

A complete dual-stack (OSPFv2 + OSPFv3) multiarea OSPF domain from a clean IP-only baseline:

- **Area 1** (R1, R2 Gi0/0): Standard area with three /24 loopbacks on R1
- **Area 0** (R2 Gi0/1, R3 Gi0/0): Backbone
- **Area 2** (R3 Gi0/1, R4): Totally stubby — R4 receives only a default route
- **Area 3** (R3 Gi0/2, R5): NSSA — R5 redistributes an external prefix as Type-7
- **External**: R3 (ASBR) redistributes R6's prefixes as Type-5, summarized to /16

## Quick Start

```bash
# 1. Import lab-04-capstone-config.unl into EVE-NG and start all nodes
# 2. Push initial configs (IP-only — no routing protocols pre-configured)
python setup_lab.py --host <eve-ng-ip>

# 3. Build the OSPF domain from scratch — see workbook.md for objectives
```

## Key Design Parameters

| Element | Value |
|---------|-------|
| OSPF process | 1 (both OSPFv2 and OSPFv3) |
| Area 2 type | Totally stubby (`area 2 stub no-summary` on R3, `area 2 stub` on R4) |
| Area 3 type | NSSA (`area 3 nssa` on both R3 and R5) |
| IPv4 inter-area summary | `172.16.0.0/21` originated by R2 ABR |
| IPv6 inter-area summary | `2001:db8:1::/48` originated by R2 ABR |
| IPv4 external summary | `192.168.0.0/16` originated by R3 ASBR |
| IPv6 external summary | `2001:db8:66::/48` originated by R3 ASBR |
| NSSA external (R5) | `192.168.55.0/24` redistributed via route-map |

## Files

| File | Purpose |
|------|---------|
| `workbook.md` | Full lab guide — challenge, verification, solutions, troubleshooting |
| `initial-configs/` | IP-only device configs (clean slate — no OSPF) |
| `solutions/` | Complete working configs for all 6 devices |
| `topology/topology.drawio` | Network diagram |
| `setup_lab.py` | Pushes initial configs to EVE-NG via REST API |
| `scripts/fault-injection/` | Three troubleshooting scenarios + solution restorer |

## Troubleshooting Scenarios

| Script | Fault Injected |
|--------|---------------|
| `inject_scenario_01.py` | R3 `area 2 stub` missing `no-summary` — R4 gets inter-area routes |
| `inject_scenario_02.py` | R3 `area 3 nssa no-redistribution` — Type-7 not translated to Type-5 |
| `inject_scenario_03.py` | R2 `area 1 range` removed — three /24s instead of /21 summary |
| `apply_solution.py` | Restores all devices to solution state |
