# Lab 05 — Topology Reference

## Summary

Four-router SP core ring plus one diagonal link, all IOS-XRv 9000. The topology forms a
parallelogram: R1 top-center, R2 top-right, R3 bottom-center, R4 bottom-left. The diagonal
link L5 (R1 to R3) bisects the ring vertically and serves as the TI-LFA PQ-node anchor in
adjacent labs. This is a standalone lab: no IS-IS, no LDP — pure OSPFv2 area 0 with SR-MPLS.

Ring links: L1 (R1-R2), L2 (R2-R3), L3 (R3-R4), L4 (R4-R1).
Diagonal: L5 (R1-R3, subnet 10.1.13.0/24).

## EVE-NG Import Instructions

1. Open EVE-NG web UI.
2. Navigate to the lab folder where you want to import.
3. Click **File > Import** (or use the upload icon).
4. Select the `.unl` lab file for this lab.
5. Click **Import** and wait for confirmation.
6. The lab topology and node configurations are loaded.

## Node Configuration Reference

| Device | Role                  | EVE-NG Template | Image               | RAM   |
|--------|-----------------------|-----------------|---------------------|-------|
| R1     | SP Edge / SR Ingress  | IOS-XRv 9000    | xrv9k-fullk9.iso 7.x | 16 GB |
| R2     | SP Core               | IOS-XRv 9000    | xrv9k-fullk9.iso 7.x | 16 GB |
| R3     | SP Edge / SR Egress   | IOS-XRv 9000    | xrv9k-fullk9.iso 7.x | 16 GB |
| R4     | SP Core               | IOS-XRv 9000    | xrv9k-fullk9.iso 7.x | 16 GB |

## Starting the Lab

1. In EVE-NG, open the lab and click **Start All Nodes**.
2. Wait 8-12 minutes for IOS-XRv 9000 nodes to fully boot.
3. Boot is complete when the console shows `RP/0/0/CPU0:<hostname>#`.
4. Console ports are assigned by EVE-NG — hover over a node to see its telnet port.
5. Connect via: `telnet <eve-ng-ip> <port>`
6. Run `setup_lab.py` only after all four nodes show the router prompt.

## Exporting the Lab

After making topology changes in EVE-NG:

1. Stop all nodes.
2. Go to **File > Export** in EVE-NG.
3. Download the `.unl` file and commit it alongside this topology.drawio.
