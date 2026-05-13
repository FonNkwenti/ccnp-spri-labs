# Design Decisions — segment-routing/lab-00-sr-foundations-and-srgb

## Model gate — 2026-04-30
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

---

## IOS-XR Command Compatibility — 2026-04-30

`ios-compatibility.yaml` has no `xrv9k` platform entries. All segment-routing SR-MPLS
commands (`segment-routing global-block`, `router isis / segment-routing mpls`,
`prefix-sid index N`) are well-documented Cisco IOS-XR 24.3.1 features with stable
syntax across the 7.1+ release family. Per the precedent established in
`mpls/lab-03-rsvp-te-tunnels/decisions.md`, these commands are treated as `pass`
without running `verify_ios_commands.py` (which requires a live EVE-NG instance).

No verification script was run. Syntax correctness was verified by code review against
Cisco IOS-XR Segment Routing Configuration Guide (Release 7.1.x).

---

## metric-style wide Required in lab-00 — 2026-04-30

`metric-style wide` is included in the lab-00 IS-IS configuration even though the
lab-00 blueprint objectives (4.2, 4.2.a, 4.2.b) do not explicitly mention TE or
wide metrics. It is required for two reasons:

1. **SR sub-TLV encoding:** SR prefix SID sub-TLVs are carried in Extended IP
   Reachability TLV 135, which is only generated when `metric-style wide` is active.
   Narrow (legacy) TLVs cannot carry SR extensions. Without wide metrics, SR simply
   does not work — the prefix SIDs are never advertised.

2. **Progressive chain integrity:** lab-01 adds TI-LFA (which relies on the same
   IS-IS TE topology), and later labs add MPLS TE extensions. Starting with wide
   metrics in lab-00 avoids a breaking change mid-chain that would confuse students
   and require re-convergence.

---

## No LDP in lab-00 — 2026-04-30

LDP is intentionally absent from lab-00 configs. lab-02 (`sr-migration-ldp-coexistence`)
is specifically designed to teach LDP+SR coexistence and the `sr-prefer` migration
procedure. Introducing LDP in lab-00 would pre-empt that lesson and muddy the
SR-only label forwarding plane that lab-00 builds. This matches the spec.md design
decision: "the only place in the series where LDP is deliberately re-introduced."

---

## Three Troubleshooting Tickets vs. One in baseline.yaml — 2026-04-30

`baseline.yaml` specifies one fault scenario (R3 missing `segment-routing mpls`).
This lab includes three scenarios:

1. **Scenario 01** (from baseline): R3 missing `segment-routing mpls` under IS-IS af
   — affects prefix SID advertisement from R3, causing all other routers to have no
   label 16003 in their LFIB.

2. **Scenario 02** (added): R4 missing `address-family ipv4 unicast` under IS-IS
   Gi0/0/0/0 — IS-IS adjacency fault rather than SR-specific. Gi0/0/0/0 is L3
   (R4↔R3); the AF removal tears down only that adjacency. R4 retains its L4
   (Gi0/0/0/1) adjacency to R1, so R4 is **not** isolated — total adjacencies in
   the domain drop from 5 to 4 and traffic reroutes via R2. All four prefix-SID
   labels remain installed across the domain. This tests student ability to
   distinguish SR failures from underlying IGP topology changes, which is a
   common real-world diagnostic trap.

3. **Scenario 03** (added): R4 missing `prefix-sid index 4` under IS-IS Loopback0
   — more surgical than Scenario 01: IS-IS routing works, IP reachability to 10.0.0.4
   is fine, but label 16004 is absent from all LFIBs. Tests understanding that prefix
   SID advertisement is distinct from IP prefix reachability.

The three-scenario set covers all three failure layers in the SR control plane: IGP
adjacency (02), SR activation (01), and SID advertisement (03). The ±2 scenario
expansion is within the skill's documented tolerance and better represents exam
troubleshooting depth for a Foundation lab.

---

## segment-routing global-block at IOS-XR Top Level — 2026-04-30

On IOS-XR, `segment-routing global-block <start> <end>` is a **top-level config block**
— it is not nested under `mpls`, `router isis`, or any other subsystem. This is a
common first-time XR operator mistake (looking for it under `mpls traffic-eng` as one
would on IOS-XE). The workbook explicitly calls this out in the concept section to
prevent students from spending time searching in the wrong config hierarchy.

---

## Rebuild — 2026-04-30

The first build of this lab (sonnet-4-6) was rejected by the user for incoherent
artifacts and a `topology.drawio` that would not open. The lab was rebuilt from
scratch on `claude-opus-4-7`. The following defects were repaired:

1. **NET addresses** — solutions/R1.cfg…R4.cfg and topology/README.md used
   `49.0001.0100.0000.000X.00`, contradicting `spec.md` and `baseline.yaml`
   (`49.0001.0000.0000.000X.00`). Fixed across all five files.

2. **topology.drawio format** — the original used a wrapped
   `<mxfile host="65bd71144e"><diagram>…</diagram></mxfile>` envelope that the
   project's drawio tooling cannot open. Rewritten in the bare
   `<mxGraphModel background="#1a1a2e">` form used by every other working lab
   in the repo. Layout: R1 top-left, R2 top-right, R3 bottom-right, R4
   bottom-left, with the L5 R1↔R3 diagonal anchored corner-to-corner so it
   does not overlap the L1/L2/L3/L4 ring edges.

3. **workbook.md** — the 618-line original had a malformed Section 2 ASCII
   topology (R3 listed twice, broken layout) and Scenario 02 narrative that
   contradicted the actual fault behavior. Rewritten in the 11-section
   structure used by `mpls/lab-03-rsvp-te-tunnels`, with internally-coherent
   troubleshooting tickets that match each `inject_scenario_*.py` script.

4. **Scenario 02 narrative** — original copy in workbook, decisions.md, and
   `inject_scenario_02.py` docstring claimed "R4 becomes completely isolated
   from IS-IS." This is wrong: Gi0/0/0/0 is L3 (R4↔R3) only — R4 retains its
   L4 adjacency to R1. Symptom is "1 adjacency down, 4 of 5 remain, traffic
   reroutes via R2." Corrected in workbook §9, decisions.md (Scenario 02
   bullet above), `inject_scenario_02.py` docstring, and the
   `scripts/fault-injection/README.md`.

5. **fault-injection/README.md** — was a bare-stub file (target device + run
   command only). Refreshed with per-scenario fault summaries, expected
   student-visible symptoms, and pedagogical rationale for why each scenario
   is included. Kept the run commands and exit codes intact.

## Model gate — 2026-04-30 (rebuild)
- Difficulty: Foundation
- Running model: claude-opus-4-7
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS
