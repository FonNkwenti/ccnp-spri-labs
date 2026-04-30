# Segment Routing Lab 00: SR-MPLS Foundations, SRGB, and Prefix SIDs

**Blueprint:** 4.2, 4.2.a (IS-IS SR extensions), 4.2.b (SRGB and SRLB)
**Difficulty:** Foundation — 90 minutes
**Platform:** IOS-XRv 9000 (R1, R2, R3, R4)

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
    R1 ──L1── R2
    │  ╲       │
   L4  L5     L2
    │    ╲     │
    R4 ──L3── R3
```

| Router | Loopback | SID | SRGB Label |
|--------|----------|-----|-----------|
| R1 | 10.0.0.1/32 | index 1 | 16001 |
| R2 | 10.0.0.2/32 | index 2 | 16002 |
| R3 | 10.0.0.3/32 | index 3 | 16003 |
| R4 | 10.0.0.4/32 | index 4 | 16004 |

SRGB: 16000-23999 | SRLB: 15000-15999 (default) | IS-IS: Level 2 only

## Key Verification Commands

```
show isis neighbors                        ! 5 adjacencies expected
show isis segment-routing label table      ! 4 prefix SID entries
show mpls forwarding labels 16001          ! R1's SID — local
show mpls forwarding labels 16004          ! R4's SID — swap/pop
show segment-routing local-block detail    ! SRGB allocated
ping 10.0.0.4 source 10.0.0.1             ! end-to-end reachability
```

## Troubleshooting Scenarios

| # | Script | Fault Description |
|---|--------|------------------|
| 01 | inject_scenario_01.py | R3 missing `segment-routing mpls` under IS-IS af — no prefix SIDs from R3 |
| 02 | inject_scenario_02.py | R4 Gi0/0/0/0 missing IS-IS `address-family ipv4 unicast` — R4 isolated from IS-IS |
| 03 | inject_scenario_03.py | R4 missing `prefix-sid index 4` — label 16004 absent from LFIB |

## Progressive Chain

This lab's solution becomes the starting point for:
- **lab-01-ti-lfa** — adds TI-LFA (Topology-Independent Loop-Free Alternate) on top of this SR foundation
