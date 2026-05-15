# Lab 05 — OSPF Segment Routing Extensions (Standalone)

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

**Exam Objective:** 4.2.a — Implement SR routing protocol extensions (OSPF)

Blueprint bullet 4.2.a lists three IGPs: BGP (via BGP-LS in lab-04), IS-IS (labs 00-04), and OSPF. This lab closes the OSPF gap. Starting from a clean interfaces-only baseline, you'll bring up OSPFv2 area 0 on the same four-router core used throughout this topic, enable SR under OSPF, assign prefix SIDs using the same indices as lab-00 (index 1-4 → labels 16001-16004), and verify that `traceroute mpls` output mirrors the IS-IS version exactly. The data plane doesn't care whether the SID came from IS-IS or OSPF — the label forwarding logic is identical.

### The Problem This Lab Solves

CCNP SPRI blueprint bullet 4.2.a says "implement SR routing protocol extensions" — plural. Labs 00-04 cover IS-IS SR in depth, but OSPF SR is tested on the exam and must be configured end-to-end at least once. The exam draws explicit distinctions: IS-IS uses TLV 135 sub-TLVs inside LSPs; OSPF uses RFC 7684 Opaque type-7 LSAs flooded within an area. **Running OSPF SR on the same four-router core with the same SRGB and the same prefix SID indices proves that the MPLS forwarding plane is IGP-agnostic — `traceroute mpls` output is byte-for-byte identical regardless of which protocol distributed the labels.**

| Piece | Role in the overall goal |
|-------|---------------------------|
| **OSPF Opaque LSAs (type 7)** | The alternate distribution channel — carries the same prefix SID information as IS-IS TLV 135, but in RFC 7684 Extended Prefix LSAs flooded at area scope |
| **SRGB and prefix SID arithmetic** | The universal label language — every router computes the same absolute label (SRGB_base + index) from the same inputs, identical to IS-IS SR computation |
| **Point-to-point network type** | The clean config baseline — eliminates DR/BDR election overhead on core links so adjacency formation mirrors IS-IS point-to-point behaviour |
| **OSPF vs. IS-IS comparison** | The proof — you inspect Opaque LSA sub-TLVs side-by-side with lab-00's IS-IS LSP output and confirm the data plane outcome is identical |

**Analogy — two dispatch systems, same shipping labels.** A trucking company runs two dispatch systems in parallel on separate test networks:

- Dispatcher-A (**IS-IS**) prints labels by embedding destination codes inside a "TLV-135 envelope" that every depot receives simultaneously.
- Dispatcher-B (**OSPF**) prints labels by embedding the same destination codes inside an "Opaque type-7 envelope" that floods within a single warehouse zone (area 0).

The drivers (the **MPLS data plane**) don't care which dispatcher handed them the label. They read the destination code, compute the route, and deliver the package. The proof that both dispatch systems work is the `traceroute mpls` output — if the hop-by-hop path is identical, the label distribution mechanism is irrelevant to the forwarding outcome.

Every subsection below is one of these pieces. Section 5 (Lab Challenge) is wiring them together end-to-end.

### OSPF Segment Routing Extensions

*The alternate distribution channel from the analogy — how OSPF carries the same SID information as IS-IS, but inside RFC 7684 Opaque LSAs instead of TLV 135 sub-TLVs.*

SR-MPLS requires that every router in the domain know every other router's prefix SID. In IS-IS, this information travels inside IS-IS LSP sub-TLVs (Extended IP Reachability TLV 135, with a Prefix-SID sub-sub-TLV). OSPF uses a different mechanism: **RFC 7684 Opaque LSAs** extended by **RFC 8665** for SR.

The relevant Opaque LSA structure for OSPFv2 SR:

| LSA Type | Opaque Type | RFC | Carries |
|----------|-------------|-----|---------|
| 10 (area scope) | 7 | RFC 7684 | Extended Prefix TLV → Prefix SID sub-TLV |
| 10 (area scope) | 8 | RFC 7684 | Extended Link TLV → Adjacency SID sub-TLV |

When you configure `prefix-sid index 1` on R1's loopback under OSPF, R1 originates an Opaque type-7 LSA advertising: "my loopback 10.0.0.1/32 has prefix SID index 1." Every other router in area 0 receives this LSA, computes `SRGB_base + index = 16000 + 1 = 16001`, and programs MPLS label 16001 in its LFIB with a swap/pop action toward R1.

In IOS-XR, you view these with:
```
show ospf database opaque-area
```

