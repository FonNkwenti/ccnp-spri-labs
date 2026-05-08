#!/usr/bin/env python3
"""
Fault Injection: Scenario 03. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "PE1"
FAULT_COMMANDS = [
    "interface Tunnel10",
    "tunnel mpls traffic-eng affinity 0x1",
]

# Preflight: confirm Tunnel10 has no affinity constraint (known-good state).
# In the solution config, Tunnel10 has no affinity command — default 0x0/0x0.
# After injection, "affinity 0x1" appears in the interface config.
PREFLIGHT_CMD = "show running-config interface Tunnel10"
PREFLIGHT_SOLUTION_MARKER = "bandwidth 10000"
PREFLIGHT_FAULT_MARKER = "affinity 0x1"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: Tunnel10 not in expected pre-injection state on PE1.")
        print("    Run apply_solution.py to restore, or setup_lab.py if lab is not yet initialized.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print("[!] Pre-flight failed: scenario appears already injected.")
        print("    Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
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
