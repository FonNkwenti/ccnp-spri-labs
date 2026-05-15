# Lessons Learned — CCNP SPRI (300-510)

Exam-specific corrections, gotchas, and rules discovered during lab generation.
New entries at the top. Review at the start of each session.

---

<!-- Template for new entries:

## YYYY-MM-DD — Brief title

**Correction:** What went wrong or what was misunderstood.

**Rule:** The correct behaviour going forward.

**Why:** The reasoning — what failure mode does this prevent?

**Touched:** Files modified to apply the fix.

-->

## 2026-05-15 — Affinity-constrained SR-TE paths use adjacency-SIDs, not prefix-SIDs

**Correction:** Workbook Task 4 expected `SID[0]: 16003` (prefix-SID). Actual output shows
`SID[0]: 24000 [Adjacency-SID]`. User mistook it for an LDP label.

**Rule:** When a CSPF constraint forces a path that diverges from the IGP shortest path, CSPF
uses adjacency-SIDs — not prefix-SIDs. A prefix-SID routes via IGP shortest path, which
would defeat the constraint. Verify Task 4 by checking metric (30 = L5) and absence of 16004
(R4), not by checking whether the SID is a prefix-SID.

**Why:** Adjacency-SIDs pin traffic to a specific physical link. Prefix-SIDs defer to IGP
routing, which does not respect SR-TE affinity constraints.

**Touched:** `lab-03-sr-te-3node/workbook.md` Task 4 verification, Section 6 Task 4 output,
`.agent/skills/LESSONS_LEARNED.md`.

---

## 2026-05-15 — SR-TE initial-configs must include `distribute link-state` in IS-IS

**Correction:** SR-TE policies showed `Operational: down` with `Source node not found in topology`
because `distribute link-state` was missing from IS-IS config in lab-03 initial-configs.

**Rule:** Every XR node in an SR-TE lab must have `distribute link-state` under
`router isis <PROCESS> address-family ipv4 unicast`. Add this alongside `segment-routing mpls`
in every initial-config generation pass. Without it the SR-TE CSPF topology stays empty.

**Why:** IOS-XR's SR-TE CSPF topology database is populated separately from the RSVP-TE
topology. `show mpls traffic-eng topology` being full does NOT mean SR-TE CSPF is working.

**Touched:** `lab-03-sr-te-3node/initial-configs/R{1,3,4}.cfg`,
`lab-03-sr-te-policies-and-steering/initial-configs/R{1,2,3,4}.cfg`,
`.agent/skills/LESSONS_LEARNED.md`.

---

## 2026-05-15 — IOS-XR 24.x SR-TE CSPF optimizes label stack: do not expect `[16004, 16003]` for dynamic IGP policies

**Correction:** Workbook verification expected `SID[0]: 16004, SID[1]: 16003` for a dynamic IGP
SR-TE policy. Actual output on XRv 9000 24.3.1 shows only `SID[0]: 16003`.

**Rule:** When verifying dynamic SR-TE policies, check `Path Accumulated Metric` to confirm the
correct path — NOT the number of SIDs in the stack. IOS-XR drops intermediate node SIDs when
the CSPF path matches the IGP shortest path. Only explicit segment-lists (Tasks 3, 7) will
reliably show multi-SID stacks.

**Why:** IOS-XR CSPF optimization: a single destination prefix-SID is sufficient when the
IGP already routes along the intended path.

**Touched:** `lab-03-sr-te-3node/workbook.md` Task 2 verification section.

---

## 2026-05-14 — lab-04-pce-srlg-tree-sid exceeds 64 GB laptop capacity; no viable variant exists

**Correction:** Asked whether classic XRv or fewer nodes could allow lab-04 to run on
the 64 GB Dell Latitude 5540.

**Rule:** Lab-04 (PCE, SRLG, Tree SID) is a **hard hardware boundary** for this laptop.
No substitution or reduction produces a runnable lab:

1. **Classic XRv cannot substitute for the PCE.** `xrv-k9-demo-6.3.1` fails on all three
   PCE functions: BGP-LS table caps corrupt the topology database; SRLG-aware CSPF requires
   post-6.3.1 features; Tree SID P2MP computation is not present in 6.3.1.

2. **4 XRv9k is the technology minimum** (PCE + R1 + R3 + R4). Removing R4 leaves only
   one path R1→R3, making SRLG path diversity impossible and Tree SID degenerate. 4 nodes
   = 64 GB — fills the entire physical host with nothing left for EVE-NG OS or hypervisor.

3. **No variant should be created for lab-04.** There is no topology reduction that
   satisfies 4.3.c + 4.3.d + 4.3.e simultaneously within 48 GB. Mark it as a hardware
   boundary in spec.md and treat it as study-only on this machine.

