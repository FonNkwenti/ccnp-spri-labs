# XR Coverage Policy

**Status:** Active (effective 2026-05-06).
**Owner:** Project — see `CLAUDE.md`.
**Authority:** Every topic `spec.md` MUST cite this document in its *Design
Decisions* section under the heading **"XR Coverage Posture"** (wording template
in §4 below). When this document and a `spec.md` disagree, this document wins
and the spec is amended.

This file is the single source of truth for how IOS XR is exposed to students
across the project. It exists because the 300-510 blueprint is platform-agnostic
in most sections but XR-flavored in others (RPL, segment routing, SRv6), and
the project also targets CCIE SP precursor fluency, which demands more XR
exposure than the bare blueprint requires.

---

## 1. Policy statement

The project serves two audiences:

1. **Primary — 300-510 SPRI exam candidate.** The bar is: every blueprint
   sub-bullet has at least one lab where that sub-bullet is the primary
   teaching point, on a platform that demonstrates the feature correctly.
2. **Secondary — CCIE SP lab precursor.** The bar is: the candidate sees IOS
   XR CLI in every topic where SP production reality runs XR, even when the
   300-510 blueprint does not strictly require it.

These two audiences are reconciled per-topic via one of five **postures**
(§2). The blueprint-mandated audience is non-negotiable; the precursor
audience is best-effort and explicitly out of scope for `IOSv-only` topics.

### Platform-selection rule (project-wide)

When a topic needs XR exposure, prefer the platform that is **just sufficient**
for the features in that topic:

| Image | RAM | Use when |
|---|---|---|
| **IOSv 15.9** | ~0.5 GB | Default for foundation IGP/BGP/MPLS work that doesn't require XR or XE-specific features. |
| **IOS XRv** (light, 6.1.x) | ~3 GB | Default for any XR exposure. Supports OSPF, IS-IS, BGP (incl. RR, confederations), MPLS LDP, MPLS-TE, basic multicast, RPL. **Lacks** SR, SRv6, EVPN, FlowSpec. |
| **IOS XRv 9000** (7.1.1) | ~16 GB | Reserve for SR, SRv6, EVPN, FlowSpec, Tree SID, PCE, and any feature plain XRv refuses. The `xr-bridge` topic always includes **one** XRv 9000 node regardless, so students see both images. |
| **CSR1000v** (IOS-XE 17.3) | ~3 GB | Where IOS-XE-specific behavior is the teaching point (currently `bgp` and `ipv6-transition`). |

This rule keeps the per-lab RAM peak well below the 64 GB host ceiling on the
Dell Latitude 5540 and avoids gratuitous XRv 9000 boot latency (~10 min/node).

---

## 2. The five postures

Every topic in `labs/` has exactly one posture. A topic's posture is recorded
in its `spec.md` and reflected in `memory/progress.md`.

| Posture | Definition | When to choose | RAM impact |
|---|---|---|---|
| `XR-native` | All core nodes are XR. IOSv may appear only as customer edge / translation reference. | Topic teaches XR-only features (SR, SRv6). | High (XRv 9000 only). |
| `XR-mixed` | Foundation/intermediate labs are IOSv; capstone(s) replace 2 nodes with IOS XRv (or XRv 9000 if features demand it). Workbook adds capstone tasks that specifically require XR CLI. | Topic's blueprint bullets are platform-agnostic for foundation labs but CCIE SP precursor wants XR fluency by end of topic. | Low for foundation, moderate for capstone. |
| `IOSv-only with XR appendix` | All labs IOSv. Specific labs append a workbook section "Same Tasks on IOS-XR" with side-by-side CLI and an `solutions-xr/<RouterX>.cfg` file showing the XR equivalent for one router. No XR boot required to complete the lab. | Topic is platform-agnostic and a full mixed retrofit is overkill, but a few high-value labs deserve XR literacy (e.g. BGP RR, confederations, FlowSpec). | Zero — XR config is read, not run. |
| `IOSv-only` | All labs IOSv. No XR exposure within the topic. CCIE SP precursor coverage for adjacent XR concepts deferred to the `xr-bridge` topic. | Topic's features are well-taught on IOSv and dialect translation is not the lesson. | Zero. |
| `Bridge` | The `xr-bridge` self-study topic itself. 4× IOS XRv + 1× XRv 9000 + 1× IOSv reference. Re-treats OSPF, IS-IS, BGP, MPLS, multicast, fast-convergence on pure XR. **Optional, build deferred**, included in the project as a bonus. | Sole instance: topic 12. | Moderate (~28 GB peak). |

