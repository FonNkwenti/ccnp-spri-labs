# Lab 03 — Design Decisions

## Model gate — 2026-04-28

- Difficulty: Intermediate
- Running model: claude-opus-4-7
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Decision 1 — Default-route origination on R3 and R4 to expose LOCAL_PREF

**Context.** Baseline objective specifies LOCAL_PREF=200 inbound on each CE from its
directly-attached PE. The customer's own /24 cannot demonstrate LP because it is locally
originated on R1 and R2; locally-originated paths win the BGP decision process at step 3
(before AS-path, before eBGP-vs-iBGP), so any LP attached to the iBGP-learned copy of the
/24 is structurally unobservable.

**Decision.** R3 and R4 each originate a default route (`ip route 0.0.0.0 0.0.0.0 Null0`
plus `network 0.0.0.0` under address-family ipv4). The default is the shared, non-locally-
originated prefix on which LP propagation across iBGP can be measured.

**Trade-off.** Adds two `network` statements and two static routes that are not in the
baseline.yaml objective wording. Without them the lab cannot demonstrate its primary
objective. Documented here so reviewers know the deviation is deliberate.

## Decision 2 — Replace baseline Ticket 3 design with /25 RIB-anchor failure

**Context.** Baseline.yaml's lab-03 troubleshooting plan calls for a ticket where "/25 is
visible at R3 but absent from R5 — root cause is missing next-hop-self or send-community
on R3." This planted fault is internally inconsistent:

- Missing `next-hop-self` produces a "/25 present at R5 but inaccessible" symptom (the
  prefix is in the BGP table, marked Inaccessible, not absent). That is exactly lab-02's
  Ticket 3, so reusing the diagnostic surface here is bad pedagogy.
- `send-community` is irrelevant in lab-03 because no community-based filter is in scope
  (communities arrive in lab-04).

**Decision.** Three pedagogically distinct tickets:

1. **Ticket 1** — LP route-map direction wrong on R1 (bound `out` instead of `in`).
   Symptom: R1 prefers ISP-B for default exit. New diagnostic: reading
   `show running-config` for direction on a route-map binding.
2. **Ticket 2** — Overly-tight iBGP egress filter on R3 hides /25 from R5. Implements the
   "/25 in R3, absent from R5" symptom from baseline but with a self-consistent root
   cause (extra prefix-list, not missing next-hop-self). Different diagnostic surface
   from lab-02 Ticket 3.
3. **Ticket 3** — Missing Null0 static for /25-high on R2. Symptom: /25 absent from R2's
   own BGP table. Teaches the `network`-statement-needs-RIB-anchor lesson, which is the
   defining gotcha of selective advertisement.

**Trade-off.** Departs from the baseline.yaml ticket prose but covers the same outbound-
policy and selective-advertisement skill surface in a more pedagogically defensible way.

## Decision 3 — Keep route-map name `TRANSIT_PREVENT_OUT` despite scope creep

**Context.** Lab-01 named the egress route-map `TRANSIT_PREVENT_OUT`. Lab-02 added a
prepend `set` clause. Lab-03 now further tightens the underlying prefix-list to a per-CE
/24-plus-own-/25 scope. The route-map name no longer reflects its full job.

**Decision.** Keep the name. Continuity with the student's lab-01/02 mental model
outweighs naming purity. Documented in lab-02 decisions.md and reaffirmed here.

**Trade-off.** Production review would likely rename to `EBGP_OUT_R3` / `EBGP_OUT_R4`.
Acceptable for the lab; production teams reading these scripts should be aware that the
name encodes only the original (lab-01) intent.

## Decision 4 — Both CEs set LP=200, not just the primary

**Context.** A simpler design would set LP=200 only on R1 (the primary) and leave R2 at
default LP=100. Then R1 always wins for the default, R2 always defers to R1 over iBGP.

**Decision.** Both CEs set LP=200 inbound from their respective PEs.

**Rationale.** Symmetric LP gives clean failover semantics. With LP=200 on both inbounds:

- During steady state, each CE prefers its own ISP for default (eBGP-over-iBGP at LP-tie).
- On eBGP failure, the surviving CE's LP=200 path is the only default left. The orphaned
  CE inherits LP=200 across iBGP and uses the surviving ISP without any further policy
  change.

The asymmetric design (only R1 at LP=200) makes R1 the sole default exit during steady
state — sub-optimal because R2-originated traffic to external destinations transits L3
unnecessarily.

**Trade-off.** Symmetric LP makes the "ISP-A is primary outbound" customer requirement
less crisp at the BGP attribute level — both CEs claim their own ISP as primary. The
end-state is each-CE-prefers-its-own-ISP, which is what the customer wants from a
load-distribution standpoint anyway. The crisp "ISP-A is primary" semantics is satisfied
by lab-02's prepend (inbound) plus the longest-match split in lab-03 (specific
destinations).
