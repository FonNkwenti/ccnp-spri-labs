#!/usr/bin/env python3
"""
Lab Setup — SR Migration: LDP Coexistence, Mapping Server, SR-Prefer (Segment Routing Lab 02)

Pushes initial configs to all lab devices via EVE-NG console ports.
Ports are discovered at runtime via the EVE-NG REST API — no hardcoded ports needed.

All nodes are IOS-XRv 9000 and use the cisco_xr_telnet Netmiko driver.
IOS-XRv 9000 nodes take 8-12 minutes to boot after power-on — wait for the
RP/0/0/CPU0:<hostname># prompt before running setup.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>

The lab .unl must already be imported into EVE-NG and all nodes started before
running this script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: lab-02-sr-migration-ldp-coexistence/ -> segment-routing/ -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "common" / "tools"))
from eve_ng import (  # noqa: E402
    EveNgError,
    connect_node,
    push_config as _xr_push,
    require_host,
    resolve_and_discover,
    soft_reset_device,
)

INITIAL_CONFIGS_DIR = SCRIPT_DIR / "initial-configs"

DEFAULT_LAB_PATH = "ccnp-spri/segment-routing/lab-02-sr-migration-ldp-coexistence.unl"

# All nodes are IOS-XRv 9000.
DEVICES = {
    "R1": "cisco_xr_telnet",
    "R2": "cisco_xr_telnet",
    "R3": "cisco_xr_telnet",
    "R4": "cisco_xr_telnet",
}

# Credentials for XRv9k nodes in this lab (local user database).
XR_USERNAME = "fon"
XR_PASSWORD = "cisco123"


def push_config(host: str, name: str, port: int, device_type: str, *, reset: bool = False) -> bool:
    cfg_file = INITIAL_CONFIGS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"  [!] Config file not found: {cfg_file}")
        return False

    print(f"[*] Connecting to {name} on {host}:{port} ({device_type}) ...")
    try:
        if reset:
            soft_reset_device(host, port)

        username = XR_USERNAME if device_type.startswith("cisco_xr") else ""
        password = XR_PASSWORD if device_type.startswith("cisco_xr") else ""
        conn = connect_node(host, port, device_type=device_type,
                            username=username, password=password)

        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!") and line.strip() != "end"
        ]
        # _xr_push appends 'commit' inside config mode for XR nodes so the
        # candidate config is committed before exit_config_mode() fires.
        # For IOS it falls through to send_config_set + save_config.
        _xr_push(conn, commands, device_type)
        conn.disconnect()
        print(f"[+] {name} configured.")
        return True
    except Exception as exc:
        print(f"  [!] {name} failed: {exc!r}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Push initial configs to lab nodes")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Soft-reset before configuring: remove existing routing and SR config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print(f"Lab Setup: SR Migration — LDP Coexistence (EVE-NG: {host})")
    print("NOTE: IOS-XRv 9000 nodes require 8-12 min to boot. Wait for the")
    print("      RP/0/0/CPU0 prompt on all nodes before running setup.")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, list(DEVICES))
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    success, failed = 0, 0
    for name, device_type in DEVICES.items():
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab — skipping.")
            failed += 1
            continue
        if push_config(host, name, port, device_type, reset=args.reset):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Setup complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
