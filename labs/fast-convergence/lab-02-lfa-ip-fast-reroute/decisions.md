## Model gate — 2026-05-09
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Workbook contract gate — 2026-05-09
- All 11 sections present
- 8 tasks covering per-prefix LFA, LFA failure test, LFA coverage gap analysis,
  MPLS LDP deployment, Remote LFA configuration, R-LFA PQ-node analysis,
  R-LFA failure test, and broken prefix-list troubleshooting (Task 8 / Ticket 1 guided)
- 3 troubleshooting tickets: Ticket 1 = R1 bogus route-map filter, Ticket 2 = R2
  MPLS LDP missing on L2, Ticket 3 = R3 LFA clause removed entirely
- Topology ASCII and link reference table match solutions
- Device inventory, cabling, and console access table present
- Base config pre-loaded/not pre-loaded split matches initial-configs vs solutions delta
- Outcome: PASS

## Design decisions — 2026-05-09

### MPLS LDP scope: all core interfaces on R1-R4
Remote LFA requires tunnel capability. IOSv supports `tunnel mpls-ldp` for R-LFA
tunnel creation. MPLS LDP (`mpls ip`) is enabled on every core IS-IS interface
(L1–L5) across all four core routers. The eBGP interfaces (R1 Gi0/3 L6 and R3 Gi0/3
L7) are excluded because MPLS has no role on the CE-facing links.

### R-LFA configured on R1 and R3 only
The spec lists R-LFA configuration as a specific task on R1, but the solutions
include R-LFA on R3 as well (both edge routers) because they are the natural
tunnel heads for MPLS LDP-protected LFA coverage. R2 and R4 (pure core routers)
get per-prefix LFA only. This matches the progressive chain: lab-03 (BGP PIC)
will inherit these configs and R1/R3 are the routers that handle eBGP convergence.

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

The workbook uses this concrete PQ-node example in Tasks 5-6.

### Convergence measurement methodology
All convergence tests use Extended Ping with repeat count and timeout tuned for
millisecond-level observation:
- LFA failure (Task 3): ping R5→10.0.0.4 with R1 shut L1 (Gi0/0)
  Actually: use R5 as ping source? R5 has no IS-IS. The CE can ping R1 directly
  (10.1.15.1) but not loopbacks without a route. Use R2→10.0.0.4 ping instead,
  which traverses L1+L2+L3. Shut L1 → R2's LFA backup via R3 (L2+L5+L3? No,
  R2→R3→R4 path is L2+L3, no L5 needed). R2 has LFA via R3 for 10.0.0.4.
  Correction: R2's path to 10.0.0.4 is via R3 (L2+L3). The LFA backup for
  protecting L2 (R2→R3) is via R1 (L1+L4). Shutting L2 on R2's side... 
  
  Simpler approach: use R2 pinging 10.0.0.4. Shut R2's Gi0/1 (L2). R2's LFA
  backup path to 10.0.0.4 via R1 (L1→L4) should take over in sub-100ms.

### Troubleshooting ticket fault choice
Each ticket targets a different LFA failure mode:
- Ticket 1 (R1): broken prefix-list filter → zero backups — most common operator error
  (pasting an LFA config from another domain without redefining the local prefix-list)
- Ticket 2 (R2): MPLS LDP missing on L2 → R-LFA tunnels broken — reminds the student
  that R-LFA has an MPLS dependency and LDP must be enabled end-to-end
- Ticket 3 (R3): LFA clause removed entirely → coverage gap on one router — tests
  the student's ability to spot a router that has zero protection in an otherwise
  protected mesh
