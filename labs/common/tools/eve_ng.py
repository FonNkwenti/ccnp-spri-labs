"""
eve_ng.py — Shared EVE-NG automation library.

Provides port discovery, Netmiko console connections, and config helpers
used by setup_lab.py, inject scripts, and apply_solution.py across all
lab topics. All scripts add labs/common/tools/ to sys.path and import from here.
"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import requests

try:
    from netmiko import ConnectHandler
except ImportError:
    ConnectHandler = None  # type: ignore[assignment,misc]


class EveNgError(RuntimeError):
    """Raised when EVE-NG REST API is unreachable or returns an error."""


# Placeholder value written into every template — require_host() rejects it.
_PLACEHOLDER_HOST = "192.168.x.x"


def require_host(host: str) -> str:
    """Return host if valid; exit with code 2 if it is still the placeholder."""
    if host == _PLACEHOLDER_HOST or not host:
        print(
            "[!] --host is required. Set it to your EVE-NG server IP, e.g.:\n"
            "    python3 setup_lab.py --host 192.168.1.50",
            file=sys.stderr,
        )
        sys.exit(2)
    return host


def _extract_port(url: str) -> int | None:
    """Extract the telnet console port from an EVE-NG node URL.

    Handles two formats:
    - Legacy:  telnet://host:32769
    - EVE-NG v5+: /html5/#/client/<base64>?token=...
      where base64 decodes to b'32769\\x00c\\x00mysql'
    """
    if url.startswith("telnet://") and ":" in url:
        try:
            return int(url.rsplit(":", 1)[-1])
        except ValueError:
            return None
    if "/client/" in url:
        try:
            b64 = url.split("/client/")[1].split("?")[0]
            decoded = base64.b64decode(b64).decode("latin-1")
            return int(decoded.split("\x00")[0])
        except (ValueError, IndexError):
            return None
    return None


def _eve_session(host: str, username: str = "admin", password: str = "eve") -> requests.Session:
    session = requests.Session()
    resp = session.post(
        f"http://{host}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return session


def discover_ports(
    host: str,
    lab_path: str,
    username: str = "admin",
    password: str = "eve",
) -> dict[str, int]:
    """Return {node_name: telnet_port} for a running EVE-NG lab.

    lab_path is relative to the EVE-NG lab root, e.g. 'ospf/lab-00-single-area-ospfv2.unl'.
    Ports are assigned dynamically at runtime — never hardcode them.
    """
    try:
        session = _eve_session(host, username, password)
        resp = session.get(f"http://{host}/api/labs/{lab_path}/nodes", timeout=10)
        resp.raise_for_status()
        nodes = resp.json().get("data", {})
    except requests.RequestException as exc:
        raise EveNgError(
            f"EVE-NG API unreachable at {host}: {exc}\n"
            "Ensure the lab is imported and all nodes are started."
        ) from exc

    port_map: dict[str, int] = {}
    for node in nodes.values():
        name = node.get("name", "")
        url = node.get("url", "")
        if name and url:
            port = _extract_port(url)
            if port is not None:
                port_map[name] = port
    return port_map


def connect_node(host: str, port: int, timeout: int = 30):
    """Open a Netmiko telnet session to an EVE-NG console port in enable mode.

    Returns the connection already in privilege mode so callers can immediately
    call send_config_set() without a separate enable() step.

    fast_cli=False and global_delay_factor=2 are required for EVE-NG console
    ports: buffered boot/session output in the telnet stream causes Netmiko to
    miss the prompt during session setup at default timing.
    """
    if ConnectHandler is None:
        raise EveNgError(
            "netmiko is not installed. Run: pip install netmiko"
        )
    conn = ConnectHandler(
        device_type="cisco_ios_telnet",
        host=host,
        port=port,
        username="",
        password="",
        secret="",
        timeout=timeout,
        fast_cli=False,
        global_delay_factor=2,
    )
    conn.enable()
    return conn


# All interfaces and routing protocols that any CCNP SPRI lab could configure.
# IOS silently ignores commands for interfaces that do not exist or have no config,
# so this list is safe to run on any device regardless of topology.
# Ordering matters:
#   1. logging synchronous — prevents log bursts from splitting a prompt mid-line
#      during the sweep itself.
#   2. interface defaults and routing-protocol removals — generate log messages.
#   3. no logging console (last) — stops IOS writing any further syslog to the
#      console port after disconnect. EVE-NG telnet buffers persist across
#      connections; without this, the next connect_node call reads the stale
#      %SYS-5-CONFIG_I line and Netmiko's handshake fails with "Pattern not detected".
_LAB_SWEEP_COMMANDS = [
    "line con 0",
    "logging synchronous",
    "exit",
    "default interface Loopback0",
    "default interface Loopback1",
    "default interface Loopback2",
    "default interface Loopback3",
    "default interface GigabitEthernet0/0",
    "default interface GigabitEthernet0/1",
    "default interface GigabitEthernet0/2",
    "default interface GigabitEthernet0/3",
    "no router ospf 1",
    "no router ospfv3 1",
    "no logging console",
]


def soft_reset_device(host: str, port: int) -> None:
    """Default all lab interfaces and remove OSPF processes.

    Runs a fixed sweep covering every interface and routing protocol used
    across all CCNP SPRI labs so that interfaces not present in the solution
    config (e.g. an unused port the student configured) are also cleared.
    Ends with 'no logging console' so IOS stops writing syslog to the console
    port after disconnect — prevents stale log lines from corrupting the next
    Netmiko session handshake on the shared EVE-NG telnet stream.
    Does NOT save config — the caller pushes the solution and saves afterward.
    """
    conn = connect_node(host, port)
    try:
        conn.send_config_set(_LAB_SWEEP_COMMANDS)
    finally:
        conn.disconnect()
    time.sleep(2)


def erase_device_config(host: str, name: str, port: int) -> bool:
    """Send 'write erase' to clear a device's startup-config without reloading.

    Uses expect_string to synchronize on IOS confirmation prompts so the
    device is still reachable when this function returns. Returns True on
    success, False on connection or command failure.
    """
    print(f"[*] {name}: erasing startup-config...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: connection failed — {exc}")
        return False
    try:
        # send_command_timing is used here because write erase prompts for
        # confirmation and then immediately returns to prompt — no reliable
        # terminating string to anchor expect_string on the second send.
        conn.send_command_timing("write erase")
        conn.send_command_timing("")   # press Enter to confirm
        print(f"[+] {name}: startup-config erased.")
        return True
    except Exception as exc:
        print(f"[!] {name}: erase failed — {exc}")
        return False
    finally:
        conn.disconnect()


def reload_device(host: str, name: str, port: int, wait: int = 180, poll_interval: int = 10):
    """Trigger a device reload and return an open connection when the device is back.

    Declines the startup-config save prompt (assumes erase_device_config was
    already called) so the device boots with an empty startup-config. Polls
    until the device accepts a Netmiko connection, then returns that live
    connection in enable mode so the caller can push config immediately without
    a second connect attempt. Returns None on timeout or connection failure.

    The caller is responsible for calling conn.disconnect() on the returned conn.
    """
    print(f"[*] {name}: sending reload (will wait up to {wait}s for reboot)...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: could not connect to send reload — {exc}")
        return None

    try:
        output = conn.send_command_timing("reload")
        if "save" in output.lower() or "modified" in output.lower():
            output = conn.send_command_timing("no")
        if "confirm" in output.lower() or "proceed" in output.lower():
            conn.send_command_timing("")
    except Exception:
        pass  # connection drop when reload fires is expected
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass

    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            conn = connect_node(host, port, timeout=30)
            # Suppress console log messages from splitting the prompt during
            # config push. On a fresh boot IOS sends interface/OSPF state
            # changes to the console which break Netmiko's prompt detection.
            conn.send_config_set(
                ["line con 0", "logging synchronous", "end"],
                cmd_verify=False,
            )
            print(f"[+] {name}: back online.")
            return conn  # caller must disconnect
        except Exception:
            remaining = max(0, int(deadline - time.monotonic()))
            print(f"[*] {name}: still rebooting ({remaining}s remaining)...")

    print(f"[!] {name}: did not come back up within {wait}s.")
    return None
