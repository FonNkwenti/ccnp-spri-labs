# XR Rebuild Plan — Session Handoff

> **Created:** 2026-05-06
> **Status:** Ready to resume in a fresh Claude Code session
> **Scope:** Rebuild seven labs cleanly under `-xr` suffix variants, preserving the original IOSv-only builds untouched. Drives the XR Coverage Retrofit to a template-compliant end state.

---

## Why this plan exists

A first attempt to **retrofit** XR into the existing capstones (Phase 3 of `tasks/2026-05-06-xr-coverage-retrofit.md`) was committed (`15ea6c7`) and then reverted (`43d1382`) because appending a Platform Mix Notice + Appendix B broke the standardized 11-section workbook template enforced by `lab-assembler/SKILL.md` Step 3.

The cleaner approach: rebuild each affected lab via `/build-lab` so the workbook is template-compliant from the start, with XR posture inherited from the **already-amended** topic specs (commits `4d8caf4`..`47a11b6`).

**Suffix convention:** `-xr` is treated as a build-tag variant (parallel to `-haiku`, `-medium`, etc. already in `/build-lab`'s strip list). Baseline lookup strips `-xr`; output writes to `labs/<topic>/lab-NN-<slug>-xr/`. The original folder is untouched.

---

## Pre-flight checklist (before opening the next session)

- [ ] Confirm git tree is clean of XR retrofit residue: `git log --oneline -5` should show `43d1382` (the revert) on top
- [ ] Confirm spec amendments are in place: `git log --oneline --grep="XR coverage posture"` should list 11 commits
- [ ] Confirm `xr-bridge` scaffold exists: `ls labs/xr-bridge/`
- [ ] Confirm `memory/xr-coverage-policy.md` exists and is committed
- [ ] EVE-NG running on the Dell Latitude 5540 (RAM headroom matters — XR images are ~3 GB each)

---

## Build queue (in this order)

Each lab is one `/build-lab` invocation in a **fresh Claude Code session**. Restart between major capstones to keep context clean — the assembler's workbook gate alone produces a lot of tool-call churn.

### Capstone retrofits (XR-mixed posture)

Each writes to `labs/<topic>/lab-NN-<slug>-xr/`. Original folder stays as-is.

| # | Command | Posture | XR routers | Status |
|---|---------|---------|------------|:------:|
| 1 | `/build-lab bgp/lab-07-capstone-config-xr` | XR-mixed | R3 (multihome PE), R4 (Route Reflector) | ☐ |
| 2 | `/build-lab bgp/lab-08-capstone-troubleshooting-xr` | XR-mixed | R3, R4 (same as lab-07) | ☐ |
| 3 | `/build-lab ospf/lab-04-capstone-config-xr` | XR-mixed | R2 (ABR), R3 (triple ABR + ASBR) | ☐ |
| 4 | `/build-lab ospf/lab-05-capstone-troubleshooting-xr` | XR-mixed | R2, R3 (same as lab-04) | ☐ |
| 5 | `/build-lab mpls/lab-04-capstone-config-xr` | XR-mixed | PE1, PE2 (RSVP-TE head/tail) | ☐ |
| 6 | `/build-lab mpls/lab-04-capstone-config-dsc-xr` | XR-mixed | PE1, PE2 | ☐ |
| 7 | `/build-lab bgp-dual-ce/lab-04-capstone-config-xr` | XR-mixed | R1 (CE1), R2 (CE2) | ☐ |

### Foundation lab XR appendices (IOSv-only with XR appendix)

These do **not** rebuild the workbook — they add a new `solutions-xr/<router>.cfg` reference file and a single optional appendix section the assembler should produce naturally because the spec posture says "IOSv-only with XR appendix". If `/build-lab` rebuilds the whole lab, that's also acceptable — the existing IOSv content will be regenerated identically because the spec content didn't change apart from the XR posture line.

Decision deferred: **revisit after the capstones are done.** May not need rebuilds — could instead hand-author just the `solutions-xr/` files using the assembler's standard XR config format as reference, without touching the workbooks.

| # | Lab | Likely action |
|---|-----|---------------|
| 8 | `bgp/lab-01-route-reflectors` | hand-author `solutions-xr/R4.cfg` (RR) |
| 9 | `bgp/lab-05-communities-flowspec` | hand-author `solutions-xr/R5.cfg` (community-set + FlowSpec) |
| 10 | `bgp/lab-06-confederations` | hand-author `solutions-xr/R3.cfg` (confed sub-AS member) |

---

## Per-build expectations

### Inputs the assembler needs to find
- `labs/<topic>/baseline.yaml` — already present; lab entries have `difficulty: Advanced` (gate enforces opus-4.7)
- `labs/<topic>/spec.md` — already amended with XR Coverage Posture section
- For progressive labs: previous lab's `solutions/` (NOT applicable to capstones — they all use `clean_slate: true`)

### Outputs (per build)
```
labs/<topic>/lab-NN-<slug>-xr/
├── README.md
├── decisions.md          # model gate + workbook gate outcomes
├── meta.yaml             # auto-generated
├── setup_lab.py
├── workbook.md           # 11 sections, contract-gate validated
├── initial-configs/      # 1 .cfg per active device (clean_slate)
├── solutions/            # 1 .cfg per active device
├── topology/
│   ├── topology.drawio   # subagent-generated
│   └── README.md
└── scripts/fault-injection/
    ├── inject_scenario_01.py
    ├── inject_scenario_02.py
    ├── inject_scenario_03.py
    ├── apply_solution.py
    └── README.md
```

### Gates the assembler will run
1. **Model gate (preflight, BLOCKING):** Advanced tier → only `claude-opus-4-7` allowed. Pass `--force-model` to override.
2. **Workbook contract gate (post-Step 3, BLOCKING):** 11-section structure, format rules for sections 3/4/5/6/7/8/9, no raw IOS in task bodies, no fault-revealing ticket headings. Failures auto-fix and re-validate.

### Special handling for `-xr` variant builds
The assembler's `meta.yaml` writes `lab: <folder-name>` — that becomes `lab-07-capstone-config-xr` for the variant. Update `decisions.md` to note:

```markdown
## Variant note
This is the `-xr` build-tag variant of `lab-07-capstone-config`. Baseline
lookup stripped the `-xr` suffix and read objectives/devices/blueprint refs
from the canonical `lab-07-capstone-config` entry in baseline.yaml. The
XR-mixed platform posture is honored from `labs/bgp/spec.md` (XR Coverage
Posture section, commit 4d8caf4).
```

`memory/progress.md` should add a **new row** under the topic's table for the `-xr` variant — do not replace the original. Suggested format:

```markdown
| lab-07-capstone-config | BGP Full Protocol Mastery — Capstone I | Built ✓ |
| lab-07-capstone-config-xr | BGP Full Protocol Mastery — Capstone I (XR-mixed variant) | Review Needed |
```

---

## Resume protocol

When you start a fresh session to continue this plan:

1. Open this file (`tasks/2026-05-06-xr-rebuild-plan.md`) and find the next unchecked row in the build queue.
2. Run that row's `/build-lab` command.
3. After the lab completes the workbook gate cleanly, **check the box** in this file and commit:
   ```
   git add tasks/2026-05-06-xr-rebuild-plan.md labs/<topic>/lab-NN-<slug>-xr/ memory/progress.md
   git commit -m "feat(<topic>): build lab-NN-<slug>-xr (XR-mixed variant)"
   ```
4. **Do not chain** multiple builds in one session. Each lab is its own session — capstones are large enough that context fills before completion.

---

## Boot verification (after each build)

The assembler stamps every retrofit-equivalent config as **syntactically translated** — it does not boot the lab. After each `-xr` build:

1. Import the lab into EVE-NG (start with `bgp/lab-07-capstone-config-xr`).
2. Boot all 7 routers; confirm IOSv-side comes up (R1, R2, R5, R6, R7) and XR-side reaches the `commit` prompt (R3, R4).
3. Run `setup_lab.py --host <eve-ng-ip>`; confirm initial-configs push without errors.
4. Walk the workbook tasks; report any XR command that parses differently than the workbook says.
5. Update `memory/progress.md`: variant row → `Built ✓` once verification passes.

---

## Out-of-scope for this plan

- `bgp/lab-08` inject-script XR translation (`scripts/fault-injection/inject_scenario_*.py` for R3/R4 tickets) — this is a separate task, tracked as a follow-up after lab-08-xr boots cleanly.
- The `xr-bridge/` bonus topic build — deferred per `memory/xr-coverage-policy.md` §2.
- Any lab currently marked "Not Started" in `memory/progress.md` — those will inherit XR posture naturally when they're built fresh; no retrofit pass is needed.

---

## Cross-references

- Original retrofit plan (now superseded): [`tasks/2026-05-06-xr-coverage-retrofit.md`](2026-05-06-xr-coverage-retrofit.md)
- XR coverage policy (postures + RAM ceiling): [`memory/xr-coverage-policy.md`](../memory/xr-coverage-policy.md)
- Spec amendment commits: `git log --oneline --grep="XR coverage posture"`
- Reverted retrofit attempt: `git show 15ea6c7` (the build) / `git show 43d1382` (the revert)
- Live status: [`STATUS.md`](../STATUS.md) — phase table reflects this plan's progress
