#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Dynamic Session Up but No Routes Received

Target:     R2 (PE East-1 -- BGP address-family IPv4 configuration)
Injects:    Removes `neighbor DYN_CUST activate` from the address-family ipv4
            section of R2's router bgp 65100 configuration.
Fault Type: BGP Peer-Group Not Activated in Address-Family (NLRI exchange disabled)

Result:     The dynamic BGP session from 10.99.0.1 (R1) remains Established
            (TCP/OPEN handshake succeeds) but no IPv4 prefixes are exchanged.
            R2 does not receive 172.16.1.0/24 from the dynamic session.
            `show ip bgp neighbors 10.99.0.1 received-routes` returns empty.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-04-dampening-dynamic -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor DYN_CUST activate",
    "exit-address-family",
]

# Pre-flight: verify DYN_CUST is activated in the IPv4 AF before injecting.
PREFLIGHT_CMD = "show running-config | section address-family ipv4"
# Present only in the known-good (AF activation present) state.
PREFLIGHT_SOLUTION_MARKER = "neighbor DYN_CUST activate"
# Removal-style fault: no unique string appears after injection.
# Use a sentinel that is never present in IOS running-config output.
PREFLIGHT_FAULT_MARKER = "__FAULT_03_ALREADY_INJECTED__"


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
