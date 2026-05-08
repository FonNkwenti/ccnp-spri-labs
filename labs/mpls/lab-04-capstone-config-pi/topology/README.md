# Topology — MPLS Lab 04 Capstone I

## Lab Topology Summary

Six-router MPLS service-provider network with two customer edges. The core
(PE1-P1-P2-PE2) forms a diamond with a P1↔P2 cross-link (L4), giving PE1 two
link-disjoint paths to PE2 plus a third path through both P routers for RSVP-TE
explicit-path demonstrations.

- **4 core routers:** PE1, P1, P2, PE2 (AS 65100, IS-IS L2, MPLS LDP, RSVP-TE)
- **2 customer edges:** CE1 (AS 65101), CE2 (AS 65102)
- **7 links:** L1–L7, all GigabitEthernet

## EVE-NG Import Instructions

1. Navigate to **File > Import** in the EVE-NG web UI.
2. Select the lab `.unl` file for this lab (created manually in EVE-NG).
3. The `.unl` file is located in the lab root directory.

## Node Configuration Reference

| Device | Template | RAM | Image |
|--------|----------|-----|-------|
| PE1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

## Starting the Lab

1. Start all six nodes and wait for boot (~3-5 minutes).
2. Note console port assignments from the EVE-NG UI (ports are dynamic).
3. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial IP configs.
4. Open `workbook.md` and begin lab tasks.

## Exporting the Lab

After making topology changes in EVE-NG, export via **File > Export** and save
the `.unl` file to the lab root. Update `setup_lab.py` if device names or
lab path changed.
