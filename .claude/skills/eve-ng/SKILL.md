---
name: eve-ng
description: EVE-NG hardware constraints and platform reference for Intel/Windows (QEMU, IOL, Dynamips). Use when generating lab configs, creating baseline.yaml topology definitions, selecting node platforms, assigning interfaces, or any time EVE-NG platform constraints (IOSv, IOSvL2, CSR1000v, IOL, XRv 9000, NX-OSv, ASAv) must be verified for compatibility. Replaces the deprecated gns3 skill.
---

# EVE-NG Lab Skill (Intel / Windows)

Hardware reference and constraint guide for the EVE-NG environment running on Dell Latitude 5540 (i7-1370P, 64 GB RAM) with Windows host. All lab generation must comply with these constraints.

-# Instructions

--# 1. Host Architecture & Constraints

This EVE-NG environment runs on **KVM/QEMU** (full virtualisation). Intel VT-x is active.

- **Platform:** EVE-NG Community/Pro on Ubuntu Server (bare-metal or VMware/Hyper-V guest)
- **Access:** Web UI at `http://<eve-ng-ip>` (default creds: `admin / eve`)
- **Emulation engines available:**
  - **QEMU** — primary engine (IOSv, IOSvL2, CSR1000v, XRv 9000, NX-OSv, ASAv, Catalyst 9kv, Cisco 8000v)
  - **IOL** — lightweight Linux-native IOS (L2 and L3 images)
  - **Dynamips** — legacy only (c7200, c3725 available but deprecated for new labs)
- **No Apple Silicon restrictions:** All Cisco image types are supported.

--# 2. Platform Selection Guide

| Role / Requirement | Primary Platform | Alternative | Notes |
|---|---|---|---|
| General routing (CCNA/CCNP routing) | `iosv` (IOSv) | `iol_l3` (IOL L3) | IOSv is heavier but closest to real IOS 15.x |
| L2 switching (VLANs, STP, EtherChannel, LACP) | `iosvl2` (IOSvL2) | `iol_l2` (IOL L2) | Full RSTP, LACP, BPDU Guard, Rapid PVST+ |
| Advanced IOS-XE (NETCONF, RESTCONF, SD-WAN) | `csr1000v` (CSR1000v) | `c8000v` (Cisco 8000v) | Heavy RAM (~3 GB); use only when IOS-XE needed |
| Service Provider (IS-IS, MPLS, Segment Routing) | `xrv9k` (IOS-XRv 9000) | `xrv` (XRv classic) | XRv 9000 for production parity; IOS-XR CLI |
| Data Centre (VxLAN, NX-OS, EVPN) | `nxosv9k` (NX-OSv 9000) | — | NX-OS CLI only |
| Security (ASA firewall, VPN) | `asav` (ASAv) | — | ASA-specific labs |
| Campus switching / IOS-XE features | `cat9kv` (Catalyst 9000v) | `iosvl2` | Very heavyweight; prefer IOSvL2 for basic switching |
| Lightweight routing (resource-constrained) | `iol_l3` (IOL L3) | `iosv` | Fastest boot, lowest RAM (~256 MB) |
| Lightweight switching | `iol_l2` (IOL L2) | `iosvl2` | Fastest boot for L2 labs |

> **Default rule:** Use `iosv` for routing labs and `iosvl2` for switching labs unless the certification blueprint explicitly requires a different platform (e.g., NX-OS for DC tracks, IOS-XR for SP tracks).

--# 3. Hardware Templates (Source of Truth)

> **Verified 2026-04-10:** Interface names below confirmed against live nodes on this EVE-NG installation. IOSv and IOSvL2 templates are accurate.

### IOSv (vios-adventerprisek9-m.SPA.159-3.M6)

| Interface | Type | Notes |
|-----------|------|-------|
| GigabitEthernet0/0 | GigE | First data interface |
| GigabitEthernet0/1 | GigE | Second data interface |
| GigabitEthernet0/2 | GigE | Third data interface |
| GigabitEthernet0/3 | GigE | Fourth data interface |

