#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — R3 BGP Table Empty Despite Established Session

Target:     R4 (Route Reflector — AS 65100)
Injects:    Removes `neighbor 10.0.0.3 route-reflector-client` from R4's
            address-family ipv4, demoting R3 from RR client to a regular
            non-client iBGP peer.
Fault Type: Missing route-reflector-client designation

Result:     R3's session to R4 stays Established but R4 applies iBGP
            split-horizon and does not reflect routes to non-client R3.
            `show ip bgp` on R3 shows no prefixes (PfxRcd = 0).

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01-route-reflectors -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEVICE_NAME = "R4"
DEFAULT_LAB_PATH = "bgp/lab-01-route-reflectors.unl"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.3 route-reflector-client",
    "exit-address-family",
]

# Pre-flight: read BGP running config to verify known-good state.
# Removing route-reflector-client leaves no unique string in the config,
# so PREFLIGHT_FAULT_MARKER is a sentinel that is never present; idempotency
# is enforced by checking the solution marker is still there.
PREFLIGHT_CMD = "show running-config | section router bgp"
# Present only in the known-good (solution) state.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.0.3 route-reflector-client"
# Sentinel: this string is never in the running-config.
PREFLIGHT_FAULT_MARKER = "neighbor 10.0.0.3 route-reflector-client __FAULT_INJECTED__"


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
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 -- R3 BGP Table Empty")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab '{args.lab_path}'.")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
