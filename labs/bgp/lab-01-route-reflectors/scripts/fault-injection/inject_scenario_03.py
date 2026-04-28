#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 — Prefixes in BGP Table Not Installed in RIB

Target:     R2 (PE East-1 — AS 65100)
Injects:    Removes `neighbor 10.0.0.4 next-hop-self` and
            `neighbor 10.0.0.5 next-hop-self` from R2's address-family ipv4.
Fault Type: Missing next-hop-self on ingress PE

Result:     Routes from Customer A (AS 65001) are advertised to iBGP peers
            with the original eBGP next-hop (10.1.12.1 -- R1's physical IP),
            which is not in the OSPF domain. On R3, `show ip bgp` shows
            172.16.1.0/24 with status `r` (next-hop unresolvable) and
            `show ip route bgp` is empty.

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

DEVICE_NAME = "R2"
DEFAULT_LAB_PATH = "ccnp-spri/bgp/lab-01-route-reflectors.unl"
FAULT_COMMANDS = [
    "router bgp 65100",
    "address-family ipv4",
    "no neighbor 10.0.0.4 next-hop-self",
    "no neighbor 10.0.0.5 next-hop-self",
    "exit-address-family",
]

# Pre-flight: read BGP running config to verify known-good state.
# Removing next-hop-self leaves no unique string, so PREFLIGHT_FAULT_MARKER
# is a sentinel that is never present; idempotency is enforced by checking
# the solution marker is still present.
PREFLIGHT_CMD = "show running-config | section router bgp"
# Present only in the known-good (solution) state.
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.0.4 next-hop-self"
# Sentinel: this string is never in the running-config.
PREFLIGHT_FAULT_MARKER = "neighbor 10.0.0.4 next-hop-self __FAULT_INJECTED__"


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
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path in EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip sanity check -- use only if lab state is known-good")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 -- Prefixes Not Installed in RIB")
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
        # cmd_verify=False prevents Netmiko racing ahead on nested config-mode
        # prompt transitions (config -> config-router -> config-router-af).
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)

        post_check = conn.send_command(PREFLIGHT_CMD)
        if PREFLIGHT_SOLUTION_MARKER in post_check:
            print("[!] Verification failed: next-hop-self is still present on R2.")
            print("    The no-command may have been sent in the wrong config context.")
            print("    Run apply_solution.py to reset, then retry.")
            return 4

        # Soft outbound reset forces R2 to re-advertise all routes to iBGP peers
        # under the new policy (without next-hop-self). Without this, existing
        # route entries on R3/R5 retain the loopback next-hop until the next
        # BGP update cycle.
        print("[*] Triggering BGP soft reset to manifest fault on downstream peers ...")
        conn.send_command("clear ip bgp * soft out", expect_string=r"#")

        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
