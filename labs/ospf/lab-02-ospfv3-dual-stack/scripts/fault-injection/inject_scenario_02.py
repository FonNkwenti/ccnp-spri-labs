#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — R1 Cannot Reach R5 via IPv6

Target:     R5 (GigabitEthernet0/0 — link to R3)
Injects:    Removes the OSPFv3 IPv6 area 3 assignment from R5 GigabitEthernet0/0,
            causing R5 to stop forming an OSPFv3 adjacency with R3.
Fault Type: Missing OSPFv3 Interface Area Assignment

Result:     'show ospfv3 neighbor' on R3 shows R5 absent. R5's loopback prefix
            2001:db8::5/128 is not redistributed into OSPFv3. Pings from R1 to
            2001:db8::5 fail while IPv4 reachability to R5 remains unaffected.

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
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ccnp-spri/ospf/lab-02-ospfv3-dual-stack.unl"

DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "no ospfv3 1 ipv6 area 3",
]

# Pre-flight: check R5 Gi0/0 interface config to verify known-good state.
# The fault is a pure removal — no positive marker string is added by the fault.
# Pre-flight checks only that the solution-state marker is present before injecting.
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Set to empty string — fault detection is handled solely via the custom preflight body.
PREFLIGHT_FAULT_MARKER = ""
# If this string is absent -> fault already injected, or lab not in solution state.
PREFLIGHT_SOLUTION_MARKER = "ospfv3 1 ipv6 area 3"


def preflight(conn) -> bool:
    """
    Custom pre-flight for Scenario 02.

    The fault removes an ospfv3 area assignment — there is no positive string
    that only appears after the fault is injected. Pre-flight logic:
      - If PREFLIGHT_SOLUTION_MARKER is absent: the fault is already active
        (or the lab is not in the solution state). Bail out either way.
    """
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Scenario 02 may already be injected, or the lab is not in the")
        print("    solution state. Run apply_solution.py to restore and retry.")
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
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, [DEVICE_NAME])
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
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
