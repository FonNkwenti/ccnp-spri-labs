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

**REVISED 2026-04-30 — see INC-2026-0001.**

**Required on: R2→R4 (confederation eBGP), R3→R4 (confederation eBGP), R2↔R3 (iBGP), R4↔R5 (iBGP).**

RFC 5065 specifies that confederation eBGP should auto-rewrite the next-hop, but Cisco IOS
does not implement this automatically. Without `next-hop-self` on R2 and R3 toward R4,
Customer A's prefix (172.16.1.0/24) is advertised to R4 with next-hop 10.1.12.1 (R1's
interface IP), which is not in OSPF. R4 marks the route inaccessible and does not advertise
it to R5, breaking return traffic from R6 to R1. Empirically confirmed — see incident report
INC-2026-0001.

R4 does NOT need next-hop-self toward R2/R3. R5 already rewrites R6's prefix next-hop to
its own loopback (10.0.0.5) via iBGP next-hop-self before handing it to R4. That loopback
is reachable via OSPF on R2/R3, so no additional rewrite is needed in the R4→R2/R3 direction.

iBGP within sub-AS 65101 (R2↔R3) and sub-AS 65102 (R4↔R5) requires next-hop-self
because iBGP preserves the original next-hop:
- R3 needs next-hop-self from R2 so that Customer A's prefix (received by R2 from R1 at
  10.1.12.1) arrives at R3 with a reachable next-hop (R2's loopback 10.0.0.2 via OSPF).
- R4 needs next-hop-self from R5 so that R6's prefix (received by R5 from R6 at
  10.1.56.6) arrives at R4 with a reachable next-hop. 10.1.56.0/24 is NOT in OSPF;
  without next-hop-self, R4 cannot resolve the next-hop and the route is unusable.

## Ticket 1 Baseline Objective Deviation

**RESOLVED 2026-04-30 — empirical verification complete.**

The baseline.yaml troubleshooting objective reads:
- Fault: "confederation-peers statement missing on R2"
- Symptom: "R1 sees AS-path including 65101"

The original workbook stated that removing `bgp confederation identifier 65100` from R2
would cause sub-AS 65101 to appear in R1's AS_PATH. **This is incorrect.** Empirical
testing on EVE-NG confirms that the actual behavior is an AS OPEN mismatch: R2 presents
itself as AS 65101, but R1 has `neighbor 10.1.12.2 remote-as 65100`, so the session is
refused and stays Idle. The R1↔R2 session goes down; R1 retains only the path via R3.
No sub-AS leakage occurs because no OPEN or UPDATE is accepted.

**Actual fault behavior (verified 2026-04-30):**
- R1 `show ip bgp summary`: neighbor 10.1.12.2 is Idle
- R1 `show ip bgp 172.16.6.0/24`: only one path (via 10.1.13.3/R3)
- R2 `show ip bgp summary`: neighbor 10.1.12.1 is Idle

**Workbook updated** to reflect the real symptom (Idle session / single path).

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
