#!/usr/bin/env python3
"""
Fault Injection: Scenario 03. Restore with: python3 apply_solution.py --host <eve-ng-ip>

Ticket 3: Removes neighbor 10.0.0.1 advertise additional-paths best 2 and
          neighbor 10.0.0.1 additional-paths receive on R4. This breaks the
          add-paths capability negotiation on the R4↔R1 iBGP session.

Symptom: show ip bgp 192.0.2.0 on R4 shows only one path. All other iBGP
         sessions on R4 exchange additional paths normally — only R4↔R1
         is broken.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.1 advertise additional-paths best 2",
    "no neighbor 10.0.0.1 additional-paths receive",
    "exit-address-family",
]

PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_MARKER = "neighbor 10.0.0.1 additional-paths receive"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_MARKER not in output:
        print("[!] Pre-flight failed: neighbor 10.0.0.1 additional-paths receive not present on R4 — lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
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
    print("Fault Injection: Scenario 03 — R4↔R1 add-paths config missing")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=[DEVICE_NAME])
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICE_NAME}. Start all nodes first.", file=sys.stderr)
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
