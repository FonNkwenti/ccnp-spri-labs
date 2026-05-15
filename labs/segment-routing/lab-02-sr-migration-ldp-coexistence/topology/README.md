# Topology — Lab 02: SR Migration: LDP Coexistence, Mapping Server, and SR-Prefer

## Lab Topology Summary

4-router SP core in a square ring with a diagonal link (L5). All routers are IOS-XRv 9000 running IS-IS Level-2, SR-MPLS, TI-LFA, and (new in this lab) LDP. R1 also serves as the SR mapping server for the 192.0.2.0/24 legacy customer prefix range. Links: L1 R1↔R2, L2 R2↔R3, L3 R3↔R4, L4 R1↔R4, L5 R1↔R3 (diagonal).

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and navigate to your lab folder.
2. Click **File > Import** (or drag-and-drop) and select `lab-02-sr-migration-ldp-coexistence.unl`.
3. Once imported, open the lab and verify all four nodes (R1, R2, R3, R4) appear in the canvas.
4. Right-click each node and select **Start** — or use **Actions > Start all nodes**.
5. Wait approximately 8-12 minutes for all IOS-XRv 9000 nodes to complete boot.
6. Verify by connecting to the console of any node and checking for the `RP/0/0/CPU0:<hostname>#` prompt.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco XRv 9000 | 16384 MB | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R2 | Cisco XRv 9000 | 16384 MB | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R3 | Cisco XRv 9000 | 16384 MB | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R4 | Cisco XRv 9000 | 16384 MB | xrv9k-fullk9-x.vrr.vga-24.3.1 |

## Starting the Lab

After all nodes have booted:
```bash
python3 setup_lab.py --host <eve-ng-ip>
```

Console port numbers are assigned by EVE-NG dynamically. Check the EVE-NG web UI or hover over each node to find the Telnet port.

## Exporting the Lab

To export the topology after making changes in EVE-NG:
1. Stop all nodes.
2. In the EVE-NG web UI, right-click the lab tab and select **Export**.
3. Save the `.unl` file to replace the one in this directory if the topology changed.
