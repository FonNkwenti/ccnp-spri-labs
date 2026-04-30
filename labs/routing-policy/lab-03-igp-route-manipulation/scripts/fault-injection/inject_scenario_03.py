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

DEVICE_NAME = "R2"

# Fault: remove the permit 30 sequence from OSPF_TO_ISIS.
# IOS deletes the entire map entry when the sequence is removed;
# E2 routes now fall through to the implicit deny.
FAULT_COMMANDS = [
    "no route-map OSPF_TO_ISIS permit 30",
]

# Pre-flight: inspect the OSPF_TO_ISIS route-map via running-config section.
# The section output will include all sequences that are defined.
PREFLIGHT_CMD = "show running-config | section route-map OSPF_TO_ISIS"
# Present only after the fault: permit 30 is gone, so its unique marker
# ("external type-2") is absent.  We use the absence of the solution marker
# as the primary fault detector; this fault marker is a distinctive string
# from the permit 40 sequence to confirm the route-map still exists at all
# (guards against a completely empty / missing route-map, which is a different
# fault class).
PREFLIGHT_FAULT_MARKER = "route-map OSPF_TO_ISIS deny 10"
# Present only in the known-good solution state — the type-2 match line in seq 30.
PREFLIGHT_SOLUTION_MARKER = "match route-type external type-2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    # The fault marker (deny 10) is present in BOTH solution and fault states,
    # so it cannot signal "already injected" on its own.  Instead, we confirm
    # the solution marker is present above and rely on its absence after injection.
    # The second guard below protects against running the script twice:
    # after injection, the solution marker is gone, so the first check catches it.
    # This comment is intentional: the fault marker here simply confirms the
    # route-map exists at all, not that the specific fault is already active.
    if PREFLIGHT_FAULT_MARKER not in output:
        print("[!] Pre-flight failed: scenario appears already injected.")
        print("    The OSPF_TO_ISIS route-map may be missing entirely.")
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
