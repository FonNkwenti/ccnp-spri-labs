---
name: cisco-troubleshooting-1
description: Systematically diagnoses and resolves Cisco IOS network faults using structured methodologies. Use when a user reports a network fault, says a lab "isn't working", asks to "troubleshoot" a problem, or describes EIGRP/OSPF/BGP adjacency failures, missing routes, connectivity problems, or configuration errors in an EVE-NG lab. Do NOT use for initial network design, security hardening, capacity planning, or routine monitoring.
---

# Cisco Network Troubleshooting Skill

Implements the **Structured Troubleshooting Process** from Cisco curriculum. Every fault follows a four-phase lifecycle: Problem Definition → Methodology Selection → Diagnostic Execution → Resolution & Reporting.

Integrates with EVE-NG labs by reading `workbook.md` for context, connecting to live routers via Netmiko (telnet to EVE-NG host or SSH), and comparing against `initial-configs/` and `solutions/`.

-# Instructions

--# Phase 0: Lab Context Gathering (Mandatory)

Before diagnosing, read the lab files at `labs/<topic>/lab-NN-<slug>/`:

1. **`workbook.md`** — topology, objectives, Console Access Table, expected verification outputs, Section 9 troubleshooting scenarios (private reference — do NOT reveal unless asked)
2. **`initial-configs/`** — pre-configured baseline state for each router
3. **`solutions/`** — expected end-state (private reference only)

Parse the Console Access Table to build the device-to-port map:
```
R1 → <port> | R2 → <port> | R3 → <port>   (dynamic EVE-NG ports from workbook Section 3)
```
EVE-NG assigns ports dynamically per lab session — check the Console Access Table in `workbook.md` Section 3 or the EVE-NG web UI for the assigned ports.

--# Phase I: Problem Definition

Transform vague symptoms into a precise problem statement.

1. Gather: exact symptoms, affected devices/interfaces, when it started, what config changed
2. Clarify using lab context — ask targeted questions: "Are you on Objective 2?", "Which router did you configure last?"
3. Document a crisp statement: **Symptoms** + **Scope** + **Lab Objective** + **Expected baseline**

See `references/methodologies.md` for examples of problem statement transformations.

--# Phase II: Methodology Selection

Use this decision tree to select the approach, then state the selection and rationale.

```
Physical problem (cable / power / hardware)?
├─ YES → Bottom-Up
└─ NO → Continue

Working reference device to compare against?
├─ YES → Compare Configurations
└─ NO → Continue

Clearly application layer (DNS / HTTP / email, ping works)?
├─ YES → Top-Down
└─ NO → Continue

Multi-hop routing / WAN / ACL blocking suspected?
├─ YES → Follow the Traffic Path
└─ NO → Divide and Conquer (default — start at Layer 3 with ping)
```

See `references/methodologies.md` for full descriptions of each methodology.

--# Phase III: Diagnostic Execution

Connect to routers via Netmiko:
```python
from netmiko import ConnectHandler
conn = ConnectHandler(
    device_type="cisco_ios_telnet",   # or "cisco_ios" for SSH
    host="<eve-ng-ip>",               # EVE-NG server IP
    port=32768,                       # dynamic port from Console Access Table
    username="", password="", secret="",
    timeout=10,
)
output = conn.send_command("show ip eigrp neighbors")
conn.disconnect()
```

Execute the diagnostic loop:
1. Gather information — run `show` commands on **both sides** of each relevant link
2. Establish baseline — compare live state against `initial-configs/` and `solutions/`
3. Eliminate valid causes — systematically rule out functioning components
4. Hypothesize → Test → Conclude → Iterate
5. Verify resolution — confirm all original symptoms are gone

See `references/diagnostic-commands.md` for the full CLI command library and evidence table template.

--# Phase IV: Resolution & Reporting

Generate a resolution report covering:
1. Incident Summary (problem statement, lab, severity)
2. Methodology Applied (selected approach + rationale)
3. Diagnostic Log (chronological, timestamped)
4. Root Cause Analysis (technical explanation + exam relevance)
5. Resolution Actions (exact IOS commands used + verification)
6. Testing & Verification (all symptoms confirmed resolved)
7. Lessons Learned (exam trap, preventive notes)

See `references/resolution-report-template.md` for the full template.

-# Common Issues

--# Lab context files not found
- **Cause:** Lab path is wrong or workbook.md has not been generated yet.
- **Solution:** Confirm the path format `labs/<topic>/lab-NN-<slug>/`. If workbook.md is missing, run the `create-lab` skill first.

--# Console Access Table missing or unparseable
- **Cause:** workbook.md was generated with a non-standard format, or dynamic EVE-NG ports haven't been populated yet.
- **Solution:** Ask the user to open the EVE-NG web UI, start the lab, note each node's assigned telnet port, and add them to `workbook.md` Section 3. There is no static port fallback — EVE-NG ports are always dynamic.

--# Netmiko connection refused
- **Cause:** EVE-NG lab is not running or the node has not finished booting.
- **Solution:** Open EVE-NG web UI and confirm all nodes show "Running" (green). IOSv boot typically takes 60–90 seconds. XRv 9000 may take 10+ minutes. Retry after boot completes.

--# User asks for the solution directly
- **Cause:** User is stuck or frustrated.
- **Solution:** Guide toward discovery first ("What does `show ip ospf neighbor` show on R2?"). Only reveal `solutions/` content if the user explicitly asks for it.

-# Quick Reference

| Resource | Path |
|----------|------|
| Lab workbook | `labs/<topic>/lab-NN-<slug>/workbook.md` |
| Initial configs | `labs/<topic>/lab-NN-<slug>/initial-configs/` |
| Solution configs | `labs/<topic>/lab-NN-<slug>/solutions/` |
| Chapter baseline | `labs/<topic>/baseline.yaml` |

-# Examples

**User:** "My EIGRP adjacency between R1 and R2 isn't forming. I've checked the configs but can't figure it out."

Actions:
1. Read `workbook.md` to identify the topology and which objective is in scope.
2. Parse Console Access Table for R1 and R2 ports.
3. Select **Divide and Conquer** (adjacency issue, unknown layer).
4. Connect to both routers — run `show ip eigrp neighbors`, `show ip interface brief`, `show ip protocols`.
5. Compare against `initial-configs/` to see what the student added vs. the baseline.
6. Form hypotheses: AS mismatch? Passive interface? K-value mismatch? Mismatched network statement?
7. Test each hypothesis. Report root cause without revealing solution configs directly.
