#!/usr/bin/env python3
"""
Lab Setup — lab-02-rpl-vs-route-maps

Pushes initial configs to all lab devices via EVE-NG console ports.
Ports are discovered at runtime via the EVE-NG REST API.

XR1 and XR2 use the cisco_xr_telnet netmiko driver (candidate-config/commit
model). IOSv nodes (R1-R4) use the default cisco_ios_telnet driver.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>

All nodes must be started in EVE-NG before running this script.
XR nodes require ~10 min boot time — wait for the XRv9k boot sequence to
complete before running setup or the telnet session will be refused.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover, soft_reset_device  # noqa: E402

INITIAL_CONFIGS_DIR = SCRIPT_DIR / "initial-configs"

DEFAULT_LAB_PATH = "ccnp-spri/routing-policy/lab-02-rpl-vs-route-maps.unl"

# IOS devices use cisco_ios_telnet (default); XR devices use cisco_xr_telnet.
DEVICES = {
    "R1": "cisco_ios_telnet",
    "R2": "cisco_ios_telnet",
    "R3": "cisco_ios_telnet",
    "R4": "cisco_ios_telnet",
    "XR1": "cisco_xr_telnet",
    "XR2": "cisco_xr_telnet",
}


def push_config(host: str, name: str, port: int, device_type: str) -> bool:
    cfg_file = INITIAL_CONFIGS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"  [!] Config file not found: {cfg_file}")
        return False

    print(f"[*] Connecting to {name} on {host}:{port} ({device_type}) ...")
    try:
        conn = connect_node(host, port, device_type=device_type)
        commands = [
            line.strip()
            for line in cfg_file.read_text().splitlines()
            if line.strip() and not line.startswith("!")
        ]
        conn.send_config_set(commands)
        conn.save_config()
        conn.disconnect()
        print(f"[+] {name} configured.")
        return True
    except Exception as exc:
        print(f"  [!] {name} failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Push initial configs to lab nodes")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Soft-reset before configuring: default all interfaces and remove routing protocols")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print(f"Lab Setup: lab-02-rpl-vs-route-maps (EVE-NG: {host})")
    print("=" * 60)
    print("NOTE: XR1 and XR2 require ~10 min to boot. If this is a fresh")
    print("      EVE-NG start, wait for the XRv9k boot sequence to finish")
    print("      before running setup or the telnet session will be refused.")
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
        if push_config(host, name, port, device_type):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Setup complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
