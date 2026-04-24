#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — Timer Mismatch on R1 Gi0/0

Target:     R1 (GigabitEthernet0/0 — link to R2)
Injects:    Non-default hello-interval (3s) and dead-interval (12s) on R1 Gi0/0
            while R2 retains default timers (Hello: 10, Dead: 40).
Fault Type: Timer Mismatch
Result:     OSPF adjacency between R1 and R2 drops after the dead-interval
            expires. R2 shows R1 missing or flapping in 'show ip ospf neighbor'.

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
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ospf/lab-00-single-area-ospfv2.unl"

DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "ip ospf hello-interval 3",
    "ip ospf dead-interval 12",
]

# Pre-flight: check R1's Gi0/0 interface config to verify known-good state.
# Defaults (10/40) do NOT appear in running-config, so we check the IP address
# as the solution-state anchor. A non-default hello-interval confirms fault presence.
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# If this string is already present -> fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "ip ospf hello-interval 3"
# If this string is absent -> not in solution state or wrong device, bail out.
PREFLIGHT_SOLUTION_MARKER = "ip address 10.1.12.1"


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
