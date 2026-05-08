#!/usr/bin/env python3
"""
Apply full solution configs to restore lab to known-good state.

Reads solution configs from ../../solutions/ and pushes them to all devices.
Supports --reset for soft-reset before applying, and --node for single-device restore.
Ports are discovered at runtime via EVE-NG REST API.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --node P2
    python3 apply_solution.py --host <eve-ng-ip> --reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOLUTIONS_DIR = (SCRIPT_DIR / ".." / ".." / "solutions").resolve()
# Depth: scripts/fault-injection -> scripts -> lab-00-srv6-control-plane -> srv6 -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host, soft_reset_device  # noqa: E402

RESTORE_TARGETS = {
    "P1": "cisco_xr_telnet",
    "P2": "cisco_xr_telnet",
    "P3": "cisco_xr_telnet",
    "P4": "cisco_xr_telnet",
    "PE1": "cisco_xr_telnet",
    "PE2": "cisco_xr_telnet",
}


def push_solution(host: str, name: str, port: int, device_type: str, *, reset: bool = False) -> bool:
    cfg_file = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"  [!] Solution not found: {cfg_file}")
        return False

    print(f"[*] Restoring {name} ({host}:{port}) ...")
    try:
        if reset:
            soft_reset_device(host, port)
        conn = connect_node(host, port, device_type=device_type)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!") and line.strip() != "end"
        ]
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"[+] {name} restored.")
        return True
    except Exception as exc:
        print(f"  [!] {name} restore failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore lab to solution state")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--node", default=None,
                        help="Restore a single device (e.g. P2) instead of all")
    parser.add_argument("--reset", action="store_true",
                        help="Soft-reset before applying config")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    host = require_host(args.host)

    targets = RESTORE_TARGETS
    if args.node:
        if args.node not in RESTORE_TARGETS:
            print(f"[!] Unknown device: {args.node}. Valid: {list(RESTORE_TARGETS)}",
                  file=sys.stderr)
            return 1
        targets = {args.node: RESTORE_TARGETS[args.node]}

    if args.lab_path:
        lab_path = args.lab_path
    else:
        lab_path = find_open_lab(host, node_names=list(targets))
        if lab_path is None:
            print("[!] No running lab found. Start all nodes first.", file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    print("=" * 60)
    print(f"Applying solutions (EVE-NG: {host}, lab: {lab_path})")
    print("=" * 60)

    success, failed = 0, 0
    for name, device_type in targets.items():
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab — skipping.")
            failed += 1
            continue
        if push_solution(host, name, port, device_type, reset=args.reset):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Restore complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
