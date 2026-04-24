#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — R3-R5 Neighbors Stuck in ExStart

Target:     R3 (Gi0/2 — link to R5, 10.1.35.0/24)
Injects:    Area mismatch on R3 Gi0/2: removes the subnet from Area 3 and places
            it into Area 0, causing R3 and R5 to disagree on the area for that link.
Fault Type: Area Mismatch

Result:     R3 and R5 neighbor state stuck in ExStart; routes from R1/R2/R4
            toward R5's loopback (172.16.5.0/24) disappear from the routing table;
            R1 cannot ping 172.16.5.1.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
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
DEFAULT_LAB_PATH = "ospf/lab-01-multiarea-ospfv2-haiku.unl"

DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 10.1.35.0 0.0.0.255 area 3",
    "network 10.1.35.0 0.0.0.255 area 0",
]

# Pre-flight: read the OSPF section of R3's running config to verify
# the lab is in the expected solution state before injecting.
PREFLIGHT_CMD = "show running-config | section router ospf"
# If this string is already present → fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "network 10.1.35.0 0.0.0.255 area 0"
# If this string is absent → not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "network 10.1.35.0 0.0.0.255 area 3"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
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
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 — R3-R5 Neighbors Stuck in ExStart")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
