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
`discover_ports(host, lab_path)` at runtime against the EVE-NG REST API, which returns the current
`{node_name: port}` map. The `--lab-path` argument points to the EXISTING, ALREADY-IMPORTED lab
in EVE-NG — it is used exclusively for REST API port discovery. It does NOT generate, create, or
modify the `.unl` file.

--# Step 2: Generate Fault Injection Scripts

For each scenario (minimum 3 per lab), generate `scripts/fault-injection/inject_scenario_0N.py`.

Use `assets/inject_scenario_01_template.py` (and `_02`, `_03`) as base templates. Customise:
- `DEFAULT_LAB_PATH` — `"<topic>/<lab-slug>.unl"` (path within EVE-NG to the running lab)
- `DEVICE_NAME` — target device name (must match the node name in the EVE-NG lab)
- `FAULT_COMMANDS` list — from the scenario's solution section (the inverse of the fix)
- `PREFLIGHT_CMD` — `show` command whose output verifies pre-injection state
- `PREFLIGHT_SOLUTION_MARKER` — string present only in the known-good config
- `PREFLIGHT_FAULT_MARKER` — string present only after the fault is already injected
- Docstring describing exactly what fault is injected

Each script must:
1. Call `require_host(args.host)` to validate the `--host` argument (exits with code 2 if placeholder)
2. Call `discover_ports(host, args.lab_path)` to get the `{node_name: port}` map via EVE-NG REST API
3. Call `connect_node(host, port)` to open a Netmiko telnet session to the console port
4. Run `preflight(conn)` to verify the lab is in the known-good state before injecting
5. Apply fault commands via `conn.send_config_set(FAULT_COMMANDS)`
6. Save with `conn.save_config()` and always `conn.disconnect()` in a `finally` block

Exit codes: `0` success, `3` EVE-NG error, `4` pre-flight check failed.

--# Step 3: Generate apply_solution.py

Use `assets/apply_solution_template.py` as the base template. Customise:
- `DEFAULT_LAB_PATH` — same value as in the inject scripts
- `RESTORE_TARGETS` — list of all device names affected by any of the scenarios

The script reads solution configs from `solutions/[Device].cfg` (two directory levels above
`scripts/fault-injection/`, i.e. the lab root). It calls `discover_ports()` for port lookup
and supports `--reset` to run `erase_device_config()` before pushing configs.

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
- [ ] `DEFAULT_LAB_PATH` set correctly in all scripts (matches the running lab's path in EVE-NG)
- [ ] `RESTORE_TARGETS` in `apply_solution.py` covers every device touched by any scenario
- [ ] `PREFLIGHT_SOLUTION_MARKER` and `PREFLIGHT_FAULT_MARKER` are distinct, unambiguous strings
- [ ] Run `python3 -m py_compile` on every generated `.py` file — fix any SyntaxError before proceeding

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
Fault Injection: Scenario 0N — [SCENARIO_TITLE]

Target:     [DEVICE_NAME] ([INTERFACE])
Injects:    [ONE_LINE_FAULT_DESCRIPTION]
Fault Type: [e.g. Timer Mismatch / Passive Interface / AS Mismatch]
Result:     [OBSERVABLE_SYMPTOM]
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host

DEFAULT_LAB_PATH = "[TOPIC]/[LAB_SLUG].unl"
DEVICE_NAME = "[DEVICE_NAME]"
FAULT_COMMANDS = ["[FAULT_COMMAND_1]", "[FAULT_COMMAND_2]"]
PREFLIGHT_CMD = "show running-config [RELEVANT_SECTION]"
PREFLIGHT_FAULT_MARKER = "[STRING_THAT_SHOWS_FAULT_ALREADY_ACTIVE]"
PREFLIGHT_SOLUTION_MARKER = "[STRING_THAT_CONFIRMS_KNOWN_GOOD_STATE]"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 0N fault")
    parser.add_argument("--host", default="192.168.x.x")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)  # exits with code 2 if placeholder

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
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
2. Set `DEFAULT_LAB_PATH = "eigrp/lab-03-[name].unl"` in each inject script.
3. For each scenario, generate an `inject_scenario_0N.py` using the template from `assets/`.
4. Generate `apply_solution.py` with `RESTORE_TARGETS` covering all affected devices.
5. Generate `scripts/fault-injection/README.md` with `--host <eve-ng-ip>` in all commands.
6. Update `meta.yaml` (Step 6).
