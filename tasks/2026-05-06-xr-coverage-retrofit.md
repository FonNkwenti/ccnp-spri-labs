# XR Coverage Retrofit — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to walk this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Review gates marked `[REVIEW GATE]` are HARD STOPS — do not proceed past one without explicit user approval.

**Goal:** Bring the project to CCIE SP precursor-grade XR coverage by (1) amending every topic spec with an explicit XR coverage posture, (2) retrofitting IOSv-only capstones to mixed-mode XR/IOSv, (3) adding optional XR appendices to high-value BGP labs, and (4) creating a bonus `xr-bridge` topic for self-study.

**Architecture:**
- **Phase 0** writes a single project-wide XR policy doc that every spec amendment will cite, so language stays consistent.
- **Phases 1–4** apply changes in increasing-risk order: spec text (reversible) → new topic (additive) → capstone retrofits (modifies built work) → optional appendices.
- Every phase ends with a `[REVIEW GATE]` where the user inspects the diff before the next phase starts.
- All built-lab modifications follow the project's existing convention: `spec.md` → `baseline.yaml` → `initial-configs/` → `solutions/` → `workbook.md` → topology drawio → fault-injection scripts.

**Tech stack / tooling:**
- Markdown specs, YAML baselines, IOSv 15.9 / IOS XRv (light, ~3 GB) / IOS-XRv 9000 7.1.1 / CSR1000v 17.3 configs.
- **Platform-selection rule (project-wide, user-confirmed 2026-05-06):** prefer plain **IOS XRv** for any node that doesn't strictly require XRv9000. Reserve XRv9000 only for SR/SRv6/EVPN/FlowSpec or anywhere XRv lacks the feature. The xr-bridge topic always includes one XRv9000 node so students see the heavier image regardless.
- Existing slash commands: `/build-capstone`, `/diagram`, `/inject-faults`, `/tag-lab`, `/project-status`.
- Existing skills: `eve-ng` (RAM/platform constraints), `drawio` (topology art), `fault-injector` (Netmiko scripts), `lab-builder`.
- Hardware ceiling: Dell Latitude 5540, ~64 GB RAM. XRv9k = 12–16 GB/node. No phase may push a single lab over ~32 GB peak.

**Verification posture (no code tests):**
This is a docs + configs project. "Verify" steps mean: (a) lab boots in EVE-NG, (b) `show` outputs match expected state, (c) blueprint coverage matrix in spec lists the bullet, (d) git diff is clean.

---

## Phase 0 — XR Coverage Policy Doc

Single source of truth that every spec amendment will cite. Doing this first prevents inconsistent wording across 11 specs.

### Task 0.1: Write the XR coverage policy

**Files:**
- Create: `memory/xr-coverage-policy.md`

- [ ] **Step 1: Draft the policy doc**

Content must include:
1. **Policy statement** — the project targets two audiences (300-510 exam, CCIE SP precursor) and how each topic resolves the trade-off.
2. **Per-topic posture table** — every topic gets one of: `XR-native` (XR is the only platform), `XR-mixed` (XR + IOSv coexist), `IOSv-only with XR appendix` (IOSv labs + XR snippets in workbook), `IOSv-only` (no XR exposure), `Bridge` (the new xr-bridge topic).
3. **RAM budget table** — peak RAM per topic for any lab in that topic, with margin against the 64 GB host.
4. **Wording template** — exact paragraph each topic spec will paste into its *Design Decisions* section under a new "XR Coverage Posture" heading.

- [ ] **Step 2: Verify against current state**

Run: `Grep` for `platform:` across `labs/*/baseline.yaml` and confirm the policy table matches reality (don't claim a topic is XR-mixed if it isn't yet).

- [ ] **Step 3: Commit**

```bash
git add memory/xr-coverage-policy.md
git commit -m "docs(xr): add project-wide XR coverage policy"
```

### Task 0.2: Update STATUS.md and tasks/todo.md to track this retrofit

**Files:**
- Modify: `tasks/todo.md` — add a "Current Session" entry pointing at this plan.
- Modify: `STATUS.md` — add an "XR Coverage Retrofit" section listing the phases.

- [ ] **Step 1: Edit `tasks/todo.md`** to reference `tasks/2026-05-06-xr-coverage-retrofit.md` as the active plan.
- [ ] **Step 2: Edit `STATUS.md`** to list the 5 phases as a checklist (no detail — just headlines).
- [ ] **Step 3: Commit**