**Why:** Tree SID (4.3.e) forces all PCCs (root + leaves) to be IOS-XR. This rules out
CSR1000v. Combined with the PCE requiring full PCEP/BGP-LS feature set, the minimum
platform is 4× XRv9k, which this laptop cannot host.

**Touched:** `labs/segment-routing/spec.md` — hardware boundary warning added to lab-04
row in the progression table; `tasks/lessons.md`.

---

## 2026-05-14 — Classic XRv (xrv 6.3.1 demo) cannot substitute XRv 9000 in SR-TE labs

**Correction:** Asked whether `xrv-k9-demo-6.3.1` could replace XRv 9000 nodes in
`segment-routing/lab-03-sr-te-policies-and-steering` (partially or completely).

**Rule:** Classic XRv (`xrv`, demo image 6.3.1) must **never** be used in any SR-TE lab.
Two hard blockers:

1. **ODN not supported at 6.3.1.** `on-demand color` (On-Demand Next-Hop) was introduced in
   IOS-XR 6.3.2. Version 6.3.1 does not have the CLI. Task 6 (color-based automated steering)
   is a core exam objective — it cannot be skipped.
2. **Demo image limitations.** The installed image is a demo/limited build with routing-table
   caps that can silently drop IS-IS TE TLVs once the table fills, making affinity constraint
   behavior unpredictable and Ticket 2 unreproducible.

All SP core nodes (R1–R4) in segment-routing labs must use `xrv9k` (IOS-XRv 9000, 24.3.1).
CE devices remain IOSv as specified. This applies to all future SR-TE labs in this topic.

**Why:** RAM is not a constraint — four XRv 9000 nodes at 4 GB each = 16 GB, well within the
48 GB EVE-NG VM allocation on the 64 GB host. There is no resource justification to accept a
demo-limited image that breaks a core exam objective.

**Touched:** `tasks/lessons.md`

---

## 2026-05-12 — IOSv 15.9(3)M6: IS-IS GR, IS-IS NSR, and BGP NSR commands absent; BFD fall-over bypasses GR test

**Correction:** fast-convergence/lab-01 was built assuming `nsf ietf`, `nsr` (under
`router isis`), and `bgp nsr` (under `router bgp`) would be accepted on IOSv 15.9(3)M6
with a "config-only, no functional effect" disclaimer. Live testing showed all three
commands are **rejected outright** ("Unrecognized command") — they are not compiled into
the IOSv image. `bgp graceful-restart` is the only GR/NSR command that passes on IOSv.

A second finding: testing BGP GR (Task 3 Part B) with `clear ip bgp *` on R5 when R1/R3
have `fall-over bfd multi-hop` configured against R5 does NOT exercise GR. `clear ip bgp *`
sends a BFD ADMINDOWN signal to its peer, which triggers `fall-over bfd` on R1 — causing an
immediate non-GR tear-down. R1 never enters GR helper mode. Ping drops are from plain BGP
reconvergence, not GR-protected forwarding.

**Rules:**

1. **IS-IS GR/NSR on IOSv:** Never emit `nsf ietf` or `nsr` under `router isis` in configs
   targeting IOSv. These commands are rejected, not silently ignored. Workbooks must mark
   the affected tasks as conceptual-reference exercises with platform notes. The correct
   syntax is for supported platforms (IOS 15.4+, IOS-XE, IOS-XR, ASR 9000+) only.

2. **BGP NSR on IOSv:** Never emit `bgp nsr` in configs targeting IOSv. Rejected.

3. **BGP GR test methodology — BFD fall-over interaction:** When `fall-over bfd` is
   configured on an eBGP session and you want to test BGP GR, you must temporarily remove
   `fall-over bfd` from that neighbor before issuing `clear ip bgp *`. Alternatively, use a
   hard reload of the restarting router (which does not send BFD ADMINDOWN). Document this
   in the lab workbook and restore `fall-over bfd` after the test.

4. **Capstone awareness:** Any fast-convergence capstone must not pre-load `nsf ietf`, `nsr`,
   or `bgp nsr`. If these features appear in exam objectives, they should be tested as
   paper/analytical tasks only on IOSv. BGP GR tests should include the `no fall-over bfd`
   workaround step.

**Why:** IOSv omits HA commands that require hardware FIB separation (CEF on a separate line
card from the RP). The `fall-over bfd` issue affects any platform using BFD fall-over — it is
not an IOSv-only bug but a test-methodology pitfall. Getting either wrong silently produces a
test that appears to measure GR but actually measures plain reconvergence.

