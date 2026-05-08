# Lab 04: PCE Path Computation, SRLG, and Tree SID

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

**Exam Objective:** 4.3.c (PCE-based path calculation), 4.3.d (SRLG), 4.3.e (Tree SID) - Implementing Cisco Service Provider Advanced Routing (300-510)

This lab introduces a centralized SR-TE control plane. Lab-03 used local CSPF on each headend; lab-04 hands path computation to a dedicated PCE controller. The PCE learns the full IGP topology via BGP-LS from R2, accepts PCEP delegations from R1, R3, and R4, computes SRLG-disjoint primary+backup pairs, and orchestrates a P2MP Tree SID rooted at R1.

### BGP-LS - Topology Distribution to the Controller

BGP-LS (RFC 7752) is a BGP address family (`link-state link-state`) that carries IGP topology - nodes, links, prefixes, and TE attributes - as BGP NLRI. R2 originates the IS-IS topology into BGP-LS and peers iBGP-LS with the PCE at 10.0.0.99. The PCE never joins IS-IS; it consumes the topology purely as a BGP-LS receiver. This isolation is intentional: a controller fault never destabilizes the forwarding plane.

```
router bgp 65100
 address-family link-state link-state
 !
 neighbor 10.0.0.99
  remote-as 65100
  update-source Loopback0
  address-family link-state link-state
  !
 !
!
```

### PCEP - Path Computation Delegation

PCEP (RFC 5440 + SR extensions RFC 8664) is the protocol PCCs (R1, R3, R4) use to ask the PCE for SR-TE label stacks. The PCC declares a candidate-path as `dynamic pcep`; on policy activation the PCC sends a Path Computation Request to the PCE; the PCE runs CSPF over its BGP-LS topology and returns a SID list; the PCC installs the stack. Delegation is per-policy - other policies on the same PCC can still use local CSPF.

```
segment-routing
 traffic-eng
  pcc
   pce address ipv4 10.0.0.99
  !
 !
!
```

### SRLG - Shared Risk Link Groups

SRLG groups links that share a physical risk (a duct, a fiber bundle, a card slot). Two links in the same SRLG cannot be considered link-disjoint by CSPF even if their IP topology is disjoint. Each interface lists one or more SRLG group names; IS-IS distributes the groups via TE sub-TLV; BGP-LS forwards them to the PCE. A `disjoint-path` constraint with `type srlg` (or `type link-or-srlg`) forces CSPF to compute a path pair sharing no SRLG group.

```
srlg
 interface GigabitEthernet0/0/0/0
  name SRLG_L1
 !
!
```

### Tree SID - P2MP via Centralized Computation

Tree SID is SR-MPLS Point-to-Multipoint with PCE-driven branch computation. The PCE holds a `p2mp policy` defining a root, a leaf set, and a color. The PCE computes the optimal Steiner tree, allocates P2MP segment identifiers, and pushes per-PCC instructions: the root encapsulates with the tree-SID label, intermediate nodes replicate per branch, leaves decapsulate. **Behavioural caveat (xrv9k 7.x):** the control plane (`show segment-routing traffic-eng p2mp policy`) works in QEMU; ASIC-level packet replication does not. Production ASR 9000 hardware would replicate at branch points.

### IOS-XR Reference Syntax

| Feature | Command path |
|---------|--------------|
| BGP-LS AF on neighbor | `router bgp / address-family link-state link-state / neighbor X / address-family link-state link-state` |
| PCC pointing at PCE | `segment-routing / traffic-eng / pcc / pce address ipv4 10.0.0.99` |
| Per-policy PCEP delegation | `dynamic / pcep` inside a candidate-path |
| SRLG on interface | `srlg / interface X / name SRLG_NAME` |
| PCE process | `pce / address ipv4 10.0.0.99 / segment-routing / traffic-eng` |
| Tree SID policy | `segment-routing / traffic-eng / p2mp / policy NAME / color N endpoint ipv4 ROOT` |
| Disjoint constraint | `dynamic / constraints / disjoint-path group-id N type link-or-srlg` |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| BGP-LS bring-up | Configure iBGP-LS between an IGP producer and a PCE, verify topology ingestion |
| PCEP delegation | Configure PCC clients, delegate dynamic candidate-paths to a PCE |
| SRLG modeling | Group links by shared risk, propagate via IS-IS + BGP-LS |
| Disjoint-path planning | Force CSPF to deliver SRLG-disjoint primary+backup pairs |
| Tree SID provisioning | Define a P2MP policy on the PCE and verify control-plane state on root + leaves |
| Controller-plane troubleshooting | Diagnose BGP-LS gaps, PCEP misconfiguration, and SRLG conflicts |