```bash
git add tasks/todo.md STATUS.md
git commit -m "chore(status): track XR coverage retrofit plan"
```

### `[REVIEW GATE 0]` — Policy approved before any spec touches

**STOP.** Show the user `memory/xr-coverage-policy.md`. Confirm:
- Does the per-topic posture table match their intent?
- Is the wording template acceptable for paste-in?
- Any topics they want to flip (e.g., promote `multicast` from IOSv-only to IOSv-only-with-XR-appendix)?

Do not start Phase 1 without explicit "approved, proceed" from the user.

---

## Phase 1 — Spec Amendments (11 topics)

For each topic spec, add the "XR Coverage Posture" subsection (paste from policy doc, fill in the posture for that topic) and add an "XR" column to the Blueprint Coverage Matrix.

**Order** (locked by dependency: foundation specs first so the wording lands cleanly, then advanced):
1. ospf
2. isis
3. bgp
4. bgp-dual-ce
5. routing-policy
6. mpls
7. fast-convergence
8. multicast
9. ipv6-transition
10. segment-routing
11. srv6

**Pattern repeated for every spec — Tasks 1.1 through 1.11.**

### Task 1.N: Amend `labs/<topic>/spec.md`

**Files:**
- Modify: `labs/<topic>/spec.md`

- [ ] **Step 1: Read the current spec end-to-end**

Confirm posture from policy doc. If the spec is already partially XR-mixed (routing-policy, segment-routing, srv6), the amendment is just formalizing what's there.

- [ ] **Step 2: Add the "XR Coverage Posture" subsection**

Paste the wording template from `memory/xr-coverage-policy.md`. Fill in:
- Posture name (`XR-native` / `XR-mixed` / `IOSv-only with XR appendix` / `IOSv-only`).
- One-sentence rationale specific to this topic.
- Cross-reference to the capstone retrofit task (Phase 3) if applicable.

Insert the subsection at the top of the *Design Decisions* section.

- [ ] **Step 3: Extend the Blueprint Coverage Matrix**

Add a new rightmost column "XR Exercised?" with values:
- `yes — primary` (XR is the platform that demonstrates this bullet).
- `yes — capstone` (XR shows up only in the capstone retrofit).
- `appendix` (XR CLI shown in workbook appendix only).
- `no` (out of scope for this topic, refer to xr-bridge).

- [ ] **Step 4: Verify wording matches policy doc**

Run: `Grep -n "XR Coverage Posture" labs/<topic>/spec.md` — should return exactly one hit.
Run: visual diff against `memory/xr-coverage-policy.md` template — wording must be identical except for posture/rationale fields.

- [ ] **Step 5: Commit (one commit per spec)**

```bash
git add labs/<topic>/spec.md
git commit -m "docs(<topic>): add XR coverage posture to spec"
```

### `[REVIEW GATE 1A]` — After ospf, isis, bgp, bgp-dual-ce (Tasks 1.1–1.4)

**STOP.** Show diffs for the four foundation specs. Confirm wording template is working in practice. Adjust template in `memory/xr-coverage-policy.md` if needed; if the template changes, re-apply to the four already-amended specs before proceeding.

### `[REVIEW GATE 1B]` — After all 11 specs (Tasks 1.5–1.11)

**STOP.** Run `/project-status` to confirm STATUS.md reflects Phase 1 complete. Show the user a single rollup: "11 specs amended, posture table, RAM totals." Approve before Phase 2.

---

## Phase 2 — XR Bridge Topic (Bonus, Option C)

Create a new self-study topic that re-implements OSPF, IS-IS, BGP, MPLS, multicast on pure XR. Not gated by any other phase — could run in parallel, but listed here so the spec wording in Phase 1 can reference `xr-bridge` consistently.

### Task 2.1: Create `labs/xr-bridge/` skeleton

**Files:**
- Create: `labs/xr-bridge/spec.md`
- Create: `labs/xr-bridge/baseline.yaml`
- Create: `labs/xr-bridge/lab-00-xr-igp-foundations/` (empty folder, will be built later)
- Create: `labs/xr-bridge/lab-01-xr-bgp-and-policy/` (empty folder)
- Create: `labs/xr-bridge/lab-02-xr-mpls-stack/` (empty folder)
- Create: `labs/xr-bridge/lab-03-xr-multicast/` (empty folder)
- Create: `labs/xr-bridge/lab-04-xr-fast-convergence/` (empty folder)
- Create: `labs/xr-bridge/lab-05-xr-capstone/` (empty folder)
- Modify: `memory/progress.md` — add xr-bridge as topic 12 with status "spec only, build deferred".

