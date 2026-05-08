# CCNP SPRI (300-510) Lab Project

## Shared Context (Skills + Standards)

See .agent/skills/memory/CLAUDE.md for the foundation skills repository context.

## This Certification

- **Exam**: CCNP SPRI (300-510)
- **Audience**: Network engineers preparing for the 300-510 exam
- **Platform**: EVE-NG on Dell Latitude 5540 (Intel/Windows)

## Project Structure

See `.agent/skills/README.md` for the foundation toolkit documentation.

## Active Work

- See `memory/progress.md` for the current chapter plan and per-topic build status
- See `labs/` for existing lab content
- Run `git submodule status` to check skills version
- Run `/project-status` for a one-command summary of where we are

### Current Build Focus (as of 2026-05-01)

**srv6** (topic 10/11, build order #10) is the active topic. lab-00 (SRv6 IS-IS
Control Plane) is built; labs 01-04 remain unbuilt. All SRv6 labs use IOS-XRv 9000
**exclusively** — IOSv and CSR1000v do not support SRv6. The best reference lab for
structure and patterns is `segment-routing/lab-00-sr-foundations-and-srgb` (same
platform, same builder, same progressive chain).

All labs in a topic are progressive: lab-N's initial-configs chain from lab-(N-1)'s
solutions. Capstones (config + troubleshooting) use clean_slate and start from IP
addressing only.

## Branching

See `BRANCHING.md` for the full rule. Short version:

- **Default to `master`.** `/build-lab` runs, lab fixes from EVE-NG testing,
  skill submodule pointer bumps, and doc/index updates all go on trunk.
- **Branch only when the change is cross-cutting or might be abandoned.** Use
  `experiment/<name>` (must include a kill-date in the first commit message)
  or `feat/<name>` (definitely shipping, big enough to want a single revert
  handle).
- **Never branch-per-lab** — progressive labs chain solutions on trunk; per-lab
  branches turn into merge hell.
- **Cross-cutting features that touch `.agent/skills/` need parallel branches
  in both repos.** Submodule `main` is a published API — other Cisco lab
  projects inherit it. Speculative skill changes belong on a submodule branch
  with the same name as the parent branch, not on submodule `main`.

## Three-Phase Workflow (slash commands)

1. Phase 1 - Plan: Upload blueprint to blueprint/300-510/blueprint.md, then run /plan-exam
2. Phase 2 - Spec: Run /create-spec <topic> per topic (review after each)
3. Phase 3 - Build: Run /build-lab <topic>/<lab-id> one lab at a time (review after each)

Additional commands: /build-capstone, /tag-lab, /sync-skills, /project-status. All commands live in .claude/commands/ - they warn on missing prerequisites but let you proceed (advisory gating).

## Lab Fix Propagation Rule

When fixing a bug in any lab workbook (phantom command, wrong command, omission,
ambiguity, task ordering error), immediately check whether the same bug exists in the
capstone project(s) for that topic and fix them too.

**Procedure:**
1. After confirming a fix in the source lab, search the topic's capstone workbook(s)
   for the same command, task, or pattern.
2. If the bug is present in a built capstone, apply the identical fix there.
3. If no capstone exists yet for the topic, do nothing — the fix will be incorporated
   when the capstone is built.

Capstone locations follow the pattern `labs/<topic>/lab-NN-capstone-*/workbook.md`.
A topic may have both a config capstone and a troubleshooting capstone — check both.

## Command Compatibility Rule

Whenever a command fails at runtime (Invalid input, wrong syntax, platform rejection,
silent no-op) — during live lab work, apply_solution.py, workbook review, or
troubleshooting — do all of the following **without waiting to be asked**:

1. **Fix the command** in the immediate file.
2. **Search all built labs** across all topics (`labs/`) for the same command
   pattern and apply the identical fix. Do not limit the search to the current
   topic or only capstones — command bugs are cross-topic.
3. **Update `ios-compatibility.yaml`** in the skills submodule:
   - Mark the failed form as `fail` on the affected platform.
   - Add or update the correct form with `pass` and a `notes` entry that explains
     the platform difference and the correct syntax.
4. **Add a `LESSONS_LEARNED.md` entry** if the fix requires a non-obvious workaround
   (wrong keyword order, missing keyword, IOSv-specific syntax, etc.). Skip if the
   fix is already documented in `ios-compatibility.yaml` notes and is self-evident.
5. **Commit the submodule** (both `LESSONS_LEARNED.md` and `ios-compatibility.yaml`
   changes in one commit) and bump the parent repo's submodule pointer.

This rule fires on every command failure, every session. It is not optional and does
not require a user prompt.

## Common Commands

```bash
# Update skills to latest
git submodule update --remote .agent/skills
git add .agent/skills

# Run lab setup
python labs/<topic>/lab-NN-<slug>/setup_lab.py --host <eve-ng-ip>

# Run tests
pytest tests/ -v
```
