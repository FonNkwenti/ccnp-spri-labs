# Multicast Routing — Lab Specification

## Exam Reference

- **Exam:** Implementing Cisco Service Provider Advanced Routing Solutions (300-510)
- **Blueprint Bullets:**
  - **2.1** Compare multicast concepts
    - **2.1.a** Multicast domains, distribution trees, and IGMP operations
    - **2.1.b** Any-Source Multicast (ASM) versus Source Specific Multicast (SSM)
    - **2.1.c** Intra-domain versus inter-domain multicast routing
  - **2.2** Describe multicast concepts
    - **2.2.a** Mapping of multicast IP addresses to MAC addresses
    - **2.2.b** Multiprotocol BGP for IPv4 and IPv6
    - **2.2.c** Principles and operations of PIM-SM
    - **2.2.d** Multicast Source Discovery Protocol (MSDP) operations
    - **2.2.e** MLDP/P2MP
    - **2.2.f** IGMP, IGMPv3 and MLD
  - **2.3** Implement PIM-SM operations
    - **2.3.a** Auto-RP, PIMv2 BSR, anycast RP, Phantom RP
    - **2.3.b** BIDIR-PIM operations
    - **2.3.c** SSM operations
    - **2.3.d** MSDP operations
  - **2.4** Troubleshoot multicast routing
    - **2.4.a** Single domain
    - **2.4.b** Multidomain

> This topic depends on `bgp` (for MBGP address-family configuration in lab-04
> and MSDP eBGP peering in lab-03) and `mpls` (for LDP/MLDP P2MP in lab-05).
> The IGP is IS-IS L2 throughout AS 65100.
>
> IOSv 15.9(3)M6 supports all required multicast features: PIM-SM, Auto-RP, BSR,
> anycast RP, Phantom RP, BIDIR-PIM, SSM, IGMP v1/v2/v3, MLD, MSDP, MBGP, and
> MLDP P2MP. No XRv9k is needed for this topic.

## Topology Summary

Four-node IOSv core (AS 65100): R1-R2-R3 triangle with R4 as a stub hanging off R1.
Two Ubuntu 20.04 Linux VMs — SRC1 (source, connected to R2) and RCV1 (receiver,
connected to R4) — provide realistic multicast traffic generation and reception.
An optional fifth router (R5, AS 65200, IOSv) joins at lab-03 for inter-domain MSDP
and MBGP. Total RAM: 4 × 512 MB (IOSv) + 2 × 1024 MB (Linux) ≈ 4 GB core, well
within the 64 GB host limit.

```
                          ┌──────────────┐
                          │    SRC1      │
                          │  ubuntu 20.04│
                          │192.168.2.10  │
                          └──────┬───────┘
                                 │ L6  192.168.2.0/24
                    ┌────────────┴─────────────┐
                    │             R2            │
                    │       lo0: 10.0.0.2/32    │
                    └───────┬───────────────────┘
                    L1  ╱            ╲  L2
             10.10.12.0/30         10.10.23.0/30
                       ╱                 ╲
    ┌──────────────┐  ╱         L3        ╲  ┌──────────────┐
    │      R1      ├────────────────────────┤      R3      │
    │  10.0.0.1    │     10.10.13.0/30      │  10.0.0.3    │
    │  RP/BSR/MSDP │                        │  RP cand.    │
    └──────┬───────┘                        └──────────────┘
           │ L4
     10.10.14.0/30
    ┌──────┴───────┐
    │      R4      │
    │  10.0.0.4    │
    │  last-hop    │
    └──────┬───────┘
           │ L7  192.168.4.0/24
    ┌──────┴───────┐
    │     RCV1     │
    │  ubuntu 20.04│
    │192.168.4.10  │
    └──────────────┘

    R5 (AS 65200, optional from lab-03) ── L5 (10.10.15.0/30) ── R1
```

Link summary: L1 R1↔R2 (10.10.12.0/30), L2 R2↔R3 (10.10.23.0/30),
L3 R1↔R3 (10.10.13.0/30), L4 R1↔R4 (10.10.14.0/30),
L5 R1↔R5 (10.10.15.0/30, optional from lab-03),
L6 R2↔SRC1 (192.168.2.0/24), L7 R4↔RCV1 (192.168.4.0/24)

