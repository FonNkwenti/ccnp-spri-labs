#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- L3 (R3<->R4) IS-IS Adjacency Down

Target:     R4 (IS-IS CORE -- GigabitEthernet0/0/0/0 address-family ipv4 unicast)
Injects:    Removes 'address-family ipv4 unicast' from Gi0/0/0/0 under IS-IS CORE
            on R4. Gi0/0/0/0 is L3 (R4 <-> R3); the AF removal tears down only that
            adjacency.
Fault Type: IS-IS Interface Address-Family Removal

Result:     Total IS-IS adjacencies in the domain drop from 5 to 4. R4 retains
            its Gi0/0/0/1 (L4) adjacency to R1, so 10.0.0.4 remains reachable
            via R1. R3 loses its direct neighbor to R4 and reaches it via R2.
            All prefix-SID labels (16001-16004) remain installed across the
            domain -- this is an IGP topology fault, not an SR fault.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: fault-injection -> scripts -> lab-00-sr-foundations-and-srgb -> segment-routing -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router isis CORE",
    " interface GigabitEthernet0/0/0/0",
    "  no address-family ipv4 unicast",
    " exit",
    "exit",
    "commit",
]

# Pre-flight: check running-config to confirm Gi0/0/0/0 is fully configured under IS-IS.
PREFLIGHT_CMD = "show running-config router isis CORE"
# Both markers must be present together to confirm solution state.
PREFLIGHT_SOLUTION_MARKER = "GigabitEthernet0/0/0/0"
# Fault marker: address-family should be present under the interface in solution state.
# Absence of address-family ipv4 unicast under GigabitEthernet0/0/0/0 means fault is active.
PREFLIGHT_FAULT_MARKER = None  # Checked structurally in preflight() below.


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: 'GigabitEthernet0/0/0/0' not found under IS-IS CORE.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    # Check that address-family ipv4 unicast appears after the interface stanza.
    # In XR running-config the interface block appears as a contiguous stanza; we check
    # that both strings co-exist in the output (necessary but not positional).
    if "address-family ipv4 unicast" not in output:
        print("[!] Pre-flight failed: 'address-family ipv4 unicast' absent under IS-IS CORE.")
        print("    Scenario 02 may already be injected. Restore with apply_solution.py.")
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
        conn = connect_node(host, port, device_type="cisco_xr_telnet")
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
