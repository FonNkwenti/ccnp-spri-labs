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

# Two-device fault: next-hop-self removed from both PEs
TARGETS = [
    {
        "name": "PE1",
        "fault_commands": [
            "router bgp 65100",
            "address-family ipv4",
            "no neighbor 10.0.0.4 next-hop-self",
        ],
        "preflight_cmd": "show running-config | section bgp",
        "preflight_solution_marker": "neighbor 10.0.0.4 next-hop-self",
        "preflight_fault_marker": "no neighbor 10.0.0.4 next-hop-self",
    },
    {
        "name": "PE2",
        "fault_commands": [
            "router bgp 65100",
            "address-family ipv4",
            "no neighbor 10.0.0.1 next-hop-self",
        ],
        "preflight_cmd": "show running-config | section bgp",
        "preflight_solution_marker": "neighbor 10.0.0.1 next-hop-self",
        "preflight_fault_marker": "no neighbor 10.0.0.1 next-hop-self",
    },
]

DEVICE_NAMES = [t["name"] for t in TARGETS]


def preflight(conn, target: dict) -> bool:
    name = target["name"]
    output = conn.send_command(target["preflight_cmd"])
    if target["preflight_solution_marker"] not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if target["preflight_fault_marker"] in output:
        print("[!] Pre-flight failed: scenario appears already injected.")
        print("    Restore with apply_solution.py.")
        return False
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
            print(f"[!] No running lab found with {DEVICE_NAMES}. Start all nodes first.",
                  file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    for target in TARGETS:
        name = target["name"]
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab '{lab_path}'.")
            return 3

        print(f"[*] Connecting to {name} on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
        except Exception as exc:
            print(f"[!] Connection to {name} failed: {exc}", file=sys.stderr)
            return 3

        try:
            if not args.skip_preflight and not preflight(conn, target):
                return 4
            print(f"[*] Injecting fault on {name} ...")
            conn.send_config_set(target["fault_commands"])
            conn.save_config()
            print(f"[+] Fault injected on {name}.")
        finally:
            conn.disconnect()

    print(f"[+] Scenario 01 is now active on {DEVICE_NAMES}.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
