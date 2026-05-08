# Topology — BGP Dual-CE Lab 00: Dual-CE iBGP Architecture and Baseline

## Lab Topology Summary

Four-router, three-AS topology. R1 and R2 are customer CEs in AS 65001. R3 is the ISP-A
PE (AS 65100); R4 is the ISP-B PE (AS 65200). Three links: R1↔R3 (eBGP to ISP-A),
R2↔R4 (eBGP to ISP-B), R1↔R2 (CE-CE iBGP underlay).

## EVE-NG Import Instructions

1. In EVE-NG, log in to the web UI.
2. Navigate to **File > Import** (top menu).
3. Select the `.unl` file for this lab (export from EVE-NG or provided by the instructor).
4. Choose the target folder (e.g., `ccnp-spri/bgp-dual-ce/`).
5. Click **Import**. The lab appears in the file browser.
6. Double-click the lab to open it.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

> Total RAM: ~2 GB. Comfortable on the Dell Latitude 5540 EVE-NG envelope.

## Starting the Lab

1. Select all nodes in the EVE-NG canvas and click **Start**.
2. Wait 60–90 seconds for the IOSv nodes to boot.
3. Console ports are assigned dynamically — check the EVE-NG web UI for each node's port.
4. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configurations.

## Exporting the Lab

After making topology changes in EVE-NG (adding/moving nodes or links):
1. In the EVE-NG web UI, click **File > Export**.
2. Download the updated `.unl` file.
3. Replace the existing `.unl` in this `topology/` directory if version-controlling it.
