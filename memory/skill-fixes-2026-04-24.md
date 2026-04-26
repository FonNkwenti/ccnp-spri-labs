# Skill Submodule Fixes — Paste-Ready

Apply these edits inside the submodule at `.agent/skills/` (i.e., the
`cisco-lab-skills` repo). After all edits:

```bash
cd .agent/skills
git checkout -b fix/lab-assembler-drawio-path-meta-pycache
# apply edits below
git add -A && git commit -m "fix: consistent topology/ path, meta.yaml ownership, pycache cleanup"
git push origin fix/lab-assembler-drawio-path-meta-pycache
# then in the parent repo:
cd ../..
git submodule update --remote .agent/skills
git add .agent/skills && git commit -m "chore: bump skills submodule"
```

---

## Fix 1 — Consistent `topology/topology.drawio` placement

**Root cause:** Skill instructs drawio file at lab root but README at
`topology/README.md`. Haiku followed the letter of the rule and put the drawio
at root; Sonnet/Opus intuited the consistent layout. Make the skill consistent.

### Fix 1a: `drawio/SKILL.md` line 14

**File:** `.agent/skills/drawio/SKILL.md`

**Find:**
```
- **Topology Diagrams**: `labs/<topic>/lab-NN-<slug>/topology.drawio`
  - Use for network topologies, physical cabling, and logical connectivity.
```

**Replace with:**
```
- **Topology Diagrams**: `labs/<topic>/lab-NN-<slug>/topology/topology.drawio`
  - Use for network topologies, physical cabling, and logical connectivity.
  - The diagram lives inside the `topology/` subdirectory alongside `topology/README.md`.
```

### Fix 1b: `lab-assembler/SKILL.md` line 511

**File:** `.agent/skills/lab-assembler/SKILL.md`

**Find:**
```
## Task
Write Draw.io XML to:
  labs/<topic>/lab-NN-<slug>/topology.drawio
```

**Replace with:**
```
## Task
Write Draw.io XML to:
  labs/<topic>/lab-NN-<slug>/topology/topology.drawio

Create the `topology/` subdirectory if it does not exist. The drawio file MUST
live inside `topology/`, not at the lab root. Sibling file in the same folder:
`topology/README.md` (written in Step 5b).
```

### Fix 1c: `lab-assembler/SKILL.md` line 656 (meta.yaml file list)

**File:** `.agent/skills/lab-assembler/SKILL.md`

**Find:**
```
  files:
    - workbook.md
    - topology.drawio
    - topology/README.md
```

**Replace with:**
```
  files:
    - workbook.md
    - topology/topology.drawio
    - topology/README.md
```

### Fix 1d: `lab-assembler/SKILL.md` line 716 (summary step list)

**File:** `.agent/skills/lab-assembler/SKILL.md`

**Find:**
```
6. Dispatch drawio subagent to write `topology.drawio`.
7. Write `topology/README.md` with EVE-NG import/export instructions.
```

**Replace with:**
```
6. Dispatch drawio subagent to write `topology/topology.drawio` (inside the `topology/` subfolder).
7. Write `topology/README.md` with EVE-NG import/export instructions.
```

### Fix 1e: `lab-assembler/SKILL.md` — add post-write path assertion

**File:** `.agent/skills/lab-assembler/SKILL.md` — append to Step 5's Post-Write Checklist (around line 544)

**Find:**
```
## Post-Write Checklist (fix before confirming done)
- [ ] Every router cell uses mxgraph.cisco.routers.router shape
- [ ] Every router has a separate label cell
- [ ] Every edge has strokeColor=#FFFFFF
- [ ] Every interface endpoint has a standalone .N octet cell
- [ ] Legend present at bottom-right with black fill
```

**Replace with:**
```
## Post-Write Checklist (fix before confirming done)
- [ ] File written to `labs/<topic>/lab-NN-<slug>/topology/topology.drawio` — NOT to the lab root
- [ ] Every router cell uses mxgraph.cisco.routers.router shape
- [ ] Every router has a separate label cell
- [ ] Every edge has strokeColor=#FFFFFF
- [ ] Every interface endpoint has a standalone .N octet cell
- [ ] Legend present at bottom-right with black fill
```

---

## Fix 2 — meta.yaml ownership: lab-assembler writes, fault-injector does not

**Root cause:** `fault-injector/SKILL.md` Step 6 instructs the subagent to
write `meta.yaml` itself, including a hardcoded `agent: claude-sonnet-4-6`
and a fallback `agent: unknown`. When dispatched by lab-assembler, the
subagent overwrites the parent's provenance. Rule: the dispatcher owns
meta.yaml; the subagent only returns a list of files it created.

### Fix 2a: `fault-injector/SKILL.md` Step 6 — replace entirely

**File:** `.agent/skills/fault-injector/SKILL.md`

