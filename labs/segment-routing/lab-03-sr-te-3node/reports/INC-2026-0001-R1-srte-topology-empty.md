# INC-2026-0001 — R1 SR-TE Policy Down: Source Node Not Found in Topology

**Lab:** `labs/segment-routing/lab-03-sr-te-3node`
**Date:** 2026-05-15
**Severity:** Task-blocking (Task 2 cannot be verified without SR-TE policy UP)

---

## 1. Incident Summary

SR-TE policy `COLOR_10` on R1 was `Operational: down` immediately after configuration.
CSPF candidate path showed `Last error: Source node not found in topology`. Task 2
verification (`show segment-routing traffic-eng policy color 10`) could not be passed.

---

## 2. Methodology Applied

**Compare Configurations** — the workbook states IS-IS TE extensions are pre-loaded.
Comparing the live IS-IS config against the baseline spec revealed a missing line.

---

## 3. Diagnostic Log

| Time (UTC) | Action | Finding |
|---|---|---|
| 07:43 | `show segment-routing traffic-eng policy color 10` | Operational: down, "Source node not found in topology" |
| 07:53 | `show running-config router isis` | `mpls traffic-eng` and `segment-routing mpls` present; `distribute link-state` absent |
| 07:54 | `show segment-routing traffic-eng topology` | Empty — no nodes, no links |
| 07:54 | `show mpls traffic-eng topology` | Full topology: R1, R3, R4 with all links and correct metrics |
| 07:54 | `show isis database verbose R1/R3/R4` | All nodes advertising SR capabilities (SRGB, prefix-SIDs, adj-SIDs) correctly |
| 07:57 | Applied `distribute link-state` under ISIS CORE address-family | Committed |
| 07:58 | `show segment-routing traffic-eng topology` | Fully populated: R1, R3, R4, all links |
| 07:58 | `show segment-routing traffic-eng policy color 10` | Operational: up, metric 20, SID[0]: 16003 |

---

## 4. Root Cause Analysis

IOS-XR maintains two independent TE topology databases:

1. **RSVP-TE topology** — fed by IS-IS TLV 22 automatically when `mpls traffic-eng` is under IS-IS
2. **SR-TE CSPF topology** — fed by IS-IS only when `distribute link-state` is configured

The initial-configs included `mpls traffic-eng level-2-only` and `mpls traffic-eng router-id Loopback0`
(populating the RSVP-TE database), but omitted `distribute link-state` (leaving the SR-TE
CSPF database empty). CSPF has no topology graph → cannot locate R1 → "source node not found."

**Exam relevance:** This is a realistic production misconfiguration. The `show mpls traffic-eng topology`
being healthy is a red herring — it is a completely different database from the one SR-TE CSPF uses.

---

## 5. Resolution

Applied to R1 (and patched into all lab initial-configs):

```
router isis CORE
 address-family ipv4 unicast
  distribute link-state
 !
!
commit
```

---

## 6. Verification

```
R1# show segment-routing traffic-eng topology
Topology database:
  Node 2  Router ID: 10.0.0.1  Hostname: R1  SRGBs: 16000-24000
  Node 5  Router ID: 10.0.0.3  Hostname: R3  SRGBs: 16000-24000
  Node 6  Router ID: 10.0.0.4  Hostname: R4  SRGBs: 16000-24000
  ... (all links with correct IGP metrics)

R1# show segment-routing traffic-eng policy color 10
  Admin: up  Operational: up
  Preference: 100 (active)
    Dynamic (valid)  Metric Type: IGP  Path Accumulated Metric: 20
    SID[0]: 16003 [Prefix-SID, 10.0.0.3]
```

Metric 20 confirms path routes via R4 (L4+L3 = 10+10), not direct L5 (metric 30).
Single SID is IOS-XR 24.x CSPF optimization — correct.

---

## 7. Lessons Learned

| Finding | Rule |
|---|---|
| `distribute link-state` missing from initial-configs | Always include alongside `segment-routing mpls` in every XR IS-IS initial-config |
| `show mpls traffic-eng topology` full ≠ SR-TE CSPF working | Use `show segment-routing traffic-eng topology` to validate SR-TE prerequisites |
| IOS-XR 24.x CSPF shows single SID when path = IGP path | Verify via `Path Accumulated Metric`, not SID count |
