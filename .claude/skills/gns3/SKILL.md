---
name: gns3
description: "DEPRECATED — use eve-ng/SKILL.md instead. GNS3/Apple Silicon archive (Dynamips only: c7200, c3725). Read-only reference for legacy GNS3 labs."
deprecated: true
---

> **DEPRECATED:** This skill applies to the GNS3/Apple Silicon environment (Dynamips only).
> For EVE-NG labs on Windows/Intel, use `eve-ng/SKILL.md` instead.
> This file is kept as a read-only archive.

# GNS3 Lab Skill (Apple Silicon — ARCHIVED)

Hardware reference and constraint guide for the GNS3 environment running on Apple M1/M2/M3. All lab generation must comply with these constraints.

-# Instructions

--# 1. Host Architecture & Constraints

This GNS3 environment uses **Dynamips** (Cisco IOS emulation) only.

- **No virtualisation:** Intel VT-x, VMware, and VirtualBox VMs are NOT supported.
- **No NX-OS or IOS-XR:** Strictly limited to classic IOS images.
- **Supported images:** `c7200` and `c3725` only.

--# 2. Platform Selection Guide

| Condition | Use |
|-----------|-----|
| Hub, Core, or ABR role | `c7200` |
| IPsec, GRE crypto features needed | `c7200` |
| More than 3 FastEthernet interfaces needed | `c7200` |
| Branch, Spoke, or Edge role | `c7200` |
| L2 switching ports needed (NM-16ESW) | `c3725` |
| Serial WAN links | either (both support `NM-4T`) |

> **Rule:** Use `c3725` **only** when the lab requires L2 switching (NM-16ESW in slot 1). Use `c7200` for all pure-routing roles. Never mix up named-mode EIGRP or IOS 15+ features on a c3725 — its IOS 12.4 image does not support them.

--# 3. Hardware Templates (Source of Truth)

### c7200

| Slot | Adapter | Interfaces |
|------|---------|------------|
| 0 | `C7200-IO-FE` | fa0/0 |
| 1 | `PA-2FE-TX` | fa1/0, fa1/1 |
| 2 | `PA-4T+` | s2/0–s2/3 |
| 3 | `PA-GE` | gi3/0 |

- **RAM:** 512 MB
- **IOS Image:** `c7200-adventerprisek9-mz.153-3.XB12.image`
- **Idle PC:** `0x60629004`

### c3725

| Slot | Adapter | Interfaces |
|------|---------|------------|
| 0 | `GT96100-FE` | fa0/0, fa0/1 |
| 1 | `NM-16ESW` | fa1/0–fa1/15 (L2 switching) |
| 2 | `NM-4T` | s2/0–s2/3 |

- **RAM:** 256 MB
- **IOS Image:** `c3725-adventerprisek9-mz.124-15.T14.image`
- **Idle PC:** `0x60c09aa0`

--# 4. VPCS (Virtual PC Simulator)

VPCS is a built-in GNS3 node — no IOS image required. Use it as a lightweight end-host for reachability testing, DHCP client simulation, and traceroute verification.

### When to use VPCS

| Condition | Use VPCS |
|-----------|----------|
| Verify routing reachability end-to-end | yes |
| Test DHCP client behaviour | yes |
| Source pings/traceroutes from a host address | yes |
| Simulate a server or application workload | no — use a router loopback instead |
| Any L3 routing function | no — VPCS has no routing stack |

> **Rule:** Add VPCS only when the lab explicitly needs a simulated end-host (e.g., "verify PC1 can reach PC2 across the WAN"). Do not add VPCS by default to every lab.

### VPCS hardware profile

| Property | Value |
|----------|-------|
| Node type | VPCS (GNS3 built-in) |
| Interfaces | `eth0` (single Ethernet) |
| IOS image | none |
| RAM | minimal (host process) |

### VPCS command reference

```
# Assign a static IP
ip <address>/<prefix-length> <gateway>
  Example: ip 192.168.10.2/24 192.168.10.1

# Verify assignment
show ip

# Ping
ping <destination>
ping <destination> -c <count> -t <ttl>

# Traceroute
trace <destination>

# DHCP (obtain address automatically)
dhcp
dhcp -t <timeout-seconds>

# Save config across reboots
save
```

### Referencing VPCS in baseline.yaml

```yaml
devices:
  - name: PC1
    type: vpcs
    interfaces:
      - name: eth0
        ip: 192.168.10.2/24
        gateway: 192.168.10.1

links:
  - "PC1:eth0 ↔ SW1:fa1/1"
```

### VPCS initial-config format

