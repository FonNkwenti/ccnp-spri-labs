# INC-2026-0001 — R2/R3 OSPF↔IS-IS Redistribution and Tag Verification Faults

**Lab:** `labs/routing-policy/lab-01-tags-regex-communities`
**Date:** 2026-05-02
**Severity:** Medium (redistribution partially working; tags missing; loop-prevention not yet verifiable)
**Devices affected:** R2 (primary), R3 (secondary)

---

## 1. Incident Summary

Task 1 verification commands show no evidence that redistribution is working:
- `show route-map OSPF_TO_ISIS` on R2 shows 0 hit counters on all sequences
- `show ip route isis` on R2 and R3 is empty
- `show isis database detail` on R2 shows redistributed routes but NO tag sub-TLV (tag 100 absent)
- Workbook verification criterion ("non-zero hit counters in show route-map") cannot be satisfied

Three separate root causes were identified via live device inspection.

---

## 2. Methodology Applied

**Compare Configurations** — compared live state against `initial-configs/R2.cfg` and the workbook
solution. The baseline has no redistribute commands; the user added them along with route-maps.
Targeted `show isis database detail` and `show ip protocols` were used to determine actual
redistribution behaviour at the IS-IS LSP level.

---

## 3. Diagnostic Log

| Time | Action | Finding |
|------|--------|---------|
| T+0 | `show route-map OSPF_TO_ISIS` on R2 | 0 "Policy routing matches" on all sequences |
| T+1 | `show run \| section router ospf` on R2 | `redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF` present |
| T+2 | `show run \| section router isis` on R2 | `redistribute ospf 1 route-map OSPF_TO_ISIS` present |
| T+3 | `show ip route isis` on R2 | Empty — no IS-IS routes in RIB |
| T+4 | `show isis database R2.00-00 detail` on R1/R2/R3 | OSPF routes ARE in LSP but with metric 0 and NO tag sub-TLV |
| T+5 | `show ip protocols` on R2 | IS-IS SP shows `Redistributing: ospf 1 (internal, external 1 & 2...)` — redistribution command is active |
| T+6 | `show run \| section route-map OSPF_TO_ISIS` on R2 | Three separate `match route-type` lines in seq 10 (not separate sequences) |
| T+7 | `show ip route isis` on R3 | Empty — no IS-IS routes winning RIB anywhere in domain |
| T+8 | `show run \| include redistribute` on R3 | No redistribute commands on R3 at all |

---

## 4. Root Cause Analysis

### RCA-1 (User Config) — Route-map structure does not match workbook design

**What the user configured on R2:**

```
route-map OSPF_TO_ISIS permit 10
 match route-type internal         ← three separate match route-type lines
 match route-type external type-1
 match route-type external type-2
 set tag 100
```

**What the workbook solution requires:**

```
route-map OSPF_TO_ISIS permit 10
 match route-type external type-1   ← one route-type per sequence
 set tag 100
route-map OSPF_TO_ISIS permit 20
 match route-type external type-2
 set tag 100
route-map OSPF_TO_ISIS permit 30
 match route-type internal
 set tag 100
```

IOS does combine multiple `match route-type` lines within the same sequence as OR (the
`show route-map` output consolidates them to a single line). So routes ARE being
redistributed — seq 10 effectively becomes "match any OSPF route type." However:

- The route-type classification that Task 1 is designed to teach (separate counters per
  route-type class) is lost — all routes hit seq 10 with no per-type visibility.
- More critically, the `set tag 100` clause appears NOT to be encoding a tag sub-TLV into
  the IS-IS LSP when the match structure combines all types (see RCA-2).

The `ISIS_TO_OSPF` route-map has the same issue:
```
route-map ISIS_TO_OSPF permit 10
 match route-type level-1     ← two lines instead of one "match route-type level-2"
 match route-type level-2
```
The correct form for IS-IS redistribution into OSPF is `match route-type level-2` only
(this is a level-2-only IS-IS domain).

---

### RCA-2 (Workbook Verification Bug) — Wrong IS-IS show command keyword

**Evidence:** After fixing RCA-1 (correct route-map structure), `show isis database
R2.00-00 verbose` reveals that `set tag 100` IS working correctly:

```
  Metric: 0          IP 10.1.14.0/24
    Route Admin Tag: 100          ← tag sub-TLV IS encoded
    Prefix-attr: X:1 R:0 N:0     ← X:1 = External (redistributed from OSPF)
```

**Root cause of apparent failure:** The workbook specified `show isis database detail`,
but that keyword omits IS-IS sub-TLVs entirely. Only `show isis database verbose` shows
Route Admin Tag sub-TLVs and Prefix Attributes. This is not a platform limitation —
`set tag 100` works correctly on IOSv 15.6(2)T. The workbook used the wrong keyword.

---

### RCA-3 (Workbook Verification Bug) — `show route-map` hit counter never increments for redistribution

**The workbook states:**
> `show route-map OSPF_TO_ISIS` on R2 must show non-zero hits on seq 10.

**What IOS actually does:**
The "Policy routing matches: 0 packets, 0 bytes" counter in `show route-map` is
**exclusively a PBR counter**. It only increments when the route-map is applied via
`ip policy route-map` on an interface and a packet is matched. For redistribution
route-maps, this counter is always 0 regardless of how many routes have been redistributed.
The verification criterion as written cannot be satisfied — ever.

**Correct verification approach for redistribution hit counters:**
There is no direct per-sequence counter for redistribution in IOS. Redistribution
effectiveness must be verified via:
- `show isis database <hostname> detail` — look for redistributed prefixes with Tag sub-TLV
- `show ip route | include tag` — shows routes with their tag values in the RIB

