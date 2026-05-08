#!/usr/bin/env python3
"""
Fault Injection: Scenario 01. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00-srv6-control-plane -> srv6 -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host

DEVICE_NAME = "P2"
DEVICE_TYPE = "cisco_xr_telnet"

FAULT_COMMANDS = [
    "router isis CORE",
    " address-family ipv4 unicast",
    "  no segment-routing srv6",
    " !",
    " address-family ipv6 unicast",
    "  no segment-routing srv6",
    " !",
    "!",
    "commit",
]

PREFLIGHT_CMD = "show running-config router isis CORE"
PREFLIGHT_SOLUTION_MARKER = "segment-routing srv6"
PREFLIGHT_FAULT_MARKER = "no-preflight-fault-marker-x01"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if "segment-routing srv6" not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)

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
        conn = connect_node(host, port, device_type=DEVICE_TYPE)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
