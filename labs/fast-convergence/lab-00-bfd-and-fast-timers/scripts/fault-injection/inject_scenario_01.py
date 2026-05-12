#!/usr/bin/env python3
"""
Fault Injection: Scenario 01. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

# Both sides of the L1 BFD session are faulted:
#   R1 Gi1 → 500 ms intervals (slow side, drives the negotiated rate up)
#   R2 Gi1 → 50 ms intervals, multiplier 1 (detection window = 500 × 1 = 500 ms)
DEVICE_NAMES = ["R1", "R2"]

R1_FAULT_COMMANDS = [
    "interface GigabitEthernet1",
    "bfd interval 500 min_rx 500 multiplier 3",
]

R2_FAULT_COMMANDS = [
    "interface GigabitEthernet1",
    "bfd interval 50 min_rx 50 multiplier 1",
]

# Pre-flight on R2: verify the lab is in the expected solution state before injecting.
PREFLIGHT_CMD = "show running-config interface GigabitEthernet1"
# If this string is already present → fault already injected, bail out.
PREFLIGHT_FAULT_MARKER = "bfd interval 50 min_rx 50 multiplier 1"
# If this string is absent → not in solution state, bail out.
PREFLIGHT_SOLUTION_MARKER = "bfd interval 150 min_rx 150 multiplier 3"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print("[!] Pre-flight failed: scenario appears already injected.")
        print("    Restore with apply_solution.py.")
        return False
    return True


def inject_device(host: str, port: int, name: str, commands: list) -> bool:
    print(f"[*] Connecting to {name} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return False
    try:
        conn.send_config_set(commands)
        conn.save_config()
    finally:
        conn.disconnect()
    print(f"[+] Fault injected on {name}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=DEVICE_NAMES)
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICE_NAMES}. Start all nodes first.", file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    r1_port = ports.get("R1")
    r2_port = ports.get("R2")

    if r1_port is None or r2_port is None:
        missing = [n for n, p in [("R1", r1_port), ("R2", r2_port)] if p is None]
        print(f"[!] Device(s) not found in lab ports: {', '.join(missing)}")
        return 3

    if not args.skip_preflight:
        print("[*] Running pre-flight check on R2 ...")
        try:
            conn = connect_node(host, r2_port)
            passed = preflight(conn)
            conn.disconnect()
        except Exception as exc:
            print(f"[!] Pre-flight connection failed: {exc}", file=sys.stderr)
            return 3
        if not passed:
            return 4

    print("[*] Injecting fault configuration ...")
    if not inject_device(host, r1_port, "R1", R1_FAULT_COMMANDS):
        return 3
    if not inject_device(host, r2_port, "R2", R2_FAULT_COMMANDS):
        return 3

    print("[+] Fault injected on R1 and R2. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
