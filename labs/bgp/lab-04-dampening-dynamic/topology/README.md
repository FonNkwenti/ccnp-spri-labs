# Lab 04 Topology — Route Dampening and Dynamic Neighbors

## 1. Topology Summary

This lab extends the lab-03 topology with one new physical link (L8) and two new BGP
features: route dampening on R5 and dynamic BGP neighbor provisioning on R2.

**Devices:** 6 routers across 3 autonomous systems
**Links:** 8 total (7 from baseline + 1 new in lab-04)

```
  AS 65001                      AS 65100 (SP Core / OSPF Area 0)                   AS 65002
┌──────────┐    L1 eBGP    ┌──────────┐  L3 OSPF/iBGP  ┌──────────┐               ┌──────────┐
│    R1    ├───────────────┤    R2    ├────────────────►│    R4    │               │    R6    │
│ Cust A   │ 10.1.12.0/24  │ PE East-1│ 10.1.24.0/24   │  P / RR  │               │ Ext Peer │
│ AS 65001 │    L2 eBGP    │ Dynamic  │  L6 OSPF only  └────┬─────┘               │ AS 65002 │
│Lo0:      ├───────────────┤ Neighbors├──────────────────►  │                     │Lo0:      │
│10.0.0.1  │ 10.1.13.0/24  │Lo0:      │ 10.1.23.0/24        │ L5 OSPF/iBGP       │10.0.0.6  │
└────┬─────┘               │10.0.0.2  │                     │ 10.1.45.0/24        │Lo1:      │
     │                     └──────────┘  ┌──────────┐        ▼                    │172.16.6.1│
     │       L8 (NEW lab-04)             │    R3    │  ┌──────────┐  L7 eBGP      └──────────┘
     └───────────────────────────────────┤ PE East-2│  │    R5    ├───────────────►
      10.99.0.0/30 Dynamic Neighbors     │ AS 65100 │  │ PE West  │ 10.1.56.0/24
      R1 Gi0/2 ↔ R2 Gi0/3               │Lo0:      │  │CSR1000v  │
                                         │10.0.0.3  │  │Dampening │
                                         └──────────┘  │Lo0:      │
                                                        │10.0.0.5  │
                                                        └──────────┘
```

### Link Table

| Link | Source | Interface | IP | Destination | Interface | IP | Subnet | Purpose |
|------|--------|-----------|-----|-------------|-----------|-----|--------|---------|
| L1 | R1 | Gi0/0 | 10.1.12.1/24 | R2 | Gi0/0 | 10.1.12.2/24 | 10.1.12.0/24 | eBGP primary |
| L2 | R1 | Gi0/1 | 10.1.13.1/24 | R3 | Gi0/0 | 10.1.13.3/24 | 10.1.13.0/24 | eBGP backup |
| L3 | R2 | Gi0/1 | 10.1.24.2/24 | R4 | Gi0/0 | 10.1.24.4/24 | 10.1.24.0/24 | OSPF/iBGP |
| L4 | R3 | Gi0/1 | 10.1.34.3/24 | R4 | Gi0/1 | 10.1.34.4/24 | 10.1.34.0/24 | OSPF/iBGP |
| L5 | R4 | Gi0/2 | 10.1.45.4/24 | R5 | Gi2 | 10.1.45.5/24 | 10.1.45.0/24 | OSPF/iBGP |
| L6 | R2 | Gi0/2 | 10.1.23.2/24 | R3 | Gi0/2 | 10.1.23.3/24 | 10.1.23.0/24 | OSPF only |
| L7 | R5 | Gi3 | 10.1.56.5/24 | R6 | Gi0/0 | 10.1.56.6/24 | 10.1.56.0/24 | eBGP |
| **L8** | **R1** | **Gi0/2** | **10.99.0.1/30** | **R2** | **Gi0/3** | **10.99.0.2/30** | **10.99.0.0/30** | **Dynamic NBR (NEW lab-04)** |

---

## 2. EVE-NG Import Instructions

1. Open the EVE-NG web UI at `http://<eve-ng-ip>`.
2. Navigate to the lab folder where you want to import this topology.
3. Click **Add/Import** and select the `.unl` file (if you have exported one) or build
   manually using the node configuration reference below.
4. Alternatively, use the `setup_lab.py` script to provision all nodes and links
   automatically via the EVE-NG API:

   ```bash
   python3 labs/bgp/lab-04-dampening-dynamic/setup_lab.py --host <eve-ng-ip>
   ```

5. Once nodes are started, open the topology view in the EVE-NG UI and verify all
   connections match the diagram in `topology.drawio`.

---

## 3. Node Configuration Reference

| Device | Role | EVE-NG Template | RAM (MB) | Image |
|--------|------|-----------------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) — Dynamic Neighbors | IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) | IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P / Route Reflector (AS 65100) | IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) — BGP Dampening | CSR1000v | 3072 | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |

**Notes:**
- IOSv nodes require the `vios-adventerprisek9-m` image (IOS 15.x). The `.SPA.156-2.T`
  variant is recommended for CCNP SP labs.
- R5 (CSR1000v) requires at least 3 GB RAM and 2 vCPUs for stable BGP operation.
  Increase to 4 GB if you observe high CPU during FlowSpec exercises.
- All routers use 4 GigabitEthernet interfaces minimum (Gi0/0 through Gi0/3 for IOSv;
  Gi0 through Gi4 for CSR1000v).

---

## 4. Starting the Lab

1. In the EVE-NG UI, right-click the lab canvas and select **Start all nodes**.
2. Wait approximately 60–90 seconds for all routers to boot.
3. Verify console access by clicking each node icon in the EVE-NG UI (opens a Telnet
   session to the console port).
4. Load the initial configuration using the setup script:

   ```bash
   python3 labs/bgp/lab-04-dampening-dynamic/setup_lab.py --host <eve-ng-ip>
   ```

5. After the script completes, verify baseline BGP sessions are up on all routers:

   ```
   R2# show ip bgp summary
   R5# show ip bgp summary
   ```

6. Confirm that L8 is IP-addressed but NOT yet in BGP (pre-lab state):

   ```
   R1# show interface GigabitEthernet0/2
   R2# show interface GigabitEthernet0/3
   R2# show ip bgp listen range   ! should be empty
   ```

---

## 5. Exporting the Lab

### Export from EVE-NG

1. In the EVE-NG UI, open the lab.
2. Click **File > Export** or use the EVE-NG CLI:

   ```bash
   # On the EVE-NG server
   cd /opt/unetlab/labs/<your-folder>/
   cp <lab-name>.unl /path/to/export/
   ```

### Export Router Configurations

To save the current running configurations of all routers:

```bash
# From the lab directory
python3 setup_lab.py --host <eve-ng-ip> --export-configs
```

Configurations are saved to `initial-configs/` (pre-lab baseline) or `solutions/`
(post-lab completed state) depending on the export flag used.

### Diagram Export

To export the topology diagram as a PNG for documentation:

1. Open `topology/topology.drawio` in Draw.io desktop or `app.diagrams.net`.
2. Select **File > Export As > PNG**.
3. Set resolution to 150 DPI minimum for lab documentation.
4. Save as `topology/topology.png`.
