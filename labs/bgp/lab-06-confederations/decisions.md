# Design Decisions — BGP Lab 06: BGP Confederations

## Model gate — 2026-04-28
- Difficulty: Advanced
- Running model: claude-sonnet-4-6
- Allowed models: claude-opus-4-7
- Outcome: OVERRIDDEN via --force-model

---

## Confederation Sub-AS Assignment

**Sub-AS 65101 for East PEs (R2, R3); Sub-AS 65102 for Core + West (R4, R5)**

The east/west split mirrors a realistic SP design where geographically distinct PE clusters
are grouped into separate sub-ASes. Grouping R4 (core) with R5 (West PE) in sub-AS 65102
keeps the sub-AS count to two and makes the confederation eBGP boundary clear: all
east-to-west traffic crosses the 65101↔65102 confederation eBGP boundary at R2↔R4 or R3↔R4.

Using private sub-AS numbers in the 65101–65102 range (within the 64512–65534 private
range) reflects real-world practice. The public confederation identifier 65100 is the
only AS number visible to external peers R1 and R6.

## next-hop-self Placement

**Only on iBGP sessions; never on confederation eBGP sessions.**

Confederation eBGP behaves like regular eBGP: the next-hop is automatically rewritten
to the peering interface address. Adding next-hop-self to confederation eBGP sessions
(R2↔R4, R3↔R4) would be redundant and is omitted to keep the design clean.

iBGP within sub-AS 65101 (R2↔R3) and sub-AS 65102 (R4↔R5) requires next-hop-self
because iBGP preserves the original next-hop:
- R3 needs next-hop-self from R2 so that Customer A's prefix (received by R2 from R1 at
  10.1.12.1) arrives at R3 with a reachable next-hop (R2's loopback 10.0.0.2 via OSPF).
- R4 needs next-hop-self from R5 so that R6's prefix (received by R5 from R6 at
  10.1.56.6) arrives at R4 with a reachable next-hop. 10.1.56.0/24 is NOT in OSPF;
  without next-hop-self, R4 cannot resolve the next-hop and the route is unusable.

## Ticket 1 Baseline Objective Deviation

The baseline.yaml troubleshooting objective reads:
- Fault: "confederation-peers statement missing on R2"
- Symptom: "R1 sees AS-path including 65101"

These do not match technically: removing `bgp confederation peers 65102` from R2 would
cause R4's sub-AS (65102) to leak into the external AS-path, not 65101. The symptom
"R1 sees 65101 in AS-path" is produced by removing `bgp confederation identifier 65100`
from R2 — R2 then presents itself as AS 65101 to the external eBGP peer R1.

**Resolution:** The symptom from the baseline takes precedence. Ticket 1 injects
`no bgp confederation identifier 65100` on R2, which produces exactly the stated symptom.
This deviation is documented here.

**Empirical verification required:** Removing `bgp confederation identifier 65100` from R2
may cause the R1↔R2 eBGP session to tear down (AS mismatch: R1 expects remote-as 65100,
R2 presents as 65101 in BGP OPEN) rather than producing sub-AS leakage in the AS-path.
The stated symptom ("R1 sees 65101 in AS-path") requires EVE-NG lab verification before
the fault script is declared production-ready. If session teardown is the observed behavior,
the fault injection should be changed to target `bgp confederation peers` instead.

## R1↔R3 eBGP Session (Backup Path)

Including a second eBGP session between R1 and R3 (via 10.1.13.0/24) exercises the iBGP
full-mesh requirement within sub-AS 65101. Without the backup path, R3's iBGP role (receiving
R2's eBGP-learned routes and propagating them) would not be verified during the lab.
The backup path also enables Ticket 2 to have an observable effect: when R3's iBGP
session to R2 is broken, R3 loses the R2-learned path but retains its own direct R1 route.

## OSPF in Initial Configs

Baseline objective specifies "IP addressing + OSPF only; no BGP" for the clean-slate
initial state. OSPF is included in all SP routers' initial configs (R2, R3, R4, R5)
despite the SKILL.md generic guidance of "IP addressing only." The OSPF underlay is
required for loopback reachability — without it, the iBGP sessions (which use loopbacks)
cannot form, making the lab incompletable from a clean baseline.

## Confederation Commands — IOS Compatibility

`bgp confederation identifier` and `bgp confederation peers` are not listed in
ios-compatibility.yaml. They are treated as known-pass on:
- IOS 15.9 (IOSv): supported since IOS 12.0
- IOS-XE 17.3 (CSR1000v): fully supported
No workarounds required.

## Standalone Lab Type

Lab-06 is clean-slate (type: standalone, clean_slate: true in baseline.yaml). Initial
configs are generated fresh from the core topology IP plan and OSPF design — not chained
from lab-05. This reflects the exam-relevant scenario where a candidate must build a
confederation from scratch, rather than extending an existing flat iBGP design.
