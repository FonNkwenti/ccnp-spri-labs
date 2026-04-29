#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- R5-R6 External Session Stuck in Active

Target:     R6 (AS 65002 External SP -- Gi0/0 link to R5)
Injects:    Changes R6's BGP MD5 password for neighbor 10.1.56.5 from
            CISCO_SP to WRONG_KEY, creating a password mismatch with R5.
Fault Type: MD5 TCP Authentication Password Mismatch

Result:     R5's eBGP session with R6 (10.1.56.6) is stuck in Active state.
            IP connectivity between R5 and R6 is unaffected (ping succeeds).
            TCP sessions never complete because R5's MD5 signatures are rejected
            by R6's wrong key. No BGP NOTIFICATION is sent -- the session simply
            times out on hold-timer expiry and retries indefinitely.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-03 -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R6"
FAULT_COMMANDS = [
    "router bgp 65002",
    "no neighbor 10.1.56.5 password CISCO_SP",
    "neighbor 10.1.56.5 password WRONG_KEY",
]

# Pre-flight: check the BGP neighbor section on R6 to verify known-good state.
PREFLIGHT_CMD = "show running-config | section router bgp"
# If this string is already present -> fault already injected, bail out.
# NOTE: IOS may store passwords in encrypted (type-7) form; WRONG_KEY may not
# appear verbatim. This check is best-effort -- use --skip-preflight if it
# false-fires. The ttl-security SOLUTION_MARKER below is never encrypted.
PREFLIGHT_FAULT_MARKER = "neighbor 10.1.56.5 password WRONG_KEY"
# If this string is absent -> not in solution state, bail out.
# Use the ttl-security line (always present in solution, never encrypted) rather
# than the password line so this check is immune to IOS type-7 encryption.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.1.56.5 ttl-security hops 1"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    if args.lab_path:
        lab_path = args.lab_path
    else:
        print("[*] Detecting open lab in EVE-NG...")
        lab_path = find_open_lab(host, node_names=[DEVICE_NAME])
        if lab_path is None:
            print(f"[!] No running lab found with {DEVICE_NAME}. Start all nodes first.",
                  file=sys.stderr)
            return 3

    try:
        ports = discover_ports(host, lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab '{lab_path}'.")
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
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
