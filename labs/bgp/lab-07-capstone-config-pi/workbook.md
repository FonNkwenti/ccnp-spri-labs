# Lab 07 — BGP Full Protocol Mastery — Capstone I

**Topic:** BGP Scalability and Troubleshooting · **Difficulty:** Advanced · **Time:** 120 minutes
**Blueprint refs:** 1.4, 1.4.a, 1.4.b, 1.5, 1.5.a–1.5.j · **Type:** capstone_i (clean-slate)
**Devices:** R1, R2, R3, R4, R5, R6, R7

---

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)
11. [Appendix: Script Exit Codes](#11-appendix-script-exit-codes)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.4 Describe BGP scalability and performance | 1.5 Troubleshoot BGP — all sub-bullets: route advertisement (1.5.a), route reflectors (1.5.b), confederations (1.5.c), multihoming (1.5.d), TTL security and inter-domain security (1.5.e), maximum prefix (1.5.f), route dampening (1.5.g), dynamic neighbors (1.5.h), communities (1.5.i), FlowSpec (1.5.j)

This capstone challenges you to build a complete production BGP service-provider topology from a bare-IP starting point across three autonomous systems and seven routers. You will configure the internal IGP (OSPF area 0), deploy iBGP route reflection, establish secure eBGP multihoming with traffic engineering, apply inter-domain security controls, enable route dampening and dynamic neighbors, tag routes with communities and extended communities, and activate BGP FlowSpec between two IOS-XE peers.

### OSPF as the BGP IGP Underlay

Every iBGP session relies on the IGP for TCP endpoint reachability. In this topology OSPF area 0 runs on the four core SP routers (R2, R3, R4, R5). All iBGP sessions source from loopback addresses advertised into OSPF. The IGP must fully converge — every loopback reachable — before any BGP neighbor can come up. External routers (R1, R6, R7) do not participate in OSPF; they peer with core routers via directly connected eBGP.

```
OSPF area 0 members: R2 (Lo0: 10.0.0.2), R3 (Lo0: 10.0.0.3),
                      R4 (Lo0: 10.0.0.4), R5 (Lo0: 10.0.0.5)
Links in area 0: L3 (R2↔R4), L4 (R3↔R4), L5 (R4↔R5), L6 (R2↔R3)
```

### iBGP Route Reflectors

A full iBGP mesh requires N×(N−1)/2 sessions — 6 sessions for 4 routers, 45 for 10. Route reflectors (RR) break this quadratic growth by designating one router to reflect routes to its clients. Clients peer only with the RR, not with each other. The RR appends two attributes to every reflected route:

- **ORIGINATOR_ID** — the router-ID of the route's originator (prevents re-advertisement loops)
- **CLUSTER_LIST** — the cluster-IDs the route has traversed (prevents inter-cluster loops)

In this topology, R4 is the sole RR in AS 65100 with clients R2, R3, and R5. There is no legacy full mesh — the capstone starts clean. R4's cluster-ID is set to its loopback (10.0.0.4) explicitly for deterministic loop prevention.

```
          ┌──────────┐
          │ R4 (RR)  │  cluster-id 10.0.0.4
          └──┬───┬───┘
     ┌───────┘   │   └───────┐
     ▼           ▼           ▼
  ┌────┐    ┌────┐      ┌────┐
  │ R2 │    │ R3 │      │ R5 │   ← RR clients
  └────┘    └────┘      └────┘
```

### eBGP Multihoming and Traffic Engineering

Customer A (R1 in AS 65001) is dual-homed to AS 65100 via R2 (primary) and R3 (backup). Three BGP attributes control path selection:

| Attribute | Scope | Applied By | Effect |
|-----------|-------|-----------|--------|
| LOCAL_PREF | AS-wide (iBGP) | R2 inbound from R1 | Set to 200 → all SP routers prefer R2 for Customer A traffic |
| AS-path prepend | Inter-AS (eBGP) | R1 outbound to R3 | Prepend 65001 → makes R3 path appear longer to R3 and its iBGP peers |
| MED (metric) | Inter-AS (eBGP) | R1 outbound | Lower MED to R2 (10) than R3 (50) → influences R2/R3 return-path preference |

**Return-path control:** MED set on R1's route-maps tells the SP PEs which path R1 prefers for inbound traffic. LOCAL_PREF on R2 tells the rest of AS 65100 which exit point to use for outbound traffic toward R1. Together they create a symmetric primary/backup flow.

### Inter-Domain Security

Four security mechanisms protect eBGP sessions:

1. **GTSM (TTL-security):** `neighbor X ttl-security hops 1` — the sender sets TTL=255; the receiver verifies TTL ≥ 254, thwarting multi-hop spoofing attacks. Applies to all directly connected eBGP sessions.
2. **MD5 authentication:** `neighbor X password <key>` — TCP-MD5 signature on every BGP segment. Both sides must match or the session hangs in Connect/Active with no NOTIFICATION. Applied on R5↔R6.
3. **Maximum-prefix with restart:** `neighbor X maximum-prefix 100 restart 5` — tears down the session if the peer advertises >100 prefixes, then auto-reconnects after 5 minutes. Applied on R2↔R1.
4. **Maximum-prefix warning-only:** `neighbor X maximum-prefix 100 75 warning-only` — logs a syslog warning at 75% utilization but keeps the session up. Applied on R5↔R6.

### Route Dampening and Dynamic Neighbors

**Route dampening** suppresses flapping eBGP prefixes by assigning a penalty (1000 per flap) that decays exponentially. When the penalty exceeds a suppress threshold, the prefix is withdrawn; when it drops below a reuse threshold, it is re-advertised. Configured on R5 for prefixes learned from R6 and R7: `bgp dampening 15 750 2000 60` (half-life 15 min, reuse 750, suppress 2000, max-suppress 60 min).

**Dynamic neighbors** allow a router to accept BGP connections from any peer within a configured IP range without pre-defining each neighbor. On R2: `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` — any device in that subnet connecting to R2's BGP port (TCP/179) with AS 65001 is accepted. The dynamic peer-group inherits all policies (route-map, communities, SoO).

### BGP Communities and Extended Communities

Communities are 32-bit tags that influence routing policy without touching prefix attributes directly:

| Community | Format | Effect |
|-----------|--------|--------|
| `no-export` | Well-known | Do not advertise outside the local AS (or confederation) |
| `no-advertise` | Well-known | Do not advertise to any BGP peer |
| `65100:100` | Custom (ASN:value) | Customer-origin tag applied by R2 inbound from R1 |
| SoO 65001:1 | Extended community | Site-of-Origin — loop prevention for dual-homed CEs |

**Community propagation requires `send-community`** on the BGP neighbor. Without it, all community attributes are stripped in both directions. Extended communities (SoO) additionally require `send-community both` (standard + extended). This is one of the most common troubleshooting scenarios in production BGP.

### BGP FlowSpec (SAFI 133)

BGP FlowSpec advertises traffic-filtering rules as NLRI (Network Layer Reachability Information) in address-family `ipv4 flowspec`. A FlowSpec rule can match on destination prefix, protocol, port, and packet length, then apply actions like drop, rate-limit, or redirect.

In this topology, R7 (AS 65003, CSR1000v) establishes the FlowSpec AFI to R5 (AS 65100, CSR1000v). R5 enables `flowspec local-install interface-all` to install received FlowSpec rules into the hardware forwarding path. Both R5 and R7 run CSR1000v because IOSv does not implement FlowSpec NLRI.

`★ Insight ─────────────────────────────────────`
- **RR breaks the iBGP full-mesh requirement.** Without R4 as RR, R2, R3, and R5 would each need sessions to every other iBGP peer — R5 would never learn R1's prefix unless it peered directly with R2 and R3. The RR reflects the route while preserving the originator's next-hop (unless `next-hop-self` overrides).
- **LOCAL_PREF vs MED direction.** LOCAL_PREF is set inbound (influences outbound traffic from the local AS). MED is set outbound (influences inbound traffic). Setting LOCAL_PREF on R2 inbound from R1 tells "AS 65100, send Customer A traffic via R2." Setting MED on R1 outbound tells "AS 65100, send return traffic via the lower-MED path."
- **`send-community both` is required for extended communities.** If you set `send-community` (without `both`), standard communities propagate but extended communities (SoO) are silently stripped. This fails silently — the session stays up, routes appear correct, but SoO loop prevention is missing.
- **CSR1000v is required for FlowSpec.** IOSv (vios-adventerprisek9) does not support SAFI 133. If you attempt `address-family ipv4 flowspec` on IOSv it rejects the command. R5 and R7 must be CSR1000v images.
`─────────────────────────────────────────────────`

### Skills this lab develops:

| Skill | Description |
|-------|-------------|
| OSPF underlay for iBGP | Deploy OSPF area 0 on 4 routers with loopback advertisements |
| Route reflector deployment | Configure RR with cluster-ID, verify ORIGINATOR_ID and CLUSTER_LIST |
| eBGP multihoming | Dual-home a customer with LOCAL_PREF, AS-path prepend, and MED |
| Inter-domain security | Apply GTSM, MD5 auth, max-prefix with restart and warning-only |
| Route dampening | Tune suppress/reuse thresholds and observe penalty accumulation |
| Dynamic BGP neighbors | Configure listen range with peer-group policy inheritance |
| BGP communities | Tag routes with custom communities, no-export, SoO |
| BGP FlowSpec | Activate SAFI 133 between two CSR1000v peers |

---

## 2. Topology & Scenario

**Scenario:** You are migrating a regional SP from a flat BGP design to a production-grade architecture. The physical cabling is complete — seven routers across three autonomous systems with IP addresses pre-assigned — but no protocols or BGP are running. Build the full stack: OSPF area 0 as the IGP underlay, R4 as a Route Reflector serving R2/R3/R5, Customer A dual-homed via R2 (primary, LOCAL_PREF 200) and R3 (backup, AS-path prepend), inter-domain security on every eBGP session, route dampening on the west PE, dynamic neighbor listen range on the east PE, communities tagging for customer prefix tracking, and BGP FlowSpec between R5 and R7.

```
  AS 65001                  AS 65100 (SP core, OSPF area 0)              AS 65002
                           ╔══════════════════════════════════╗
   ┌────┐    ┌────┐        ║  ┌────┐          ┌────┐  ┌────┐  ║    ┌────┐
   │ R1 ├─L1─┤ R2 │════════╬══┤ R4 │══════════┤ R5 │══╬══L7══┤ R6 │
   └────┘    └────┘        ║  └────┘          └────┘  ║    └────┘
       │    (PE East-1)    ║  (P / RR)       (PE West)║  (AS 65002)
       │                   ║  IOSv            CSR1000v ║
       │    ┌────┐         ║                          ║
       └─L2─┤ R3 │═════════╝                          ║
            └────┘          L8 ┌────┐                  ║
           (PE East-2)    ────┤ R7 │──────────────────  (AS 65003)
                              └────┘
                             CSR1000v
                             (FlowSpec peer)
```

| Link | Endpoints | Subnet | Purpose |
|------|-----------|--------|---------|
| L1 | R1 Gi0/0 ↔ R2 Gi0/0 | 10.1.12.0/24 | eBGP R1↔R2 (primary) |
| L2 | R1 Gi0/1 ↔ R3 Gi0/0 | 10.1.13.0/24 | eBGP R1↔R3 (backup) |
| L3 | R2 Gi0/1 ↔ R4 Gi0/0 | 10.1.24.0/24 | OSPF + iBGP R2↔R4 |
| L4 | R3 Gi0/1 ↔ R4 Gi0/1 | 10.1.34.0/24 | OSPF + iBGP R3↔R4 |
| L5 | R4 Gi0/2 ↔ R5 Gi2 | 10.1.45.0/24 | OSPF + iBGP R4↔R5 |
| L6 | R2 Gi0/2 ↔ R3 Gi0/2 | 10.1.23.0/24 | OSPF IGP only |
| L7 | R5 Gi3 ↔ R6 Gi0/0 | 10.1.56.0/24 | eBGP R5↔R6 |
| L8 | R5 Gi4 ↔ R7 Gi1 | 10.1.57.0/24 | eBGP R5↔R7 (FlowSpec) |
| — | R1 Gi0/2 ↔ R2 Gi0/3 | 10.99.0.0/30 | Dynamic-neighbor range |

**Key relationships:**
- R4 is the sole Route Reflector for AS 65100. R2, R3, R5 are RR clients only — no full mesh.
- R1 (Customer A) is dual-homed: R2 is primary (LOCAL_PREF 200), R3 is backup (AS-path prepend).
- R5 and R7 are CSR1000v for BGP FlowSpec support. R1–R4 and R6 are IOSv.
- The dynamic-neighbor link (10.99.0.0/30) between R1 Gi0/2 and R2 Gi0/3 lets R2 accept BGP connections from any IP in the 10.99.0.0/24 range.

---

## 3. Hardware & Environment Specifications

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) — dual-homed | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) — RR client, primary eBGP to R1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) — RR client, backup eBGP to R1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) — RR client, FlowSpec, CSR1000v | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R7 | External peer (AS 65003) — FlowSpec originator, CSR1000v | CSR1000v | csr1000v-universalk9.17.03.05 |

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-ID |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A prefix |
| R2 | Loopback0 | 10.0.0.2/32 | OSPF + iBGP source |
| R3 | Loopback0 | 10.0.0.3/32 | OSPF + iBGP source |
| R4 | Loopback0 | 10.0.0.4/32 | OSPF + iBGP source + RR cluster-ID |
| R5 | Loopback0 | 10.0.0.5/32 | OSPF + iBGP source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-ID |
| R6 | Loopback1 | 172.16.6.1/24 | External SP prefix |
| R7 | Loopback0 | 10.0.0.7/32 | BGP router-ID |
| R7 | Loopback1 | 172.16.7.1/24 | External FlowSpec peer prefix |

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP network | Customer A aggregate |
| R6 | 172.16.6.0/24 | eBGP network | External SP peer aggregate |
| R7 | 172.16.7.0/24 | eBGP network | FlowSpec peer aggregate |

