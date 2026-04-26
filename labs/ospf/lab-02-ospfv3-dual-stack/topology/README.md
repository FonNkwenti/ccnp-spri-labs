# Topology — Lab 02: OSPFv3 Dual-Stack Multiarea

## Lab Topology Summary

Five IOSv routers in a chain-with-branches layout (identical physical topology to lab-01):
- R1 (Area 1) → R2 (ABR 0/1) → R3 (ABR 0/2/3) → R4 (Area 2) and R5 (Area 3)
- Four OSPF areas with dual-stack (IPv4 + IPv6) on every link
- Both OSPFv2 (IPv4) and OSPFv3 (IPv6) run simultaneously in the same area structure

The `topology.drawio` file shows IPv4 and IPv6 link addresses. The `.unl` file must be created manually in EVE-NG.

## EVE-NG Import Instructions

1. Log in to the EVE-NG web UI.
2. Navigate to the folder where you want to store this lab.
3. Click **File > Import** (or the upload icon in the top toolbar).
4. Select `lab-02-ospfv3-dual-stack.unl` from your local filesystem.
5. The lab topology will appear in the EVE-NG canvas.

> This lab uses the same five-router topology as lab-01. If lab-01 is already imported, you can duplicate its `.unl` and rename it — no cabling changes are needed.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

## Starting the Lab

1. In the EVE-NG canvas, select all nodes and click **Start**.
2. Wait approximately 60–90 seconds for all IOSv nodes to boot.
3. Console port numbers will appear in the EVE-NG UI next to each node.
4. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configs.

## Exporting the Lab

After making topology changes in EVE-NG (adding links, renaming nodes):
1. Right-click the canvas background.
2. Select **Export** and choose the `.unl` format.
3. Save the updated `.unl` file back to this directory.
