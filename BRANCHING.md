# Branching Strategy

This project (and the shared skills submodule it depends on) follows a **trunk-based
default with branches reserved for risk**. The goal is simple: keep day-to-day lab
work on `master` so progressive lab chains stay coherent, and isolate anything that
might be abandoned or that touches many topics at once on a feature/experiment branch.

---

## The Rule

**Default to `master`. Branch only when the change is cross-cutting or might be abandoned.**

### On `master` directly

- `/build-lab` runs — single-lab builds, including capstones.
- Lab fixes discovered during EVE-NG deployment and testing (phantom commands,
  wrong syntax, task ordering bugs, ambiguity).
- Skill submodule pointer bumps after a skill change has been merged in the
  submodule's own repo.
- Documentation and index updates (`STATUS.md`, `README.md`, `memory/progress.md`).
- Anything that touches one topic and is small enough to revert with a single
  `git revert <sha>` if it turns out wrong.

### On a branch

Use a branch when **at branch-creation time** you can honestly answer "yes" to any
of these:

- Will this touch multiple topics or rewrite shared infrastructure (specs, builder
  skills, baseline conventions)?
- Might I abandon this in a week?
- Do I want a single revert handle (one merge commit) instead of a chain of commits
  scattered across trunk?

If "yes" to any → branch.

If "no" to all → trunk. Don't branch to *defer* a decision; that's how branches turn
into zombies.

---

## Branch Naming

Two prefixes. That's it.

| Prefix         | Meaning                                                | Example                  |
| -------------- | ------------------------------------------------------ | ------------------------ |
| `experiment/`  | Speculative. May be abandoned. `git branch -D` is OK. | `experiment/xr-retrofit` |
| `feat/`        | Definitely shipping, but big enough to want a single   | `feat/xr-mode-flag`      |
|                | merge commit as a revert handle.                       |                          |

No `build/<lab>` or `fix/<lab>` prefixes — those changes go on trunk.

### The kill-date tripwire

Every `experiment/` branch's **first commit message** must include a kill-date:

```
experiment(xr-retrofit): initial spike on dual-stack XR support

Kill-date: 2026-06-01 — abandon if not merged by then.
```

This forces a go/no-go decision instead of letting the branch drift for weeks.
The XR retrofit ran for ~3 weeks because nothing forced the conversation; a
kill-date in the commit message gives future-you (or the next session) a clear
prompt to either land it or delete it.

`feat/` branches don't need kill-dates — the intent to ship is already declared.

---

## Submodule Workflow (`.agent/skills`)

The `.agent/skills/` directory is a **git submodule** pointing at
`cisco-lab-skills-eve-ng` — a separate repository that other Cisco lab projects
also pull from. Changes to skills are inherited by every project that pulls the
submodule. **Treat the submodule's `main` branch as a published API.**

### Trunk vs. branch in the submodule

The same rule applies inside the submodule, but with a higher bar — because
submodule trunk is shared:

- **Submodule trunk (`main`):** mature skill updates, bug fixes, documented
  conventions. Once committed and pushed, any project that runs
  `git submodule update --remote` will receive it.
- **Submodule branches (`experiment/...`, `feat/...`):** speculative skill
  changes, work-in-progress builder behavior, anything you don't want other
  projects to inherit yet.

### The dual-repo dance for cross-cutting features

When a feature spans both labs and skills (the XR retrofit was a textbook
example: it changed `lab-assembler` *and* mutated lab specs), branch in **both
repos** with the same name:

```
parent repo:    git checkout -b experiment/xr-retrofit
submodule:      cd .agent/skills && git checkout -b experiment/xr-retrofit
```

Work happens on the submodule branch. The parent branch tracks the submodule
pointer to that branch. When the experiment lands:

1. Merge the submodule branch into submodule `main`, push.
2. In the parent branch, bump the submodule pointer to the new `main` SHA.
3. Merge the parent branch into parent `master`, push.

When the experiment is abandoned:

1. `git branch -D experiment/xr-retrofit` in the parent.
2. `cd .agent/skills && git push origin --delete experiment/xr-retrofit`
   (and locally `git branch -D` it).

No skill changes leak into the shared trunk; no other project inherits the
half-baked work.

### The "submodule trunk is published API" corollary

Because other projects auto-pull from submodule `main`, **never push directly
to submodule `main` from a speculative session**. The flow is:

```
submodule branch  →  PR/review/test  →  submodule main  →  parent pointer bump
```

If you find yourself committing directly to submodule `main` for "just a quick
fix," ask whether other projects would want that fix today. If not, branch.

---

## Merging

- **`feat/` branches:** merge with `--no-ff` so there's a single merge commit
  to revert if needed.
- **`experiment/` branches that succeed:** treat as `feat/` at merge time —
  rename or just merge with `--no-ff`.
- **`experiment/` branches that fail:** `git branch -D` and walk away. No
  merge, no commit, no trace on trunk.
- **Rebase before merging** if the branch has been open more than a few days,
  to keep `STATUS.md`, `baseline.yaml`, and `README.md` index files conflict-free.

---

## Anti-Patterns

- **Branch-per-lab.** Progressive labs chain `lab-N/initial-configs/` from
  `lab-(N-1)/solutions/` on trunk. Per-lab branches force you to replay every
  upstream solution edit into every downstream branch — more time merging than
  building.
- **Branching to defer a decision.** If you don't know whether something should
  ship, don't start a branch as a hedge. Decide first, then branch (or don't).
- **Long-lived experiment branches with no kill-date.** Three weeks of XR
  retrofit happened because nothing forced go/no-go. Kill-dates fix this.
- **Pushing speculative skill changes to submodule `main`.** Other projects
  pull from there. Use a submodule branch.
- **Mixing trunk lab-fixes and feature work in the same session.** Finish the
  fix on trunk, commit, *then* `checkout -b` for the feature.

---

## Quick Reference

```
$ # Lab fix during testing (phantom command in workbook)
$ git checkout master
$ # ...edit files...
$ git commit -m "fix(mpls/lab-03): correct mpls te tunnels show command syntax"

$ # Cross-cutting experiment (touches skills + multiple specs)
$ git checkout -b experiment/xr-retrofit
$ cd .agent/skills && git checkout -b experiment/xr-retrofit && cd ../..
$ # ...work...
$ # If abandoned: git branch -D in both repos, done.
$ # If shipped: merge submodule branch first, bump pointer, merge parent branch.

$ # New builder feature, definitely shipping
$ git checkout -b feat/xr-mode-flag
$ # ...work, merge with --no-ff when ready...
```
