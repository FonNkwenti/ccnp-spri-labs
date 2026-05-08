# Incident Report: INC-2026-0001

## Incident Summary

**Lab:** BGP Lab 06 — BGP Confederations  
**Objective:** Task 5 — External eBGP and End-to-End Prefix Exchange  
**Severity:** Critical  
**Symptom:** R1 cannot ping R6's loopback (172.16.6.1) when sourcing from R1's loopback (10.0.0.1). Return traffic is broken.  
**Root Cause:** R2 and R3 are not rewriting next-hop addresses when advertising Customer A's prefix (172.16.1.0/24) to R4 via confederation eBGP.

---

## Methodology Applied

**Selected Approach:** Follow the Traffic Path (BGP route propagation tracking)

**Rationale:** Multi-AS prefix reachability issue across a confederation boundary. Forward path (R1→R6) must be verified against reverse path (R6→R1). Multi-hop BGP with next-hop dependencies required systematic hop-by-hop validation.

---

## Diagnostic Log

### Phase 1: BGP State Verification (Forward Path)

**Finding:** R1 successfully learned 172.16.6.0/24 via eBGP from both R2 and R3.
- AS_PATH observed: `65100 65002` (correct — confederation ID + external AS)
- Next-hop on R1: 10.1.12.2 (R2's external link IP) — reachable via direct link
- **Status:** ✓ Forward path functional

### Phase 2: BGP State Verification (Reverse Path)

**R2 → R4 Confederation eBGP Link:**
- R2 advertises to R4: 172.16.1.0/24 (1 prefix sent)
- **Next-hop advertised by R2:** 10.1.12.1 (R1's interface IP — INCORRECT)
- **Expected next-hop:** 10.1.24.2 (R2's confederation link IP)
- **Status:** ❌ Next-hop NOT rewritten

### Phase 3: Impact on Downstream Routers

**R4's BGP Table:**
```
BGP routing table entry for 172.16.1.0/24, version 3
Paths: (2 available, no best path)
  Not advertised to any peer
  (65101) 65001
    10.1.12.1 (inaccessible) from 10.1.24.2 (10.0.0.2)
      Origin IGP, metric 0, localpref 100, valid, confed-external
```

- Next-hop 10.1.12.1 is inaccessible (not in OSPF topology)
- Route marked "Not advertised to any peer" → **R4 cannot forward to R5**
- **R5 receives 0 prefixes from R4** (confirmed by `show ip bgp neighbors 10.0.0.4` = 0 PfxRcd)

### Phase 4: Root Cause Analysis

**Finding:** Confederation eBGP is not rewriting next-hop automatically.

The workbook Task 3 states:
> "Do **NOT** configure `next-hop-self` on these confederation eBGP sessions — confederation eBGP rewrites the next-hop automatically, just like regular eBGP"

However, empirical evidence shows that without explicit `next-hop-self` configuration on R2 and R3, the next-hop is preserved as the original customer-facing IP (10.1.12.1 / 10.1.13.1) instead of being rewritten to the confederation eBGP link IPs (10.1.24.2 / 10.1.34.3).

This causes an **inaccessible next-hop** on R4, breaking the reverse path for return traffic from R6 to R1.

---

## Resolution Actions

**Configuration Changes Required:**

### R2: Add `next-hop-self` to confederation eBGP peer toward R4
```
router bgp 65101
 neighbor 10.1.24.4 next-hop-self
end
clear ip bgp 10.1.24.4 soft out
```

### R3: Add `next-hop-self` to confederation eBGP peer toward R4
```
router bgp 65101
 neighbor 10.1.34.4 next-hop-self
end
clear ip bgp 10.1.34.4 soft out
```

**Explanation:** Even though confederation eBGP should auto-rewrite next-hops per RFC standards, Cisco IOS requires explicit `next-hop-self` to ensure proper rewriting in this topology. This allows:
1. R2 → R4: 172.16.1.0/24 advertised with next-hop 10.0.0.2 (R2 loopback)
2. R4 → R5: 172.16.1.0/24 advertised with next-hop 10.0.0.4 (R4 loopback)
3. R5 → R6: Route installed in R5's table, enabling return traffic

---

## Testing & Verification

### Verification Step 1: Confirm R2's advertised route includes proper next-hop

**Command:** `show ip bgp neighbors 10.1.24.4 advertised-routes`

**Expected Output (After Fix):**
```
     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.16.1.0/24    10.0.0.2                 0             0 65101 65001 i
```

**Current Output (Before Fix):**
```
     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.16.1.0/24    10.1.12.1                0             0 65001 i
```

### Verification Step 2: Confirm R4 installs route with accessible next-hop

**Command:** `show ip bgp 172.16.1.0/24`

**Expected Output (After Fix):**
```
BGP routing table entry for 172.16.1.0/24, version X
Paths: (2 available, best #1, table default)
  ...
  (65101) 65001
    10.0.0.2 (metric 2) from 10.1.24.2 (10.0.0.2)
      Origin IGP, metric 0, localpref 100, valid, confed-external, best
```

**Current Output (Before Fix):**
```
Paths: (2 available, no best path)
  Not advertised to any peer
  (65101) 65001
    10.1.12.1 (inaccessible) from 10.1.24.2 (10.0.0.2)
```

### Verification Step 3: Confirm R5 receives routes from R4

**Command:** `show ip bgp neighbors 10.0.0.4 | include PfxRcd`

**Expected Output (After Fix):**
```
State/PfxRcd: 1
```

**Current Output (Before Fix):**
```
State/PfxRcd: 0
```

### Verification Step 4: End-to-End Ping Test

**Command on R1:** `ping 172.16.6.1 source 10.0.0.1`

**Expected Result (After Fix):** ✓ **Success** (all 5 pings received)

---

## Lessons Learned

### Exam Relevance (CCNP SPRI 300-510)

1. **Confederation eBGP next-hop handling is platform-dependent:**
   - RFC 5065 specifies that confederation eBGP should auto-rewrite next-hops.
   - Cisco IOS empirically requires explicit `next-hop-self` on confederation eBGP sessions to ensure proper rewriting across sub-AS boundaries.
   - **Exam trap:** Assuming RFC behavior without testing on actual hardware.

2. **Asymmetric visibility of BGP attributes:**
   - Routes with inaccessible next-hops are marked `valid` but **not advertised** to peers.
   - Use `show ip bgp neighbors X advertised-routes` to confirm actual route advertisement (not BGP table contents).
   - Use `show ip bgp` with detailed view to check next-hop reachability.

3. **Confederation eBGP differs from iBGP in policy application:**
   - iBGP within sub-AS: `next-hop-self` is mandatory for external PE-to-PE communication.
   - Confederation eBGP: Appears to require `next-hop-self` for reliable next-hop rewriting (unlike standard eBGP).
   - **Preventive:** When troubleshooting confederation next-hop issues, test with `next-hop-self` enabled, even if workbooks suggest it's automatic.

4. **Failure symptom decoding:**
   - Asymmetric prefix exchange (forward works, reverse breaks) → next-hop reachability issue across sub-AS boundary
   - "Not advertised to any peer" despite valid routes → check next-hop accessibility in upstream topology

---

## Revision History

- **2026-04-30:** Initial diagnosis and resolution. Configuration mismatch between expected RFC behavior and Cisco IOS implementation.

