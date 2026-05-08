# Topology — Lab 00: Static IPv6-in-IPv4 and 6to4 Tunnels

## Topology Summary

4-node linear chain. R1 and R4 are dual-stack CE/PE routers (IOSv); R2 and R3 are IPv4-only P routers (IOSv). Three physical links (L1, L2, L3) form the IPv4 backbone. Two tunnel overlays (Tunnel0 static, Tunnel1 6to4) connect R1↔R4 end-to-end.

## EVE-NG Import Instructions

1. Open the EVE-NG web UI at `http://<eve-ng-ip>`.
2. Navigate to **File > Import** in the top menu.
3. Select the `.unl` file for this lab (`lab-00-manual-and-6to4-tunnels.unl`) and click **Import**.
4. The lab appears in your lab list. Open it to see the topology.

The `.unl` file is created by recreating the topology in EVE-NG manually or by importing an exported copy.

## Node Configuration Reference

| Device | EVE-NG Template | Image | RAM |
|--------|-----------------|-------|-----|
| R1 | Cisco IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R2 | Cisco IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R3 | Cisco IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R4 | Cisco IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |

Connect interfaces according to the cabling table in `workbook.md` Section 3.

## Starting the Lab

1. In the EVE-NG web UI, right-click the canvas and select **Start all nodes**.
2. Wait 60–90 seconds for all IOSv nodes to boot fully.
3. Open the EVE-NG web UI — each node shows a console port in the tooltip on hover.
4. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configurations.

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, reconnecting links):

1. In the EVE-NG web UI, go to **File > Export**.
2. Save the `.unl` file and place it alongside this `topology/` folder for version control.
