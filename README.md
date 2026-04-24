# CCNP SPRI (300-510) Lab Series

A comprehensive set of hands-on labs for the CCNP SPRI (300-510) exam: *Implementing Cisco Service Provider Advanced Routing Solutions*.

**Exam Code:** 300-510  
**Total Blueprint Objectives:** 94  
**Planned Lab Count:** ~64 labs across 10 topics  
**Platform:** EVE-NG (Intel/Windows)

## Project Status

### Phase 1: Exam Planning ✓ Complete
- Blueprint analyzed and organized into 10 technology-based topics
- Topic plan created: `specs/topic-plan.yaml`
- Total estimated labs: 64 (including capstones)
- Coverage: 100% of exam objectives mapped

### Phase 2: Specification Development 🔄 70% Complete (7/10 topics)
**Completed:**
- [x] ospf — OSPF Routing (spec + baseline)
- [x] isis — IS-IS Routing (spec + baseline)  
- [x] bgp — BGP Scalability and Troubleshooting (spec + baseline)
- [x] routing-policy — Routing Policy and Manipulation (spec + baseline)
- [x] ipv6-transition — IPv6 Tunneling and Transition (spec + baseline)
- [x] fast-convergence — Fast Convergence (spec + baseline)
- [x] mpls — MPLS (spec + baseline)

**Remaining:**
- [ ] multicast — Multicast Routing (PIM-SM, MBGP, MSDP)
- [ ] segment-routing — Segment Routing and SR-TE
- [ ] srv6 — Segment Routing v6

### Phase 3: Lab Construction 🔄 In Progress (1 lab built)
- **ospf/lab-00-single-area-ospfv2** ✓ Built and approved
- Remaining labs build on prior lab solutions — work sequentially

## Lab Chapters

<!-- lab-index-start -->

| # | Topic | Status | Labs Est. | Blueprint Bullets | Notes |
|---|-------|--------|-----------|-------------------|-------|
| 1 | **ospf** | Phase 3 (1/6) | 6 | 1.1–1.2.b | Multiarea OSPFv2/v3, summarization, LSA behavior |
| 2 | **isis** | Phase 2 ✓ | 5 | 1.3–1.3.b | Multilevel IS-IS, dual-stack, L1/L2 |
| 3 | **bgp** | Phase 2 ✓ | 9 | 1.4–1.5.j | Scalability, communities, FlowSpec, dampening |
| 4 | **routing-policy** | Phase 2 ✓ | 7 | 3.1–3.4.b | RPL vs route-maps, conditional matching, traffic steering |
| 5 | **ipv6-transition** | Phase 2 ✓ | 6 | 1.6–1.6.e | 6PE, static tunnels, NAT64, MAP-T |
| 6 | **fast-convergence** | Phase 2 ✓ | 6 | 1.7–1.7.g | BFD, NSF, NSR, LFA/IP-FRR, BGP PIC |
| 7 | **mpls** | Phase 2 ✓ | 6 | 4.1–4.1.e | LDP, LSP, RSVP-TE, BGP-free core |
| 8 | **multicast** | Phase 2 ◻ | 8 | 2.1–2.4.b | PIM-SM, MBGP, MSDP, MLDP, IGMP/MLD |
| 9 | **segment-routing** | Phase 2 ◻ | 7 | 4.2–4.3.e | SR-TE, TI-LFA, SR Prefer, PCE, SRLG |
| 10 | **srv6** | Phase 2 ◻ | 5 | 4.4–4.4.d | SRv6 data-plane, Flex-Algo, interworking |

<!-- lab-index-end -->

## Workflow: Three-Phase Pipeline

Each topic moves through three sequential phases:

### Phase 1: Exam Planning (exam-planner skill)
- **Input:** Exam blueprint (`blueprint/300-510/blueprint.md`)
- **Output:** `specs/topic-plan.yaml` with 10 topics, dependencies, and build order
- **Status:** ✓ Complete

### Phase 2: Specification (spec-creator skill)
- **Input:** Topic from `topic-plan.yaml` + blueprint bullets
- **Output:** `labs/<topic>/spec.md` (progression table, coverage matrix) + `labs/<topic>/baseline.yaml` (topology, IPs, lab definitions)
- **Process:** One topic at a time, review after each
- **Status:** 3/10 topics done → next: `routing-policy`

### Phase 3: Lab Construction (lab-builder skill)
- **Input:** `spec.md` + `baseline.yaml` for a topic
- **Output:** Workbooks, configs, solutions, topology diagrams, fault-injection scripts (one lab at a time)
- **Process:** Sequential with pause-and-review between labs
- **Status:** Pending Phase 2 completion

## Commands

```bash
# Phase 1 (already done, but shown for reference)
/plan-exam                    # Read blueprint, create topic-plan.yaml

# Phase 2: Create specs for next topic
/create-spec routing-policy   # Create spec.md and baseline.yaml for routing-policy

# Phase 3: Build labs for a topic (after spec approval)
/build-lab routing-policy/lab-00-introduction   # Build one lab at a time
/build-topic routing-policy                     # Build all labs for a topic with review gates

# Optional: Wrap-up
/build-capstone               # Build multi-domain capstone spanning multiple topics
/tag-lab routing-policy/lab-00-introduction     # Add metadata (difficulty, blueprint refs)
```

## Getting Started

### Prerequisites
1. Clone with submodules: `git clone --recurse-submodules <repo-url>`
2. Install Python: `pip install -r requirements.txt`
3. EVE-NG running on local network (see `.agent/skills/eve-ng/SKILL.md` for image constraints)

### Running Labs
1. Navigate to a lab: `cd labs/<topic>/<lab-folder>/`
2. Run setup: `python setup_lab.py --host <eve-ng-ip>`
3. Follow the workbook: `workbook.md`

## Development

Lab creation is orchestrated via **Claude Code skills** mounted at `.agent/skills/`:

| Skill | Phase | Role |
|-------|-------|------|
| `exam-planner` | 1 | Read blueprint, produce topic plan |
| `spec-creator` | 2 | Spec one topic per run (review gate) |
| `lab-builder` | 3 | Build labs for topic (pause between each) |
| `drawio` | 3 | Render topology diagrams (Cisco style) |
| `fault-injector` | 3 | Generate fault scenarios for capstones |

See `CLAUDE.md` and `.agent/skills/CLAUDE.md` for detailed workflow context and skill documentation.