The output shows LSA type 10 entries with opaque type 7 (prefix) and 8 (link). Compare to IS-IS:
```
show isis database detail
```
which shows sub-TLV 135 with embedded SID sub-sub-TLVs. Same payload, different distribution protocol.

### SRGB and Prefix SID Index Arithmetic

*The universal label language from the analogy — how every router independently computes the same absolute label from SRGB + index, identically to IS-IS SR.*

The **Segment Routing Global Block (SRGB)** is a contiguous label range reserved on every node in the SR domain. IOS-XR default is 16000-23999 (8000 labels). The SRGB is configured globally and distributed by the IGP to every other router.

Prefix SID allocation works by index, not by absolute label:
- R1 configures `prefix-sid index 1` → advertises index 1 to OSPF
- R2 looks up R1's SRGB (16000-23999), computes 16000 + 1 = **16001**, programs this as the label to use for traffic destined to R1's loopback
- The computation is symmetric — every router with the same SRGB computes the same label for a given node, enabling consistent label planes without label negotiation

This is fundamentally different from LDP: LDP assigns labels locally per-FEC and exchanges them per-session. SR advertises a global index and every router independently computes the label from that index and its own known SRGB.

### OSPFv2 Point-to-Point Network Type for SP Links

*The clean config baseline from the analogy — eliminating DR/BDR overhead so OSPF adjacency formation mirrors IS-IS point-to-point behaviour.*

In SP deployments, core links are almost always configured as point-to-point under OSPF (`network point-to-point` under the OSPF interface config). This:
- Eliminates DR/BDR election (pointless overhead on a two-router link)
- Makes adjacency formation faster and more predictable
- Applies cleanly to the /24 addressing used in this lab (subnets are routed, not broadcast-domain)

On IOS-XR, the interface network type is set inside the OSPF area interface block:
```
router ospf 1
 area 0
  interface GigabitEthernet0/0/0/0
   network point-to-point
```

### The "Pick One IGP" Production Rule

*The proof from the analogy — this lab validates OSPF SR capability, not dual-IGP deployment, which would cause administrative distance conflicts and label churn in production.*

This lab exists to prove a capability, not to recommend a deployment pattern. In production, SR networks run **either IS-IS or OSPF** as their IGP — never both simultaneously on the same interfaces. Running dual IGPs causes:
- Administrative distance fights when both IGPs install routes for the same prefix
- Label churn: if IS-IS and OSPF compute different next-hops for the same destination, SR labels programmed from each may conflict
- Operational complexity: two protocol databases, two sets of adjacencies, two sets of timers

The exam tests whether you know OSPF SR extension syntax (4.2.a) and that the data plane outcome is identical to IS-IS SR. Lab-05 proves both points cleanly because it runs OSPF SR in isolation, with no IS-IS in the picture.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| OSPFv2 area 0 on IOS-XRv 9000 | Bring up OSPF neighborships on a four-router ring with a diagonal link |
| SR enablement under OSPF | Configure `segment-routing mpls` and SRGB on IOS-XR OSPF process |
| Prefix SID allocation | Assign per-node SID indices under OSPF area interface config |
| Opaque LSA inspection | Read Extended Prefix LSAs (opaque type 7/8) to verify SID distribution |
| End-to-end SR forwarding verification | Confirm MPLS traceroute hops match expected SR label forwarding |
| OSPF vs. IS-IS SR comparison | Contrast LSA/LSP propagation and sub-TLV encoding between the two IGPs |

---

## 2. Topology & Scenario

**Scenario:** SP-CORE's lab team wants to validate that the SR data plane is truly IGP-agnostic before committing to a future migration from IS-IS to OSPF on the production backbone. Your task is to build an OSPF SR test bed on the standard four-router core, allocate the same prefix SIDs that the IS-IS environment uses, and confirm that MPLS traceroute output is byte-for-byte equivalent.

