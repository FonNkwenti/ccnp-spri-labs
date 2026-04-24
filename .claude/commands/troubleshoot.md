---
description: Diagnose and resolve a Cisco IOS/XE/XR network fault in an EVE-NG lab
argument-hint: <topic-slug>/<lab-id> and/or symptom description
---

You are running a structured troubleshooting session for: `$ARGUMENTS`

If `$ARGUMENTS` provides no lab path or symptom, ask the user which lab (under `labs/`) the fault is in and what the observed symptom is, then stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If no lab path is identifiable from `$ARGUMENTS`, ask the user to confirm which lab directory applies before connecting to any devices.
2. If `labs/<topic>/<lab-id>/workbook.md` exists, note any troubleshooting hints or known fault scenarios in Section 9 — reference these during diagnosis.
3. If the EVE-NG host is not reachable, warn before attempting device connections.

Then read `.agent/skills/cisco-troubleshooting-1/SKILL.md` and execute the four-phase methodology for `$ARGUMENTS`.

This command is for **active lab practice** — diagnosing a fault you are experiencing right now in EVE-NG. It is not for generating fault scripts (use `/inject-faults` for that).