**Find (lines 76–93):**
```
--# Step 6: Update meta.yaml

Update provenance tracking for this lab.

- **If `meta.yaml` already exists** (lab-assembler wrote it): append to `updated[]`:
  ```yaml
  updated:
    - date: "[YYYY-MM-DD]"
      agent: claude-sonnet-4-6
      skill: inject-faults
      skill_version: "[date of .agent/skills HEAD]"
      files:
        - scripts/fault-injection/inject_scenario_01.py
        # ... all inject scripts generated
        - scripts/fault-injection/apply_solution.py
        - scripts/fault-injection/README.md
  ```
- **If `meta.yaml` does not exist** (standalone run on a pre-existing lab): create it with `created` fields set to today's date and `agent: unknown` to indicate provenance was not tracked at generation time, then add the fault-injection files to `created.files`.
```

**Replace with:**
```
--# Step 6: Report generated files (do NOT write meta.yaml)

The fault-injector skill MUST NOT write or modify `meta.yaml`. Provenance is
owned by the caller:

- **When dispatched by lab-assembler (default):** Return the list of generated
  files in your Output Confirmation. The parent `lab-assembler` run will fold
  those paths into `meta.yaml.created.files` using the parent agent's
  provenance. Do not touch meta.yaml.

- **When invoked standalone on a pre-existing lab (rare):** The invoking user
  or orchestrator is responsible for running `/tag-lab <lab-path>` after this
  skill completes. `/tag-lab` stamps the correct provenance and appends an
  `updated[]` entry with the real agent ID. Do not auto-write meta.yaml.

This rule prevents "subagent bleed" where the fault-injector's own identity
(`agent: claude-sonnet-4-6` or `agent: unknown`) overwrites the parent's
provenance record.
```

### Fix 2b: `fault-injector/SKILL.md` line 227 — remove meta.yaml step

**File:** `.agent/skills/fault-injector/SKILL.md`

**Find:**
```
6. Update `meta.yaml` (Step 6).
```

**Replace with:**
```
6. Report generated files to the caller per Step 6 — DO NOT write `meta.yaml`.
```

### Fix 2c: `lab-assembler/SKILL.md` Step 8 — pick up fault-injector files

**File:** `.agent/skills/lab-assembler/SKILL.md` line 631–639

**Find:**
```
--# Step 8: Write meta.yaml

After the fault-injector skill completes, write `meta.yaml` in the lab directory.

1. Get `skill_version`: run `git -C .agent/skills log --format="%ci" -1` and take the date portion (YYYY-MM-DD).
2. Get today's date (YYYY-MM-DD).
3. Glob all files created in this lab directory (recursive, relative paths).
4. Write `labs/<topic>/lab-NN-<slug>/meta.yaml`:
```

**Replace with:**
```
--# Step 8: Write meta.yaml

After the fault-injector subagent completes, lab-assembler owns meta.yaml.
The fault-injector does NOT write meta.yaml (see fault-injector/SKILL.md Step 6).
Collect the fault-injection file paths from the subagent's Output
Confirmation and include them in `created.files` below.

1. Get `skill_version`: run `git -C .agent/skills log --format="%ci" -1` and take the date portion (YYYY-MM-DD).
2. Get today's date (YYYY-MM-DD).
3. Glob all files created in this lab directory (recursive, relative paths).
   Exclude `__pycache__/` and `*.pyc` artifacts.
4. Write `labs/<topic>/lab-NN-<slug>/meta.yaml`:
```

### Fix 2d: `lab-assembler/SKILL.md` line 651 — generic agent placeholder

**File:** `.agent/skills/lab-assembler/SKILL.md`

**Find:**
```
  agent: claude-sonnet-4-6
  skill: lab-assembler
```

**Replace with:**
```
  agent: [CURRENT_AGENT_ID]   # e.g. claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5-20251001
  skill: lab-assembler
```

---

## Fix 3 — Don't litter `__pycache__/` during py_compile

**Root cause:** `python3 -m py_compile file.py` always drops a `__pycache__/`
directory next to the file. Neither skill tells the agent to clean up after.
Switch to the in-process idiom that does not write cache files, OR clean up
after running.

### Fix 3a: `fault-injector/SKILL.md` line 74

**File:** `.agent/skills/fault-injector/SKILL.md`

**Find:**
```
- [ ] Run `python3 -m py_compile` on every generated `.py` file — fix any SyntaxError before proceeding
```

**Replace with:**
```
- [ ] Syntax-check every generated `.py` file WITHOUT creating cache files. Use one of:
  - `python3 -c "import ast, sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]" inject_scenario_01.py ...`  (preferred — no filesystem side effects)
  - OR `python3 -m py_compile *.py && rm -rf __pycache__ scripts/fault-injection/__pycache__`  (acceptable — but MUST include the rm)
  Fix any SyntaxError before proceeding. Never leave `__pycache__/` directories in the lab package.
```