| Link | Endpoints | Subnet |
|------|-----------|--------|
| L1 | R1 Gi0/0 ↔ R2 Gi0/0 | 10.1.12.0/24 |
| L2 | R1 Gi0/1 ↔ R3 Gi0/0 | 10.1.13.0/24 |
| L3 | R2 Gi0/1 ↔ R4 Gi0/0 | 10.1.24.0/24 |
| L4 | R3 Gi0/1 ↔ R4 Gi0/1 | 10.1.34.0/24 |
| L5 | R4 Gi0/2 ↔ R5 Gi2 | 10.1.45.0/24 |
| L6 | R2 Gi0/2 ↔ R3 Gi0/2 | 10.1.23.0/24 |
| L7 | R5 Gi3 ↔ R6 Gi0/0 | 10.1.56.0/24 |
| L8 | R5 Gi4 ↔ R7 Gi1 | 10.1.57.0/24 |

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R6 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R7 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames (R1–R7)
- `no ip domain-lookup` on all devices
- Loopback0 on all seven routers with `/32` mask
- Loopback1 on R1 (172.16.1.1/24), R6 (172.16.6.1/24), R7 (172.16.7.1/24)
- All interface IP addressing with descriptions (L1–L8 plus dynamic-neighbor link)
- All interfaces in `no shutdown` state