**Touched:**
- `labs/fast-convergence/lab-01-nsf-and-nsr/workbook.md` — Tasks 1, 3A, 5, 6, Tickets 1/3
  converted to conceptual-reference; Task 3B updated with `no fall-over bfd` workaround note;
  completion checklist labelled Live/Conceptual/Paper/Analytical.
- `.agent/skills/reference-data/ios-compatibility.yaml` — four new rows added.
- `.agent/skills/LESSONS_LEARNED.md` — cross-certification entry added.

---

## 2026-05-08 — Cross-cutting features need flags + opt-in, not in-place mutation

**Correction:** The "XR coverage retrofit" applied IOS XR support to existing built
labs by mutating their specs, configs, and workbooks in place. It contaminated two
capstones whose underlying topology had been pure-IOSv (`mpls/lab-04-capstone-config`,
`bgp-dual-ce/lab-04-capstone-config`), created a parallel `-dsc` capstone artifact with
no IOSv ancestor, and interleaved 15 retrofit commits with ~17 unrelated commits so a
clean revert wasn't possible. Two rollback phases were required: Phase 1 cherry-reverted
the 15 retrofit commits; Phase 2 surgically restored configs/workbooks/meta.yaml on the
two capstones whose XR contamination predated the reverts.

**Rule:** When adding a cross-cutting capability (alternate platform, alternate protocol,
optional feature) across an existing lab corpus:
1. **Build-time flag, not in-place mutation.** Implement as `--<feature>-mode` on the
   builder. Default off. Existing labs stay byte-identical unless rebuilt with the flag.
2. **Side-by-side artifacts.** New variant lands as a sibling folder with a suffix
   (`<lab-id>-<variant>`) — never overwrite the original. Tooling and indexes treat the
   suffix as a first-class lab.
