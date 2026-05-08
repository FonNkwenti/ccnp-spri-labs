## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Solution config fixes — 2026-04-30
- Added `neighbor X next-hop-self` to PE1 and PE2 iBGP sessions.
  Without this, the iBGP next-hop for customer prefixes is the CE interface address
  (e.g. 10.10.111.11), which is unreachable from the remote PE via IS-IS. The BGP
  route would be marked inaccessible and no traffic would flow.
- Added `network 10.0.0.1 mask 255.255.255.255` (PE1) and
  `network 10.0.0.4 mask 255.255.255.255` (PE2) under address-family ipv4.
  Required for BGP-LU: `send-label` only allocates and advertises labels for prefixes
  already present in the BGP RIB. Without the network statement, `show ip bgp labels`
  returns empty even with send-label configured.

## Troubleshooting ticket count — 2026-04-30
- Spec defined 1 troubleshooting ticket (BGP-LU send-label mismatch).
- Build added 2 additional tickets as enrichments:
  - Ticket 1: next-hop-self missing on PE1/PE2 (customer prefix next-hop unreachable)
  - Ticket 2: BGP inadvertently configured on P1 (BGP-free core invariant broken)
- Total: 3 tickets. All map directly to tasks and real-world failure modes for this topology.

## inject_scenario_03 preflight fix — 2026-04-30
- Removed dead `PREFLIGHT_FAULT_MARKER = "no neighbor 10.0.0.1 send-label"` constant.
  IOS removes configuration lines entirely on `no X`; it never writes the `no` form into
  running-config. The second guard (`if PREFLIGHT_FAULT_MARKER in output`) could never
  trigger. The fix collapses to a single check: absence of SOLUTION_MARKER means either
  the fault is already injected or the lab is not in solution state — both require
  apply_solution.py.
