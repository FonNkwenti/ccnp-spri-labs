## Model gate — 2026-05-09
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Workbook contract gate — 2026-05-09
- All 11 sections present
- 8 tasks covering baseline observation, global add-paths, per-neighbor add-paths,
  PIC backup verification, edge failure test, core failure test, path identifier
  inspection, and missing backup path troubleshooting
- 3 troubleshooting tickets: Ticket 1 = R2↔R3 additional-paths receive missing,
  Ticket 2 = R2 select backup missing, Ticket 3 = R4↔R1 add-paths config omitted
- Topology ASCII and link reference table match solutions
- Device inventory, cabling, and console access table present
- Base config pre-loaded/not pre-loaded split matches initial-configs vs solutions delta
- Outcome: PASS

## Design decisions — 2026-05-09

### Progressive chain: lab-03 initial = lab-02 solution
The initial configs for lab-03 are the lab-02 solutions — BFD, tuned timers,
NSF/NSR, BGP GR, LFA, R-LFA, and MPLS LDP are all pre-loaded. The student
configures only the BGP PIC and Add-Paths pieces. This isolates the learning
to the exam objective and avoids reconfiguring unrelated features.

### R5 unchanged from lab-02
R5 does not need add-paths configuration. The eBGP sessions from R5 to R1 and
R3 carry only one path each (R5's only prefix 192.0.2.0/24, advertised via
`network`). Add-paths is an iBGP concern in this design — the SP core routers
exchange multiple paths among themselves. R5's configuration is identical to
the lab-02 solution.

### Why bgp recursion host
`bgp recursion host` forces BGP to resolve recursive next-hops via the IGP's
native next-hop rather than through other BGP routes. This matters for PIC
because the backup path must be resolved in the FIB via the IGP's LFA backup.
Without it, a BGP next-hop failure could cause a brief forwarding loop while
BGP re-resolves through a different recursion path. This is a standard best
practice for PIC deployments.

### best 2 (not best 3 or all)
The topology has exactly two eBGP paths into AS 65100 (R1↔R5 and R3↔R5).
Advertising `best 2` ensures every iBGP speaker receives both paths. `best 3`
would be wasteful in this 5-router topology. The CE-side (R5) does not run
add-paths so only one eBGP path exists per edge router.

### Soft-clear requirement after add-paths config
Add-paths capability is negotiated during BGP OPEN message exchange. Changing
the per-neighbor add-paths configuration does not trigger automatic
renegotiation — the session must be reset (hard clear) or soft-cleared
(route-refresh) to renegotiate capabilities. The workbook explicitly instructs
the student to `clear ip bgp * soft` after configuring both sides of each
session.

### Troubleshooting ticket fault choice
Each ticket targets a different add-paths/PIC failure mode:
- Ticket 1 (R2↔R3): missing `additional-paths receive` — most common
  misconfiguration (one side has advertise but nobody can receive). Tests
  the student's understanding of bidirectional capability negotiation.
- Ticket 2 (R2): missing `select backup` — subtle failure: BGP table has
  two paths but CEF has no backup. Tests whether the student checks the
  forwarding plane (CEF) in addition to the control plane (BGP table).
- Ticket 3 (R4↔R1): omitted per-neighbor config for one session in a
  full mesh — classic copy-paste error where one neighbor is skipped.
  Tests systematic verification of all iBGP sessions.

### Failure testing methodology
Two distinct failure tests isolate edge vs core PIC behavior:
- **Edge test** (Task 5): Shut R1's eBGP interface Gi0/3. Tests whether
  PIC Edge on R1/R3 pre-installed the alternate path and whether core
  router R2's PIC Core backup activates. The eBGP session drops cleanly
  (BFD detects in ~150 ms), and forwarding switches in the FIB.
- **Core test** (Task 6): Remove IS-IS from R1's Loopback0. This is a
  more fundamental failure — the BGP next-hop 10.0.0.1 disappears from
  the IGP entirely. Without PIC, every prefix with next-hop 10.0.0.1
  would require a full BGP best-path recomputation. This test verifies
  that PIC Core pre-installed the backup via R3's loopback.

### Path ID inspection (Task 7)
The `rx pathid` and `tx pathid` fields in `show ip bgp <prefix>` are the
add-paths path identifiers. Path ID 0 means no add-paths (default). Non-zero
path IDs indicate add-paths is active and the value identifies the specific
path instance. The workbook instructs the student to compare what each router
sends vs receives to confirm bidirectional add-paths operation.

### Convergence measurement
PIC convergence is measured differently from IGP convergence:
- **IGP convergence** (lab-02): ping from inside the IGP domain (R2→R4).
  Link failure triggers LFA switchover in < 50 ms — 1–2 drops at most on
  a fast-firing ping.
- **BGP PIC convergence** (lab-03): ping from a core router (R2) to the
  external prefix (192.0.2.1). The ping traverses the core to the edge
  router, then across the eBGP link to R5. Edge failure triggers PIC
  Core switchover — ~1–3 drops expected due to BFD detection (150 ms)
  plus forwarding-plane reprogramming.

The workbook uses `ping 192.0.2.1 source lo0 repeat 200 timeout 0` for
sub-second observation. The `timeout 0` means no inter-packet delay, giving
the highest temporal resolution that IOS can provide for packet loss analysis.
