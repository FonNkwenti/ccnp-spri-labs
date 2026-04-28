#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — R3 iBGP Session Stays in Active

Target:     R3 (PE East-2 — AS 65100)
Injects:    Removes `neighbor 10.0.0.4 update-source Loopback0` from R3's
            router bgp 65100 process.
Fault Type: Missing update-source (wrong TCP source IP)

Result:     R3's iBGP TCP connection to R4 originates from the physical
            egress interface IP instead of Loopback0. R4 expects a connection
            from 10.0.0.3 (R3's loopback) and rejects the session.
            `show ip bgp summary` on R3 shows 10.0.0.4 permanently in
            Active state.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01-route-reflectors -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover  # noqa: E402

DEVICE_NAME = "R3"
DEFAULT_LAB_PATH = "ccnp-spri/bgp/lab-01-route-reflectors.unl"
FAULT_COMMANDS = [
    "router bgp 65100",
    "no neighbor 10.0.0.4 update-source Loopback0",
]

# Pre-flight: read BGP running config to verify known-good state.
# Removing update-source leaves no unique string, so PREFLIGHT_FAULT_MARKER
# is a sentinel that is never present; idempotency is enforced by checking
# the solution marker is still present.
PREFLIGHT_CMD = "show running-config | section router bgp"
# Present only in the known-good (solution) state.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.0.4 update-source Loopback0"
# Sentinel: this string is never in the running-config.
PREFLIGHT_FAULT_MARKER = "neighbor 10.0.0.4 update-source __FAULT_INJECTED__"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: fault already appears to be injected.")
        print("    Restore with apply_solution.py before re-injecting.")
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
    print("Fault Injection: Scenario 02 -- R3 iBGP Session in Active")
    print("=" * 60)

    try:
        args.lab_path, ports = resolve_and_discover(host, args.lab_path, [DEVICE_NAME])
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab '{args.lab_path}'.")
        return 3

    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)

        post_check = conn.send_command(PREFLIGHT_CMD)
        if PREFLIGHT_SOLUTION_MARKER in post_check:
            print("[!] Verification failed: update-source Loopback0 is still present on R3.")
            print("    The no-command may have been sent in the wrong config context.")
            print("    Run apply_solution.py to reset, then retry.")
            return 4

        # Hard reset forces R3 to reconnect using the physical interface IP
        # (the fault). A soft reset is not sufficient — the existing TCP session
        # was established with the loopback IP and stays up until torn down.
        print("[*] Resetting BGP session to manifest fault on R3 ...")
        conn.send_command("clear ip bgp 10.0.0.4", expect_string=r"#")

        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
