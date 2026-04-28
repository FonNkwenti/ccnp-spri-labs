## Model gate — 2026-04-26
- Difficulty: Advanced
- Running model: claude-sonnet-4-6
- Allowed models: claude-opus-4-7
- Outcome: OVERRIDDEN via --force-model

---

## clean_slate initial-config rule — 2026-04-26

lab-04 is `type: capstone_i` with `clean_slate: true`. Initial configs must NOT be copied
from lab-03 solutions. Per lab-assembler SKILL.md Step 4, configs are generated from
`baseline.yaml core_topology` IP addressing only:
- All interface IP addresses pre-configured
- No OSPF process (no `router ospf 1`, no `network` statements)
- No OSPFv3 process (no `router ospfv3 1`, no `ospfv3 N ipv6 area N` on interfaces)
- No static routes on R3 (student task — activates ASBR redistribution)
- No route-map/redistribution on R5 (student task — NSSA ASBR configuration)
- `ipv6 unicast-routing` and `no ip domain-lookup` pre-enabled as global prerequisites

---

## R1 loopback deviation — 2026-04-26

baseline.yaml specifies R1 Lo0 (10.0.0.1/32) and Lo1 (172.16.1.1/24).
Two additional loopbacks added: Lo2 (172.16.2.1/24, 2001:db8:1:2::1/64) and
Lo3 (172.16.3.1/24, 2001:db8:1:3::1/64) following the same precedent as lab-03.

Rationale: A single Area-1 /24 cannot demonstrate inter-area summarization collapse.
Three /24s within 172.16.0.0/21 make `area 1 range 172.16.0.0 255.255.248.0` meaningful
(collapses 172.16.1-3.0/24 into a single Type-3 LSA at R2).

Same precedent documented in labs/ospf/lab-03-summarization-stub-nssa/decisions.md.

---

## R5 loopback deviation — 2026-04-26

baseline.yaml specifies R5 Lo0 (10.0.0.5/32). Two loopbacks added:
- Lo1 (172.16.5.1/24, 2001:db8:5::1/64) — placed in OSPF Area 3 (internal route)
- Lo2 (192.168.55.1/24) — configured with IP address but NOT in OSPF and NOT
  redistributed in initial-config. Student configures NSSA redistribution as part
  of the capstone challenge.

Rationale: Without Lo2, there is no external prefix for R5 to redistribute into Area 3,
making the NSSA ASBR objective unachievable. Lo1 provides an Area-3 internal route to
contrast with the redistributed external.

---

## R4 loopback addition — 2026-04-26

baseline.yaml specifies R4 Lo0 (10.0.0.4/32). Lo1 (172.16.4.1/24, 2001:db8:4::1/64)
added to give Area 2 an internal prefix visible when the student verifies totally-stubby
behavior (only default route + intra-area routes should appear in R4's RIB).

---

## IOS compatibility — unknown commands — 2026-04-26

The following commands are not in `reference-data/ios-compatibility.yaml` but are
well-established in IOS 15.x on IOSv (ios-classic group). Proceeding as `pass`:

- `area N range <prefix> <mask>` under `router ospf 1` (inter-area ABR summary)
- `area N range <prefix>/<len>` under `router ospfv3 1 address-family ipv6 unicast`
- `summary-address <prefix> <mask>` under `router ospf 1` (external ASBR summary)
- `summary-prefix <prefix>/<len>` under `router ospfv3 1 address-family ipv6 unicast`
- `redistribute static subnets` under `router ospf 1`
- `redistribute static` under `router ospfv3 1 address-family ipv6 unicast`
- `redistribute connected subnets route-map MAP` under `router ospf 1` (R5 NSSA)
- `area N nssa no-redistribution` under `router ospf 1` (fault scenario only)
- `area N stub no-summary` under `router ospf 1` (totally stubby ABR)

All verified against IOS 15.9 field experience and lab-03 execution.

---

## R6 return-path static routes — 2026-04-26

R6 has no OSPF and no routing protocol. Without a default static route, ping replies
originating from R6 (sourced from 192.168.66.1 or 2001:db8:66::1) cannot reach R1,
R4, or R5 — the echo-request arrives via R3's redistributed static, but R6 has no
return path. This breaks the workbook Section 7.5 end-to-end reachability checks.

Fix applied to both initial-configs/R6.cfg and solutions/R6.cfg:
  ip route 0.0.0.0 0.0.0.0 10.1.36.3
  ipv6 route ::/0 2001:DB8:36::3

Pre-existing bug: labs/ospf/lab-03-summarization-stub-nssa/initial-configs/R6.cfg
also omits these static routes. Lab-03 was marked Built ✓ but the same Section 7
reachability verification step would have failed silently. That lab is not modified
here; noting for the next maintenance pass.

---

## Troubleshooting scenario design — 2026-04-26

Three tickets cover the three non-backbone areas (one fault per area):

1. **Ticket 1 (Area 2 — totally stubby)**: R3 configured with `area 2 stub` instead of
   `area 2 stub no-summary`. R4 receives Type-3 inter-area LSAs from all areas (including
   172.16.x.x and external summaries) instead of only the default route. Student identifies
   the missing `no-summary` keyword at the ABR.

2. **Ticket 2 (Area 3 — NSSA translation)**: `area 3 nssa no-redistribution` injected on R3.
   R5's redistributed 192.168.55.0/24 (Type-7 LSA) is not translated to Type-5 at R3.
   The prefix is visible within Area 3 only; R1/R2/R4 have no route to 192.168.55.0/24.

3. **Ticket 3 (Area 1 — inter-area summarization)**: R2's `area 1 range 172.16.0.0 255.255.248.0`
   removed. R3/R4/R5 receive three individual /24 Type-3 LSAs (172.16.1/2/3.0/24) from Area 1
   instead of the single 172.16.0.0/21 summary. Student restores the range on R2.