- **RAM:** 512 MB recommended
- **IOS Version:** 15.9(3)M6
- **EVE-NG node type:** `vios`
- **Supported features:** Named-mode EIGRP, OSPFv3, BGP, MPLS, IPv6, GRE, IPsec

### IOSvL2 (viosl2-adventerprisek9-m.ssa.high_iron_20200929)

| Interface | Type | Notes |
|-----------|------|-------|
| GigabitEthernet0/0 | GigE | Routed or switchport |
| GigabitEthernet0/1 | GigE | Routed or switchport |
| GigabitEthernet0/2 | GigE | Routed or switchport |
| GigabitEthernet0/3 | GigE | Routed or switchport |
| GigabitEthernet1/0 | GigE | Switchport only |
| GigabitEthernet1/1 | GigE | Switchport only |
| GigabitEthernet1/2 | GigE | Switchport only |
| GigabitEthernet1/3 | GigE | Switchport only |

- **RAM:** 768 MB recommended
- **IOS Version:** 15.x (high_iron_20200929)
- **EVE-NG node type:** `viosl2`
- **Supported features:** VLANs, 802.1Q, RSTP (Rapid PVST+), LACP, PAgP, BPDU Guard, PortFast, VTP, EtherChannel, SVI routing
- **Note:** All 8 interfaces come `up/up` by default at boot — no `no shutdown` needed. IOSv interfaces start `administratively down`.

### CSR1000v (csr1000vng-universalk9.17.03.05)

| Interface | Type | Notes |
|-----------|------|-------|
| GigabitEthernet1 | GigE | First data interface (NOT Gi0/0) |
| GigabitEthernet2 | GigE | Second data interface |
| GigabitEthernet3 | GigE | Third data interface |

> **Note:** CSR1000v interface naming differs from IOSv — uses `GigabitEthernet1/2/3`, not `GigabitEthernet0/0-0/3`.

- **RAM:** 3072 MB minimum (4096 MB recommended)
- **IOS-XE Version:** 17.03.05
- **EVE-NG node type:** `csr1000vng`

### IOL L3 (i86bi_LinuxL3-AdvEnterpriseK9-M2_157_3_May_2018.bin)

| Interface | Type | Notes |
|-----------|------|-------|
| Ethernet0/0 | Ethernet | First data interface |
| Ethernet0/1 | Ethernet | Second data interface |
| Ethernet0/2 | Ethernet | Third data interface |
| Ethernet0/3 | Ethernet | Fourth data interface |
| Ethernet1/0 | Ethernet | Fifth data interface |
| Ethernet1/1 | Ethernet | Sixth data interface |
| Ethernet1/2 | Ethernet | Seventh data interface |
| Ethernet1/3 | Ethernet | Eighth data interface |

- **RAM:** 256 MB
- **IOS Version:** 15.7(3)M
- **EVE-NG node type:** `iol` (requires `iourc` license file)

### IOL L2 (i86bi_linux_l2-adventerprisek9-ms.SSA.high_iron_20190423.bin)

Same interface naming as IOL L3 (`Ethernet0/0` through `Ethernet1/3`), but ports support switchport commands.

- **RAM:** 256 MB
- **EVE-NG node type:** `iol` (requires `iourc` license file)

### IOS-XRv 9000 (xrv9k-fullk9-x.vrr.vga-7.1.1.qcow2)

| Interface | Type | Notes |
|-----------|------|-------|
| GigabitEthernet0/0/0/0 | GigE | IOS-XR naming convention |
| GigabitEthernet0/0/0/1 | GigE | |
| GigabitEthernet0/0/0/2 | GigE | |
| GigabitEthernet0/0/0/3 | GigE | |

- **RAM:** 4096–16384 MB (boot requires 4 GB minimum)
- **IOS-XR Version:** 7.1.1
- **EVE-NG node type:** `xrv9k`
- **Warning:** Long boot time (~10 min). Use only when IOS-XR features are required.

