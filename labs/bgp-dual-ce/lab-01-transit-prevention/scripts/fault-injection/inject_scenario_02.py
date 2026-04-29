#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Route-Map Defined But Not Bound to Neighbor

Target:     R1 (BGP)
Injects:    Removes the `neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out`
            binding under address-family ipv4. The prefix-list and route-map
            objects remain defined and look correct in the running-config, but
            no policy is actually applied to the eBGP session, so the leak
            persists (10.200.1.0/24 still reaches R3 with AS-path 65001 65200).
Fault Type: Policy framework correct, attachment missing

Before running, ensure the lab is in the SOLUTION state.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router bgp 65001",
    "address-family ipv4",
    "no neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out",
    "exit-address-family",
]

PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.13.2 route-map TRANSIT_PREVENT_OUT out"
PREFLIGHT_FAULT_MARKER = "neighbor 10.1.13.2 route-map __FAULT_INJECTED__"

POST_INJECT_COMMANDS = ["clear ip bgp 10.1.13.2 soft out"]


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: scenario 02 already injected.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x", help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None)
    parser.add_argument("--skip-preflight", action="store_true")
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
            print(f"[!] No running lab found with {DEVICE_NAME}.", file=sys.stderr)
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
        print("[*] Forcing outbound policy refresh ...")
        for cmd in POST_INJECT_COMMANDS:
            conn.send_command(cmd)
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