---

## 2. Topology & Scenario

You are the SP design engineer extending the lab-03 SR-TE network with a centralized controller. Operations has approved a single PCE node (10.0.0.99) sitting on the management plane behind R2. The PCE will compute paths for headends R1, R3, R4 and orchestrate a multicast Tree SID delivering low-latency video from R1 toward R3 and R4. Your tasks: stand up the controller plane, replace one local-CSPF policy with PCE-delegated computation, wrap a production-grade SRLG-disjoint pair around critical traffic, and prove the Tree SID control plane converges.

```
                 AS 65100 SP core (IS-IS L2 + SR-MPLS)

           ┌──────────────┐                          ┌──────────────┐
           │      R1      │────────── L1 ────────────│      R2      │
           │ Lo0 10.0.0.1 │       10.1.12.0/24       │ Lo0 10.0.0.2 │
           └──┬────────┬──┘                          └──┬────────┬──┘
              │        │                                │        │
              │L4      │L5 (diagonal)                   │L2      │L6 (BGP-LS)
              │        │                                │        │10.1.29.0/24
              │        │                                │        │
           ┌──┴───┐    │                          ┌─────┴──┐ ┌───┴────────┐
           │  R4  │────┼─── L3 (10.1.34.0/24) ────│   R3   │ │    PCE     │
           │ 10.0 │    │                          │ 10.0   │ │ 10.0.0.99  │
           │ .0.4 │    └──────────────────────────│ .0.3   │ └────────────┘
           └──────┘                               └──┬─────┘
                                                     │ L8 (10.1.33.0/24)
            L7 (10.1.11.0/24)                      ┌─┴──┐
           ┌─────┐                                 │CE2 │ AS 65102
           │ CE1 │──────────────── (to R1) ───┐    │    │
           │     │ AS 65101                   │    └────┘
           └─────┘                            │
                                              │
                                              └─→ R1 Gi0/0/0/3
```

PCE is reachable through R2 only. R2 carries `10.0.0.99/32` as a redistributed static route into IS-IS so R1, R3, R4 can establish PCEP sessions to the controller. PCE itself runs no IGP - it has a static default route via R2 and learns the full IS-IS topology purely through BGP-LS.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP edge / SR ingress, Tree SID root, PCC | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R2 | SP core / BGP-LS producer to PCE | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R3 | SP edge / SR egress, Tree SID leaf, PCC | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R4 | SP core / Tree SID leaf, PCC | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| PCE | SR PCE controller / BGP-LS receiver | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| CE1 | Customer edge AS 65101 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer edge AS 65102 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP source, Tree SID root |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, BGP-LS source to PCE |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP source, Tree SID leaf |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, Tree SID leaf |
| PCE | Loopback0 | 10.0.0.99/32 | PCE listener, BGP-LS source |
| CE1 | Loopback0 | 10.0.0.11/32 | Router ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix |
| CE2 | Loopback0 | 10.0.0.12/32 | Router ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix |

### Cabling