Key relationships:
- SRC1 (Ubuntu) sources real UDP multicast via `mcjoin`; R2 is its default gateway and last-hop PIM-SM router toward the source
- RCV1 (Ubuntu) joins multicast groups via the OS multicast socket API; R4 is its last-hop PIM-SM router and IGMP querier
- R4 sends IGMP membership reports on behalf of RCV1 (triggered by RCV1's kernel join)
- R1 is the anchor RP connecting to R2, R3, R4, and the optional R5 — using all 4 IOSv interfaces
- R5 (AS 65200): eBGP and MSDP peer of R1 for inter-domain labs only

## Multicast Traffic Reference

### SRC1 — sourcing multicast (Ubuntu 20.04)

```bash
# Install mcjoin (available in Ubuntu universe repo)
sudo apt-get install -y mcjoin

# Send to ASM group 239.1.1.1 (rate: 1 pkt/sec, TTL 16)
sudo mcjoin -s -g 239.1.1.1 -p 5001 -i ens3 -t 1

# Send to SSM group 232.1.1.1 (lab-02)
sudo mcjoin -s -g 232.1.1.1 -p 5001 -i ens3 -t 1

# Alternative: Python one-liner (no install needed)
python3 -c "
import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 16)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
             socket.inet_aton('192.168.2.10'))
while True: s.sendto(b'hello', ('239.1.1.1', 5001)); time.sleep(1)
"
```

### RCV1 — receiving multicast (Ubuntu 20.04)

```bash
# Install mcjoin
sudo apt-get install -y mcjoin

# Join ASM group 239.1.1.1 (triggers IGMP report on R4)
sudo mcjoin -g 239.1.1.1 -i ens3

# Join SSM group 232.1.1.1 with source filter (IGMPv3, lab-02)
sudo mcjoin -g 232.1.1.1 -i ens3 192.168.2.10

# Verify multicast socket state (Linux kernel)
netstat -gn

# Capture incoming multicast frames
sudo tcpdump -i ens3 host 239.1.1.1 -v
```

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|------------|------|------|----------------|---------|
| 00 | lab-00-pim-sm-foundations | PIM-SM Foundations | Foundation | 60m | progressive | 2.1, 2.1.a, 2.1.b, 2.2.a, 2.2.c, 2.2.f, 2.3, 2.4.a | R1, R2, R3, R4, SRC1, RCV1 |
| 01 | lab-01-rp-mechanisms | RP Mechanisms: Auto-RP, BSR, Anycast, Phantom | Foundation | 75m | progressive | 2.3.a, 2.4.a | R1, R2, R3, R4, SRC1, RCV1 |
| 02 | lab-02-ssm-and-bidir-pim | SSM and BIDIR-PIM | Intermediate | 75m | progressive | 2.1.b, 2.2.f, 2.3.b, 2.3.c, 2.4.a | R1, R2, R3, R4, SRC1, RCV1 |
| 03 | lab-03-msdp-inter-domain | MSDP and Inter-Domain Multicast | Intermediate | 90m | progressive | 2.1.c, 2.2.d, 2.3.d, 2.4.b | all |
| 04 | lab-04-mbgp-multicast | Multiprotocol BGP for Multicast | Intermediate | 75m | progressive | 2.1.c, 2.2.b, 2.2.f, 2.4.b | all |
| 05 | lab-05-mldp-p2mp | MLDP and P2MP LSPs | Intermediate | 90m | progressive | 2.2.e, 2.4.a | R1, R2, R3, R4, SRC1, RCV1 |
| 06 | lab-06-capstone-config | Multicast Full Deployment — Capstone I | Advanced | 120m | capstone_i | all | all |
| 07 | lab-07-capstone-troubleshooting | Multicast Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 2.1 | Compare multicast concepts | lab-00 (SPT/RPT, ASM model), lab-02 (ASM vs SSM) |
| 2.1.a | Multicast domains, distribution trees, and IGMP operations | lab-00 ((*,G) and (S,G) trees, DR election, IGMP join from RCV1, RPF) |
| 2.1.b | ASM versus SSM | lab-00 (ASM), lab-02 (SSM 232.x.x.x, BIDIR vs ASM) |
| 2.1.c | Intra-domain versus inter-domain multicast routing | lab-03 (MSDP SA federation), lab-04 (MBGP RPF for inter-domain) |
| 2.2 | Describe multicast concepts | lab-00 through lab-05 |
| 2.2.a | Mapping of multicast IP addresses to MAC addresses | lab-00 (01:00:5e:xx:xx mapping rule, L3 group → L2 MAC, verified via tcpdump on RCV1) |
| 2.2.b | Multiprotocol BGP for IPv4 and IPv6 | lab-04 (address-family ipv4 multicast, separate RIB, RPF preference) |
| 2.2.c | Principles and operations of PIM-SM | lab-00 (DR, RP, register, join/prune, RPT→SPT switchover triggered by real traffic from SRC1) |
| 2.2.d | MSDP operations | lab-03 (SA messages, SA-cache, peer authentication, SA-filter) |
| 2.2.e | MLDP/P2MP | lab-05 (P2MP LSP, MLDP bindings, mLDP FIB, RCV1 receives over MPLS labels) |
| 2.2.f | IGMP, IGMPv3 and MLD | lab-00 (IGMPv2 from RCV1), lab-02 (IGMPv3 SSM join), lab-04 (MLD for IPv6) |
| 2.3 | Implement PIM-SM operations | lab-00 (static RP), lab-01 (RP mechanisms) |
| 2.3.a | Auto-RP, PIMv2 BSR, anycast RP, Phantom RP | lab-01 (all four mechanisms) |
| 2.3.b | BIDIR-PIM operations | lab-02 (DF election, bidir shared tree, no SPT switchover) |
| 2.3.c | SSM operations | lab-02 (SSM range, IGMPv3 include from RCV1, (S,G) join without RP) |
| 2.3.d | MSDP operations | lab-03 (MSDP peering, SA generation, SA filtering, anycast RP sync) |
| 2.4 | Troubleshoot multicast routing | integrated in labs 00-05; comprehensive in lab-07 |
| 2.4.a | Single domain | lab-00 (RPF failure, wrong RP), lab-01 (RP not elected), lab-05 (MLDP not established) |
| 2.4.b | Multidomain | lab-03 (MSDP peer down, SA blocked), lab-04 (MBGP RPF mismatch) |

## Design Decisions

- **All-IOSv routers + Ubuntu Linux VMs for traffic** — IOSv 15.9(3)M6 supports all
  multicast control-plane features. Ubuntu 20.04 VMs (SRC1 on R2, RCV1 on R4) provide
  real multicast socket joins and real UDP multicast streams via `mcjoin`. This makes
  IGMP snooping, IGMP membership report timing, and SPT switchover observable in a
  way that loopback-ping simulation cannot. Total RAM: 4 × 512 MB + 2 × 1024 MB ≈ 4 GB.

- **`mcjoin` as the primary traffic tool** — `mcjoin` is a minimal, purpose-built
  multicast tester available in Ubuntu's universe repo (`apt install mcjoin`). It sends
  or receives one group at a time with configurable rate and TTL. A Python fallback
  (no install needed) is documented in the Multicast Traffic Reference section above
  for environments where apt access is unavailable. Phase 3 workbooks will include
  full `mcjoin` command sequences per lab step.

- **R1 as the anchor RP** — R1 connects to all other routers (R2 via L1, R3 via L3,
  R4 via L4, R5 via L5). Placing the RP at the hub avoids sub-optimal RPT joins
  in early labs and makes Auto-RP/BSR transitions in lab-01 clearly visible.

- **Triangle core (R1-R2-R3) + stub (R4)** — three routers in a triangle create
  multiple equal-cost paths so that RPF tie-breaking and SPT switchover are visible.
  R4 as a stub is the canonical last-hop router; RCV1 on its Gi0/1 segment provides
  a realistic IGMP querier/member relationship without adding another routing peer.

- **Eight labs (matches estimate)** — 2.3.a covers four distinct RP mechanisms
  each requiring its own config; dedicating lab-01 keeps lab-00 focused on fundamentals.
  MLDP is progressive in lab-05: LDP is enabled then immediately used for MLDP P2MP,
  consistent with the "only add, never remove" rule.

- **R5 inter-domain scope** — R5 (AS 65200, IOSv) is deliberately minimal: one
  loopback, one link to R1, eBGP + MSDP. Keeps the inter-domain focus on MSDP SA
  exchange and MBGP RPF semantics without a second full IGP domain.
