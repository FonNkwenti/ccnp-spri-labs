## Model gate — 2026-04-28
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions

### Static routes (not IGP) for iBGP loopback reachability
The CE-CE iBGP session terminates on Loopback0 of each CE, but no IGP runs in the
customer AS. Loopback reachability is supplied by a single `/32` static route on each
CE pointing at the directly connected interface IP on link L3. Reasons:

- An IGP (OSPF or IS-IS) would add a full topic of unrelated configuration to a
  Foundation lab whose objective is the iBGP session itself.
- The customer AS in this series has only two routers and a single inter-CE link —
  IGP scaling benefits do not apply.
- Static plumbing makes the loopback peering pre-condition explicit. Lab-04 (capstone
  config) and lab-05 (capstone troubleshooting) are `clean_slate: true`, so no
  state from this lab leaks forward; lab-01/02/03 do not touch L3 layer-3, so the
  static survives the entire progressive chain.

The advisor explicitly endorsed this choice over the alternatives (direct-interface
peering — forbidden by objective 4 requiring `update-source Loopback0`; IGP — overkill
for a 60-minute Foundation lab).

### Two-phase task structure (observe gap → close gap)
Section 5 sequences the lab as Phase 1 (eBGP only) → Phase 2 (CE-CE iBGP). Phase 1
ends with Task 4 explicitly asking the student to observe the routing gap on each CE
before any iBGP is configured. Phase 2 then closes the gap. The pedagogical reason:
the gap is the motivation for iBGP in this architecture, and seeing it in the BGP
table is more memorable than reading about it in Section 1 prose.

### R2 originates 192.168.1.0/24 from a Null0 static + network statement
R1 has Loopback1 (192.168.1.1/24) — the customer PI prefix is anchored on a real
interface. R2 deliberately has no Loopback1; instead R2 installs `ip route
192.168.1.0 255.255.255.0 Null0` and uses a `network 192.168.1.0 mask 255.255.255.0`
statement. Reasons:

- Demonstrates the Null0 + network pattern, which is the standard PI-prefix
  origination technique when no local interface anchors the prefix.
- Both CEs originate the same /24 — this is the dual-CE redundancy pattern. With both
  ISPs receiving the prefix from independent CEs, AS 65001 has no single point of
  failure for inbound reachability.
- Sets up lab-03's selective advertisement: R2 will originate 192.168.1.128/25 from a
  Null0 static + network statement, and R1 (which already has the /24 on Lo1) will
  add 192.168.1.0/25 the same way. Establishing the Null0 pattern in lab-00 means
  lab-03 students do not encounter the technique for the first time mid-lab.

### Independent eBGP next-hops left untouched (no peer-group, no template)
The eBGP sessions on each CE are configured neighbor-by-neighbor without
peer-templates or peer-groups. A more elegant configuration would group similar
neighbors, but lab-00 introduces only one eBGP neighbor per CE — the simplification
gives no leverage and only obscures the per-neighbor `update-source` and
`next-hop-self` directives that Phase 2 must layer on top.

### Three faults — all from the dual-CE iBGP foundation
The fault catalogue is bounded by what is configured in this lab: the eBGP sessions,
the customer-prefix advertisements, the static-route plumbing, the iBGP session, and
`next-hop-self`. The three planted faults exercise the most operationally common
failure modes:

1. **Missing iBGP plumbing** (Ticket 1) — `update-source Loopback0` removed.
2. **Missing address-family activation** (Ticket 2) — eBGP session up, prefixes not
   advertised.
3. **Missing next-hop-self** (Ticket 3) — iBGP session up, prefix received, but the
   next-hop is unresolvable.

Faults that depend on later-lab features (transit leaks, AS-path prepend, LOCAL_PREF)
are deferred to their own labs.