| Link | A-side | B-side | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi0/0/0/0 | R2 Gi0/0/0/0 | 10.1.12.0/24 | SP core, IS-IS+SR+LDP, SRLG_L1 |
| L2 | R2 Gi0/0/0/1 | R3 Gi0/0/0/0 | 10.1.23.0/24 | SP core, IS-IS+SR+LDP, SRLG_L2, BLUE |
| L3 | R3 Gi0/0/0/1 | R4 Gi0/0/0/0 | 10.1.34.0/24 | SP core, IS-IS+SR+LDP, SRLG_L3, RED |
| L4 | R1 Gi0/0/0/1 | R4 Gi0/0/0/1 | 10.1.14.0/24 | SP core ring closer, SRLG_L4 |
| L5 | R1 Gi0/0/0/2 | R3 Gi0/0/0/2 | 10.1.13.0/24 | SP core diagonal, SRLG_L5 |
| L6 | R2 Gi0/0/0/2 | PCE Gi0/0/0/0 | 10.1.29.0/24 | BGP-LS + PCEP path to PCE |
| L7 | R1 Gi0/0/0/3 | CE1 Gi0/0 | 10.1.11.0/24 | eBGP R1 ↔ CE1 |
| L8 | R3 Gi0/0/0/3 | CE2 Gi0/0 | 10.1.33.0/24 | eBGP R3 ↔ CE2 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| CE1 | 192.0.2.0/24 | eBGP `network` | Customer prefix steered by SR-TE |
| CE2 | 198.51.100.0/24 | eBGP `network` | Customer prefix tagged color:10 by R3 |
| R2 | 10.0.0.99/32 | redistribute static into IS-IS | PCE loopback reachability for R1/R3/R4 PCEP |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PCE | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py` (chained from lab-03 solutions plus a new PCE node):

**IS pre-loaded:**

- All lab-03 solution state on R1, R2, R3, R4, CE1, CE2 (IS-IS L2, SR-MPLS, TI-LFA, LDP, SR-TE static policies for color 10/20/30, automated steering on color 10)
- New L6 interface IP addressing on R2 (Gi0/0/0/2 = 10.1.29.2/24)
- New PCE node booted with hostname, Loopback0 (10.0.0.99/32), and Gi0/0/0/0 (10.1.29.99/24)

**IS NOT pre-loaded** (student configures this):

- PCE reachability path (static route on R2 toward 10.0.0.99/32 + redistribution into IS-IS; static default on PCE via R2)
- iBGP-LS session R2 ↔ PCE (BGP link-state address-family on both ends)
- PCE process (`pce / address ipv4 / segment-routing traffic-eng`)
- PCC client config on R1, R3, R4 pointing at the PCE
- PCEP-delegated candidate-path on R1's color-30 SR-TE policy
- Disjoint-path SR-TE policy pair (color 40 primary + color 41 backup, link-disjoint via PCE)
- SRLG groups on every core interface of R1, R2, R3, R4
- Tree SID P2MP policy on PCE rooted at R1, leaves R3 and R4

---

## 5. Lab Challenge: Core Implementation

### Task 1: PCE reachability and BGP-LS bring-up

- On R2, configure a static route for the PCE loopback `10.0.0.99/32` pointing at `10.1.29.99`, then redistribute it into IS-IS using a route-policy that only permits the PCE loopback prefix.
- On PCE, configure a static route covering `10.0.0.0/24` via `10.1.29.2` so PCE can reach all core router loopbacks.
- Configure iBGP between R2 (Loopback0 source) and PCE (Loopback0 source) under AS 65100, activate the `link-state link-state` address-family on both ends only - do NOT activate the IPv4 unicast AF for this neighbor.

**Verification:** `show bgp link-state link-state summary` on PCE must list R2 in Established state with a non-zero PfxRcd count.

---

### Task 2: PCE topology ingestion check

- Inspect the BGP-LS NLRI on PCE and confirm every IS-IS node and link from the core is present.
- Cross-check against `show isis database` on any core router - the same set of node and link advertisements must appear.

**Verification:** `show bgp link-state link-state` on PCE must list four node NLRIs (one per IS-IS router) and at least five link NLRIs (one per core link L1-L5).

---

### Task 3: PCEP client configuration on R1, R3, R4

- On R1, R3, and R4, configure a PCC pointing at PCE address `10.0.0.99` under `segment-routing traffic-eng / pcc`.
- Verify TCP reachability to the PCE first (PCEP runs over TCP/4189). If PCE reachability fails, return to Task 1.

**Verification:** `show segment-routing traffic-eng pcc ipv4 peer` on each PCC must show the PCE peer in `up` state. `show pce session` on PCE must list R1, R3, R4 as connected clients.

---

### Task 4: Delegate the color-30 SR-TE policy to the PCE

- On R1, modify the existing color-30 SR-TE policy so its dynamic candidate-path uses `pcep` instead of local computation. Keep the metric type set to `te`.
- The PCE now owns path computation for color 30. Confirm the policy returns to UP state with a SID list pushed by the PCE.

**Verification:** `show segment-routing traffic-eng policy color 30 detail` on R1 must report `Computation Type: PCEP` and a non-empty `Segment List`. `show pce lsp` on PCE must list the corresponding LSP.

---

### Task 5: SRLG on every core link

- On every core router (R1, R2, R3, R4) configure SRLG group names so that each link L1-L5 has a single SRLG name shared by both endpoints. Suggested names: SRLG_L1, SRLG_L2, SRLG_L3, SRLG_L4, SRLG_L5 - one group per physical link.
- On every endpoint of a given link the same SRLG group name MUST be applied so PCE sees the link as belonging to that group on both sides.

**Verification:** `show srlg interface brief` on each core router must list its core interfaces with the assigned group name. `show bgp link-state link-state detail` on PCE must show the SRLG sub-TLV present on every link NLRI.

---

### Task 6: SRLG-aware disjoint policy pair (color 40 primary, color 41 backup)

- On R1, build two SR-TE policies that share a disjoint-path group-id (group-id 1) and both delegate computation to the PCE. The primary policy carries color 40 toward end-point 10.0.0.3; the backup policy carries color 41 to the same endpoint. Both candidate-paths use `dynamic pcep` with metric type `igp` and a `disjoint-path group-id 1 type link` constraint.
- The PCE will compute two link-disjoint SID stacks satisfying the group constraint.

**Verification:** `show segment-routing traffic-eng policy color 40 detail` and `... color 41 detail` on R1 must both be UP with non-overlapping SID lists. `show pce lsp detail` on PCE must report the disjoint-path constraint satisfied.

---

### Task 7: Tree SID P2MP - root R1, leaves R3 and R4

- On PCE, configure a P2MP policy named `TREE_1` under `segment-routing traffic-eng p2mp` with color 100 and endpoint Loopback0 of R1. Add a dynamic candidate-path so the PCE computes the Steiner tree centrally.
- The leaves R3 and R4 are signalled to the PCE through their PCC sessions (Task 3); no explicit leaf-side P2MP policy is required for control-plane verification.

**Verification:** `show segment-routing traffic-eng p2mp policy` on PCE must report the P2MP policy in administrative `up` state with the configured color and endpoint.

> **xrv9k 7.x caveat:** the control plane converges; ASIC-level P2MP replication is unsupported in QEMU. Verification stops at the control-plane state. On real ASR 9000 hardware the line card replicates packets per branch.

---

### Task 8: Document the controller-plane separation

- Confirm that disabling IS-IS on PCE does NOT affect PCE topology learning (it never had IS-IS) - the PCE only depends on BGP-LS from R2 plus the static return path. This separation is a production-grade design pattern; capture a one-line note in your lab journal.

**Verification:** `show isis adjacency` on PCE must return no output. `show bgp link-state link-state summary` must still show R2 Established and the topology fully populated.

---

## 6. Verification & Analysis

### BGP-LS session

```bash
RP/0/RP0/CPU0:PCE# show bgp link-state link-state summary
BGP router identifier 10.0.0.99, local AS number 65100
...
Neighbor        Spk    AS   MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  St/PfxRcd
10.0.0.2          0  65100      57      48       12    0    0 00:12:34         9   ! <- R2 Established with non-zero PfxRcd
```

### PCE topology

```bash
RP/0/RP0/CPU0:PCE# show bgp link-state link-state
...
*>i[V][L2][I0x0][N[c65100][b0.0.0.0][s0000.0000.0001.00]]/328   ! <- R1 node NLRI
*>i[V][L2][I0x0][N[c65100][b0.0.0.0][s0000.0000.0002.00]]/328   ! <- R2 node NLRI
*>i[V][L2][I0x0][N[c65100][b0.0.0.0][s0000.0000.0003.00]]/328   ! <- R3 node NLRI
*>i[V][L2][I0x0][N[c65100][b0.0.0.0][s0000.0000.0004.00]]/328   ! <- R4 node NLRI
```

### PCEP session and delegated LSP

```bash
RP/0/RP0/CPU0:R1# show segment-routing traffic-eng pcc ipv4 peer
PCC's peer database:
-------------------------------------
 Peer address: 10.0.0.99
   State up                      ! <- session UP
   Capabilities: Stateful, Update, Segment-Routing

