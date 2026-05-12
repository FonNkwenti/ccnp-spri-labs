## Model gate — 2026-05-09
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Workbook contract gate — 2026-05-09
- All 11 sections present
- 8 tasks covering IS-IS NSF, BGP GR, live GR test, contrast without GR, IS-IS NSR, BGP NSR, NSF/NSR comparison, and asymmetric GR troubleshooting (Task 8 / Ticket 1 guided)
- 3 troubleshooting tickets: Ticket 1 = R1 missing nsf ietf, Ticket 2 = R5 missing bgp graceful-restart, Ticket 3 = R4 missing nsf ietf
- Topology ASCII and link reference table match solutions
- Device inventory, cabling, and console access table present
- Base config pre-loaded/not pre-loaded split matches initial-configs vs solutions delta
- Outcome: PASS

## Platform refactor — 2026-05-12
- Change: All devices switched from iosv to csr1000v (IOS-XE)
- Interface naming: Gi0/X → GigabitEthernet1/2/3/4 per CSR1000v convention
- IS-IS GR (`nsf ietf`): Upgraded from conceptual reference to **live configuration**
  (CSR1000v 17.03.05 supports the command, unlike IOSv 15.9)
- NSR (`nsr`/`bgp nsr`): Confirmed **rejected** on CSR1000v (same as IOSv) — remains conceptual
- Files updated: solutions/*.cfg, initial-configs/*.cfg, workbook.md (all sections),
  topology/README.md, meta.yaml, README.md
- Model gate: PASS (Intermediate, claude-sonnet-4-6)

## Design decisions — 2026-05-09

### BGP GR live test source/destination (Task 3 Part B)
R2 pings 192.0.2.1 (R5 Lo1) via iBGP from R1 or R3. R1 and R3 advertise 192.0.2.0/24
into the iBGP mesh with next-hop-self. This avoids the lab-00 lesson: R5 has no IS-IS
and cannot source pings to most of the SP core without static routes. Using R2 as the
ping source ensures the test path traverses the GR-protected iBGP routes.

### NSR scope: R1 only
NSR (IS-IS `nsr` and BGP `bgp nsr`) is configured on R1 only. IOSv accepts the commands
but provides no functional standby-RP behavior. Limiting NSR to R1 contains the behavioral
gap documentation to one device and keeps the exam intent clear: the student configures NSR,
observes the IOSv limitation, and understands the dual-RP requirement without confusion from
seeing the same "no effect" on all four core routers.

### BGP GR state string — live validation needed
The workbook references `BGP state = Active (GR)` in the expected output for Task 3 Part B.
This string was inferred from RFC 4724 behavior descriptions. IOSv 15.9(3)M6 may render
the state differently (e.g., `Idle (GR)`, `Active`, or a separate `GR state:` field).
Validate on a live lab and update the expected-output block in Task 3 Part B accordingly.

### Troubleshooting ticket fault choice
Each ticket removes one GR command from a different router (R1, R5, R4) to reinforce that
GR is cooperative — any single missing side breaks the protection for that pair. Ticket 1
targets R1 (an SP edge router whose helper role is non-obvious), Ticket 2 targets R5 (the
external CE — often overlooked), and Ticket 3 targets R4 (a pure core router that students
might assume is less important for the eBGP GR path).