- [ ] **Step 1: Write `spec.md`** following the same structure as existing topic specs:
  - Exam Reference: list 300-510 bullets covered by re-treatment + a "CCIE SP precursor" note.
  - Topology Summary: 4-node XRv9k core + 1 IOSv "translation reference" router that runs identical config in IOS dialect for side-by-side comparison.
  - Lab Progression: 6 labs as listed above.
  - Blueprint Coverage Matrix: every row marked `appendix-style — re-treatment, not primary`.
  - Design Decisions: XR Coverage Posture = `Bridge`. Explicit note that this topic is **optional self-study**, not part of the 300-510 build sequence.
  - RAM budget: 4 × 3 GB XRv + 1 × 16 GB XRv9000 + 1 × 0.5 GB IOSv ≈ 28.5 GB peak — comfortably within the 64 GB ceiling.

- [ ] **Step 2: Write `baseline.yaml`** with 4 IOS XRv nodes (R1–R4) + 1 XRv9000 node (R5, "advanced features showcase") + 1 IOSv (REF, translation reference). Link plan mirrors fast-convergence diamond so students can A/B compare. RAM: 4×3 + 1×16 + 1×0.5 ≈ 28.5 GB peak — fits the 64 GB ceiling with comfortable margin. Note in the spec that **every xr-bridge lab includes the XRv9000 node** (per user instruction) so students always see at least one node of the heavier image, even when the lab's feature could run on plain XRv.

- [ ] **Step 3: Create empty lab folders** (just the directory + a `.gitkeep`-equivalent placeholder `README.md` saying "spec-only, build deferred").

- [ ] **Step 4: Add to `memory/progress.md`** as topic 12 with status `spec-only`.

- [ ] **Step 5: Verify topology with eve-ng skill**

Use the `eve-ng` skill to confirm RAM math, interface counts, and platform compatibility. The skill will reject impossible configs.

- [ ] **Step 6: Commit**

```bash
git add labs/xr-bridge/ memory/progress.md
git commit -m "feat(xr-bridge): scaffold optional XR self-study topic"
```

### `[REVIEW GATE 2]` — XR bridge spec approved

**STOP.** Show the user `labs/xr-bridge/spec.md`. Specifically confirm:
- 6-lab arc is the right shape, not too long, not too short.
- 28.5 GB RAM peak fits the host comfortably — no workaround needed.
- Inclusion of one XRv9000 node in every lab (per user instruction) is reflected in spec topology and lab progression.
- "Build deferred" status is fine — the user originally said "as a bonus for individual exploration", so spec-only matches that intent.

Do not start Phase 3 without approval.

---

## Phase 3 — Mixed-Platform Capstone Retrofits (Option B)

This is the only phase that **modifies already-built work**. Per the user's CLAUDE.md, every retrofit needs explicit ask-before-modify approval. Each retrofit is its own task with its own review gate.

**Order** (user-specified, 2026-05-06; bgp-dual-ce added 2026-05-06 amendment):
1. mpls / lab-04-capstone-config + lab-05-capstone-troubleshooting
2. fast-convergence / capstone(s)
3. isis / lab-04-capstone-troubleshooting
4. ospf / capstone(s)
5. bgp / lab-07-capstone-config + lab-08-capstone-troubleshooting
6. bgp-dual-ce / capstone(s)
7. multicast / capstone(s)

**Platform rule (user-specified, 2026-05-06):** Use **IOS XRv** (~3 GB image, no SR/SRv6/EVPN) for the 2 flipped nodes in every Phase 3 capstone. Reserve **XRv9000** only for capstones whose blueprint bullets demand advanced features the XRv image lacks — currently none in this list, so all six capstones get plain XRv. RAM math per capstone: 2×IOSv (1 GB) + 2×XRv (6 GB) + remaining IOSv ≈ ~10 GB peak, well under ceiling.

Per-capstone procedure is identical. Documented once below; instantiated per topic.

### Task 3.N: Retrofit `<topic>` capstone(s) to mixed XR/IOSv