RP/0/RP0/CPU0:R1# show segment-routing traffic-eng policy color 30 detail
SR-TE policy database
---------------------
Color: 30, End-point: 10.0.0.3
  ...
  Candidate-paths:
    Preference: 100 (PCEP) (active)        ! <- PCEP-delegated, active
      Computation Type: PCEP               ! <- centrally computed
      Segment-List: 0x...
        SID[0]: 16002                       ! <- SID stack pushed from PCE
        SID[1]: 16003
```

### SRLG interface assignment

```bash
RP/0/RP0/CPU0:R1# show srlg interface brief
Interface                 SRLG Names
GigabitEthernet0/0/0/0    SRLG_L1                ! <- link-1 SRLG bound on R1
GigabitEthernet0/0/0/1    SRLG_L4                ! <- link-4 SRLG bound on R1
GigabitEthernet0/0/0/2    SRLG_L5                ! <- link-5 SRLG bound on R1
```

### Tree SID control-plane state

```bash
RP/0/RP0/CPU0:PCE# show segment-routing traffic-eng p2mp policy
SR-TE P2MP policy database
--------------------------
Policy: TREE_1
  Color: 100  Endpoint: 10.0.0.1            ! <- root reachable, color matches
  Admin state: up                            ! <- control plane converged
  Operational state: up
