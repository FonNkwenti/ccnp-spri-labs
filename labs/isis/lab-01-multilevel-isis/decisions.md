# Build Decisions — isis/lab-01-multilevel-isis

## Model gate — 2026-04-29

- Difficulty: Intermediate
- Running model: claude-opus-4-7
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Decision 1 — IS-IS commands marked unknown in ios-compatibility.yaml; treated as pass on IOSv

The `ios-compatibility.yaml` reference file does not contain entries for IS-IS commands
(`router isis`, `net`, `is-type`, `metric-style wide`, `ip router isis`, `isis circuit-type`,
etc.). All these commands are standard IOS IS-IS commands available since IOS 12.0 and are
fully supported on IOSv (IOS 15.9(3)M6). Treated as implicit `pass` on `iosv` for this lab.
No platform switch needed.

## Decision 2 — Explicit `isis circuit-type level-2-only` on the R2↔R3 backbone link

Without explicit `level-2-only` on R2 Gi0/1 and R3 Gi0/0, the inter-area link still works:
IS-IS will attempt an L1 adjacency (which fails due to area mismatch) and succeed with an L2
adjacency. However, the failed L1 attempts generate syslog noise and waste CPU cycles. Best
practice on production SP cores is always to be explicit. This also makes the lab more
instructive — Ticket 3 plants a `level-1` mis-configuration on this interface, and a student
who understands WHY the link is explicitly `level-2-only` can diagnose the fault faster.

## Decision 3 — R1 solution config is unchanged from lab-00

R1 is a pure L1 stub router in area 49.0001. Lab-01 adds no configuration to R1 — the ATT bit
mechanism installs the default route automatically when R2 promotes to L1/L2. This is
intentional and pedagogically important: the student must recognise that R1 requires NO changes
yet still gains inter-area reachability. Keeping R1's solution identical to lab-00 demonstrates
the zero-touch benefit of the ATT bit.

## Decision 4 — Three fault scenarios targeting distinct multilevel failure classes

Three ticket types selected to cover the three core multilevel IS-IS failure domains introduced
in this lab, each producing a visibly different symptom:

| Ticket | Fault class | Target | Fault | Primary symptom |
|--------|-------------|--------|-------|-----------------|
| 1 | NET area mismatch | R4 | Area field typo (49.0099 vs 49.0002) | R4 stuck in INIT with R3; R4/R5 routes missing from R1 |
| 2 | is-type misconfiguration | R2 | `is-type level-2-only` (no L1 capability) | R1↔R2 drops to INIT/DOWN; R1 loses ALL IS-IS routes |
| 3 | circuit-type mismatch | R2 Gi0/1 | `isis circuit-type level-1` on backbone link | R2↔R3 no L2 adjacency; inter-area routes and default route withdraw |

Ticket 1 mirrors the planted fault from lab-00 (area-ID typo) but targets a different device
and area, reinforcing the pattern without repetition. Tickets 2 and 3 are new: they address
`is-type` and `circuit-type` — the two knobs introduced in this lab that didn't exist in lab-00.

## Decision 5 — IP addressing convention for new links (10.1.XY.R format)

Links L3 and L4 follow the same IP scheme as L1 and L2: the subnet is 10.1.XY.0/24 where
X and Y are the lower router numbers on the link, and each router uses its own number as the
host octet. Specifically:
- L3 (R3↔R4, 10.1.34.0/24): R3=10.1.34.3, R4=10.1.34.4
- L4 (R3↔R5, 10.1.35.0/24): R3=10.1.35.3, R5=10.1.35.5

This convention was established in lab-00 and the ospf topic. Consistency across topics reduces
cognitive load during troubleshooting (the host octet is always the router's number).

## Decision 6 — R3 Loopback0 uses `isis circuit-type level-1` despite R3 being `is-type level-1-2`

R3's solution config contains `isis circuit-type level-1` on Loopback0. At first glance this may
look inconsistent — R3 is a `level-1-2` router, so why scope its loopback to L1?

This is intentional and correct for two reasons:

1. **Passive interfaces never send Hellos.** Because `passive-interface Loopback0` is set, the
   `circuit-type` line has no effect on adjacency formation. The loopback will never participate
   in Hello exchange at any level regardless of this setting.

2. **L1/L2 auto-injection propagates L1 prefixes into L2 LSDB automatically.** R3 floods its
   own L1-learned prefixes (including its loopback) into the L2 LSDB without any additional
   configuration. Setting `circuit-type level-1` on the loopback does not prevent this; it only
   affects which level of Hellos would be sent on that interface (moot here due to `passive`).

The alternative — `circuit-type level-1-2` — would be equally correct. The `level-1` setting
is preserved from the lab-00 solution (where all routers were L1-only) and left unchanged
because changing it would add noise to the config diff without functional benefit.
