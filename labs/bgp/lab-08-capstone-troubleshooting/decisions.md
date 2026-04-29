## Model gate — 2026-04-28
- Difficulty: Advanced
- Running model: claude-opus-4-7
- Allowed models: claude-opus-4-7
- Outcome: PASS

---

## capstone_ii initial-config design — 2026-04-28

lab-08 is `type: capstone_ii` with `clean_slate: true`. Per the convention established by
ospf/lab-05-capstone-troubleshooting (see its decisions.md): capstone_ii initial-configs are
fully configured WITH faults baked in. The `clean_slate: true` flag means "do not chain from
lab-07 progressively" (the student is not expected to have already completed lab-07) — it
does NOT mean "IP-only configs."

Students receive a pre-broken topology and must diagnose and repair 6 concurrent faults.
There are no inject scripts. `setup_lab.py` loads the broken topology directly.
`apply_solution.py` restores all devices to the clean solution state.

Solutions for lab-08 are identical to lab-07-capstone-config solutions (the correct
fully-configured 7-router BGP service-provider topology with route reflection, multihoming,
inter-domain security, communities, dampening, dynamic neighbors, and FlowSpec).

---

## Six-fault design — 2026-04-28

Six faults covering six distinct fault classes from the BGP blueprint. Each fault has a
distinct symptom observable with standard `show` commands. Faults are concurrent — students
must isolate all six. Each fault is on a different device-pair so faults do not mask each
other during diagnosis.

### Fault 1 — Missing next-hop-self on R5 toward R4 (RR)

Device: R5, address-family ipv4 unicast under router bgp 65100
Injected: removed `neighbor 10.0.0.4 next-hop-self`

R5 advertises its eBGP-learned prefixes to R4 (the RR) with the eBGP peer address as next-hop
(10.1.56.6 from R6, 10.1.57.7 from R7). R4 reflects these to R2 and R3 unchanged. R2/R3 have
those /24 transit subnets in OSPF only as host-side connected routes on R5 — but **R5's
eBGP-peer subnets (10.1.56.0/24, 10.1.57.0/24) are NOT redistributed into OSPF** (only Lo0
and the OSPF-participating links 10.1.45.0/24 are). Result: R2/R3 receive the prefix from R4
with an unreachable next-hop, mark it not-best, and never install it.

Symptom: `show ip bgp 172.16.6.0/24` on R5 also shows the missing-NHS impact in reverse —
when R5 receives 172.16.1.0/24 from R4 (originating at R2), R5 does install it (NHS isn't
needed for inbound). The complaint is most visible from the RR-clients on the East side
trying to reach R6's prefix via R5.

Repair: `neighbor 10.0.0.4 next-hop-self` under address-family ipv4 unicast on R5.

### Fault 2 — Wrong route-map direction on R2 toward R1

Device: R2, neighbor 10.1.12.1 inside address-family ipv4 unicast
Injected: changed `neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in` to `... out`

The route-map sets `local-preference 200`, `community 65100:100 additive`, and
`extcommunity soo 65001:1`. Applied outbound, it shapes what R2 advertises to R1 (and
LOCAL_PREF outbound to an eBGP peer is silently ignored anyway). The Customer-A prefix
arrives at R2 untagged: no LP=200, no community, no SoO. The multihoming preference design
collapses — R2 and R3 both have LP=100, so AS-path tie-breaks (and prepending on R3 still
makes R2 win, but the design intent is broken).

Symptom: `show ip bgp 172.16.1.0/24` on R5 shows LP=100, no community, no SoO.

Repair: change route-map direction back to `in` on neighbor 10.1.12.1.

### Fault 3 — MD5 password mismatch on R6↔R5 (corrupt R6 side)

Device: R6, neighbor 10.1.56.5
Injected: changed `neighbor 10.1.56.5 password CISCO_SP` to `neighbor 10.1.56.5 password WRONG_PASS`

R5's side has the correct password. MD5 digests do not match → TCP rejects the SYN+OPTION
→ BGP never reaches OPEN. The session oscillates Active↔Idle. `%TCP-6-BADAUTH` is the
diagnostic.

Symptom: R5 `show ip bgp summary` shows 10.1.56.6 in `Active` or `Idle`, never Established.
TTL-security (which is on both sides) is not the issue here — only the MD5 key.

Repair: `neighbor 10.1.56.5 password CISCO_SP` on R6 (replace WRONG_PASS).

Note: fault was placed on R6 (not R5) so that fixing it requires touching R6 — it forces
the student to look beyond the SP-Core during diagnosis.

### Fault 4 — maximum-prefix 1 on R2↔R1 (flap loop)

Device: R2, neighbor 10.1.12.1
Injected: changed `maximum-prefix 100 75 restart 5` to `maximum-prefix 1 75 restart 5`