```

---

## 7. Verification Cheatsheet

### BGP-LS Session

```
router bgp <AS>
 address-family link-state link-state
 !
 neighbor <peer-loopback>
  remote-as <AS>
  update-source Loopback0
  address-family link-state link-state
```

| Command | Purpose |
|---------|---------|
| `address-family link-state link-state` | Activates the BGP-LS AFI/SAFI |
| `neighbor X address-family link-state link-state` | Activates BGP-LS only for this peer |
| `update-source Loopback0` | Sources the iBGP-LS session from the loopback |

> **Exam tip:** BGP-LS is `link-state link-state` (AFI=link-state, SAFI=link-state) - both keywords required.

### PCC Configuration

```
segment-routing
 traffic-eng
  pcc
   pce address ipv4 <pce-loopback>
```

| Command | Purpose |
|---------|---------|
| `pcc / pce address ipv4` | Tells the PCC where to find the PCE |
| `dynamic / pcep` (under candidate-path) | Per-policy delegation to the PCE |

### SRLG

```
srlg
 interface <intf>
  name <SRLG_NAME>
```

| Command | Purpose |
|---------|---------|
| `srlg / interface X / name N` | Assigns SRLG group N to interface X |

> **Exam tip:** SRLG group names must match on both link endpoints to be useful.

### Tree SID

```
pce
 address ipv4 <pce-loopback>
 segment-routing
  traffic-eng

segment-routing
 traffic-eng
  p2mp
   policy <NAME>
    color <C> endpoint ipv4 <root-loopback>
    candidate-paths
     preference 100
      dynamic
```

| Command | Purpose |
|---------|---------|
| `pce / address ipv4` | Defines PCE listener identity |
| `p2mp / policy / color C endpoint ipv4 R` | P2MP policy, root R, color C |

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show bgp link-state link-state summary` | Neighbor Established, non-zero PfxRcd |
| `show bgp link-state link-state` | Node and link NLRIs visible |
| `show pce session` | PCC clients connected |
| `show pce lsp` | Delegated LSPs UP |
| `show segment-routing traffic-eng pcc ipv4 peer` | PCC reports PCE peer up |
| `show segment-routing traffic-eng policy color N detail` | Computation Type: PCEP, SID list non-empty |
| `show srlg interface brief` | Each core interface lists its SRLG group |
| `show segment-routing traffic-eng p2mp policy` | Tree SID policy admin/oper state up |

### Common PCE/SRLG/Tree SID Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| BGP-LS neighbor stuck in Idle/Active | PCE loopback not reachable - missing static or redistribution on R2 |
| PCE topology has fewer nodes than IS-IS | `metric-style wide` missing on R2 - TE attrs absent in BGP-LS NLRI |
| PCC session never reaches up | Wrong PCE address in PCC config or TCP/4189 unreachable |
| Disjoint policy reports `no path` | All links share one SRLG group, or group-id collision between unrelated policies |
| Tree SID admin up but oper down | Leaf PCC sessions not up - check Task 3 first |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: PCE reachability and BGP-LS bring-up

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
prefix-set PCE_LOOPBACK
 10.0.0.99/32
