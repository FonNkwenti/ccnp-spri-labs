# Topology — IS-IS Lab 02: Dual-Stack Summarization and Route Leaking

## Topology Summary

Six-router topology extending the lab-01 two-area IS-IS design with full dual-stack IPv6 support and an external partner router. The backbone chain runs R1 — R2 — R3, with R4 and R5 as L1 stubs in area 49.0002 and R6 as a non-IS-IS external device connected to R3.

| Attribute | Value |
|-----------|-------|
| Routers | 6 (R1–R6) |
| IS-IS routers | 5 (R1–R5) |
| External (non-IS-IS) | 1 (R6) |
| IS-IS areas | 2 (49.0001, 49.0002) |
| Links | 5 (L1–L5) |
| Topology file | `topology.drawio` |

## EVE-NG Import Instructions

1. Open the EVE-NG web UI in your browser (`http://<eve-ng-ip>/`).
2. Navigate to the folder where you want to store the lab (e.g., `ccnp-spri/isis/`).
3. Click **File → Import** (or the import icon in the toolbar).
4. Select the `.unl` file for this lab. The `.unl` file is created manually in EVE-NG — use `topology.drawio` as your layout reference when placing nodes.
5. The lab topology will appear in the EVE-NG canvas. Verify that all six nodes (R1–R6) and five links are present.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

**Interface mapping (EVE-NG Gi numbering = lab Gi numbering):**

| Device | EVE-NG Interface | Lab Role |
|--------|-----------------|----------|
| R3 | GigabitEthernet0/3 | Link to R6 (L5) — activate in lab-02 |

## Starting the Lab

1. Right-click each node in EVE-NG and select **Start** (or use **Start All Nodes**).
2. Wait approximately 2–3 minutes for all IOSv nodes to complete boot.
3. Note the console port assignments from the EVE-NG UI (hover over each node).
4. Run setup: `python3 setup_lab.py --host <eve-ng-ip>`
5. Open `workbook.md` and begin Section 5.

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, links, or labels):
1. Click **File → Export** in the EVE-NG web UI.
2. Save the `.unl` file locally.
3. Store it alongside this `topology/` directory for version control.
