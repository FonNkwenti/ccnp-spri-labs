# Topology — BGP Dual-CE Lab 03: Selective Prefix Advertisement

## Lab Topology Summary

Six-router, three-AS topology — physically identical to lab-02. R1, R2 are customer CEs
in AS 65001. R3 is the ISP-A edge (AS 65100); R4 is the ISP-B edge (AS 65200). R5 inside
ISP-A and R6 inside ISP-B remain the iBGP internal hosts for verification.

Five links (no change vs. lab-02):
- L1: R1 ↔ R3 (eBGP customer-to-ISP-A)
- L2: R2 ↔ R4 (eBGP customer-to-ISP-B)
- L3: R1 ↔ R2 (CE-CE iBGP underlay)
- L4: R3 ↔ R5 (ISP-A internal, 10.1.35.0/30)
- L5: R4 ↔ R6 (ISP-B internal, 10.1.46.0/30)

**New in lab-03 (policy-only):**
- R3 and R4 each originate a default route (`0.0.0.0/0`) toward the customer.
- R1 originates `192.168.1.0/25` (Null0); R2 originates `192.168.1.128/25` (Null0).
- LOCAL_PREF=200 inbound on each CE's eBGP from its directly-attached PE.
- `TRANSIT_PREVENT` prefix-list scope tightened per CE: each CE permits the /24 plus its
  own /25 only.

## EVE-NG Import Instructions

1. In EVE-NG, log in to the web UI.
2. Navigate to **File > Import** (top menu).
3. Select the `.unl` file for this lab (export from EVE-NG or provided by the instructor).
4. Choose the target folder (e.g., `ccnp-spri/bgp-dual-ce/`).
5. Click **Import**. The lab appears in the file browser.
6. Double-click the lab to open it.

## Node Configuration Reference

| Device | EVE-NG Template | RAM | Image |
|--------|----------------|-----|-------|
| R1 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |
| R6 | Cisco IOSv | 512 MB | vios-adventerprisek9-m.SPA.156-2.T |

> Total RAM: ~3 GB.

## Starting the Lab

1. Select all six nodes in the EVE-NG canvas and click **Start**.
2. Wait 60–90 seconds for the IOSv nodes to boot.
3. Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configurations (lab-02
   solution state for all six devices). LP route-maps, default-route origination, /25
   origination, and the tightened `TRANSIT_PREVENT` prefix-lists are the lab challenge.

## Exporting the Lab

After making topology changes in EVE-NG (adding/moving nodes or links):
1. In the EVE-NG web UI, click **File > Export**.
2. Download the updated `.unl` file.
3. Replace the existing `.unl` in this `topology/` directory if version-controlling it.
