# Topology — lab-02-rpl-vs-route-maps

**Lab title**: Routing Policy and Manipulation — RPL vs Route Maps

## Device Summary

| Device | Platform | AS     | Loopbacks                                    | Role              |
|--------|----------|--------|----------------------------------------------|-------------------|
| R1     | IOSv     | 65100  | Lo0: 10.0.0.1/32, Lo1: 172.16.1.0/24        | IGP hub / eBGP PE |
| R2     | IOSv     | 65100  | Lo0: 10.0.0.2/32                             | IGP transit       |
| R3     | IOSv     | 65100  | Lo0: 10.0.0.3/32                             | IGP transit / ASBR|
| R4     | IOSv     | 65200  | Lo0: 10.0.0.4/32, Lo1: 172.20.4.0/24, Lo2: 172.20.5.0/24 | eBGP peer (AS 65200) |
| XR1    | XRv    | 65100  | Lo0: 10.0.0.5/32, Lo1: 172.16.11.0/24       | XR IS-IS/iBGP node|
| XR2    | XRv    | 65100  | Lo0: 10.0.0.6/32                             | XR IS-IS/iBGP node|

## Link Table

| Link | Source         | Dest           | Subnet         | Protocol      |
|------|----------------|----------------|----------------|---------------|
| L1   | R1: Gi0/0      | R2: Gi0/0      | 10.1.12.0/24   | OSPF/IS-IS    |
| L2   | R2: Gi0/1      | R3: Gi0/0      | 10.1.23.0/24   | OSPF/IS-IS    |
| L3   | R3: Gi0/1      | R4: Gi0/0      | 10.1.34.0/24   | eBGP          |
| L4   | R1: Gi0/1      | R4: Gi0/1      | 10.1.14.0/24   | eBGP          |
| L5   | R1: Gi0/2      | R3: Gi0/2      | 10.1.13.0/24   | OSPF/IS-IS    |
| L6   | R2: Gi0/2      | XR1: Gi0/0/0/0 | 10.1.25.0/24   | IS-IS         |
| L7   | R3: Gi0/3      | XR2: Gi0/0/0/0 | 10.1.36.0/24   | IS-IS         |
| L8   | XR1: Gi0/0/0/1 | XR2: Gi0/0/0/1 | 10.1.56.0/24   | IS-IS / iBGP  |

## Layout Description

```
┌──────────────────────────────────────────────────────────────────┐
│  AS 65100  (teal dashed zone)                                    │
│                                                                  │
│  R1 ──────── R2 ──────── XR1                                    │
│  │  (L1)    │  (L2)   │  (L6)  │                               │
│  │          │         │        │  (L8)                          │
│  │  (L5)   R3 ──────── XR2                                     │
│  │           │  (L7)                                            │
│  │ (L4)      │ (L3)                                             │
│  │           │                                                  │
└──│───────────│──────────────────────────────────────────────────┘
   │           │
   ▼           ▼
┌──────────────┐
│  AS 65200    │
│  (orange)    │
│     R4       │
└──────────────┘
```

## Key Topology Notes

- **eBGP boundary**: L3 (R3-R4) and L4 (R1-R4) cross the AS 65100/65200 boundary
- **IGP domain**: R1/R2/R3 run OSPF and IS-IS; XR1/XR2 extend IS-IS into the XR cluster
- **XRv cluster**: XR1 and XR2 are visually distinguished by a blue border and label
- **Policy comparison**: R1/R2/R3 use IOS route maps; XR1/XR2 use IOS-XR RPL (route-policy language) — the key lab contrast

## Diagram File

Open `topology.drawio` in Draw.io (desktop or web) to view the full interactive diagram.
Style follows the project's Cisco19 dark-canvas standard.