```
                    ┌────────────────────────┐
                    │           R1           │
                    │  (SP Edge / SR Ingress)│
                    │   Lo0: 10.0.0.1/32     │
                    │   SID index: 1 (16001) │
                    └───┬──────┬──────┬──────┘
                        │      │      │
           Gi0/0/0/0    │      │      │ Gi0/0/0/2
          10.1.12.1/24  │      │      │ 10.1.13.1/24
          L1 (R1-R2)    │      │      │ L5 diagonal (R1-R3)
                        │      │      │
          Gi0/0/0/1     │      │
          10.1.14.1/24  │      │
          L4 (R1-R4)    │      │
                        │      │
         ┌──────────────┘      └──────────────────────────┐
         │                                                 │
┌────────┴───────────┐                        ┌───────────┴────────────┐
│        R4          │                        │           R2           │
│   (SP Core)        │                        │      (SP Core)         │
│  Lo0: 10.0.0.4/32  │                        │   Lo0: 10.0.0.2/32     │
│  SID index: 4      │                        │   SID index: 2 (16002) │
│        (16004)     │                        └───────────┬────────────┘
└────────┬───────────┘                                    │
  Gi0/0/0/0│                                    Gi0/0/0/1 │ 10.1.23.2/24
 10.1.34.4/24│ L3 (R4-R3)                      L2 (R2-R3) │
             │                                             │
         ┌───┴──────────────────────────────────┬─────────┘
         │                                      │
┌────────┴───────────────────────────────────────────────────┐
│                           R3                               │
│             (SP Edge / SR Egress)                          │
│                 Lo0: 10.0.0.3/32                           │
│                 SID index: 3 (16003)                       │
└────────────────────────────────────────────────────────────┘

Gi0/0/0/0: 10.1.23.3/24 (L2 to R2)
Gi0/0/0/1: 10.1.34.3/24 (L3 to R4)
Gi0/0/0/2: 10.1.13.3/24 (L5 diagonal to R1)
```

**Key relationships:**
- Ring: R1-R2-R3-R4-R1 (L1, L2, L3, L4). Diagonal L5 (R1↔R3) provides redundancy.
- All links are /24, point-to-point under OSPF — no DR/BDR election.
- SRGB 16000-23999 on all nodes; prefix SID indices 1-4 → absolute labels 16001-16004.
- No IS-IS, no LDP, no CE edges — pure OSPF SR standalone.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | SP Edge / SR Ingress | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 | 16 GB |
| R2 | SP Core | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 | 16 GB |
| R3 | SP Edge / SR Egress | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 | 16 GB |
| R4 | SP Core | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 | 16 GB |

> **Boot note:** IOS-XRv 9000 nodes take 8-12 minutes to fully boot. Wait for the
> `RP/0/0/CPU0:<hostname>#` prompt on all nodes before running `setup_lab.py`.
>
> **Platform flexibility:** Labs 00, 01, 02, and 05 can run on Classic IOS-XRv 6.3.1
> (`xrv-k9-demo-6.3.1`, 4 GB RAM) as a lighter alternative to IOS-XRv 9000
> (16 GB RAM). All OSPF SR features (prefix SIDs, SRGB, TI-LFA) work correctly on
> Classic XRv. **Labs 03 and 04 require IOS-XRv 9000** — Classic XRv does not
> support SR-TE policies, PCE, Tree SID, or SRLG.

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, SR prefix SID source |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, SR prefix SID source |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, SR prefix SID source |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, SR prefix SID source |

### Cabling

| Link ID | Source | Interface | Target | Interface | Subnet |
|---------|--------|-----------|--------|-----------|--------|
| L1 | R1 | Gi0/0/0/0 | R2 | Gi0/0/0/0 | 10.1.12.0/24 |
| L2 | R2 | Gi0/0/0/1 | R3 | Gi0/0/0/0 | 10.1.23.0/24 |
| L3 | R3 | Gi0/0/0/1 | R4 | Gi0/0/0/0 | 10.1.34.0/24 |
| L4 | R1 | Gi0/0/0/1 | R4 | Gi0/0/0/1 | 10.1.14.0/24 |
| L5 | R1 | Gi0/0/0/2 | R3 | Gi0/0/0/2 | 10.1.13.0/24 |

### Console Access

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames (R1, R2, R3, R4)
- Interface IP addressing on all five core links (L1-L5) and all loopbacks
- Interface descriptions referencing the link IDs

**IS NOT pre-loaded** (student configures this):
- OSPF routing process and area 0 assignments
- SRGB (Segment Routing Global Block)
- SR enablement under OSPF
- Per-node prefix SID allocations on each loopback

---

## 5. Lab Challenge: Core Implementation

### Task 1: OSPFv2 Area 0 Neighborships

- Bring up an OSPFv2 process (process ID 1) on all four routers.
- Configure each router with an explicit router ID equal to its loopback address (10.0.0.X/32 → router-id 10.0.0.X).
- Include all five core links (L1-L5) and all loopback interfaces in area 0. Set loopbacks as passive interfaces.
- Configure all core link interfaces as point-to-point network type to eliminate DR/BDR overhead.

