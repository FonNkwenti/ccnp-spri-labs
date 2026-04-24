#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — R1 Cannot Reach R4 Loopback

Target:     R2 (OSPF process 1 — Area 1 outbound Type-3 filter)
Injects:    An outbound prefix-list filter on R2 that blocks the Type-3 Summary
            LSA for 172.16.4.0/24 from being advertised into Area 1. R3-R4
            adjacency and all other routes remain intact.
Fault Type: ABR Outbound Type-3 Filter (area filter-list)

Result:     R1 has no route to 172.16.4.0/24; ping from R1 to 172.16.4.1 fails.
            R3 and R4 communicate normally; other inter-area routes on R1 are
            unaffected. The symptom looks like a route missing from R2's LSA
            advertisement into Area 1.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>

NOTE: Restoration requires apply_solution.py with --reset to remove the
      prefix-list and filter-list that cannot be negated by config push alone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01-multiarea-ospfv2 -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ospf/lab-01-multiarea-ospfv2.unl"

DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "ip prefix-list BLOCK_R4_LOOP seq 10 deny 172.16.4.0/24",
    "ip prefix-list BLOCK_R4_LOOP seq 20 permit 0.0.0.0/0 le 32",
    "router ospf 1",
    "area 1 filter-list prefix BLOCK_R4_LOOP out",
]

# Pre-flight: check R2's running config for OSPF area 1 configuration.
PREFLIGHT_CMD = "show running-config | section router ospf"
# If this string is already present → fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "filter-list prefix BLOCK_R4_LOOP"
# If this string is absent → not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "network 10.1.23.0 0.0.0.255 area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears already injected. Restore with apply_solution.py --reset.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 — R1 Cannot Reach R4 Loopback")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("    To restore: python3 apply_solution.py --host <eve-ng-ip> --reset")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