---

### RCA-4 (Workbook Design Issue) — IS-IS RIB is empty due to AD conflict; IS-IS→OSPF redistribution cannot produce routes

**The workbook states:**
> `show ip route ospf` on R3 must show IS-IS-originated prefixes with tag 200.

**Why this cannot be achieved in the current topology:**

Both OSPF (AD 110) and IS-IS (AD 115) run on the **same interfaces** (Gi0/0, Gi0/1, Gi0/2,
Lo0). For every prefix known by IS-IS, an identical or better OSPF route exists with lower
AD. OSPF wins the RIB on every router. Result:

- `show ip route isis` is empty on R1, R2, R3 (IS-IS routes exist in topology DB but
  never win the RIB)
- `redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF` under `router ospf 1` on
  R2 redistributes from the IS-IS **RIB** (not topology DB) — and the RIB is empty
- No IS-IS-tagged routes can appear in the OSPF table anywhere

The loop-prevention scenario requires routes that exist **exclusively** in one protocol's
domain. The current topology has full overlap. The workbook's verification criterion cannot
be achieved without either:
  (a) Adjusting admin distances (`distance` command under `router isis SP`)
  (b) Adding prefixes that exist only in IS-IS (e.g., a loopback only advertised into IS-IS)

This is a workbook assumption that does not hold for the given topology.

---

## 5. Resolution Actions

### Applied to live lab (2026-05-02):

**R2 — route-map structure corrected:**
```
no route-map OSPF_TO_ISIS permit 10
no route-map OSPF_TO_ISIS permit 20
no route-map OSPF_TO_ISIS permit 30
route-map OSPF_TO_ISIS permit 10
 match route-type external type-1
 set tag 100
route-map OSPF_TO_ISIS permit 20
 match route-type external type-2
 set tag 100
route-map OSPF_TO_ISIS permit 30
 match route-type internal
 set tag 100
no route-map ISIS_TO_OSPF permit 10
route-map ISIS_TO_OSPF permit 10
 set metric 20
 set tag 200
no router isis                    ! removed stray unnamed IS-IS process
```

**R1, R2, R3 — IS-IS-only Loopback10 added:**
```
interface Loopback10
 ip address 10.200.0.{1,2,3} 255.255.255.255
 ip router isis SP
 ! no ip ospf 1 area 0 — deliberately excluded so IS-IS wins the RIB
```

**Workbook updated:** Section 5 Task 1 & 2 verification, Section 6 Objective 1,
Section 7 verification cheatsheet — all corrected to use `verbose` and `show ip route
<prefix>`. Initial configs for R1, R2, R3 updated with Loopback10.

---

## 6. Testing & Verification (Confirmed 2026-05-02)

- [x] `show isis database R2.00-00 verbose` shows `Route Admin Tag: 100` on all OSPF-redistributed prefixes (10.1.14.0/24, 172.16.1.0/24, 10.0.0.1/32, 10.0.0.3/32, 10.200.0.1/32, 10.1.13.0/24). Prefix-attr X:1 confirmed.
- [x] `show ip route isis` on R2 shows `i L2 10.200.0.3/32 [115/20]` — IS-IS RIB is no longer empty
- [x] `show ip route 10.200.0.3` on R1 shows `Tag 200, type extern 2 / Route tag 200`
- [x] `show ip ospf database external 10.200.0.3` on R2 shows `External Route Tag: 200, Metric: 20`
- [x] `show ip route ospf` on R1 shows `O E2 10.200.0.3/32 [110/20]` via R2
- [x] IS-IS topology still shows full connectivity on R1, R2, R3
- [x] `show route-map OSPF_TO_ISIS` shows correct single-type structure (one type per sequence)

---

## 7. Lessons Learned

| # | Learning | Exam Relevance |
|---|----------|---------------|
| 1 | `show route-map` "Policy routing matches" is PBR-only; it is always 0 for redistribution route-maps. Never use this counter to verify redistribution correctness. | Exam may ask how to verify redistribution — answer is via the target protocol's table or database, not `show route-map`. |
| 2 | `show isis database detail` does NOT show IS-IS sub-TLVs. Use `show isis database <lspid> verbose` to see `Route Admin Tag` and `Prefix-attr` sub-TLVs. The `detail` / `verbose` distinction is undocumented in most guides and is a common exam/lab trap. | Any question asking you to verify IS-IS route tags requires `verbose`. |
| 3 | In IS-IS redistribution route-maps, write exactly **one `match route-type` per sequence**. Multiple `match route-type` lines in the same sequence are combined as OR by IOS, obscuring per-type visibility and preventing the educational purpose of separate sequences. | The separate-sequence structure is the standard in Cisco SPRI curriculum and required for meaningful hit counter analysis. |
| 4 | When OSPF (AD 110) and IS-IS (AD 115) share all interfaces, IS-IS never wins the RIB. IS-IS→OSPF redistribution reads from the IS-IS RIB (not topology DB), so it exports nothing. Add IS-IS-only prefixes (loopbacks not in OSPF) to give IS-IS unique routes for redistribution demonstrations. | Mutual redistribution lab scenarios require distinct route domains or IS-IS-only prefixes to verify the IS-IS→OSPF direction. |
| 5 | `show ip route \| include tag` does NOT show tags — the tag appears only in `show ip route <prefix>` detailed output. For OSPF external tags, also use `show ip ospf database external <prefix>` which explicitly shows `External Route Tag: <value>`. | Verify OSPF redistribution tags via database or per-prefix route detail, not via pipe-grep. |
