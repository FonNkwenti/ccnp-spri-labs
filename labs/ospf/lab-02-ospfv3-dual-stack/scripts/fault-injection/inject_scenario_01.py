#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — R4 Has No OSPFv3 Neighbors

Target:     R4 (GigabitEthernet0/0 — link to R3)
Injects:    Removes the OSPFv3 IPv6 area 2 assignment from R4 GigabitEthernet0/0,
            breaking OSPFv3 adjacency formation between R4 and R3.
Fault Type: Missing OSPFv3 Interface Area Assignment

Result:     'show ospfv3 neighbor' on R4 shows no neighbors. R4's IPv6 routing
            table is empty. Pings from R1 to 2001:db8:4::1 fail.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-02-ospfv3-dual-stack -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ccnp-spri/ospf/lab-02-ospfv3-dual-stack.unl"

DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "no ospfv3 1 ipv6 area 2",
]

# Pre-flight: check R4 Gi0/0 interface config to verify known-good state.
# The fault is a pure removal — no positive marker string is added by the fault.
# Pre-flight checks only that the solution-state marker is present before injecting.
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Set to empty string — fault detection is handled solely via the custom preflight body.
PREFLIGHT_FAULT_MARKER = ""
# If this string is absent -> fault already injected, or lab not in solution state.
PREFLIGHT_SOLUTION_MARKER = "ospfv3 1 ipv6 area 2"


def preflight(conn) -> bool:
    """
    Custom pre-flight for Scenario 01.

    The fault removes an ospfv3 area assignment — there is no positive string
    that only appears after the fault is injected. Pre-flight logic:
      - If PREFLIGHT_SOLUTION_MARKER is absent: the fault is already active
        (or the lab is not in the solution state). Bail out either way.
    """
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Scenario 01 may already be injected, or the lab is not in the")
        print("    solution state. Run apply_solution.py to restore and retry.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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
