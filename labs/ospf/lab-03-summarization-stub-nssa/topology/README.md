# Topology — OSPF Lab 03: Summarization, Stub, and NSSA

Six-router dual-stack OSPF topology with one external AS router. Linear chain from R1
through R3, with R4 (Area 2), R5 (Area 3), and R6 (external AS) branching off R3.

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and log in
2. Navigate to the folder where you want the lab (e.g., `ospf/`)
3. Click **Import** (top-right menu or file manager)
4. Select `lab-03-summarization-stub-nssa.unl` from this `topology/` directory
5. After import, open the lab and verify all six nodes appear: R1, R2, R3, R4, R5, R6

> The `.unl` file is created manually in EVE-NG after drawing the topology.
> If you do not have a `.unl` file yet, build the topology using `topology.drawio`
> as a reference, then export the `.unl` from EVE-NG for future use.

## Node Configuration Reference

| Device | EVE-NG Template | Image | RAM |
|--------|----------------|-------|-----|
| R1 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R6 | Cisco IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

## Link Connections

| Link | From | Interface | To | Interface |
|------|------|-----------|----|-----------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 |
| L3 | R3 | Gi0/1 | R4 | Gi0/0 |
| L4 | R3 | Gi0/2 | R5 | Gi0/0 |
| L5 | R3 | Gi0/3 | R6 | Gi0/0 |

## Starting the Lab

1. Right-click each node and select **Start** (or use **Start all nodes**)
2. Wait approximately 60 seconds for all IOSv nodes to boot
3. Console ports are dynamically assigned — check the EVE-NG web UI or use
   `python3 setup_lab.py --host <eve-ng-ip>` (auto-discovers ports via REST API)
4. Run `setup_lab.py` to push initial configs once all nodes show the IOS prompt

## Exporting the Lab

After making topology changes in EVE-NG:

1. Close all open consoles
2. File > Export > select this lab
3. Save the `.unl` back to `topology/` to keep the package self-contained
