# Build Decisions — bgp-dual-ce/lab-04-capstone-config

## 1. Model gate — 2026-04-28

- Difficulty: Advanced
- Running model: claude-opus-4-7
- Allowed models: claude-opus-4-7
- Outcome: PASS

## 2. TE coherence — three knobs reconciled

The lab activates three traffic-engineering levers simultaneously: AS-path prepend
on R2→R4, symmetric LOCAL_PREF 200 inbound on both CEs, and selective /25 split.
These were verified against the baseline objectives (which explicitly call for all
three) and against lab-05's planted-fault list (fault #3 explicitly validates that
LOCAL_PREF inbound, not outbound, is the correct construction). The combined story
is "/25s handle normal load distribution; the /24 aggregate biases toward ISP-A as
the inbound preferred path; each CE locally prefers its own egress." The workbook
states this story in Section 1 and Task 7's verification.

## 3. Section 9 — no planted faults

Capstone I objectives are 100% build-and-verify. Inventing fresh faults for
Section 9 would either duplicate lab-05's named faults or add unauthorized content.
Section 9 is therefore a one-line pointer to lab-05 plus four self-diagnosis hints
covering the most common student mistakes. The fault-injector subagent dispatch
(Step 7 of lab-assembler) was skipped; `meta.yaml` does not list any
`scripts/fault-injection/*` files.

## 4. iBGP next-hop reachability — host static routes

The capstone deliberately does not deploy an IGP across the customer or ISP
internals. Each iBGP session uses `update-source Loopback0`, which requires the
peer's Lo0 to be reachable. The clean-slate initial configs include a single host
static route on each router pointing at the peer's Lo0 over the directly-connected
link (e.g., `ip route 10.0.0.2/32 10.1.12.2` on R1). This is also visible in the
solution configs. The Section 4 prerequisites list this so students do not waste
time wondering why `update-source` works without an IGP.

## 5. R1 Lo1 physical, R2 /24 via Null0

R1 has Loopback1 = 192.168.1.1/24 as a physical loopback in the initial configs;
the `network 192.168.1.0 mask 255.255.255.0` matches it directly. R2 has no Lo1
and the student adds `ip route 192.168.1.0/24 Null0` plus the `network` statement
during Task 4. This asymmetry is intentional — it forces the student to encounter
both common idioms for originating a customer aggregate.

## 6. Selective /25 prepend scope

R2's outbound route-map toward R4 prepends both 192.168.1.0/24 and 192.168.1.128/25.
The /25 prepend is harmless (R1 does not advertise the upper /25 anywhere, so no
competing path exists), and keeping the route-map free of per-prefix sequence
numbers is simpler to read and maintain. The workbook does not state a requirement
for prefix-scoped prepend.
