# BGP Lab 07 — Full Protocol Mastery (Capstone I)

| Field | Value |
|-------|-------|
| Difficulty | Advanced |
| Time budget | 120 minutes |
| Devices | R1, R2, R3, R4, R5, R6, R7 (7 total) |
| Type | Capstone I — configuration from scratch |
| Prerequisites | Labs 00–05 (BGP foundations through communities/FlowSpec) |
| Baseline | Clean slate — interfaces and IP addresses only |

---

## 1. Lab Overview

This is the BGP configuration capstone. You will build a complete production
service-provider topology that integrates **every BGP feature** from the
preceding labs in this topic. The lab does not walk you through individual tasks;
it states the target architecture and you implement it.

**Architecture:**
```
AS 65001 (R1)  ─── eBGP ───  AS 65100 (R2 R3 R4 R5)  ─── eBGP ───  AS 65002 (R6)
   ▲                                                                      ▲
   │ dual-home                                                             │
   ▼                                                                       ▼
   R3 backup                                                  AS 65003 (R7) FlowSpec
```

The clean-slate baseline gives you only IP addressing on each router. Everything
else — OSPF, BGP, RR, communities, route-maps, FlowSpec — you build.

## 2. Target Architecture

By the end of the challenge, the network must satisfy all of the following:

### 2.1 IGP
- OSPF process 1, area 0 on R2, R3, R4, R5 only.
- Loopback0 advertised by every SP router.
- R1, R6, R7 do **not** run OSPF (they are external).

### 2.2 iBGP — Route Reflection
- R4 is the Route Reflector for AS 65100 with `bgp cluster-id 10.0.0.4`.
- R2, R3, R5 are RR clients (`route-reflector-client` on R4).
- **No legacy full-mesh sessions** — the only iBGP next-hop for R2, R3, R5 is R4.
- `next-hop-self` on every client → RR session.
- `send-community both` on every iBGP session.

### 2.3 eBGP Sessions
| Session | TTL-Sec | MD5 (`CISCO_SP`) | Max-Prefix |
|---------|---------|------------------|------------|
| R1↔R2 (primary) | hops 1 | — | 100 75 restart 5 |
| R1↔R3 (backup)  | hops 1 | — | 100 75 restart 5 |
| R5↔R6 | hops 1 | yes | 100 75 restart 5 |
| R5↔R7 | hops 1 | yes | 100 75 restart 5 |
| R6↔R5 (R6 side) | (auto-applies) | yes | 100 75 restart 5 |
| R7↔R5 (R7 side) | hops 1 | yes | 100 75 restart 5 |

### 2.4 Multihoming and Path Selection
- **Primary (R1↔R2):** R2 sets `local-preference 200` inbound on Customer A's
  172.16.1.0/24 prefix. R1 sets MED 10 outbound toward R2.
- **Backup (R1↔R3):** R1 prepends `65001 65001` and sets MED 50 outbound toward R3.
- Result: AS 65100 prefers via R2; AS 65001 prefers return via R2.

### 2.5 Route Dampening
- `bgp dampening 15 750 2000 60` on R5. Dampening is router-global → it applies to
  both R5↔R6 and R5↔R7 eBGP-learned prefixes.

### 2.6 Dynamic Neighbors
- On R2: `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` with `remote-as 65001`,
  `bgp listen limit 10`.
- On R1: static `neighbor 10.99.0.2 remote-as 65100` (the active side).
- The L8 link 10.99.0.0/30 carries the dynamic-neighbor session.

### 2.7 Communities and Extended Communities
| Where | What | Why |
|-------|------|-----|
| R2 inbound from R1 | `set community 65100:100 additive` | Tag Customer-A primary |
| R3 inbound from R1 | `set community 65100:200 additive` | Tag Customer-A backup |
| R2 inbound from R1 | `set extcommunity soo 65001:1` | Site-of-Origin loop guard |
| R3 inbound from R1 | `set extcommunity soo 65001:1` | Site-of-Origin loop guard |
| R6 outbound to R5 | `set community no-export` | Stay inside AS 65100 |
| R7 outbound to R5 | `set community no-advertise` | Drop after consumption |

### 2.8 BGP FlowSpec
- Activate `address-family ipv4 flowspec` on R5 and R7.
- R7 originates: `class-map type traffic FS_DROP_SSH_CUSTA` matching dst
  172.16.1.0/24, protocol TCP, dest-port 22 → `policy-map type traffic
  PM_FS_BLACKHOLE_SSH` with `police rate 0 pps drop/drop`.
- R5: `bgp flowspec local-install interface-all` + `ip flowspec ipv4` on Gi3
  (the R5↔R6 boundary interface) so the rule is applied at the AS edge.
- R7 keeps `bgp flowspec disable-local-install` (originator only — does not enforce
  its own rules locally).

## 3. Verification Matrix

After implementing, run each verification on the listed device and confirm the
expected outcome. Capture the output.

