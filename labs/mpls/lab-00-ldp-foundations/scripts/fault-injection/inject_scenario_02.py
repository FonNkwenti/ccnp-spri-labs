#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — Asymmetric LDP Bindings

Symptom:     One router's MPLS binding table is missing label entries that all
             other routers carry; traffic toward a specific destination loses
             its label and is dropped or falls back to IP forwarding.
Expected fix: Re-enable MPLS on the affected interface so LDP discovery
              resumes and bindings are exchanged symmetrically across all
              label-switching routers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, require_host, resolve_and_discover  # noqa: E402

DEVICE_NAME = "P2"
DEFAULT_LAB_PATH = "labs/mpls/lab-00-ldp-foundations"

FAULT_COMMANDS = ["interface GigabitEthernet0/2", "no mpls ip"]

PREFLIGHT_CMD = "show mpls interfaces GigabitEthernet0/2"
PREFLIGHT_SOLUTION_MARKER = "Yes"       # Tagging column value when enabled
PREFLIGHT_FAULT_MARKER = "No"           # Tagging column value when disabled


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: MPLS not enabled on Gi0/2 ('{PREFLIGHT_SOLUTION_MARKER}' absent).")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--user", default="admin",
                        help="EVE-NG API username (default: admin)")
    parser.add_argument("--password", default="eve",
                        help="EVE-NG API password (default: eve)")
    parser.add_argument("--node-prefix", default="",
                        help="Optional prefix prepended to node names")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)
    device = f"{args.node_prefix}{DEVICE_NAME}"

    print("=" * 60)
    print("Fault Injection: Scenario 02")
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
        if PREFLIGHT_SOLUTION_MARKER in post and PREFLIGHT_FAULT_MARKER not in post:
            print("[!] Verification failed: MPLS still appears enabled on Gi0/2.")
            return 6

        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {device}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