**IS NOT pre-loaded** (student configures this):
- OSPF process on R2, R3, R4, R5
- BGP process on all seven routers
- Route reflector configuration on R4
- iBGP sessions and RR client relationships
- eBGP sessions with all security controls
- Multihoming traffic engineering (LOCAL_PREF, AS-path prepend, MED)
- Route dampening on R5
- Dynamic neighbor listen range on R2
- Community tagging, no-export, SoO
- BGP FlowSpec address-family on R5 and R7

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete BGP SP topology from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Task 1 — Deploy OSPF Area 0 as the Core IGP

- Configure OSPF process 1 on R2, R3, R4, and R5 with router-ID from Loopback0.
- Place all SP-core loopbacks and internal links (L3, L4, L5, L6) in area 0.
- Do NOT enable OSPF on CE-facing interfaces (L1, L2 on R2/R3) or external interfaces (L7, L8 on R5).
- Verify every SP router sees all four loopbacks plus all internal subnets.

**Verification:** `show ip ospf neighbor` shows full adjacency on every OSPF link. `show ip route ospf` on R5 shows R2, R3, R4 loopbacks. `ping 10.0.0.4 source 10.0.0.5` from R5 succeeds.

---

### Task 2 — Configure iBGP Route Reflection

- Create BGP process AS 65100 on R2, R3, R4, and R5.
- On R4, set `bgp cluster-id 10.0.0.4`.
- Establish iBGP sessions: R2↔R4, R3↔R4, R5↔R4 — all sourced from Loopback0.
- On R4, configure R2, R3, and R5 as route-reflector-clients under address-family ipv4.
- On each client (R2, R3, R5), configure `next-hop-self` toward R4 so reflected routes have reachable next-hops.
- Do NOT configure direct iBGP sessions between R2, R3, and R5 — the RR must be the only iBGP control-plane path.

