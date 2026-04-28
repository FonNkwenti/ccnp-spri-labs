#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — Missing Network Statement on R1 Loopback0

Target:     R1 (router ospf 1 process)
Injects:    Removes the 'network 10.0.0.1 0.0.0.0 area 0' statement from R1's
            OSPF process, causing Loopback0 (10.0.0.1/32) to be excluded from
            R1's Router-LSA.
Fault Type: Missing OSPF Network Statement
Result:     OSPF adjacencies remain FULL (formed over Gi0/0), but 10.0.0.1/32
            disappears from the routing tables of R2 and R3. Pings to R1's
            loopback from remote routers fail.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00-single-area-ospfv2 -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ccnp-spri/ospf/lab-00-single-area-ospfv2.unl"

DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 10.0.0.1 0.0.0.0 area 0",
]

# Pre-flight: check R1's OSPF process configuration.
# The fault is a removal, so there is no positive string added by the fault.
# We check only that the solution-state marker (the Loopback0 network stmt)
# is present before injecting, and absent as evidence the fault is in effect.
PREFLIGHT_CMD = "show running-config | section ospf"
# Used as evidence the fault is already active (solution marker absent).
# Set to empty string — fault detection is handled in the custom preflight body.
PREFLIGHT_FAULT_MARKER = ""
# If this string is absent -> fault already injected (or lab not in solution state).
PREFLIGHT_SOLUTION_MARKER = "network 10.0.0.1 0.0.0.0 area 0"


def preflight(conn) -> bool:
    """
    Custom pre-flight for Scenario 03.

    The fault removes a network statement — there is no positive string that only
    appears after the fault is injected. Pre-flight logic:
      - If PREFLIGHT_SOLUTION_MARKER is absent: the fault is already active
        (or the lab is not in the solution state). Bail out either way.
    """
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Scenario 03 may already be injected, or the lab is not in the")
        print("    solution state. Run apply_solution.py to restore and retry.")
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
    print("Fault Injection: Scenario 03")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
