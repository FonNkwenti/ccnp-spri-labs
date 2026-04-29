#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — FlowSpec NLRI Absent from R5's Table

Target:     R5 (PE West — address-family ipv4 flowspec, neighbor 10.1.57.7)
Injects:    Removes `neighbor 10.1.57.7 activate` and
            `neighbor 10.1.57.7 send-community both` from R5's
            address-family ipv4 flowspec configuration.
Fault Type: FlowSpec AF Neighbor Not Activated (NLRI exchange disabled)

Result:     R7's FlowSpec session toward R5 drops to Idle/Active for the
            flowspec AF. `show bgp ipv4 flowspec` on R5 returns an empty table
            even though the unicast session to R7 remains Established.
            The SSH-drop rule for 172.16.1.0/24 is never installed on R5.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-05-communities-flowspec -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4 flowspec",
    "no neighbor 10.1.57.7 activate",
    "no neighbor 10.1.57.7 send-community both",
    "exit-address-family",
]

# Pre-flight: verify R5 has the flowspec neighbor activated before injecting.
PREFLIGHT_CMD = "show running-config | section address-family ipv4 flowspec"
# Present only in the known-good (flowspec AF activated) state.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.57.7 activate"
# Removal-style fault: no unique string appears after injection.
# Use a sentinel that is never present in IOS running-config output.
PREFLIGHT_FAULT_MARKER = "__FAULT_02_ALREADY_INJECTED__"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print("[!] Pre-flight failed: fault already appears to be injected.")
        print("    Restore with apply_solution.py before re-injecting.")
        return False
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
