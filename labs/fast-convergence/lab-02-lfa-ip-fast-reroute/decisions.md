## Model gate — 2026-05-09
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Rebuild gate — 2026-05-12
- Rebuilt on CSR1000v (was IOSv)
- Interface naming: Gi1/2/3/4 throughout
- IS-IS NSF: live, inherited from lab-01 CSR1000v solutions (`nsf ietf` on R1–R4)
- NSR: conceptual only — CSR1000v single-RP platform rejects `nsr` and `bgp nsr`
- LFA and R-LFA: live on CSR1000v — removed all IOSv-limitation / paper-exercise notes
- MPLS LDP: carries forward on core IS-IS interfaces
- BFD and BGP GR: inherited from lab-01
- Agent: pi

## Workbook contract gate — 2026-05-09 (re-validated 2026-05-12)
- All 11 sections present
- 8 tasks covering per-prefix LFA, LFA failure test, LFA coverage gap analysis,
  MPLS LDP deployment, Remote LFA configuration, R-LFA PQ-node analysis,
  R-LFA failure test, and broken prefix-list troubleshooting (Task 8 / Ticket 1 guided)
- 3 troubleshooting tickets: Ticket 1 = R1 bogus route-map filter, Ticket 2 = R2
  MPLS LDP missing on Gi2 (L2), Ticket 3 = R3 LFA clause removed entirely
- Topology ASCII and link reference table match solutions
- Device inventory, cabling, and console access table present
- Base config pre-loaded/not pre-loaded split matches initial-configs vs solutions delta
- All interface names use CSR1000v GigabitEthernetX convention
- Outcome: PASS

## Design decisions — 2026-05-09 (updated 2026-05-12)

### Platform: CSR1000v (IOS-XE 17.03.05)
All five devices run CSR1000v. Interface naming is GigabitEthernet1/2/3/4
matching the EVE-NG CSR1000v template. The IOSv Gi0/X naming used in the
original build is replaced throughout.

### MPLS LDP scope: all core interfaces on R1-R4
Remote LFA requires tunnel capability. CSR1000v supports `tunnel mpls-ldp`
for R-LFA tunnel creation. MPLS LDP (`mpls ip`) is enabled on every core
IS-IS interface (L1–L5) across all four core routers. The eBGP interfaces
(R1 Gi4 L6 and R3 Gi4 L7) are excluded because MPLS has no role on the
CE-facing links.

### R-LFA configured on R1 and R3 only
The spec lists R-LFA configuration as a specific task on R1, but the solutions
include R-LFA on R3 as well (both edge routers) because they are the natural
tunnel heads for MPLS LDP-protected LFA coverage. R2 and R4 (pure core routers)
get per-prefix LFA only. This matches the progressive chain: lab-03 (BGP PIC)
will inherit these configs and R1/R3 are the routers that handle eBGP convergence.

### IS-IS NSF: inherited from lab-01 (live, not conceptual)
CSR1000v supports `nsf ietf` under `router isis`. All four core routers carry
this configuration forward from lab-01. The initial-configs are lab-01 solutions
exactly — no config delta needed between lab-01 end state and lab-02 start state.

### LFA coverage gap — deliberate pedagogical choice
The 5-link meshed core topology yields near-100% per-prefix LFA coverage with
default metrics (all interfaces metric 10). The workbook task (Task 4) asks the
student to find a gap but acknowledges that the topology may or may not produce
one with default metrics. The key insight is understanding the LFA inequality
and why certain topologies are fully covered while others aren't. The task
instructs the student to run `show isis fast-reroute summary` and report the
actual coverage percentage, then explain under what conditions a gap would
occur (unequal metrics, topology changes).

### PQ-node for R-LFA: R3 is the primary PQ node
For R1 protecting destinations via R2 (L1 failure scenario):
- P-space of R1: {R1, R3, R4} (nodes reachable without traversing L1)
- Q-space of R2: {R2, R3, R4} (nodes that can reach R2 without traversing L1)
- PQ = {R3, R4} → R3 is the best-metric PQ node (closest to R1 via L5)

The workbook uses this concrete PQ-node example in Tasks 6-7.

### Convergence measurement methodology
All convergence tests use Extended Ping with repeat count and timeout tuned for
millisecond-level observation. The LFA failure test uses R2 pinging 10.0.0.4
while shutting R2's Gi2 (L2 to R3). The precomputed LFA backup via R1 (L1→L4)
should take over within 1-2 lost ping packets.

### Troubleshooting ticket fault choice
Each ticket targets a different LFA failure mode:
- Ticket 1 (R1): broken prefix-list filter → zero backups — most common operator error
  (pasting an LFA config from another domain without redefining the local prefix-list)
- Ticket 2 (R2): MPLS LDP missing on Gi2 → R-LFA tunnels broken — reminds the student
  that R-LFA has an MPLS dependency and LDP must be enabled end-to-end
- Ticket 3 (R3): LFA clause removed entirely → coverage gap on one router — tests
  the student's ability to spot a router that has zero protection in an otherwise
  protected mesh
