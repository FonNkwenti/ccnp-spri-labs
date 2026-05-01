# Build Decisions — isis/lab-02-dual-stack-summarization

## Model gate — 2026-04-30

- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Decision 1 — IS-IS commands treated as implicit pass on IOSv

IS-IS commands (`router isis`, `net`, `is-type`, `metric-style wide`, `address-family ipv6`, `multi-topology`, `summary-address`, `summary-prefix`, `redistribute isis ip level-2 into level-1`, `distribute-list prefix`, `ipv6 router isis`, `isis circuit-type`) are not enumerated in `ios-compatibility.yaml`. All are standard IOS IS-IS commands available since IOS 12.0+ and are fully supported on IOSv (IOS 15.9(3)M6). Treated as implicit `pass` on `iosv` for this lab, consistent with the Decision 1 precedent from lab-01.

## Decision 2 — IPv6 summary prefix is 2001:DB8::/45, not /40

The initial plan considered `2001:DB8::/40` as the IPv6 aggregate. A `/40` covers the third-group range 0x0000–0x00FF, which would capture transit link subnets:
- 2001:db8:12::/64 (third group 0x0012) — inside /40
- 2001:db8:23::/64 (third group 0x0023) — inside /40

These transit subnets must NOT be summarized because they carry active IS-IS adjacencies and would create routing instability if suppressed by the aggregate. The correct prefix is `2001:DB8::/45`, which covers third groups 0x0000–0x0007, capturing only:
- 2001:db8:1::/64 (R1 Lo1) ← included
- 2001:db8:4::/64 (R4 Lo1) ← included
- 2001:db8:5::/64 (R5 Lo1) ← included

All transit subnets (0x0012, 0x0023, 0x0034, 0x0035, 0x0036) fall outside the /45 boundary.

## Decision 3 — IPv4 summarization only on R3 (area 49.0002 border), not R2

Summary-address is configured only on R3 because R3 is the L1/L2 border router injecting area 49.0002's L1 prefixes into the L2 LSDB. R2 (the area 49.0001 border) has no area-specific Lo1 prefixes to aggregate in this topology — R1's Lo1 (172.16.1.0/24) is a single prefix that does not benefit from summarization and is already visible from R2's L1 LSDB. Adding a needless summary on R2 would create a Null0 discard for an unused aggregate range.

IPv6 summarization (`summary-prefix 2001:DB8::/45`) IS configured on both R2 and R3 because both routers inject the aggregate into their respective level databases. This is pedagogically important: the student must apply the same summary-prefix command on both border routers to suppress the individual Lo1 /64 prefixes across both L1 and L2 boundaries.

## Decision 4 — R3 Gi0/3 is shutdown in initial-configs; student activates it in Task 2

R3's Gi0/3 (link to R6) is present but `shutdown` in the initial-configs. This forces the student to consciously activate the interface, add IP addressing, configure static routes, and enable redistribution — all as a single coherent Task 2. If Gi0/3 were pre-configured and active, the redistribution task would lose its instructional flow and the student would not practice the full workflow of connecting an external device to an IS-IS domain.

## Decision 5 — Three fault scenarios target orthogonal IS-IS subsystems

| Ticket | Fault class | Target | Fault | Primary symptom |
|--------|-------------|--------|-------|-----------------|
| 1 | MT-IPv6 interface participation | R4 | `ipv6 router isis CORE` removed from all interfaces | IPv4 IS-IS intact; all IPv6 routes absent from R4 |
| 2 | External redistribution pipeline | R3 | `redistribute static ip` removed from IS-IS process | 192.168.66.0/24 disappears from entire IS-IS domain |
| 3 | Route-leak filter | R2 | `LEAK_FROM_L2` prefix-list permit entry removed | 192.168.66.0/24 visible in L2 table but absent from area 49.0001 |

Each ticket forces a different diagnostic path: T1 requires comparing IPv4 and IPv6 IS-IS interface state; T2 requires tracing the redistribution source on R3; T3 requires isolating the route-leak filter despite the prefix being correctly redistributed.

## Decision 6 — Route-leak syntax is `distribute-list prefix <name>`, not `distribute-list prefix-list`

The IOS syntax for IS-IS route leaking uses `distribute-list prefix <prefix-list-name>` — the keyword `prefix-list` does not appear in this context. This differs from OSPF/EIGRP where `distribute-list prefix-list <name>` is common. The difference is explicitly called out in the workbook cheatsheet to prevent the most common student error on this command.

## Decision 7 — R6 has identical initial-config and solution config

R6 is an external non-IS-IS router. Its full configuration (IP addressing, loopbacks, static default routes) is pre-loaded in initial-configs, and there is nothing additional for the student to configure on R6. The solution config is therefore identical to the initial config. The student's work for R6-related tasks (redistribution, static routes on R3) happens entirely on R3, not on R6 itself.
