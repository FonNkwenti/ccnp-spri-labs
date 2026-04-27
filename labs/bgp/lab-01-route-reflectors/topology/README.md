# Lab 01 — Topology Reference

## Topology Summary

This lab uses the same six-router, three-AS physical topology as lab-00, with R4 promoted
to Route Reflector. The iBGP architecture changes significantly:

- **6 routers**: R1 (CE), R2 (PE East-1), R3 (PE East-2), R4 (P / RR), R5 (PE West), R6 (External SP)
- **3 autonomous systems**: AS 65001 (Customer A), AS 65100 (SP Core), AS 65002 (External SP)
- **7 physical links**: L1–L7 (see cabling table below)
- **Route Reflector**: R4 is the single RR for AS 65100, serving R2, R3, and R5 as clients
- **Cluster ID**: 10.0.0.4 (R4's own Loopback0 address)
- **OSPF Area 0**: R2, R3, R4, R5 — all internal SP links and loopback0 interfaces
- **iBGP sessions**: R4 reflects between all three RR clients; legacy R2-R5 direct session retained (additive progressive rule)
- **eBGP sessions**: R1-R2 (AS65001 to AS65100 primary), R5-R6 (AS65100 to AS65002)
- **L2 (R1-R3)**: IP-addressed but no BGP in lab-01; second eBGP path not activated until lab-02

## EVE-NG Import Instructions

1. Open the EVE-NG web UI at `http://<eve-ng-ip>`.
2. Navigate to the lab folder where you want to import the topology.
3. Click **File > Import** in the top menu.
4. Select the `.unl` file exported from this lab (located alongside this README after export).
5. Click **Import** and wait for the confirmation message.
6. The lab will appear in your lab list. Open it to view and start nodes.

> The `.drawio` file in this directory is a **reference diagram only** — EVE-NG uses `.unl`
> format for its native topology. Use `setup_lab.py` to push the initial configuration to
> running nodes.

## Node Configuration Table

| Device | Role | EVE-NG Template | Image | RAM |
|--------|------|-----------------|-------|-----|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | PE East-1 / RR client (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | PE East-2 / RR client (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | P Router / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5 | PE West / RR client (AS 65100) | CSR1000v | csr1000v-universalk9.17.03.05 | 3072 MB |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

> R5 runs IOS-XE (CSR1000v). Its interface names differ from IOSv: GigabitEthernet2 and
> GigabitEthernet3 are used for the core and external links respectively.

## Cabling Table

| Link ID | Source | Interface | Target | Interface | Subnet | Purpose |
|---------|--------|-----------|--------|-----------|--------|---------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/24 | eBGP AS65001 to AS65100 (primary) |
| L2 | R1 | Gi0/1 | R3 | Gi0/0 | 10.1.13.0/24 | IP-only in lab-01; eBGP activated in lab-02 |
| L3 | R2 | Gi0/1 | R4 | Gi0/0 | 10.1.24.0/24 | OSPF + iBGP (R2 to RR) |
| L4 | R3 | Gi0/1 | R4 | Gi0/1 | 10.1.34.0/24 | OSPF + iBGP (R3 to RR) |
| L5 | R4 | Gi0/2 | R5 | Gi2 | 10.1.45.0/24 | OSPF + iBGP (R5 to RR) |
| L6 | R2 | Gi0/2 | R3 | Gi0/2 | 10.1.23.0/24 | OSPF IGP only; East-PE resilience |
| L7 | R5 | Gi3 | R6 | Gi0/0 | 10.1.56.0/24 | eBGP AS65100 to AS65002 |

## Starting the Lab

1. In the EVE-NG web UI, open the lab.
2. Click **Start all nodes** (or start each node individually by right-clicking).
3. Wait approximately 2–3 minutes for IOSv nodes to boot; CSR1000v (R5) may take up to
   5 minutes.
4. Check each node's console by clicking its icon in the topology and selecting
   **Console**. You should see the IOS/IOS-XE prompt.
5. Once all consoles are responsive, run the setup script to push the base configuration:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

6. Verify the base config is loaded by checking `show ip ospf neighbor` on R2 — you should
   see R3, R4 as OSPF neighbors before starting the lab tasks.

## Exporting the Lab

If you modify the topology in EVE-NG (add nodes, change connections), export the updated
`.unl` file so it can be committed to the repository:

1. In the EVE-NG web UI, open the lab.
2. Click **File > Export**.
3. Select the export path and click **Export**.
4. Copy the resulting `.unl` file into this `topology/` directory, replacing the old one.
5. Commit the updated file to git.

> Do not edit the `.drawio` file to match topology changes made in EVE-NG — update the
> `.drawio` separately using the Draw.io desktop app or web editor, following the visual
> style guide in `.agent/skills/drawio/SKILL.md`.
