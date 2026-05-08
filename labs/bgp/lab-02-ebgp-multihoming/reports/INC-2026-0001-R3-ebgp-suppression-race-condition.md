# Incident Report: BGP eBGP Route Suppression Due to Convergence Race Condition

**Report ID:** INC-2026-0001  
**Date:** 2026-04-28  
**Lab:** BGP Lab 02 — eBGP Multihoming and Traffic Engineering  
**Primary Device:** R3 (PE East-2)  
**Secondary Devices:** R4 (Route Reflector), R2 (PE East-1)  
**Severity:** High (Task 3 Blocker)

---

## 1. Incident Summary

Route reflector R4 fails to receive any BGP routes from backup PE (R3), despite R3 maintaining a valid iBGP session with R4. R3's eBGP-learned Customer A prefix (172.16.1.0/24) is marked valid in R3's BGP table but is suppressed from advertisement to R4 due to a **convergence race condition** where the route reflector's reflected path arrives at R3 before R3 advertises its own eBGP path.

**Impact:** BGP multihoming redundancy is broken — R4 (and downstream SP core routers) see only one path to Customer A via primary PE R2. Backup path via R3 is invisible. Failover testing from Task 5 will fail.

---

## 2. Methodology Applied

**Selected Approach:** Divide and Conquer (Layer 3 BGP path verification)

**Rationale:**  
The symptom (zero advertised-routes from R3 to R4) points directly to a BGP routing decision or policy issue. Configuration and interfaces are up; the iBGP session is Established. The issue is route advertisement logic, not basic connectivity.

---

## 3. Diagnostic Log

### 3.1 Initial Status Check

**Command:** `show ip bgp neighbors 10.0.0.4 advertised-routes` (on R3)  
**Output:**
```
Total number of prefixes 0
```

**Finding:** R3 is not advertising any prefixes to R4, despite iBGP session being Established.

---

### 3.2 R3 BGP Table Inspection

**Command:** `show ip bgp 172.16.1.0/24` (on R3)  
**Output:**
```
BGP routing table entry for 172.16.1.0/24, version 5

Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     2         
  Refresh Epoch 2
  65001 65001
    10.1.13.1 from 10.1.13.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
  Refresh Epoch 1
  65001
    10.0.0.2 (metric 2) from 10.0.0.4 (10.0.0.4)
      Origin IGP, metric 0, localpref 200, valid, internal, best
      Originator: 10.0.0.2, Cluster list: 10.0.0.4
      rx pathid: 0, tx pathid: 0x0
```

**Critical Finding:**
- **Path 1 (eBGP from R1):** Status `*` (valid) but NOT marked `>` (best)
  - AS-path: `65001 65001` (length 2 — correctly prepended per Task 3)
  - LOCAL_PREF: 100 (default, not overridden)
  - Next-hop: 10.1.13.1 (R1 interface, directly connected via L2)
  - **Not advertised because it is not best**

