---
name: fault-injector
description: Generates Python fault-injection scripts for lab troubleshooting scenarios using Netmiko. Use when the user asks to "inject faults", "generate troubleshooting scripts", "create fault scenarios", "add troubleshooting practice", or automatically after lab-assembler generates a workbook.
---

# Fault Injector Skill

Generates Python scripts that inject the troubleshooting scenarios defined in lab workbooks into the live lab environment. Enables students to set up fault conditions for exam-style troubleshooting practice without manual configuration.

-# Instructions

--# Step 1: Parse Inputs

Read from the lab directory:
1. `workbook.md` — extract troubleshooting scenarios from Section 9
2. From each scenario extract: **Scenario Number**, **Target Device**, **Fault Type**, **Commands to inject**

**Port discovery at runtime:** Console ports are NOT hardcoded in the scripts. Each script calls
`find_open_lab(host, node_names=[DEVICE_NAME])` to auto-discover which lab is currently running,
then passes the result to `discover_ports(host, lab_path)` for the `{node_name: port}` map.
The optional `--lab-path` argument lets users override auto-discovery when needed. Scripts must
NEVER hardcode a `DEFAULT_LAB_PATH` — lab paths vary across EVE-NG instances and .unl filenames.

--# Step 2: Generate Fault Injection Scripts

For each scenario (minimum 3 per lab), generate `scripts/fault-injection/inject_scenario_0N.py`.

**Capstone detection**: Check the lab slug. If it contains `capstone-troubleshooting`, use
`assets/inject_scenario_01_capstone_template.py` (and `_02`, `_03`) as base templates instead.
Capstone templates suppress all device name output in print statements so students cannot infer
which router is affected by reading terminal output during live lab runs. For all other labs,
use `assets/inject_scenario_01_template.py` (and `_02`, `_03`).

Customise:
- `DEVICE_NAME` — target device name (must match the node name in the EVE-NG lab)
- `FAULT_COMMANDS` list — from the scenario's solution section (the inverse of the fix)
- `PREFLIGHT_CMD` — `show` command whose output verifies pre-injection state
- `PREFLIGHT_SOLUTION_MARKER` — string present only in the known-good config
- `PREFLIGHT_FAULT_MARKER` — string present only after the fault is already injected
- Docstring containing only the scenario number and restore instruction — **never** fault type, target device, or expected symptom (those would tip off the student before they troubleshoot)

Each script must:
1. Call `require_host(args.host)` to validate the `--host` argument (exits with code 2 if placeholder)
2. Call `find_open_lab(host, node_names=[DEVICE_NAME])` to auto-discover the running lab path
3. Call `discover_ports(host, lab_path)` to get the `{node_name: port}` map via EVE-NG REST API
4. Call `connect_node(host, port)` to open a Netmiko telnet session to the console port
5. Run `preflight(conn)` to verify the lab is in the known-good state before injecting
6. Apply fault commands via `conn.send_config_set(FAULT_COMMANDS)`
7. Save with `conn.save_config()` and always `conn.disconnect()` in a `finally` block

**Never define `DEFAULT_LAB_PATH`.** Lab paths vary across EVE-NG instances. Auto-discovery
via `find_open_lab()` is required; `--lab-path` is an optional manual override only.

Exit codes: `0` success, `3` EVE-NG error, `4` pre-flight check failed.

--# Step 3: Generate apply_solution.py

Use `assets/apply_solution_template.py` as the base template. Customise:
- `RESTORE_TARGETS` — list of all device names affected by any of the scenarios

The script reads solution configs from `solutions/[Device].cfg` (two directory levels above
`scripts/fault-injection/`, i.e. the lab root). It calls `find_open_lab(host, node_names=RESTORE_TARGETS)`
to auto-discover the lab, then `discover_ports()` for port lookup. Supports `--reset` to run
`soft_reset_device()` (issues `default interface` + `no router` to clear running-config state without a
reload) before pushing configs, and `--node` to target a single device. Do NOT define `DEFAULT_LAB_PATH`.

--# Step 4: Generate scripts/fault-injection/README.md

Use `assets/README_template.md` as the base. Fill in:
- One section per scenario: scenario number, target device, command to run
- **Ops-only — do NOT include fault names or descriptions that reveal what is broken**
- Usage instructions for injecting and restoring
- Prerequisites (EVE-NG lab running with all nodes started, netmiko installed)

--# Step 5: Validate

