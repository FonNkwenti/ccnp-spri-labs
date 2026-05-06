# CCNP SPRI (300-510) Lab Series

> Hands-on labs for the CCNP SPRI (300-510) exam: *Implementing Cisco Service Provider Advanced Routing Solutions*.
> Built on EVE-NG (Intel/Windows) using the [cisco-lab-skills](.agent/skills/) toolkit.

**For current build progress, see [`STATUS.md`](STATUS.md).**

## At a Glance

| | |
|---|---|
| **Exam** | CCNP SPRI — Implementing Cisco Service Provider Advanced Routing Solutions |
| **Code** | 300-510 |
| **Blueprint** | [`blueprint/300-510/blueprint.md`](blueprint/300-510/blueprint.md) |
| **Topics** | 10 (see [`specs/topic-plan.yaml`](specs/topic-plan.yaml)) |
| **Total labs (planned)** | ~64 |
| **Platform** | EVE-NG (Intel/Windows) |
| **Skill toolkit** | [`.agent/skills/`](.agent/skills/) (git submodule) |

## Quick Start

```bash
git clone --recurse-submodules <repo-url>
cd ccnp-spri-labs
pip install -r requirements.txt
```

Run the reference lab to verify your EVE-NG setup:

```bash
cd labs/ospf/lab-00-single-area-ospfv2/
python setup_lab.py --host <eve-ng-ip>
# then follow workbook.md
```

> First time? Read [`labs/ospf/lab-00-single-area-ospfv2/README.md`](labs/ospf/lab-00-single-area-ospfv2/) for a full walkthrough.

## Repository Layout

```
ccnp-spri-labs/
├── blueprint/300-510/          Exam blueprint (source of truth for objectives)
├── specs/topic-plan.yaml       Topic breakdown + build order (Phase 1 output)
├── labs/<topic>/               Per-topic specs (Phase 2) and lab builds (Phase 3)
│   ├── spec.md                 Topic spec — progression and coverage
│   ├── baseline.yaml           Topology + IP plan + lab definitions
│   └── lab-NN-<slug>/          Built lab: workbook, configs, topology, scripts
├── memory/                     Cross-session notes and progress logs
├── tests/                      Repo-level tests
└── .agent/skills/              Lab-generation toolkit (git submodule)
```

## How Labs Are Built

Every topic moves through three sequential phases. The skill toolkit at `.agent/skills/` automates each one.

| Phase | Skill | Input → Output |
|-------|-------|----------------|
| **1. Plan** | `exam-planner` | Blueprint → `specs/topic-plan.yaml` |
| **2. Spec** | `spec-creator` | Topic → `labs/<topic>/spec.md` + `baseline.yaml` |
| **3. Build** | `lab-builder` | Spec → workbook, configs, topology, fault-injection scripts |

Each phase has a review gate — outputs are inspected before the next phase begins.
See [`.agent/skills/README.md`](.agent/skills/) for the full skill catalogue and design.

## Suggested Practice Order

<!-- practice-order-start -->
1. **ospf** — multiarea OSPFv2/v3, summarization, LSA behavior
2. **isis** — multilevel IS-IS, dual-stack, L1/L2 boundaries
3. **bgp** — scalability, communities, FlowSpec, dampening
3a. **bgp-dual-ce** — dual-CE multihoming: transit prevention, inbound TE, selective advertisement · *supplements bgp*
4. **routing-policy** — RPL vs route-maps, traffic steering · *needs ospf, isis, bgp*
5. **ipv6-transition** — 6PE, static tunnels, NAT64, MAP-T · *needs bgp*
6. **fast-convergence** — BFD, NSF, NSR, LFA/IP-FRR, BGP PIC · *needs ospf, isis, bgp*
7. **mpls** — LDP, LSP, RSVP-TE, BGP-free core · *needs ospf, isis, bgp*
8. **multicast** — PIM-SM, MBGP, MSDP, MLDP · *needs bgp, mpls*
9. **segment-routing** — SR-TE, TI-LFA, PCE, Tree SID · *needs mpls, routing-policy*
10. **srv6** — SRv6 data-plane, Flex-Algo, interworking · *needs segment-routing*
<!-- practice-order-end -->

> **You can practice topics in any order.** Each lab is self-contained — every lab folder has its own `setup_lab.py`, initial configs, and topology, so prerequisites are baked in and don't depend on having completed earlier labs. The order above is the recommended progression for working through the exam from scratch; if you already know the foundations, jump straight to whichever topic you want to drill.

## Commands

| Command | Phase | Purpose |
|---------|-------|---------|
| `/plan-exam` | 1 | Read blueprint, create `topic-plan.yaml` |
| `/create-spec <topic>` | 2 | Generate `spec.md` + `baseline.yaml` for one topic |
| `/build-lab <topic>/<lab-id>` | 3 | Build a single lab |
| `/build-topic <topic>` | 3 | Build all labs for a topic with review gates |
| `/build-capstone` | 3 | Multi-domain capstone spanning topics |
| `/tag-lab <topic>/<lab-id>` | — | Stamp lab `meta.yaml` with provenance + telemetry (see [`docs/telemetry-and-cost.md`](docs/telemetry-and-cost.md)) |
| `/sync-skills` | — | Pull latest `.agent/skills/` from upstream |
| `/project-status` | — | Regenerate [`STATUS.md`](STATUS.md) |

For the current state of the project (which labs are built, what's next), run `/project-status` or read [`STATUS.md`](STATUS.md).

## Prerequisites

- Python 3.10+ with `pip install -r requirements.txt`
- EVE-NG accessible on your network (see [`.agent/skills/eve-ng/SKILL.md`](.agent/skills/eve-ng/) for image and hardware constraints)
- Cisco IOSv / IOSvL2 / XRv 9000 images loaded in EVE-NG (per topic requirements in `baseline.yaml`)

## Working on This Project

| If you want to… | Read |
|----|----|
| Understand conventions and project context | [`CLAUDE.md`](CLAUDE.md) |
| See live build progress | [`STATUS.md`](STATUS.md) |
| Learn how the skill toolkit works | [`.agent/skills/README.md`](.agent/skills/) |
| Read the exam blueprint | [`blueprint/300-510/blueprint.md`](blueprint/300-510/blueprint.md) |
| Track build cost / compare models | [`docs/telemetry-and-cost.md`](docs/telemetry-and-cost.md) |

---

*This README is generated from `.agent/skills/scaffolding/README_template.md` at project bootstrap. Keep it stable — put live status in [`STATUS.md`](STATUS.md) instead.*
