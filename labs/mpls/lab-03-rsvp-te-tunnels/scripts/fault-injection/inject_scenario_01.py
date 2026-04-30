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

# Both L4 endpoints must be faulted — CSPF sees per-link bandwidth from both ends.
TARGETS = [
    ("P1", ["interface GigabitEthernet0/1", "ip rsvp bandwidth 10"]),
    ("P2", ["interface GigabitEthernet0/1", "ip rsvp bandwidth 10"]),
]

PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/1"
# Solution state: full bandwidth configured. Absence means either fault is injected
# or lab is not in solution state — apply_solution.py required in either case.
# NOTE: do not also check for "ip rsvp bandwidth 10" — it is a substring of
# "ip rsvp bandwidth 100000" and would produce a false match on solution state.
PREFLIGHT_SOLUTION_MARKER = "ip rsvp bandwidth 100000"


def preflight(conn, device_name: str) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Either Scenario 01 is already active, or the lab is not in solution state.")
        print("    Run apply_solution.py to restore the known-good config.")
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

    all_names = [name for name, _ in TARGETS]

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=all_names)
        if lab_path is None:
            print(f"[!] No running lab found with {all_names}. Start all nodes first.",
                  file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    # Pre-flight pass: check all targets before injecting any
    if not args.skip_preflight:
        for name, _ in TARGETS:
            port = ports.get(name)
            if port is None:
                print(f"[!] {name} not found in lab '{lab_path}'.")
                return 3
            print(f"[*] Pre-flight check on {name} ({host}:{port}) ...")
            try:
                conn = connect_node(host, port)
            except Exception as exc:
                print(f"[!] Connection to {name} failed: {exc}", file=sys.stderr)
                return 3
            try:
                if not preflight(conn, name):
                    return 4
            finally:
                conn.disconnect()

    # Inject pass: apply fault commands to each target
    for name, fault_cmds in TARGETS:
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
            print(f"[*] Injecting fault on {name} ...")
            conn.send_config_set(fault_cmds)
            conn.save_config()
        finally:
            conn.disconnect()
        print(f"[+] Fault injected on {name}.")

    print("[+] Scenario 01 is now active on P1 and P2.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
