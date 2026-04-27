## Model gate — 2026-04-27
- Difficulty: Advanced
- Running model: claude-sonnet-4-6
- Allowed models: claude-opus-4-7
- Outcome: OVERRIDDEN via --force-model

---

## capstone_ii initial-config design — 2026-04-27

lab-05 is `type: capstone_ii` with `clean_slate: true`. Unlike capstone_i (where initial-configs
are IP-only and the student builds everything), capstone_ii initial-configs are fully configured
OSPF WITH faults baked in. The `clean_slate: true` flag means "do not chain from lab-04 progressively"
(the student is not expected to have completed lab-04 first) — it does NOT mean "IP-only configs."

Students receive a pre-broken topology and must diagnose and repair ≥5 concurrent faults. There are
no inject scripts. `setup_lab.py` loads the broken topology directly. `apply_solution.py` restores
all devices to the clean solution state.

Solutions for lab-05 are identical to lab-04-capstone-config solutions (the correct fully-configured
dual-stack multiarea OSPF topology).

---

## Five-fault design — 2026-04-27

Five faults covering all five required fault classes. Each fault has a distinct symptom
observable with standard `show` commands. Faults are concurrent — students must isolate all five.

### Fault 1 — Adjacency mismatch (Area 2, R3 ↔ R4)

Device: R3, interface GigabitEthernet0/1 (R3-R4 link)
Injected: `ip ospf dead-interval 80` on R3 Gi0/1

R4 retains the IOS default dead-interval of 40s. R3 Gi0/1 advertises dead-interval 80 in
Hello packets. The two endpoints disagree; the adjacency never reaches FULL.

Symptom: `show ip ospf neighbor` on R3 shows R4 stuck in INIT or no entry. Area 2 prefix
172.16.4.0/24 does not appear in R1/R2's LSDB. R4 loses all inter-area routes.

Repair: `no ip ospf dead-interval` on R3 Gi0/1 (restores default 40s).

### Fault 2 — LSA propagation (Area 3, Type-7 never originated at ASBR)

Device: R5, ip prefix-list NSSA_EXTERNAL_PREFIX
Injected: `ip prefix-list NSSA_EXTERNAL_PREFIX seq 5 permit 192.168.55.0/25` (wrong /25 mask)

IOS prefix-list matching requires an exact prefix-length match unless ge/le qualifiers are
present. The Lo2 connected route is 192.168.55.0/24; the permit entry is /25. No match →
route-map NSSA_EXTERNAL denies Lo2 → `redistribute connected` skips it → no Type-7 LSA is
originated at R5. Because no Type-7 exists, R3 has nothing to translate.

Symptom: `show ip ospf database nssa-external` on R5 shows **no entry** for 192.168.55.0/24.
`show ip route 192.168.55.0` on every router returns no match.

Repair: `no ip prefix-list NSSA_EXTERNAL_PREFIX seq 5` then
`ip prefix-list NSSA_EXTERNAL_PREFIX seq 5 permit 192.168.55.0/24` on R5.

### Fault 3 — Summarization (Area 1, wrong range mask on R2)

Device: R2, router ospf 1
Injected: `area 1 range 172.16.0.0 255.255.254.0` (wrong /23 mask, should be /21)

A /23 summary (172.16.0.0 – 172.16.1.255) does not encompass Lo2 (172.16.2.0/24) or Lo3
(172.16.3.0/24) on R1. Those two specific /24s leak as individual Type-3 LSAs rather than
being suppressed into the summary. This also means the summary itself covers a smaller range
than intended, and R3/R4/R5 see 3 routes instead of 1.

Symptom: `show ip route` on R3 shows 172.16.2.0/24 and 172.16.3.0/24 as separate entries
alongside 172.16.0.0/23 summary. R2's LSDB has three Type-3 LSAs for Area 1 /24s instead
of one /21 summary.

Repair: `area 1 range 172.16.0.0 255.255.248.0` on R2 (correct /21 mask).

### Fault 4 — IPv6 parity gap (Area 3, R5 OSPFv3 adjacency missing)

Device: R5, interface GigabitEthernet0/0
Injected: `ospfv3 1 ipv6 area 3` removed from R5 Gi0/0

OSPFv2 adjacency between R5 and R3 is fully functional. OSPFv3 has no adjacency because R5's
transit interface is not participating in OSPFv3 process 1. R5's IPv6 loopback prefixes
(2001:DB8::5/128, 2001:DB8:5::/64) are not in the IPv6 LSDB at R3/R2/R1. Pings from R1
to R5 work over IPv4 but not IPv6.

Symptom: `show ospfv3 neighbor` on R5 shows no entry for R3. `show ospfv3 database` on R1
has no entries from Area 3. IPv4 ping R1→R5 Lo1 succeeds; IPv6 ping fails.

Repair: `ospfv3 1 ipv6 area 3` under interface GigabitEthernet0/0 on R5.

### Fault 5 — Redistribution filter drop (R3 ASBR blocks R6 external prefix)

Device: R3, router ospf 1
Injected:
```
ip prefix-list BLOCK_EXT seq 5 deny 192.168.66.0/24
ip prefix-list BLOCK_EXT seq 10 permit 0.0.0.0/0 le 32
distribute-list prefix BLOCK_EXT out static
```

R3 has the static route to 192.168.66.0/24 (via R6), but the distribute-list filters it
during redistribution into OSPF. No Type-5 LSA for 192.168.66.0/24 is originated. The
summary-address 192.168.0.0/16 also does NOT fire because there are no component subnets.
R1, R2, R4, and R5 have no route to R6's Loopback1.

Symptom: R3 `show ip route static` shows 192.168.66.0/24. But `show ip ospf database external`
shows no LSAs for that prefix on R1 or R2. `show ip ospf redistribute` on R3 shows the prefix
suppressed by distribute-list.

Repair: `no distribute-list prefix BLOCK_EXT out static` on R3, then remove the prefix-list.

---

## R1 loopback deviation — 2026-04-27

Carried forward from lab-04-capstone-config/decisions.md. Three loopbacks (Lo1, Lo2, Lo3)
with 172.16.x.0/24 prefixes are required to make the Area 1 /21 summary meaningful.

---

## R6 return-path static routes — 2026-04-27

Carried forward from lab-04-capstone-config/decisions.md. R6 must have:
  ip route 0.0.0.0 0.0.0.0 10.1.36.3
  ipv6 route ::/0 2001:DB8:36::3
Both initial-configs/R6.cfg and solutions/R6.cfg include these routes.
