# Phase IV: Resolution Report Template

Use this template to generate the final troubleshooting report.

---

## 1. Incident Summary

```
Incident ID:     [INC-YYYY-NNNN]
Lab:             labs/<topic>/lab-NN-<slug>/
Reported:        [timestamp]
Severity:        [High / Medium / Low]

Problem Statement:
[Precise technical description — specific devices, interfaces, symptoms, and timeline]
```

---

## 2. Methodology Applied

```
Selected Approach: [Top-Down / Bottom-Up / Divide & Conquer / Follow Traffic Path / Compare Configurations]

Rationale:
[Why this methodology was selected for this problem]
```

---

## 3. Diagnostic Log

Chronological record of all actions taken:

```
[HH:MM] [Action taken]
        Command: [show command or config step]
        Result:  [What was observed]

[HH:MM] [Hypothesis formed]
        Hypothesis: [...]
        Test:       [...]
        Result:     [...]

[HH:MM] ROOT CAUSE IDENTIFIED: [brief description]
```

---

## 4. Root Cause Analysis

```
Root Cause:
[Technical explanation of what was wrong and why it caused the observed symptoms]

Technical Details:
- [Specific misconfig / parameter mismatch / missing command]
- [How it prevented the expected behaviour]

Impact:
- [What failed as a result]
```

---

## 5. Resolution Actions

```
Configuration Change on [Device]:
---------------------------------
[Device]# configure terminal
[Device](config)# [commands applied]
[Device](config)# end
[Device]# write memory

Verification:
-------------
[Device]# [show command confirming fix]
[expected output confirming resolution]
```

---

## 6. Testing and Verification

```
Test 1: [Description]
        Command / Action: [...]
        Result: [SUCCESS ✓ / FAIL ✗]

Test 2: [Description]
        Command / Action: [...]
        Result: [SUCCESS ✓ / FAIL ✗]

All symptoms from initial problem report resolved: [YES / NO]
```

---

## 7. Lessons Learned and Recommendations

```
Root Cause Category: [e.g., Timer Mismatch / AS Number Error / Missing Network Statement]

Exam Relevance:
- [Which ENARSI blueprint bullet this maps to]
- [Common exam trap to remember]

Preventive Notes:
- [What to verify when configuring this feature]
- [Common pitfalls for this protocol/feature]
```
