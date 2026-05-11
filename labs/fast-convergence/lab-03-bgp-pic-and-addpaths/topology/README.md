# Topology — Fast Convergence Lab 03: BGP PIC and Add-Paths

## Topology Summary

Five-router IS-IS L2 meshed core (R1–R4) with one external CE (R5 in AS 65200)
dual-homed via two eBGP links. Identical physical topology to lab-00, lab-01,
and lab-02. This lab adds BGP Prefix-Independent Convergence (PIC) on all four
core routers and BGP Add-Paths on all iBGP sessions. R1 and R3 serve as BGP PIC
Edge routers (eBGP to R5); R2 and R4 serve as BGP PIC Core routers. R5 is the
external CE advertising prefix 192.0.2.0/24.

## EVE-NG Import Instructions

1. In the EVE-NG web UI, navigate to the lab folder (e.g., `ccnp-spri/fast-convergence/`).
2. Click **File > Import** in the top menu.
3. Select the `.unl` file for this lab (`lab-03-bgp-pic-and-addpaths.unl`).
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
