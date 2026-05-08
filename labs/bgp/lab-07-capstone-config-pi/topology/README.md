# Topology — BGP Lab 07 Capstone I

## Lab Topology Summary

Seven-router three-AS BGP service-provider topology. AS 65100 core runs OSPF area 0
with R4 as Route Reflector for clients R2, R3, R5. Customer A (AS 65001) is dual-homed
via R2 and R3. R5 serves as the west PE with two external peers: R6 (AS 65002, IOSv)
and R7 (AS 65003, CSR1000v for BGP FlowSpec).

- **7 routers:** R1–R7 (5 IOSv, 2 CSR1000v)
- **8 + 1 links:** L1–L8 plus dynamic-neighbor range 10.99.0.0/30
- **4 autonomous systems:** 65001, 65100, 65002, 65003

## EVE-NG Import Instructions

1. Navigate to **File > Import** in the EVE-NG web UI.
2. Select the lab `.unl` file for this lab (created manually in EVE-NG).
3. The `.unl` file is located in the lab root directory.

## Node Configuration Reference

| Device | Template | RAM | Image |
|--------|----------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco CSR1000v | 4096 MB | csr1000v-universalk9.17.03.05 |
| R6 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R7 | Cisco CSR1000v | 4096 MB | csr1000v-universalk9.17.03.05 |

## Starting the Lab

1. Start all seven nodes and wait for boot (~5-8 minutes for CSR1000v nodes).
2. Note console port assignments from the EVE-NG UI (ports are dynamic).
3. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial IP configs.
4. Open `workbook.md` and begin lab tasks.

## Exporting the Lab

After making topology changes in EVE-NG, export via **File > Export** and save
the `.unl` file to the lab root. Update `setup_lab.py` if device names or
lab path changed.
