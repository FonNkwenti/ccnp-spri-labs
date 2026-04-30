#!/usr/bin/env python3
"""
Lab Setup -- Routing-Policy Lab 01: Tags, Route Types, Regex, and BGP Communities

Pushes the progressive initial-configs (= lab-00 solutions) to all 4 lab devices
via EVE-NG console ports. Console ports are discovered at runtime via the EVE-NG REST API.

This is a progressive lab extending lab-00. Initial-configs contain the complete
lab-00 solution state — OSPF/IS-IS/BGP active, FILTER_R4_IN applied, lab-00
route-maps defined. Students add redistribution, tags, AS-path regex, and community
features through the workbook tasks.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>
    python3 setup_lab.py --host <eve-ng-ip> --node R1,R3
    python3 setup_lab.py --host <eve-ng-ip> --reset --node R2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: lab-01-tags-regex-communities/ -> routing-policy/ -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "common" / "tools"))
from eve_ng import (  # noqa: E402
    EveNgError,
    connect_node,
    require_host,
    resolve_and_discover,
    soft_reset_device,
)

INITIAL_CONFIGS_DIR = SCRIPT_DIR / "initial-configs"

DEFAULT_LAB_PATH = "ccnp-spri/routing-policy/lab-01-tags-regex-communities.unl"

DEVICES = ["R1", "R2", "R3", "R4"]


def push_config(host: str, name: str, port: int, reset: bool = False) -> bool:
    cfg_file = INITIAL_CONFIGS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"  [!] Config file not found: {cfg_file}")
        return False

    if reset:
        print(f"[*] Resetting {name} on {host}:{port} ...")
        try:
            soft_reset_device(host, port)
            print(f"[+] {name} reset complete.")
        except Exception as exc:
            print(f"  [!] {name} reset failed: {exc}")
            return False

    print(f"[*] Connecting to {name} on {host}:{port} ...")
    try:
        if reset:
            soft_reset_device(host, port)
        conn = connect_node(host, port)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!") and line.strip() != "end"
        ]
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"[+] {name} configured.")
        return True
    except Exception as exc:
        print(f"  [!] {name} failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Push lab-00 solution configs as lab-01 baseline to lab nodes"
    )
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Reset devices before config push")
    parser.add_argument("--node", default=None,
                        help="Comma-separated device names to configure (e.g., R1,R3)")
    args = parser.parse_args()

    host = require_host(args.host)

    target_devices = DEVICES
    if args.node:
        requested = [n.strip() for n in args.node.split(",")]
        invalid = [n for n in requested if n not in DEVICES]
        if invalid:
            print(f"[!] Invalid device(s): {', '.join(invalid)}", file=sys.stderr)
            print(f"    Available: {', '.join(DEVICES)}", file=sys.stderr)
            return 2
        target_devices = requested

    print("=" * 60)
    print(f"Lab Setup: routing-policy lab-01 (EVE-NG: {host})")
    print("Baseline: lab-00 solution state -- OSPF/IS-IS/BGP active.")
    if args.reset:
        print("[*] Reset mode enabled")
    if args.node:
        print(f"[*] Targeting devices: {', '.join(target_devices)}")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, list(DEVICES))
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    success, failed = 0, 0
    for name in target_devices:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab -- skipping.")
            failed += 1
            continue
        if push_config(host, name, port, reset=args.reset):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Setup complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