**Verification:** `show ospf neighbor` on each router must show all adjacent neighbors in FULL state. R1 must show three neighbors (R2, R3, R4); R2 must show two (R1, R3); R3 must show three (R1, R2, R4); R4 must show two (R1, R3).

---

### Task 2: SRGB and SR Enablement

- Configure the Segment Routing Global Block as 16000 to 23999 on all four routers. This is the Cisco IOS-XR default range and matches all other labs in this topic.
- Enable segment routing MPLS mode under the OSPF process on all four routers.

**Verification:** `show ospf segment-routing` must confirm SR is active and show the configured SRGB range. `show mpls label range` should reflect the SRGB allocation.

---

### Task 3: Per-Node Prefix SID Allocation

- Assign a prefix SID index to each router's loopback interface within the OSPF area 0 interface configuration. Use the same index scheme as lab-00: R1=index 1, R2=index 2, R3=index 3, R4=index 4. These map to absolute labels 16001, 16002, 16003, 16004 respectively.
- After configuration, verify that all four routers' prefix SIDs appear in the OSPF database on every peer.
- Verify that the MPLS label forwarding table contains entries for all four loopbacks using SR labels, not LDP labels.
- From R1, run an MPLS traceroute to R3's loopback (10.0.0.3/32) and confirm the path uses SR label 16003, swapped at each transit LSR, with a PHP pop at the penultimate hop (R2 or R4 depending on IGP path chosen).

**Verification:** `show ospf database opaque-area` on any router must show Opaque type-7 LSAs for each node's loopback with embedded prefix SID data. `show mpls forwarding labels 16001 16004` must show MPLS entries for all four SIDs. `traceroute mpls ipv4 10.0.0.3/32 source Loopback0` from R1 must resolve a complete hop-by-hop path.

---

### Task 4: OSPF SR LSA Inspection and IS-IS Comparison

- Examine the OSPF database in detail to locate the Opaque LSA carrying R3's prefix SID. Identify the LSA type (10), opaque type (7), and the encoded prefix SID index value.
- Note the Router ID of the originating router and the LSA age in the database. Compare what you see here to the IS-IS sub-TLV structure from lab-00's `show isis database detail` output: same SID information, different encapsulation.
- Document the key difference in flood scope: IS-IS LSPs flood domain-wide (no concept of area in IS-IS L2). OSPF type-10 Opaque LSAs flood only within an area — this is why the troubleshooting scenario (R3 in area 1) causes R3's SID to disappear from R1's view.
- Observe the timing of SID propagation after a `no prefix-sid / prefix-sid` toggle on one router: record the time between configuration change and database update. Compare to a similar flip in IS-IS.

**Verification:** `show ospf database opaque-area detail` on R1 must show an Opaque LSA for 10.0.0.3/32 with `Opaque Type: 7`, a `Prefix-SID Sub-TLV` entry, and `SID Index: 3`. The LSA age should be recent (seconds old after the configuration is applied).

---

## 6. Verification & Analysis

### Task 1: OSPFv2 Neighborships

```
RP/0/0/CPU0:R1# show ospf neighbor

* Indicates MADJ interface
# Indicates Neighbor awaiting BFD session up

Neighbors for OSPF 1

Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/  -        00:00:37    10.1.12.2       GigabitEthernet0/0/0/0   ! ← R2 FULL (point-to-point: no DR role)
10.0.0.4          1   FULL/  -        00:00:39    10.1.14.4       GigabitEthernet0/0/0/1   ! ← R4 FULL
10.0.0.3          1   FULL/  -        00:00:38    10.1.13.3       GigabitEthernet0/0/0/2   ! ← R3 FULL via L5 diagonal

Total neighbor count: 3
```

### Task 2: SR Enablement

```
RP/0/0/CPU0:R1# show ospf segment-routing

        OSPF Router with ID (10.0.0.1) (Process ID 1)

Segment Routing Global Block (SRGB):
  Range: 16000-23999, Size: 8000    ! ← correct range, all 8000 labels available
  Label type: MPLS

Segment Routing: ENABLED            ! ← SR active under this OSPF process
Forwarding: MPLS forwarding enabled
```

### Task 3: Prefix SIDs and MPLS Forwarding

