#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- R3 Stops Receiving IPv4 NLRIs from R1

Target:     R1 (eBGP neighbor 10.1.13.2 toward R3)
Injects:    Removes `neighbor 10.1.13.2 activate` from the IPv4 unicast
            address-family on R1, so BGP opens the session to R3 but does
            not negotiate IPv4 unicast NLRI exchange.
Fault Type: Missing neighbor activate (Address-Family Misconfiguration)

Result:     R1-R3 eBGP session stays Established but no IPv4 NLRIs are
            exchanged; R3 stops seeing 192.168.1.0/24 and any other
            prefixes that R1 would advertise.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00 -> bgp-dual-ce -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router bgp 65001",
    "address-family ipv4",
    "no neighbor 10.1.13.2 activate",
    "exit-address-family",
]

# Pre-flight: read BGP running config on R1 to verify known-good state.
PREFLIGHT_CMD = "show running-config | section router bgp"
# If this string is already present -> fault already injected, bail out.
# For a remove-only fault, no new line is added; use a sentinel that can
# never appear in a legitimate IOS BGP config to avoid false positives.
PREFLIGHT_FAULT_MARKER = "neighbor 10.1.13.2 activate __FAULT_INJECTED__"
# If this string is absent -> not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.13.2 activate"

POST_INJECT_COMMANDS = ["clear ip bgp 10.1.13.2 soft out"]


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears already injected. Restore with apply_solution.py.")
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
        print("[*] Triggering outbound soft-reset to propagate change ...")
        conn.send_command(POST_INJECT_COMMANDS[0])
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
