# Lab 02 — RPL vs Route-Maps: Policy Sets and Hierarchical Policies

**Topic:** Routing Policy and Manipulation
**Exam:** 300-510 SPRI
**Blueprint:** 3.1, 3.2.d, 3.2.j
**Difficulty:** Intermediate
**Time:** 90 minutes
**Type:** Progressive (extends lab-01)

---

## Overview

This lab introduces IOS-XR's Routing Policy Language (RPL) as a direct contrast to IOS
route-maps. Two XRv9k routers (XR1, XR2) join the SP core IS-IS and iBGP fabric and carry
the RPL policy framework while the IOS core (R1/R2/R3) continues to run route-maps.

After completing this lab you will be able to:

- Bring up an IOS-XR router in an IS-IS L2 domain alongside IOS peers
- Write RPL named sets (`prefix-set`, `community-set`, `as-path-set`) and explain how they
  differ from IOS `ip prefix-list` / `ip community-list`
- Build a hierarchical RPL parent policy that calls two child policies via `apply`
- Write and instantiate a parameterized RPL policy with `$set_name` arguments
- Identify the three fundamental behavioral differences between RPL and route-maps

---

## Topology

```
                     AS 65100 (SP core)
          ┌────┐                     ┌────┐
          │ R1 ├────── L1 ───────────┤ R2 │
          └─┬──┘     10.1.12.0/24   └──┬─┘
            │                          │  └── Gi0/2 ── L6 ── 10.1.25.0/24 ──┐
            L5 10.1.13.0/24           L2 10.1.23.0/24                        │
            │                          │                                    ┌──┴──┐
          ┌─┴──┐                     ┌──┴─┐                                 │ XR1 │ 10.0.0.5
          │ R3 ├────── L3 ───────────┤ R4 │ AS 65200                       └──┬──┘
          └────┘     10.1.34.0/24   └────┘              L8 10.1.56.0/24       │
            │ └── Gi0/3 ─ L7 ─ 10.1.36.0/24 ──┐        ──────────────────────┘
            │                                ┌──┴──┐
            └──────── L4 10.1.14.0/24 ───────┤ XR2 │ 10.0.0.6
                      (R1:Gi0/1 ↔ R4:Gi0/1)  └─────┘
```

**Loopbacks:**

| Device | Lo0          | Lo1            | Role                   |
|--------|--------------|----------------|------------------------|
| R1     | 10.0.0.1/32  | 172.16.1.1/24  | SP edge, eBGP to R4    |
| R2     | 10.0.0.2/32  | —              | SP transit             |
| R3     | 10.0.0.3/32  | —              | SP edge, eBGP to R4    |
| R4     | 10.0.0.4/32  | 172.20.4.1/24  | External (AS 65200)    |
| XR1    | 10.0.0.5/32  | 172.16.11.1/24 | XR RPL node (AS 65100) |
| XR2    | 10.0.0.6/32  | —              | XR RPL node (AS 65100) |

---

## Prerequisites

- lab-01-tags-regex-communities must be complete (this lab extends those configs)
- XR1 and XR2 nodes imported and started in EVE-NG (~4 GB RAM each; allow 10 min boot)
- All IOSv nodes (R1/R2/R3/R4) running with lab-01 configs loaded (initial-configs provide this)

---

## Lab Objectives

1. Activate XR1/XR2 — bring up IS-IS L2 and iBGP full mesh, verify adjacency and route reachability
2. Side-by-side comparison — R1 (route-map) vs XR1 (RPL): same outcome, different syntax
3. RPL named sets — build `prefix-set`, `community-set`, `as-path-set` on XR1/XR2
4. Hierarchical RPL — parent `EBGP_IN` calls child policies via `apply`
5. Parameterized RPL — `MATCH_PREFIX_FROM_SET($set_name)` instantiated with two different arguments
6. RPL vs route-map differences — document three fundamental behavioral differences

---

## Key Files

| File | Purpose |
|------|---------|
| `initial-configs/R1-R4.cfg` | Lab-01 solutions pre-loaded on IOSv core |
| `initial-configs/XR1.cfg` | IP addressing only (no protocols) |
| `initial-configs/XR2.cfg` | IP addressing only (no protocols) |
| `solutions/XR1.cfg` | Full RPL solution with all named sets and policies |
| `solutions/XR2.cfg` | Paired XR node with egress policy demonstration |
| `workbook.md` | Step-by-step tasks with verification commands |

---

## Quick Start

```bash
# Push initial configs to all nodes (XR nodes will just get IPs)
python3 setup_lab.py --host <eve-ng-ip>

# After XR nodes boot (~10 min), verify IS-IS adjacency on R2:
show isis neighbors

# Verify iBGP session to XR1 on R1:
show bgp neighbors 10.0.0.5 | include BGP state

# On XR1, verify full-mesh iBGP and IS-IS:
show isis neighbors
show bgp summary
```

---

## XR Automation Notes

XR nodes use `cisco_xr_telnet` netmiko driver (patched in `labs/common/tools/eve_ng.py`).
XR config uses candidate-config/commit — `save_config()` in netmiko sends `commit`.
Do not include literal `commit` in `.cfg` files; it is handled by the automation layer.