```
RP/0/0/CPU0:R2# show ospf database opaque-area

            OSPF Router with ID (10.0.0.2) (Process ID 1)

                Type-10 Opaque Area Link States (Area 0)

  LS age: 45
  LS Type: Opaque Area Link
  Opaque Type: 7 (Extended Prefix)   ! ← opaque type 7 = Extended Prefix LSA
  Opaque ID: 1
  Advertising Router: 10.0.0.1       ! ← R1 originated this LSA
  ...
  TLV Type: Extended Prefix          ! ← prefix TLV
    Address: 10.0.0.1/32
    Sub-TLV Type: Prefix-SID
      Flags: (None)
      SRGB Relative Index: 1         ! ← index 1 → label 16001 with SRGB base 16000
      SRGB Index Range: 8000
```

```
RP/0/0/CPU0:R1# show mpls forwarding labels 16001 16004

Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
16001  Pop         SR Pfx (idx 1)     Lo0          point2point     0           ! ← R1 pops its own SID (PHP)
16002  16002       SR Pfx (idx 2)     Gi0/0/0/0    10.1.12.2       0           ! ← swap to R2 via L1
16003  16003       SR Pfx (idx 3)     Gi0/0/0/2    10.1.13.3       0           ! ← swap to R3 via L5 diagonal
16004  16004       SR Pfx (idx 4)     Gi0/0/0/1    10.1.14.4       0           ! ← swap to R4 via L4
```

```
RP/0/0/CPU0:R1# traceroute mpls ipv4 10.0.0.3/32 source Loopback0

Tracing MPLS Label Switched Path targeting 10.0.0.3/32, timeout is 2 seconds

Codes: '!' - success, 'Q' - request not sent, '.' - timeout,
  'L' - labeled output interface, 'B' - unlabeled output interface,
  'D' - DS Map mismatch, 'F' - no FEC mapping, 'f' - FEC mismatch,
  'M' - malformed request, 'm' - unsupported tlvs, 'N' - no label entry,
  'P' - no rx intf label prot, 'p' - premature termination of LSP,
  'R' - transit router, 'I' - unknown upstream index,
  'X' - unknown return code, 'x' - return code 0

Type escape sequence to abort.

  0 10.0.0.1 MRU 1500 [Labels: 16003 Exp: 0]  ! ← R1 pushes SR label 16003 for R3's loopback
L 1 10.1.13.3 MRU 1500 [Labels: implicit-null Exp: 0] 5 ms  ! ← R3 is directly adjacent via L5; penultimate pops (PHP)
! 2 10.0.0.3 5 ms                                              ! ← R3 receives native IP — label forwarding complete
```

### Task 4: OSPF vs. IS-IS LSA/LSP Timing

After toggling a prefix-sid on R4 (`no prefix-sid index 4` then `prefix-sid index 4`), check database convergence:

```
RP/0/0/CPU0:R1# show ospf database opaque-area | include age
  LS age: 3     ! ← R4's Extended Prefix LSA just refreshed; ~3 seconds after config change
```

In IS-IS (from lab-00 notes), the equivalent toggle converged in 1-2 seconds via LSP flooding.
Both protocols converge in the same time range — the choice of OSPF vs. IS-IS has no material
impact on SR SID propagation latency in this four-router topology.

---

## 7. Verification Cheatsheet

### OSPF Process Configuration (IOS-XR)

```
router ospf 1
 router-id 10.0.0.X
 segment-routing mpls
 area 0
  interface Loopback0
   passive enable
   prefix-sid index N
  !
  interface GigabitEthernet0/0/0/X
   network point-to-point
  !
 !
!
```

| Command | Purpose |
|---------|---------|
| `segment-routing mpls` | Enable SR MPLS mode under this OSPF process |
| `prefix-sid index N` | Allocate prefix SID index N for this interface's prefix |
| `passive enable` | Suppress hellos on loopback — still advertises the prefix |
| `network point-to-point` | Skip DR/BDR election on this link |

> **Exam tip:** In IOS-XR, prefix SIDs are configured under the OSPF area interface block — not globally or under `router ospf` directly. This differs from the way some IOS-XE documentation presents the config.

### SRGB Configuration

```
segment-routing
 global-block 16000 23999
!
```

| Command | Purpose |
|---------|---------|
| `global-block 16000 23999` | Reserve MPLS labels 16000-23999 as the SRGB |

