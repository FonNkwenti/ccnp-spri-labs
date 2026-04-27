#!/usr/bin/env python3
"""
Lab Setup — BGP Lab 01: iBGP Route Reflectors and Cluster IDs

Pushes initial configs to all lab devices via EVE-NG console ports.
Ports are discovered at runtime via the EVE-NG REST API — no hardcoded ports needed.

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
# Depth: lab-01-route-reflectors/ -> bgp/ -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

INITIAL_CONFIGS_DIR = SCRIPT_DIR / "initial-configs"

# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "bgp/lab-01-route-reflectors.unl"

DEVICES = ["R1", "R2", "R3", "R4", "R5", "R6"]


def push_config(host: str, name: str, port: int) -> bool:
    cfg_file = INITIAL_CONFIGS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print(f"  [!] Config file not found: {cfg_file}")
        return False

    print(f"[*] Connecting to {name} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
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
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print(f"Lab Setup: BGP Lab 01 — Route Reflectors (EVE-NG: {host})")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    success, failed = 0, 0
    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab — skipping.")
            failed += 1
            continue
        if push_config(host, name, port):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Setup complete: {success} succeeded, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