**Verification:** `show ip bgp summary` on R4 shows three Established iBGP sessions. `show ip bgp` on R5 shows at least the locally originated routes. `show ip bgp neighbors 10.0.0.4` on R2 confirms RR-client status.

---

### Task 3 — Configure eBGP Multihoming with Traffic Engineering

- Create BGP process AS 65001 on R1. Advertise 172.16.1.0/24 via a network statement.
- Establish eBGP R1↔R2 (primary, L1) and R1↔R3 (backup, L2).
- On R1, create route-maps to set MED: 10 toward R2, 50 toward R3. Also prepend AS 65001 toward R3 for longer AS-path.
- On R2, create a route-map inbound from R1 that sets LOCAL_PREF 200 for prefix 172.16.1.0/24 and tags it with community 65100:100. Apply SoO 65001:1.
- On R3, create a route-map inbound from R1 that applies SoO 65001:1 (no LOCAL_PREF change, so it stays at default 100).
- On both R2 and R3, configure `next-hop-self` toward R4 so R5 receives routes with loopback next-hops.
- Verify R5 sees 172.16.1.0/24 with LOCAL_PREF 200 from R2 (best) and LOCAL_PREF 100 from R3 (backup).

**Verification:** `show ip bgp 172.16.1.0/24` on R5 shows best path via R2 (LOCAL_PREF 200). `show ip bgp 172.16.1.0/24` on R3 shows two paths — the eBGP path from R1 and the reflected iBGP path from R4 via R2. The path via R2 has shorter AS-path (no prepend).

---

### Task 4 — Apply Inter-Domain Security

- On every eBGP session (R1↔R2, R1↔R3, R5↔R6, R5↔R7), configure `ttl-security hops 1`.
- On R5↔R6, add MD5 authentication with password `CISCO_SP` (both sides must match).
- On R2↔R1, configure `maximum-prefix 100 restart 5` so the session tears down and auto-reconnects if R1 floods prefixes.
- On R5↔R6, configure `maximum-prefix 100 75 warning-only` so a syslog fires at 75 prefix threshold but the session stays up.
- Ensure `no ip domain-lookup` is set to prevent DNS resolution delays during TCP session setup.

**Verification:** `show ip bgp neighbors <peer>` on all eBGP sessions shows `TTL Security hops 1` and the correct maximum-prefix settings. `show ip bgp neighbors 10.1.56.6 | include password` confirms MD5 is configured.

---

### Task 5 — Configure Route Dampening and Dynamic Neighbors