- [ ] One inject script per scenario
- [ ] `apply_solution.py` restores all affected devices
- [ ] `README.md` lists all available scenarios
- [ ] All scripts are idempotent (safe to run multiple times)
- [ ] NO `DEFAULT_LAB_PATH` constant in any script — auto-discovery via `find_open_lab()` is used
- [ ] `find_open_lab` is imported from `eve_ng` in all scripts
- [ ] `--lab-path` defaults to `None` and is treated as optional override only
- [ ] `RESTORE_TARGETS` in `apply_solution.py` covers every device touched by any scenario
- [ ] `PREFLIGHT_SOLUTION_MARKER` and `PREFLIGHT_FAULT_MARKER` are distinct, unambiguous strings
- [ ] **No script docstring, banner, print, or preflight error message reveals the fault type, affected device/interface, or expected symptom** — students must discover these through troubleshooting, not by reading the script
- [ ] **Capstone labs only** (`capstone-troubleshooting` in lab slug): no inject script print statement references a router or device name — verify the `_capstone_template.py` variants were used, not the regular ones
- [ ] Syntax-check every generated `.py` file WITHOUT creating cache files. Use one of:
  - `python3 -c "import ast, sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]" inject_scenario_01.py ...`  (preferred — no filesystem side effects)
  - OR `python3 -m py_compile *.py && rm -rf __pycache__ scripts/fault-injection/__pycache__`  (acceptable — but MUST include the rm)
  Fix any SyntaxError before proceeding. Never leave `__pycache__/` directories in the lab package.

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

-# Output Structure

```
labs/<topic>/lab-NN-<slug>/
└── scripts/
    └── fault-injection/
        ├── README.md
        ├── inject_scenario_01.py
        ├── inject_scenario_02.py
        ├── inject_scenario_03.py
        └── apply_solution.py
```

-# Script Structure Reference

```python
#!/usr/bin/env python3
"""
Fault Injection: Scenario 0N. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host

DEVICE_NAME = "[DEVICE_NAME]"
FAULT_COMMANDS = ["[FAULT_COMMAND_1]", "[FAULT_COMMAND_2]"]
PREFLIGHT_CMD = "show running-config [RELEVANT_SECTION]"
PREFLIGHT_FAULT_MARKER = "[STRING_THAT_SHOWS_FAULT_ALREADY_ACTIVE]"
PREFLIGHT_SOLUTION_MARKER = "[STRING_THAT_CONFIRMS_KNOWN_GOOD_STATE]"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print("[!] Pre-flight failed: scenario appears already injected.")
        print("    Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 0N fault")
    parser.add_argument("--host", default="192.168.x.x")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)  # exits with code 2 if placeholder

    if args.lab_path:
        lab_path = args.lab_path
    else:
        lab_path = find_open_lab(host, node_names=[DEVICE_NAME])
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICE_NAME}. Start all nodes first.",
                  file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab '{lab_path}'.")
        return 3

    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

-# Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state (inject scripts only) |

-# Common Issues

--# workbook.md has no troubleshooting scenarios
- **Cause:** The workbook was generated without a Section 9, or scenarios were not written.
- **Solution:** Stop. Ask the user to add at least 3 troubleshooting scenarios to `workbook.md` Section 9 before running this skill. Use `assets/troubleshooting_scenarios_template.md` (from the `lab-assembler` assets) as a reference format.

--# EVE-NG port discovery fails (EveNgError)
- **Cause:** Lab is not running, the `.unl` file hasn't been imported yet, or `--host` is wrong.
- **Solution:** Ensure the lab is imported into EVE-NG and all nodes are started. Verify `--host` is the EVE-NG server IP, and `--lab-path` matches the path shown in the EVE-NG web UI (e.g. `ospf/lab-00-single-area-ospfv2.unl`).

--# Scenario fault commands are unclear
- **Cause:** The solution section in the workbook doesn't clearly show what was misconfigured.
- **Solution:** Derive the fault as the inverse of the solution: if the solution says `ip ospf hello-interval 10`, the fault is `ip ospf hello-interval 30`.

--# apply_solution.py restores wrong state
- **Cause:** `solutions/` configs were updated after the fault scripts were generated.
- **Solution:** Regenerate `apply_solution.py` after any workbook or solutions update.

-# Examples

User: "Generate fault injection scripts for EIGRP Lab 03."

Actions:
1. Read `labs/eigrp/lab-03-[name]/workbook.md` — extract 3 troubleshooting scenarios (target device, fault type, commands).
2. For each scenario, generate an `inject_scenario_0N.py` using the template from `assets/` — using `find_open_lab()` for lab discovery, NOT a hardcoded `DEFAULT_LAB_PATH`.
3. Generate `apply_solution.py` with `RESTORE_TARGETS` covering all affected devices.
4. Generate `scripts/fault-injection/README.md` with `--host <eve-ng-ip>` in all commands.
5. Report generated files to the caller per Step 6 — DO NOT write `meta.yaml`.
