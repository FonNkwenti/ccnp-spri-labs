# Topology — Lab 01: Tags, Route Types, Regex, and BGP Communities

## Diagram

See `topology.drawio` (open with draw.io desktop or draw.io VS Code extension).

## Summary

Identical physical topology to lab-00: three SP core routers (R1, R2, R3) in a triangle connected by L1/L2/L5, and one external AS router (R4) with dual eBGP sessions to R1 (L4) and R3 (L3).

Lab-01 adds logical function on top of the same physical layout:
- **R2**: redistributes bidirectionally between OSPF and IS-IS (tagger role)
- **R3**: redistributes bidirectionally with loop-prevention deny sequences
- **R1**: sets community 65100:100 inbound from R4 on FILTER_R4_IN
- **R3**: sets community 65100:200 inbound from R4 using AS-path regex filter

## IP Addressing

| Link | Subnet | R1 | R2 | R3 | R4 |
|------|--------|----|----|----|-----|
| L1 (R1↔R2) | 10.1.12.0/24 | .1 | .2 | — | — |
| L2 (R2↔R3) | 10.1.23.0/24 | — | .2 | .3 | — |
| L3 (R3↔R4) | 10.1.34.0/24 | — | — | .3 | .4 |
| L4 (R1↔R4) | 10.1.14.0/24 | .1 | — | — | .4 |
| L5 (R1↔R3) | 10.1.13.0/24 | .1 | — | .3 | — |

| Device | Loopback0 | Loopback1 | Loopback2 |
|--------|-----------|-----------|-----------|
| R1 | 10.0.0.1/32 | 172.16.1.1/24 | — |
| R2 | 10.0.0.2/32 | — | — |
| R3 | 10.0.0.3/32 | — | — |
| R4 | 10.0.0.4/32 | 172.20.4.1/24 | 172.20.5.1/24 |

## Key Policy Flows

```
AS 65200 (R4)
  │
  ├── L4 ──► R1 ─ FILTER_R4_IN: deny 172.20.5.0/24, permit 172.20.4.0/24
  │                              set community 65100:100, local-pref 150
  │
  └── L3 ──► R3 ─ FILTER_R4_ASPATH: match as-path _65200$
                                      set community 65100:200
         │
         ├── OSPF_TO_ISIS (deny tag 200, permit by type, set tag 100)
         └── ISIS_TO_OSPF (deny tag 100, permit all, set tag 200 metric 20)

R2 ─ OSPF_TO_ISIS (permit all by type, set tag 100)  ← tagger only
   └── ISIS_TO_OSPF (permit all, set tag 200 metric 20)
```