> **Exam tip:** The SRGB must be identical across all nodes in the SR domain. Mismatched SRGBs cause label computation errors — each router derives absolute labels using the *remote* router's SRGB base + locally received index.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ospf neighbor` | All adjacencies in FULL state; no DR role shown for p2p links |
| `show ospf segment-routing` | SR ENABLED; SRGB range 16000-23999; size 8000 |
| `show ospf database opaque-area` | Opaque Type 7 LSAs — one per node advertising its loopback SID |
| `show ospf database opaque-area detail` | Prefix-SID sub-TLV with correct SRGB Relative Index |
| `show mpls forwarding labels 16001 16004` | SR swap/pop entries for all four loopback SIDs |
| `show ospf segment-routing` | SR state and prefix-SID bindings from local OSPF SR database |
| `traceroute mpls ipv4 10.0.0.3/32 source Loopback0` | Complete hop-by-hop SR path to R3; PHP at penultimate |

### Common OSPF SR Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No OSPF neighbors on a link | Interface not in area 0, or `passive enable` set on non-loopback |
| Prefix SID absent from `show ospf database opaque-area` | `prefix-sid index N` missing, or interface in wrong area |
| MPLS forwarding entry shows LDP label instead of SR | `segment-routing mpls` missing under OSPF process |
| SRGB conflict log on one node | `global-block` range differs from peers; check `show mpls label range` |
| `traceroute mpls` shows only one hop | PHP is correct — penultimate node pops the label; the egress node sees native IP |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: OSPFv2 Area 0 Neighborships

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospf 1
 router-id 10.0.0.1
 area 0
  interface Loopback0
   passive enable
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/1
   network point-to-point
  !
  interface GigabitEthernet0/0/0/2
   network point-to-point
  !
 !
!
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 router-id 10.0.0.2
 area 0
  interface Loopback0
   passive enable
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/1
   network point-to-point
  !
 !
!
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospf 1
 router-id 10.0.0.3
 area 0
  interface Loopback0
   passive enable
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/1
   network point-to-point
  !
  interface GigabitEthernet0/0/0/2
   network point-to-point
  !
 !
!
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 router-id 10.0.0.4
 area 0
  interface Loopback0
   passive enable
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/1
   network point-to-point
  !
 !
!
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospf neighbor
show ospf interface brief
```
</details>

---

### Task 2: SRGB and SR Enablement

<details>
<summary>Click to view All Devices Configuration</summary>

```bash
! R1, R2, R3, R4 — identical SRGB config on all
segment-routing
 global-block 16000 23999
!

! Add segment-routing mpls under the OSPF process (all routers)
router ospf 1
 segment-routing mpls
!
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospf segment-routing
show mpls label range
```
</details>

---

### Task 3: Per-Node Prefix SID Allocation

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospf 1
 area 0
  interface Loopback0
   prefix-sid index 1
  !
 !
!
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 area 0
  interface Loopback0
   prefix-sid index 2
  !
 !
!
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospf 1
 area 0
  interface Loopback0
   prefix-sid index 3
  !
 !
!
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 area 0
  interface Loopback0
   prefix-sid index 4
  !
 !
!
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospf database opaque-area
show mpls forwarding labels 16001 16004
show ospf segment-routing
traceroute mpls ipv4 10.0.0.3/32 source Loopback0
```
</details>

---

### Task 4: OSPF SR LSA Inspection and IS-IS Comparison

<details>
<summary>Click to view Key Show Commands and What to Look For</summary>