**Files (per capstone):**
- Modify: `labs/<topic>/spec.md` — update Capstone topology section to reflect new XR nodes.
- Modify: `labs/<topic>/baseline.yaml` — flip 2 of the existing nodes to `xrv9k`, adjust RAM and interface mappings.
- Modify: `labs/<topic>/lab-NN-capstone-*/initial-configs/<XRn>.cfg` — replace IOSv config with XRv9k equivalent.
- Modify: `labs/<topic>/lab-NN-capstone-*/solutions/<XRn>.cfg` — XR-dialect solution.
- Modify: `labs/<topic>/lab-NN-capstone-*/workbook.md` — add an "XR Tasks" section (1–2 tasks specifically requiring XR CLI), update verification commands to show both `show` (IOS) and `show` (XR) outputs.
- Modify: `labs/<topic>/lab-NN-capstone-*/topology/topology.drawio` — re-render with XR nodes.
- Modify (TS capstone only): `labs/<topic>/lab-NN-capstone-troubleshooting/scripts/fault-injection/inject_scenario_*.py` — Netmiko XR fault injection for replaced nodes.
- Modify: `labs/<topic>/lab-NN-capstone-*/meta.yaml` — bump `last_modified`, add `xr_retrofit: 2026-05-NN`.

- [ ] **Step 1: Verify the capstone is currently built and tagged**

Run: `Bash` → `cat labs/<topic>/lab-NN-capstone-*/meta.yaml`. If `built: true` is missing, **STOP** — do not retrofit an unbuilt capstone; flag to user.

- [ ] **Step 2: Identify which 2 nodes flip to XR**

Choose the two nodes whose role most benefits from XR exposure (typically the PE pair, or one P + one PE). Document choice in `labs/<topic>/lab-NN-capstone-*/decisions.md`.

- [ ] **Step 3: Update `baseline.yaml`**

Change `platform: iosv` → `platform: xrv9k` for the two chosen nodes. Update RAM in the YAML if represented. Re-verify with `eve-ng` skill.

- [ ] **Step 4: Translate initial-configs and solutions**

For each flipped node:
- Read the IOSv config.
- Translate to XRv9k 7.1.1 dialect (interface naming, `router bgp` hierarchy with address-families, `router isis` hierarchy, RPL for any route-maps).
- Save to `initial-configs/<XRn>.cfg` and `solutions/<XRn>.cfg`.
- Diff against the original IOS config to make sure no functionality is dropped.

- [ ] **Step 5: Update workbook**

Add a new section "Capstone Tasks — XR Nodes" with at least 2 tasks that specifically require XR CLI (e.g., "configure RPL `prefix-set` on XR1 to filter customer prefixes" — IOSv cannot do this).

- [ ] **Step 6: Regenerate topology diagram**

Use the `drawio` skill: `/diagram <topic>/lab-NN-capstone-*`. Confirm the new diagram shows XR vs IOSv with distinct icons.

- [ ] **Step 7: Regenerate fault-injection scripts (TS capstone only)**

Use the `fault-injector` skill / `/inject-faults <topic>/lab-NN-capstone-troubleshooting`. The skill must produce Netmiko scripts that handle both `cisco_xr` and `cisco_ios` device types in the same script.

- [ ] **Step 8: Boot the capstone in EVE-NG and verify end-to-end**

Run: `python labs/<topic>/lab-NN-capstone-*/setup_lab.py --host <eve-ng-ip>` then walk through the workbook tasks manually. Capture `show` output proving every task passes on the new mixed topology.

- [ ] **Step 9: Re-tag**

Run: `/tag-lab <topic>/lab-NN-capstone-* gemini xr-retrofit` (or whichever agent did the retrofit). Confirm `meta.yaml` updated.

- [ ] **Step 10: Commit (one commit per capstone)**

```bash
git add labs/<topic>/
git commit -m "feat(<topic>): retrofit capstone to mixed XR/IOSv"
```

### `[REVIEW GATE 3.N]` — After every single capstone retrofit

**STOP after each capstone**, not after each topic. Show:
- The diff summary (`git show --stat HEAD`).
- The boot screenshot or success log.
- The new workbook XR Tasks section.

The user must approve each retrofit before the next begins. Per CLAUDE.md: "Always Ask Before — Modifying a config/baseline file that already has work built from it."

---

## Phase 4 — BGP Scale XR Appendices (Option A, scoped)

Lowest-risk, highest-CCIE-value targeted appendices. Only three labs, all in the `bgp` topic.

**Targets:**
- `labs/bgp/lab-01-route-reflectors` — IOS XRv RR config appendix.
- `labs/bgp/lab-05-communities-flowspec` — XRv9000 FlowSpec (`address-family ipv4 flowspec`) appendix (XRv lacks FlowSpec).
- `labs/bgp/lab-06-confederations` — IOS XRv confederation config appendix.

