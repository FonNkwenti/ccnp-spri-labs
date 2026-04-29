#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 — External Prefix Suppressed by Dampening

Target:     R6 (Loopback1 — 172.16.6.1/24, eBGP peer toward R5)
Injects:    Shuts and re-enables R6's Loopback1 five times in quick succession,
            generating five BGP withdraw/re-advertise cycles for 172.16.6.0/24.
            Each withdrawal adds 1000 to the penalty on R5; five flaps accumulate
            a penalty of ~5000, well above the suppress-limit of 2000.
Fault Type: BGP Route Dampening (penalty accumulation via repeated interface flap)

Result:     172.16.6.0/24 shows the 'd' (dampened/suppressed) flag on R5 and is
            absent from the IP routing table of all SP core routers.
            The student must clear the dampening history to restore reachability.

NOTE: This script does NOT clear the dampening -- that is the student's task.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Depth: scripts/fault-injection -> scripts -> lab-04-dampening-dynamic -> bgp -> labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, find_open_lab, require_host  # noqa: E402

DEVICE_NAME = "R6"

# Number of shut/no-shut cycles — must exceed suppress-limit (2000) with 1000 penalty/flap
FLAP_COUNT = 5
# Seconds to pause between shut and no-shut within each cycle; allows BGP to register withdrawal
FLAP_PAUSE = 3

# Pre-flight: verify Lo1 is configured and up before flapping.
PREFLIGHT_CMD = "show running-config interface Loopback1"
# Present only in the known-good (Lo1 configured) state.
PREFLIGHT_SOLUTION_MARKER = "ip address 172.16.6.1 255.255.255.0"
# Sentinel: no string uniquely marks "flap already injected" in running-config.
PREFLIGHT_FAULT_MARKER = "__FAULT_01_ALREADY_INJECTED__"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print("[!] Pre-flight failed: fault already appears to be injected.")
        print("    Restore with apply_solution.py before re-injecting.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=None,
                        help="Lab .unl path in EVE-NG (auto-discovered if omitted)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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

        print(f"[*] Flapping R6 Loopback1 {FLAP_COUNT} times to accumulate dampening penalty on R5 ...")
        for i in range(1, FLAP_COUNT + 1):
            print(f"    Cycle {i}/{FLAP_COUNT}: shutting Loopback1 ...")
            conn.send_config_set(["interface Loopback1", "shutdown"])
            time.sleep(FLAP_PAUSE)
            print(f"    Cycle {i}/{FLAP_COUNT}: re-enabling Loopback1 ...")
            conn.send_config_set(["interface Loopback1", "no shutdown"])
            time.sleep(FLAP_PAUSE)

        # Leave Loopback1 up (stable) -- penalty on R5 will keep prefix suppressed
        # until manually cleared. Do NOT save config: flap is an operational action.
        print("[*] Flapping complete. Loopback1 left in 'no shutdown' state.")
        print("[*] Check R5: show ip bgp dampening dampened-paths")
        print("[*] Check R5: show ip bgp 172.16.6.0")
    finally:
        conn.disconnect()

    print(f"[+] Scenario 01 fault injected via {DEVICE_NAME}.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
