# BGP Lab 05 — BGP Communities and FlowSpec

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Core Implementation](#5-lab-challenge-core-implementation)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)
11. [Appendix: Script Exit Codes](#11-appendix-script-exit-codes)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.5.i — BGP Communities · 1.5.j — BGP FlowSpec

BGP communities are lightweight route-tagging attributes that allow SPs to attach policy metadata to prefixes, control propagation boundaries, and signal treatment rules across AS boundaries — all without creating per-prefix filter lists. FlowSpec (RFC 5575) extends this model into the traffic plane: rules matching destination IP, protocol, and port are encoded as BGP NLRI and distributed to enforcing routers, turning BGP into a programmable traffic-control plane.

### Standard BGP Communities (RFC 1997)

A standard community is a 32-bit tag formatted as `ASN:value` (e.g., `65100:100`). Communities are carried in the `COMMUNITY` optional transitive attribute. A router can match a community with `ip community-list` and take policy action in a route-map.

```
ip community-list standard CUST-A-TAGGED permit 65100:100

route-map TAG-CUST-A permit 10
 set community 65100:100 additive
```

The `additive` keyword appends the new community to any existing ones. Without it, the previous community list is replaced entirely.

| Community Format | Meaning |
|-----------------|---------|
| `ASN:value` | Private SP tagging (e.g., 65100:100 = Customer A origin) |
| `0:value` | Legacy short format |
| `internet` | Well-known — no restriction |
| `no-export` | Well-known — do not advertise to eBGP peers |
| `no-advertise` | Well-known — do not advertise to any BGP peer |
| `local-AS` | Well-known — do not send outside the sub-confederation AS |

### Well-Known Communities

Three well-known communities control propagation automatically without per-peer route-maps:

- **`no-export`** — The receiving router does not advertise this prefix to any eBGP neighbor. The prefix stays within the AS (or sub-confederation).
- **`no-advertise`** — The receiving router does not advertise this prefix to any BGP peer at all, including iBGP. Effectively local-only.
- **`local-AS`** — Used in confederation designs; not re-advertised outside the sub-AS.

> **Exam tip:** `no-export` stops at the AS boundary (inside is fine). `no-advertise` stops at the router — it is not sent to any peer, iBGP or eBGP.

### Extended Communities and Site-of-Origin (SoO)

Extended communities (RFC 4360) are 64-bit attributes that carry richer metadata. The SoO community (`ip extcommunity-list standard SOO permit soo ASN:ID`) marks routes with their originating site. When a dual-homed customer CE is connected to two PEs (R2 and R3), both PEs tag Customer A's prefix with the same SoO value. If R3 ever receives Customer A's prefix back from R4 via the RR with that SoO already attached, it knows the prefix already came from this site and drops it — preventing routing loops.

```
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1

route-map APPLY-SOO permit 10
 set extcommunity soo 65001:1
```

For extended communities to propagate, `send-community extended` (or `send-community both`) must be configured on each neighbor.

### BGP FlowSpec (RFC 5575 / RFC 8955)

BGP FlowSpec uses a new address family (AFI 1, SAFI 133 — `ipv4 flowspec`) to distribute traffic-matching rules as BGP NLRI. Each FlowSpec route encodes:

- **Match criteria:** destination prefix, source prefix, IP protocol, port numbers, DSCP, TCP flags
- **Action:** carried as BGP extended communities — e.g., `traffic-rate 0` (drop), `traffic-rate N` (rate-limit), `redirect VRF`

On IOS-XE, the match criteria are defined using `class-map type traffic` and the action is defined in `policy-map type traffic`. The FlowSpec AFI peering between routers propagates these rules without any per-router ACL provisioning.

```
class-map type traffic match-all FS_DROP_SSH
 match destination-address ipv4 172.16.1.0 255.255.255.0
 match protocol tcp
 match destination-port 22

policy-map type traffic PM_DROP_SSH
 class FS_DROP_SSH
  police rate 0 pps
   conform-action drop
   exceed-action drop
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Standard community tagging | Setting ASN:value communities inbound at PE with `set community` |
| Community propagation control | Ensuring `send-community both` is set on all iBGP and RR neighbors |
| Community filtering | Matching tagged prefixes with `ip community-list` in route-maps |
| Well-known community enforcement | Applying `no-export` and `no-advertise` and observing propagation stops |
| SoO extended community | Tagging dual-homed customer routes to prevent PE-to-PE routing loops |
| BGP FlowSpec AFI peering | Activating `address-family ipv4 flowspec` between IOS-XE peers |
| FlowSpec rule definition | Writing `class-map type traffic` + `policy-map type traffic` for drop rules |
| FlowSpec verification | Using `show bgp ipv4 flowspec` to confirm NLRI install on enforcer |

---

## 2. Topology & Scenario

**Scenario:** Telco-SP "AS 65100" has grown to include a new external IOS-XE peer, AS 65003 (R7), which also originates BGP FlowSpec rules for traffic engineering. The NOC needs to:

1. Tag all Customer A routes internally with a community to enable policy-based routing
2. Prevent external prefix leakage by tagging select prefixes with well-known communities
3. Protect the dual-homed customer from routing loops using Site-of-Origin
4. Deploy a FlowSpec drop rule to block inbound SSH attacks destined for Customer A's prefix

```
AS 65001        AS 65100 (SP Core — OSPF area 0 / iBGP via R4 RR)
                                                                    AS 65002
┌──────────┐ L1  ┌──────────┐                                      
│    R1    ├─────┤    R2    │                                      
│  CE      │     │ PE East-1│  L3                                  
│ 10.0.0.1 │     │ 10.0.0.2 ├──────────┐                          
│ Lo1:     │     └──────────┘          │                           
│172.16.1.1│                      ┌────┴─────┐                    ┌──────────┐
│          │  L2  ┌──────────┐ L4 │    R4    │  L5  ┌──────────┐ L7│    R6    │
└────┬─────┤──────┤    R3    ├────┤   P / RR ├──────┤    R5    ├───┤  Ext-SP  │
     │     │      │ PE East-2│    │ 10.0.0.4 │      │ PE West  │   │ 10.0.0.6 │
     │     │      │ 10.0.0.3 │    └──────────┘      │ 10.0.0.5 │   │Lo1:      │
     │     │      └──────────┘                      │ CSR1000v │   │172.16.6.1│
     │     │            L6 connects R2↔R3 (IGP)     └────┬─────┘   └──────────┘
     │     │                                             │ L8
     └─────┘                                        ┌────┴─────┐    AS 65003
     (L1 = primary eBGP, L2 = backup eBGP)         │    R7    │
                                                    │  Ext-SP2 │
                                                    │ 10.0.0.7 │
                                                    │ CSR1000v │
                                                    │Lo1:      │
                                                    │172.16.7.1│
                                                    └──────────┘
```

**Key link summary:**
- L1: R1 Gi0/0 ↔ R2 Gi0/0 — `10.1.12.0/24` (eBGP primary)
- L2: R1 Gi0/1 ↔ R3 Gi0/0 — `10.1.13.0/24` (eBGP backup)
- L3: R2 Gi0/1 ↔ R4 Gi0/0 — `10.1.24.0/24` (OSPF/iBGP)
- L4: R3 Gi0/1 ↔ R4 Gi0/1 — `10.1.34.0/24` (OSPF/iBGP)
- L5: R4 Gi0/2 ↔ R5 Gi2   — `10.1.45.0/24` (OSPF/iBGP)
- L6: R2 Gi0/2 ↔ R3 Gi0/2 — `10.1.23.0/24` (OSPF IGP only)
- L7: R5 Gi3  ↔ R6 Gi0/0  — `10.1.56.0/24` (eBGP AS65100↔65002)
- L8: R5 Gi4  ↔ R7 Gi1    — `10.1.57.0/24` (eBGP AS65100↔65003 + FlowSpec)

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R7 | External SP Peer 2 — FlowSpec (AS 65003) | CSR1000v | csr1000v-universalk9.17.03.05 |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A advertised prefix |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, iBGP peering source, cluster-id |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP peering source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id |
| R6 | Loopback1 | 172.16.6.1/24 | External SP prefix |
| R7 | Loopback0 | 10.0.0.7/32 | BGP router-id |
| R7 | Loopback1 | 172.16.7.1/24 | External SP2 prefix |

### Cabling Table

| Link | Source | Destination | Subnet | Purpose |
|------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | eBGP primary |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.1.13.0/24 | eBGP backup |
| L3 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/24 | OSPF/iBGP |
| L4 | R3 Gi0/1 | R4 Gi0/1 | 10.1.34.0/24 | OSPF/iBGP |
| L5 | R4 Gi0/2 | R5 Gi2 | 10.1.45.0/24 | OSPF/iBGP |
| L6 | R2 Gi0/2 | R3 Gi0/2 | 10.1.23.0/24 | OSPF IGP |
| L7 | R5 Gi3 | R6 Gi0/0 | 10.1.56.0/24 | eBGP AS65100↔65002 |
| L8 | R5 Gi4 | R7 Gi1 | 10.1.57.0/24 | eBGP AS65100↔65003 + FlowSpec |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP network | Customer A aggregate; tagged 65100:100 at R2/R3 |
| R6 | 172.16.6.0/24 | eBGP network | External peer prefix; tagged `no-export` |
| R7 | 172.16.7.0/24 | eBGP network | External peer2 prefix; tagged `no-advertise` |

### Console Access Table

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
- Hostnames and `no ip domain-lookup` on all routers
- Interface IP addressing on all routed links and loopbacks (including R7 Gi1 and R5 Gi4)
- OSPF area 0 on R2, R3, R4, R5 (IGP underlay for iBGP next-hop reachability)
- iBGP sessions: R4 as Route Reflector with R2, R3, R5 as RR clients; legacy direct R2↔R5 session
- eBGP sessions: R1↔R2 (primary), R1↔R3 (backup), R5↔R6
- BGP route dampening on R5 (tuned profile: 15 750 2000 60)
- Inter-domain security: TTL-security hops 1 on all eBGP sessions; MD5 authentication on R5↔R6
- Maximum-prefix limits: warning-only on R5↔R6, teardown+restart on R2↔R1
- Dynamic BGP neighbors on R2 (listen range 10.99.0.0/24 peer-group DYN_CUST)
- Multihoming traffic engineering: LOCAL_PREF 200 at R2 inbound, AS-path prepend on R3 backup path, MED outbound at R1

**IS NOT pre-loaded** (student configures this):
- BGP standard community tagging on R2 and R3 (Customer A routes)
- `send-community both` on any neighbor (iBGP or eBGP)
- Community filtering with `ip community-list`
- Well-known community assignment (`no-export`, `no-advertise`)
- SoO extended community definition and application on R2 and R3
- eBGP peering between R5 and R7 (neighbor declaration and address-family activation)
- BGP FlowSpec address-family on R5 and R7
- FlowSpec rule definition on R7 (class-map type traffic + policy-map type traffic)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Activate R7 and Establish eBGP with R5

- Bring up an eBGP session between R5 (AS 65100) and R7 (AS 65003) using the directly connected `10.1.57.0/24` link
- Activate the session in both the `ipv4 unicast` and `ipv4 flowspec` address families on both routers
- On R7, advertise its Loopback1 prefix (172.16.7.0/24) into BGP using a network statement
- On R5, enable FlowSpec local installation on all interfaces

**Verification:** `show bgp ipv4 unicast neighbors 10.1.57.7 | include BGP state` must show `Established`; `show bgp ipv4 flowspec summary` on R5 must list R7 as an active peer.

---

### Task 2: Tag Customer A Routes with Standard Community 65100:100

- On R2, update the inbound route-map applied to the R1 eBGP session to additionally tag Customer A's prefix (172.16.1.0/24) with community `65100:100`
- Use the `additive` keyword so existing policy attributes are preserved
- Enable `send-community both` on R2's iBGP neighbors (R4 and the legacy R5 session) so the community propagates through the SP core
- On R4, enable `send-community both` toward all three RR clients (R2, R3, R5) — the RR must carry communities transparently
- Verify the community appears on R5 using `show ip bgp 172.16.1.0/24`
- Demonstrate filtering: create an `ip community-list` on R5 matching `65100:100` and use it in `show ip bgp community 65100:100` to confirm the tag is visible

**Verification:** `show ip bgp 172.16.1.0/24` on R5 must show `Community: 65100:100`; `show ip bgp community 65100:100` on R5 must include 172.16.1.0/24.

---

### Task 3: Apply Well-Known Communities — no-export and no-advertise

- On R6, create a route-map that tags its advertised prefix (172.16.6.0/24) with the `no-export` community before sending it to R5. Enable `send-community` on R6's neighbor toward R5.
- On R5, apply a route-map inbound from R6 that additionally stamps the received prefix with `no-export` (as a defense-in-depth measure) and enable `send-community both` toward all iBGP peers.
- On R7, apply a route-map outbound toward R5 that tags 172.16.7.0/24 with `no-advertise`
- Verify propagation boundaries: 172.16.6.0/24 must appear in R4's BGP table but must NOT be sent to R1 or R3 via eBGP; 172.16.7.0/24 must appear in R5's BGP table but must NOT be forwarded to any other BGP peer including iBGP.

**Verification:** `show ip bgp 172.16.6.0/24` on R5 must show `Community: no-export`; `show ip bgp 172.16.7.0/24` on R5 must show `Community: no-advertise`; these prefixes must NOT appear in R2's BGP table.

---

### Task 4: Configure Site-of-Origin Extended Community for Dual-Homed Customer A

- Define an extended community list on R2 and R3 matching SoO value `65001:1`
- On R2, update the inbound route-map from R1 (L1 primary path) to set the extended community `soo 65001:1` on Customer A's prefix; also enable `send-community both` to carry extended communities to iBGP peers
- Apply the same SoO stamp on R3 inbound from R1 (L2 backup path)
- Confirm that if the RR reflects Customer A's prefix back toward R3, R3 discards the route because the SoO matches — preventing the backup PE from re-advertising a route that originated from its own site

**Verification:** `show ip bgp 172.16.1.0/24` on R5 must show an extended community entry containing `SoO:65001:1`. On R3, `show ip bgp 172.16.1.0/24` received from R4 must show the SoO attribute; the route is accepted but the SoO prevents re-advertisement back toward R1 on L2.

---

### Task 5: Originate a BGP FlowSpec Rule on R7 and Verify Install on R5

- On R7, define a traffic class matching destination prefix `172.16.1.0/24`, protocol TCP, destination port 22 using `class-map type traffic`
- Define a policy with action `police rate 0 pps` (drop) bound to that class using `policy-map type traffic`
- Configure the FlowSpec address family on R7 with `bgp flowspec disable-local-install` (R7 originates the rule but does not enforce it locally) and activate the R5 neighbor in the FlowSpec AF with `send-community both`
- On R5, activate the R7 neighbor in `address-family ipv4 flowspec` and enable `bgp flowspec local-install interface-all` to install received FlowSpec rules into the forwarding plane
- Verify the FlowSpec NLRI appears in R5's BGP table and is installed

**Verification:** `show bgp ipv4 flowspec` on R5 must list the FlowSpec NLRI for destination 172.16.1.0/24 with TCP/22; `show bgp ipv4 flowspec summary` must show R7 as Established.

---

## 6. Verification & Analysis

### Task 1 — R5↔R7 eBGP Session

```
R5# show bgp ipv4 unicast summary | include 10.1.57.7
10.1.57.7       4      65003      65      67       18          0          0 00:08:42        4   ! ← State: integer = # prefixes received; must not show Idle or Active

R5# show bgp ipv4 flowspec summary
Neighbor        V    AS MsgRcvd MsgSent TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.57.7       4 65003      22      20       3    0    0 00:08:40        1   ! ← FlowSpec session Established; 1 FlowSpec NLRI received
```

### Task 2 — Community 65100:100 on 172.16.1.0/24

```
R5# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 12
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65001
    10.0.0.2 (metric 3) from 10.0.0.4 (10.0.0.4)
      Origin IGP, metric 10, localpref 200, valid, internal, best
      Community: 65100:100                        ! ← Community present after full RR chain
      Extended Community: SoO:65001:1             ! ← Extended community also propagated
      CLUSTER_LIST: 10.0.0.4
      ORIGINATOR_ID: 10.0.0.2

R5# show ip bgp community 65100:100
BGP table version is 12, local router ID is 10.0.0.5
   Network          Next Hop          Metric LocPrf Weight Path
*> 172.16.1.0/24   10.0.0.2              10    200      0 65001 i ! ← Tag confirmed visible
```

### Task 3 — Well-Known Communities

```
R5# show ip bgp 172.16.6.0/24
    Community: no-export                          ! ← no-export tag present
    ...

R5# show ip bgp 172.16.7.0/24
    Community: no-advertise                       ! ← no-advertise tag present
    ...

! Confirm 172.16.6.0/24 is NOT in R2's BGP table (no-export blocks eBGP & iBGP re-adv):
R2# show ip bgp 172.16.6.0/24
% Network not in table                            ! ← Correct: no-export stopped propagation

! Confirm 172.16.7.0/24 is NOT in R4's BGP table:
R4# show ip bgp 172.16.7.0/24
% Network not in table                            ! ← Correct: no-advertise stops all forwarding
```

### Task 4 — SoO Extended Community

```
R5# show ip bgp 172.16.1.0/24
      Extended Community: SoO:65001:1             ! ← SoO attribute present
      Community: 65100:100

R3# show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 8
  65001
    10.0.0.2 (metric 2) from 10.0.0.4 (10.0.0.4)
      Extended Community: SoO:65001:1             ! ← R3 sees the SoO; loop prevention active
```

### Task 5 — FlowSpec Install on R5

```
R5# show bgp ipv4 flowspec
BGP table version is 3, local router ID is 10.0.0.5
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
Origin codes: i - IGP, e - EGP, ? - incomplete

   Network          Next Hop            Metric LocPrf Weight Path
*> [Dest:172.16.1.0/24][Proto:=6][DstPort:=22]
                    10.1.57.7                              0 65003 i ! ← FlowSpec NLRI installed
                    Extended Community: MLNH:0 TRA:0:0    ! ← traffic-rate 0 action encoded

R5# show bgp ipv4 flowspec summary
Neighbor        V    AS MsgRcvd MsgSent TblVer  InQ OutQ Up/Down  State/PfxRcd
10.1.57.7       4 65003      35      30       3    0    0 00:12:08        1   ! ← 1 FlowSpec NLRI
```

---

## 7. Verification Cheatsheet

### Standard Community Operations

```
ip community-list standard <NAME> permit <ASN:value>
ip community-list standard <NAME> permit no-export
ip community-list standard <NAME> permit no-advertise

route-map SET-COMMUNITY permit 10
 set community <ASN:value> additive
```

| Command | Purpose |
|---------|---------|
| `set community 65100:100 additive` | Append community in route-map |
| `set community no-export` | Apply no-export well-known community |
| `set community no-advertise` | Apply no-advertise well-known community |
| `neighbor X send-community` | Send standard communities to neighbor |
| `neighbor X send-community both` | Send standard + extended communities |
| `neighbor X send-community extended` | Send only extended communities |

> **Exam tip:** Without `send-community` on the neighbor, communities are set locally but silently stripped before the update is sent. BGP does NOT send communities by default — you must explicitly enable it per neighbor.

### Community Verification

```
show ip bgp community <ASN:value>
show ip bgp <prefix>
show ip bgp community-list <NAME>
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp 172.16.1.0/24` | `Community: 65100:100` in the prefix entry |
| `show ip bgp community 65100:100` | Lists all prefixes tagged with that community |
| `show ip bgp community no-export` | Lists prefixes with no-export community |

### Extended Community (SoO) Operations

```
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1

route-map APPLY-SOO permit 10
 set extcommunity soo 65001:1
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp <prefix>` | `Extended Community: SoO:65001:1` in the path |
| `show ip extcommunity-list` | Lists defined extended community lists |

### BGP FlowSpec (IOS-XE)

```
address-family ipv4 flowspec
 bgp flowspec local-install interface-all   ! receiver/enforcer
 bgp flowspec disable-local-install         ! originator only (no local enforce)
 neighbor X activate
 neighbor X send-community both
exit-address-family
```

| Command | What to Look For |
|---------|-----------------|
| `show bgp ipv4 flowspec` | Lists FlowSpec NLRI with encoded match+action |
| `show bgp ipv4 flowspec summary` | FlowSpec neighbor states and prefix counts |
| `show bgp ipv4 flowspec detail` | Full encoding of each FlowSpec route |

> **Exam tip:** Both the originator (R7) and enforcer (R5) must have `address-family ipv4 flowspec` configured and the neighbor activated in that AF. If only one side has it, the session stays up but no FlowSpec NLRI is exchanged.

### Verification Commands Quick Reference

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp <prefix>` | Community, Extended Community, CLUSTER_LIST in path entry |
| `show ip bgp community <value>` | All prefixes tagged with that community value |
| `show ip bgp summary` | Neighbor states, prefix counts |
| `show bgp ipv4 flowspec summary` | FlowSpec peer states |
| `show bgp ipv4 flowspec` | Installed FlowSpec NLRI (match criteria + action) |
| `show ip extcommunity-list` | Defined extended community lists |

### Common BGP Communities Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Community set but not visible at remote router | `send-community` missing on the originating neighbor |
| Community propagated to one hop but stops at RR | RR missing `send-community both` toward its clients |
| `no-export` prefix still visible at remote AS | Community tagged on wrong router (receiver, not sender) |
| SoO attribute not appearing on reflected routes | `send-community extended` or `both` not set on iBGP peers |
| FlowSpec session stays in Idle | `address-family ipv4 flowspec` not activated on one side |
| FlowSpec NLRI not installed | `bgp flowspec local-install interface-all` missing on enforcer |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Activate R7 and Establish eBGP with R5

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 (CSR1000v IOS-XE)
router bgp 65100
 neighbor 10.1.57.7 remote-as 65003
 neighbor 10.1.57.7 description External-Peer-R7-AS65003-FlowSpec
 !
 address-family ipv4
  neighbor 10.1.57.7 activate
  neighbor 10.1.57.7 send-community both
 exit-address-family
 !
 address-family ipv4 flowspec
  bgp flowspec local-install interface-all
  neighbor 10.1.57.7 activate
  neighbor 10.1.57.7 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view R7 Configuration</summary>

```bash
! R7 (CSR1000v IOS-XE)
ip prefix-list R7-PREFIX seq 5 permit 172.16.7.0/24
!
router bgp 65003
 bgp router-id 10.0.0.7
 bgp log-neighbor-changes
 neighbor 10.1.57.5 remote-as 65100
 neighbor 10.1.57.5 description PE-West-R5-AS65100
 !
 address-family ipv4 unicast
  network 172.16.7.0 mask 255.255.255.0
  neighbor 10.1.57.5 activate
  neighbor 10.1.57.5 send-community both
 exit-address-family
 !
 address-family ipv4 flowspec
  bgp flowspec disable-local-install
  neighbor 10.1.57.5 activate
  neighbor 10.1.57.5 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show bgp ipv4 unicast summary | include 10.1.57.7
R5# show bgp ipv4 flowspec summary
```
</details>

---

### Task 2: Community 65100:100 Tagging

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — update existing route-map, add send-community
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
 address-family ipv4
  neighbor 10.0.0.4 send-community both
  neighbor 10.0.0.5 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — RR must propagate communities to all clients
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.2 send-community both
  neighbor 10.0.0.3 send-community both
  neighbor 10.0.0.5 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip bgp 172.16.1.0/24
R5# show ip bgp community 65100:100
```
</details>

---

### Task 3: Well-Known Communities no-export and no-advertise

<details>
<summary>Click to view R6 Configuration (no-export)</summary>

```bash
! R6
ip prefix-list R6-PREFIX seq 5 permit 172.16.6.0/24
!
route-map TO-R5-NOEXPORT permit 10
 match ip address prefix-list R6-PREFIX
 set community no-export
!
route-map TO-R5-NOEXPORT permit 20
!
router bgp 65002
 address-family ipv4
  neighbor 10.1.56.5 route-map TO-R5-NOEXPORT out
  neighbor 10.1.56.5 send-community
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 (no-export inbound defense-in-depth)</summary>

```bash
! R5 — also apply no-export inbound from R6 and enable send-community to iBGP
ip prefix-list EXT-PEER-R6 seq 5 permit 172.16.6.0/24
!
route-map FROM-R6-APPLY-NOEXP permit 10
 match ip address prefix-list EXT-PEER-R6
 set community no-export additive
!
route-map FROM-R6-APPLY-NOEXP permit 20
!
router bgp 65100
 address-family ipv4
  neighbor 10.1.56.6 route-map FROM-R6-APPLY-NOEXP in
  neighbor 10.1.56.6 send-community both
  neighbor 10.0.0.4 send-community both
  neighbor 10.0.0.2 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view R7 Configuration (no-advertise)</summary>

```bash
! R7 — tag own prefix with no-advertise
ip prefix-list R7-PREFIX seq 5 permit 172.16.7.0/24
!
route-map TO-R5-NOADVERTISE permit 10
 match ip address prefix-list R7-PREFIX
 set community no-advertise
!
route-map TO-R5-NOADVERTISE permit 20
!
router bgp 65003
 address-family ipv4 unicast
  neighbor 10.1.57.5 route-map TO-R5-NOADVERTISE out
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip bgp 172.16.6.0/24
R5# show ip bgp 172.16.7.0/24
R2# show ip bgp 172.16.6.0/24     ! must return "Network not in table"
R4# show ip bgp 172.16.7.0/24     ! must return "Network not in table"
```
</details>

---

### Task 4: SoO Extended Community

<details>
<summary>Click to view R2 and R3 Configuration</summary>

```bash
! R2 (already included in Task 2 solution — reproduced for clarity)
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1
!
route-map FROM-CUST-A-PRIMARY permit 10
 set extcommunity soo 65001:1
 set community 65100:100 additive
 set local-preference 200

! R3
ip prefix-list CUST-A-BACKUP seq 5 permit 172.16.1.0/24
ip extcommunity-list standard SOO_CUSTA permit soo 65001:1
!
route-map FROM-CUST-A-BACKUP permit 10
 match ip address prefix-list CUST-A-BACKUP
 set extcommunity soo 65001:1
!
route-map FROM-CUST-A-BACKUP permit 20
!
router bgp 65100
 address-family ipv4
  neighbor 10.1.13.1 route-map FROM-CUST-A-BACKUP in
  neighbor 10.0.0.4 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip bgp 172.16.1.0/24    ! look for "Extended Community: SoO:65001:1"
R3# show ip bgp 172.16.1.0/24    ! SoO attribute visible on reflected route from R4
```
</details>

---

### Task 5: BGP FlowSpec Rule

<details>
<summary>Click to view R7 FlowSpec Configuration</summary>

```bash
! R7 — define the traffic class and action policy for FlowSpec
class-map type traffic match-all FS_DROP_SSH_CUSTA
 match destination-address ipv4 172.16.1.0 255.255.255.0
 match protocol tcp
 match destination-port 22
!
policy-map type traffic PM_FS_BLACKHOLE_SSH
 class FS_DROP_SSH_CUSTA
  police rate 0 pps
   conform-action drop
   exceed-action drop
!
! Configure FlowSpec AF (originator — disable local install)
router bgp 65003
 address-family ipv4 flowspec
  bgp flowspec disable-local-install
  neighbor 10.1.57.5 activate
  neighbor 10.1.57.5 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view R5 FlowSpec Receiver Configuration</summary>

```bash
! R5 — activate FlowSpec AF and enable local install
router bgp 65100
 address-family ipv4 flowspec
  bgp flowspec local-install interface-all
  neighbor 10.1.57.7 activate
  neighbor 10.1.57.7 send-community both
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show bgp ipv4 flowspec
R5# show bgp ipv4 flowspec summary
R5# show bgp ipv4 flowspec detail
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                            # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>      # restore
```

---

### Ticket 1 — R5 Does Not See Community 65100:100 on 172.16.1.0/24

The NOC reports that a community-based routing policy on R5 is not triggering. `show ip bgp community 65100:100` on R5 returns no entries, even though R2 appears to be tagging the route correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.1.0/24` on R5 shows `Community: 65100:100`; `show ip bgp community 65100:100` on R5 lists the prefix.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm R2 is setting the community
R2# show ip bgp 172.16.1.0/24
! Look for: Community: 65100:100 — if absent, the route-map is broken

! 2. Check if R2 is propagating the community to R4
R2# show ip bgp neighbors 10.0.0.4 | include send community
! Should show: Community attribute sent to this neighbor

! 3. Check R4's view — is the community there?
R4# show ip bgp 172.16.1.0/24
! If Community is absent at R4, the issue is R2 → R4 propagation (send-community missing)

! 4. Check R4 to R5 — does R4 forward community?
R4# show ip bgp neighbors 10.0.0.5 | include send community
! Should show: Community attribute sent to this neighbor
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: send-community both missing on R4 toward R5

R4(config)# router bgp 65100
R4(config-router)# address-family ipv4
R4(config-router-af)# neighbor 10.0.0.5 send-community both
R4(config-router-af)# end
R4# clear ip bgp 10.0.0.5 soft out

! Verify:
R5# show ip bgp 172.16.1.0/24    ! Community: 65100:100 must now appear
```
</details>

---

### Ticket 2 — FlowSpec NLRI Not Appearing on R5

The security team deployed a FlowSpec drop rule on R7 for SSH attacks targeting Customer A (172.16.1.0/24). R7 shows the FlowSpec session as Established, but `show bgp ipv4 flowspec` on R5 returns an empty table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show bgp ipv4 flowspec` on R5 lists the NLRI for `[Dest:172.16.1.0/24][Proto:=6][DstPort:=22]`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm FlowSpec session state
R5# show bgp ipv4 flowspec summary
! Check: is the session Established? If Idle, the AF is not activated on one side.

! 2. Check R5's FlowSpec neighbor capability
R5# show bgp ipv4 unicast neighbors 10.1.57.7 | include capability
! Look for: AF ipv4 flowspec negotiated

! 3. Check R7's FlowSpec AF config
R7# show bgp ipv4 flowspec summary
! Confirm R7 sees R5 as an active FlowSpec peer

! 4. Check if FlowSpec NLRI is in R7's table
R7# show bgp ipv4 flowspec
! If no NLRI here, the class-map/policy-map is not injecting the flowspec route
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: address-family ipv4 flowspec not activated for the R7 neighbor on R5

R5(config)# router bgp 65100
R5(config-router)# address-family ipv4 flowspec
R5(config-router-af)# neighbor 10.1.57.7 activate
R5(config-router-af)# neighbor 10.1.57.7 send-community both
R5(config-router-af)# bgp flowspec local-install interface-all
R5(config-router-af)# end

! Verify:
R5# show bgp ipv4 flowspec summary  ! R7 must show as Established
R5# show bgp ipv4 flowspec          ! NLRI must appear
```
</details>

---

### Ticket 3 — 172.16.6.0/24 Visible at R2 (no-export Not Enforced)

The NOC requires that the R6 external prefix 172.16.6.0/24 remain within AS 65100 and not propagate to Customer A (R1) or be reflected toward the East PEs. However, R2's BGP table shows the prefix, and the community tag is absent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp 172.16.6.0/24` on R5 shows `Community: no-export`; `show ip bgp 172.16.6.0/24` on R2 returns "Network not in table".

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check the community on R5 after receiving from R6
R5# show ip bgp 172.16.6.0/24
! If Community line is absent, the no-export tag was not set or not propagated

! 2. Check R6's outbound route-map
R6# show route-map
! Confirm route-map TO-R5-NOEXPORT is present and the set community no-export action exists

! 3. Check that R6 is propagating communities
R6# show ip bgp neighbors 10.1.56.5 | include send community
! Must show: Community attribute sent

! 4. If community is set on R5 but still propagating to R2, check R5's iBGP propagation
R5# show ip bgp neighbors 10.0.0.4 | include send community
! Must show send-community enabled — without it, R4 strips the tag
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fault: R6 missing send-community on neighbor toward R5 (community tagged but stripped)

R6(config)# router bgp 65002
R6(config-router)# address-family ipv4
R6(config-router-af)# neighbor 10.1.56.5 send-community
R6(config-router-af)# end
R6# clear ip bgp 10.1.56.5 soft out

! Verify:
R5# show ip bgp 172.16.6.0/24    ! Community: no-export must appear
R2# show ip bgp 172.16.6.0/24    ! Must return "% Network not in table"
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R5↔R7 eBGP session is Established in both `ipv4 unicast` and `ipv4 flowspec` AFs
- [ ] 172.16.7.0/24 appears in R5's BGP table from R7
- [ ] `show ip bgp 172.16.1.0/24` on R5 shows `Community: 65100:100`
- [ ] `show ip bgp community 65100:100` on R5 lists 172.16.1.0/24
- [ ] `show ip bgp 172.16.6.0/24` on R5 shows `Community: no-export`
- [ ] `show ip bgp 172.16.7.0/24` on R5 shows `Community: no-advertise`
- [ ] 172.16.6.0/24 is NOT present in R2's BGP table
- [ ] 172.16.7.0/24 is NOT present in R4's BGP table
- [ ] `show ip bgp 172.16.1.0/24` on R5 shows `Extended Community: SoO:65001:1`
- [ ] `show bgp ipv4 flowspec` on R5 lists the FlowSpec NLRI for 172.16.1.0/24 TCP/22

### Troubleshooting

- [ ] Ticket 1 resolved: community 65100:100 visible on R5 after fixing send-community
- [ ] Ticket 2 resolved: FlowSpec NLRI appears in R5's table after activating the AF
- [ ] Ticket 3 resolved: 172.16.6.0/24 shows no-export on R5 and is absent from R2

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure (one or more devices failed) | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed (lab nodes not started) | Inject scripts only |
