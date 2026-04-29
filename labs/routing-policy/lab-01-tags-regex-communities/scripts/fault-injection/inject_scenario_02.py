#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — IS-IS to OSPF Redistribution Removed on R2

Target:     R2 (redistribution point — OSPF process 1 / IS-IS SP)
Injects:    Removes `redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF`
            from router ospf 1 on R2, severing IS-IS route injection into OSPF.
Fault Type: Missing Redistribution Statement

Result:     IS-IS routes disappear from `show ip route ospf` on R1 and R3.
            Prefixes learned only via IS-IS (e.g. R4 loopbacks reachable through
            IS-IS) become unreachable from OSPF-only paths.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01 -> routing-policy -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router ospf 1",
    "no redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF",
    "exit",
]

# Pre-flight: verify redistribution is present under OSPF process 1.
PREFLIGHT_CMD = "show running-config | section router ospf 1"
# Fault already active if the redistribute line is gone; detect by absence below.
PREFLIGHT_FAULT_MARKER = "no redistribute isis"   # will never appear in running-config
# Known-good marker: redistribution present.
PREFLIGHT_SOLUTION_MARKER = "redistribute isis SP level-2 subnets route-map ISIS_TO_OSPF"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Either the lab is not in solution state, or the fault is already active.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    # No reliable fault marker to check for a removal-type fault; solution marker
    # absence is sufficient to detect already-injected state.
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
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

    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
