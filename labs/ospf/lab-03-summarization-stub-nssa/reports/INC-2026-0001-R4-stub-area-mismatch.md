# Phase IV: Resolution Report

---

## 1. Incident Summary

```
Incident ID:     INC-2026-0001
Lab:             labs/ospf/lab-03-summarization-stub-nssa/
Reported:        2026-04-27
Severity:        Medium

Problem Statement:
R4 reported zero OSPF neighbors despite the R3-R4 link (10.1.34.0/24,
R3 Gi0/1 <-> R4 Gi0/0) being physically up and IP-reachable. Area 2 was
fully isolated from the OSPF domain -- no inter-area routes from Area 2
were visible anywhere in the topology.
```

---

## 2. Methodology Applied

```
Selected Approach: Compare Configurations

Rationale:
A clean baseline existed in initial-configs/ and the student's partial
configuration on R3 was visible in the running config. Diffing both live
routers against the baseline exposed the asymmetry directly -- no traffic
tracing or bottom-up physical checks were required because both interfaces
were already confirmed up/up.
```

---

## 3. Diagnostic Log

```
[T+0] Checked OSPF neighbors on R3
        Command: show ip ospf neighbor
        Result:  R2 FULL, R5 FULL -- R4 absent from table

[T+1] Checked OSPF interface state on R3
        Command: show ip ospf interface brief
        Result:  Gi0/1 in Area 2, state DR, 0/0 neighbors
                 Interface is active; OSPF is running; no peer

[T+2] Checked OSPF neighbors on R4
        Command: show ip ospf neighbor
        Result:  Empty -- no neighbors at all

[T+3] Compared running OSPF config on R3 vs baseline
        Command: show running-config | section router ospf
        Result:  R3 has "area 2 stub no-summary" -- not in initial-config
                 Student has already configured the stub area on the ABR

[T+4] Compared running OSPF config on R4 vs baseline
        Command: show running-config | section router ospf
        Result:  R4 has only the three network statements -- no area 2 stub

[T+4] ROOT CAUSE IDENTIFIED: OSPF Hello E-bit mismatch
        R3 sends Hellos with E=0 (stub area)
        R4 sends Hellos with E=1 (regular area, default)
        IOS silently drops mismatched Hellos -- adjacency never reaches Init

[T+5] Student applied fix on R4
        Command: area 2 stub (under router ospf 1)

[T+6] Verified resolution
        Command: show ip ospf neighbor (on both R3 and R4)
        Result:  R3: 10.0.0.4 FULL/DR | R4: 10.0.0.3 FULL/BDR
```

---

## 4. Root Cause Analysis

```
Root Cause:
"area 2 stub" was configured on R3 (the ABR) but not on R4 (the stub
area internal router). OSPF requires every router in a stub area to
declare the area as stub -- not just the ABR.

Technical Details:
- OSPF encodes the area type in every Hello packet via the E bit
  (External LSA capability bit): E=0 for stub, E=1 for regular
- R3 "area 2 stub no-summary" set E=0 on its Gi0/1 Hello packets
- R4 had no stub declaration, so its Hellos carried E=1 (default)
- IOS discards any Hello where the E bit does not match the local value
- Result: neither side ever transitions past Down state

Impact:
- R3-R4 adjacency never formed
- Area 2 was completely isolated -- no routes from 10.0.0.4/32,
  172.16.4.0/24, or 10.1.34.0/24 reached any other router
```

---

## 5. Resolution Actions

```
Configuration Change on R4:
---------------------------
R4(config)# router ospf 1
R4(config-router)# area 2 stub
R4(config-router)# end

Note: "no-summary" is NOT added on R4 -- that keyword is ABR-only and
suppresses Type-3 LSAs from being flooded into the stub area. Internal
routers only need "area N stub" to set the E bit correctly.

No change needed on R3 -- "area 2 stub no-summary" was correct.
```

---

## 6. Testing and Verification

```
Test 1: R3 OSPF neighbor table
        Command: show ip ospf neighbor
        Result:  10.0.0.4  FULL/DR  Gi0/1  SUCCESS

Test 2: R4 OSPF neighbor table
        Command: show ip ospf neighbor
        Result:  10.0.0.3  FULL/BDR  Gi0/0  SUCCESS

All symptoms from initial problem report resolved: YES
```

---

## 7. Lessons Learned and Recommendations

```
Root Cause Category: Stub Area Misconfiguration -- Missing area stub on internal router

Exam Relevance:
- Maps to SPRI 300-510 blueprint: OSPF area types (stub, totally stubby, NSSA)
- Common exam trap: candidates configure the ABR correctly but forget that
  ALL routers inside the stub area must also have "area N stub"
- "no-summary" is ABR-only -- adding it to an internal router is harmless
  but irrelevant; the E bit behaviour comes from "stub" alone

Preventive Notes:
- After configuring any stub or NSSA area, verify with
  "show ip ospf" -- it lists all configured area types per process
- Check "show ip ospf neighbor" on BOTH sides of the link;
  a one-sided empty table with an up/up interface almost always
  means a Hello parameter mismatch (area type, timer, or MTU)
- The E bit mismatch produces no log messages and no debug output
  at default settings -- silence is not a sign the link is healthy
```
