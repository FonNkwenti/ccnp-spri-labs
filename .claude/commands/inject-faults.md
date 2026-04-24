---
description: Generate Netmiko fault-injection scripts for a lab's troubleshooting scenarios
argument-hint: <topic-slug>/<lab-id>
---

You are generating fault-injection scripts for: `$ARGUMENTS`

If `$ARGUMENTS` is empty or not of the form `<topic-slug>/<lab-id>`, ask the user which lab to target and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/workbook.md` does not exist, warn that the workbook is missing and suggest running `/build-lab $ARGUMENTS` first. Ask whether to proceed anyway.
2. If `labs/$ARGUMENTS/workbook.md` exists but has no troubleshooting scenarios section (Section 9 or equivalent), warn that fault injection requires defined fault scenarios. Ask whether to proceed anyway.
3. If `labs/$ARGUMENTS/workbook.md` exists but has no Console Access Table, warn that Netmiko needs console port mappings to connect to devices. Ask whether to proceed anyway.
4. If `labs/$ARGUMENTS/scripts/fault-injection/` already contains scripts, warn that re-running will overwrite them and confirm.

Then read `.agent/skills/fault-injector/SKILL.md` and execute it for `$ARGUMENTS`.

Note: `/build-lab` and `/build-topic` dispatch the `fault-injector` skill automatically at Step 7 of `lab-assembler`. Use this command only when you need to regenerate fault scripts independently — for example, after adding new troubleshooting scenarios to an existing workbook.
