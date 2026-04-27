# Topology — BGP Lab 00: eBGP and iBGP Foundations

## Lab Topology Summary

Six-router, three-AS topology. AS 65100 (SP core) runs R2, R3, R4, R5 in OSPF area 0.
Customer A (AS 65001, R1) is dual-homed to R2 and R3. External SP peer (AS 65002, R6)
connects to R5. Seven active links (L1–L7). R3 is OSPF-only in this lab.

## EVE-NG Import Instructions

1. In EVE-NG, log in to the web UI.
2. Navigate to **File > Import** (top menu).
3. Select the `.unl` file for this lab (export from EVE-NG or provided by the instructor).
4. Choose the target folder (e.g., `ccnp-spri/bgp/`).
5. Click **Import**. The lab appears in the file browser.
6. Double-click the lab to open it.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco CSR1000v | 4096 MB | csr1000v-universalk9.17.03.05 |
| R6 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

> Total RAM: ~6.5 GB. Within the Dell Latitude 5540 EVE-NG envelope.

## Starting the Lab

1. Select all nodes in the EVE-NG canvas and click **Start**.
2. Wait 60–90 seconds for IOSv nodes to boot; CSR1000v (R5) may take 3–5 minutes.
3. Console ports are assigned dynamically — check the EVE-NG web UI for each node's port.
4. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configurations.

## Exporting the Lab

After making topology changes in EVE-NG (adding/moving nodes or links):
1. In the EVE-NG web UI, click **File > Export**.
2. Download the updated `.unl` file.
3. Replace the existing `.unl` in the lab's `topology/` directory if version-controlling it.
