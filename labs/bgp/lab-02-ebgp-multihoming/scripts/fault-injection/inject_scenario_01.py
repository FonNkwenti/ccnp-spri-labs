#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — Missing next-hop-self on R3

Target:     R3 (iBGP neighbor 10.0.0.4 — link to R4)
Injects:    Removes 'neighbor 10.0.0.4 next-hop-self' from R3's address-family ipv4
Fault Type: Missing next-hop-self

Result:     R3 forwards the eBGP next-hop (10.1.13.1) into the iBGP fabric.
            R4 cannot resolve 10.1.13.1 via OSPF, so R3's path to 172.16.1.0/24
            is marked inaccessible. Only R2's path appears in R4's BGP table.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-02-ebgp-multihoming -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover  # noqa: E402

DEVICE_NAME = "R3"
DEFAULT_LAB_PATH = "ccnp-spri/bgp/lab-02-ebgp-multihoming.unl"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.4 next-hop-self",
    "exit-address-family",
]

# Pre-flight: read running config on the target interface / process to verify
# the lab is in the expected solution state before injecting.
PREFLIGHT_CMD = "show running-config | section router bgp"
# If this string is already present -> fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "neighbor 10.0.0.4 next-hop-self __FAULT_INJECTED__"
# If this string is absent -> not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.0.4 next-hop-self"


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
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, [DEVICE_NAME])
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
