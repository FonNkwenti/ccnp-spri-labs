#!/usr/bin/env python3
"""
Solution Restoration: BGP Capstone Troubleshooting Lab.
Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-08 -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host, soft_reset_device  # noqa: E402

# solutions/ is two levels above this script (lab root)
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

RESTORE_TARGETS = [
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "R7",
]


def restore_device(host: str, ports: dict, name: str, *, reset: bool) -> bool:
    port = ports.get(name)
    if port is None:
        print("[!] Target device not found in lab ports -- skipping.")
        return False

    cfg_file = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_file.exists():
        print("[!] Solution config not found -- skipping target device.")
        return False

    print(f"[*] Restoring target device on {host}:{port} ...")
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
        print("[+] Target device restored.")
        return True
    except Exception as exc:
        print(f"[!] Target device restore failed: {exc}")
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
                        help="Restore a single device only. Omit to restore all targets.")
    args = parser.parse_args()

    host = require_host(args.host)

    if args.node:
        if args.node not in RESTORE_TARGETS:
            print(f"[!] '{args.node}' is not a valid restore target.", file=sys.stderr)
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
        lab_path = find_open_lab(host, node_names=list(RESTORE_TARGETS))
        if lab_path is None:
            print("[!] No running lab found with required devices. Start all nodes first.",
                  file=sys.stderr)
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