### Fix 3b: `lab-assembler/SKILL.md` line 575

**File:** `.agent/skills/lab-assembler/SKILL.md`

**Find:**
```
**Validate:** Run `python3 -m py_compile setup_lab.py` — fix any SyntaxError before proceeding.
```

**Replace with:**
```
**Validate:** Syntax-check without writing cache files. Preferred:
```bash
python3 -c "import ast; ast.parse(open('setup_lab.py').read(), 'setup_lab.py')"
```
If you use `python3 -m py_compile setup_lab.py` instead, you MUST follow it
with `rm -rf __pycache__` — never leave `__pycache__/` in the lab package.
Fix any SyntaxError before proceeding.
```

### Fix 3c: Add a final-cleanup checkbox to lab-assembler's completion checklist

**File:** `.agent/skills/lab-assembler/SKILL.md` — in the Step 9/final validation
checklist (find the block near line 720 that enumerates build steps).

**Find:**
```
11. Write `meta.yaml` listing all created files (including `exam` and `devices` fields).
```

**Replace with:**
```
11. Write `meta.yaml` listing all created files (including `exam` and `devices` fields).
12. Final cleanup — remove any `__pycache__/` directories and `*.pyc` files from the lab package:
    ```bash
    find labs/<topic>/lab-NN-<slug> -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find labs/<topic>/lab-NN-<slug> -type f -name '*.pyc' -delete 2>/dev/null
    ```
    Verify with `find labs/<topic>/lab-NN-<slug> -name '__pycache__'` — must return empty.
```

---

## Fix 4 — Add `.gitignore` entry so pycache never gets committed

**File:** `.agent/skills/.gitignore` (and **also** the parent exam repo's
`.gitignore` — do both)

**Find:** (check current contents first with `cat .gitignore`)

**Append if not present:**
```
# Python bytecode cache — never commit into lab packages
__pycache__/
*.pyc
*.pyo
```

---

## Fix 5 — Update LESSONS_LEARNED.md

**File:** `.agent/skills/LESSONS_LEARNED.md` — append a new entry.

**Append:**
```markdown
## 2026-04-24 — Three-model comparison surfaced three skill-level bugs

From the OSPF lab-01 three-model build comparison (Haiku / Sonnet / Opus):

1. **Inconsistent drawio placement rule:** `lab-assembler` said drawio at lab
   root, but `topology/README.md` in a subfolder. Haiku followed the letter
   of the rule (wrong folder); Sonnet/Opus inferred the consistent layout.
   **Fix:** Both `drawio/SKILL.md` and `lab-assembler/SKILL.md` now specify
   `topology/topology.drawio` and Step 5 has a path assertion in its
   post-write checklist.

2. **meta.yaml subagent bleed:** `fault-injector/SKILL.md` Step 6 told the
   subagent to write meta.yaml directly, causing it to overwrite the parent's
   provenance with its own identity (Haiku and Sonnet builds both required
   manual overrides post-dispatch).
   **Fix:** Fault-injector no longer touches meta.yaml. lab-assembler owns
   meta.yaml; fault-injector returns its file list via Output Confirmation.

3. **`__pycache__` litter:** Both skills instructed `python3 -m py_compile`
   with no cleanup. Every build left `__pycache__/` directories in
   `scripts/fault-injection/` and sometimes at lab root.
   **Fix:** Syntax-check via `ast.parse` (no filesystem side effect) or
   follow py_compile with explicit `rm -rf __pycache__`. Final-cleanup step
   added to lab-assembler. `.gitignore` entries added.

Detection path: side-by-side review of three same-spec builds made the
pattern visible. Single-build review would have missed #1 and #3.
```

---

## Verification after applying

Back in the parent repo, pick one existing lab and re-run the skill against a
scratch copy to verify the fixes:

```bash
# From parent exam repo
git submodule update --remote .agent/skills
# Rebuild a sacrificial copy of lab-01 to verify
cp -r labs/ospf/lab-01-multiarea-ospfv2-opus labs/ospf/_verify-scratch
# Trigger a rebuild with /build-lab ospf/_verify-scratch and check:
#   - topology/topology.drawio exists (NOT topology.drawio at root)
#   - meta.yaml has the correct agent field for the model running
#   - No __pycache__/ directories anywhere under the lab folder
rm -rf labs/ospf/_verify-scratch
```

---

## Summary — files touched in the submodule

| File | Edits |
|---|---|
| `drawio/SKILL.md` | 1 (path) |
| `lab-assembler/SKILL.md` | 5 (path × 3, agent placeholder, cleanup step) |
| `fault-injector/SKILL.md` | 3 (Step 6 rewrite, Step 5 compile, Step 9 reference) |
| `.gitignore` | 1 (pycache entries) |
| `LESSONS_LEARNED.md` | 1 (append entry) |
| **Total** | 11 edits across 5 files |
