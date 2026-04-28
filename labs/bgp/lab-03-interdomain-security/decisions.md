## Model gate — 2026-04-27
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions

### MD5 password `CISCO_SP` for R5↔R6
The key string is intentionally simple and consistent across the topology to aid learning.
Production deployments should use complex, randomly generated strings stored in a secrets manager.

### maximum-prefix modes differ by session type
- R5↔R6 uses `warning-only` because R6 is a trusted SP peer where an early warning is
  sufficient — the session should not drop on threshold breach.
- R2↔R1 uses `restart 5` because R1 is a customer CE; a route leak from CE must trigger
  a circuit-breaker. The 5-minute restart window is a reasonable recovery window that
  prevents immediate re-flood while allowing auto-recovery.

### R3 does not get maximum-prefix in Task 3
The baseline.yaml objectives specify `maximum-prefix 100 restart 5` on R2↔R1 only.
R3↔R1 (backup path) is left without maximum-prefix to illustrate that the control
must be applied per-session, not globally — a deliberate teaching point.

### R4 unchanged from lab-02
R4 has no eBGP sessions in this lab's scope. All security controls target eBGP only.
iBGP sessions within AS 65100 are not hardened in this lab.
