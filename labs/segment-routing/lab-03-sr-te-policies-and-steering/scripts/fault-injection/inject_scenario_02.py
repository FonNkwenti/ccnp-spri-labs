#!/usr/bin/env python3
"""
Fault Injection: Scenario 02. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-03 -> segment-routing -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host

DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "segment-routing",
    " traffic-eng",
    "  interface GigabitEthernet0/0/0/0",
    "   no affinity",
]
PREFLIGHT_CMD = "show segment-routing traffic-eng interface GigabitEthernet0/0/0/0"
# Solution marker: affinity IS configured (present before fault)
PREFLIGHT_SOLUTION_MARKER = "affinity"
# Fault marker: check solution marker is absent after fault; pre-flight uses
# the solution marker to confirm we are in a clean state before injecting.
PREFLIGHT_FAULT_MARKER = None  # removal fault — we check solution marker absence instead


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x")
    parser.add_argument("--lab-path", default=None, help="Lab .unl path (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        lab_path = find_open_lab(host, node_names=[DEVICE_NAME])
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICE_NAME}. Start all nodes first.", file=sys.stderr)
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
        print(f"[+] Fault injected on {DEVICE_NAME}.")
    finally:
        conn.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
