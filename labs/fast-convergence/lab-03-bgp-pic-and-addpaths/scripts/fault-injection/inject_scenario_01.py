#!/usr/bin/env python3
"""
Fault Injection: Scenario 01. Restore with: python3 apply_solution.py --host <eve-ng-ip>

Ticket 1: Removes neighbor 10.0.0.3 additional-paths receive on R2, and also
          removes neighbor 10.0.0.2 additional-paths receive on R3. This breaks
          the add-paths capability negotiation on the R2↔R3 iBGP session.

Symptom: show ip bgp 192.0.2.0 on R2 shows only one path (via R1) despite
         global bgp additional-paths install being present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

TARGET_DEVICES = ["R2", "R3"]

FAULT_COMMANDS_R2 = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.3 additional-paths receive",
    "exit-address-family",
]

FAULT_COMMANDS_R3 = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.2 additional-paths receive",
    "exit-address-family",
]

FAULT_COMMANDS = {
    "R2": FAULT_COMMANDS_R2,
    "R3": FAULT_COMMANDS_R3,
}

PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_MARKERS = {
    "R2": "neighbor 10.0.0.3 additional-paths receive",
    "R3": "neighbor 10.0.0.2 additional-paths receive",
}


def preflight(conn, name: str) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    marker = PREFLIGHT_MARKERS.get(name, "")
    if marker and marker not in output:
        print(f"[!] Pre-flight failed: '{marker}' not present on {name} — lab not in expected pre-injection state.")
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
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 — R2↔R3 additional-paths receive missing")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=TARGET_DEVICES)
        if lab_path is None:
            print(f"[!] No running lab found with {', '.join(TARGET_DEVICES)}. Start all nodes first.", file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    for name in TARGET_DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab '{lab_path}' — skipping.")
            continue

        print(f"[*] Connecting to {name} on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
        except Exception as exc:
            print(f"[!] Connection to {name} failed: {exc}", file=sys.stderr)
            return 3

        try:
            if not args.skip_preflight and not preflight(conn, name):
                return 4
            print(f"[*] Injecting fault on {name} ...")
            conn.send_config_set(FAULT_COMMANDS[name])
            conn.save_config()
        finally:
            conn.disconnect()
        print(f"[+] Fault injected on {name}.")

    print("=" * 60)
    print("Scenario 01 is now active on R2 and R3.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
