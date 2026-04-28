# Lab 02 — eBGP Multihoming Topology

## 1. Topology Summary

This lab uses a three-AS BGP design with 6 nodes and 7 physical links.

| AS | Devices | Role |
|----|---------|------|
| AS 65001 | R1 | Customer A CE — dual-homed via L1 (primary) and L2 (backup) |
| AS 65100 | R2, R3, R4, R5 | SP Core — OSPF area 0 IGP, iBGP via R4 Route Reflector |
| AS 65002 | R6 | External SP Peer — eBGP to R5 via L7 |

### Link Table

| Link | Source | Source IP | Target | Target IP | Subnet | Purpose |
|------|--------|-----------|--------|-----------|--------|---------|
| L1 | R1 Gi0/0 | 10.1.12.1 | R2 Gi0/0 | 10.1.12.2 | 10.1.12.0/24 | eBGP primary (CE to PE East-1) |
| L2 | R1 Gi0/1 | 10.1.13.1 | R3 Gi0/0 | 10.1.13.3 | 10.1.13.0/24 | eBGP backup (CE to PE East-2) |
| L3 | R2 Gi0/1 | 10.1.24.2 | R4 Gi0/0 | 10.1.24.4 | 10.1.24.0/24 | OSPF/iBGP R2 to R4 |
| L4 | R3 Gi0/1 | 10.1.34.3 | R4 Gi0/1 | 10.1.34.4 | 10.1.34.0/24 | OSPF/iBGP R3 to R4 |
| L5 | R4 Gi0/2 | 10.1.45.4 | R5 Gi2 | 10.1.45.5 | 10.1.45.0/24 | OSPF/iBGP R4 to R5 |
| L6 | R2 Gi0/2 | 10.1.23.2 | R3 Gi0/2 | 10.1.23.3 | 10.1.23.0/24 | OSPF IGP East PE resilience |
| L7 | R5 Gi3 | 10.1.56.5 | R6 Gi0/0 | 10.1.56.6 | 10.1.56.0/24 | eBGP external (AS 65100 to AS 65002) |

---

## 2. EVE-NG Import Instructions

1. Open the EVE-NG web UI and navigate to the target lab folder.
2. Click **File > Import** (or use the hamburger menu and select **Import**).
3. Select the `.unl` lab file exported from EVE-NG. The `.drawio` file is a diagram reference only — EVE-NG does not import `.drawio` directly.
4. After import, open the lab and verify all nodes appear with the correct names and connections.
5. To update the diagram to match a modified EVE-NG topology, export the lab as `.unl`, update the IP addressing in `baseline.yaml`, and regenerate the diagram.

---

## 3. Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|-----------------|-----|-------|
| R1 | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | CSR1000v | 3072 MB | csr1000v-universalk9.17.03.05 |
| R6 | IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

All IOSv nodes use a single QEMU virtual CPU. R5 (CSR1000v) requires 3 GB RAM and at least 1 vCPU for IOS-XE BGP FlowSpec support.

---

## 4. Starting the Lab

1. In the EVE-NG web UI, open the lab.
2. Right-click the canvas and select **Start all nodes**, or start each node individually.
3. Wait approximately 60–90 seconds for IOSv nodes to boot and 3–4 minutes for R5 (CSR1000v).
4. Console into each node via `telnet <eve-ng-ip> <console-port>` (ports are shown in the EVE-NG UI node properties).
5. Run `setup_lab.py` to push the base configuration:

```bash
python labs/bgp/lab-02-ebgp-multihoming/setup_lab.py --host <eve-ng-ip>
```

6. Verify OSPF and iBGP are up before starting lab tasks:

```
R4# show ip ospf neighbor
R4# show ip bgp summary
```

---

## 5. Exporting the Lab

1. In the EVE-NG web UI, open the lab.
2. Click **File > Export** (or the hamburger menu > **Export**).
3. Save the `.unl` file locally. This file contains the full topology, node images, and connections.
4. Commit the `.unl` export alongside the `.drawio` diagram if you want a fully reproducible snapshot.

> Note: EVE-NG stores node startup configs separately from the `.unl`. To export configs, use `File > Export configs` (Pro) or manually copy running-configs from each device.