```bash
! OSPF Extended Prefix LSA inspection (R2 viewing R1's SID)
RP/0/0/CPU0:R2# show ospf database opaque-area detail
! Look for: Opaque Type: 7, Advertising Router: 10.0.0.1
!           Prefix-SID Sub-TLV, SRGB Relative Index: 1

! IS-IS equivalent (from lab-00 reference)
RP/0/0/CPU0:R2# show isis database detail R1.00-00
! Look for: Extended IP Reachability TLV 135, SID sub-sub-TLV, Index: 1

! Toggle test — on R4, flip the prefix SID
RP/0/0/CPU0:R4# conf t
RP/0/0/CPU0:R4(config)# router ospf 1
RP/0/0/CPU0:R4(config-ospf)# area 0
RP/0/0/CPU0:R4(config-ospf-ar)# interface Loopback0
RP/0/0/CPU0:R4(config-ospf-ar-if)# no prefix-sid index 4
RP/0/0/CPU0:R4(config-ospf-ar-if)# commit
! Wait ~2 seconds, then restore
RP/0/0/CPU0:R4(config-ospf-ar-if)# prefix-sid index 4
RP/0/0/CPU0:R4(config-ospf-ar-if)# commit
! Check convergence on R1
RP/0/0/CPU0:R1# show ospf database opaque-area | include age
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                          # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — R3's Loopback Prefix SID Absent from All Peers

The NOC reports that MPLS traceroute from R1 to 10.0.0.3/32 fails — no SR label is being pushed for R3's loopback. IP reachability to R3 works fine, but `show mpls forwarding labels 16003` on R1 returns no entry.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ospf database opaque-area` on R1 shows an Opaque type-7 LSA originating from 10.0.0.3 with prefix SID index 3. `show mpls forwarding labels 16003` on R1 shows a valid swap/pop entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ospf database opaque-area` — look for LSA originating from 10.0.0.3. If it is absent or has no Prefix-SID sub-TLV, the fault is upstream of R1 (R3 not advertising).
2. On R3: `show ospf database opaque-area` — does R3's own database contain a type-7 LSA from itself? If not, R3 is not originating the LSA.
3. On R3: `show ospf interface` — check which area each interface is in. If R3's interfaces are in area 1 instead of area 0, type-10 area-scoped LSAs will not cross the area boundary.
4. On R3: `show ospf` — look at the area list. If R3 shows `Area 1` with no `Area 0`, the misconfiguration is confirmed.
5. Root cause: R3's OSPF area is configured as area 1. Type-10 Opaque LSAs (Extended Prefix) are area-scoped — they do not flood across area boundaries. R1 and R2 never see R3's SID advertisement.
</details>

<details>
<summary>Click to view Fix</summary>

On R3: move all OSPF interfaces (including Loopback0) from area 1 to area 0.

```bash
RP/0/0/CPU0:R3# conf t
RP/0/0/CPU0:R3(config)# router ospf 1
RP/0/0/CPU0:R3(config-ospf)# area 1
RP/0/0/CPU0:R3(config-ospf-ar)# no interface Loopback0
RP/0/0/CPU0:R3(config-ospf-ar)# no interface GigabitEthernet0/0/0/0
RP/0/0/CPU0:R3(config-ospf-ar)# no interface GigabitEthernet0/0/0/1
RP/0/0/CPU0:R3(config-ospf-ar)# no interface GigabitEthernet0/0/0/2
RP/0/0/CPU0:R3(config-ospf-ar)# exit
RP/0/0/CPU0:R3(config-ospf)# area 0
RP/0/0/CPU0:R3(config-ospf-ar)# interface Loopback0
RP/0/0/CPU0:R3(config-ospf-ar-if)# passive enable
RP/0/0/CPU0:R3(config-ospf-ar-if)# prefix-sid index 3
RP/0/0/CPU0:R3(config-ospf-ar-if)# exit
RP/0/0/CPU0:R3(config-ospf-ar)# interface GigabitEthernet0/0/0/0
RP/0/0/CPU0:R3(config-ospf-ar-if)# network point-to-point
RP/0/0/CPU0:R3(config-ospf-ar-if)# exit
RP/0/0/CPU0:R3(config-ospf-ar)# interface GigabitEthernet0/0/0/1
RP/0/0/CPU0:R3(config-ospf-ar-if)# network point-to-point
RP/0/0/CPU0:R3(config-ospf-ar-if)# exit
RP/0/0/CPU0:R3(config-ospf-ar)# interface GigabitEthernet0/0/0/2
RP/0/0/CPU0:R3(config-ospf-ar-if)# network point-to-point
RP/0/0/CPU0:R3(config-ospf-ar-if)# commit
```

Verify: `show ospf database opaque-area` on R1 now shows R3's type-7 Opaque LSA with index 3.
</details>

---

### Ticket 2 — R2's Loopback Label Missing from R1 and R3's Forwarding Tables

A monitoring script reports that MPLS OAM pings to 10.0.0.2/32 (label 16002) fail from both R1 and R3. R2's IP loopback is reachable via OSPF, but the SR label entry for it does not appear in any peer's MPLS forwarding table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show mpls forwarding labels 16002` on R1 and R3 both show a valid entry. `traceroute mpls ipv4 10.0.0.2/32 source Loopback0` from R1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ospf database opaque-area` — check for a type-7 LSA from 10.0.0.2. If absent, R2 is not advertising its prefix SID.
2. On R2: `show ospf database opaque-area` — R2's own database should have a self-originated type-7 LSA. If it does not, the `prefix-sid` config is missing on R2.
3. On R2: `show ospf` and `show ospf interface detail` for Loopback0. Look for "Prefix SID" in the output. Absence means the SID was never configured.
4. On R2: `show run router ospf` — check whether `prefix-sid index 2` is present under `area 0 / interface Loopback0`. If missing, that is the fault.
5. Root cause: R2's `prefix-sid index 2` is absent from its OSPF area interface configuration. No prefix SID sub-TLV is generated, no Opaque LSA is flooded, and no peer installs a label for R2's loopback.
</details>

<details>
<summary>Click to view Fix</summary>

On R2: add the missing prefix SID under OSPF area 0 Loopback0 interface.

```bash
RP/0/0/CPU0:R2# conf t
RP/0/0/CPU0:R2(config)# router ospf 1
RP/0/0/CPU0:R2(config-ospf)# area 0
RP/0/0/CPU0:R2(config-ospf-ar)# interface Loopback0
RP/0/0/CPU0:R2(config-ospf-ar-if)# prefix-sid index 2
RP/0/0/CPU0:R2(config-ospf-ar-if)# commit
```

Verify: `show mpls forwarding labels 16002` on R1 and R3 now shows a swap entry for R2's loopback.
</details>

---

### Ticket 3 — R4's SRGB Too Small — Label 16004 Rejected

A lab engineer reports that `show mpls forwarding labels 16004` returns no output on all routers except R4 itself, and that the OSPF database shows no Opaque type-7 LSA originating from R4. R4's loopback is reachable via OSPF IP forwarding, but all SR label entries for it are absent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ospf database opaque-area` on R1 shows R4's type-7 Opaque LSA with index 4. `show mpls forwarding labels 16004` on R1, R2, R3 all show a valid swap/pop entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show mpls label range` — check the SRGB start and end. If the range is smaller than 16000-23999 (for example 16000-16003), label 16004 is outside the SRGB and cannot be allocated as a prefix SID.
2. On R4: `show ospf segment-routing` — look at the "Range" field. A shrunken SRGB (e.g. 16000-16003, size 4) is confirmed here.
3. On R4: `show ospf database opaque-area` — R4's own view. If R4 has suppressed its own type-7 LSA because the SID index 4 falls outside its SRGB (4 > size 4 in a 0-indexed block of 4 labels), the LSA is absent.
4. On R4: `show run | include global-block` — the fault will be `global-block 16000 16003` instead of `global-block 16000 23999`.
5. Root cause: R4's SRGB is misconfigured with too small a range. Index 4 requires SRGB_base + 4 = 16004, but if the block ends at 16003, the label 16004 is not in the block. IOS-XR rejects the prefix SID allocation and does not originate the Opaque LSA.
</details>