### NX-OSv 9000 (nxosv9k-9500-9.3.5)

| Interface | Type | Notes |
|-----------|------|-------|
| Ethernet1/1 | Ethernet | NX-OS naming — 1-based |
| Ethernet1/2 | Ethernet | |
| Ethernet1/3 | Ethernet | |
| Ethernet1/4 | Ethernet | |
| mgmt0 | Management | Out-of-band management |

- **RAM:** 4096 MB minimum
- **NX-OS Version:** 9.3.5
- **EVE-NG node type:** `nxosv9k`

### ASAv (asav-961-001)

| Interface | Type | Notes |
|-----------|------|-------|
| GigabitEthernet0/0 | GigE | Data (outside/inside) |
| GigabitEthernet0/1 | GigE | |
| GigabitEthernet0/2 | GigE | |
| GigabitEthernet0/3 | GigE | |
| Management0/0 | Management | OOB management |

- **RAM:** 2048 MB
- **ASA Version:** 9.6.1
- **EVE-NG node type:** `asav`

--# 4. VPC Nodes (End-Host Simulation)

EVE-NG includes a built-in **VPC** node (Virtual PC) — equivalent to GNS3's VPCS.

### When to use VPC

| Condition | Use VPC |
|-----------|---------|
| Verify routing reachability end-to-end | yes |
| Test DHCP client behaviour | yes |
| Source pings/traceroutes from a host address | yes |
| Simulate a server or application workload | no — use a router loopback instead |
| Any L3 routing function | no — VPC has no routing stack |

### VPC hardware profile

| Property | Value |
|----------|-------|
| Node type | VPC (EVE-NG built-in) |
| Interface | `e0` (single Ethernet) |
| IOS image | none |
| RAM | minimal |

### VPC command reference

```
# Assign a static IP
ip <address> <netmask> <gateway>
  Example: ip 192.168.10.2 255.255.255.0 192.168.10.1

# Verify assignment
show

# Ping
ping <destination>

# DHCP
dhcp

# Save config
save
```

> **Note:** EVE-NG VPC syntax differs slightly from GNS3 VPCS. Use `ip <addr> <mask> <gw>` (dotted-decimal mask, not prefix length).

### Referencing VPC in baseline.yaml

```yaml
devices:
  - name: PC1
    type: vpc
    interfaces:
      - name: e0
        ip: 192.168.10.2/24
        gateway: 192.168.10.1

links:
  - "PC1:e0 ↔ R1:GigabitEthernet0/1"
```

VPC config files use `.vpc` extension, placed in `initial-configs/PC1.vpc`.

---

--# 5. Console Access Convention

EVE-NG assigns console telnet ports **dynamically** at lab creation — there is no static `500N` convention like GNS3.

### Method 1: EVE-NG REST API (recommended for automation)

Discover ports at runtime before connecting:

```python
import requests

EVE_NG_HOST = "192.168.1.x"   # Your EVE-NG server IP
LAB_PATH    = "your_lab.unl"   # Lab file path on server

def get_node_ports(host, lab_path):
    """Return dict of node_name -> telnet_port."""
    session = requests.Session()
    session.post(f"http://{host}/api/auth/login",
                 json={"username": "admin", "password": "eve"})
    nodes = session.get(f"http://{host}/api/labs/{lab_path}/nodes").json()
    return {
        n["name"]: int(n["url"].split(":")[-1])
        for n in nodes["data"].values()
        if n.get("url")
    }
```

### Method 2: HTML5 Console (browser-based)

Open EVE-NG web UI → click any node → "Console" button. No client software needed. Best for manual lab work.

### Method 3: SecureCRT / PuTTY (telnet client)

1. In EVE-NG web UI, right-click node → "Console" → copy the telnet URI.
2. Connect via `telnet <eve-ng-ip> <port>`.
3. Ports are visible in the EVE-NG web UI per-lab under each node's details.

