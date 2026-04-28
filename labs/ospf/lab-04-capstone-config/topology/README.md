# Topology — OSPF Lab 04: Capstone I

## Physical Layout

Six IOSv routers connected in a hub-and-spoke pattern centered on R3 (the triple ABR + ASBR),
with R2 acting as the Area 0 / Area 1 ABR.

```
[R1]──Area 1──[R2]──Area 0──[R3]──Area 2──[R4]
                               │
                             Area 3
                               │
                              [R5]
                               │
                             External
                               │
                              [R6]
```

## Area Boundaries

| Area | Type | Routers | Links |
|------|------|---------|-------|
| Area 0 | Backbone | R2 (Gi0/1), R3 (Gi0/0) | 10.1.23.0/24 |
| Area 1 | Standard | R1 (all), R2 (Gi0/0) | 10.1.12.0/24 |
| Area 2 | Totally Stubby | R3 (Gi0/1), R4 (all) | 10.1.34.0/24 |
| Area 3 | NSSA | R3 (Gi0/2), R5 (all) | 10.1.35.0/24 |
| External | — | R3 (Gi0/3), R6 (all) | 10.1.36.0/24 |

## Device Roles

| Router | Role |
|--------|------|
| R1 | Area 1 internal — three /24 loopbacks for summarization exercise |
| R2 | ABR Area 0 / Area 1 — originates inter-area summaries |
| R3 | Triple ABR (0/2/3) + ASBR — redistributes R6 external routes |
| R4 | Totally stubby internal — receives only default route from R3 |
| R5 | NSSA ASBR — redistributes Lo2 (192.168.55.0/24) as Type-7 |
| R6 | External AS — no OSPF, provides prefixes for R3 redistribution |

## Open `topology.drawio`

Import into [draw.io](https://app.diagrams.net/) or the VS Code draw.io extension.
The diagram shows area shading, link subnets, summarization annotations, and loopback addresses.