<details>
<summary>Click to view Fix</summary>

On R4: correct the SRGB to the full 16000-23999 range.

```bash
RP/0/0/CPU0:R4# conf t
RP/0/0/CPU0:R4(config)# segment-routing
RP/0/0/CPU0:R4(config-sr)# global-block 16000 23999
RP/0/0/CPU0:R4(config-sr)# commit
```

Verify: `show ospf segment-routing` on R4 now shows Range: 16000-23999. Within seconds, R4 re-originates the type-7 Opaque LSA with index 4, and `show mpls forwarding labels 16004` on R1-R3 shows the entry.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPFv2 area 0 established — all four routers show FULL adjacencies on all five core links
- [ ] SRGB 16000-23999 confirmed on all four routers via `show ospf segment-routing`
- [ ] SR MPLS mode enabled under OSPF process on all routers
- [ ] Prefix SID indices 1-4 assigned on loopback interfaces for R1, R2, R3, R4
- [ ] `show ospf database opaque-area` shows four type-7 Opaque LSAs (one per node)
- [ ] `show mpls forwarding labels 16001 16004` shows all four SR MPLS entries on each router
- [ ] `traceroute mpls ipv4 10.0.0.3/32 source Loopback0` from R1 succeeds with correct SR label stack
- [ ] OSPF vs. IS-IS SID propagation timing comparison documented in your lab notes

### Troubleshooting

- [ ] Ticket 1 diagnosed (R3 area mismatch) and resolved — R3's SID visible in all peers' Opaque LSA databases
- [ ] Ticket 2 diagnosed (R2 prefix-sid missing) and resolved — label 16002 forwarding entry present on R1 and R3
- [ ] Ticket 3 diagnosed (R4 SRGB too small) and resolved — label 16004 forwarding entry present on R1, R2, R3

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
