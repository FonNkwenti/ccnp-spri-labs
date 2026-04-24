---
description: Create or update a Cisco topology diagram in Draw.io for a lab
argument-hint: <topic-slug>/<lab-id> or topology description
---

You are generating or updating a topology diagram for: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the user which lab or topology to diagram and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/` does not exist, warn that the lab folder is missing and confirm the target path before continuing.
2. If `labs/$ARGUMENTS/topology.drawio` already exists, warn that it will be overwritten and confirm.
3. If the topology is unchanged or near-identical to an adjacent lab (e.g. lab-01 shares the same devices and links as lab-00), warn that reuse may be more appropriate. Check whether `baseline.yaml` lists any topology changes for this lab — if not, suggest copying the adjacent diagram instead of generating a new one.

Then read `.agent/skills/drawio/SKILL.md` and execute it for `$ARGUMENTS`.

Note: `/build-lab` and `/build-topic` dispatch the `drawio` skill automatically at Step 5 of `lab-assembler`. Use this command only when you need to regenerate or update a diagram independently of a full lab build.