---

## 3. Per-topic posture table

Effective state at end of the XR Coverage Retrofit (Phase 3 + Phase 4 of the
2026-05-06 plan). Topics still at their pre-retrofit posture as of writing
are flagged in the *Current* column.

| # | Topic | Current posture (pre-retrofit) | Target posture | Driver |
|---|---|---|---|---|
| 1 | `ospf` | IOSv-only | **XR-mixed** | 1.2 multiarea — XR exposure in capstone (Phase 3 #4). |
| 2 | `isis` | IOSv-only | **XR-mixed** | 1.3 multilevel — XR exposure in capstone (Phase 3 #3). |
| 3 | `bgp` | IOSv-only (+ CSR1000v) | **XR-mixed + appendix** | Capstone retrofit (Phase 3 #5) + lab-01/05/06 appendices (Phase 4). |
| 4 | `bgp-dual-ce` | IOSv-only | **XR-mixed** | Capstone retrofit (Phase 3 #6) — one CE pair flipped to IOS XRv to demonstrate XR-side dual-CE iBGP and inbound TE. |
| 5 | `routing-policy` | XR-mixed | **XR-mixed** | Already correct. RPL is XR-only by definition; XR1/XR2 carry §3.1, §3.2.d, §3.2.j. |
| 6 | `mpls` | IOSv-only | **XR-mixed** | 4.1.a/b/c/d/e — capstone retrofit (Phase 3 #1). LDP, BGP-LU, RSVP-TE on XR. |
| 7 | `fast-convergence` | IOSv-only | **XR-mixed** | 1.7.b NSF, 1.7.c NSR — NSR only demonstrable on XR; capstone retrofit (Phase 3 #2). |
| 8 | `multicast` | IOSv-only | **XR-mixed** | 2.x — capstone retrofit (Phase 3 #7). |
| 9 | `ipv6-transition` | IOSv-only (+ CSR1000v) | **IOSv-only** | 1.6.c 6PE is the only XR-canonical bullet; deferred to `xr-bridge` rather than retrofit. Documented gap. |
| 10 | `segment-routing` | XR-native | **XR-native** | Already correct. |
| 11 | `srv6` | XR-native | **XR-native** | Already correct. SRv6 is the only feature that absolutely requires XRv 9000. |
| 12 | `xr-bridge` *(new)* | n/a | **Bridge** (spec-only, build deferred) | Bonus self-study topic. |

### Documented gaps

- **`ipv6-transition` is intentionally left IOSv-only.** 6PE (§1.6.c) is
  SP-XR-flavored in production, but the cost/benefit of retrofitting this
  topic is poor compared to pointing students to `xr-bridge`. The spec must
  explicitly call this out so students know where to go for XR exposure on
  that bullet.

---

## 4. Wording template — paste into every topic `spec.md`

Insert this subsection at the **top** of the *Design Decisions* section of
every topic `spec.md`. Replace `<POSTURE>`, `<RATIONALE>`, and the
optional cross-references in the bracketed slots. Do not alter wording
outside the bracketed slots — the consistency of phrasing across 11 specs is
load-bearing for navigation.

```markdown
- **XR Coverage Posture: `<POSTURE>`** (per `memory/xr-coverage-policy.md`).
  <RATIONALE — one or two sentences specific to this topic explaining
  why this posture is the right fit. Reference the primary blueprint
  bullets that drive the posture choice.>
  [If `XR-mixed`: name the capstone(s) that carry XR exposure and link
   to the Phase 3 retrofit task.]
  [If `IOSv-only with XR appendix`: list the labs that carry the
   appendix and the routers whose `solutions-xr/<RouterX>.cfg` exists.]
  [If `IOSv-only`: name the `xr-bridge` lab that picks up the deferred
   coverage, e.g. "XR exposure for this topic's bullets is deferred to
   `labs/xr-bridge/lab-NN-...`."]
```

### Blueprint Coverage Matrix — new column

Every topic spec's Blueprint Coverage Matrix gets a new rightmost column
**"XR Exercised?"** with one of:

- `yes — primary` — XR is the platform that demonstrates this bullet (the
  bullet is the lab's main teaching point, on XR).
- `yes — capstone` — XR demonstrates this bullet only inside the capstone
  retrofit, not in foundation labs.
- `appendix` — XR CLI for this bullet is shown in a workbook appendix,
  not run on XR hardware.
- `no` — XR exposure for this bullet is deferred to the `xr-bridge` topic.

---

## 5. RAM budget summary (peak per topic, post-retrofit)

| Topic | Posture | Foundation peak | Capstone peak | Notes |
|---|---|---|---|---|
| `ospf` | XR-mixed | ~3 GB (5×IOSv) | ~9 GB (3×IOSv + 2×XRv) | Phase 3 #4. |
| `isis` | XR-mixed | ~3 GB (6×IOSv) | ~10 GB (4×IOSv + 2×XRv) | Phase 3 #3. |
| `bgp` | XR-mixed + appendix | ~5 GB (IOSv + 1×CSR) | ~12 GB (4×IOSv + 1×CSR + 2×XRv) | Phase 3 #5 + Phase 4. |
| `bgp-dual-ce` | XR-mixed | ~3 GB (6×IOSv) | ~9 GB (4×IOSv + 2×XRv) | Phase 3 #6. |
| `routing-policy` | XR-mixed | ~2 GB (lab-00/01) → ~9 GB (lab-02+ with XR1/XR2) | ~10 GB | unchanged. |
| `mpls` | XR-mixed | ~3 GB (4×IOSv) | ~10 GB (4×IOSv + 2×XRv) | Phase 3 #1. |
| `fast-convergence` | XR-mixed | ~3 GB (5×IOSv) | ~10 GB (3×IOSv + 2×XRv) | Phase 3 #2. NSR demonstrable for first time. |
| `multicast` | XR-mixed | ~4 GB (4×IOSv + 2×Linux) | ~11 GB (3×IOSv + 2×XRv + 2×Linux) | Phase 3 #7. |
| `ipv6-transition` | IOSv-only | ~3 GB | ~3 GB | unchanged. |
| `segment-routing` | XR-native | ~80 GB peak (5×XRv 9000) | ~80 GB | unchanged — already at hardware ceiling, see lab-00 prereq notes. |
| `srv6` | XR-native | ~96 GB peak (6×XRv 9000) | ~96 GB | **exceeds 64 GB ceiling** — known, documented in srv6 spec, students must boot in halves. |
| `xr-bridge` | Bridge | ~28 GB (4×XRv + 1×XRv 9000 + 1×IOSv) | ~28 GB | comfortably within ceiling. |

The two ceiling-violating topics (`segment-routing`, `srv6`) are pre-existing
constraints that the XR Coverage Retrofit does **not** make worse. They are
listed here for completeness, not for action.

---

## 6. Change control

This document changes only by the same review-gate process used for spec
amendments. To propose a posture change for any topic:

1. Open a task in `tasks/todo.md` describing the proposed flip and the
   blueprint-bullet driver.
2. Update §3 of this document and §5 if RAM changes.
3. Update the affected topic `spec.md` to match (do not let them drift).
4. Commit all three together.

Drift between this document and any topic `spec.md` is a project bug and
should be filed as a follow-up immediately.
