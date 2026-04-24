# Topology — lab-00-single-area-ospfv2

Three-router linear chain (R1–R2–R3) in a single OSPF Area 0. Two Ethernet
links; no optional devices. IOSv only.

## Files

| File | Purpose |
|------|---------|
| `topology.drawio` | Conceptual topology — design reference |
| `lab-00-single-area-ospfv2.unl` | EVE-NG native lab file — export from EVE-NG after building |
| `README.md` | This file |

## Importing the Lab

1. EVE-NG web UI → **File → Import** → select `lab-00-single-area-ospfv2.unl`
2. Place at path `ospf/lab-00-single-area-ospfv2.unl` (matches `DEFAULT_LAB_PATH` in scripts)
3. Open the lab → **Start all nodes**
4. Wait ~30s for IOSv boot, then run `python3 setup_lab.py --host <eve-ng-ip>`

If you imported to a different path, pass `--lab-path <your-path>` to all scripts.

## Node Configuration

| Node | EVE-NG Template | RAM | Image |
|------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |

## Starting the Lab

After import, start all nodes and note console port assignments from the
EVE-NG web UI (right-click each node → Console). Ports are dynamic —
`setup_lab.py` discovers them via the REST API automatically.

## Exporting After Changes

If you modify the topology (add nodes, change links):
1. EVE-NG web UI → open lab → **More actions → Export**
2. Save the downloaded `.unl` here, replacing the old file
3. Commit `.unl` + `topology.drawio` together so they stay in sync

## Manual Fallback

If the `.unl` is missing or incompatible:

| Node | Platform | Links |
|------|----------|-------|
| R1 | `vios` | Gi0/0 → R2 Gi0/0 |
| R2 | `vios` | Gi0/0 → R1 Gi0/0, Gi0/1 → R3 Gi0/0 |
| R3 | `vios` | Gi0/0 → R2 Gi0/1 |

Subnets: R1–R2 = 10.1.12.0/24, R2–R3 = 10.1.23.0/24