R1 advertises 172.16.1.0/24. That single prefix immediately reaches the limit; R2 sends a
NOTIFICATION (cease, maximum-prefix-reached) and tears the session down. After 5 minutes
the `restart` timer brings it back, the prefix arrives again, the limit trips again, the
session bounces. Permanent flap loop.

Symptom: `show ip bgp summary` on R2 shows alternating Established / Idle (PfxCt). Console
log: `%BGP-4-MAXPFX: ... reaches 1, max 1`.

Repair: restore `maximum-prefix 100 75 restart 5` on R2 neighbor 10.1.12.1.

### Fault 5 — Missing send-community both on R2 toward RR

Device: R2, neighbor 10.0.0.4 inside address-family ipv4 unicast
Injected: removed `neighbor 10.0.0.4 send-community both`

R2 attaches `community 65100:100` and `extcommunity SoO:65001:1` to 172.16.1.0/24 inbound
from R1 (after Ticket 2 is fixed). The communities exist locally on R2 but are NOT
propagated to the RR because `send-community both` is missing on the iBGP session toward
10.0.0.4. The reflected copy at R5 is therefore community-less.

Symptom: After fixing Ticket 2 (route-map direction), `show ip bgp 172.16.1.0/24` on R2
shows the community attached locally, but R4 and R5 still see the prefix without it.

Repair: `neighbor 10.0.0.4 send-community both` under address-family ipv4 unicast on R2.

### Fault 6 — Missing per-neighbor activate inside flowspec AFI on R7

Device: R7, address-family ipv4 flowspec, neighbor 10.1.57.5
Injected: removed `neighbor 10.1.57.5 activate` from inside the flowspec AFI block

R7 still has `neighbor 10.1.57.5 activate` inside `address-family ipv4 unicast` (kept
intact — the unicast session works). But without `activate` inside `address-family ipv4
flowspec`, R7 does NOT advertise the FlowSpec SAFI capability during OPEN negotiation.
R5 observes the unicast session as Established, but `show bgp ipv4 flowspec summary`
on R5 shows no peer; `show bgp ipv4 flowspec` returns no NLRIs.

Symptom: R5 `show bgp ipv4 flowspec` empty. R5↔R7 unicast session looks healthy. R7
`show bgp all neighbors 10.1.57.5` does not list flowspec under "For address family".

Repair: `neighbor 10.1.57.5 activate` inside `address-family ipv4 flowspec` on R7.

---

## Fault placement constraints — 2026-04-28

- Each fault is on a different device-pair, so the symptoms cannot mask each other:
  - Fault 1: R5 (iBGP to R4 / impact on East PEs)
  - Fault 2: R2↔R1 (eBGP control-plane policy)
  - Fault 3: R5↔R6 (eBGP TCP-layer)
  - Fault 4: R2↔R1 (eBGP session-layer)
  - Fault 5: R2↔R4 (iBGP attribute propagation)
  - Fault 6: R5↔R7 (eBGP SAFI-negotiation)
- Fault 2 and Fault 4 both target R2's neighbor 10.1.12.1 but exercise different layers
  (RIB-IN policy vs. session control-plane). The student must recognize that two
  independent faults can coexist on a single session — fixing one does not fix the other.
- MD5 fault was placed on R5↔R6 (not R5↔R7) deliberately: stacking MD5 + missing flowspec
  activate on the same session would cause the MD5 fault to mask the flowspec fault until
  MD5 is repaired. With MD5 on R5↔R6 and FlowSpec on R5↔R7, both diagnoses are independent.

---

## Awareness note: lab-07 inject_scenario_01 — 2026-04-28

While building lab-08 the advisor flagged that lab-07's `inject_scenario_01.py` is documented
as "Remove `next-hop-self` on R4 toward R5", but R4's lab-07 solution config does not
configure `next-hop-self` toward any RR client (only `route-reflector-client` and
`send-community both`). The inject script is therefore a no-op against the lab-07 solution.

The textbook fault is "remove next-hop-self on **R5** toward **R4**" — which is what we
plant here in lab-08 as Fault 1. Lab-07's inject_scenario_01 was not modified by this build
(out of scope); flagged for a future fix to that lab.

---

## R1 advertised prefix — 2026-04-28

Carried forward from lab-07-capstone-config: R1 advertises only 172.16.1.0/24 (Lo1). This
is the prefix used to test LOCAL_PREF, community tagging, SoO, and as the FlowSpec NLRI
destination match.

---

## R6/R7 return-path defaults — 2026-04-28

Carried forward from lab-07-capstone-config: R6 has `ip route 0.0.0.0 0.0.0.0 10.1.56.5`
and R7 has `ip route 0.0.0.0 0.0.0.0 10.1.57.5` for return-path reachability when needed
during diagnosis. Both initial-configs and solutions retain these.