### Method 4: SSH to Node Management Interface

Configure a management network (`192.168.100.0/24`) on all nodes. Use `device_type="cisco_ios"` with SSH instead of telnet.

### Console Access Table format (workbooks)

Because ports are dynamic, workbooks should use this format:

```
| Device | Console Port | Connection Command |
|--------|-------------|-------------------|
| R1     | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2     | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
```

When automating with `setup_lab.py`, pass `--host <eve-ng-ip>` and the script will discover ports via the REST API.

---

--# 6. Design Rules for Lab Generation

1. **GigabitEthernet is standard:** All IOSv/IOSvL2 interfaces are GigE (`GigabitEthernet0/0`). Do NOT use `FastEthernet` for IOSv/IOSvL2 labs.
2. **Platform-command alignment:** Before generating configs, verify the target platform supports the required syntax. Check `reference-data/ios-compatibility.yaml`. IOSv (IOS 15.9) and IOSvL2 support all IOS 15.x features including named-mode EIGRP, RSTP, LACP, BPDU Guard, OSPFv3.
3. **IOS-XR and NX-OS labs:** Use `xrv9k` and `nxosv9k` only when the lab explicitly requires those OSes. Config syntax is different from IOS — do not mix.
4. **Physical link table:** Always define links explicitly in `baseline.yaml` using the format:
   `Source:Interface ↔ Target:Interface`
5. **Device count:** Minimum 3, maximum 15 routers per chapter topology. VPC nodes do not count toward the router limit.
6. **Resource planning (64 GB host):**
   | Platform | RAM/node | Max nodes (safe) |
   |----------|----------|-----------------|
   | IOSv | 512 MB | 20 |
   | IOSvL2 | 768 MB | 15 |
   | IOL L3/L2 | 256 MB | 40 |
   | CSR1000v | 3072 MB | 8 |
   | XRv 9000 | 4096 MB | 6 |
   | NX-OSv 9000 | 4096 MB | 6 |
7. **Image permissions:** After uploading any image to EVE-NG, always run:
   ```bash
   /opt/unetlab/wrappers/unl_wrapper -a fixpermissions
   ```
8. **VPC config files use `.vpc` extension** — never `.cfg`. Place in `initial-configs/`.
9. **Ship the EVE-NG `.unl` file.** Every lab MUST include a `topology/` directory
   containing the exported `.unl` file alongside `topology.drawio` and a
   `README.md` explaining the import process. See Section 7 for the standard.

--# 7. Shipping EVE-NG Lab Files (`.unl`)

**Every lab MUST ship its EVE-NG `.unl` export.** The `.drawio` diagram is
the *design reference*; the `.unl` is the *exact buildable artifact*. Without
the `.unl`, students must rebuild the topology by hand from the diagram —
error-prone, time-consuming, and produces subtly different link IDs that
break the REST-API port-discovery contract.

### Required structure per lab

```
labs/<topic>/lab-NN-<slug>/
  topology/
    topology.drawio                   # conceptual diagram (design)
    lab-NN-<slug>.unl                 # EVE-NG native lab (buildable)
    README.md                         # import instructions + manual fallback
```

Filename convention: `.unl` filename matches the lab folder name exactly
(e.g. `lab-00-vlans-and-trunking.unl`). This becomes the `lab_path` arg for
REST-API port discovery:

```python
discover_ports(host, "switching/lab-00-vlans-and-trunking.unl")
```

### topology/README.md must cover

1. **What's in the folder** (table: `.drawio` vs `.unl` vs `README.md`)
2. **Import steps** — navigate EVE-NG web UI, Add New Lab → Import, upload
   `.unl`, Start all nodes
3. **Lab path expectation** — where in EVE-NG's folder tree the lab should
   live (the path `setup_lab.py` defaults to), and what `--lab-path` to pass
   if the student imports it elsewhere
