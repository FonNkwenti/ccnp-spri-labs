# Topology — Lab 01: Multiarea OSPFv2 and LSA Propagation

## Lab Topology Summary

Five IOSv routers in a chain-with-branches layout:
- R1 (Area 1) → R2 (ABR 0/1) → R3 (ABR 0/2/3) → R4 (Area 2) and R5 (Area 3)
- Four OSPF areas: Area 0 (backbone), Area 1, Area 2, Area 3
- Four point-to-point links on /24 subnets

The `topology.drawio` file is the Cisco-style reference diagram. The `.unl` file must be created manually in EVE-NG.

## EVE-NG Import Instructions

1. Log in to the EVE-NG web UI.
2. Navigate to the folder where you want to store this lab.
3. Click **File > Import** (or the upload icon in the top toolbar).
4. Select `lab-01-multiarea-ospfv2.unl` from your local filesystem.
5. The lab topology will appear in the EVE-NG canvas.

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
