# Lab 08: BGP Comprehensive Troubleshooting — Topology

## Summary

Three-AS service-provider topology with a 7th external peer for FlowSpec — physically
identical to lab-07 (capstone configuration). The topology layout, link table, and node
sizing match lab-07 exactly. The **only difference** is that lab-08 ships pre-broken: 6
concurrent faults are baked into `initial-configs/`. The clean target state is identical
to lab-07's solution.

```
                               AS 65100 (SP Core, OSPF area 0, R4 = RR)
                ┌───────────────────────────────────────────────────────────────┐
                │                                                               │
AS 65001        │   ┌────┐ L3   ┌────┐ L5   ┌────┐                              │
┌──────┐  L1    │   │ R2 ├──────┤ R4 ├──────┤ R5 │   L7   ┌──────┐              │
│  R1  ├────────┼───┤PE-E1│      │ RR │      │PE-W├────────┤  R6  │ AS 65002    │
│  CE  │        │   └─┬──┘      └─┬──┘      └─┬──┘        └──────┘              │
└──┬───┘  L2    │     │ L6        │ L4        │ L8                              │
   │            │   ┌─┴──┐       │           │                                  │
   └────────────┼───┤ R3 ├───────┘           │   ┌──────┐ AS 65003              │
                │   │PE-E2│                  └───┤  R7  │ FlowSpec               │
                │   └────┘                       └──────┘ originator             │
                └───────────────────────────────────────────────────────────────┘
   L8 (10.99.0.0/30 dynamic-neighbor range): R1 Gi0/2 ↔ R2 Gi0/3
```

### Layout Description

| Zone | Devices | ASN |
|------|---------|-----|
| Customer A | R1 | 65001 |
| SP Core (East PEs) | R2, R3 | 65100 |
| SP Core (P/RR) | R4 | 65100 |
| SP Core (West PE) | R5 | 65100 |
| External SP Peer | R6 | 65002 |
| External FlowSpec Originator | R7 | 65003 |

R5 and R7 are CSR1000v (IOS-XE 17.3) for FlowSpec SAFI support; all others are IOSv
(IOS 15.9).

---

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and log in.
2. Navigate to **File > Import** (or use the Labs menu > Import).
3. Select the `.unl` file for this lab (generated from `topology.drawio`).
4. After import, the lab appears in your lab list.
5. Open the lab — all 7 nodes and connections are pre-wired per this topology.

---

## Node Configuration Table

| Device | Role | ASN | Template | Image | RAM |
|--------|------|-----|----------|-------|-----|
| R1 | Customer A CE | 65001 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | PE East-1 / dynamic-neighbor listen | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | PE East-2 (multihome backup) | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | P-router / Route Reflector | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5 | PE West / FlowSpec installer | 65100 | csr1000v | csr1000v-universalk9.17.03.05 | 3072 MB |
| R6 | External SP Peer | 65002 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R7 | External FlowSpec Originator | 65003 | csr1000v | csr1000v-universalk9.17.03.05 | 3072 MB |

---

## Starting the Lab

1. Open the lab in EVE-NG.
2. Select all nodes (Ctrl+A) and click **Start**.
3. Wait approximately 3 minutes for IOSv nodes and 5 minutes for the two CSR1000v
   nodes (R5, R7) to reach a usable prompt.
4. Push the pre-broken baseline:
   ```bash
   python labs/bgp/lab-08-capstone-troubleshooting/setup_lab.py --host <eve-ng-ip>
   ```
5. Console into any device:
   ```bash
   telnet <eve-ng-ip> <console-port>
   ```
   Console port numbers are shown in the EVE-NG UI node properties panel.

---

## Exporting the Lab

To export the lab as a `.unl` archive for sharing or backup:

1. In the EVE-NG web UI, right-click the lab in the lab list.
2. Select **Export** and save the `.unl` file.
3. Alternatively, lab files live at:
   ```
   /opt/unetlab/labs/<your-folder>/<lab-name>.unl
   ```

---

## Link Reference

| Link | Source | Destination | Subnet | Purpose |
|------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | eBGP AS 65001 ↔ AS 65100 (primary) |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.1.13.0/24 | eBGP AS 65001 ↔ AS 65100 (backup) |
| L3 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/24 | OSPF + iBGP R2↔R4 (RR client) |
| L4 | R3 Gi0/1 | R4 Gi0/1 | 10.1.34.0/24 | OSPF + iBGP R3↔R4 (RR client) |
| L5 | R4 Gi0/2 | R5 Gi2 | 10.1.45.0/24 | OSPF + iBGP R4↔R5 (RR client) |
| L6 | R2 Gi0/2 | R3 Gi0/2 | 10.1.23.0/24 | OSPF only (East-PE direct) |
| L7 | R5 Gi3 | R6 Gi0/0 | 10.1.56.0/24 | eBGP AS 65100 ↔ AS 65002 + FlowSpec apply |
| L8 (FS) | R5 Gi4 | R7 Gi1 | 10.1.57.0/24 | eBGP AS 65100 ↔ AS 65003 (FlowSpec SAFI) |
| L8 (Dyn) | R1 Gi0/2 | R2 Gi0/3 | 10.99.0.0/30 | Dynamic-neighbor listen range demo |