4. **Manual fallback** — node list with platform types and full link table
   (mirroring `baseline.yaml`) so the student can rebuild if the `.unl` is
   missing, corrupted, or incompatible with their EVE-NG version

### Export workflow (for lab authors)

1. Build the topology in EVE-NG until all nodes start cleanly
2. EVE-NG web UI: open the lab → **More actions → Export**
3. Save the downloaded `.unl` into `labs/<topic>/<lab>/topology/`
4. Commit `.unl` + `.drawio` + `README.md` together — they must stay in sync
5. Update `meta.yaml` files block to reference all three:
   ```yaml
   files:
     topology:
       diagram: topology/topology.drawio
       eve_ng_lab: topology/<lab-folder-name>.unl
       readme: topology/README.md
   ```

### Never

- Do not ship only the `.drawio` ("students can build it themselves") —
  this is explicitly what this section exists to prevent
- Do not generate a `.unl` programmatically — the format is EVE-NG internal
  XML with node UUIDs that must be allocated by the running EVE-NG instance.
  The only way to produce a working `.unl` is export from EVE-NG itself
- Do not commit the `.unl` without testing that it re-imports and starts

--# 8. Installed Image Inventory

> **Last verified:** 2026-04-10. This table reflects images confirmed on disk at
> `C:\Users\Nkwenti\Documents\EVE-NG\eve images\Cisco`. Add a row when you upload a new image.

### Installed — Confirmed on Disk

| Platform | Image Filename | Version | EVE-NG Node Type | Status |
|----------|---------------|---------|-----------------|--------|
| IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 15.9(3)M6 | `vios` | Installed |
| IOSvL2 | viosl2-adventerprisek9-m.ssa.high_iron_20200929 | 15.x (2020) | `viosl2` | Installed |
| CSR1000v | csr1000vng-universalk9.17.03.05-serial | 17.03.05 | `csr1000vng` | Installed |
| IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-7.1.1.qcow2 | 7.1.1 | `xrv9k` | Installed |
| IOS-XRv classic | xrv-k9-demo-6.3.1 | 6.3.1 | `xrv` | Installed (demo/limited) |
| NX-OSv 9000 | nxosv9k-9500-9.3.5 | 9.3.5 | `nxosv9k` | Installed |
| ASAv | asav-961-001 | 9.6.1 | `asav` | Installed |
| IOL L3 | i86bi_LinuxL3-AdvEnterpriseK9-M2_157_3_May_2018.bin | 15.7(3)M | `iol` | Installed |
| IOL L2 | i86bi_linux_l2-adventerprisek9-ms.SSA.high_iron_20190423.bin | 15.x (2019) | `iol` | Installed |
| Catalyst 9000v | cat9kv-17.10.01-prd7 | 17.10.01 | `cat9kv` | Installed |
| Cisco 8000v | c8000v-17.06.03 | 17.06.03 | `c8000v` | Installed |
| Linux (Ubuntu Server) | linux-ubuntu-server-20.04 | 20.04 LTS | `linux` | Installed |
| Linux (Alpine) | linux-alpine-3.18.4 | 3.18.4 | `linux` | Installed ⚠️ |

### Not Installed — Commonly Needed

| Image / Tool | Purpose | Notes |
|---|---|---|
| Linux VM (Ubuntu 22.04) | Newer LTS for automation labs | Optional upgrade from 20.04 — 20.04 is sufficient for all current exam objectives |
| SD-WAN (vManage, vBond, vSmart, vEdge) | SD-WAN topology simulation | Heavy (4+ VMs per pod). v20.x+ required for current Cisco SD-WAN exams; v19.2 is outdated |
| WLC (Catalyst Wireless LAN Controller) | Wireless controller labs | EVE-NG does not support RF simulation — wireless labs require physical APs or dedicated wireless lab platforms |
| Catalyst Center (DNA Center) | Campus automation, SD-Access | Requires 56+ GB RAM per instance — impractical in EVE-NG; use dCloud or physical for this feature |
| ISE (Identity Services Engine) | 802.1X, TACACS+, RADIUS, TrustSec | Very heavy (~12 GB RAM). Viable in EVE-NG but not yet installed |

