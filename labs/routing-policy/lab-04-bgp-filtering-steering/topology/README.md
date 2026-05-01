# Topology — lab-04-bgp-filtering-steering

6-router SP core: R1/R2/R3/R4 (IOSv) + XR1/XR2 (XRv9k). Topology is identical to
lab-03. R4 is in AS 65200 with dual eBGP sessions to R1 (L4) and R3 (L3). IS-IS L1-L2
boundary on R2↔XR1 (L6) carried forward from lab-03.

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and navigate to your lab folder.
2. Click **File → Import** (or use the import icon in the toolbar).
3. Select the `.unl` file exported from a previous EVE-NG session for this lab.
   If no `.unl` exists yet, create the topology manually using the node reference below
   and export it once done.
4. After import, the topology appears in the canvas. Verify all links are connected.

## Node Configuration Reference

| Device | EVE-NG Template | vCPUs | RAM | Image |
|--------|----------------|-------|-----|-------|
| R1 | Cisco IOSv | 1 | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 1 | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 1 | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 1 | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| XR1 | Cisco XRv 9000 | 2 | 4096 MB | xrv9k-fullk9-x.vrr-6.6.3 |
| XR2 | Cisco XRv 9000 | 2 | 4096 MB | xrv9k-fullk9-x.vrr-6.6.3 |

## Starting the Lab

1. In the EVE-NG canvas, select all nodes and click **Start**.
2. IOSv nodes boot in ~60 seconds. XRv9k nodes require ~10 minutes.
3. Console port assignments appear in the node properties panel (right-click a node → Edit).
4. Run `setup_lab.py --host <eve-ng-ip>` once all nodes show console prompts.

## Exporting the Lab

After making topology changes in the EVE-NG canvas:
1. Click **File → Export** and save the `.unl` file.
2. Store the `.unl` alongside this `topology/` folder for version control.
   The `.unl` is not checked into git by default (it is binary/XML and regenerated from EVE-NG).
