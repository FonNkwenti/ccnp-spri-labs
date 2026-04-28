# BGP Lab 07: Full Protocol Mastery — Capstone I

**Type:** Capstone I (configuration-from-scratch)
**Difficulty:** Advanced
**Time:** 120 minutes
**Devices:** 7 (R1, R2, R3, R4, R5, R6, R7)
**Clean slate:** Yes — initial configs contain only IP addressing on interfaces.

## Mission

Build the complete production BGP service-provider topology from the interface-only
baseline. Integrate every BGP feature covered in labs 00–05:

- OSPF area 0 IGP across AS 65100 core (R2, R3, R4, R5)
- Route Reflector (R4) with R2/R3/R5 as clients — no legacy iBGP full mesh
- Customer A dual-homing: R1↔R2 primary (LOCAL_PREF 200), R1↔R3 backup (AS-path
  prepend ×2 + MED 50)
- Inter-domain security: TTL-security (GTSM), MD5 authentication, maximum-prefix
  with restart on every eBGP session
- Route dampening on R5 (applies to R6 and R7 via router-global config)
- Dynamic neighbor listen range on R2 (10.99.0.0/24) for the customer block
- Communities: 65100:100 (Customer-A primary tag), 65100:200 (Customer-A backup tag),
  no-export at the AS boundary, no-advertise from R7, SoO 65001:1 on both R2 and R3
- BGP FlowSpec: R7 originates a TCP/22 → 172.16.1.0/24 drop rule; R5 installs and
  applies it on the R5↔R6 boundary

Lab-06 confederation logic is **not** in scope.

## Files

```
README.md                            ← this file
workbook.md                          ← lab challenge declaration + verification matrix
decisions.md                         ← design rationale and capstone deltas
meta.yaml                            ← provenance (auto-stamped)
setup_lab.py                         ← pushes initial-configs/ via EVE-NG REST + SSH
initial-configs/R{1..7}.cfg          ← clean-slate (IP addressing only)
solutions/R{1..7}.cfg                ← reference target configuration
topology/topology.drawio             ← logical topology (open in draw.io)
topology/README.md                   ← EVE-NG import/export guide
scripts/fault-injection/             ← 3 scenario fault scripts + apply_solution.py
```

## Quick Start

1. Import `topology/topology.drawio` (or the matching `.unl`) into EVE-NG.
2. Start all 7 nodes; wait ~3 min (IOSv) and ~5 min (CSR1000v R5/R7) for boot.
3. Push the clean-slate baseline:
   ```bash
   python labs/bgp/lab-07-capstone-config/setup_lab.py --host <eve-ng-ip>
   ```
4. Open `workbook.md` and complete the lab challenge.
5. Compare your work to `solutions/` and run a verification pass.

## Hardware

| Device | Platform | Image | RAM |
|--------|----------|-------|-----|
| R1, R2, R3, R4, R6 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5, R7 | csr1000v | csr1000v-universalk9.17.03.05 | 3072 MB |

R5 and R7 must be CSR1000v — IOSv does not implement BGP FlowSpec SAFI.
