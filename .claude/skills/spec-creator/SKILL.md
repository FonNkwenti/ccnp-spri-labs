---
name: spec-creator
description: Generates detailed lab specs and baseline.yaml for a single topic from the topic-plan.yaml. Creates progressive lab sequences with blueprint coverage, shared topology, and folder structure. Phase 2 of the workflow (exam-planner -> spec-creator -> lab-builder). Use when the user asks to "create specs for [topic]", "plan labs for [topic]", "generate baseline for [topic]", or after exam-planner has produced topic-plan.yaml.
---

# Spec Creator Skill (Phase 2)

Generates the detailed lab specification and baseline.yaml for a single topic from the
topic plan. Runs once per topic with a review gate after each. This is Phase 2 of the
three-phase workflow: exam-planner -> **spec-creator** -> lab-builder.

-# Instructions

--# Step 1: Read Topic Plan and Blueprint

Read in parallel:
1. `specs/topic-plan.yaml` — find the target topic entry (topic_id, blueprint_refs,
   estimated_labs, scope_notes, dependencies)
2. `blueprint/<exam-code>/blueprint.md` — extract the full text of each blueprint bullet
   listed in the topic's `blueprint_refs`

If `specs/topic-plan.yaml` does not exist, STOP and ask:
> "No topic plan found. Please run the exam-planner skill first to generate
> `specs/topic-plan.yaml` from the exam blueprint."

If the user specifies a topic that is not in the plan, STOP and ask whether to add it
to the plan or whether they meant a different topic.

--# Step 2: Design the Lab Sequence

Design a progressive lab series for this topic. Rules:

**Progression and continuity:**
1. Labs are numbered starting from `00` (introduction/foundation)
2. Each lab builds on the previous — solutions become the next lab's initial-configs
3. Topology and IP addressing remain consistent across all labs in the topic
4. Only add configuration between labs, never remove
5. Labs that cannot flow progressively from the sequence go at the **end**, just before
   the capstones, and are tagged `standalone: true`

**Lab folder naming:**
- Each lab folder includes a descriptive slug: `lab-00-introduction`,
  `lab-01-classic-adjacency`, `lab-02-named-mode`, etc.
- Slug must be lowercase kebab-case, max 40 characters
- The slug should describe the lab's primary focus

**Difficulty progression:**
- Foundation (labs 00-01): basic concepts, simple topology
- Intermediate (labs 02-04): deeper features, more devices
- Advanced (labs 05+): complex scenarios, edge cases, optimisation
- Capstone I (second-to-last): full protocol configuration from scratch
- Capstone II (last): comprehensive troubleshooting with 5+ concurrent faults

**Blueprint coverage:**
- Every blueprint bullet in the topic's `blueprint_refs` must be covered by at least
  one lab
- Each lab declares which `blueprint_refs` it addresses

**Lab count:**
- Use the `estimated_labs` from topic-plan.yaml as a starting point
- Adjust if needed (more bullets = more labs), but confirm with the user if deviating
  by more than +/- 2 from the estimate
- The last 2 labs are ALWAYS Capstone I and Capstone II

--# Step 3: Design Shared Topology

Design the topology that all labs in this topic will share:

1. **Core devices** — present in ALL labs (minimum 3, maximum 15 total)
2. **Optional devices** — introduced in later labs for advanced scenarios
3. **Links** — all connections with pre-reserved subnets
4. **IP addressing** — fully pre-planned for all devices (core + optional), even if
   optional devices are not active in early labs

Platform selection: consult `eve-ng/SKILL.md` for valid platforms. Default to `iosv`
for routing, `iosvl2` for switching, `csr1000v` for IOS-XE features.

--# Step 4: Write spec.md

Write `labs/<topic>/spec.md`:

```markdown
# [Topic Name] — Lab Specification

## Exam Reference
- **Exam:** [Exam Name] ([Exam Code])
- **Blueprint Bullets:**
  - [bullet ID]: [full bullet text]
  - [bullet ID]: [full bullet text]

## Topology Summary
[2-3 lines describing the topology: device count, roles, link structure]

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-introduction | [Title] | Foundation | 45m | progressive | 3.1 | R1, R2, R3 |
| 01 | lab-01-classic-adjacency | [Title] | Foundation | 60m | progressive | 3.2.a | R1, R2, R3 |
| ... | | | | | | | |
| N-1 | lab-N-1-capstone-config | [Protocol] Capstone I | Advanced | 120m | capstone_i | all | all |
| N | lab-N-capstone-troubleshooting | [Protocol] Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.1 | [description] | lab-00, lab-01 |
| 3.2.a | [description] | lab-01, lab-02 |

## Design Decisions
- [Any notable grouping, ordering, or topology decisions and their rationale]
```

