# Lab 05 — Topology Reference

## Area Boundaries

| Area | Type | Devices | Interfaces |
|------|------|---------|------------|
| Area 0 | Backbone | R2, R3 | R2 Gi0/1 ↔ R3 Gi0/0 (10.1.23.0/24) |
| Area 1 | Standard | R1, R2 | R1 Gi0/0 ↔ R2 Gi0/0 (10.1.12.0/24); R1 Lo0-3 |
| Area 2 | Totally Stubby | R3, R4 | R3 Gi0/1 ↔ R4 Gi0/0 (10.1.34.0/24); R4 Lo0-1 |
| Area 3 | NSSA | R3, R5 | R3 Gi0/2 ↔ R5 Gi0/0 (10.1.35.0/24); R5 Lo0-1 |
| External | n/a | R3, R6 | R3 Gi0/3 ↔ R6 Gi0/0 (10.1.36.0/24) — no OSPF |

## Device Roles

| Device | OSPF Role | Notes |
|--------|-----------|-------|
| R1 | Area 1 internal router | Lo1-3 provide three /24s for R2 summarization |
| R2 | ABR (Area 0 / Area 1) | Summarizes 172.16.0.0/21 (IPv4), 2001:DB8:1::/48 (IPv6) |
| R3 | Triple ABR + ASBR | Redistributes static (R6 prefix); translates R5 Type-7→Type-5 |
| R4 | Area 2 internal (totally stubby) | Receives only default route from R3 |
| R5 | Area 3 internal + NSSA ASBR | Redistributes Lo2 (192.168.55.0/24) as Type-7 NSSA external |
| R6 | External AS (no OSPF) | Has default static route back into OSPF domain |

## Summarization Points

| ABR/ASBR | Summary | Command |
|----------|---------|---------|
| R2 (ABR) | 172.16.0.0/21 | `area 1 range 172.16.0.0 255.255.248.0` |
| R2 (ABR) | 2001:DB8:1::/48 | `area 1 range 2001:DB8:1::/48` (OSPFv3 AF) |
| R3 (ASBR) | 192.168.0.0/16 | `summary-address 192.168.0.0 255.255.0.0` |
| R3 (ASBR) | 2001:DB8:66::/48 | `summary-prefix 2001:DB8:66::/48` (OSPFv3 AF) |

## Planted Fault Map

| # | Device | Location | Fault |
|---|--------|----------|-------|
| 1 | R3 | Gi0/1 | Dead-interval 80 (mismatch with R4 default 40) |
| 2 | R5 | ip prefix-list NSSA_EXTERNAL_PREFIX | Wrong /25 mask (should be /24) — no Type-7 generated |
| 3 | R2 | router ospf 1 | `area 1 range 172.16.0.0 255.255.254.0` (wrong /23) |
| 4 | R5 | Gi0/0 | Missing `ospfv3 1 ipv6 area 3` |
| 5 | R3 | router ospf 1 | `distribute-list prefix BLOCK_EXT out static` |
