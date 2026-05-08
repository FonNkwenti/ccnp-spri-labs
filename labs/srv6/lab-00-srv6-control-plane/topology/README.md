# Topology — SRv6 Lab 00: IS-IS Control Plane

Six-router IOS-XRv 9000 IS-IS L2 dual-stack core: a four-node P ring (P1-P2-P3-P4)
with a diagonal P1↔P3 and two PE routers (PE1 off P1, PE2 off P3). Seven physical
links, dual-stack IPv4/IPv6, SRv6 locator block fc00:0::/32.

## EVE-NG Import

1. Open EVE-NG Web UI → File → Import
2. Select the `.unl` file from this lab's EVE-NG export
3. The lab imports as `srv6/lab-00-srv6-control-plane.unl`

## Node Configuration

| Device | Template | RAM | Image |
|--------|----------|-----|-------|
| P1 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |
| P2 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |
| P3 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |
| P4 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |
| PE1 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |
| PE2 | Cisco IOS-XRv 9000 | 4096 MB | xrv9k-fullk9-7.1.1 |

## Starting the Lab

1. Start all 6 nodes (select all → Start)
2. Wait 8–12 minutes for all nodes to reach `RP/0/0/CPU0:<hostname>#` prompt
3. Note console port assignments from the EVE-NG UI (right-click → Properties)
4. Run `python3 setup_lab.py --host <eve-ng-ip>` from the lab root

## Exporting

After making topology changes in EVE-NG:
1. File → Export → Save the `.unl` file
2. Replace the `.unl` in this lab's directory
3. Commit with a message describing the topology change