VPCS startup config is a plain text file (one command per line, no `!` separators):

```
ip 192.168.10.2/24 192.168.10.1
save
```

Place it at `initial-configs/PC1.vpc` (`.vpc` extension, not `.cfg`).

---

--# 5. Console Port Convention

Base port: 5000. Assign sequentially — routers first, then VPCS nodes.

| Device | Console Port | Telnet Command |
|--------|-------------|----------------|
| R1 | 5001 | `telnet localhost 5001` |
| R2 | 5002 | `telnet localhost 5002` |
| R3 | 5003 | `telnet localhost 5003` |
| RN | 500N | `telnet localhost 500N` |
| PC1 | 5020 | `telnet localhost 5020` |
| PC2 | 5021 | `telnet localhost 5021` |
| PCN | 502N | `telnet localhost 502N` |

> VPCS ports start at 5020 to leave room for up to 19 routers (5001–5019) without collision.

--# 6. Design Rules for Lab Generation

1. **No high-speed interfaces:** Do not use `TenGig` or `HundredGig`. Use `FastEthernet` or `GigabitEthernet` (gi3/0 on c7200).
2. **No incompatible technology:** Exclude features requiring IOS-XR, NX-OS, or containerisation.
3. **Physical link table:** Always define links explicitly in `baseline.yaml` using the format:
   `Source:Interface ↔ Target:Interface`
4. **Supported node types (non-IOS):** Unmanaged Switch (generic GNS3 built-in); VPCS (see Section 4 — use only when a simulated end-host is needed, not by default).
5. **Device count:** Minimum 3 routers, maximum 15 routers per chapter topology (core + optional combined). VPCS nodes do not count toward the router limit.
6. **Platform-command alignment:** Before generating configs, confirm the IOS image version supports the required syntax. Check `.agent/skills/reference-data/ios-compatibility.yaml`. Named-mode EIGRP and any IOS 15+ feature must use c7200. If a command is `fail` on the target platform, switch to c7200 or find a supported alternative.
7. **VPCS config files use `.vpc` extension** — never `.cfg`. Place them in `initial-configs/` alongside router configs.

-# Common Issues

--# Feature not available on c3725
- **Cause:** c3725 IOS image does not support advanced crypto (IPsec, DMVPN) or advanced BGP features.
- **Solution:** Upgrade the affected router to c7200 in `baseline.yaml`. Update console ports and interface names accordingly (`fa0/0` → `fa0/0` is the same, but `gi3/0` is only on c7200).

--# Interface name mismatch in configs
- **Cause:** Config references `Gi0/0` but the platform only has `Fa0/0`.
- **Solution:** Check the slot table above. c3725 slot 0 = `Fa0/0`/`Fa0/1`. c7200 slot 3 = `Gi3/0`. Never use interface names not listed in the slot tables.

--# Too many interfaces needed
- **Cause:** Lab requires more than 2 FastEthernet on a c3725 (only fa0/0 and fa0/1 in slot 0).
- **Solution:** Switch to c7200 (slot 1 provides fa1/0 and fa1/1, slot 3 provides gi3/0), or use an unmanaged switch to extend a single interface into multiple segments.

-# Examples

When generating `baseline.yaml` for an OSPF multi-area lab with 4 routers:
- R1 (ABR, connects Area 0 to Area 1): `c7200` — hub/ABR role, needs 3 interfaces
- R2 (Area 0 internal): `c7200` — routing-only role
- R3 (ABR, connects Area 0 to Area 2): `c7200` — hub/ABR role, needs 3 interfaces
- R7 (Area 2 stub, added in Lab 05): `c7200` — routing-only role

When generating `baseline.yaml` for a switching lab (e.g., VLANs, STP):
- SW1 (Layer 2 switch, 12 access ports): `c3725` — NM-16ESW in slot 1 provides fa1/0–fa1/15
- SW2 (Layer 2 switch): `c3725` — NM-16ESW required; no L3 routing features needed
- R1 (default gateway / router-on-a-stick): `c7200` — routing role

When a lab requires end-to-end reachability verification (e.g., "verify PC can reach remote subnet"):
- PC1 (`vpcs`, type: vpcs) — connected to R1 fa1/0 on 192.168.10.0/24, gateway 192.168.10.1
- PC2 (`vpcs`, type: vpcs) — connected to R3 fa1/0 on 192.168.30.0/24, gateway 192.168.30.1
- Console ports: PC1 → 5020, PC2 → 5021
- `initial-configs/PC1.vpc`: `ip 192.168.10.2/24 192.168.10.1`
- Workbook verification step: `PC1> ping 192.168.30.2`
