## Model gate — 2026-04-30
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## IOS compatibility verification — 2026-04-30
- All RSVP-TE commands (mpls traffic-eng tunnels, ip rsvp bandwidth, tunnel mode
  mpls traffic-eng, ip explicit-path, mpls traffic-eng level-2) were `unknown` in
  ios-compatibility.yaml — no live EVE-NG was available to probe at build time.
- Treated as `pass` on `ios-classic` based on spec.md authoritative statement:
  "IOSv 15.9 supports IS-IS with MPLS-TE extensions natively" and "RSVP signaling".
  IOSv 15.9(3)M6 has full support for MPLS TE, RSVP-TE, IS-IS TE sub-TLVs, and
  explicit path configuration — these are well-established IOS classic features.

## Solution config design — 2026-04-30
- Added `tunnel mpls traffic-eng bandwidth 10000` and `tunnel mpls traffic-eng priority 1 1`
  to Tunnel10 and Tunnel20. Bandwidth is required to make Ticket 1's admission-control
  fault meaningful: without a requested bandwidth, CSPF does not prune L4 even when
  `ip rsvp bandwidth 10` is configured (zero-bandwidth tunnels bypass admission control).
- Used `next-address loose 10.0.0.3` / `next-address loose 10.0.0.4` for explicit path
  PE1-via-P2. Loose hops with loopback addresses are correct for IS-IS-based TE — strict
  hops require the actual interface IP of the directly adjacent router, not the loopback.
- Tunnels only on PE1 (headend). PE2 is the tail — it participates in RSVP signaling
  via RESV messages but does not originate tunnels in this lab.

## Troubleshooting ticket design — 2026-04-30
- 3 tickets, each exercising a different RSVP-TE failure domain:
  - Ticket 1: RSVP bandwidth admission control (ip rsvp bandwidth undersized on L4)
  - Ticket 2: IS-IS TE topology flooding (mpls traffic-eng level-2 removed from P2)
  - Ticket 3: RSVP global enablement (mpls traffic-eng tunnels removed from P1 globally)
- These map to the three "must remember" commands for exam prep: ip rsvp bandwidth,
  mpls traffic-eng level-2, and mpls traffic-eng tunnels (global vs per-interface).

## Ticket 1 path-option redesign — 2026-04-30
- Initial design used `path-option 20 dynamic lockdown` for Tunnel10's secondary.
- Advisor identified that in the diamond topology (PE1-P1-PE2 and PE1-P2-PE2), L4 (the
  P1↔P2 cross-link) is never on any 2-hop optimal path. CSPF with a dynamic secondary
  would always pick a 2-hop path bypassing L4, so the `ip rsvp bandwidth 10` fault on L4
  produced no observable symptom for Tunnel10.
- Fix: changed path-option 20 to `explicit name PE1-via-L4` with loose waypoints
  10.0.0.2 (P1) → 10.0.0.3 (P2) → 10.0.0.4 (PE2). This forces the secondary to transit
  L4 (P1 Gi0/1 ↔ P2 Gi0/1), making the bandwidth fault visible: CSPF prunes L4 when
  available BW (10 kbps) < requested BW (10,000 kbps), preventing the explicit path from
  signalling.
- Added `ip explicit-path name PE1-via-L4 enable` to PE1.cfg solution accordingly.

## Preflight correctness — 2026-04-30
- Per the IOS behavior lesson from lab-02's inject_scenario_03 bug: IOS removes lines
  on `no X`, never storing the "no" form in running-config. All fault-injection scripts
  in this lab detect fault state by checking ABSENCE of the solution marker, not by
  looking for a "no X" string. inject_scenario_03 additionally uses `^` anchor in
  PREFLIGHT_CMD to distinguish the global command from per-interface occurrences.
