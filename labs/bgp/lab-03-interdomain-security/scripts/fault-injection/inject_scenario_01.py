#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — PE-East-2 Backup Session Fails to Establish

Target:     R1 (AS 65001 CE -- Gi0/1 link to R3)
Injects:    Removes ttl-security hops 1 from R1 toward 10.1.13.3.
            Without GTSM, R1 reverts to the eBGP default TTL of 1.
            R3 retains ttl-security hops 1 (minimum acceptable TTL = 254).
            BGP packets from R1 arrive at R3 with TTL=1; R3 drops them silently.
Fault Type: GTSM Misconfiguration — ttl-security absent on one side

Result:     R3's eBGP session with R1 (10.1.13.1) stays in Active state.
            No BGP NOTIFICATION is sent -- the hold timer expires on both sides.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-03 -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router bgp 65001",
    "no neighbor 10.1.13.3 ttl-security hops 1",
]

# Pre-flight: check the BGP neighbor section on R1 to verify known-good state.
PREFLIGHT_CMD = "show running-config | section router bgp"
# If this string is absent -> not in solution state (or fault already injected), bail out.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.13.3 ttl-security hops 1"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found on R1.")
        print("    Either the fault is already injected or the lab is not in solution state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 -- PE-East-2 Backup Session Fails")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