### Task 4.N: Add XR appendix to `<bgp lab>`

**Files (per lab):**
- Modify: `labs/bgp/<lab>/workbook.md` — append a new section "Appendix: Same Tasks on IOS-XR".
- Create: `labs/bgp/<lab>/solutions-xr/<RouterX>.cfg` — XR-dialect solution for the RR/FlowSpec/confed router only (not full topology).

- [ ] **Step 1: Read the current workbook**, identify the core teaching task (the RR config, the FlowSpec policy, the confederation peering).

- [ ] **Step 2: Write the XR appendix section** in `workbook.md`. Structure:
  - "What changes on XR" — 2–3 sentences on the dialect difference.
  - Side-by-side CLI table: IOSv left, XR right.
  - "Verification on XR" — equivalent `show bgp ...` commands with expected output.

- [ ] **Step 3: Write `solutions-xr/<RouterX>.cfg`** containing the XR config for the *one* router that demonstrates the feature. No full-topology XR rebuild.

- [ ] **Step 4: Update `meta.yaml`** — add `xr_appendix: true`.

- [ ] **Step 5: Commit (one commit per lab)**

```bash
git add labs/bgp/<lab>/
git commit -m "docs(bgp/<lab>): add XR CLI appendix"
```

### `[REVIEW GATE 4]` — After all three appendices

**STOP.** Show the three workbook diffs. Approve before Phase 5.

---

## Phase 5 — Integration & Final Sweep

### Task 5.1: Cross-check spec ↔ policy ↔ matrix consistency

**Files:** read-only sweep, no edits expected.

- [ ] **Step 1: Run** `Grep` for "XR Coverage Posture" across all `labs/*/spec.md` — must return 11 hits.
- [ ] **Step 2: Run** `Grep` for "XR Exercised?" — must return 11 hits in spec matrices.
- [ ] **Step 3: Compare each spec's posture line against `memory/xr-coverage-policy.md`** — postures must agree.
- [ ] **Step 4: If any mismatch, file as a follow-up task** (do not silently fix; surface to user).

### Task 5.2: Refresh STATUS.md and run /project-status

- [ ] **Step 1:** Run `/project-status` — confirm output reflects all retrofits.
- [ ] **Step 2:** Edit `STATUS.md` — mark XR Coverage Retrofit phases complete.
- [ ] **Step 3:** Edit `tasks/todo.md` — clear the "Current Session" entry, move the plan filename into a "Completed Plans" section if you keep one.

- [ ] **Step 4: Final commit**

```bash
git add STATUS.md tasks/todo.md
git commit -m "chore(status): close out XR coverage retrofit"
```

### `[REVIEW GATE 5]` — Done

**STOP.** Final summary to user:
- 11 specs amended.
- 1 new bridge topic scaffolded (build deferred).
- N capstones retrofitted to mixed XR/IOSv.
- 3 BGP labs got XR appendices.
- One commit per artifact, total commit count: ~24–28.

Ask whether to push to remote (per CLAUDE.md "Always Ask Before — Running git push").

---

## Self-Review Notes

- **Spec coverage:** Every blueprint section in `blueprint/300-510/blueprint.md` has at least one task touching its topic. ✓
- **Placeholder scan:** No "TBD", no "similar to Task N", no "implement appropriate X". The per-task instantiation pattern in Phase 1, Phase 3, Phase 4 is parameterized by topic name only — every instance is mechanically identical, no judgment calls hidden behind placeholders.
- **Type/name consistency:** Posture names (`XR-native`, `XR-mixed`, `IOSv-only with XR appendix`, `IOSv-only`, `Bridge`) are introduced in Task 0.1 and used identically through Phases 1, 2, 5. ✓
- **Risk ordering:** Phase 1 (text only, fully reversible) → Phase 2 (additive, doesn't touch built work) → Phase 3 (modifies built work, gated per-capstone) → Phase 4 (appendix-only, additive) → Phase 5 (integration). ✓
- **Review gates:** 0, 1A, 1B, 2, 3.N (×6), 4, 5 = 12 gates. User explicitly asked for review gates so the long exercise can be implemented smoothly.
- **CLAUDE.md compliance:** "Plan First" ✓; "Always Ask Before modifying built work" ✓ (gate per capstone); "Verify before done" ✓ (Phase 5 cross-check); "ASCII diagrams use box-drawing" — none in this plan, but Phase 2 spec topology will follow the rule.
