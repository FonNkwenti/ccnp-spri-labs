#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — AS-Path ACL Regex Anchor Too Broad on R3

Target:     R3 (eBGP speaker — AS 65100, peer to R4/AS 65200)
Injects:    Replaces `ip as-path access-list 1 permit _65200$` with
            `ip as-path access-list 1 permit _65200_` on R3, then soft-clears
            the inbound eBGP session to activate the new pattern immediately.
Fault Type: AS-Path Regular Expression Error (missing end anchor)

Result:     `show ip as-path-access-list 1` shows the trailing underscore
            pattern (_65200_) instead of the end-anchor pattern (_65200$).
            In production this would match AS 65200 as a transit AS (e.g.
            AS_PATH "65200 65300"), admitting routes that should be blocked.
            In this lab topology the observable symptom is the wrong regex
            shown in the ACL — student must recognise that _ matches start,
            end, space, or comma but $ anchors to end-of-string only.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-01 -> routing-policy -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "no ip as-path access-list 1 permit _65200$",
    "ip as-path access-list 1 permit _65200_",
    "do clear ip bgp 10.1.34.4 soft in",
]

# Pre-flight: verify the AS-path ACL has the correct end-anchored pattern.
PREFLIGHT_CMD = "show ip as-path-access-list 1"
# Fault already active if the unanchored pattern is present.
PREFLIGHT_FAULT_MARKER = "permit _65200_"
# Known-good solution state marker.
PREFLIGHT_SOLUTION_MARKER = "permit _65200$"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 03 appears already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
