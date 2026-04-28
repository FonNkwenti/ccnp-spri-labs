# Design Decisions — BGP Lab 05: BGP Communities and FlowSpec

## Model gate — 2026-04-28
- Difficulty: Advanced
- Running model: claude-haiku-4-5-20251001
- Allowed models: claude-opus-4-7
- Outcome: OVERRIDDEN via --force-model

---

## Community Architecture

**Standard community format: `65100:N`**
`65100` (the SP AS) as the first octet ensures communities are recognizable as SP-internal
tags. The second octet encodes the service class (100 = Customer A origin in this lab).
This mirrors real SP practice where communities like `65100:100`, `65100:200` represent
distinct customer or service tiers.

**SoO value: `65001:1`**
SoO is formatted as `ASN:site-ID`. Using AS 65001 (Customer A's ASN) as the first
part makes it obvious which customer the SoO belongs to. Site ID 1 is used because
Customer A has a single site; a real SP would use different IDs per customer location.

**Why apply SoO on both R2 and R3?**
Both PEs must stamp the SoO because the RR (R4) reflects Customer A's route to all
clients. Without SoO on R3, the backup PE would accept the reflected route and
potentially re-advertise it back toward R1 on the L2 link, creating a loop.

## FlowSpec Design Choices

**R7 as FlowSpec originator, R5 as enforcer**
R7 originates the FlowSpec NLRI and disables local install (`bgp flowspec disable-local-install`)
because the enforcement point should be at the SP boundary (R5), not at R7 itself.
R5 enforces the rule at the GigabitEthernet3/4 eBGP boundary using
`bgp flowspec local-install interface-all`.

**IOS-XE platform requirement for FlowSpec**
IOSv (IOS 15.9) does not implement SAFI 133 (ipv4 flowspec). Both R5 and R7 are
CSR1000v (IOS-XE 17.3) — the only platform in this EVE-NG lab that supports FlowSpec.
This reflects real-world deployments where FlowSpec requires a modern OS upgrade.

**class-map type traffic + policy-map type traffic**
IOS-XE uses these QoS-style constructs to define FlowSpec match criteria and actions.
The `police rate 0 pps` with `conform-action drop` encodes a `traffic-rate 0` action
into the FlowSpec extended community, which is the RFC 5575 standard drop encoding.

## Well-Known Community Placement

**`no-export` applied at R6 outbound AND R5 inbound**
Applying it at R6 (origin) is the cleanest design — the source tags its own prefix.
The R5 inbound application is defense-in-depth in case R6's tagging is misconfigured.
Both reinforce the same policy boundary.

**`no-advertise` applied at R7 outbound**
`no-advertise` is more restrictive than `no-export` — the receiving router (R5) will
not forward this prefix to any BGP peer, including iBGP neighbors like R4. This is
appropriate for the R7 prefix since it is used solely for FlowSpec demonstration and
should not appear in the SP core routing table.

## Initial Config Chain

Lab-05 is progressive (extends lab-04). Initial-configs for R1–R4 and R6 are exact
copies of lab-04 solutions. R5's initial config adds GigabitEthernet4 (the R7 link)
so the IP layer is pre-provisioned — the student only configures BGP. R7 is a new
node initialized with IP addressing only (no BGP process).
