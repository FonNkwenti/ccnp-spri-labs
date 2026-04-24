# setup_lab.py — Reference

Every lab ships a `setup_lab.py` that authenticates to EVE-NG, starts the lab's
nodes, discovers console ports, and pushes the per-device files in
`initial-configs/` over telnet via Netmiko.

This document covers usage, flags, and the EVE-NG path conventions shared by
all labs in the repo.

---

## Prerequisites

```bash
pip install netmiko requests
```

The lab must already be imported into EVE-NG and visible in the web UI.
Default credentials assume `admin` / `eve` (the EVE-NG defaults).

---

## Basic Invocation

From the lab directory:

```bash
python setup_lab.py --host <eve-ng-ip>
```

This runs four steps:

1. Authenticate to the EVE-NG REST API
2. Start every node in the lab (skipped if already running) and wait 30s for IOSv boot
3. Discover console (telnet) ports for each node
4. Push the matching `initial-configs/<device>.cfg` to every device

---

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--host` | *(required)* | EVE-NG server IP or hostname |
| `--lab-path` | `<topic>/<lab-name>.unl` | Path of the lab on the EVE-NG server (relative to lab root). Override if you imported the lab to a different folder |
| `--username` | `admin` | EVE-NG username |
| `--password` | `eve` | EVE-NG password |
| `--no-push` | *(off)* | Skip the config push — only authenticate, start nodes, and report console ports |

---

## Lab Path Convention

EVE-NG stores every lab internally as `*.unl` on its filesystem regardless of how
the lab was built. The default `--lab-path` follows the repo's topic/lab naming:

```
<topic>/<lab-name>.unl
```

For example, `ospf/lab-00-single-area-ospfv2` resolves to
`ospf/lab-00-single-area-ospfv2.unl` on the EVE-NG server.

If you imported the lab into a different folder in the EVE-NG file manager,
override with `--lab-path`:

```bash
python setup_lab.py --host <eve-ng-ip> --lab-path my-folder/lab-00-single-area-ospfv2.unl
```

---

## Common Workflows

**Discover console ports without touching configs:**

```bash
python setup_lab.py --host <eve-ng-ip> --no-push
```

Useful when devices already hold a working config and you just need the
telnet port mapping.

**Re-push configs after wiping a device:**

```bash
python setup_lab.py --host <eve-ng-ip>
```

Re-running is idempotent — the script connects, sends the config set, saves,
and disconnects.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ERROR: 401 Unauthorized` | Wrong EVE-NG credentials | Pass `--username` / `--password` explicitly |
| `No ports discovered` | Wrong `--lab-path`, or nodes not running | Verify the lab path in the EVE-NG UI; re-run after starting nodes manually |
| `netmiko not installed` | Missing dependency | `pip install netmiko requests` |
| `push failed — Pattern not detected` | IOSv still booting | Wait longer after boot, or re-run the script |
