#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — R5's External Route Not Visible Outside Area 3

Target:     R3 (ABR between Area 0 and Area 3 NSSA)
Injects:    Adds `area 3 nssa no-redistribution` to OSPF process 1, disabling
            the Type-7 to Type-5 LSA translation that R3 performs as the ABR.
Fault Type: NSSA no-redistribution (Type-7 to Type-5 translation disabled)

Result:     R5's Type-7 LSA for 192.168.55.0/24 stays within Area 3 and is
            never translated to a Type-5; R1, R2, and R4 have no route to
            192.168.55.0/24 even though the Type-7 is present in Area 3.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-03 -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router ospf 1",
    "area 3 nssa no-redistribution",
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "area 3 nssa no-redistribution",
    "exit-address-family",
]

# Pre-flight: read running OSPF config to verify known-good state.
PREFLIGHT_CMD = "show running-config | section router ospf"
# If this string is already present -> fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "no-redistribution"
# If this string is absent -> not in solution state, bail out.
# Uses a specific string (with leading space and no trailing qualifier) to
# distinguish plain "area 3 nssa" from "area 3 nssa no-redistribution".
PREFLIGHT_SOLUTION_MARKER = " area 3 nssa\n"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER.strip()}' not found "
              "(or already has no-redistribution appended).")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 03 appears already injected. Restore with apply_solution.py.")
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
