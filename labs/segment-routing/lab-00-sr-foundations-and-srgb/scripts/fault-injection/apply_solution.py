#!/usr/bin/env python3
"""
Solution Restoration -- SR Foundations and SRGB Lab (lab-00-sr-foundations-and-srgb)

Reads per-device configs from solutions/ and pushes them to all affected
devices, returning the lab to the known-good state after fault injection.

All devices (R3, R4) are IOS-XRv 9000 and use the cisco_xr_telnet driver.
IOS-XR uses candidate-config/commit -- solution configs must include 'commit'.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --node R3    # restore one device
    python3 apply_solution.py --host <eve-ng-ip> --node R4    # restore one device

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
# Depth: fault-injection -> scripts -> lab-00-sr-foundations-and-srgb -> segment-routing -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import (  # noqa: E402
    EveNgError,
    connect_node,
    discover_ports,
    find_open_lab,
    push_config as _xr_push,
    require_host,
)

# solutions/ is two levels above this script (lab root / scripts / fault-injection)
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

# Only R3 and R4 are faulted across scenarios -- restored in order.
RESTORE_TARGETS = ["R1", "R2", "R3", "R4"]

XR_USERNAME = "fon"
XR_PASSWORD = "cisco123"


def restore_device(host: str, ports: dict, name: str) -> bool:
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
        conn = connect_node(host, port, device_type="cisco_xr_telnet",
                            username=XR_USERNAME, password=XR_PASSWORD)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!") and line.strip() != "end"
        ]
        _xr_push(conn, commands, "cisco_xr_telnet")
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
    parser.add_argument("--node", default=None,
                        help="Restore a single device only (e.g. R3). Omit to restore all targets.")
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
        if restore_device(host, ports, name):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Restoration complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