3. **Per-lab opt-in.** Each lab decides whether the variant applies (some topologies
   simply can't host the feature). Track opt-in in `baseline.yaml`, not by mass-rebuilding.
4. **Spec extension, not rewrite.** Specs gain an optional appendix for the variant; the
   IOSv body stays unchanged. Avoid "Platform Mix Notice" headers that bake variant text
   into the primary workbook.
5. **One-commit-per-lab.** Each variant build is one commit on top of an unchanged base,
   so rollback is `git revert` of that single commit.

**Why:** In-place retrofits couple unrelated labs to one mega-change, force every commit
to touch many files, and make rollback combinatorially hard. The `-dsc` capstone showed
the worst failure mode: a retrofit can create artifacts that have no clean origin to
revert to. Flag + opt-in keeps the original corpus stable and makes the variant track
independently versionable.

**Touched:**
- Phase 1 rollback: commit `66f3776` (15 cherry-reverts).
- Phase 2 rollback: commit `637793c` (capstone surgical cleanup + `-dsc` deletion).
- Future: design `--xr-mode` for `/build-lab` per this rule before re-attempting XR work.

---

## 2026-05-03 — Verify third-party analysis against primary sources before acting

**Correction:** A Pi-generated audit of the BGP capstone workbook (`lab-07-capstone-config`)
identified 6 "root causes" for non-deterministic lab output. 4 of the 6 claims were factually
wrong when checked against primary source skill files. The most critical mistake was misreading
an enforcement gap (gate didn't exist yet) as a gate that wasn't enforced. The workbook was
built 2026-04-28; the workbook contract gate was added 2026-05-01 — Pi blamed the gate instead
of the build date.

**Rule:** Before acting on any third-party analysis of skill files:
1. **Timestamp first.** Check `meta.yaml created.date` against the commit date of the gate/rule
   being blamed. If the artifact predates the rule, the root cause is absence, not failure.
2. **Read the primary source.** For any claim about what a skill does or doesn't say, grep the
   actual SKILL.md. Don't accept "the skill says X" without verifying the line number.
3. **Distinguish real bugs from historical gaps.** Real bugs: rule exists, artifact violates it.
   Historical gaps: rule didn't exist when the artifact was built. Fixes differ — bugs need
   enforcement fixes; gaps need rebuild decisions.

**Why:** Acting on wrong root causes produces wrong fixes. Adding enforcement for a rule that
already exists wastes a commit; rebuilding a lab that the current gate would pass is unnecessary
churn. The two confirmed bugs (drawio dispatch contradictions) were real and worth fixing. The
four false claims would have led to unnecessary changes to skill files that were already correct.

**Touched:**
- `.agent/skills/lab-assembler/SKILL.md` — Step 5 Pre/Post-Write checklists (drawio dispatch
  contradictions fixed); Step 3b Section 5 gate tightened with explicit FAIL patterns.
- `tasks/pre-gate-labs.txt` — Pre-gate audit output (38 pre-gate labs, 6 FAIL, 32 OK).

---

## 2026-04-30 — Workbook topology ASCII: bordered-box style with rich per-router info

**Correction:** First build of `segment-routing/lab-00-sr-foundations-and-srgb`
shipped a minimal 5-line ASCII topology (just `R1 ──L1── R2`-style edges, no
bordered boxes, no per-router metadata). The user rejected it as "too minimal"
and not matching the project's diagram style.

**Rule:** Every workbook Section 2 topology diagram MUST use **bordered router
boxes with rich metadata inside**. The pattern, established in
`mpls/lab-03-rsvp-te-tunnels` and refined in
`segment-routing/lab-00-sr-foundations-and-srgb`:

1. **Box-drawing chars only** — `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ═ ║`. Never `+--`, `|`,
   or `+`.
2. **Each router box ≥ 5 lines tall** containing:
   - Router name (centered)
   - `Lo0   <loopback>/32`
   - Protocol-specific identifier (NET for IS-IS, RID for OSPF, ASN for BGP)
   - Per-protocol label/SID/community as relevant
   - **Interface list mapping** for any links not drawn visually (the diagonal
     escape hatch — see point 5)
3. **Inter-box links** drawn explicitly:
   - Horizontal links: `═════` between `├` and `┤` connectors, with
     `Gi0/0/0/X ══ Gi0/0/0/Y` interface labels above and `Lₙ — <subnet>` label
     also above
   - Vertical links: `║` chars in the side columns aligning with `┬`/`┴`
     connectors on box edges, with subnet text adjacent
4. **Header banner** at the top inside the code fence, listing the protocols
   and key knobs (e.g. `IS-IS Level 2 • SR-MPLS • SRGB 16000-23999`).
5. **Diagonals** — pure-ASCII cannot draw clean diagonals over the ring lines.
   Do not try. Instead declare the diagonal link on each endpoint's interface
   list inside the box (`Gi0/0/0/X → Rn (Lm)`) and add a single labeled
   callout below the diagram (`Lₙ (RA↔RB diagonal) — <subnet> — Gi0/0/0/X ⇄
   Gi0/0/0/Y`).
6. **Verify alignment with `awk '{print length}'`** — every box-row line in
   the diagram should report the same column count. `gawk` with UTF-8 locale
   returns display columns, so consistent counts == consistent visual width.
7. **Always follow the diagram with a prose paragraph** summarizing the
   topology shape (ring vs. star vs. dual-PE), expected adjacency count, and
   any link with non-obvious purpose (TI-LFA path, RR client, etc).

**Why:** Minimal edge-only diagrams force the reader to cross-reference the
device + link tables for every piece of info, which slows comprehension and
makes the workbook feel under-built. Bordered boxes with metadata give a
single-glance picture of who-runs-what-where.

**Touched:** `labs/segment-routing/lab-00-sr-foundations-and-srgb/workbook.md`
Section 2; this lessons file.

---

## 2026-04-28 — EVE-NG lab path: never hardcode without fallback

**Correction:** BGP labs 01–06 shipped with `DEFAULT_LAB_PATH = "bgp/lab-XX.unl"`,
missing the `ccnp-spri/` parent-folder prefix. `setup_lab.py` and `apply_solution.py`
returned 404 from `/api/labs/bgp/lab-XX.unl/nodes` even when the lab was open in
EVE-NG. Lab-02's `decisions.md` explicitly cited lab-01's broken path as canonical,
which propagated the regression to every subsequent lab.

**Rule:** Every script that resolves an EVE-NG lab path MUST go through
`resolve_and_discover()` in `labs/common/tools/eve_ng.py`. The function tries
`DEFAULT_LAB_PATH` first as a fast path, then falls back to `find_open_lab()`
which walks the folder tree. Never call `discover_ports(host, args.lab_path)`
directly from a lab script. The fast-path string MUST include the project parent
folder (e.g. `ccnp-spri/<topic>/<slug>.unl`) — when copying a script from another
lab, always re-derive the path from the current lab's location, do not copy the
literal string.

**Why:** Hardcoded paths break when the user imports the lab under a different
parent folder, renames it, or opens it via the GUI from a custom location.
The hybrid resolver self-heals in those cases. The `find_open_lab` helper had
its 412 issue fixed in commit 6e3b6a5 (two-pass folder walk), so the original
reason to revert to hardcoded paths no longer applies.

**Touched:**
- `labs/common/tools/eve_ng.py` — added `resolve_and_discover()`.
- 41 lab scripts under `labs/{bgp,ospf}/lab-*/` — converted to the helper and
  fixed the missing `ccnp-spri/` prefix in BGP labs 01–06.
- `.agent/skills/lab-assembler/assets/setup_lab_template.py` — template now uses
  the helper and warns about the `[PROJECT_FOLDER]` substitution.