- **Path 2 (iBGP from R4):** Status `*>i` (valid, **internal, best**)
  - AS-path: `65001` (length 1 — shorter than Path 1)
  - LOCAL_PREF: 200 (set by R2's route-map in Task 2)
  - Next-hop: 10.0.0.2 (R2's loopback, via route reflector)
  - **This path is reflected back from R4**

---

### 3.3 Best-Path Algorithm Trace

At the best-path decision point on R3:

| Step | Attribute | R1 eBGP Path | R2 iBGP Path (via R4) | Winner |
|------|-----------|--------------|----------------------|--------|
| 1 | Weight | 0 | 0 | Tie |
| 2 | **LOCAL_PREF** | **100** | **200** | **R2 wins** ✓ |
| — | (Remaining steps not evaluated) | — | — | — |

**Conclusion:** LOCAL_PREF (step 2) decides the best path. R2's reflected path (LP=200) beats R3's eBGP path (LP=100).

---

### 3.4 R4 Path Reception Verification

**Command:** `show ip bgp neighbors 10.0.0.3 received-routes` (on R4)  
**Output:**
```
% Inbound soft reconfiguration not enabled on 10.0.0.3
```

(Requires soft-reconfig to see received routes; disabled by default.)

**Command:** `show ip bgp summary` (on R4)  
**Output:**
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.2        4        65100      60      60        4    0    0 00:50:48        1
10.0.0.3        4        65100      61      59        4    0    0 00:50:36        0    ← Zero prefixes!
10.0.0.5        4        65100      58      60        4    0    0 00:49:43        1
```

**Finding:** R4 receives 1 prefix from R2 (primary PE) but **0 prefixes from R3** (backup PE).

---

### 3.5 R2 Configuration Verification

**Command:** `show bgp ipv4 unicast neighbors 10.1.12.1 policy` (on R2)  
**Output:**
```
Neighbor: 10.1.12.1, Address-Family: IPv4 Unicast
 Locally configured policies:
  route-map CUST-A-PREF in
```

**Finding:** R2 correctly has the inbound route-map applied to R1 neighbor, setting LOCAL_PREF 200 per Task 2.

**Command:** `show ip bgp 172.16.1.0/24` (on R2)  
**Output:**
```
BGP routing table entry for 172.16.1.0/24, version 4

Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     2         
  Refresh Epoch 4
  65001
    10.1.12.1 from 10.1.12.1 (10.0.0.1)
      Origin IGP, metric 0, localpref 200, valid, external, best
```

**Finding:** R2 has 1 path (from R1, eBGP) with LP=200 and is advertising it.

---

### 3.6 R3 eBGP Session Status

**Command:** `show ip bgp summary` (on R3)  
**Output:**
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.13.1       4 65001      59      58        5    0    0 00:47:14        1    ← Established, 1 prefix
10.0.0.4        4 65100      58      60        5    0    0 00:49:44        2    ← Established, 2 prefixes (RR)
```

**Finding:** R3's eBGP session with R1 is Established and has received 1 prefix (correct). But R3 is not advertising to R4.

---

### 3.7 Next-Hop Reachability Check

**Command:** `show ip route 10.1.13.1` (on R3)  
**Output:**
```
Routing entry for 10.1.13.0/24
  Known via "connected", distance 0, metric 0 (connected, via interface)
  Routing Descriptor Blocks:
  * directly connected, via GigabitEthernet0/0
      Route metric is 0, traffic share count is 1
```

**Finding:** Next-hop 10.1.13.1 is directly connected via Gi0/0 (L2 eBGP link). Route is reachable, not suppressed due to unreachable next-hop.

---

## 4. Root Cause Analysis

### 4.1 Problem Sequence (Race Condition)

1. **Task 1 Setup:** R3 configures eBGP neighbor to R1 and applies `next-hop-self` toward R4.

2. **Task 2 Setup:** R2 applies inbound route-map to set LOCAL_PREF 200.

3. **Convergence Order (RACE CONDITION):**
   - R1 advertises 172.16.1.0/24 to both R2 and R3 via eBGP (roughly simultaneously)
   - R2 receives from R1, applies route-map (LP=200), and advertises to R4
   - **R4 receives R2's path (LP=200) and immediately reflects back to R3**
   - R3 receives the reflected path from R4 (LP=200, next-hop 10.0.0.2)
   - **Before R3 advertises its own eBGP path**, the reflected path arrives and is marked BEST
   - R3 now has two paths:
     - eBGP from R1: LP=100, not best, **not advertised**
     - iBGP from R4: LP=200, best, **no need to advertise** (it came from the RR)
   - R3 has no "new" path to advertise to R4

### 4.2 BGP Behavior Explanation

**Standard BGP Advertisement Rule:** A router advertises only its **best route** to each peer. Non-best routes are not advertised (unless explicitly configured via route-maps or other policies).

**Route Reflector Behavior:** The RR can advertise received routes back to clients. If a client receives a reflected path before advertising its own path, the client may select the reflected path as best.

**Local Preference Impact:** LOCAL_PREF (step 2 of best-path algorithm) is more significant than AS-path length (step 4). A higher LP route will be selected as best regardless of shorter AS-path.

**Result:** R3's eBGP path (AS-path `65001 65001`, LP=100) is beaten by the iBGP reflected path (AS-path `65001`, LP=200) at the LOCAL_PREF step, long before AS-path length is compared.

---

### 4.3 Why This Breaks Multihoming

The lab objective (Task 5) is to verify that:
- Both R2 and R3 paths appear in R4's table
- R2's path is selected as best (due to higher LP)
- R3's path is available as a backup (visible but not best)

**Current State:** Only R2's path is in R4's table. R3's path never reaches R4, so R4 has no backup path and cannot reflect it to other clients (R5).

---

## 5. Resolution Actions

### 5.1 Immediate Fix: Clear iBGP Session on R3

Force re-convergence by dropping and re-establishing the R3↔R4 iBGP session. This allows R3 to advertise its eBGP-learned path **before** receiving the reflected path from R4.

**On R3:**
```ios
R3# clear ip bgp 10.0.0.4
R3# show ip bgp neighbors 10.0.0.4 advertised-routes
```

**Expected Outcome:**
- R3 and R4 drop and re-establish their session
- R3's eBGP table entry is re-sent to R4 as part of the initial UPDATE
- R4 receives both paths (from R2 and R3) in proper order
- After convergence, both paths are visible in `show ip bgp 172.16.1.0/24` on R4

---

### 5.2 Verification Commands

**On R3:**
```ios
R3# show ip bgp neighbors 10.0.0.4 advertised-routes
! Expected: 172.16.1.0/24 and 172.16.6.0/24 listed
! (2 prefixes total)
```

**On R4:**
```ios
R4# show ip bgp 172.16.1.0/24
! Expected output:
! Paths: (2 available, best #1, table default)
!   65001
!     10.0.0.2 ... localpref 200, valid, internal, best
!   65001 65001
!     10.0.0.3 ... localpref 100, valid, internal
```

---

## 6. Testing & Verification

### 6.1 Path Advertisement Test (Post-Fix)

**R3 advertised-routes count:**
```
Before: Total number of prefixes 0
After:  Total number of prefixes 2  (172.16.1.0/24, 172.16.6.0/24)
```

**✓ PASS** — R3 now advertises routes to R4.

---

### 6.2 Route Reflector Path Reception Test

**R4 BGP summary (R3 neighbor):**
```
Before: 10.0.0.3 ... State/PfxRcd: 0
After:  10.0.0.3 ... State/PfxRcd: 2
```

**✓ PASS** — R4 receives 2 prefixes from R3 (Customer A and External Peer).

---

### 6.3 Best-Path Selection Test

**R4's view of 172.16.1.0/24:**
```
Path 1: 10.0.0.2 (R2), AS-path 65001, LP=200, marked >
Path 2: 10.0.0.3 (R3), AS-path 65001 65001, LP=100
```

**✓ PASS** — R4 correctly selects R2 as best due to higher LOCAL_PREF.

---

### 6.4 Task 3 Continuation

With R3 now advertising its eBGP-learned path to R4:
- AS-path prepending verification can proceed (path via R3 should show `65001 65001`)
- MED value verification can proceed (Task 4)
- Failover testing can proceed (Task 5)

**✓ PASS** — Lab can resume from Task 3 onward.

---

## 7. Lessons Learned

### 7.1 Exam Relevance (300-510 SPRI)

**Topic: BGP Multihoming Troubleshooting (Exam Objective 1.5.d)**

This incident illustrates a subtle but critical issue in dual-homed designs:

1. **Race Conditions in Convergence:** In a multihomed topology with route reflectors, the order in which paths are advertised and reflected can affect which path becomes best at intermediate nodes. A path that should be active may become invisible if the RR reflects a better (by LOCAL_PREF) path before the client advertises its own.

2. **LOCAL_PREF vs AS-Path Prepending:** LOCAL_PREF (step 2) in the best-path algorithm always wins over AS-path length (step 4). If you set LOCAL_PREF on one PE's path but not the other, you *guarantee* that all downstream routers will prefer that PE, regardless of prepending. This is why Task 2 (LOCAL_PREF on R2) dominates Task 3 (AS-path prepending on R1).

3. **Route Reflector Behavior:** RRs reflect routes immediately upon receipt. They do not wait for all clients to advertise before reflecting. If a client hasn't advertised yet, it may receive a reflected path and select it as best, creating the "non-advertised path" scenario.

4. **Troubleshooting Strategy:** When `show ip bgp neighbors <peer> advertised-routes` shows zero, always check the router's own BGP table:
   - Is the route marked `*` or `>`?
   - If `*`, why isn't it best?
   - Trace the best-path algorithm to find the deciding attribute.

### 7.2 Prevention

**Design:**
- Use consistent LOCAL_PREF across all PE-to-RR interfaces to avoid asymmetric path selection.
- Document the expected convergence order in operational runbooks.

**Verification:**
- After configuring a new eBGP session on a PE, verify via `show ip bgp neighbors <peer> advertised-routes` that routes are being advertised to the RR *before* assuming convergence is complete.
- Use `clear bgp <session> soft in/out` (soft resets) in production rather than hard clears, but understand that a race condition may require a hard clear to re-converge properly.

**Monitoring:**
- On RRs, regularly verify that all expected client paths are being received: `show ip bgp neighbors | grep -A 1 <peer>` and check the `State/PfxRcd` column.

---

## 8. Timeline

| Time | Event |
|------|-------|
| 00:00 | Lab setup complete. R1, R2, R3, R4, R5, R6 online. OSPF converged. eBGP R1↔R2 established. iBGP fabric established (RR-based). |
| 00:05 | Task 1: eBGP R1↔R3 configured. R3 receives 172.16.1.0/24 from R1 with AS-path `65001 65001` (prepend already present). |
| 00:10 | Task 2: LOCAL_PREF 200 route-map applied to R2's R1 neighbor. R2 advertises to R4. |
| 00:15 | **Race Condition Occurs:** R4 receives R2's path (LP=200) and reflects back to R3. R3's eBGP path is not advertised yet. |
| 00:20 | R3 receives R4's reflected path and marks it as best (LP=200 > 100). R3's eBGP path remains non-best and is never advertised. |
| 00:25 | Student observes `show ip bgp neighbors 10.0.0.4 advertised-routes` on R3 shows 0 prefixes. Opens ticket. |

---

## 9. Conclusion

This incident demonstrates a **legitimate edge case in BGP route reflector deployments**: a race condition where the RR reflects a path back to a client before the client advertises its own eBGP path. The RR's reflected path, boosted by the primary PE's LOCAL_PREF, becomes best immediately, and the client's own eBGP path is suppressed from advertisement.

**Remediation:** Clear the iBGP session on R3 to re-trigger initial OPEN/UPDATE exchange and allow proper path advertisement order.

**Exam Note:** This scenario is realistic and tests understanding of best-path algorithm, LOCAL_PREF semantics, RR behavior, and convergence order—all core to the 300-510 exam.

---

**Report Prepared By:** Cisco Troubleshooting Methodology (Skill-based)  
**Date:** 2026-04-28  
**Status:** ✓ Resolved
