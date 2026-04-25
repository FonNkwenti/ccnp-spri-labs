"""
eve_ng.py — Shared EVE-NG automation library.

Provides port discovery, Netmiko console connections, and config helpers
used by setup_lab.py, inject scripts, and apply_solution.py across all
lab topics. All scripts add labs/common/tools/ to sys.path and import from here.
"""

from __future__ import annotations

import base64
import sys
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
    )
    conn.enable()
    return conn


def erase_device_config(host: str, name: str, port: int) -> None:
    """Issue 'write erase' and reload on a device, then wait for it to come back."""
    if ConnectHandler is None:
        raise EveNgError("netmiko is not installed.")
    conn = connect_node(host, port)
    try:
        conn.send_command_timing("write erase", strip_prompt=False, strip_command=False)
        conn.send_command_timing("\n", strip_prompt=False, strip_command=False)
        conn.send_command_timing("reload", strip_prompt=False, strip_command=False)
        conn.send_command_timing("\n", strip_prompt=False, strip_command=False)
    finally:
        conn.disconnect()
    # Caller is responsible for waiting for boot before pushing configs.
    print(f"[*] {name}: write erase + reload issued. Wait ~60s before restoring config.")
