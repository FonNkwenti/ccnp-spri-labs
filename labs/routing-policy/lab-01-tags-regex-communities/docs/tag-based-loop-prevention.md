# Tag-Based Loop Prevention — Theory & Scenarios

## Table of Contents

1. [The Problem: Redistribution Loops](#1-the-problem-redistribution-loops)
2. [The Solution: Tag-Based Loop Prevention](#2-the-solution-tag-based-loop-prevention)
3. [Two-Router Design Pattern](#3-two-router-design-pattern)
4. [Scenario A: OSPF→IS-IS→OSPF Loop (172.16.1.0/24)](#4-scenario-a-ospf→is-is→ospf-loop-172161024)
5. [Scenario B: IS-IS→OSPF→IS-IS Loop (10.200.0.2/32)](#5-scenario-b-is-is→ospf→is-is-loop-102000232)
6. [Tag State Machine](#6-tag-state-machine)
7. [What Happens When Loop Prevention Is Missing](#7-what-happens-when-loop-prevention-is-missing)
8. [Verification Commands Reference](#8-verification-commands-reference)

---

## 1. The Problem: Redistribution Loops

When two routing protocols redistribute into each other (mutual redistribution), a route can
bounce indefinitely across the protocol boundary — a **redistribution loop**.

### How a loop forms

```
     OSPF domain                    IS-IS domain
  ┌────────────────┐          ┌──────────────────────┐
  │                │          │                      │
  │  R1──R2──R3    │   ──►    │  R2──R3──XR1──XR2    │
  │                │   OSPF   │                      │
  │                │   ──►    │                      │
  │                │   IS-IS  │                      │
  │                │   ──►    │                      │
  │                │   OSPF   │                      │
  │                │   ──►    │                      │
  │                │   IS-IS  │                      │
  │                │    ...   │                      │
  └────────────────┘          └──────────────────────┘
```

**A single route's journey without loop prevention:**

1. Route originates in OSPF (e.g., a connected subnet redistributed into OSPF on R1)
2. R2 redistributes OSPF→IS-IS → route now exists in IS-IS
3. R3 learns the route via IS-IS and redistributes IS-IS→OSPF → route re-enters OSPF
4. R2 sees the route back in OSPF (now from R3) and redistributes it OSPF→IS-IS again
5. R3 sees it in IS-IS again and ships it back to OSPF
6. Repeat steps 4–5 indefinitely

### Why Cisco IOS does not detect this automatically

Unlike Spanning Tree Protocol or RPF checks, **redistribution has no built-in loop
detection mechanism**. Each redistribution event is a local policy action — the router
sees a route in protocol A, applies a route-map, and installs it in protocol B. The router
has no awareness that the same prefix has crossed this boundary before.

### Symptoms of an active redistribution loop

| Symptom | What to look for |
|---------|-----------------|
| **Duplex LSAs** | `show ip ospf database external <prefix>` shows the same prefix advertised by **two different routers** (R2 and R3) |
| **Route flapping** | `show ip route <prefix>` alternates between two next-hops and metrics every few seconds |
| **Metric inflation** | Each pass through the redistribution cycle adds metric overhead — the route's OSPF cost or IS-IS metric grows with every loop iteration |
| **CPU spikes** | SPF and IS-IS SPD fire repeatedly as LSAs / LSPs are updated |
| **Clear-text loop** | `debug ip routing` shows the same prefix being installed and removed in rapid succession |

---

## 2. The Solution: Tag-Based Loop Prevention

Route tags are a 32-bit integer attached to a route as it crosses a protocol boundary.
Two tags define the scheme:

| Tag | Meaning | Applied by | Checked by |
|-----|---------|-----------|------------|
| **100** | "This route originated in OSPF" | OSPF→IS-IS route-maps | IS-IS→OSPF deny on the loop protector |
| **200** | "This route originated in IS-IS" | IS-IS→OSPF route-maps | OSPF→IS-IS deny on the loop protector |

### The principle

> **Stamp the origin tag on first crossing. Deny the origin tag on re-entry.**

A route that came from OSPF will carry tag 100 when it appears in IS-IS. When the loop
protector router sees that route and considers sending it back to OSPF, the tag says *"this
was just in OSPF — if you send it back, you're creating a cycle."* The deny sequence blocks it.

The tag does not prevent the **first** redistribution — it prevents the **second** crossing
in the opposite direction.

### Where the deny sequences must go

The deny sequence must go on the **receiving side** of the loop — the router that could pull
a route back into the protocol it just left.

```
  OSPF ──OSPF→IS-IS──► IS-IS ──IS-IS→OSPF──► OSPF
        (tagger)                (loop protector)
                                 deny tag 100
                                 ─── blocks re-entry into OSPF

  IS-IS ──IS-IS→OSPF──► OSPF ──OSPF→IS-IS──► IS-IS
         (tagger)                (loop protector)
                                 deny tag 200
                                 ─── blocks re-entry into IS-IS
```

---

## 3. Two-Router Design Pattern

In the SP CORE topology, redistribution runs on **two routers** (R2 and R3) with distinct
roles:

### R2 — the "Tagger Only"

```
┌──────────────────────────────────────────────────────────┐
│                        R2                                 │
│                                                           │
│  OSPF◄───────ISIS_TO_OSPF───────IS-IS                    │
│              permit 10                                    │
│              set tag 200                                  │
│              set metric 20                                │
│                                                           │
│  OSPF───────OSPF_TO_ISIS───────►IS-IS                    │
│              permit 10 (E1)                               │
│              permit 20 (E2)      set tag 100              │
│              permit 30 (internal)                         │
│                                                           │
│  Role: Stamp the origin tag. Never block.                 │
└──────────────────────────────────────────────────────────┘
```

- **OSPF→IS-IS**: stamps **tag 100** on all OSPF route types (E1, E2, internal)
- **IS-IS→OSPF**: stamps **tag 200** (metric 20) on all IS-IS routes
- **No deny sequences** — R2 permits everything that matches the route-type criteria

R2's route-maps represent the **uncontrolled** flow — tags are stamped but nothing is
blocked. This is by design: the tag is the label that R3 uses to identify and stop the loop.

### R3 — the "Loop Protector"

```
┌──────────────────────────────────────────────────────────┐
│                        R3                                 │
│                                                           │
│  OSPF◄───────ISIS_TO_OSPF───────IS-IS                    │
│              deny 10 match tag 100    ◄── NEW             │
│              permit 20                                     │
│              set tag 200                                   │
│              set metric 20                                 │
│                                                           │
│  OSPF───────OSPF_TO_ISIS───────►IS-IS                    │
│              deny 10 match tag 200    ◄── NEW             │
│              permit 20 (E1)                               │
│              permit 30 (E2)      set tag 100              │
│              permit 40 (internal)                         │
│                                                           │
│  Role: Block tagged routes from re-entering their         │
│        origin protocol.                                   │
└──────────────────────────────────────────────────────────┘
```

- **Both maps have a `deny 10` at the top** that matches the opposite-tag
- `ISIS_TO_OSPF deny 10 match tag 100` — blocks OSPF-origin routes from re-entering OSPF
- `OSPF_TO_ISIS deny 10 match tag 200` — blocks IS-IS-origin routes from re-entering IS-IS
- After the deny, the permit sequences are identical to R2's (tag the remaining routes by type)

### Why R2 doesn't need denies

If R2 also had deny sequences, the loop would still be prevented — but the design would lose
**symmetry**. With R2 as the unrestricted tagger, you can add new redistribution points
(e.g., R1, XR1, XR2) without rethinking the loop prevention. Any route that enters the
other protocol via any router gets tagged. R3 alone acts as the single gate. If both
routers denied, you'd need to coordinate who denies what, and a misconfiguration on one
side could break the scheme silently.

---

## 4. Scenario A: OSPF→IS-IS→OSPF Loop (172.16.1.0/24)

R1 injects 172.16.1.0/24 into OSPF as an E1 external route (`redistribute connected`). This
prefix tries to loop back into OSPF through the mutual redistribution.

### Flow diagram

```
                  Tag 100 stamped             Tag 100 matched,
                  by R2's OSPF→IS-IS          route BLOCKED by
                  route-map                   R3's ISIS_TO_OSPF
                  ┌─────┐                     deny 10 match tag 100
┌───┐            │ R2  │                          ┌───┐
│ R1│──OSPF──►   │ ║   │──IS-IS────────────────►  │ R3│
└───┘            │ ║   │                          └───┘
  │               └─────┘                           │
  │ 172.16.1.0/24  ▲                                │
  │ enters OSPF    │                                │
  │ as E1          │      ╔══════════════════╗      │
  │                │      ║  THE LOOP ATTEMPT ║     │
  └────────────────┘      ║  OSPF→IS-IS→OSPF  ║     │
                          ║  →IS-IS→OSPF→...  ║     │
                          ╚══════════════════╝      │
                                                    │
                                  ┌─────────────────┘
                                  │  "Tag 100 = was just in OSPF.
                                  │   Do NOT send back to OSPF."
                                  ▼
                                BLOCKED ✗
```

### Step-by-step trace

| Step | Router | Event | Route's Tag |
|------|--------|-------|-------------|
| 1 | **R1** | `redistribute connected metric-type 1 subnets` under `router ospf 1`. 172.16.1.0/24 enters OSPF as type E1 | *(none)* |
| 2 | **R2** | Learns via OSPF (`O E1`). `OSPF_TO_ISIS permit 20 match route-type external type-1` matches. Stamps **tag 100** and redistributes into IS-IS | **tag 100** |
| 3 | **R3** | Learns via IS-IS. `ISIS_TO_OSPF` route-map is evaluated: | tag 100 |
| 4a | **R3** *(no loop prevention)* | `ISIS_TO_OSPF permit 20` matches (no deny sequence). Stamps **tag 200**, redistributes into OSPF. R2 sees the route in OSPF from R3, redistributes it back to IS-IS with tag 100. R3 picks it up from IS-IS again, sends it back to OSPF. **Loop** | tag 200 → tag 100 → tag 200 → … |
| 4b | **R3** *(loop prevention active)* | `ISIS_TO_OSPF deny 10 match tag 100` fires first. The route carries tag 100 — the **deny matches** and the route is dropped. Permit sequence 20 is never reached. **Loop stopped** | — |

### Verification on the running lab

```bash
! Confirm the route is absent from OSPF re-origination on R3
R3# show ip ospf database external 172.16.1.0
  ! Advertising Router must be 10.0.0.1 (R1) only
  ! If 10.0.0.3 (R3) also shows as an advertiser, the deny is not firing

! Confirm the route carries tag 100 in R2's IS-IS LSP
R1# show isis database R2.00-00 verbose | include 172.16.1.0
  ! Should show "Route Admin Tag: 100" beneath the prefix
```

---

## 5. Scenario B: IS-IS→OSPF→IS-IS Loop (10.200.0.2/32)

R2's Loopback10 (10.200.0.2/32) is an **IS-IS-only prefix** — it has `ip router isis SP`
configured but is **not in OSPF**. It originates natively in IS-IS. This prefix tries to
loop back into IS-IS through the mutual redistribution.

### Flow diagram

```
                   Tag 200 stamped              Tag 200 matched,
                   by R2's IS-IS→OSPF           route BLOCKED by
                   route-map                    R3's OSPF_TO_ISIS
                   ┌─────┐                     deny 10 match tag 200
┌───┐             │ R2  │                          ┌───┐
│R2 │──IS-IS◄───  │ ║   │◄──OSPF────────────────  │ R3│
│Lo10│            │ ║   │                          └───┘
└───┘            └─────┘                           │
  10.200.0.2/32   │                                 │
  native IS-IS    │      ╔══════════════════╗       │
  (not in OSPF)   │      ║  THE LOOP ATTEMPT ║      │
                  │      ║  IS-IS→OSPF→IS-IS ║      │
                  │      ║  →OSPF→IS-IS→...  ║      │
                  │      ╚══════════════════╝       │
                  │                                 │
                  └─────────────────────────────────┘
                                   │
                   "Tag 200 = was just in IS-IS.
                    Do NOT send back to IS-IS."
                                   ▼
                                 BLOCKED ✗
```

### Step-by-step trace

| Step | Router | Event | Route's Tag |
|------|--------|-------|-------------|
| 1 | **R2** | 10.200.0.2/32 exists in R2's IS-IS L2 LSP natively. It is a **native IS-IS prefix** — never injected into OSPF | *(none)* |
| 2 | **R2** | `ISIS_TO_OSPF permit 10` matches all IS-IS routes. Stamps **tag 200**, sets metric 20, and redistributes into OSPF as an E2 Type-5 LSA | **tag 200** |
| 3 | **R3** | Learns via OSPF (`O E2` with tag 200). `OSPF_TO_ISIS` route-map is evaluated | tag 200 |
| 4a | **R3** *(no loop prevention)* | `OSPF_TO_ISIS permit 20/30/40` matches (OSPF E2). Stamps **tag 100**, redistributes into IS-IS. R2 sees 10.200.0.2/32 in IS-IS from R3 (with tag 100), redistributes it back to OSPF with tag 200. R3 picks it up, sends it back to IS-IS. **Loop** | tag 100 → tag 200 → tag 100 → … |
| 4b | **R3** *(loop prevention active)* | `OSPF_TO_ISIS deny 10 match tag 200` fires first. The route carries tag 200 — the **deny matches** and the route is dropped. Permit sequences are never reached. **Loop stopped** | — |

### Verification on the running lab

```bash
! Confirm R3's IS-IS LSP does NOT contain 10.200.0.2/32
R1# show isis database R3.00-00 verbose | include 10.200.0.2
  ! Must return NO output — the prefix must be absent from R3's LSP

! If it IS present, the OSPF_TO_ISIS deny is not working
R1# show isis database R3.00-00 verbose
  ! Look for 10.200.0.2/32 with "Route Admin Tag: 100"
  ! If present with tag 100, the deny 10 match tag 200 is misfiring
  ! (probably because the deny sequence is not sequence 10, or match tag is wrong)

! Confirm R3's route-map shows the deny sequence
R3# show route-map OSPF_TO_ISIS
route-map OSPF_TO_ISIS, deny, sequence 10
  Match clauses:
    tag 200
  ...
```

---

## 6. Tag State Machine

A route's tag changes as it crosses protocol boundaries. The state machine shows
which tag values are valid at each stage:

```
                    ┌──────────────────┐
                    │  OSPF domain     │
                    │  Tag: (none)     │
                    └────────┬─────────┘
                             │
               R2 redistributes OSPF→IS-IS
                             │ set tag 100
                             ▼
                    ┌──────────────────┐
                    │  IS-IS domain    │
                    │  Tag: 100        │ ← "I came from OSPF"
                    └────────┬─────────┘
                             │
               R3 considers IS-IS→OSPF
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
            deny 10 matches       No deny (broken)
            tag 100 — BLOCK       Route enters OSPF
                    │             Tag: 200
                    │                  │
                    │                  ▼
                    │          R2 sees in OSPF again
                    │          Redistributes OSPF→IS-IS
                    │          Tag: 100 again
                    │                  │
                    │                  ▼
                    │          LOOP CONTINUES
                    │          Until CPU/SPF exhaustion
                    ▼
              LOOP STOPPED
```

The pattern is invariant:

```
Origin protocol → First crossing (tag X) → Other protocol
    → Re-entry attempt → deny match tag X → BLOCKED
```

The tag value (X = 100 for OSPF, X = 200 for IS-IS) identifies which protocol the route
**most recently crossed from**. The deny checks that tag and refuses the return journey.

---

## 7. What Happens When Loop Prevention Is Missing

### Symptom 1: Duplicate LSAs

```
R2# show ip ospf database external 10.200.0.2

  LS Type: AS External Link
  Link State ID: 10.200.0.2
  Advertising Router: 10.0.0.2    ← R2 originating (correct, original redistribution)
  ...
  External Route Tag: 200

  LS Type: AS External Link        ← DUPLICATE
  Link State ID: 10.200.0.2
  Advertising Router: 10.0.0.3    ← R3 re-originating (LOOP)
  ...
  External Route Tag: 200
```

### Symptom 2: Route Flapping

```
R1# show ip route 10.200.0.2
  ! First check:
  O E2 10.200.0.2/32 [110/20] via 10.1.12.2
  ! Five seconds later:
  O E2 10.200.0.2/32 [110/40] via 10.1.13.3
  ! Five seconds later:
  O E2 10.200.0.2/32 [110/20] via 10.1.12.2
```

The metric doubles every loop iteration because each crossing adds the redistribution metric.

### Symptom 3: CPU Saturation

```
R2# show processes cpu | include OSPF|ISIS
OSPF Router    20%   →    85%   →    90%   →  ...
ISIS SPF       10%   →    45%   →    55%   →  ...
```

Both SPF (OSPF) and SPD (IS-IS) fire on every LSA/LSP update, creating a positive
feedback loop that saturates the control plane.

### Symptom 4: BGP Instability

BGP routes whose next-hop resolves through the flapping IGP prefix re-verify reachability
on every IGP change. iBGP sessions may flap if the loopback route they depend on keeps
changing:

```
R1# show ip bgp summary | include 10.0.0.2
  BGP neighbor is 10.0.0.2,  vrf default
  ...   Idle (Admin)  ...   Idle (Admin)  ...   Established
```

### Fixing the loop

```bash
! Add the missing deny sequence on the loop protector (R3)
route-map OSPF_TO_ISIS deny 10
 match tag 200
!
! Ensure the deny is sequence 10 (before all permit sequences)
route-map ISIS_TO_OSPF deny 10
 match tag 100
```

After adding the denies, the duplicate LSA disappears within one OSPF LSA refresh
interval (default 30 minutes, or flush immediately by clearing the OSPF process on R3
if maintenance allows).

---

## 8. Verification Commands Reference

### Confirm tag is stamped at redistribution

| Command | What to look for |
|---------|-----------------|
| `R1# show isis database R2.00-00 verbose` | `Route Admin Tag: 100` beneath OSPF-redistributed prefixes |
| `R1# show ip route 10.200.0.3` | `Tag 200` on IS-IS→OSPF redistributed routes |
| `R2# show ip ospf database external 10.200.0.3` | `External Route Tag: 200`, `Metric Type: 2`, `Metric: 20` |

### Confirm loop prevention is working

| Command | What to look for |
|---------|-----------------|
| `R1# show isis database R3.00-00 verbose` | **NO** entry for 10.200.0.2/32 in R3's LSP (deny blocked re-entry) |
| `R1# show ip ospf database external 10.1.14.0` | Advertising Router **10.0.0.1 only** (R3 not re-advertising) |
| `R3# show route-map OSPF_TO_ISIS` | `deny, sequence 10` with `match tag 200` present |
| `R3# show route-map ISIS_TO_OSPF` | `deny, sequence 10` with `match tag 100` present |

### Diagnose a loop

| Command | What to look for |
|---------|-----------------|
| `show ip route <prefix>` | Metric changing on successive checks; next-hop alternating between routers |
| `show ip ospf database external <prefix>` | Same prefix advertised by two different advertising routers |
| `show isis database <router> verbose` | Prefix appearing in LSP with tag from wrong origin (e.g., IS-IS prefix with tag 100 in R3's LSP) |
| `show processes cpu \| include OSPF\|ISIS` | SPF/SPD CPU percentage climbing steadily |
| `clear ip route *` | Temporary symptom relief (loops resume after next redistribution cycle) |

### Key exam tips

- **`verbose` vs `detail`** — `show isis database ... verbose` is required to see route
  tag sub-TLVs. The `detail` keyword hides them.
- **OSPF refreshes every 30 min** — if you fix a loop mid-session, the duplicate LSA
  might persist until the next refresh. Use `clear ip ospf redistribution` to flush
  immediately in a lab.
- **"Policy routing matches" is a PBR counter** — `show route-map` shows this as 0 for
  redistribution route-maps. It is **not** evidence that the route-map is not matching.
  Use the IS-IS LSP and OSPF database as ground truth.
- **Implicit deny** — if you add a deny sequence but miss one route type class (e.g.,
  you permit E1 and internal but forget E2), the E2 routes silently fall through the
  implicit deny and are dropped. Always verify redistributed prefixes appear in the
  target protocol's database after applying a route-map change.
