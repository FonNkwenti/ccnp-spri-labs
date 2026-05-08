# Topology — MPLS Lab 04: Full Mastery — Capstone I

## Lab Topology Summary

Six-node topology: four SP core routers (PE1, P1, P2, PE2) forming a diamond with a P1↔P2
cross-link, plus two customer edge routers (CE1, CE2) connected to the PE edges. Seven physical
links (L1–L7). The core runs IS-IS L2 + MPLS LDP + RSVP-TE; CE–PE links are plain IP for eBGP.
PE1 is the RSVP-TE headend with Tunnel10 (primary dynamic + secondary explicit PE1-via-P2);
PE2 is the tail. P1 and P2 are BGP-free transit nodes — they carry no customer routes, only
labeled traffic.

This is a `clean_slate` capstone — initial-configs contain only IP addressing. The student
builds the entire MPLS stack (IS-IS, LDP, iBGP+LU, eBGP, MPLS-TE, Tunnel10, autoroute) from
scratch.

## EVE-NG Import Instructions

1. In EVE-NG web UI, navigate to your lab folder (e.g. `ccnp-spri/mpls/`).
2. Click **File → Import** (or the upload icon on the folder toolbar).
3. Select the `.unl` file for this lab from your local machine.
4. After import, the lab appears in the folder listing. Click it to open.

> The `.unl` file is hand-built in EVE-NG. The `topology.drawio` in this folder is a
> reference diagram — use it to replicate the node placement and links in EVE-NG.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| PE1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

Interface mapping (EVE-NG e0 = Gi0/0, e1 = Gi0/1, e2 = Gi0/2):

- PE1 e0 → CE1 e0 (L1), PE1 e1 → P1 e0 (L2), PE1 e2 → P2 e0 (L3)
- P1 e1 → P2 e1 (L4), P1 e2 → PE2 e1 (L5)
- P2 e2 → PE2 e2 (L6)
- PE2 e0 → CE2 e0 (L7)

## Starting the Lab

1. In EVE-NG, open the lab and click **Start all nodes**.
2. Wait ~60 seconds for all IOSv nodes to finish booting.
3. Console port assignments appear in the EVE-NG UI when you hover over each node.
4. Note the port for each device and run `setup_lab.py` from the project root:
   ```bash
   python3 labs/mpls/lab-04-capstone-config/setup_lab.py --host <eve-ng-ip>
   ```

`setup_lab.py` pushes IP addressing only (clean_slate). All MPLS protocols are left
unconfigured — building them is the lab itself.

## Exporting the Lab

After making topology changes in EVE-NG (adding nodes, reconnecting links):
1. In the lab, click **File → Export**.
2. Save the `.unl` file. Replace the existing `.unl` in your local copy if version-tracking it.
