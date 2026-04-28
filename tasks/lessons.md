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

