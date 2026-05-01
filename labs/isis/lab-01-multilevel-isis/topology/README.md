# Topology — Multilevel IS-IS and Route Advertisement (isis/lab-01)

Five-router chain with a fork at R3: R1–R2 in area 49.0001, R3–R4–R5 in area 49.0002,
with a single L2 backbone adjacency on the R2↔R3 link.

## EVE-NG Import Instructions

1. Log into the EVE-NG web UI.
2. Navigate to **File > Import**.
3. Select the `.unl` file for this lab (created separately in EVE-NG after wiring the topology).
4. After import, the lab appears in your lab list — open it to verify node placement.

> The `.unl` file is not included in the git repository. Create it manually in EVE-NG by
> adding nodes and connecting them as shown in `topology.drawio`, then export via
> **File > Export** to save the `.unl`.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |
| R5 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.159-3.M6 |

## Starting the Lab

1. Power on all nodes in EVE-NG (right-click > Start or Start All).
2. Wait approximately 2–3 minutes for IOSv to boot.
3. Note the console port for each node from the EVE-NG UI (hover over each node).
4. Run `setup_lab.py` to push initial configs automatically — ports are discovered at runtime.

## Exporting After Topology Changes

If you modify the EVE-NG topology (add nodes, change links), export the updated `.unl`
via **File > Export** and commit the updated file to the repository.

## Interface Wiring Summary

| Source | Interface | Target | Interface | Subnet |
|--------|-----------|--------|-----------|--------|
| R1 | GigabitEthernet0/0 | R2 | GigabitEthernet0/0 | 10.1.12.0/24 |
| R2 | GigabitEthernet0/1 | R3 | GigabitEthernet0/0 | 10.1.23.0/24 |
| R3 | GigabitEthernet0/1 | R4 | GigabitEthernet0/0 | 10.1.34.0/24 |
| R3 | GigabitEthernet0/2 | R5 | GigabitEthernet0/0 | 10.1.35.0/24 |