end-set
!
route-policy STATIC_TO_ISIS
 if destination in PCE_LOOPBACK then
  pass
 else
  drop
 endif
end-policy
!
router static
 address-family ipv4 unicast
  10.0.0.99/32 10.1.29.99
 !
!
router isis CORE
 address-family ipv4 unicast
  redistribute static route-policy STATIC_TO_ISIS
 !
!
router bgp 65100
 address-family link-state link-state
 !
 neighbor 10.0.0.99
  remote-as 65100
  update-source Loopback0
  description iBGP-LS to PCE
  address-family link-state link-state
  !
 !
!
```

</details>

<details>
<summary>Click to view PCE Configuration</summary>

```bash
! PCE
router static
 address-family ipv4 unicast
  10.0.0.0/24 10.1.29.2
 !
!
router bgp 65100
 bgp router-id 10.0.0.99
 address-family link-state link-state
 !
 neighbor 10.0.0.2
  remote-as 65100
  update-source Loopback0
  description iBGP-LS to R2
  address-family link-state link-state
  !
 !
!
```

</details>

### Task 3: PCEP client configuration on R1, R3, R4

<details>
<summary>Click to view PCC Configuration (apply on R1, R3, R4)</summary>

```bash
segment-routing
 traffic-eng
  pcc
   pce address ipv4 10.0.0.99
  !
 !
!
```

</details>

### Task 4: Delegate the color-30 SR-TE policy to the PCE

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  policy COLOR_30
   color 30 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      pcep
      !
      metric type te
     !
    !
   !
  !
 !
!
```

</details>

### Task 5: SRLG on every core link

<details>
<summary>Click to view SRLG Configuration (R1)</summary>

```bash
! R1
srlg
 interface GigabitEthernet0/0/0/0
  name SRLG_L1
 !
 interface GigabitEthernet0/0/0/1
  name SRLG_L4
 !
 interface GigabitEthernet0/0/0/2
  name SRLG_L5
 !
!
```

</details>

<details>
<summary>Click to view SRLG Configuration (R2)</summary>

```bash
! R2
srlg
 interface GigabitEthernet0/0/0/0
  name SRLG_L1
 !
 interface GigabitEthernet0/0/0/1
  name SRLG_L2
 !
!
```

</details>

<details>
<summary>Click to view SRLG Configuration (R3)</summary>

```bash
! R3
srlg
 interface GigabitEthernet0/0/0/0
  name SRLG_L2
 !
 interface GigabitEthernet0/0/0/1
  name SRLG_L3
 !
 interface GigabitEthernet0/0/0/2
  name SRLG_L5
 !
!
```

</details>

<details>
<summary>Click to view SRLG Configuration (R4)</summary>

```bash
! R4
srlg
 interface GigabitEthernet0/0/0/0
  name SRLG_L3
 !
 interface GigabitEthernet0/0/0/1
  name SRLG_L4
 !
!
```

</details>

### Task 6: SRLG-aware disjoint policy pair

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  policy COLOR_40_PRIMARY
   color 40 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      pcep
      !
      metric type igp
      constraints
       disjoint-path group-id 1 type link
      !
     !
    !
   !
  !
  policy COLOR_40_BACKUP
   color 41 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      pcep
      !
      metric type igp
      constraints
       disjoint-path group-id 1 type link
      !
     !
    !
   !
  !
 !
!
```

</details>

### Task 7: Tree SID P2MP

<details>
<summary>Click to view PCE Configuration</summary>

```bash
! PCE
pce
 address ipv4 10.0.0.99
 segment-routing
  traffic-eng
  !
 !
!
segment-routing
 traffic-eng
  p2mp
   policy TREE_1
    color 100 endpoint ipv4 10.0.0.1
    candidate-paths
     preference 100
      dynamic
      !
     !
    !
   !
  !
 !
