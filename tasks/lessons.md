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

