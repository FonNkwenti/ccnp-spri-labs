#!/usr/bin/env python3
"""
Solution Restoration -- Lab 06: BGP Confederations

Reads per-device configs from solutions/ and pushes them to all affected
devices, returning the lab to the known-good state after fault injection.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --reset          # soft-reset before restore
    python3 apply_solution.py --host <eve-ng-ip> --node R2        # restore one device
    python3 apply_solution.py --host <eve-ng-ip> --reset --node R5  # soft-reset + restore one device

Exit codes:
    0 -- all devices restored
    1 -- one or more devices failed to restore
    2 -- --host not set (placeholder value detected)
    3 -- EVE-NG connectivity or port discovery error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-06-confederations -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover, soft_reset_device  # noqa: E402

# solutions/ is two levels above this script (lab root)
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

DEFAULT_LAB_PATH = "ccnp-spri/bgp/lab-06-confederations.unl"

# All devices affected by any scenario — restored in order.
# Scenario 01 touches R2; Scenario 02 touches R3; Scenario 03 touches R5.
# All six devices included so a full domain restore returns every router to known-good.
RESTORE_TARGETS = [
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
]


def restore_device(host: str, ports: dict, name: str, *, reset: bool) -> bool:
    port = ports.get(name)
    if port is None:
        print(f"[!] {name} not found in lab ports -- skipping.")
        return False

    cfg_file = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"[!] {cfg_file} not found -- skipping {name}.")
        return False

    print(f"[*] Restoring {name} on {host}:{port} ...")
    try:
        if reset:
            soft_reset_device(host, port)

        conn = connect_node(host, port)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!")
        ]
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"[+] {name} restored.")
        return True
    except Exception as exc:
        print(f"[!] {name} restore failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore lab to known-good state")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Soft-reset before restoring: default interfaces and remove routing protocols")
    parser.add_argument("--node", default=None,
                        help="Restore a single device only (e.g. R2). Omit to restore all targets.")
    args = parser.parse_args()

    host = require_host(args.host)

    if args.node:
        if args.node not in RESTORE_TARGETS:
            print(f"[!] '{args.node}' is not a valid target. Choose from: {', '.join(RESTORE_TARGETS)}",
                  file=sys.stderr)
            return 1
        targets = [args.node]
    else:
        targets = RESTORE_TARGETS

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, list(RESTORE_TARGETS))
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    success, failed = 0, 0
    for name in targets:
        if restore_device(host, ports, name, reset=args.reset):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Restoration complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
