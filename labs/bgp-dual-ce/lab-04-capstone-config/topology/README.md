# Lab 04 — Topology Diagram

## Files

- `topology.drawio` — EVE-NG-importable Draw.io diagram (6 routers, 5 links, 3 AS zones).

## Import into Draw.io

1. Open [Draw.io Desktop](https://www.drawio.com/) or https://app.diagrams.net.
2. Select **File > Open** and choose `topology.drawio`.
3. The diagram opens with a dark navy canvas (`#1a1a2e`).

## Import into EVE-NG

EVE-NG accepts `.drawio` files as topology diagrams via the built-in topology editor:

1. Log into the EVE-NG web UI.
2. Open (or create) your lab.
3. In the topology editor, click **Import** (or use the topology image upload button).
4. Upload `topology.drawio`.
5. Position nodes to match the imported image; wire them according to the link table below.

## Topology Summary

| ID | Link | Subnet | Role |
|----|------|--------|------|
| L1 | R1 Gi0/0 ↔ R3 Gi0/0 | 10.1.13.0/30 | eBGP CE↔ISP-A |
| L2 | R2 Gi0/0 ↔ R4 Gi0/0 | 10.1.24.0/30 | eBGP CE↔ISP-B |
| L3 | R1 Gi0/1 ↔ R2 Gi0/1 | 10.1.12.0/30 | CE-CE iBGP |
| L4 | R3 Gi0/1 ↔ R5 Gi0/0 | 10.1.35.0/30 | ISP-A internal iBGP |
| L5 | R4 Gi0/1 ↔ R6 Gi0/0 | 10.1.46.0/30 | ISP-B internal iBGP |

## Device Summary

| Router | Role | AS | Lo0 | Lo1 |
|--------|------|----|-----|-----|
| R1 | CE1 | 65001 | 10.0.0.1/32 | 192.168.1.1/24 |
| R2 | CE2 | 65001 | 10.0.0.2/32 | — |
| R3 | ISP-A PE | 65100 | 10.0.0.3/32 | 10.100.1.1/24 |
| R4 | ISP-B PE | 65200 | 10.0.0.4/32 | 10.200.1.1/24 |
| R5 | ISP-A Internal | 65100 | 10.0.0.5/32 | 10.100.2.1/24 |
| R6 | ISP-B Internal | 65200 | 10.0.0.6/32 | 10.200.2.1/24 |
