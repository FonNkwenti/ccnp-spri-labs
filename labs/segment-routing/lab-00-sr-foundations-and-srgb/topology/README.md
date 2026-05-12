# Lab 00 Topology: SR-MPLS Foundations, SRGB, and Prefix SIDs

## Diagram

Open `topology.drawio` in Draw.io (desktop or web) to view the full diagram.
All four core routers use the **Cisco ASR 9000** icon (`mxgraph.cisco19.rect;prIcon=asr_9000`).

## Device Summary

| Router | Platform | Loopback0 | IS-IS NET | Prefix SID | Label |
|--------|----------|-----------|-----------|------------|-------|
| R1 | ASR 9000 (xrv9k) | 10.0.0.1/32 | 49.0001.0000.0000.0001.00 | index 1 | 16001 |
| R2 | ASR 9000 (xrv9k) | 10.0.0.2/32 | 49.0001.0000.0000.0002.00 | index 2 | 16002 |
| R3 | ASR 9000 (xrv9k) | 10.0.0.3/32 | 49.0001.0000.0000.0003.00 | index 3 | 16003 |
| R4 | ASR 9000 (xrv9k) | 10.0.0.4/32 | 49.0001.0000.0000.0004.00 | index 4 | 16004 |

## Link Summary

| Link | Endpoints | Subnet | R1-side Intf | Remote Intf |
|------|-----------|--------|-------------|-------------|
| L1 | R1 ↔ R2 | 10.1.12.0/24 | R1 Gi0/0/0/0 | R2 Gi0/0/0/0 |
| L2 | R2 ↔ R3 | 10.1.23.0/24 | R2 Gi0/0/0/1 | R3 Gi0/0/0/0 |
| L3 | R3 ↔ R4 | 10.1.34.0/24 | R3 Gi0/0/0/1 | R4 Gi0/0/0/0 |
| L4 | R1 ↔ R4 | 10.1.14.0/24 | R1 Gi0/0/0/1 | R4 Gi0/0/0/1 |
| L5 | R1 ↔ R3 | 10.1.13.0/24 | R1 Gi0/0/0/2 | R3 Gi0/0/0/2 |

## Notes

- All links run IS-IS Level 2 with SR-MPLS enabled.
- L5 (R1↔R3 diagonal) is the critical path for TI-LFA in lab-01 — it provides the link-disjoint alternate for R2↔R4 traffic.
- SRGB 16000-23999 is consistent across all four routers.
- SRLB 15000-15999 (IOS-XR default) provides adjacency SID allocation on each node.