| # | Device | Command | Expected |
|---|--------|---------|----------|
| 1 | R4 | `show ip ospf neighbor` | 3 FULL adjacencies (R2, R3, R5) |
| 2 | R4 | `show ip bgp summary` | 3 iBGP peers up; prefix counts non-zero |
| 3 | R4 | `show ip bgp 172.16.1.0/24` | ORIGINATOR_ID 10.0.0.2; CLUSTER_LIST 10.0.0.4 |
| 4 | R5 | `show ip bgp 172.16.1.0/24` | LOCAL_PREF 200; community 65100:100; SoO 65001:1 |
| 5 | R5 | `show ip bgp neighbors 10.1.56.6` | TTL=254, MD5 enabled, max-prefix 100/75 restart |
| 6 | R5 | `show ip bgp dampening flap-statistics` | Empty initially; populates after a flap |
| 7 | R2 | `show ip bgp peer-group DYN_CUST` | Dynamic peer 10.99.0.1 listed |
| 8 | R6 | `show ip bgp 172.16.1.0/24` | Not present (no-export blocked it at R5) |
| 9 | R5 | `show bgp ipv4 flowspec` | One NLRI: dst 172.16.1/24 proto=6 port=22 |
| 10 | R5 | `show bgp ipv4 flowspec detail` | `Local install: yes`; action `traffic-rate 0` |
| 11 | R5 | `show ip flowspec interface-stats` | Gi3 active for ipv4 |
| 12 | R1 | `show ip bgp 172.16.6.0/24` | Path via R2 (LOCAL_PREF / MED preferred) |

## 4. Failure-Mode Convergence Tests

Verify the design fails over correctly:

1. **Primary path failure.** `shutdown` on R2 Gi0/0 (R1 side). Confirm R1's path
   to 172.16.6.0/24 reroutes via R3 within ~30 s. Restore.
2. **Dampening trigger.** Flap R6 Lo1 five times in 60 s. Confirm penalty exceeds
   suppress threshold on R5; route enters Damp state. Wait ~60 s for unsuppress.
3. **FlowSpec drop verification.** From R1 Lo1 (172.16.1.1) attempt SSH to a host
   reachable via R6. The FlowSpec rule is installed at the R5↔R6 boundary, so
   return TCP/22 traffic toward 172.16.1.0/24 is policed to 0 pps (dropped) at R5.

## 5. Lab Challenge: Full Protocol Mastery

You have **120 minutes**. Working from the clean-slate baseline:

1. Implement everything in Section 2 on every router.
2. Pass every check in Section 3.
3. Pass the failure-mode tests in Section 4.

There is no step-by-step task list. The verification matrix is the contract.

If you get stuck, refer back to:
- Lab-00 → eBGP/iBGP basics
- Lab-01 → Route reflection
- Lab-02 → Multihoming, LOCAL_PREF, AS-path prepend, MED
- Lab-03 → TTL-security, MD5, maximum-prefix
- Lab-04 → Dampening, dynamic neighbors
- Lab-05 → Communities, SoO, FlowSpec

The reference configuration is in `solutions/`. Resist the urge to peek before you
finish.

## 6. Troubleshooting Hints

| Symptom | First check |
|---------|-------------|
| iBGP session up but no prefixes | `next-hop-self` missing on RR client → RR side; `route-reflector-client` missing on RR |
| Community not visible at far end | `send-community both` missing on at least one hop |
| eBGP session down right after coming up | TTL-security mismatch (one side has it, the other doesn't), or MD5 password mismatch |
| Max-prefix shutdown | `clear ip bgp <neighbor>` after fixing root cause; verify `restart 5` is set |
| FlowSpec NLRI on R7 but not on R5 | `address-family ipv4 flowspec` not negotiated (`activate` missing on either side) |
| Dampening route stuck suppressed | `clear ip bgp dampening <prefix>` |
| Dynamic neighbor session never forms | `bgp listen range` mask wrong, or static side missing `remote-as` |

## 7. Performance Targets

- Initial convergence (BGP up + RIB stable): under 90 s after `setup_lab.py` completes.
- Failover (primary down → backup active): under 30 s.
- FlowSpec NLRI propagation R7 → R5: under 5 s after origination.

## 8. Cleanup Between Runs

Between full repeats, reset all 7 devices to the clean-slate baseline:
```bash
python labs/bgp/lab-07-capstone-config/setup_lab.py --host <eve-ng-ip>
```
The script overwrites running-config with the contents of `initial-configs/`.

## 9. Lab Teardown

When done:
1. Save your final running-config from each router (`copy run start`).
2. Optionally export the EVE-NG lab as a `.unl` archive for later replay.
3. Stop all 7 nodes in the EVE-NG UI.

Compare your work against `solutions/R{1..7}.cfg` and `decisions.md` (which
explains *why* each design choice was made).

## 10. Troubleshooting Scenarios

Three pre-built fault scripts are provided in `scripts/fault-injection/` to exercise
your diagnosis skills after the build. Each script injects one fault on one device;
`apply_solution.py` resets to the clean solution.

| Script | Fault | Expected Symptom |
|--------|-------|-------------------|
| `inject_scenario_01.py` | Remove `next-hop-self` on R4 toward R5 | R5 has BGP routes but they are not best because the next-hop is unreachable |
| `inject_scenario_02.py` | Remove `send-community both` on R2 toward R4 | RR (R4) and R5 lose the 65100:100 community on Customer-A's prefix |
| `inject_scenario_03.py` | Apply `maximum-prefix 1` on R5↔R7 | R5↔R7 session bounces and stays down (max-prefix exceeded; `restart 5` triggers loop) |

Run sequence per scenario:
```bash
python scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip>
# diagnose; fix on the running device or:
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

## 11. Further Reading

- Cisco IOS BGP Command Reference (15.x M&T)
- Cisco IOS-XE BGP Configuration Guide 17.3 — *FlowSpec* chapter
- RFC 4456 — BGP Route Reflection
- RFC 4271 §9 — BGP Path Attributes
- RFC 4360 — BGP Extended Communities (SoO)
- RFC 5575 / RFC 8955 — Dissemination of Flow Specification Rules
- RFC 7311 — AIGP (informational; not used here but mentioned in the topic)
- RFC 2439 — BGP Route Flap Damping