### Image Gap Notes

- **Linux VM** (Ubuntu 20.04) is installed — automation labs (Ansible, Python, NETCONF, YANG, telemetry) are unblocked. **Alpine 3.18.4 is also available** as a resource-constrained alternative: use ONLY in large labs (10+ devices) where RAM is tight and only a minimal Linux server is needed for basic scripts or utilities. Default to Ubuntu for any lab with fewer than 10 devices or when standard tools are required.
- **SD-WAN** requires a dedicated image set; not substitutable with CSR1000v in an SD-WAN topology.
- **Wireless and DNA Center** gaps cannot be closed in EVE-NG — plan to use Cisco dCloud or physical gear for those objectives.
- Exam-specific image requirements (which platforms each exam needs, versions, and quantities) belong in the individual exam repo, not here.

-# Common Issues

--# QEMU node fails to start

- **Cause:** KVM not enabled, or image permissions not fixed.
- **Solution:**
  1. Verify KVM: `kvm-ok` on the EVE-NG host.
  2. Fix permissions: `/opt/unetlab/wrappers/unl_wrapper -a fixpermissions`
  3. Check EVE-NG logs: `/opt/unetlab/data/Logs/`

--# Interface name mismatch in configs

- **Cause:** Config references `FastEthernet0/0` but IOSv only has `GigabitEthernet0/0`.
- **Solution:** Check Section 3 hardware templates. IOSv/IOSvL2 = `Gi0/0`. CSR1000v = `Gi1`. IOL = `Et0/0`. XRv 9000 = `Gi0/0/0/0`.

--# Console connection refused

- **Cause:** Node is not yet started, or EVE-NG assigned a different port.
- **Solution:** Start the node in EVE-NG web UI. Rediscover ports via REST API or check the web UI node details.

--# IOL node fails to start (license error)

- **Cause:** `iourc` license file missing or in wrong location on EVE-NG server.
- **Solution:** Ensure `iourc` is placed at `/opt/unetlab/addons/iol/bin/iourc`. Regenerate with `CiscoIOUKeygen.py` if needed.

--# Too many interfaces needed

- **Cause:** IOSv has only 4 interfaces (`Gi0/0`–`Gi0/3`). IOSvL2 has 8. IOL has 8 per card.
- **Solution:** Use IOL L3 (up to 8 interfaces across 2 cards) or add an EVE-NG unmanaged switch node to extend a single interface into multiple segments.

-# Examples

When generating `baseline.yaml` for an OSPF multi-area lab with 4 routers:
- R1 (ABR, connects Area 0 to Area 1): `iosv` — needs 3 interfaces (`Gi0/0`, `Gi0/1`, `Gi0/2`)
- R2 (Area 0 internal): `iosv` — 2 interfaces
- R3 (ABR, connects Area 0 to Area 2): `iosv` — 3 interfaces
- R7 (Area 2 stub, added Lab 05): `iosv`

When generating `baseline.yaml` for a switching lab (VLANs, STP, EtherChannel):
- SW1 (L2 switch, 6 access + 2 trunk ports): `iosvl2` — use `Gi1/0`–`Gi1/3` for switchports
- SW2 (L2 switch): `iosvl2`
- R1 (default gateway / router-on-a-stick): `iosv`

When a lab requires end-to-end reachability verification:
- PC1 (`vpc` type) — connected to R1 `GigabitEthernet0/1` on `192.168.10.0/24`
- PC2 (`vpc` type) — connected to R3 `GigabitEthernet0/1` on `192.168.30.0/24`
- `initial-configs/PC1.vpc`: `ip 192.168.10.2 255.255.255.0 192.168.10.1`
- Workbook verification step: `PC1> ping 192.168.30.2`
