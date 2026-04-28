## Model gate — 2026-04-26
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

---

## Initial-config chain deviations — 2026-04-26

Lab-03 is progressive (extends lab-02) but introduces R6 for the first time.
Standard rule ("copy lab-02 solutions verbatim") is modified as follows:

1. **R1 initial-configs**: Lab-02 R1 solution + Lo2 (172.16.2.1/24, 2001:db8:1:2::1/64)
   and Lo3 (172.16.3.1/24, 2001:db8:1:3::1/64) added and placed in OSPF Area 1.
   Rationale: A single Area-1 prefix (172.16.1.0/24) cannot demonstrate summarization
   collapse. Three /24s within 172.16.0.0/21 make the `area 1 range` task meaningful.

2. **R3 initial-configs**: Lab-02 R3 solution + Gi0/3 (10.1.36.3/24, 2001:db8:36::3/64)
   pre-configured with IP addressing but NOT added to OSPF. Student activates R6
   integration as Task 1.

3. **R5 initial-configs**: Lab-02 R5 solution + Lo2 (192.168.55.1/24) configured but NOT
   in OSPF via network statement and NOT redistributed. Student redistributes it as the
   NSSA ASBR task.

4. **R6 initial-configs**: Brand-new device (no lab-02 predecessor). IP-only config:
   Lo0, Lo0_v6, Lo1 (192.168.66.1/24, 2001:db8:66::1/64), Gi0/0 (10.1.36.6/24,
   2001:db8:36::6/64). No routing protocol. R6 stays IP-only throughout the lab —
   R3 uses static routes to reach R6's loopbacks and redistributes them into OSPF.

---

## Summarization prefix selection — 2026-04-26

- IPv4 inter-area summary on R2: `area 1 range 172.16.0.0 255.255.248.0` collapses
  172.16.1.0/24, 172.16.2.0/24, and 172.16.3.0/24 from R1 into one Type-3 LSA.
  R2 is ABR for Area 1 only; `area 1 range` covers Area-1 routes exclusively.
  R4's 172.16.4.0/24 (Area 2) is not affected by this command and is not summarized
  in this lab.

- IPv6 inter-area summary on R2: `area 1 range 2001:db8:1::/48` collapses the three
  Area-1 loopback /64 prefixes (2001:db8:1::/64, 2001:db8:1:2::/64, 2001:db8:1:3::/64).
  The Area-1 link prefix (2001:db8:12::/64) and Lo0 (2001:db8::1/128) are NOT within
  this summary and continue as separate Type-3 LSAs.

- IPv4 external summary on R3: `summary-address 192.168.0.0 255.255.0.0` collapses
  the single /24 external route (192.168.66.0/24) into a /16 Type-5 LSA. This
  intentionally demonstrates: (a) LSA count reduction, (b) the auto-generated Null0
  discard route (AD 254) that IOS installs to prevent routing loops.

---

## IOS compatibility — unknown commands — 2026-04-26

The following commands are not in `reference-data/ios-compatibility.yaml` but are
well-established in IOS 15.x on IOSv (ios-classic group). Proceeding as `pass`:

- `area N range <prefix> <mask>` under `router ospfv3 1 address-family ipv6 unicast`
- `summary-prefix <prefix>/<len>` under `router ospfv3 1 address-family ipv6 unicast`
- `redistribute static` under `router ospfv3 1 address-family ipv6 unicast`
- `area N nssa no-redistribution` under `router ospf 1`
- `redistribute connected subnets route-map MAP` under `router ospf 1`

---

## Troubleshooting scenario design — 2026-04-26

Three tickets chosen to cover each major lab theme:

1. **Ticket 1 (redistribution)**: distribute-list added to R3 blocking external prefix
   from OSPF. Student sees 192.168.66.0/24 disappear from all routers.

2. **Ticket 2 (stub area mismatch)**: `area 2 nssa` injected on R3, replacing
   `area 2 stub no-summary`. R4 (which has `area 2 stub`) sees area-type mismatch;
   R3-R4 adjacency drops. Student must identify area-type conflict.

3. **Ticket 3 (NSSA translation)**: `area 3 nssa no-redistribution` injected on R3.
   Type-7 LSAs from R5 are not translated to Type-5 at R3. R5's redistributed
   192.168.55.0/24 is visible only within Area 3, invisible to R1/R2/R4.
