#!/usr/bin/env python3
"""
Fault Injection: Scenario 03. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00 -> routing-policy -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R1"

# Must enter address-family ipv4 because the neighbor knob lives there (R1.cfg line 66).
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.1.14.4 route-map FILTER_R4_IN in",
    "neighbor 10.1.14.4 route-map FILTER_R4_IN out",
    "exit-address-family",
]

# Use a pipe to keep output short — 'show ip bgp neighbors' without a pipe
# produces many screenfuls and can exceed Netmiko's read_timeout on slow
# EVE-NG telnet sessions even with terminal length 0 applied.
# On IOSv, the direction line reads: "Route map for incoming/outgoing
# advertisements is FILTER_R4_IN" — filter on the map name to capture it.
PREFLIGHT_CMD = "show ip bgp neighbors 10.1.14.4 | include FILTER_R4_IN"

# Present in solution state: route-map applied inbound.
PREFLIGHT_SOLUTION_MARKER = "incoming"

# Present only after the fault is injected: route-map applied outbound.
PREFLIGHT_FAULT_MARKER = "outgoing"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD, read_timeout=30)
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
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
        print("[*] Soft-resetting BGP inbound from 10.1.14.4 to activate fault ...")
        conn.send_command("clear ip bgp 10.1.14.4 soft in", read_timeout=30)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
