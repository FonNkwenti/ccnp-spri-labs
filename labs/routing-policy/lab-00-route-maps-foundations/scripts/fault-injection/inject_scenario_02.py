#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Prefix-List ge/le Wrong Boundary

Target:     R1 (prefix-list PFX_R4_LO2_EXACT, used in FILTER_R4_IN deny 10)
Injects:    Replaces the exact-match entry in PFX_R4_LO2_EXACT
            (permit 172.20.5.0/24) with an aggregate match
            (permit 172.20.0.0/16 le 24), which matches BOTH R4 loopback
            prefixes (172.20.4.0/24 and 172.20.5.0/24).
Fault Type: Prefix-List ge/le Over-Match / Too-Wide Boundary

Result:     Route-map FILTER_R4_IN deny 10 now matches both R4 prefixes;
            the permit 20 catch-all is never reached. R1's BGP table has
            0 entries from R4.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00 -> routing-policy -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R1"

# Two-step replace: clear the exact seq 5, then redefine with over-wide boundary.
# On IOS, a new seq with the same number replaces the old entry, but using
# 'no ... seq 5' first guarantees a clean overwrite.
FAULT_COMMANDS = [
    "no ip prefix-list PFX_R4_LO2_EXACT seq 5",
    "ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.0.0/16 le 24",
]

# Scope to the single prefix-list so PFX_R4_LE_24 (which also contains 172.20.0.0/16)
# does not pollute the marker check.
PREFLIGHT_CMD = "show ip prefix-list PFX_R4_LO2_EXACT"

# Present in solution state: exact-match entry for Lo2.
PREFLIGHT_SOLUTION_MARKER = "permit 172.20.5.0/24"

# Present only after the fault is injected.
PREFLIGHT_FAULT_MARKER = "permit 172.20.0.0/16 le 24"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found in PFX_R4_LO2_EXACT.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