--# Step 5: Write baseline.yaml

Write `labs/<topic>/baseline.yaml`:

```yaml
topic: [topic_id]
topic_name: "[Topic Name]"
exam: "[Exam Code]"
version: 1.0

meta:
  created:
    date: "[YYYY-MM-DD]"
    agent: claude-sonnet-4-6
    skill: spec-creator
    skill_version: "[date of .agent/skills HEAD]"  # run: git -C .agent/skills log --format='%ci' -1
  updated: []

core_topology:
  devices:
    - name: R1
      platform: iosv|iosvl2|csr1000v|iol_l3|iol_l2|xrv9k|nxosv9k|asav
      role: [descriptive role]
      loopback0: [IP/mask]
      console_port: null   # Dynamic — assigned by EVE-NG at lab creation time
  links:
    - id: L1
      source: [Device:Interface]
      target: [Device:Interface]
      subnet: [network/mask]

optional_devices:
  - name: R4
    platform: iosv|iosvl2|csr1000v|iol_l3|iol_l2
    role: [role]
    loopback0: [IP/mask]
    console_port: null   # Dynamic
    available_from: lab-02-[slug]
    purpose: [why needed]

optional_links:
  - id: L3
    source: [Device:Interface]
    target: [Device:Interface]
    subnet: [network/mask]
    available_from: lab-02-[slug]

labs:
  - number: 0
    folder: lab-00-introduction
    title: "[Lab Title]"
    difficulty: Foundation
    type: progressive
    time_minutes: 45
    devices: [R1, R2, R3]
    blueprint_refs: ["3.1"]
    objectives:
      - [objective 1]
      - [objective 2]

  - number: 1
    folder: lab-01-classic-adjacency
    title: "[Lab Title]"
    difficulty: Foundation
    type: progressive
    time_minutes: 60
    devices: [R1, R2, R3]
    extends: lab-00-introduction
    blueprint_refs: ["3.2.a"]
    objectives:
      - [objective 1]

  # ... progressive labs ...

  # Standalone labs (if any) go here, before capstones
  - number: N-2
    folder: lab-N-2-[slug]
    title: "[Lab Title]"
    difficulty: Advanced
    type: standalone
    time_minutes: 90
    devices: [R1, R2, R3, R4]
    blueprint_refs: ["3.5"]
    objectives:
      - [objective — does not depend on previous lab state]

  # Capstones — always last two
  - number: N-1
    folder: lab-N-1-capstone-config
    title: "[Protocol] Full Protocol Mastery — Capstone I"
    type: capstone_i
    clean_slate: true
    difficulty: Advanced
    time_minutes: 120
    blueprint_refs: all
    devices: [all active devices]
    objectives:
      - [comprehensive config objectives covering all blueprint bullets]

  - number: N
    folder: lab-N-capstone-troubleshooting
    title: "[Protocol] Comprehensive Troubleshooting — Capstone II"
    type: capstone_ii
    clean_slate: true
    difficulty: Advanced
    time_minutes: 120
    blueprint_refs: all
    devices: [all active devices]
    objectives:
      - [5+ concurrent fault diagnosis objectives spanning all blueprint bullets]
```

## Required per-lab fields in baseline.yaml labs[]

- `number` — integer, lab ordering within the topic
- `folder` — directory name (kebab-case), matches `labs/<topic>/<folder>/`
- `title` — human-readable title
- `difficulty` — **REQUIRED**. One of: `Foundation` | `Intermediate` | `Advanced`.
  This field drives the hard model-enforcement gate in `/build-lab` and `/build-topic`.
  A missing or invalid difficulty will cause the gate to fall back to `Intermediate`
  and warn the user. Pick the tier honestly — do not downgrade difficulty to enable
  a cheaper model. Difficulty reflects the lab's pedagogical rigor, not build budget.
- `blueprint_refs` — list of exam-blueprint bullet IDs this lab covers
- `devices` — active devices from core_topology.devices
- `time_minutes` — estimated completion time
- `objectives` — list of learning objectives

## Difficulty tier definitions (for spec authors)

- **Foundation** — first lab(s) of a topic; single concept; minimal prior knowledge.
  Scaffolds into later labs. Example: `lab-00-single-area-ospfv2`.
- **Intermediate** — combines 2–3 concepts; exercises real troubleshooting.
  The meat of the certification. Example: `lab-01-multiarea-ospfv2`.
