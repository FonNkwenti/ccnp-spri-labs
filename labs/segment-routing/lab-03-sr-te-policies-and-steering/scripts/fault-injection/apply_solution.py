#!/usr/bin/env python3
"""
Solution Restoration — SR-TE Policies, Constraints, and Automated Steering (Lab 03)

Reads per-device configs from solutions/ and pushes them to all affected
devices, returning the lab to the known-good state after fault injection.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --reset          # soft-reset before restore
    python3 apply_solution.py --host <eve-ng-ip> --node R1        # restore one device
    python3 apply_solution.py --host <eve-ng-ip> --reset --node R1  # soft-reset + restore one device

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
# Depth: scripts/fault-injection -> scripts -> lab-03 -> segment-routing -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import (  # noqa: E402
    EveNgError,
    connect_node,
    discover_ports,
    find_open_lab,
    push_config as _xr_push,
    require_host,
    soft_reset_device,
)

# solutions/ is two directory levels above this script (lab root / solutions/)
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

# All devices affected by any troubleshooting scenario — restored in order.
RESTORE_TARGETS = ["R1", "R2", "R3", "R4", "CE1", "CE2"]

# Device type map: IOS-XRv 9000 routers use cisco_xr_telnet; IOSv CE devices use cisco_ios_telnet.
DEVICE_TYPES = {
    "R1": "cisco_xr_telnet",
    "R2": "cisco_xr_telnet",
    "R3": "cisco_xr_telnet",
    "R4": "cisco_xr_telnet",
    "CE1": "cisco_ios_telnet",
    "CE2": "cisco_ios_telnet",
}

XR_USERNAME = "fon"
XR_PASSWORD = "cisco123"


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
            soft_reset_device(host, port, cfg_file)

        device_type = DEVICE_TYPES.get(name, "cisco_xr_telnet")
        username = XR_USERNAME if device_type.startswith("cisco_xr") else ""
        password = XR_PASSWORD if device_type.startswith("cisco_xr") else ""
        conn = connect_node(host, port, device_type=device_type,
                            username=username, password=password)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!") and line.strip() != "end"
        ]
        _xr_push(conn, commands, device_type)
        conn.disconnect()
        print(f"[+] {name} restored.")
        return True
    except Exception as exc:
        print(f"[!] {name} restore failed: {exc!r}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore lab to known-good state")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--reset", action="store_true",
                        help="Soft-reset before restoring: default all interfaces and remove routing protocols")
    parser.add_argument("--node", default=None,
                        help="Restore a single device only (e.g. R1). Omit to restore all targets.")
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

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=RESTORE_TARGETS)
        if lab_path is None:
            print("[!] No running lab found. Start all nodes in EVE-NG first.", file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
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
