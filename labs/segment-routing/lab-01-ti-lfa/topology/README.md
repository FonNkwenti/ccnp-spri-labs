# Topology — Lab 01: TI-LFA

## Topology Summary

Four IOS-XRv 9000 routers (R1–R4) in a square ring with one diagonal link (L5). Five
IS-IS L2 links total: L1 top (R1↔R2), L2 right (R2↔R3), L3 bottom (R3↔R4), L4 left
(R1↔R4), L5 diagonal (R1↔R3). The diagonal is the key TI-LFA alternate path that enables
100% repair coverage.

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and navigate to the lab directory.
2. Click **File → Import** (or the import icon in the toolbar).
3. Select `lab-01-ti-lfa.unl` from your local machine.
4. EVE-NG places the imported lab in the current directory.
5. Open the lab, verify all four nodes are present.

The `.unl` file is created and maintained manually in EVE-NG. This `topology/` folder
contains the reference diagram (`topology.drawio`) — import it into draw.io for a rendered
view of the intended physical layout.

## Node Configuration Reference

| Device | EVE-NG Template   | RAM   | Image                      |
|--------|-------------------|-------|----------------------------|
| R1     | Cisco IOS XRv (classic) | 3 GB | xrvr-os-mbi-6.3.1    |
| R2     | Cisco IOS XRv (classic) | 3 GB | xrvr-os-mbi-6.3.1    |
| R3     | Cisco IOS XRv (classic) | 3 GB | xrvr-os-mbi-6.3.1    |
| R4     | Cisco IOS XRv (classic) | 3 GB | xrvr-os-mbi-6.3.1    |

## Starting the Lab

1. Power on all nodes via **Start all nodes** in the EVE-NG UI.
2. IOS-XRv 9000 boot time: **8–12 minutes**. Wait until the
   `RP/0/0/CPU0:<hostname>#` prompt appears on every console before running setup.
3. Note the console port assignments from the EVE-NG node properties panel — these are
   passed automatically to `setup_lab.py` at runtime via the REST API.

## Exporting the Lab

After making topology changes in EVE-NG (adding/removing nodes or links):

1. Stop all nodes.
2. Click **File → Export** in the EVE-NG UI.
3. Download the updated `.unl` file and store it alongside this lab folder.
