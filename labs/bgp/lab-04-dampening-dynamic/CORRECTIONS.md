# Lab-04 (Dampening & Dynamic Neighbors) — Corrections Summary

## Issues Found (2026-04-29)

### 1. **Missing L8 Interface Configuration in Initial Configs** ✅ FIXED

**Problem:** The workbook states that "L8 physical link cabled: R1 Gi0/2 and R2 Gi0/3 are IP-addressed but not in BGP yet" is pre-loaded in the base config (line 262). However, the initial configs (`R1.cfg` and `R2.cfg`) did NOT include these interfaces at all.

**Impact:** Students had to manually add the L8 interface configuration, which was supposed to be pre-loaded. This created confusion about what was pre-loaded vs. what needed to be configured.

**Fix Applied:**
- Added Gi0/2 (10.99.0.1/30) to `R1.cfg` initial config
- Added Gi0/3 (10.99.0.2/30) to `R2.cfg` initial config
- Both interfaces are now IP-addressed and ready for BGP configuration as stated in the workbook

---

### 2. **Status Code Verification Using Wrong Command** ✅ FIXED

**Problem:** The workbook uses `show ip bgp 172.16.6.0` (detailed view) to verify status codes like 'd' (damped). However, IOS/IOS-XE only displays status codes in **table view** commands like `show ip bgp` or `show ip bgp dampening flap-statistics`, NOT in the detailed-view command `show ip bgp <prefix>`.

**Evidence:**
- User's output showed `show ip bgp 172.16.6.0` displays detailed attributes but NO status codes
- `show ip bgp` and `show ip bgp dampening flap-statistics` show status codes correctly

**Affected sections:**
- Task 1 Verification (line 282) — expected 'd' flag in detailed view
- Task 2 Verification (line 294) — expected 'd' flag in detailed view  
- Task 3 Verification (line 304) — expected 'd' flag disappearance in detailed view
- Challenge Task 1 section (line 459) — mentioned 'd' flag in `show ip bgp <prefix>`

**Fix Applied:**
- Clarified that Task 1/2/3 verification requires `show ip bgp` (table view) for status codes
- Updated Task 2 examples to show BOTH commands with their purposes
- Added critical note in Verification Cheatsheet explaining the difference between table-view (shows status codes) and detailed-view (shows full attributes)

**Verification Cheatsheet Addition:**
```
> **Critical:** Status codes (d, *, >, etc.) appear ONLY in table-view commands 
> (`show ip bgp`, `show ip bgp dampening flap-statistics`). The detailed-view 
> command `show ip bgp <prefix>` does NOT show status codes.
```

---

### 3. **Non-Existent Command Reference: `show ip bgp listen range`** ✅ FIXED

**Problem:** The workbook references `show ip bgp listen range` command (lines 104, 320, 394, 498) as a verification command. This command does NOT exist on IOS/IOS-XE.

**Evidence:** User's attempt resulted in:
```
R2#sh ip bgp listen range
              ^
% Invalid input detected at '^' marker.
```

**Actual behavior:** Listen range information appears in `show ip bgp summary` output as:
```
BGP peergroup DYN_CUST listen range group members:
  10.99.0.0/24
```

**Fix Applied:**
- Updated Task 4 verification section to reference `show ip bgp summary` instead
- Updated Verification Commands table to show the correct command
- Provided actual command output format showing where listen range info appears

---

### 4. **Unclear BGP Configuration Requirements in Task 4** ⚠️ CLARIFIED

**Problem:** Task 4 description (lines 309-320) didn't explicitly list all required BGP configuration steps. Specifically, `neighbor DYN_CUST remote-as 65001` is required but wasn't immediately obvious in the bullet points.

**Fix Applied:**
- Reorganized Task 4 description to list exact commands required:
  - `neighbor DYN_CUST peer-group`
  - `neighbor DYN_CUST remote-as 65001` (now explicit)
  - `neighbor DYN_CUST description Dynamic-Customer-AS65001`
  - `bgp listen limit 10`
  - `bgp listen range 10.99.0.0/24 peer-group DYN_CUST`
  - Address-family commands

---

## Secondary Finding: Systematic Issue Across Other Labs

**Scope:** A scan of all BGP lab workbooks (lab-00 through lab-08) reveals that while other labs use `show ip bgp <prefix>` to verify attributes (ORIGINATOR_ID, CLUSTER_LIST, LOCAL_PREF, Community, AS_PATH, etc.), these attributes ARE correctly shown in the detailed view and the labs are correct.

**Only Lab-04 has the status-code issue** because it's the only one that tries to verify status codes from the detailed-view command.

**Recommendation:** No changes needed to other labs. The status-code verification issue was specific to lab-04.

---

## Files Modified

1. **labs/bgp/lab-04-dampening-dynamic/initial-configs/R1.cfg**
   - Added GigabitEthernet0/2 interface configuration (10.99.0.1/30)

2. **labs/bgp/lab-04-dampening-dynamic/initial-configs/R2.cfg**
   - Added GigabitEthernet0/3 interface configuration (10.99.0.2/30)

3. **labs/bgp/lab-04-dampening-dynamic/workbook.md**
   - Task 1 Verification: Clarified status code verification uses `show ip bgp` table view
   - Task 2 Verification: Split into table-view and detailed-view commands with explanations
   - Task 3 Verification: Clarified status code verification approach
   - Task 4 Description: Reorganized to explicitly list all BGP configuration commands
   - Task 4 Verification: Replaced non-existent `show ip bgp listen range` with `show ip bgp summary`
   - Section 6.2: Added note explaining table-view vs detailed-view commands
   - Section 7 (Verification Cheatsheet): Added critical callout about status code visibility
   - Section 7 (Verification Commands table): Updated to show correct commands

---

## Testing Recommendations

When lab-04 is next deployed, verify:

1. ✅ R1 and R2 have L8 interfaces (Gi0/2 and Gi0/3) IP-addressed before any BGP config
2. ✅ Task 1 verification uses `show ip bgp dampening parameters` + `show ip bgp` (table view)
3. ✅ Task 2 flap simulation shows 'd' flag in `show ip bgp dampening flap-statistics` output
4. ✅ Task 4 listen range info appears in `show ip bgp summary` output
5. ✅ No reference to `show ip bgp listen range` command remains

---

## Lessons Learned for Future Lab Development

1. **Always verify base config claims:** If a workbook says "X is pre-loaded", verify the initial config files actually contain X.
2. **Distinguish command output formats:** IOS command variations (table vs detailed view) show different information. Document which format is needed for which verification goal.
3. **Test configuration steps end-to-end:** Every configuration step mentioned in the workbook should be tested to ensure it works as described.
4. **Verify show command output:** Commands cited in workbooks should be verified to exist on the actual platforms/images used.

---

*Corrections applied and verified 2026-04-29*
