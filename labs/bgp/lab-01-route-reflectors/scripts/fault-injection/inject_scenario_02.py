#!/usr/bin/env python3
"""
Fault Injection: Scenario 02. Restore with: python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01-route-reflectors -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, require_host, resolve_and_discover  # noqa: E402

DEFAULT_LAB_PATH = "ccnp-spri/bgp/lab-01-route-reflectors.unl"
DEVICE_NAMES = ["R3", "R4"]

FAULT_COMMANDS = {
    "R3": ["router bgp 65100", "no neighbor 10.0.0.4 update-source Loopback0"],
    "R4": ["router bgp 65100", "no neighbor 10.0.0.3 update-source Loopback0"],
}

PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = {
    "R3": "neighbor 10.0.0.4 update-source Loopback0",
    "R4": "neighbor 10.0.0.3 update-source Loopback0",
}


def preflight(conn, device: str) -> bool:
    marker = PREFLIGHT_SOLUTION_MARKER[device]
    output = conn.send_command(PREFLIGHT_CMD)
    if marker not in output:
        print("[!] Pre-flight failed: lab not in expected pre-injection state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def inject(conn, device: str) -> bool:
    """Inject fault commands and verify the change landed. Returns True on success."""
    conn.send_config_set(FAULT_COMMANDS[device], cmd_verify=False)
    post = conn.send_command(PREFLIGHT_CMD)
    marker = PREFLIGHT_SOLUTION_MARKER[device]
    if marker in post:
        print(f"[!] Verification failed on {device}: '{marker}' is still present.")
        print("    The no-command may have been sent in the wrong config context.")
        print("    Run apply_solution.py to reset, then retry.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, DEVICE_NAMES)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    for device in DEVICE_NAMES:
        if device not in ports:
            print(f"[!] {device} not found in lab '{args.lab_path}'.")
            return 3

    # --- R3 ---
    print(f"[*] Connecting to R3 on {host}:{ports['R3']} ...")
    try:
        conn_r3 = connect_node(host, ports["R3"])
    except Exception as exc:
        print(f"[!] R3 connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn_r3, "R3"):
            return 4
        print("[*] Injecting fault on R3 ...")
        if not inject(conn_r3, "R3"):
            return 4
        conn_r3.save_config()
    finally:
        conn_r3.disconnect()

    # --- R4 ---
    print(f"[*] Connecting to R4 on {host}:{ports['R4']} ...")
    try:
        conn_r4 = connect_node(host, ports["R4"])
    except Exception as exc:
        print(f"[!] R4 connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn_r4, "R4"):
            return 4
        print("[*] Injecting fault on R4 ...")
        if not inject(conn_r4, "R4"):
            return 4

        # Hard reset tears down the existing session. Both sides retry from
        # physical interface IPs, which the respective peers reject.
        print("[*] Resetting BGP session to manifest fault ...")
        conn_r4.send_command("clear ip bgp 10.0.0.3", expect_string=r"#")

        conn_r4.save_config()
    finally:
        conn_r4.disconnect()

    print("[+] Fault injected on R3 and R4. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
