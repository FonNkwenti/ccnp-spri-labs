# Design Decisions — BGP Lab 07: Full Protocol Mastery (Capstone I)

## Model gate — 2026-04-28
- Difficulty: Advanced
- Running model: claude-opus-4-7
- Allowed models: claude-opus-4-7
- Outcome: PASS

---

## Capstone Scope vs. Progressive Lab-05

Lab-05 is the terminal node of the progressive chain (lab-00 → lab-05) and contains
nearly every BGP feature in the topic. Lab-07 is **not** a copy of lab-05; it is the
production-realistic version of the same topology. Five deltas distinguish them:

1. **No legacy iBGP full mesh.** Lab-01 left a direct R2↔R5 iBGP session in place
   (additive continuity). Capstone removes it — R4 (RR) is the only iBGP next-hop for
   R2 and R5. This is the standard SP scaling pattern: route reflection replaces full
   mesh, it does not run in parallel with it.

2. **Dampening applied to both eBGP sessions on R5.** Lab-04 dampened only R5↔R6.
   `bgp dampening` is a router-global command in IOS BGP — it applies to all eBGP-learned
   prefixes regardless of which neighbor sent them. Lab-07 calls this out explicitly
   in the workbook so candidates understand R5↔R7 inherits dampening automatically.

3. **Two communities for path-class differentiation.** Primary path (R2 inbound from R1)
   tags 65100:100; backup path (R3 inbound from R1) tags 65100:200. This lets downstream
   policy distinguish primary vs. backup at the community level rather than relying only
   on LOCAL_PREF.

4. **SoO (Site-of-Origin) extended community on both R2 and R3** for Customer A's
   prefix. Without SoO on both PEs, a route Customer A receives back from the SP via
   the alternate eBGP session could be re-imported as if it were a new origin — an iBGP
   re-injection loop. SoO 65001:1 marks the prefix's true origin (Customer A) so each
   PE drops it on inbound if it sees its own SoO.

5. **`maximum-prefix … restart 5`** on every eBGP session (R1↔R2, R1↔R3, R5↔R6,
   R5↔R7) — not `warning-only`. Lab-03 used `warning-only` for R5↔R6 as a teaching
   step (observe the syslog without action). Capstone forces session restart on overflow,
   matching production policy. The 75 % warning threshold remains so operators get a
   syslog before the session drops.

## TTL-Security and MD5 on R5↔R7

Lab-05 left R5↔R7 without `ttl-security` or `password` because the FlowSpec mechanics
were the focus. Capstone hardens this session — both `ttl-security hops 1` and
`password CISCO_SP` apply on both ends. FlowSpec install is unaffected by GTSM/MD5
since they operate below the BGP session layer.

## FlowSpec Boundary Application

Baseline objective: "R5 installs and applies it on the R5↔R6 boundary."
Two valid IOS-XE approaches:
- `bgp flowspec local-install interface-all` (router-global) — installs FlowSpec rules
  on every interface that has `ip flowspec ipv4` enabled.
- `ip flowspec ipv4` on a specific interface — opt-in per-interface.

Lab-07 uses **both**: `interface-all` in the `address-family ipv4 flowspec` block,
plus `ip flowspec ipv4` on R5 Gi3 (the R5↔R6 boundary). This makes the boundary
explicit at the interface level even though `interface-all` would technically cover
all interfaces — easier to reason about during verification.

## Capstone-I Workbook Structure

Per the OSPF lab-04-capstone-config precedent, capstone-I labs use a non-standard
workbook section ordering:
- Section 5 = "Lab Challenge: Full Protocol Mastery" (declares objectives, no
  step-by-step tasks)
- Section 9 = "Lab Teardown"
- Section 10 = "Troubleshooting Scenarios" (provides 3 scripted faults that the
  fault-injector subagent generates)
- Section 11 = "Further Reading"

This differs from the standard 11-section template where Section 9 is
"Troubleshooting." The candidate is expected to build the entire stack from the
clean-slate baseline — the workbook does not hand-hold them through individual
configuration tasks.

## Dynamic Neighbor Range

The `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` on R2 + the L8 link
(10.99.0.0/30 R1↔R2) is preserved from lab-04. R1 carries `neighbor 10.99.0.2 remote-as
65100` so a single TCP session forms over the listen range and demonstrates dynamic
neighbor acceptance. In production this would be dozens of customer CPEs; for the
capstone, one is sufficient to verify the feature.

## AS-path Prepend Length

R1 prepends its own AS twice (65001 65001) on the backup path to R3 — three total
AS occurrences in the AS-path when seen by R3. Lab-02 used a single prepend; capstone
uses double prepend so the path-length difference is unambiguous even if external
ASes also prepend, and so the influence on best-path is robust under propagation.

## IOS Compatibility

All commands in this lab are present in:
- IOS 15.9 (IOSv): R1, R2, R3, R4, R6
- IOS-XE 17.3 (CSR1000v): R5, R7

FlowSpec (`address-family ipv4 flowspec`, `class-map type traffic`, `policy-map type
traffic`) is IOS-XE only — confined to R5 and R7. `bgp listen range`, `ttl-security`,
MD5 password, `maximum-prefix … restart`, `bgp dampening`, RR cluster-id, and SoO
extcommunity are present on both platforms.
