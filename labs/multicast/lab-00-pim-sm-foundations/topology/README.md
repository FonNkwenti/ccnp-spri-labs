# Topology — PIM-SM Foundations

## Lab Topology Summary

4-router IS-IS L2 hub-and-spoke with two Linux VMs:
- R1 (center/hub) connects to R2, R3, and R4
- R2 (upper-left) connects to R1 and R3, and is the first-hop router for SRC1
- R3 (right) connects to R1 and R2 as a transit router
- R4 (bottom) connects to R1 and is the last-hop router for RCV1
- SRC1 (Ubuntu 20.04) hangs off R2 Gi0/2 on the 192.168.2.0/24 segment
- RCV1 (Ubuntu 20.04) hangs off R4 Gi0/1 on the 192.168.4.0/24 segment

**Total nodes:** 6 (4 IOSv routers + 2 Ubuntu Linux VMs)

## EVE-NG Import Instructions

1. Log in to the EVE-NG web UI.
2. Navigate to **File > Import** (or use the **+** button and select Import).
3. Select the `.unl` file for this lab (generated after building the topology in EVE-NG).
4. After import, the lab appears under your project folder.
5. Open the lab and verify all nodes are present.

> The `.unl` file is created manually inside EVE-NG. Use `topology.drawio` as the layout reference when placing nodes.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| SRC1 | Linux | 1024 MB | linux-ubuntu-server-20.04 |
| RCV1 | Linux | 1024 MB | linux-ubuntu-server-20.04 |

## Starting the Lab

1. In the EVE-NG web UI, right-click the canvas and select **Start all nodes**.
2. Wait approximately 60–90 seconds for IOSv to boot and 30–60 seconds for Linux VMs.
3. Check the node icons — they turn green when the node is reachable via console.
4. Note the console port assignments from the EVE-NG node properties (hover over each node).
5. Run `setup_lab.py` from the lab root to push initial configurations to R1–R4.

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, rewiring links):

1. Stop all nodes.
2. Go to **File > Export** in the EVE-NG web UI.
3. Save the `.unl` file and replace the copy in this repository if you want to track changes.
