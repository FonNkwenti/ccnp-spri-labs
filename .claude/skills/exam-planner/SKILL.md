---
name: exam-planner
description: Reads a full exam blueprint and produces a topic-plan.yaml with technology-based topic breakdown, lab counts, blueprint coverage mapping, and empty folder structure. Use when the user asks to "plan the exam", "create topic plan", "break down the blueprint", or after bootstrap when the blueprint file has been uploaded.
---

# Exam Planner Skill

Reads a complete certification exam blueprint and produces a strategic topic plan that
organises all exam objectives into technology-based lab topics. This is Phase 1 of the
three-phase workflow: **exam-planner** -> spec-creator -> lab-builder.

-# Instructions

--# Step 1: Locate and Validate the Blueprint

1. Look for the blueprint file in `blueprint/<exam-code>/`. The file may be named
   inconsistently (e.g., `exam-topics.md`, `blueprint.md`, `350-401.md`).
2. If found but poorly named, rename it to `blueprint.md` inside the same folder.
3. If not found, ask the user to upload it:
   > "Please place the exam blueprint markdown file in `blueprint/<exam-code>/blueprint.md`
   > (e.g., `blueprint/350-401/blueprint.md`). The file should contain the official exam
   > topics copied from Cisco's exam page."
4. Read the blueprint file. Confirm it contains numbered exam objectives with domain
   structure (e.g., "1.0 Architecture", "2.0 Virtualization", etc.).
5. Extract: exam name, exam code, blueprint version/date if present, total domain count,
   total objective count.
6. Check for supplementary references in `blueprint/<exam-code>/references/`. If the
   folder exists and contains files (markdown, text, PDF, etc.), read them all. These are
   additional materials the user has provided to enrich the terse blueprint bullets — OCG
   chapter outlines, study guide excerpts, course notes, vendor documentation, etc. Use
   them to inform topic grouping, scope_notes, and lab count estimates. References are
   **optional** — the skill must work with just the blueprint alone.

--# Step 2: Analyse and Group Objectives into Topics

Group blueprint objectives into **technology-based topics**, not by blueprint domain order.
The goal is to create lab topics that make sense as learning units.

**Grouping rules:**

1. **Large technologies get their own topic.** If a technology has 4+ blueprint bullets
   or spans significant depth (e.g., OSPF, EIGRP, BGP), it becomes its own topic.
2. **Related small technologies may be combined.** If a technology has only 1-2 bullets
   and naturally groups with another (e.g., all multicast protocols under "Multicasting"),
   combine them into a single topic.
3. **Topic names are technology-based, not domain-based.** Use names like `eigrp`, `ospf`,
   `bgp`, `switching`, `multicasting`, `security`, `automation` — not "Domain 3" or
   "Infrastructure 3.0".
4. **Every blueprint bullet must map to exactly one topic.** No bullet left uncovered,
   no bullet assigned to multiple topics.

**Output per topic:**
- `topic_id`: lowercase kebab-case folder name (e.g., `eigrp`, `ospf`, `ip-services`)
- `topic_name`: human-readable title (e.g., "EIGRP Routing", "IP Services")
- `blueprint_refs`: list of blueprint bullet IDs this topic covers (e.g., `["3.1", "3.2.a", "3.2.b"]`)
- `estimated_labs`: estimated number of labs (including 2 capstones)
- `scope_notes`: brief note on what this topic covers and any grouping decisions
- `dependencies`: list of topic_ids that should be completed before this one (optional)

--# Step 3: Determine Lab Counts and Progression

For each topic, estimate the number of labs needed:

1. **Minimum:** 3 labs (1 foundation + Capstone I + Capstone II)
2. **Typical:** 5-8 labs for a major technology (foundation -> intermediate -> advanced -> capstones)
3. **Maximum:** 10 labs for very large technologies

The last 2 labs in every topic are always **Capstone I** (full configuration challenge)
and **Capstone II** (comprehensive troubleshooting).

Assign a suggested build order across topics. This is a recommendation, not a constraint.
Consider dependencies (e.g., EIGRP and OSPF before Redistribution).

--# Step 4: Write topic-plan.yaml

Write `specs/topic-plan.yaml` in the exam project root:

```yaml
exam:
  name: "[Full Exam Name]"
  code: "[Exam Code]"
  blueprint_version: "[Version/date from blueprint file, or 'unknown']"
  blueprint_source: "blueprint/<exam-code>/blueprint.md"
  total_objectives: [count]
  planned_date: "[YYYY-MM-DD]"

topics:
  - topic_id: eigrp
    topic_name: "EIGRP Routing"
    blueprint_refs:
      - "3.1"
      - "3.2.a"
      - "3.2.b"
    estimated_labs: 7
    scope_notes: "Covers classic and named mode, dual-stack, stub, summarization, authentication"
    dependencies: []
    build_order: 1

  - topic_id: ospf
    topic_name: "OSPF Routing"
    blueprint_refs:
      - "3.3"
      - "3.3.a"
      - "3.3.b"
    estimated_labs: 8
    scope_notes: "Covers OSPFv2/v3, area types, LSA types, tuning, authentication"
    dependencies: []
    build_order: 2

  # ... one entry per topic

coverage_matrix:
  # Every blueprint bullet mapped to its topic — ensures nothing is missed
  "3.1": eigrp
  "3.2.a": eigrp
  "3.3": ospf
  # ... one entry per bullet

summary:
  total_topics: [count]
  total_estimated_labs: [count]
  build_order: ["eigrp", "ospf", "bgp", "redistribution", ...]
```

