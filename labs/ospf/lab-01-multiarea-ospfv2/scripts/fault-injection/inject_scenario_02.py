#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 — R1 Cannot Reach R5 Loopback1

Target:     R5 (OSPF process 1)
Injects:    Removes the network 172.16.5.0 0.0.0.255 area 3 statement from R5
Fault Type: Missing OSPF Network Statement (prefix not advertised)

Result:     Lo1 (172.16.5.0/24) is no longer in R5's OSPF process.
            R5's Type-1 LSA omits the Lo1 stub link; no Type-3 LSA for
            172.16.5.0/24 is generated; R1 cannot reach 172.16.5.1.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01-multiarea-ospfv2 -> ospf -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host, resolve_and_discover  # noqa: E402


# Path to the EXISTING, ALREADY-IMPORTED lab in EVE-NG — used only for port
# discovery via the REST API. This does NOT create or modify the .unl file.
DEFAULT_LAB_PATH = "ccnp-spri/ospf/lab-01-multiarea-ospfv2.unl"

DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 172.16.5.0 0.0.0.255 area 3",
]

# Pre-flight: check the OSPF process config on R5 to verify Lo1 network
# statement is present (known-good state) before injecting.
PREFLIGHT_CMD = "show running-config | section router ospf"
# This fault is a pure removal — there is no string that appears only after
# injection. Set to a sentinel that can never be present in IOS config output
# so the second pre-flight guard is effectively disabled; the solution-marker
# check (absence of the network statement) is the real guard here.
PREFLIGHT_FAULT_MARKER = "__SENTINEL_NEVER_PRESENT__"
# If this string is absent → Lo1 already removed from OSPF, bail out.
PREFLIGHT_SOLUTION_MARKER = "network 172.16.5.0 0.0.0.255 area 3"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        print("    (Lo1 network statement already absent — scenario may already be active.)")
        return False
    # PREFLIGHT_FAULT_MARKER is a sentinel; this branch is never reached in
    # normal operation but is kept to preserve the standard preflight pattern.
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check — use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 — R1 Cannot Reach R5 Loopback1")
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
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