!
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show bgp link-state link-state summary
show bgp link-state link-state
show pce session
show pce lsp
show pce lsp detail
show segment-routing traffic-eng pcc ipv4 peer
show segment-routing traffic-eng policy color 30 detail
show segment-routing traffic-eng policy color 40 detail
show srlg interface brief
show segment-routing traffic-eng p2mp policy
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                 # reset to known-good
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # bring lab to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # restore between tickets
```

---

### Ticket 1 — PCE topology reports fewer link attributes than IS-IS

The NOC reports that the PCE's BGP-LS topology shows every node and every link, but `show bgp link-state link-state detail` is missing TE attributes (admin-weight, IGP metric, SRLG sub-TLV) on a subset of links. As a consequence, every PCEP-delegated policy on R1 falls back to a generic shortest path; SRLG-disjoint computation fails with "constraint not satisfiable."

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show bgp link-state link-state detail` on PCE shows full TE sub-TLVs (metric, admin weight, SRLG) on every link NLRI; PCE-delegated policies recover.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On PCE, `show bgp link-state link-state detail | i SRLG|TE Default|Admin` and note which links are missing TE attributes.
2. On the originator R2, inspect `show isis interface | i Metric Style` and `show running-config router isis CORE address-family ipv4 unicast`.
3. If R2's IS-IS AF has reverted to narrow metric-style, IS-IS stops advertising TE/SRLG sub-TLVs - so BGP-LS forwards a topology without TE attributes to PCE.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
router isis CORE
 address-family ipv4 unicast
  metric-style wide
 !
!
```

After the fix, `show bgp link-state link-state detail` on PCE redisplays full TE sub-TLVs within ~30 seconds.

</details>

---

### Ticket 2 — PCC reports PCE session stuck connecting

R1's color-30 SR-TE policy is in `Down (Computation pending)` state. Operations confirms the PCC session log on R1 cycles through TCP-connect attempts but never reaches `up`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show segment-routing traffic-eng pcc ipv4 peer` on R1 shows the PCE peer `up`, color-30 policy returns to UP with a SID list.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, `show segment-routing traffic-eng pcc ipv4 peer` lists the PCE address. Confirm it matches `10.0.0.99` exactly.
2. On R1, `ping 10.0.0.99 source Loopback0`. If pings succeed but the PCC peer address differs from 10.0.0.99, the PCC was misconfigured.
3. On PCE, `show pce session` should list R1 as a connected client; if R1 is absent, PCEP TCP never reached PCE.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
segment-routing
 traffic-eng
  pcc
   no pce address ipv4 10.0.0.98
   pce address ipv4 10.0.0.99
  !
 !
!
```

</details>

---

### Ticket 3 — Disjoint policy pair reports "no path"

The color-40/41 disjoint policy pair on R1 was UP at end of Task 6. After the latest config push, both policies report `Down (no path satisfying constraints)`. PCE log indicates "disjoint constraint not satisfiable."

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show segment-routing traffic-eng policy color 40 detail` and `... color 41 detail` on R1 are both UP with non-overlapping SID lists.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1 and R2, `show srlg interface brief` and confirm the SRLG group names assigned to L1 (Gi0/0/0/0). Same group name on both endpoints is required for SRLG-aware CSPF.
2. If R2 reports SRLG_L4 on its Gi0/0/0/0 (mismatch with R1's SRLG_L1) the SRLG topology fed to PCE is inconsistent and PCE cannot find any pair of paths that share zero SRLGs.
3. `show pce lsp detail` on PCE confirms reason: disjoint not satisfiable.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
srlg
 interface GigabitEthernet0/0/0/0
  no name SRLG_L4
  name SRLG_L1
 !
!
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] PCE reachable from R1, R3, R4 (10.0.0.99 pings from each PCC's loopback)
- [ ] BGP-LS session R2 ↔ PCE Established with non-zero PfxRcd
- [ ] PCE topology: 4 node NLRIs and at least 5 link NLRIs visible
- [ ] PCEP sessions UP on R1, R3, R4 (`show pce session` lists all three)
- [ ] Color-30 policy on R1 reports `Computation Type: PCEP`
- [ ] SRLG group names present on every core interface of R1-R4
- [ ] Color-40 + color-41 policies on R1 both UP with disjoint SID lists
- [ ] Tree SID `TREE_1` admin/oper state up on PCE

### Troubleshooting

- [ ] Ticket 1 diagnosed and fixed (`metric-style wide` restored on R2)
- [ ] Ticket 2 diagnosed and fixed (PCC PCE address corrected to 10.0.0.99)
- [ ] Ticket 3 diagnosed and fixed (R2 L1 SRLG group name aligned to SRLG_L1)
- [ ] Lab restored to known-good with `apply_solution.py` after each ticket

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
