#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Prepend on the Wrong eBGP Egress

Targets:    R1 and R2 (BGP route-maps)
Injects:    Removes `set as-path prepend 65001 65001` from R2's route-map
            TRANSIT_PREVENT_OUT (the correct egress) and adds the same set clause
            to R1's route-map TRANSIT_PREVENT_OUT (the wrong egress). Result:
            R3 sees AS-path `65001 65001 65001` (length 3) and R4 sees `65001`
            (length 1). Inbound preference inverts -- ISP-B becomes the primary
            inbound path instead of ISP-A.
Fault Type: Prepend on backup vs. primary inverted (egress placement error)

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICES = ["R1", "R2"]

R2_FAULT_COMMANDS = [
    "route-map TRANSIT_PREVENT_OUT permit 10",
    "no set as-path prepend 65001 65001",
    "exit",
]
R1_FAULT_COMMANDS = [
    "route-map TRANSIT_PREVENT_OUT permit 10",
    "set as-path prepend 65001 65001",
    "exit",
]

PREFLIGHT_CMD = "show route-map TRANSIT_PREVENT_OUT"
R2_SOLUTION_MARKER = "as-path prepend 65001 65001"
R1_FAULT_MARKER = "as-path prepend 65001 65001"

R2_POST_INJECT = ["clear ip bgp 10.1.24.2 soft out"]
R1_POST_INJECT = ["clear ip bgp 10.1.13.2 soft out"]


def preflight_r2(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if R2_SOLUTION_MARKER not in output:
        print(f"[!] R2 pre-flight failed: '{R2_SOLUTION_MARKER}' not found in route-map.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def preflight_r1(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if R1_FAULT_MARKER in output:
        print(f"[!] R1 pre-flight failed: '{R1_FAULT_MARKER}' already present in route-map.")
        print("    Scenario 01 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def inject_device(host, port, name, fault_cmds, post_cmds, preflight_fn, skip_preflight) -> bool:
    print(f"[*] Connecting to {name} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name} connection failed: {exc}", file=sys.stderr)
        return False
    try:
        if not skip_preflight and not preflight_fn(conn):
            return False
        print(f"[*] Injecting fault on {name} ...")
        conn.send_config_set(fault_cmds)
        conn.save_config()
        for cmd in post_cmds:
            conn.send_command(cmd)
    finally:
        conn.disconnect()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x", help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=DEVICES)
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICES}.", file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    for name in DEVICES:
        if name not in ports:
            print(f"[!] {name} not found in lab '{lab_path}'.")
            return 3

    if not inject_device(host, ports["R2"], "R2", R2_FAULT_COMMANDS, R2_POST_INJECT,
                         preflight_r2, args.skip_preflight):
        return 4
    if not inject_device(host, ports["R1"], "R1", R1_FAULT_COMMANDS, R1_POST_INJECT,
                         preflight_r1, args.skip_preflight):
        return 4

    print("[+] Fault injected on R1 and R2. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
