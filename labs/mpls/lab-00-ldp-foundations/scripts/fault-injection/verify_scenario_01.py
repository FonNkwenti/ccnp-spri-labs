#!/usr/bin/env python3
"""
Verifier: Scenario 01 — LDP Session Flapping

Checks: P1 config has Loopback0 router-id; P1 shows Oper sessions to PE1
and P2; PE1 reports Oper state toward P1. Exit 0 success, exit 5 failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, require_host, resolve_and_discover  # noqa: E402

DEVICE_NAMES = ["P1", "PE1"]
DEFAULT_LAB_PATH = "labs/mpls/lab-00-ldp-foundations"

# P1 loopback: 10.0.0.2 | PE1: 10.0.0.1 | P2: 10.0.0.3
P1_PEER_PE1 = "10.0.0.1"
P1_PEER_P2  = "10.0.0.3"
P1_LOOPBACK = "10.0.0.2"


def check_p1(conn) -> list[str]:
    failures: list[str] = []

    cfg = conn.send_command("show running-config | include mpls ldp router-id")
    if "Loopback99" in cfg:
        failures.append("P1: mpls ldp router-id Loopback99 still in running-config")
    if "Loopback0" not in cfg:
        failures.append("P1: mpls ldp router-id Loopback0 not found — fix not applied")

    nbrs = conn.send_command("show mpls ldp neighbor")
    for peer_ip in (P1_PEER_PE1, P1_PEER_P2):
        if peer_ip not in nbrs:
            failures.append(f"P1: peer {peer_ip} not in 'show mpls ldp neighbor'")
        else:
            idx = nbrs.find(peer_ip)
            if "Oper" not in nbrs[idx: idx + 300]:
                failures.append(f"P1: LDP session to {peer_ip} is not Oper")

    return failures


def check_pe1(conn) -> list[str]:
    failures: list[str] = []
    out = conn.send_command(f"show mpls ldp neighbor {P1_LOOPBACK}")
    if "Oper" not in out:
        failures.append(f"PE1: LDP neighbor {P1_LOOPBACK} (P1) not in Oper state")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Scenario 01 fix")
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
    devices = [f"{args.node_prefix}{d}" for d in DEVICE_NAMES]
    p1_name, pe1_name = devices[0], devices[1]

    print("=" * 60)
    print("Verifier: Scenario 01 -- LDP Session Stable?")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(
            host, args.lab_path, devices,
            username=args.user, password=args.password,
        )
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 5

    all_failures: list[str] = []

    for name, checker in ((p1_name, check_p1), (pe1_name, check_pe1)):
        port = ports.get(name)
        if port is None:
            all_failures.append(f"{name} not found in lab '{args.lab_path}'")
            continue
        print(f"[*] Connecting to {name} on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
        except Exception as exc:
            all_failures.append(f"{name}: connection failed — {exc}")
            continue
        try:
            all_failures.extend(checker(conn))
        finally:
            conn.disconnect()

    if all_failures:
        print("[FAIL] Scenario 01 fix NOT verified:")
        for msg in all_failures:
            print(f"  - {msg}")
        return 5

    print("[PASS] LDP session stable — Scenario 01 fix verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