- **Advanced** — capstone-style; spans multiple areas; open-ended troubleshooting
  or design justification. Both capstone labs are always `Advanced`.

See `MODEL-POLICY.md` at the skills submodule root for the allowed-model mapping
per tier.

--# Step 6: Create Lab Folder Structure

Create empty lab subdirectories under `labs/<topic>/`:

```
labs/<topic>/
  lab-00-introduction/
  lab-01-classic-adjacency/
  lab-02-named-mode/
  ...
  lab-N-1-capstone-config/
  lab-N-capstone-troubleshooting/
```

Do NOT generate lab content (workbooks, configs, scripts) — that is the lab-builder
skill's job in Phase 3.

--# Step 7: Validate

Before presenting to the user, confirm:
- [ ] Every blueprint bullet in the topic's `blueprint_refs` is covered by at least one lab
- [ ] Total device count is between 3 (minimum) and 15 (maximum) across core + optional
- [ ] Platform choices respect EVE-NG constraints (see `eve-ng/SKILL.md`)
- [ ] IP addresses are pre-reserved for all optional devices
- [ ] The last 2 labs are Capstone I (`type: capstone_i`) and Capstone II (`type: capstone_ii`)
- [ ] All progressive labs form a valid chain (each extends the previous)
- [ ] Standalone labs (if any) come after all progressive labs and before capstones
- [ ] Lab folder names are valid kebab-case and match the `folder` field in baseline.yaml
- [ ] `spec.md` Blueprint Coverage Matrix has no gaps
- [ ] Every lab entry has a `difficulty` field set to `Foundation` | `Intermediate` | `Advanced` (required for the model-enforcement gate)

--# Step 8: Pause for Review

Present the spec and explicitly ask:

> "Here is the lab specification for [Topic Name] ([N] labs).
>
> Please review:
> 1. Does the lab progression make sense?
> 2. Are the blueprint bullets correctly assigned?
> 3. Is the topology appropriate for these labs?
> 4. Any labs to add, remove, or reorder?
>
> Once approved, I'll move to the next topic: [next topic from build_order],
> or if all topics are done, we can start Phase 3 (lab-builder)."

Do NOT proceed to the next topic or to Phase 3 until the user approves.

-# Continuity Rules

1. **Core devices** maintain consistent IPs across ALL labs in the topic
2. **Optional devices** are pre-reserved with IPs but only activated when declared
3. **Progressive labs** chain: solutions become the next lab's initial-configs
4. **Standalone labs** start from baseline topology (IP only, no protocol config)
5. **Capstones** always start from clean slate (IP addressing only)
6. **Config chaining rule (progressive only):** only add commands between labs, never remove

-# Common Issues

--# topic-plan.yaml not found
- **Cause:** exam-planner skill has not been run.
- **Solution:** Stop. Ask the user to run the exam-planner skill first.

--# Topic has too many blueprint bullets for estimated lab count
- **Cause:** The exam-planner underestimated lab count for this topic.
- **Solution:** Propose an increased count and explain which bullets need additional labs.
  Update `specs/topic-plan.yaml` with the revised count after user approval.

--# baseline.yaml already exists for this topic
- **Cause:** A previous spec was generated for this topic.
- **Solution:** Stop and ask: overwrite, extend, or skip? Do not silently overwrite.

--# Dependency topic not yet spec'd
- **Cause:** This topic depends on another (e.g., Redistribution depends on EIGRP + OSPF)
  that hasn't been through spec-creator yet.
- **Solution:** Warn the user but allow proceeding. The dependency is for build order
  (lab generation), not spec creation. Note: "Specs for [dependency] should be approved
  before building labs for this topic."

-# Examples

User: "Create specs for EIGRP" (after exam-planner has run)

Actions:
1. Read `specs/topic-plan.yaml` — find the eigrp topic entry.
2. Read `blueprint/350-410/blueprint.md` — extract EIGRP-related bullets.
3. Design 7-lab sequence: introduction, classic adjacency, named mode, advanced features,
   summarization-and-filtering, capstone-config, capstone-troubleshooting.
4. Design shared topology: 3 core routers (R1 hub, R2/R3 branches) + optional R4 (stub).
5. Write `labs/eigrp/spec.md` with progression table and coverage matrix.
6. Write `labs/eigrp/baseline.yaml` with full topology and lab definitions.
7. Create empty folders: `labs/eigrp/lab-00-introduction/`, etc.
8. Present spec and pause for review.
