# Lab 00 — Topology

## Summary

A 4-router routing-policy starter topology: a 3-router SP core (AS 65100) running OSPF area 0,
IS-IS L2, and iBGP full-mesh, plus a single external router (R4 in AS 65200) that dual-homes
back into AS 65100 via eBGP to R1 and R3. R2 is pure transit — it has no eBGP. The two
external prefixes on R4 (172.20.4.0/24 and 172.20.5.0/24) become the targets of the inbound
filter exercise on R1.

```
                          AS 65100 (SP core)
                ┌─────────────────────────────────────────────┐
                │   ┌────┐  L1   ┌────┐                       │
                │   │ R1 ├───────┤ R2 │                       │
                │   └─┬──┘       └─┬──┘                       │
                │     │ L5         │ L2                       │
                │     │            │                          │
                │   ┌─┴──┐ ────────┘                          │
                │   │ R3 │                                    │
                │   └─┬──┘                                    │
                └─────┼────────────────────────────────────────┘
                      │ L3 (eBGP)         L4 (eBGP) ──── to R1
                      │                   │
                ┌─────┴─────────┐         │
                │       R4      ├─────────┘
                │   AS 65200    │
                │ Lo1 172.20.4  │
                │ Lo2 172.20.5  │
                └───────────────┘
```

---

## EVE-NG Import Instructions

1. Open the EVE-NG web UI and log in.
2. Navigate to **File > Import** (or use the Labs menu > Import).
3. Select the `.unl` file for this lab (generated from `topology.drawio`).
4. After import, the lab appears in your lab list.
5. Open the lab — all 4 nodes and connections are pre-wired per this topology.

---

## Node Configuration Table

| Device | Role | ASN | Template | Image | RAM |
|--------|------|-----|----------|-------|-----|
| R1 | SP core / eBGP edge | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | SP core / transit | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | SP core / eBGP edge | 65100 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | External AS | 65200 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

---

## Starting the Lab

1. Open the lab in EVE-NG.
2. Select all nodes (Ctrl+A) and click **Start**.
3. Wait approximately 3 minutes for IOSv nodes to reach a usable prompt.
4. Push the IP-only baseline:
   ```bash
   python labs/routing-policy/lab-00-route-maps-foundations/setup_lab.py --host <eve-ng-ip>
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
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | OSPF area 0 + IS-IS L2 + iBGP transport |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | OSPF area 0 + IS-IS L2 + iBGP transport |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | eBGP AS 65100 ↔ AS 65200 |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | eBGP AS 65100 ↔ AS 65200 (multihoming) |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | OSPF area 0 + IS-IS L2 + iBGP transport (diagonal) |
