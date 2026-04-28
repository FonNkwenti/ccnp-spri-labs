# BGP Lab 03 — Topology Reference

## 1. Lab Topology Summary

This topology models a three-AS service provider environment for the BGP interdomain security lab.

- **6 devices** across three autonomous systems
- **7 physical links** (all routed /24 subnets)
- **Multi-AS**: AS 65001 (Customer A), AS 65100 (SP-Core), AS 65002 (External SP Peer)

### Autonomous System Layout

| AS | Devices | Role |
|----|---------|------|
| AS 65001 | R1 | Customer A dual-homed CE |
| AS 65100 | R2, R3, R4, R5 | SP-Core: PEs + P/Route Reflector |
| AS 65002 | R6 | External SP peer |

### Key Security Controls

| Session | GTSM | MD5 | Maximum-Prefix |
|---------|------|-----|----------------|
| R1 ↔ R2 (Gi0/0 ↔ Gi0/0) | hops 1 | — | 100 restart 5 on R2 |
| R1 ↔ R3 (Gi0/1 ↔ Gi0/0) | hops 1 | — | — |
| R5 ↔ R6 (Gi3 ↔ Gi0/0) | hops 1 | CISCO_SP | 100 75 warning-only on R5 |

---

## 2. EVE-NG Import Instructions

1. Open the EVE-NG web UI in your browser (`http://<eve-ng-ip>`).
2. Log in and navigate to the lab folder where you want to import.
3. Click **Import** (or use the hamburger menu > Import topology).
4. Select `topology.drawio` — EVE-NG accepts `.drawio` files directly as visual reference overlays, or use it as a layout guide when manually building the lab.
5. To build the lab programmatically, run the setup script from the lab root:

```bash
python3 labs/bgp/lab-03-interdomain-security/setup_lab.py --host <eve-ng-ip>
```

6. The setup script creates all nodes and links and uploads initial configurations.

---

## 3. Node Configuration Reference

| Device | Role | EVE-NG Template | RAM | Image |
|--------|------|-----------------|-----|-------|
| R1 | Customer A CE (AS 65001) | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE-East-1 (AS 65100) | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE-East-2 (AS 65100) | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P / Route Reflector (AS 65100) | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE-West IOS-XE (AS 65100) | CSR1000v | 3072 MB | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address | Purpose |
|--------|-----------|---------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id |
| R1 | Loopback1 | 172.16.1.0/24 | Customer A advertised prefix |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP update-source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP update-source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, RR update-source |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP update-source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id |
| R6 | Loopback1 | 172.16.6.0/24 | External SP advertised prefix |

### Link Table

| Link ID | Source | Target | Subnet | Purpose |
|---------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | eBGP primary (GTSM, max-pfx) |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.1.13.0/24 | eBGP backup (GTSM) |
| L3 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/24 | OSPF + iBGP |
| L4 | R3 Gi0/1 | R4 Gi0/1 | 10.1.34.0/24 | OSPF + iBGP |
| L5 | R4 Gi0/2 | R5 Gi2 | 10.1.45.0/24 | OSPF + iBGP |
| L6 | R2 Gi0/2 | R3 Gi0/2 | 10.1.23.0/24 | OSPF IGP only (East PE resilience) |
| L7 | R5 Gi3 | R6 Gi0/0 | 10.1.56.0/24 | eBGP external (GTSM + MD5) |

---

## 4. Starting the Lab

1. In the EVE-NG UI, open the lab and power on all nodes.
2. Wait approximately 60–90 seconds for IOS/IOS-XE boot (CSR1000v R5 takes longer).
3. Connect to each device via telnet from the EVE-NG host:

```bash
telnet <eve-ng-ip> <console-port>
```

4. Verify base configuration is loaded (hostnames, interfaces, OSPF, BGP without security):

```
R1# show ip bgp summary
R2# show ip ospf neighbor
```

5. Begin the lab tasks from `workbook.md` Section 5.

---

## 5. Exporting the Lab

To save a snapshot of any device configuration:

```bash
# From EVE-NG UI: right-click the lab > Export configs
# Or connect and copy running config:
R1# show running-config
```

To export the topology diagram as PNG for documentation:

1. Open `topology.drawio` in Draw.io desktop or `app.diagrams.net`.
2. File > Export As > PNG (set scale to 2x for print quality).
3. Save as `topology.png` in this `topology/` directory.