- On R5, enable `bgp dampening 15 750 2000 60` to suppress flapping eBGP prefixes.
- On R2, configure `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` with `bgp listen limit 10`.
- Create the DYN_CUST peer-group on R2 with `remote-as 65001` and the same route-map policy as the static R1 session.
- On R1, configure an additional eBGP neighbor to 10.99.0.2 (R2's dynamic-range interface).
- Activate the dynamic neighbor session and verify R2 accepts it.

**Verification:** `show ip bgp dampening parameters` on R5 shows the configured values. `show ip bgp peer-group DYN_CUST` on R2 lists the dynamic peer-group. `show ip bgp summary` on R2 shows the dynamic neighbor in Established state.

---

### Task 6 — Apply BGP Communities

- On R2, ensure `send-community both` is configured toward R4 so the custom community 65100:100 and SoO propagate.
- On R5, create a route-map that applies `no-export` to 172.16.6.0/24 inbound from R6.
- On R6, create a route-map that sets `no-export` on 172.16.6.0/24 outbound to R5.
- On R7, create a route-map that sets `no-advertise` on 172.16.7.0/24 outbound to R5.
- Verify community propagation: R5→R6 prefix should not propagate beyond AS 65100.

**Verification:** `show ip bgp 172.16.6.0/24` on R5 shows community `no-export`. `show ip bgp 172.16.7.0/24` on R5 shows community `no-advertise`. `show ip bgp 172.16.1.0/24` on R4 shows community `65100:100` and extended community SoO `65001:1`.

---

### Task 7 — Configure BGP FlowSpec

- On R5 and R7 (both CSR1000v), activate `address-family ipv4 flowspec` under the BGP process.
- Configure the FlowSpec neighbor activation for R5↔R7 with `send-community both`.
- On R5, add `flowspec` global configuration with `local-install interface-all` to install received FlowSpec rules.
- Enable `ip bgp-community new-format` on R5 and R2 for AA:NN community display.

**Verification:** `show bgp ipv4 flowspec summary` on R5 shows the FlowSpec peering to R7 in Established state. `show flowspec ipv4 detail` shows the local-install policy.

---

### Task 8 — End-to-End Acceptance Test

- From R1, verify reachability to external peers: `ping 172.16.6.1 source 172.16.1.1` and `ping 172.16.7.1 source 172.16.1.1` must succeed.
- On R5, confirm 172.16.1.0/24 is reachable with LOCAL_PREF 200 via R2: `show ip bgp 172.16.1.0/24`.
- On R4, confirm all three RR-client sessions are Established with prefixes received.
- On R2, verify the dynamic neighbor from R1's 10.99.0.1 is active: `show ip bgp summary`.
- On R5, verify FlowSpec peering to R7 is Established: `show bgp ipv4 flowspec summary`.
- On R5, verify route dampening is active: `show ip bgp dampening parameters`.

**Verification:** All checks pass without any stale sessions or partial states.

---

## 6. Verification & Analysis

### Task 1 — OSPF Underlay

```bash
R4# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/BDR        00:00:34    10.1.24.2       GigabitEthernet0/0  ! ← R2 on L3
10.0.0.3          1   FULL/BDR        00:00:34    10.1.34.3       GigabitEthernet0/1  ! ← R3 on L4
10.0.0.5          1   FULL/BDR        00:00:34    10.1.45.5       GigabitEthernet0/2  ! ← R5 on L5

R5# show ip route ospf
      10.0.0.2/32 [110/31] via 10.1.45.4, GigabitEthernet2   ! ← R2 loopback via R4
      10.0.0.3/32 [110/31] via 10.1.45.4, GigabitEthernet2   ! ← R3 loopback via R4
      10.0.0.4/32 [110/21] via 10.1.45.4, GigabitEthernet2   ! ← R4 loopback
      10.1.23.0/24 [110/30] via 10.1.45.4, GigabitEthernet2  ! ← L6 via R4
      10.1.24.0/24 [110/20] via 10.1.45.4, GigabitEthernet2  ! ← L3 via R4
      10.1.34.0/24 [110/20] via 10.1.45.4, GigabitEthernet2  ! ← L4 via R4
```

### Task 2 — iBGP Route Reflection

```bash
R4# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.2        4 65100      15      15        5    0    0 00:10:00        2  ! ← R2 (RR client)
10.0.0.3        4 65100      12      12        5    0    0 00:09:00        1  ! ← R3 (RR client)
10.0.0.5        4 65100      10      10        5    0    0 00:08:00        0  ! ← R5 (RR client)

R5# show ip bgp neighbors 10.0.0.4 | include route-reflector
  Route-Reflector Client                            ! ← R5 is an RR client of R4
```

### Task 3 — Multihoming

```bash
R5# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 5
Paths: (2 available, best #1)
  Local
    10.0.0.2 from 10.0.0.4 (10.0.0.2)              ! ← via R2 (reflected by R4)
      Origin IGP, metric 10, localpref 200, valid, internal, best  ! ← LOCAL_PREF 200
      Community: 65100:100                          ! ← custom community tag
      Extended Community: SoO:65001:1               ! ← SoO loop prevention
  Local
    10.0.0.3 from 10.0.0.4 (10.0.0.3)              ! ← via R3 (backup)
      Origin IGP, metric 50, localpref 100, valid, internal  ! ← LOCAL_PREF 100
      Extended Community: SoO:65001:1
```

### Task 4 — Inter-Domain Security

```bash
R2# show ip bgp neighbors 10.1.12.1 | include TTL|maximum
  TTL Security hops 1                                 ! ← GTSM active
  Maximum prefixes allowed 100, threshold 75%         ! ← max-prefix with restart 5

R5# show ip bgp neighbors 10.1.56.6 | include TTL|maximum|password
  TTL Security hops 1                                 ! ← GTSM active
  Maximum prefixes allowed 100, threshold 75%         ! ← warning-only mode
  MD5 password is configured                          ! ← MD5 auth active
```

### Task 5 — Dampening and Dynamic Neighbors

```bash
R5# show ip bgp dampening parameters
dampening 15 750 2000 60                              ! ← half-life 15, reuse 750, suppress 2000, max 60

R2# show ip bgp peer-group DYN_CUST
BGP peer-group DYN_CUST, remote AS 65001
  Description: Dynamic-Customer-AS65001

R2# show ip bgp summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
...
*10.99.0.1      4 65001       8       8        5    0    0 00:05:00        1  ! ← dynamic neighbor (* prefix)
* Dynamically created based on a listen range command
```

### Task 6 — Communities

```bash
R5# show ip bgp 172.16.6.0/24
BGP routing table entry for 172.16.6.0/24
  Community: no-export                                ! ← will not leave AS 65100

R5# show ip bgp 172.16.7.0/24
BGP routing table entry for 172.16.7.0/24
  Community: no-advertise                             ! ← will not be advertised to any peer
```

### Task 7 — FlowSpec

```bash
R5# show bgp ipv4 flowspec summary
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.57.7       4 65003       5       5        2    0    0 00:03:00        0  ! ← FlowSpec peering UP

R5# show flowspec ipv4 detail
AFI: IPv4
  Flow:  Install
```

### Task 8 — End-to-End

```bash
R1# ping 172.16.6.1 source 172.16.1.1
Sending 5, 100-byte ICMP Echos to 172.16.6.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.1.1
!!!!!                                                ! ← R1 → R6 succeeds
Success rate is 100 percent (5/5)

R1# ping 172.16.7.1 source 172.16.1.1
Sending 5, 100-byte ICMP Echos to 172.16.7.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.7.1
!!!!!                                                ! ← R1 → R7 succeeds
Success rate is 100 percent (5/5)
```

---

## 7. Verification Cheatsheet

### OSPF Underlay Configuration

```
router ospf 1
 router-id 10.0.0.X
 network 10.0.0.X 0.0.0.0 area 0
 network 10.1.XX.0 0.0.0.255 area 0
```

| Command | Purpose |
|---------|---------|
| `router ospf 1` | OSPF process 1 |
| `network <subnet> <wildcard> area 0` | Advertise subnet into area 0 |
| `router-id <loopback>` | Stable OSPF router-ID |

### iBGP Route Reflector

```
router bgp 65100
 bgp cluster-id 10.0.0.4
 neighbor 10.0.0.X remote-as 65100
 neighbor 10.0.0.X update-source Loopback0
 address-family ipv4
  neighbor 10.0.0.X activate
  neighbor 10.0.0.X route-reflector-client
  neighbor 10.0.0.X next-hop-self
  neighbor 10.0.0.X send-community both
```

| Command | Purpose |
|---------|---------|
| `bgp cluster-id <ip>` | Set RR cluster-ID (loop prevention) |
| `neighbor X route-reflector-client` | Mark neighbor as RR client |
| `neighbor X next-hop-self` | Rewrite BGP next-hop to local loopback |

### eBGP Multihoming

```
route-map FROM-CUST-A-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set local-preference 200
 set community 65100:100 additive
 set extcommunity soo 65001:1

route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set metric 50
 set as-path prepend 65001
```

| Command | Purpose |
|---------|---------|
| `set local-preference <N>` | Higher value preferred for outbound traffic |
| `set as-path prepend <ASN>` | Lengthen AS-path to make path less preferred |
| `set metric <N>` | MED — lower value preferred for inbound traffic |
| `set extcommunity soo <ASN>:<val>` | Site-of-Origin for loop prevention |

### Inter-Domain Security

```
neighbor X ttl-security hops 1
neighbor X password CISCO_SP
neighbor X maximum-prefix 100 restart 5
neighbor X maximum-prefix 100 75 warning-only
```

| Command | Purpose |
|---------|---------|
| `ttl-security hops 1` | GTSM — only accept packets with TTL ≥ 254 |
| `password <key>` | TCP-MD5 authentication |
| `maximum-prefix N restart M` | Tear down session at N prefixes, reconnect after M minutes |
| `maximum-prefix N 75 warning-only` | Log warning at 75% of N, never tear down |

### Route Dampening and Dynamic Neighbors

```
bgp dampening 15 750 2000 60
bgp listen range 10.99.0.0/24 peer-group DYN_CUST
bgp listen limit 10
```

| Command | Purpose |
|---------|---------|
| `bgp dampening <half> <reuse> <suppress> <max>` | Suppress flapping prefixes |
| `bgp listen range <subnet> peer-group <name>` | Accept BGP connections from IP range |
| `bgp listen limit <N>` | Max dynamic peers from the listen range |

### FlowSpec (CSR1000v only)

```
address-family ipv4 flowspec
 neighbor 10.1.57.7 activate
 neighbor 10.1.57.7 send-community both

flowspec
 address-family ipv4
  local-install interface-all
```

| Command | Purpose |
|---------|---------|
| `address-family ipv4 flowspec` | Activate FlowSpec SAFI 133 |
| `local-install interface-all` | Install FlowSpec rules on all interfaces |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | FULL adjacencies on all OSPF links |
| `show ip route ospf` | All loopbacks and core subnets reachable |
| `show ip bgp summary` | All sessions Established; RR-client indicators |
| `show ip bgp 172.16.1.0/24` | Dual paths, LOCAL_PREF 200 best, SoO present |
| `show ip bgp neighbors X | include TTL\|maximum\|password` | Security controls active |
| `show ip bgp dampening parameters` | Dampening values configured |
| `show ip bgp peer-group DYN_CUST` | Dynamic peer-group with correct policies |
| `show ip bgp 172.16.6.0/24` | Community no-export present |
| `show bgp ipv4 flowspec summary` | FlowSpec session Established |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /24 | 0.0.0.255 | Interface subnet matching |
| /30 | 0.0.0.3 | Point-to-point links |
| /32 | 0.0.0.0 | Host route / loopback |

### Common BGP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| iBGP session stuck in Connect | IGP not converged — loopback not reachable |
| Route not reflected to R5 | Missing `route-reflector-client` on R4 |
| BGP route next-hop unreachable | Missing `next-hop-self` on PE toward RR |
| eBGP session stuck in Active | `ttl-security hops` mismatch or missing |
| BGP session flaps immediately after Established | MD5 password mismatch |
| Community tags missing on reflected routes | Missing `send-community both` on RR |
| FlowSpec session down | SAFI not negotiated — peer not CSR1000v |
| Dynamic neighbor never appears | `bgp listen range` subnet does not match peer IP |
| Dual-homed paths are active-active | Missing LOCAL_PREF or AS-path prepend |
| Dampened prefix stuck suppressed | Penalty above reuse threshold — `clear ip bgp dampening` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 — OSPF Area 0

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 router-id 10.0.0.2
 network 10.0.0.2 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.23.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 router-id 10.0.0.4
 network 10.0.0.4 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 10.1.45.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf neighbor
show ip route ospf
ping 10.0.0.4 source 10.0.0.5
```
</details>

### Task 2 — Route Reflector

<details>
<summary>Click to view R4 (RR) Configuration</summary>

```bash
! R4
router bgp 65100
 bgp router-id 10.0.0.4
 bgp log-neighbor-changes
 bgp cluster-id 10.0.0.4
 neighbor 10.0.0.2 remote-as 65100
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.0.0.3 remote-as 65100
 neighbor 10.0.0.3 update-source Loopback0
 neighbor 10.0.0.5 remote-as 65100
 neighbor 10.0.0.5 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 route-reflector-client
  neighbor 10.0.0.2 send-community both
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 route-reflector-client
  neighbor 10.0.0.3 send-community both
  neighbor 10.0.0.5 activate
  neighbor 10.0.0.5 route-reflector-client
  neighbor 10.0.0.5 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 (Client) Configuration</summary>

```bash
! R2
router bgp 65100
 bgp router-id 10.0.0.2
 neighbor 10.0.0.4 remote-as 65100
 neighbor 10.0.0.4 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.0.0.4 activate
  neighbor 10.0.0.4 next-hop-self
  neighbor 10.0.0.4 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp neighbors 10.0.0.4 | include route-reflector
```
</details>

### Task 3 — eBGP Multihoming

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24
!
route-map TO-R2-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set metric 10
!
route-map TO-R2-PRIMARY permit 20
!
route-map TO-R3-BACKUP permit 10
 match ip address prefix-list CUST-A
 set metric 50
 set as-path prepend 65001
!
route-map TO-R3-BACKUP permit 20
!
router bgp 65001
 bgp router-id 10.0.0.1
 neighbor 10.1.12.2 remote-as 65100
 neighbor 10.1.13.3 remote-as 65100
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  neighbor 10.1.12.2 activate
  neighbor 10.1.12.2 route-map TO-R2-PRIMARY out
  neighbor 10.1.13.3 activate
  neighbor 10.1.13.3 route-map TO-R3-BACKUP out
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 (Primary PE) Configuration</summary>

```bash
! R2
ip prefix-list CUST-A seq 5 permit 172.16.1.0/24
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1
!
route-map FROM-CUST-A-PRIMARY permit 10
 match ip address prefix-list CUST-A
 set local-preference 200
 set community 65100:100 additive
 set extcommunity soo 65001:1
!
route-map FROM-CUST-A-PRIMARY permit 20
!
router bgp 65100
 neighbor 10.1.12.1 remote-as 65001
 !
 address-family ipv4
  neighbor 10.1.12.1 activate
  neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 172.16.1.0/24               ! on R5 — LOCAL_PREF 200 via R2
show ip bgp 172.16.1.0/24               ! on R3 — two paths visible
```

</details>

### Tasks 4–7 — Remaining Configuration

Full solution configs are available in `solutions/`:
- `R1.cfg` — eBGP multihoming, MED, AS-path prepend, TTL-security, dynamic neighbor
- `R2.cfg` — LOCAL_PREF, community 65100:100, SoO, max-prefix restart, dynamic listen range
- `R3.cfg` — SoO, TTL-security, next-hop-self
- `R4.cfg` — Route Reflector with cluster-ID, three RR clients, send-community both
- `R5.cfg` — Dampening, no-export on R6 prefix, MD5 auth, max-prefix warning, FlowSpec
- `R6.cfg` — no-export, MD5, TTL-security
- `R7.cfg` — no-advertise, FlowSpec AFI

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — R5 Never Learns Customer A's Prefix

R1 and R2 have an Established eBGP session, R2 sees 172.16.1.0/24 in its BGP table, and iBGP between R2 and R4 is Established. However, R5's BGP table shows no route to 172.16.1.0/24, and pings from R5 to 172.16.1.1 fail.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R5 shows the prefix with LOCAL_PREF 200 from R2 and LOCAL_PREF 100 from R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 172.16.1.0/24` on R5 — route is missing.
2. `show ip bgp 172.16.1.0/24` on R4 — route is present. R4 sees it from R2.
3. `show ip bgp neighbors 10.0.0.5` on R4 — check the advertised-routes count and whether 172.16.1.0/24 appears in the advertised list.
4. `show ip bgp neighbors 10.0.0.5 | include route-reflector` on R4 — if this line is missing, R5 is not an RR client and R4 will not reflect routes to it (iBGP split-horizon: routes learned from one iBGP peer are not advertised to another iBGP peer unless the router is an RR).
</details>

<details>
<summary>Click to view Fix</summary>

On R4, add the route-reflector-client configuration for R5:

```bash
R4# configure terminal
R4(config)# router bgp 65100
R4(config-router)# address-family ipv4
R4(config-router-af)# neighbor 10.0.0.5 route-reflector-client
R4(config-router-af)# end
R4# clear ip bgp 10.0.0.5 soft out
```

Verify R5 now receives the reflected route: `show ip bgp 172.16.1.0/24` shows the prefix.
</details>

---

### Ticket 2 — R1's Backup Path Through R3 Is Preferred Over Primary

Traffic from AS 65100 to Customer A is routing through R3 instead of R2. The primary path via R2 should be preferred, but `show ip bgp 172.16.1.0/24` on R5 shows the best path through R3. All sessions are Established and routes appear present.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R5 shows best path via R2 with LOCAL_PREF 200.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 172.16.1.0/24` on R5 — note LOCAL_PREF values. If both paths show LOCAL_PREF 100, no LOCAL_PREF preference is applied.
2. `show ip bgp 172.16.1.0/24` on R4 — same LOCAL_PREF values, confirming the issue is at the ingress PE (R2).
3. `show route-map FROM-CUST-A-PRIMARY` on R2 — check if the route-map exists and contains `set local-preference 200`.
4. `show running-config | section router bgp` on R2 — check if the route-map is applied inbound on neighbor 10.1.12.1. If the route-map is defined but not attached, LOCAL_PREF is not set.
</details>

<details>
<summary>Click to view Fix</summary>

On R2, apply the route-map inbound on the eBGP neighbor:

```bash
R2# configure terminal
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor 10.1.12.1 route-map FROM-CUST-A-PRIMARY in
R2(config-router-af)# end
R2# clear ip bgp 10.1.12.1 soft in
```

Wait ~5 seconds. Verify: `show ip bgp 172.16.1.0/24` now shows LOCAL_PREF 200 via R2.
</details>

---

### Ticket 3 — Community Tags Missing on Reflected Routes

The network operations team reports that community 65100:100 and extended community SoO:65001:1 are visible on R2's local BGP table for 172.16.1.0/24 but are absent on R4 and R5. R2's route-map sets the communities correctly, and all iBGP sessions are Established.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R4 and R5 shows Community: 65100:100 and Extended Community: SoO:65001:1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip bgp 172.16.1.0/24` on R2 — communities are present locally.
2. `show ip bgp 172.16.1.0/24` on R4 — communities are missing. This means they were stripped during iBGP advertisement.
3. `show ip bgp neighbors 10.0.0.4` on R2 — check if `send-community` is configured. Look for "Community attribute sent to this neighbor."
4. The root cause: R2 is missing `send-community both` toward R4. Without it, standard and extended communities are stripped silently — the session stays up, routes are advertised, but community tags are absent.
</details>

<details>
<summary>Click to view Fix</summary>

On R2, add `send-community both` toward R4:

```bash
R2# configure terminal
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor 10.0.0.4 send-community both
R2(config-router-af)# end
R2# clear ip bgp 10.0.0.4 soft out
```

Verify: `show ip bgp 172.16.1.0/24` on R4 now shows both communities.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPF area 0 FULL adjacencies on all core links (L3, L4, L5, L6)
- [ ] All SP loopbacks reachable via OSPF (`show ip route ospf`)
- [ ] iBGP sessions R2↔R4, R3↔R4, R5↔R4 all Established
- [ ] R4 correctly reflecting routes to all three RR clients
- [ ] eBGP R1↔R2 (primary) and R1↔R3 (backup) Established
- [ ] R1's 172.16.1.0/24 visible with LOCAL_PREF 200 via R2 (best), 100 via R3
- [ ] MED correctly set: 10 toward R2, 50 toward R3
- [ ] AS-path prepended on R1→R3 path (AS-path includes 65001 65001)
- [ ] TTL-security hops 1 on all eBGP sessions
- [ ] MD5 authentication on R5↔R6 (both sides match)
- [ ] Maximum-prefix 100 restart 5 on R2↔R1
- [ ] Maximum-prefix 100 75 warning-only on R5↔R6
- [ ] Route dampening active on R5 with correct parameters
- [ ] Dynamic neighbor listen range on R2 accepts R1's 10.99.0.1
- [ ] Community 65100:100 and SoO 65001:1 on 172.16.1.0/24 propagated to R5
- [ ] no-export community on 172.16.6.0/24 at R5
- [ ] no-advertise community on 172.16.7.0/24 at R5
- [ ] FlowSpec peering R5↔R7 Established in address-family ipv4 flowspec
- [ ] `flowspec local-install interface-all` configured on R5
- [ ] End-to-end ping R1→R6 and R1→R7 succeeds

### Troubleshooting

- [ ] Ticket 1 resolved: R5 sees 172.16.1.0/24 via RR reflection
- [ ] Ticket 2 resolved: LOCAL_PREF 200 applied, R2 is best path
- [ ] Ticket 3 resolved: Communities visible on R4 and R5

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
