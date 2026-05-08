# SRv6 Lab 00: SRv6 IS-IS Control Plane

**Blueprint:** 4.4, 4.4.a (SRv6 control plane operations), 4.4.d (locator)
**Difficulty:** Foundation — 60 minutes
**Platform:** IOS-XRv 9000 (P1, P2, P3, P4, PE1, PE2)

## Quick Start

```bash
# 1. Push initial configs (IP addressing only)
python3 setup_lab.py --host <eve-ng-ip>

# 2. Work through workbook.md Tasks 1-5

# 3. Apply full solution (if needed)
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

## Topology at a Glance

```
    P1 ──L1── P2
    │╲  L5    │
   L4 ╲     L2
    │   ╲     │
    P4 ──L3── P3
   PE1──L6──P1
   PE2──L7──P3
```

| Router | Loopback0 (v6) | Locator | IS-IS NET |
|--------|----------------|---------|-----------|
| P1 | fc00:0:1::1/128 | fc00:0:1::/48 | 49.0001...0001.00 |
| P2 | fc00:0:2::1/128 | fc00:0:2::/48 | 49.0001...0002.00 |
| P3 | fc00:0:3::1/128 | fc00:0:3::/48 | 49.0001...0003.00 |
| P4 | fc00:0:4::1/128 | fc00:0:4::/48 | 49.0001...0004.00 |
| PE1 | fc00:0:11::1/128 | fc00:0:11::/48 | 49.0001...0011.00 |
| PE2 | fc00:0:12::1/128 | fc00:0:12::/48 | 49.0001...0012.00 |

Locator block: fc00:0::/32 | IS-IS: Level 2 only | 7 links total

## Key Verification Commands

```
show isis adjacency                               ! 7 adjacencies expected
show segment-routing srv6 locator                 ! per-node locator status
show isis segment-routing srv6                    ! IS-IS SRv6 registration
show segment-routing srv6 sid                     ! 6 End SIDs expected
show route ipv6 fc00:0::/32 longer-prefixes       ! 6 /48 locator routes
ping fc00:0:12::1 source fc00:0:1::1              ! end-to-end IPv6 reachability
```

## Troubleshooting Scenarios

| # | Script | Symptom |
|---|--------|---------|
| 01 | inject_scenario_01.py | P2's locator missing from every SID table |
| 02 | inject_scenario_02.py | P4 reports only one IS-IS neighbor |
| 03 | inject_scenario_03.py | PE2's locator shows Status: Down |

## Files

```
lab-00-srv6-control-plane/
├── workbook.md                   ← Full lab guide with theory and tasks
├── setup_lab.py                  ← Push initial-configs to EVE-NG
├── README.md                     ← This file
├── decisions.md                  ← Design decisions and build provenance
├── meta.yaml                     ← Build manifest
├── initial-configs/              ← IP-only base configs (P1-P4, PE1, PE2)
├── solutions/                    ← Full solution configs
├── topology/
│   ├── topology.drawio           ← Cisco-icon topology diagram
│   └── README.md                 ← EVE-NG import/export instructions
└── scripts/fault-injection/      ← Automated fault injection and restore
    ├── inject_scenario_01.py
    ├── inject_scenario_02.py
    ├── inject_scenario_03.py
    └── apply_solution.py
```

## Progressive Chain

This lab's solution becomes the starting point for:
- **lab-01-srv6-data-plane** — adds End.X SIDs, SRH forwarding, and H.Encaps
- **lab-02-flex-algo-and-l3vpn** — adds Flex-Algo, BGP SRv6 L3VPN, and interworking gateway
