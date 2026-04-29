#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Transit Filter Applied to the Wrong Session

Target:     R2 (BGP)
Injects:    Removes the transit-prevention route-map from the eBGP session
            toward R4 (10.1.24.2) and instead binds it outbound on the iBGP
            session toward R1 (10.0.0.1). Result: R2 stops sending non-customer
            prefixes to R1 over iBGP -- so R1 loses its view of 10.200.1.0/24.
            Meanwhile the eBGP session toward R4 is unfiltered, so the transit
            leak (10.100.1.0/24 reaching R4 via AS-path 65001 65100) persists.
Fault Type: Filter on wrong session (placement error)

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router bgp 65001",
    "address-family ipv4",
    "no neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out",
    "neighbor 10.0.0.1 route-map TRANSIT_PREVENT_OUT out",
    "exit-address-family",
]

PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.24.2 route-map TRANSIT_PREVENT_OUT out"
PREFLIGHT_FAULT_MARKER = "neighbor 10.0.0.1 route-map TRANSIT_PREVENT_OUT out"

POST_INJECT_COMMANDS = [
    "clear ip bgp 10.0.0.1 soft out",
    "clear ip bgp 10.1.24.2 soft out",
]


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
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
    parser.add_argument("--host", default="192.168.x.x", help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
