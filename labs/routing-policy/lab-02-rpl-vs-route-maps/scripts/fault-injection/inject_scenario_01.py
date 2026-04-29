#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — XR1 Silent Route Drop

Target:     XR1 (IBGP neighbor-group — inbound route-policy)
Injects:    A broken child policy (no pass at end) is applied inbound on XR1's
            IBGP neighbor-group, replacing the working IBGP_IN policy.
Fault Type: BGP Route Policy Misconfiguration

Result:     All inbound IBGP routes are silently dropped on XR1. BGP sessions
            remain up but no prefixes are received. Peers show XR1 as
            established with 0 prefixes in the adj-rib-in.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-02-rpl-vs-route-maps -> routing-policy -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "XR1"
FAULT_COMMANDS = [
    "route-policy IBGP_IN_BROKEN",
    "  apply SET_LOCAL_PREF_BY_COMMUNITY",
    "end-policy",
    "commit",
    "router bgp 65100",
    " neighbor-group IBGP",
    "  address-family ipv4 unicast",
    "   route-policy IBGP_IN_BROKEN in",
    "  exit",
    " exit",
    "exit",
    "commit",
]

# Pre-flight: check BGP summary to confirm IBGP_IN is the active inbound policy.
PREFLIGHT_CMD = "show bgp ipv4 unicast summary"
# Match the applied form only — not the bare policy definition (which lingers after restore).
PREFLIGHT_FAULT_MARKER = "route-policy IBGP_IN_BROKEN in"
# If this string is absent in running-config → not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "IBGP_IN"


def preflight(conn) -> bool:
    # Check running-config for route-policy assignment to detect state.
    output = conn.send_command("show running-config formal | include route-policy IBGP")
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 01 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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
        conn = connect_node(host, port, device_type="cisco_xr_telnet")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