--# Step 5: Create Empty Folder Structure

Create empty directories for each topic:

```
labs/
  eigrp/
  ospf/
  bgp/
  redistribution/
  ...
```

Do NOT create lab subdirectories yet (e.g., `lab-01-xxx/`). Those are created by the
spec-creator skill in Phase 2.

Also create the specs directory if it doesn't exist:
```
specs/
  topic-plan.yaml   (just written in Step 4)
```

--# Step 6: Generate Coverage Report

Print a summary to the user showing:

1. **Topic breakdown table:**

| # | Topic | Labs | Blueprint Bullets | Dependencies |
|---|-------|------|-------------------|--------------|
| 1 | EIGRP | 7 | 3.1, 3.2.a, 3.2.b | none |
| 2 | OSPF | 8 | 3.3, 3.3.a, 3.3.b | none |
| ... | | | | |

2. **Coverage check:** Confirm every blueprint bullet is assigned to a topic.
   If any bullet is unassigned, flag it explicitly.

3. **Suggested build order** with rationale for dependencies.

4. **Total lab count** across all topics (including capstones).

--# Step 7: Pause for Review

Present the plan and explicitly ask:

> "Here is the topic plan for [Exam Name]. Please review:
> 1. Are the topic groupings correct? Should any be split or merged?
> 2. Are the lab counts reasonable?
> 3. Is the build order right?
> 4. Any topics missing or misassigned?
>
> Once approved, I'll proceed to Phase 2 (spec-creator) to build detailed
> specs for each topic, starting with [first topic in build order]."

Do NOT proceed to Phase 2 until the user explicitly approves.

-# Validate

Before presenting the plan, confirm:
- [ ] Every blueprint bullet is assigned to exactly one topic
- [ ] No topic has fewer than 3 estimated labs
- [ ] Every topic has a unique `topic_id` (valid as a folder name)
- [ ] `coverage_matrix` has one entry per blueprint bullet
- [ ] `build_order` is assigned to every topic
- [ ] Dependencies form a DAG (no circular dependencies)
- [ ] Empty `labs/<topic>/` folders have been created

-# Common Issues

--# Blueprint file not found
- **Cause:** User has not uploaded the blueprint, or it's in an unexpected location.
- **Solution:** Search the project for any `.md` file containing exam objective numbering
  (e.g., "1.0", "2.0" patterns). If found, confirm with user and move to
  `blueprint/<exam-code>/blueprint.md`. If not found, ask user to upload.

--# Technology too broad to be a single topic
- **Cause:** A technology like "Infrastructure Services" covers DHCP, NTP, SNMP, syslog,
  TFTP — each with different lab setups.
- **Solution:** If the combined bullet count exceeds 8, consider splitting. Ask the user:
  "Infrastructure Services has 10 bullets. Should I split into 'IP Services' and
  'Network Management', or keep as one topic with more labs?"

--# Blueprint has ambiguous grouping
- **Cause:** Some bullets could belong to multiple topics (e.g., "3.4 Configure redistribution
  between EIGRP and OSPF" touches both protocols).
- **Solution:** Assign to the topic where the skill is primarily tested. Redistribution
  between protocols gets its own topic if there are 3+ bullets. Note the cross-reference
  in `scope_notes`.

--# Exam blueprint is outdated
- **Cause:** User uploaded an old version of the blueprint.
- **Solution:** Check for version dates in the file. If the blueprint appears older than
  1 year, warn the user:
  > "This blueprint appears to be from [date]. Cisco may have updated the exam topics.
  > Please verify at https://www.cisco.com/c/en/us/training-events/training-certifications/exams.html
  > before I proceed."

-# Examples

User: "Plan the CCNP ENCOR exam labs from the blueprint I uploaded."

Actions:
1. Read `blueprint/350-401/blueprint.md`.
2. Group objectives into topics: eigrp, ospf, bgp, switching, wireless, security,
   automation, ip-services, virtualization, network-design.
3. Estimate labs per topic (5-8 each, ~65 total).
4. Write `specs/topic-plan.yaml` with full coverage matrix.
5. Create empty `labs/eigrp/`, `labs/ospf/`, etc.
6. Present topic breakdown table and coverage report.
7. Pause for user review and approval.
