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


def find_open_lab(
    host: str,
    node_names: list[str],
    username: str = "admin",
    password: str = "eve",
) -> str | None:
    """Walk the EVE-NG folder tree and return the path of the first lab whose
    running nodes include all names in node_names.

    Searches breadth-first starting from the root folder. Returns a path
    suitable for passing to discover_ports(), e.g.
    'ccnp-spri/ospf/lab-03-summarization-stub-nssa.unl'.
    Returns None if no matching lab is found.
    """
    try:
        session = _eve_session(host, username, password)
    except requests.RequestException as exc:
        raise EveNgError(f"EVE-NG login failed at {host}: {exc}") from exc

    def _list_folder(path: str) -> tuple[list[str], list[str]]:
        # Root folder requires trailing slash: /api/folders/
        # Subfolders do not: /api/folders/ccnp-spri/ospf
        url = f"http://{host}/api/folders/{path}"
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException:
            return [], []
        data = resp.json().get("data", {})
        prefix = f"{path}/" if path else ""
        lab_paths = [f"{prefix}{d['file']}" for d in data.get("labs", []) if d.get("file")]
        # EVE-NG uses "folders" (not "dirs"); filter ".." parent entries
        subdirs = [
            f"{prefix}{d['name']}"
            for d in data.get("folders", [])
            if d.get("name") and d["name"] != ".."
        ]
        return lab_paths, subdirs

    # Pass 1: walk the full folder tree to collect all .unl paths.
    # discover_ports() must NOT be called here — EVE-NG tracks the open lab
    # per user, so opening any lab via the API will cause subsequent folder
    # listing requests to return 412 ("lab is open, close it first").
    all_lab_paths: list[str] = []
    visited: set[str] = set()
    queue = [""]
    while queue:
        folder = queue.pop(0)
        if folder in visited:
            continue
        visited.add(folder)
        lab_paths, subdirs = _list_folder(folder)
        all_lab_paths.extend(lab_paths)
        queue.extend(subdirs)

    # Pass 2: now that folder browsing is complete, check each lab for the
    # expected running nodes.
    for lab_path in all_lab_paths:
        try:
            ports = discover_ports(host, lab_path, username, password)
            if all(name in ports for name in node_names):
                return lab_path
        except EveNgError:
            continue
    return None


def resolve_and_discover(
    host: str,
    default_lab_path: str,
    node_names: list[str],
    username: str = "admin",
    password: str = "eve",
) -> tuple[str, dict[str, int]]:
    """Resolve the lab on EVE-NG and return (lab_path, port_map).

    Hybrid strategy: try ``default_lab_path`` first as a fast path; on miss
    (HTTP 404, or the lab does not contain all expected nodes), fall back to
    :func:`find_open_lab` which walks the EVE-NG folder tree. This insulates
    callers from how the user organized the lab in EVE-NG (e.g. moved into a
    different parent folder, renamed the .unl, opened via the GUI from a
    custom location).

    Raises :class:`EveNgError` if neither the fast path nor the folder walk
    finds a lab whose running nodes include every name in ``node_names``.
    """
    if default_lab_path:
        try:
            ports = discover_ports(host, default_lab_path, username, password)
            if all(n in ports for n in node_names):
                return default_lab_path, ports
        except EveNgError:
            pass
    found = find_open_lab(host, node_names, username, password)
    if found:
        ports = discover_ports(host, found, username, password)
        return found, ports
    raise EveNgError(
        f"No EVE-NG lab found containing nodes {node_names}.\n"
        f"Tried default path '{default_lab_path}' and folder-tree search.\n"
        "Ensure the lab is imported and all nodes are started."
    )


def connect_node(
    host: str,
    port: int,
    timeout: int = 30,
    device_type: str = "cisco_ios_telnet",
):
    """Open a Netmiko telnet session to an EVE-NG console port in enable mode.

    Returns the connection already in privilege mode so callers can immediately
    call send_config_set() without a separate enable() step.

    Pass device_type="cisco_xr_telnet" for IOS-XR (XRv9k) nodes. XR has no
    enable mode and uses candidate-config/commit — the IOS-specific enable()
    and logging-console suppression steps are skipped automatically.

    fast_cli=False and global_delay_factor=2 are required for EVE-NG console
    ports: buffered boot/session output in the telnet stream causes Netmiko to
    miss the prompt during session setup at default timing.
    """
    if ConnectHandler is None:
        raise EveNgError(
            "netmiko is not installed. Run: pip install netmiko"
        )
    conn = ConnectHandler(
        device_type=device_type,
        host=host,
        port=port,
        username="",
        password="",
        secret="",
        timeout=timeout,
        fast_cli=False,
        global_delay_factor=2,
    )
    if not device_type.startswith("cisco_xr"):
        # Drain any stale telnet buffer from previous sessions before enable()
        # searches for '#'. EVE-NG telnet ports are persistent — IOS-XE platforms
        # (CSR1000v) generate more post-save syslog output than IOSv, so without
        # this drain the buffered %SYS-5-CONFIG_I line causes enable() to time out
        # with "Pattern not detected: '#'".
        time.sleep(1)
        conn.clear_buffer()
        conn.enable()
        # A previous session may have left the router in config or config-if mode.
        # Netmiko's enable() sees '#' in the prompt and considers the device enabled
        # without checking whether it is also in config mode. Only send 'end' when
        # check_config_mode() confirms we are in config mode — sending 'end' from
        # exec mode causes IOS to attempt DNS resolution ("end" treated as hostname),
        # which hangs on devices that don't yet have 'no ip domain lookup' configured.
        if conn.check_config_mode():
            conn.send_command("end", expect_string=r"#", read_timeout=15)
        # Silence console logging so that any IOS syslog messages buffered from a
        # previous session (e.g. %SYS-5-CONFIG_I after save_config) do not corrupt
        # subsequent command/prompt matching. cmd_verify=False avoids echo-matching
        # against potentially stale buffer content.
        conn.send_config_set(["no logging console"], cmd_verify=False)
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
    # IOSv naming (GigabitEthernet0/x)
    "default interface GigabitEthernet0/0",
    "default interface GigabitEthernet0/1",
    "default interface GigabitEthernet0/2",
    "default interface GigabitEthernet0/3",
    # CSR1000v naming (GigabitEthernet1-4, no slot prefix)
    "default interface GigabitEthernet1",
    "default interface GigabitEthernet2",
    "default interface GigabitEthernet3",
    "default interface GigabitEthernet4",
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
