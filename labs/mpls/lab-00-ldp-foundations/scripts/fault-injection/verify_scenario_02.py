#!/usr/bin/env python3
"""
Verifier: Scenario 02 — Asymmetric LDP Bindings

Checks on P2: Gi0/2 MPLS Tagging 'Yes'; LDP session to PE2 Oper;
local + remote bindings for PE2 /32 present. Exit 0 success, exit 5 failure.
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

# PE2 loopback used for LDP neighbor and binding checks
PE2_LOOPBACK = "10.0.0.4"


def check_p2(conn) -> list[str]:
    failures: list[str] = []

    # Check 1: MPLS re-enabled on Gi0/2
    iface_out = conn.send_command("show mpls interfaces")
    gi02_lines = [ln for ln in iface_out.splitlines() if "GigabitEthernet0/2" in ln]
    if not gi02_lines:
        failures.append("P2: GigabitEthernet0/2 not listed in 'show mpls interfaces'")
    else:
        line = gi02_lines[0]
        tokens = line.split()
        if len(tokens) >= 3 and tokens[2] == "No":
            failures.append("P2: Gi0/2 Tagging 'No' — mpls ip not restored")
        elif "Yes" not in line:
            failures.append("P2: Gi0/2 does not show 'Yes' in 'show mpls interfaces'")

    # Check 2: LDP session to PE2 is Oper
    nbrs = conn.send_command("show mpls ldp neighbor")
    idx = nbrs.find(PE2_LOOPBACK)
    if idx == -1:
        failures.append(f"P2: PE2 ({PE2_LOOPBACK}) not in 'show mpls ldp neighbor'")
    elif "Oper" not in nbrs[idx: idx + 300]:
        failures.append(f"P2: LDP session to PE2 ({PE2_LOOPBACK}) not Oper")

    # Check 3: local + remote binding for PE2 loopback /32
    bindings = conn.send_command(f"show mpls ldp bindings {PE2_LOOPBACK} 32")
    has_local = "loc" in bindings.lower() or "local" in bindings.lower()
    has_remote = "remote" in bindings.lower()
    if not has_local:
        failures.append(f"P2: no local binding for {PE2_LOOPBACK}/32")
    if not has_remote:
        failures.append(f"P2: no remote binding from PE2 for {PE2_LOOPBACK}/32")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Scenario 02 fix")
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
    args = parser.parse_args()

    host = require_host(args.host)
    device = f"{args.node_prefix}{DEVICE_NAME}"

    print("=" * 60)
    print("Verifier: Scenario 02 -- LDP Bindings Symmetric?")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(
            host, args.lab_path, [device],
            username=args.user, password=args.password,
        )
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 5

    port = ports.get(device)
    if port is None:
        print(f"[!] {device} not found in lab '{args.lab_path}'.")
        return 5

    print(f"[*] Connecting to {device} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 5

    try:
        failures = check_p2(conn)
    finally:
        conn.disconnect()

    if failures:
        print("[FAIL] Scenario 02 fix NOT verified:")
        for msg in failures:
            print(f"  - {msg}")
        return 5

    print("[PASS] LDP bindings symmetric — Scenario 02 fix verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
