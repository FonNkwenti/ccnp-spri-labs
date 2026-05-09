# Topology — Fast Convergence Lab 01: NSF and NSR

## Topology Summary

Five-router IS-IS L2 meshed core (R1–R4) with one external CE (R5 in AS 65200) dual-homed via two eBGP links. Identical physical topology to lab-00. This lab adds IS-IS Graceful Restart (NSF) on R1–R4, BGP Graceful Restart on R1–R5, and IS-IS/BGP NSR configuration on R1. Seven physical links: five core links forming a ring with diagonal (L1–L5), plus two eBGP uplinks (L6 R1↔R5, L7 R3↔R5). All routers run IOSv.

## EVE-NG Import Instructions

1. In the EVE-NG web UI, navigate to the lab folder (e.g., `ccnp-spri/fast-convergence/`).
2. Click **File > Import** in the top menu.
3. Select the `.unl` file for this lab (`lab-01-nsf-and-nsr.unl`).
4. Confirm the import. EVE-NG places the lab in the current folder.
5. Open the lab by double-clicking it in the folder view.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

## Starting the Lab

1. Right-click the lab canvas and select **Start all nodes**.
2. Wait approximately 60–90 seconds for all IOSv nodes to boot.
3. Check node status — all five nodes should show a green indicator.
4. Console ports are assigned dynamically. Check each node's console port in the EVE-NG web UI (click the node, then **Console**) or retrieve via REST API.
5. Run `setup_lab.py` to push initial configurations:
   ```bash
   python3 setup_lab.py --host <eve-ng-ip>
   ```

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, modifying connections):

1. In the EVE-NG web UI, navigate to **File > Export**.
2. Save the `.unl` file.
3. Replace the old `.unl` in this folder with the updated export.
4. Commit the updated `.unl` to version control.
