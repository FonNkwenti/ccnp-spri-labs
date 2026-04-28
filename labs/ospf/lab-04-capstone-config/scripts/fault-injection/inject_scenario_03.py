#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — Inter-Area Summary Missing on ABR

Target:     R2 (ABR — Area 0 / Area 1)
Injects:    Removes the 'area 1 range 172.16.0.0 255.255.248.0' summary
            from router ospf 1, and removes the 'area 1 range 2001:DB8:1::/48'
            summary from the OSPFv3 IPv6 address-family on R2.
Fault Type: Missing Inter-Area Route Summarization

Result:     R3, R4, and R5 see three individual /24 routes (172.16.1.0,
            172.16.2.0, 172.16.3.0) injected as separate Type-3 LSAs into
            the backbone instead of the single 172.16.0.0/21 aggregate.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-04 -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R2"

# Removes both the OSPFv2 and OSPFv3 area 1 range/summary commands.
FAULT_COMMANDS = [
    "router ospf 1",
    "no area 1 range 172.16.0.0 255.255.248.0",
    "exit",
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "no area 1 range 2001:DB8:1::/48",
    "exit-address-family",
    "exit",
]

# Pre-flight: Scenario 3 removes a config line, so the solution marker is
# the range command itself. The fault state is defined by its absence.
# PREFLIGHT_FAULT_MARKER is a sentinel that never appears in any running-config.
PREFLIGHT_CMD = "show running-config | section router ospf 1"
# Present only in the known-good (summarization enabled) state.
PREFLIGHT_SOLUTION_MARKER = "area 1 range 172.16.0.0 255.255.248.0"
# Sentinel: this string is never in the running-config.
PREFLIGHT_FAULT_MARKER = "__FAULT_03_ALREADY_INJECTED__"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: fault already appears to be injected.")
        print("    Restore with apply_solution.py before re-injecting.")
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
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
