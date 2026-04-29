#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — LDP Session Flapping

Symptom:     LDP sessions toggle Oper -> Active -> Oper roughly every 30 s;
             LFIB entries churn and forwarding briefly interrupts with each
             reset cycle.
Expected fix: Restore `mpls ldp router-id Loopback0 force` on the affected
              core router so the LDP transport address is reachable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-00-ldp-foundations -> mpls -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, require_host, resolve_and_discover  # noqa: E402

DEVICE_NAME = "P1"
DEFAULT_LAB_PATH = "labs/mpls/lab-00-ldp-foundations"

FAULT_COMMANDS = ["mpls ldp router-id Loopback99 force"]

PREFLIGHT_CMD = "show running-config | include mpls ldp router-id"
PREFLIGHT_SOLUTION_MARKER = "mpls ldp router-id Loopback0 force"
PREFLIGHT_FAULT_MARKER = "mpls ldp router-id Loopback99 force"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: fault already injected (Loopback99 present).")
        print("    Restore with apply_solution.py before re-injecting.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--user", default="admin",
                        help="EVE-NG API username (default: admin)")
    parser.add_argument("--password", default="eve",
                        help="EVE-NG API password (default: eve)")
    parser.add_argument("--node-prefix", default="",
                        help="Optional prefix prepended to node names (e.g. 'lab1-')")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)
    device = f"{args.node_prefix}{DEVICE_NAME}"

    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(
            host, args.lab_path, [device],
            username=args.user, password=args.password,
        )
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 6

    port = ports.get(device)
    if port is None:
        print(f"[!] {device} not found in lab '{args.lab_path}'.")
        return 6

    print(f"[*] Connecting to {device} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 6

    try:
        if not args.skip_preflight and not preflight(conn):
            return 6
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)

        post = conn.send_command(PREFLIGHT_CMD)
        if PREFLIGHT_FAULT_MARKER not in post:
            print("[!] Verification failed: Loopback99 router-id did not land.")
            return 6

        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {device}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
