# Topology - Lab 04: PCE Path Computation, SRLG, and Tree SID

Seven-node SP topology: four IOS-XRv 9000 core routers (R1, R2, R3, R4), two IOSv customer edges (CE1, CE2), and one IOS-XRv 9000 PCE controller (PCE) peered with R2 over a dedicated link L6. Eight links total - five core links (L1-L5), one BGP-LS/PCEP link (L6), and two PE-CE access links (L7, L8).

## EVE-NG Import Instructions

1. Open EVE-NG in your browser and navigate to the `ccnp-spri/segment-routing/` folder.
2. Click **File > Import** and select the `.unl` file for this lab.
3. The topology loads automatically. Verify all 7 nodes appear in the canvas.
4. Right-click the lab canvas and select **Start all nodes**.
5. Wait approximately 4-6 minutes for all five IOS-XRv nodes (R1-R4 + PCE) to boot fully (IOSv boots faster).

## Node Configuration Reference

| Device | EVE-NG Template | RAM (MB) | Image |
|--------|----------------|----------|-------|
| R1 | Cisco XRv9K | 16384 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R2 | Cisco XRv9K | 16384 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R3 | Cisco XRv9K | 16384 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R4 | Cisco XRv9K | 16384 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| PCE | Cisco XRv9K | 16384 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| CE1 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |

## Starting the Lab

1. After all nodes show a green indicator, note the console ports assigned by EVE-NG (visible in the node properties or via the EVE-NG API).
2. Run `setup_lab.py --host <eve-ng-ip>` from the lab root directory to push initial-configs to all nodes.
3. Console ports are discovered automatically - no manual port lookup required.

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, rewiring links), export the updated `.unl` file via **File > Export** and replace the file in this directory so the lab package stays in sync.

## Topology Diagram

Open `topology.drawio` in Draw.io Desktop or draw.io online to view the full visual layout with interface labels and subnet annotations.
