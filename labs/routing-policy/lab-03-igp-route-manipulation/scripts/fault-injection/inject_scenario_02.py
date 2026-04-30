#!/usr/bin/env python3
"""
Fault Injection: Scenario 02. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R2"

# Fault: remove the correct seq 5 entry and add the typo (10.0.0.50/32).
# The mismatched prefix never matches XR1's Loopback0 in the L1 LSDB,
# so LEAK_L1_TO_L2 route-map produces no output for that prefix.
FAULT_COMMANDS = [
    "no ip prefix-list LEAK_FROM_L1 seq 5",
    "ip prefix-list LEAK_FROM_L1 seq 5 permit 10.0.0.50/32",
]

# Pre-flight: confirm LEAK_FROM_L1 has the correct seq 5 entry before injecting.
# Use "show ip prefix-list LEAK_FROM_L1" so output lines are narrow enough to
# distinguish "10.0.0.5/32" from "10.0.0.50/32" unambiguously.
PREFLIGHT_CMD = "show ip prefix-list LEAK_FROM_L1"
# Present only after fault is injected.  The extra "0" digit is the fault marker.
# Using "seq 5 permit 10.0.0.50/32" avoids false-match against the solution string
# (which is "seq 5 permit 10.0.0.5/32") because the trailing "0" makes it unique.
PREFLIGHT_FAULT_MARKER = "seq 5 permit 10.0.0.50/32"
# Present in the known-good state — the correct host route for XR1 Loopback0.
PREFLIGHT_SOLUTION_MARKER = "seq 5 permit 10.0.0.5/32"


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
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
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
