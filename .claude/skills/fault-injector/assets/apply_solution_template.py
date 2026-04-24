#!/usr/bin/env python3
"""
Solution Restoration — [LAB_TITLE]

Reads per-device configs from solutions/ and pushes them to all affected
devices, returning the lab to the known-good state after fault injection.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --reset   # erase before restore

Exit codes:
    0 — all devices restored
    1 — one or more devices failed to restore
    2 — --host not set (placeholder value detected)
    3 — EVE-NG connectivity or port discovery error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-NN -> <topic> -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402

# solutions/ is two levels above this script (lab root)
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "[TOPIC]/[LAB_SLUG].unl"

# All devices affected by the troubleshooting scenarios — restored in order.
RESTORE_TARGETS = [
    "[DEVICE_NAME_1]",
    "[DEVICE_NAME_2]",
]


def restore_device(host: str, ports: dict, name: str, *, reset: bool) -> bool:
    port = ports.get(name)
    if port is None:
        print(f"[!] {name} not found in lab ports — skipping.")
        return False

    cfg_file = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"[!] {cfg_file} not found — skipping {name}.")
        return False

    print(f"[*] Restoring {name} on {host}:{port} ...")
    try:
        if reset:
            erase_device_config(host, name, port)

        conn = connect_node(host, port)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!")
        ]
        conn.send_config_set(commands)
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
                        help="Erase device config before restoring (full write erase)")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    success, failed = 0, 0
    for name in RESTORE_TARGETS:
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
