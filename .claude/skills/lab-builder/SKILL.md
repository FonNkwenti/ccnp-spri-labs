---
name: lab-builder
description: Builds labs for a topic one at a time with pause-and-review between each. Ensures config chaining, topology continuity, and progressive difficulty. Phase 3 of the workflow (exam-planner -> spec-creator -> lab-builder). Use when the user asks to "build labs for [topic]", "generate the EIGRP labs", "start building [topic] labs", or after spec-creator has produced spec.md and baseline.yaml.
---

# Lab Builder Skill (Phase 3)

Builds labs for a topic sequentially with a review gate after each lab. Each lab's solutions
become the next lab's initial-configs, maintaining config chaining and topology continuity.
This is Phase 3 of the three-phase workflow: exam-planner -> spec-creator -> **lab-builder**.

-# Instructions

--# Step 1: Load Baseline and Spec

Read in parallel:
1. `labs/<topic>/baseline.yaml` — device list, IPs, lab definitions, objectives
2. `labs/<topic>/spec.md` — lab progression table, blueprint coverage, design decisions

If either file is missing, STOP:
> "`baseline.yaml` or `spec.md` not found for this topic. Please run the spec-creator
> skill first to generate them."

Parse the `labs:` array from baseline.yaml. This defines the full lab sequence, including
lab type (`progressive`, `standalone`, `capstone_i`, `capstone_ii`).

--# Step 2: Build Labs Sequentially (Pause-and-Review)

For each lab in `baseline.yaml` `labs:` array, in order (number 0, 1, 2, ...):

**2a. Determine initial-configs source:**

| Lab Type | `initial-configs/` Source |
|----------|--------------------------|
| Progressive (first lab, number 0) | `baseline.yaml` `core_topology` IP addressing only — no protocol config |
| Progressive (number > 0) | Previous lab's `solutions/` copied exactly |
| Standalone (`type: standalone`) | `baseline.yaml` `core_topology` IP addressing only |
| Capstone I (`type: capstone_i`) | `baseline.yaml` `core_topology` IP addressing only — clean slate |
| Capstone II (`type: capstone_ii`) | `baseline.yaml` `core_topology` IP addressing only — clean slate |

**2b. Determine active devices:**
- Read `labs[N].devices` from baseline.yaml.
- New devices (introduced in this lab but not the previous) get initial-configs from
  `core_topology` or `optional_devices` IP addressing.

**2c. Invoke lab-assembler:**
- Pass the lab entry from baseline.yaml (number, folder, title, objectives, devices, type).
- The lab directory is `labs/<topic>/<folder>/` where `<folder>` is the `folder` field
  from baseline.yaml (e.g., `lab-00-introduction`).
- `lab-assembler` generates: `workbook.md`, `initial-configs/`, `solutions/`,
  `topology.drawio`, `setup_lab.py`, `meta.yaml`, `scripts/fault-injection/`.

**2d. PAUSE for review:**

After each lab is generated, STOP and present a summary:

> "Lab [number]: **[title]** is ready for review.
>
> - Folder: `labs/<topic>/<folder>/`
> - Devices: [device list]
> - Type: [progressive/standalone/capstone_i/capstone_ii]
> - Files generated: workbook.md, [N] initial-configs, [N] solutions, topology.drawio,
>   setup_lab.py, [N] fault-injection scripts
>
> Please review the workbook and configs. Reply 'continue' to proceed to the next lab,
> or provide feedback to revise this lab first."

Do NOT proceed to the next lab until the user explicitly approves.

--# Step 3: Validation (After All Labs)

After all labs in the topic are built and approved, run the final validation checklist:

- [ ] All devices use IPs from `baseline.yaml` (core_topology + optional_devices)
- [ ] Progressive labs chain correctly: Lab N `initial-configs/` = Lab (N-1) `solutions/`
- [ ] Standalone labs start from baseline IP addressing only
- [ ] Capstone I and II start from baseline IP addressing only (clean slate)
- [ ] New devices only appear when declared in `labs[N].devices`
- [ ] No configs removed between progressive labs (only add, never remove)
- [ ] `topology.drawio` follows the drawio Visual Style Guide (white links, left labels)
- [ ] Every blueprint bullet from `spec.md` is covered by at least one lab
- [ ] Lab folder names match the `folder` field in baseline.yaml

Present the validation results and flag any issues.

-# Config Chaining Reference

```
Lab 00 (progressive)     ← baseline.yaml core_topology (IP only)
    │ solutions/
    ▼
Lab 01 (progressive)     ← Lab 00 solutions/ (exact copy)
    │ solutions/
    ▼
Lab 02 (progressive)     ← Lab 01 solutions/ (exact copy)
    │ solutions/
    ▼
  ...
    ▼
Lab N-2 (standalone)     ← baseline.yaml core_topology (IP only, not chained)
Lab N-1 (capstone_i)     ← baseline.yaml core_topology (IP only, clean slate)
Lab N   (capstone_ii)    ← baseline.yaml core_topology (IP only, clean slate)
```

**Critical rule:** Progressive labs ONLY ADD configuration between labs — never remove.
Standalone and capstone labs reset to baseline IP addressing.

-# Common Issues

--# Missing baseline.yaml or spec.md
- **Cause:** spec-creator skill has not been run for this topic.
- **Solution:** Stop. Ask the user to run the spec-creator skill first.

--# Config Chaining Failure
- **Cause:** Lab N `initial-configs/` is missing configurations from Lab (N-1) `solutions/`.
- **Solution:** Re-copy the exact contents of Lab (N-1) `solutions/` into Lab N
  `initial-configs/` before applying any new changes.

--# New Device Added Without Declaration
- **Cause:** A device appears in configs but is not in `labs[N].devices` in baseline.yaml.
- **Solution:** Cross-check the device list. Only add devices explicitly declared for that lab.

--# Topology Diagram Style Violation
- **Cause:** `topology.drawio` generated without invoking the `drawio` skill.
- **Solution:** Invoke the `drawio` skill to apply the Visual Style Guide (white links,
  Cisco icons, left labels, IP octets, legend box).

-# Examples

User: "Build the EIGRP labs" (after spec-creator has run for eigrp)

Actions:
1. Read `labs/eigrp/baseline.yaml` and `labs/eigrp/spec.md`.
2. Build lab-00-introduction: IP-only initial-configs from core_topology, invoke
   lab-assembler. PAUSE — present summary, wait for approval.
3. Build lab-01-classic-adjacency: copy lab-00 solutions as initial-configs. PAUSE.
4. Build lab-02-named-mode: copy lab-01 solutions. PAUSE.
5. Continue through all progressive labs...
6. Build lab-05-capstone-config (capstone_i): clean slate from baseline. PAUSE.
7. Build lab-06-capstone-troubleshooting (capstone_ii): clean slate from baseline. PAUSE.
8. Run final validation checklist across all 7 labs.
