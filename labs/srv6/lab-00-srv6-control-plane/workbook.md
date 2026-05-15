# SRv6 Lab 00: SRv6 IS-IS Control Plane

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

**Exam Objective:** 4.4, 4.4.a (SRv6 control plane operations), 4.4.d (SRv6 locator) — CCNP SPRI 300-510

Segment Routing over IPv6 (SRv6) replaces MPLS labels with 128-bit IPv6 addresses called Segment Identifiers (SIDs). Where SR-MPLS uses a label stack, SRv6 uses an IPv6 routing header (SRH) that carries an ordered list of SIDs. The control plane — the topic of this lab — is responsible for allocating SIDs and advertising them into the IGP so every node knows how to reach every other node's SID block.

### The Problem This Lab Solves

SRv6 shifts the forwarding identifier from a 32-bit MPLS label to a 128-bit IPv6 address, but that shift adds a new operational gap: without a mechanism to distribute per-node SID blocks across the domain, no router can build a forwarding path to a remote SID. In SR-MPLS, the SRGB plus an index is enough — every node already speaks MPLS. In SRv6, the SID **is** the IPv6 address, so the control plane must advertise actual IPv6 prefixes that represent each node's allocatable SID space. A router that can't see another router's locator can never send it SRv6-encapsulated traffic — the data plane has no destination to target.

**IS-IS SRv6 Locator TLV advertisement closes this gap by distributing per-node /48 locator prefixes so every router populates its local SID table with the domain's End SIDs.**

| Piece | Role in the overall goal |
|-------|--------------------------|
| SRv6 vs SR-MPLS model | Establishes the data-plane abstraction the control plane serves — without understanding why SIDs replace labels, locator advertisement has no context |
| SRv6 Locator | The per-node namespace that must be distributed — each router claims a /48 block, and IS-IS tells every other router where it lives |
| IS-IS SRv6 Extensions | The protocol machinery that moves locator information between routers — Locator TLVs are the delivery vehicle |
| IOS-XR SRv6 Configuration | Where the engineer connects the three control-plane toggles — global SRv6 block, encapsulation source, and IS-IS activation |

**Analogy — postal sorting center network.**
- **SRv6 vs SR-MPLS:** Old system uses internal barcode labels (MPLS); new system routes by the destination street address directly (SRv6) — same delivery, different identifier.
- **SRv6 Locator:** Each sorting center's ZIP code prefix — everything addressed to a prefix in that block is routed to that center.
- **IS-IS SRv6 Extensions:** The inter-office bulletin board that tells every center the current list of ZIP codes and which truck routes reach them.
- **IOS-XR SRv6 Configuration:** The control panel at each sorting center that an operator configures to join the bulletin system — three switches that must all be on.

Every subsection below is one of these pieces, starting with the conceptual shift from the old model to the new.

### SRv6 vs SR-MPLS

*The sorting-center foundation — before the control plane can distribute SIDs, we first understand why SRv6 replaces MPLS labels with IPv6 addresses as forwarding identifiers.*

| Property | SR-MPLS | SRv6 |
|----------|---------|------|
| Data-plane identifier | 32-bit MPLS label | 128-bit IPv6 SID |
| Label/SID distribution | IS-IS TLV 135 sub-TLVs | IS-IS SRv6 Locator TLV |
| Forwarding header | MPLS label stack | SRH (Segment Routing Header, IP protocol 43) |
| Global block | SRGB (e.g. 16000-23999) | Locator block (e.g. fc00:0::/32) |
| Per-node range | Prefix-SID index | Locator prefix (e.g. fc00:0:1::/48) |
| Per-link SID | Adj-SID (SRLB) | End.X SID |
| Service SID | — (requires BGP LU or 6PE) | End.DT4 / End.DT6 (native service SID) |

The fundamental difference: SRv6 uses IPv6 addresses themselves as SIDs. This collapses forwarding + services into a single address family and removes the need for an MPLS data plane entirely — SRv6 is a pure IPv6 solution.

### The SRv6 Locator

*The ZIP-code prefix from the analogy — the locator is the per-node namespace that IS-IS advertises so every router knows where each SID block lives.*

An SRv6 **locator** is an IPv6 prefix that represents a node's SID space. It serves two roles:
1. **Routing:** The locator is advertised into the IGP. Any packet whose destination falls inside the locator prefix is forwarded toward the owning node.
2. **SID allocation:** The SID manager carves function-specific sub-prefixes out of the locator. A `/48` locator (the typical deployment) gives 16 bits of function space — enough for up to 65,535 distinct behaviors.

In this lab, every node gets a `/48` locator from the `fc00:0::/32` block:
- P1: `fc00:0:1::/48`  |  P2: `fc00:0:2::/48`
- P3: `fc00:0:3::/48`  |  P4: `fc00:0:4::/48`
- PE1: `fc00:0:11::/48` | PE2: `fc00:0:12::/48`

The SID manager automatically allocates sub-ranges within each locator:
- A `/64` for the End (node) SID — e.g. `fc00:0:1:1::/64`
- Additional `/64` blocks for End.X (per-adjacency) SIDs as interfaces are configured

### IS-IS SRv6 Extensions

*The inter-office bulletin board from the analogy — IS-IS Locator TLVs are the delivery mechanism that carries every router's locator prefix to every other router in the domain.*

IS-IS carries SRv6 information through a new TLV hierarchy:

**SRv6 Locator TLV (type 27)** — carried inside IS-IS reachability TLVs. Contains the locator prefix, metric, algorithm, and flags. When `segment-routing srv6 locator <name>` is active under the IS-IS address-family, the router originates one Locator TLV per locator it owns. Every other router installs a route for that locator prefix.

```
IS-IS Reachability TLV (135 for IPv4, 236 for IPv6)
  └── SRv6 Locator TLV (27)
        ├── Prefix: fc00:0:1::/48
        ├── Metric: 0
        ├── Algorithm: 0 (SPF)
        └── Flags: D-bit set (locator is up)
```

**End SID sub-TLV** — carried inside the Locator TLV. Advertises the node's End behavior SID. The End function simply forwards the packet to the node's loopback — it is the SRv6 equivalent of a prefix-SID in SR-MPLS.

**End.X SID sub-TLV** — also carried inside the Locator TLV. Each is associated with a specific adjacency. When a packet arrives with an End.X SID as the active segment, the node cross-connects it out the corresponding interface. These are covered in lab-01.

In lab-00, we enable only the control plane: locator advertisement and End SID allocation. No End.X, no SRH forwarding — that's lab-01's data-plane domain.

### IOS-XR SRv6 Configuration Structure

*The control panel from the analogy — this section maps the three independent toggles an operator must configure to bring a node into the SRv6 control plane.*

SRv6 configuration on IOS-XR has three locations that must all be present:

```
segment-routing           ! top-level — NOT nested under mpls
 srv6
  encapsulation
   source-address fc00:0:1::1    ! IPv6 SA for SRH-encapsulated packets
  !
  locators
   locator P1_LOC
    prefix fc00:0:1::/48         ! SID allocation pool for this node
   !
  !
 !
!

router isis CORE
 address-family ipv6 unicast
  segment-routing srv6           ! activates SRv6 in IS-IS for this AF
   locator P1_LOC                ! which locator to advertise
  !
 !
!
```

On IOS-XR, `segment-routing` is a **top-level config block** — it is not under `mpls`, `router isis`, or any other subsystem. The `encapsulation source-address` is required for SRv6 to function (it sets the outer IPv6 SA for SRH-encapsulated packets), but in lab-00 it is a prerequisite for the SID manager to come up — actual encapsulation occurs in lab-01.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| SRv6 locator configuration | Define per-node /48 locators under the top-level `segment-routing srv6` block |
| IS-IS SRv6 activation | Enable `segment-routing srv6` under both IPv4 and IPv6 IS-IS address-families |
| Locator verification | Read and interpret `show segment-routing srv6 locator` output |
| SID table inspection | Verify End SID allocation via `show segment-routing srv6 sid` |
| SRv6 control-plane troubleshooting | Diagnose missing locator TLV, wrong prefix-length, or IS-IS AF mismatch |

---

## 2. Topology & Scenario

### Scenario

You are deploying SRv6 in a six-router service provider core. The P routers (P1, P2, P3, P4) form a ring with a diagonal P1↔P3, and two PE routers (PE1, PE2) attach to P1 and P3 respectively. All nodes run IOS-XRv 9000 in EVE-NG. Currently only IP addresses are configured — no IGP, no SRv6.

Your task is to:
1. Bring up IS-IS Level 2 dual-stack (IPv4 + IPv6) on all six routers.
2. Configure SRv6 globally and allocate a per-node /48 locator from the `fc00:0::/32` block.
3. Activate SRv6 under IS-IS so every node advertises its locator.
4. Verify that every node sees every other node's locator in the SID table.

The end state is a fully-converged IS-IS dual-stack underlay where every SRv6 locator is reachable — the control-plane foundation that lab-01 (data plane), lab-02 (Flex-Algo + L3VPN), and the capstones all build on.

### Topology

```
         ┌──────────────────────┐                 ┌──────────────────────┐
         │         PE1          │                 │         PE2          │
         │   10.0.0.11/32       │                 │   10.0.0.12/32       │
         │ fc00:0:11::/48 loc   │                 │ fc00:0:12::/48 loc   │
         └──────────┬───────────┘                 └──────────┬───────────┘
                    │ Gi0/0/0/0                              │ Gi0/0/0/0
                    │ 10.10.6.1/30                           │ 10.10.7.1/30
                    │ fc00:10:6::1/64                        │ fc00:10:7::1/64
                    │                                        │
                    │ 10.10.6.2/30                           │ 10.10.7.2/30
                    │ fc00:10:6::2/64                        │ fc00:10:7::2/64
                    │ Gi0/0/0/3                              │ Gi0/0/0/3
         ┌──────────┴───────────┐                 ┌──────────┴───────────┐
         │         P1           │                 │         P3           │
         │   10.0.0.1/32        │  10.10.5.0/30   │   10.0.0.3/32        │
         │ fc00:0:1::/48 loc    ├───────L5────────┤ fc00:0:3::/48 loc    │
         │ NET .0001.00         │   fc00:10:5::/64│ NET .0003.00         │
         └──┬──────────────┬────┘                 └──┬──────────────┬────┘
            │              │                         │              │
   Gi0/0/0/0│    Gi0/0/0/1 │               Gi0/0/0/0 │    Gi0/0/0/1│
    10.10.1.1│   10.10.4.2 │             10.10.2.2  │   10.10.3.1│
       /30 L1│        /30 L4│                  /30 L2│        /30 L3│
            │              │                         │              │
    10.10.1.2│   10.10.4.1 │             10.10.2.1  │   10.10.3.2│
   Gi0/0/0/0 │   Gi0/0/0/1 │            Gi0/0/0/1   │  Gi0/0/0/0 │
     ┌───────┴───────┐      │              ┌─────────┴───────┐     │
     │      P2       │      └──────────────┤      P4         │─────┘
     │ 10.0.0.2/32   │                    │ 10.0.0.4/32     │
     │ .0002.00 loc  │                    │ .0004.00 loc    │
     │ fc00:0:2::/48 │                    │ fc00:0:4::/48   │
     └───────────────┘                    └─────────────────┘
```

Links: L1 P1↔P2, L2 P2↔P3, L3 P3↔P4, L4 P1↔P4, L5 P1↔P3 diagonal, L6 PE1↔P1, L7 PE2↔P3.

Three distinct paths exist PE1↔PE2: direct diagonal P1→P3 (L5, 2 hops), via-P2 (L1+L2, 3 hops), via-P4 (L4+L3, 3 hops). At the control-plane level (lab-00), IS-IS converges all three with equal default metrics — path selection via Flex-Algo is lab-02's responsibility.

### Device & Locator Table

| Device | Role | Loopback0 (v4) | Loopback0 (v6) | IS-IS NET | SRv6 Locator |
|--------|------|----------------|----------------|-----------|-------------|
| P1 | P core (BGP-free hub) | 10.0.0.1/32 | fc00:0:1::1/128 | 49.0001.0000.0000.0001.00 | fc00:0:1::/48 |
| P2 | P core (apex) | 10.0.0.2/32 | fc00:0:2::1/128 | 49.0001.0000.0000.0002.00 | fc00:0:2::/48 |
| P3 | P core (BGP-free hub) | 10.0.0.3/32 | fc00:0:3::1/128 | 49.0001.0000.0000.0003.00 | fc00:0:3::/48 |
| P4 | P core (apex) | 10.0.0.4/32 | fc00:0:4::1/128 | 49.0001.0000.0000.0004.00 | fc00:0:4::/48 |
| PE1 | SP edge | 10.0.0.11/32 | fc00:0:11::1/128 | 49.0001.0000.0000.0011.00 | fc00:0:11::/48 |
| PE2 | SP edge | 10.0.0.12/32 | fc00:0:12::1/128 | 49.0001.0000.0000.0012.00 | fc00:0:12::/48 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| P1 | P core (hub, ring + diagonal) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |
| P2 | P core (apex, ring only) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |
| P3 | P core (hub, ring + diagonal) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |
| P4 | P core (apex, ring only) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |
| PE1 | SP edge (iBGP later) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |
| PE2 | SP edge (iBGP later) | xrv9k | IOS-XRv 9000 7.1.1 | 16384 MB |

### Loopback Address Table

| Device | Interface | IPv4 Address | IPv6 Address | Purpose |
|--------|-----------|-------------|--------------|---------|
| P1 | Loopback0 | 10.0.0.1/32 | fc00:0:1::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |
| P2 | Loopback0 | 10.0.0.2/32 | fc00:0:2::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |
| P3 | Loopback0 | 10.0.0.3/32 | fc00:0:3::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |
| P4 | Loopback0 | 10.0.0.4/32 | fc00:0:4::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |
| PE1 | Loopback0 | 10.0.0.11/32 | fc00:0:11::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |
| PE2 | Loopback0 | 10.0.0.12/32 | fc00:0:12::1/128 | Router ID, IS-IS NET source, SRv6 encapsulation SA |

### Cabling

| Link | Endpoints | Subnet (IPv4) | Subnet (IPv6) |
|------|-----------|---------------|---------------|
| L1 | P1 Gi0/0/0/0 ↔ P2 Gi0/0/0/0 | 10.10.1.0/30 (.1=P1, .2=P2) | fc00:10:1::/64 (::1=P1, ::2=P2) |
| L2 | P2 Gi0/0/0/1 ↔ P3 Gi0/0/0/0 | 10.10.2.0/30 (.1=P2, .2=P3) | fc00:10:2::/64 (::1=P2, ::2=P3) |
| L3 | P3 Gi0/0/0/1 ↔ P4 Gi0/0/0/0 | 10.10.3.0/30 (.1=P3, .2=P4) | fc00:10:3::/64 (::1=P3, ::2=P4) |
| L4 | P4 Gi0/0/0/1 ↔ P1 Gi0/0/0/1 | 10.10.4.0/30 (.1=P4, .2=P1) | fc00:10:4::/64 (::1=P4, ::2=P1) |
| L5 | P1 Gi0/0/0/2 ↔ P3 Gi0/0/0/2 | 10.10.5.0/30 (.1=P1, .2=P3) | fc00:10:5::/64 (::1=P1, ::2=P3) |
| L6 | PE1 Gi0/0/0/0 ↔ P1 Gi0/0/0/3 | 10.10.6.0/30 (.1=PE1, .2=P1) | fc00:10:6::/64 (::1=PE1, ::2=P1) |
| L7 | PE2 Gi0/0/0/0 ↔ P3 Gi0/0/0/3 | 10.10.7.0/30 (.1=PE2, .2=P3) | fc00:10:7::/64 (::1=PE2, ::2=P3) |

### Console Access

| Device | Port | Connection Command |
|--------|------|--------------------|
| P1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

> **Boot warning:** IOS-XRv 9000 nodes take 8–12 minutes to reach the `RP/0/0/CPU0:<hostname>#` prompt. Do not run `setup_lab.py` until every node has completed boot.

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames
- All interface IPv4 and IPv6 addresses (7 links + 6 loopbacks)
- Interface descriptions and `no shutdown` on all active ports

**IS NOT pre-loaded** (student configures this):
- IS-IS process and IS-IS NET on each router
- IS-IS address-families (IPv4 unicast + IPv6 unicast)
- `metric-style wide` under both address-families
- Per-interface IS-IS attachment (passive on Loopback0, point-to-point on core links)
- Top-level `segment-routing srv6` block with per-node locator and encapsulation source
- `segment-routing srv6 locator` under IS-IS IPv4 and IPv6 address-families

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Bring Up IS-IS Level 2 Dual-Stack on All Six Routers

- On each router, configure IS-IS process `CORE` with the NET from the device table (system ID matches the loopback number: `0000.0000.0001` for P1, `0000.0000.0011` for PE1, etc.).
- Set `is-type level-2-only` — production SP cores avoid L1/L2 overhead.
- Under `address-family ipv4 unicast` AND `address-family ipv6 unicast`, enable `metric-style wide`. This is a strict prerequisite for SRv6 — narrow TLVs cannot carry SRv6 Locator TLVs.
- Attach Loopback0 to IS-IS as `passive` under both address-families.
- Attach every core-facing GigabitEthernet to IS-IS as `point-to-point` under both address-families. P1 has four interfaces (Gi0/0/0/0–Gi0/0/0/3), P2 and P4 have two each, P3 has four, PE1 and PE2 have one each.

**Verification:** `show isis adjacency` on every router shows all expected neighbors in `Up` state. P1 sees 4 neighbors (P2, P4, P3 via L5, PE1); P2 sees 2 (P1, P3); P3 sees 4 (P1, P2, P4, PE2); P4 sees 2 (P3, P1); PE1 sees 1 (P1); PE2 sees 1 (P3). Total unique adjacencies = 7 (one per link). `show isis ipv6 topology` confirms the full IPv6 topology.

---

### Task 2: Configure the SRv6 Global Block and Per-Node Locators

- On every router, add the top-level `segment-routing srv6` block:
  - Set the encapsulation source address to the router's Loopback0 IPv6 address (e.g. P1 uses `fc00:0:1::1`).
  - Define a locator with a descriptive name (e.g. `P1_LOC`) and the router's /48 prefix from the locator table (e.g. `fc00:0:1::/48`).
- The `encapsulation source-address` is required for the SRv6 SID manager to initialise — even though no encapsulation happens in lab-00, the SID manager will not allocate End SIDs without it.

> **Important:** The `segment-routing srv6` block is at the IOS-XR top level — it is **not** nested under `mpls`, `router isis`, or any subsystem. Placing it under the wrong hierarchy is the most common XR operator mistake on this objective.

**Verification:** `show segment-routing srv6 locator` on each router lists its own locator with `Status: Active`. The prefix length must be `/48`. If the locator status is `Down`, the SID manager has not initialised (check the encapsulation source-address is configured and is a valid local IPv6 address).

---

### Task 3: Activate SRv6 Under IS-IS

- Under `router isis CORE`, in **both** the IPv4 and IPv6 address-families, add `segment-routing srv6 locator <name>` (using the locator name from Task 2).
- This tells IS-IS to originate SRv6 Locator TLVs for that locator in the corresponding address-family LSAs.
- The locator is the same across both AFs — IS-IS must be told in both contexts.

**Verification:** `show isis segment-routing srv6` lists the local locator with its End SID. `show segment-routing srv6 sid` on every router lists its own End SID (behavior `End`, no parent) — the local SID is allocated even before any remote SIDs are learned because the SID manager carves it out of the locator at commit time.

---

### Task 4: Verify the Domain-Wide SRv6 SID Table

- Once all six routers have SRv6 active under IS-IS, the Locator TLVs propagate. Every router learns every other router's locator via IS-IS.
- The SID manager on each router installs remote End SIDs into the local SID table.

**Verification:**
- `show segment-routing srv6 sid` on P1 lists at least 6 End SID entries — one local (P1) and five remote (P2, P3, P4, PE1, PE2).
- `show isis segment-routing srv6` on any router shows the full locator table.
- `show route ipv6 fc00:0::/32 longer-prefixes` confirms that every /48 locator route is in the RIB via IS-IS.

---

### Task 5: End-to-End IPv6 Reachability and Locator Troubleshooting

- From P1, ping every other router's Loopback0 IPv6 address (e.g. `ping fc00:0:3::1`). All must succeed — IS-IS has converged the dual-stack underlay.
- From P2, run `show segment-routing srv6 sid` and confirm that all six locators are present. If a locator is missing, that node has not advertised its Locator TLV — the fault is on the originating node.
- > **Tip:** To understand what happens when the SRv6 block is removed, work through Ticket 4 in Section 9 — it simulates this exact fault and walks you through the diagnosis.

**Verification:**
- `ping fc00:0:12::1 source fc00:0:1::1` from P1 succeeds (5/5).
- `show segment-routing srv6 sid` on every router shows 6 End SIDs — one per node in the domain.

---

## 6. Verification & Analysis

### Task 1: IS-IS Adjacency Verification

```
RP/0/0/CPU0:P1# show isis adjacency
IS-IS CORE Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 BFD IPv6 BFD
P2             Gi0/0/0/0                *PtoP*         Up    27   00:05:32 Yes  None     None    ! ← L1
P4             Gi0/0/0/1                *PtoP*         Up    28   00:05:30 Yes  None     None    ! ← L4
P3             Gi0/0/0/2                *PtoP*         Up    25   00:05:28 Yes  None     None    ! ← L5 diagonal
PE1            Gi0/0/0/3                *PtoP*         Up    26   00:05:25 Yes  None     None    ! ← L6 access
Total adjacency count: 4
```

P1 has 4 neighbors. P2 has 2, P3 has 4, P4 has 2, PE1 has 1, PE2 has 1. Per-link unique count = 7.

### Task 1: IS-IS IPv6 Topology

```
RP/0/0/CPU0:P1# show isis ipv6 topology
IS-IS CORE paths to IPv6 routers
System Id        Metric   Next-Hop             Interface
P2               10        {fe80::...}          Gi0/0/0/0      ! ← via L1
P3               10        {fe80::...}          Gi0/0/0/2      ! ← via L5 diagonal (shorter metric)
P4               10        {fe80::...}          Gi0/0/0/1      ! ← via L4
PE1              10        {fe80::...}          Gi0/0/0/3      ! ← via L6
PE2              20        {fe80::...}          Gi0/0/0/2      ! ← via P3, 2 hops
```

### Task 2: SRv6 Locator Status

```
RP/0/0/CPU0:P1# show segment-routing srv6 locator
Name                  ID       Algo      Prefix               Status
----------------------------   ----      ------               ------
P1_LOC                 1        0        fc00:0:1::/48        Active    ! ← status must be Active
```

If `Status` is `Down`, the SID manager has not initialised — verify the encapsulation source-address is a valid local IPv6 address and `commit` is complete.

### Task 3: IS-IS SRv6 Registration

```
RP/0/0/CPU0:P1# show isis segment-routing srv6
IS-IS CORE SRv6 Locators:
  Locator: P1_LOC, Prefix: fc00:0:1::/48, Algorithm: 0
    End SID: fc00:0:1:1:: (dynamic)        ! ← SID manager auto-allocated End SID

IS-IS CORE SRv6 Remote SIDs:
  (populated once other nodes advertise their locators)
```

### Task 4: Domain-Wide SRv6 SID Table

```
RP/0/0/CPU0:P1# show segment-routing srv6 sid
SID                         Behavior   Context                           Owner           State
--------------------------  ---------  -------------------------------   --------------  -----
fc00:0:1:1::                End        'default':0                       sid-mgr         InUse   ! ← P1 (local)
fc00:0:2:1::                End        'default':0                       isis-CORE       InUse   ! ← P2
fc00:0:3:1::                End        'default':0                       isis-CORE       InUse   ! ← P3
fc00:0:4:1::                End        'default':0                       isis-CORE       InUse   ! ← P4
fc00:0:11:1::               End        'default':0                       isis-CORE       InUse   ! ← PE1
fc00:0:12:1::               End        'default':0                       isis-CORE       InUse   ! ← PE2
```

Six End SIDs on every router confirms full SRv6 control-plane convergence. The `Owner` column shows `sid-mgr` for the local entry and `isis-CORE` for remote entries learned via IS-IS.

### Task 4: IPv6 Route Table — Locator Prefixes

```
RP/0/0/CPU0:P1# show route ipv6 fc00:0::/32 longer-prefixes
L     fc00:0:1::/48  is directly connected, Loopback0            ! ← local locator
i L2  fc00:0:2::/48  [115/20] via fe80::..., Gi0/0/0/0          ! ← P2 via L1
i L2  fc00:0:3::/48  [115/20] via fe80::..., Gi0/0/0/2          ! ← P3 via L5
i L2  fc00:0:4::/48  [115/20] via fe80::..., Gi0/0/0/1          ! ← P4 via L4
i L2  fc00:0:11::/48 [115/20] via fe80::..., Gi0/0/0/3          ! ← PE1 via L6
i L2  fc00:0:12::/48 [115/30] via fe80::..., Gi0/0/0/2          ! ← PE2 via P1→P3 (2 hops)
```

### Task 5: End-to-End IPv6 Reachability

```
RP/0/0/CPU0:P1# ping fc00:0:12::1 source fc00:0:1::1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to fc00:0:12::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/2/3 ms
```

---

## 7. Verification Cheatsheet

### IS-IS Dual-Stack Configuration

```
router isis CORE
 net 49.0001.0000.0000.000X.00
 is-type level-2-only
 address-family ipv4 unicast
  metric-style wide
 !
 address-family ipv6 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
 interface GigabitEthernet0/0/0/X
  point-to-point
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
```

| Command | Purpose |
|---------|---------|
| `router isis CORE` | IS-IS process definition |
| `net 49.0001.0000.0000.000X.00` | IS-IS NET — system ID matches node number |
| `is-type level-2-only` | Restrict to L2 (production SP core) |
| `metric-style wide` | Required for SRv6 Locator TLVs (narrow TLVs cannot carry them) |
| `address-family ipv6 unicast` | Dual-stack — SRv6 locators are IPv6, both AFs needed |

### SRv6 Global Configuration

```
segment-routing
 srv6
  encapsulation
   source-address fc00:0:X::1
  !
  locators
   locator <NAME>
    prefix fc00:0:X::/48
   !
  !
 !
!
```

| Command | Purpose |
|---------|---------|
| `segment-routing srv6` | Top-level block — NOT under `mpls` or `router isis` |
| `encapsulation source-address <ipv6>` | Sets outer SRH IPv6 SA; required for SID manager initialisation |
| `locator <NAME> prefix <prefix>` | Defines per-node /48 SID allocation pool |

### IS-IS SRv6 Activation

```
router isis CORE
 address-family ipv4 unicast
  segment-routing srv6
   locator <NAME>
  !
 !
 address-family ipv6 unicast
  segment-routing srv6
   locator <NAME>
  !
 !
!
```

| Command | Purpose |
|---------|---------|
| `segment-routing srv6 locator <NAME>` | Under IS-IS af — originates SRv6 Locator TLV for this locator |

> **Exam tip:** The SRv6 control plane has **three independent toggles** that must all be active: (1) top-level `segment-routing srv6` with locator defined, (2) `encapsulation source-address` on a valid local IPv6 address, and (3) `segment-routing srv6 locator <name>` under each IS-IS address-family. Removing any of the three breaks the control plane in a different way — knowing which toggle controls which behaviour is the diagnostic skill that Ticket 1 tests.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis adjacency` | 7 unique adjacencies across the domain; every expected neighbor in Up state |
| `show isis ipv6 topology` | All 6 routers reachable via IPv6 IS-IS |
| `show segment-routing srv6 locator` | Each local locator with Status: Active |
| `show isis segment-routing srv6` | Local End SID allocated; remote SIDs populated |
| `show segment-routing srv6 sid` | 6 End SID entries (one per router) per node |
| `show route ipv6 fc00:0::/32 longer-prefixes` | 6 /48 locator routes via IS-IS |
| `ping fc00:0:12::1 source fc00:0:1::1` | End-to-end IPv6 reachability across the domain |

### Common SRv6 Control-Plane Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show segment-routing srv6 locator` returns no output | Top-level `segment-routing srv6` block not committed or has no locator configured |
| Locator `Status: Down` | Encapsulation source-address not configured or points to non-existent/mismatched IPv6 address |
| SID table shows only local entry — no remote SIDs | `segment-routing srv6 locator` missing under IS-IS af on the remote nodes |
| One locator missing from `show route ipv6` on every router | That node's `segment-routing srv6 locator` missing or `metric-style wide` missing under IS-IS af |
| IPv4 routes present but IPv6 missing | `address-family ipv6 unicast` not configured under `router isis` or under the interface |
| All remote SIDs missing on one router | `metric-style wide` missing on that router — cannot process Locator TLVs from others |
| Locator accepted but SID table empty | Locator prefix-length mismatch — must be /48 to match domain allocation (a longer prefix leaves no function bits) |

---

## 8. Solutions (Spoiler Alert!)

> Try Tasks 1–5 yourself before opening these.

### Task 1: IS-IS L2 Dual-Stack

<details>
<summary>Click to view P1 Configuration</summary>

```
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 address-family ipv4 unicast
  metric-style wide
 !
 address-family ipv6 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  point-to-point
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
 interface GigabitEthernet0/0/0/2
  point-to-point
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
 interface GigabitEthernet0/0/0/3
  point-to-point
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view P2, P3, P4, PE1, PE2 Configuration</summary>

Same structure as P1 with the following differences:
- NET system ID: P2=`0000.0000.0002`, P3=`0000.0000.0003`, P4=`0000.0000.0004`, PE1=`0000.0000.0011`, PE2=`0000.0000.0012`
- Interface count varies: P2 and P4 have 2 Gi interfaces each; PE1 and PE2 have 1 Gi each

See `solutions/P2.cfg` through `solutions/PE2.cfg` for the complete configs.
</details>

---

### Task 2: SRv6 Global and Per-Node Locator

<details>
<summary>Click to view P1 SRv6 Configuration</summary>

```
segment-routing
 srv6
  encapsulation
   source-address fc00:0:1::1
  !
  locators
   locator P1_LOC
    prefix fc00:0:1::/48
   !
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view All Devices</summary>

Same structure on every router, only the locator name (P2_LOC, P3_LOC, P4_LOC, PE1_LOC, PE2_LOC), prefix, and source-address change to match the router's own loopback IPv6 address and assigned locator from the device table in Section 2.
</details>

---

### Task 3 + 4: IS-IS SRv6 Activation

<details>
<summary>Click to view P1 IS-IS SRv6 (add to IS-IS block from Task 1)</summary>

```
router isis CORE
 address-family ipv4 unicast
  segment-routing srv6
   locator P1_LOC
  !
 !
 address-family ipv6 unicast
  segment-routing srv6
   locator P1_LOC
  !
 !
!
commit
```
</details>

<details>
<summary>Click to view All Devices</summary>

Same addition under both IPv4 and IPv6 IS-IS address-families on all routers using their respective locator name.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```
show segment-routing srv6 locator
show isis segment-routing srv6
show segment-routing srv6 sid
show route ipv6 fc00:0::/32 longer-prefixes
ping fc00:0:12::1 source fc00:0:1::1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

> **Ticket 4 is a manual fault** — no inject script. Follow the reproduction steps in the ticket to induce the fault, diagnose, and fix.

---

### Ticket 1 — One SRv6 End SID Missing From All SID Tables

A network engineer reports that pre-deployment checks show only five SRv6 End SIDs on every router instead of six. IPv6 ping to P2's Loopback0 (`fc00:0:2::1`) works from all nodes, and all IS-IS adjacencies are Up — the IGP underlay is healthy. The SRv6 SID that is missing is always `fc00:0:2:1::`. The team confirmed that P2 has `segment-routing srv6` configured with its locator.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Symptom:**
- All 7 IS-IS adjacencies are Up.
- `show segment-routing srv6 locator` on P2 shows `P2_LOC` with prefix `fc00:0:2::/48` and Status: Active — the local locator is fine.
- `show segment-routing srv6 sid` on P1, P3, P4, PE1, and PE2 shows 5 End SIDs — `fc00:0:2:1::` is absent from every node.
- On P2 itself, `show segment-routing srv6 sid` shows only its own local End SID — no remote SIDs at all.
- `show isis segment-routing srv6` on P2 shows the local locator but `Remote SIDs` is empty.
- IPv6 ping to `fc00:0:2::1` still works from all nodes — IS-IS still advertises the IPv6 loopback route without the SRv6 extensions.

**Success criteria:** `show segment-routing srv6 sid` on every router shows all 6 End SIDs. P2's remote SID table is fully populated.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm scope: `show segment-routing srv6 sid` on P1 shows 5 SIDs — `fc00:0:2:1::` (P2's End SID) is missing. The fault is localized to P2 — every other router is missing the same entry, which means P2 is not advertising its locator into IS-IS.

2. On P2, check the three SRv6 toggles:
   - Top-level: `show segment-routing srv6 locator` — P2_LOC is present, prefix `fc00:0:2::/48`, Status: Active. The locator definition is fine.
   - Encapsulation source: `show running-config segment-routing srv6` — `source-address fc00:0:2::1` is configured. Good.
   - IS-IS: `show running-config router isis CORE` — check both address-families. The `segment-routing srv6 locator P2_LOC` line is **missing** from both `address-family ipv4 unicast` and `address-family ipv6 unicast`.

3. Impact: without the IS-IS activation, P2 does not originate SRv6 Locator TLV 27 for `fc00:0:2::/48`. Other routers still have the IPv6 loopback route via IS-IS (which is why ping works), but they have no SRv6 SID to install for P2.

4. Confirm via the IS-IS database: on P1, `show isis database P2 detail | include "SRv6"` returns nothing — no Locator TLV from P2.

This is the SRv6 equivalent of "missing `segment-routing mpls` under IS-IS af" in SR-MPLS. The locator is configured but never advertised.
</details>

<details>
<summary>Click to view Fix</summary>

On P2:
```
router isis CORE
 address-family ipv4 unicast
  segment-routing srv6
   locator P2_LOC
  !
 !
 address-family ipv6 unicast
  segment-routing srv6
   locator P2_LOC
  !
 !
!
commit
```

IS-IS originates the Locator TLV immediately. Verify on P1:
```
show segment-routing srv6 sid | include "fc00:0:2:1"
```
P2's End SID appears as `Owner: isis-CORE`.
</details>

---

### Ticket 2 — One Router Reports Fewer IS-IS Neighbors Than Expected

The operations team noticed an alert: P4's IS-IS neighbor count dropped from 2 to 1 overnight. P4 is still reachable — IPv6 ping to `fc00:0:4::1` succeeds from all routers, and P4's SRv6 End SID `fc00:0:4:1::` is present in every SID table. But the alert dashboard shows a topology change, and the team is concerned about redundancy if the remaining path also fails.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Symptom:**
- `show isis adjacency` on P4 lists only one neighbor (P1 over Gi0/0/0/1 / L4). The adjacency to P3 over Gi0/0/0/0 / L3 is absent.
- `show isis adjacency` on P3 also lists only 3 neighbors instead of 4 — P4 is missing from P3's adjacency list.
- `ping fc00:0:4::1` from P3 works — IPv6 connectivity between P3 and P4 still functions at Layer 3.
- Total domain-wide adjacencies drop from 7 to 6. Forwarding still works but the L3 link is down at the IGP level — if L4 also fails, P4 is fully isolated.
- P4's SRv6 locator `fc00:0:4::/48` is still advertised into IS-IS via the surviving L4 adjacency, so all End SIDs remain reachable. The issue is topology redundancy, not SRv6.

**Success criteria:** `show isis adjacency` on P4 lists 2 neighbors (P1 and P3). Total domain-wide adjacencies = 7.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Locate the missing adjacency: `show isis adjacency` on P4 — only Gi0/0/0/1 (L4 to P1) shows Up. Gi0/0/0/0 (L3 to P3) is absent.

2. Confirm Layer 3 is fine: `ping fc00:10:3::1 source fc00:10:3::2` from P4 to P3's L3 address succeeds. The fault is not physical, not IPv6, not L1/L2 — it is strictly at the IS-IS layer on P4's L3 interface.

3. Inspect IS-IS attachment on P4: `show running-config router isis CORE / interface GigabitEthernet0/0/0/0` — the interface block is present with `point-to-point`, but both `address-family ipv4 unicast` and `address-family ipv6 unicast` sub-blocks are missing.

4. Impact: on IOS-XR, an IS-IS interface needs both the interface-level attributes (`point-to-point`) AND per-address-family blocks to exchange IS-IS hellos for that AF. Without any AF block, the interface stays attached to IS-IS but does not send or receive IS-IS hello PDUs — adjacency never forms.

5. Cross-check from P3: `show isis adjacency` on P3 also misses P4 — confirming the failure is symmetric. Both sides need IS-IS hellos to form adjacency.
</details>

<details>
<summary>Click to view Fix</summary>

On P4:
```
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
commit
```

Adjacency forms within one IS-IS hello interval. Verify on both P4 and P3:
```
show isis adjacency
```
P4 shows 2 neighbors (P1, P3); P3 shows 4 neighbors (P1, P2, P4, PE2).
</details>

---

### Ticket 3 — One Node's SRv6 Locator Shows Status Down

A network engineer is testing the SRv6 control plane and notices that PE2's locator `PE2_LOC` is listed as `Status: Down` in `show segment-routing srv6 locator`. The other five routers all report `Status: Active`. PE2 was configured at the same time as PE1, and the team says both received identical configuration. The other routers cannot see PE2's End SID — `fc00:0:12:1::` is absent from every SID table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Symptom:**
- `show segment-routing srv6 locator` on PE2 shows `PE2_LOC` with Status: Down (not Active).
- `show segment-routing srv6 sid` on PE2 shows no SID entries — the SID manager has not carved any SIDs from the locator because the locator is not active.
- All other routers show 5 End SIDs in their SID tables — `fc00:0:12:1::` is missing.
- IPv6 ping to `fc00:0:12::1` still works from all routers — IS-IS advertises PE2's loopback prefix, but no SRv6 SID exists.
- `show isis segment-routing srv6` on PE2 may show the locator registered under IS-IS but with no End SID allocated.

**Success criteria:** `show segment-routing srv6 locator` on PE2 shows Status: Active. `show segment-routing srv6 sid` on all routers includes `fc00:0:12:1::`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check PE2's locator: `show segment-routing srv6 locator` — Status: Down. The locator was defined but the SID manager rejected it.

2. Check the encapsulation source-address: `show running-config segment-routing srv6 encapsulation` — the source-address is correctly set to PE2's Loopback0 IPv6 (`fc00:0:12::1`). That's fine.

3. Inspect the locator definition: `show running-config segment-routing srv6 locators` — the prefix is configured as `fc00:0:12::/64` instead of `/48`. A `/64` locator has **zero** function bits (it takes the full /64, leaving no sub-prefix space for the End SID allocation). The SID manager requires at least a few bits of function space to carve out SID entries — a `/48` gives 16 bits; a `/64` gives zero.

4. Impact: the SID manager cannot allocate an End SID from a /64 locator because there is no room. It marks the locator as Down and emits a log message about insufficient function space. IS-IS never originates the Locator TLV because the locator is not active — other routers never learn `fc00:0:12::/48`.

5. The correct prefix per the domain plan is `/48` — all six routers share the `fc00:0::/32` block with each node occupying its own `/48`. PE2's `/64` does not match the plan and is too long for the SID manager to operate.

This is a common first-time SRv6 mistake: confusing the link prefix length (/64 for interface addresses) with the locator prefix length (/48 for the global SID block). The distinction between locator length and interface prefix length is the lesson.
</details>

<details>
<summary>Click to view Fix</summary>

On PE2:
```
segment-routing
 srv6
  locators
   no locator PE2_LOC
   locator PE2_LOC
    prefix fc00:0:12::/48
   !
  !
 !
!
commit
```

The SID manager immediately activates the locator and allocates the End SID `fc00:0:12:1::`. Verify:
```
show segment-routing srv6 locator    ! Status: Active
show segment-routing srv6 sid        ! End SID fc00:0:12:1:: allocated
```

Then on P1:
```
show segment-routing srv6 sid | include "fc00:0:12:1"   ! now visible
```
</details>

---

### Ticket 4 — All Remote SIDs Disappear After Configuration Change

After a maintenance window, an engineer notices that a router's SRv6 SID table contains only its own local End SID — all five remote SIDs are gone. IS-IS adjacencies are all Up and IPv6 routing works, but the SRv6 control plane has collapsed on this node. The engineer recalls making a configuration change but isn't sure what caused the impact.

**Inject:** Manual — see diagnosis steps for how to reproduce. (No inject script; this ticket teaches the effect of removing the top-level SRv6 block.)

**Success criteria:** `show segment-routing srv6 sid` on the affected router shows all 6 End SIDs again.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Reproduce: on any router, remove the top-level `segment-routing srv6` block (`no segment-routing srv6`) and commit.

2. Observe the effect:
   - `show segment-routing srv6 sid` — only the local SID remains (`Owner: sid-mgr`); all five remote SIDs are gone. A `no segment-routing srv6` at the top level tears down the entire SRv6 subsystem, including the SID manager's ability to track remote SIDs learned via IS-IS.
   - `show segment-routing srv6 locator` — returns empty (the locator definition is gone).
   - `show isis segment-routing srv6` — the IS-IS Locator TLV is no longer originated, so the remote SID table is also empty.

3. Note what still works: IS-IS adjacencies, IPv4/IPv6 routes, and ping — the IGP underlay is untouched. Only the SRv6 overlay dissolves.

</details>

<details>
<summary>Click to view Fix</summary>

Re-add the top-level `segment-routing srv6` block with the locator and encapsulation source-address, then re-activate under both IS-IS address-families. After commit, the SID manager re-initialises and IS-IS re-originates the Locator TLV — remote SIDs re-populate on all routers within one IS-IS LSP flood interval.

```
segment-routing
 srv6
  encapsulation
   source-address fc00:0:X::1
  !
  locators
   locator <NAME>
    prefix fc00:0:X::/48
   !
  !
 !
!

router isis CORE
 address-family ipv4 unicast
  segment-routing srv6
   locator <NAME>
  !
 !
 address-family ipv6 unicast
  segment-routing srv6
   locator <NAME>
  !
 !
!
commit
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS CORE process configured on all 6 routers with correct NET (`49.0001.0000.0000.000X.00`)
- [ ] `is-type level-2-only` on every router
- [ ] `metric-style wide` under both IPv4 and IPv6 IS-IS address-families on every router
- [ ] Loopback0 attached as `passive` under both AFs; every core interface attached as `point-to-point` under both AFs
- [ ] `show isis adjacency` shows 7 unique adjacencies across the domain (4 on P1, 2 on P2, 4 on P3, 2 on P4, 1 on PE1, 1 on PE2)
- [ ] Top-level `segment-routing srv6` configured on every router with `encapsulation source-address <loopback-v6>` and per-node /48 locator
- [ ] `show segment-routing srv6 locator` shows Status: Active on every router
- [ ] `segment-routing srv6 locator <name>` under both IS-IS IPv4 and IPv6 address-families on every router
- [ ] `show isis segment-routing srv6` lists the local locator with allocated End SID on every router
- [ ] `show segment-routing srv6 sid` shows 6 End SID entries (one per router) on every router
- [ ] `show route ipv6 fc00:0::/32 longer-prefixes` shows 6 /48 locator prefixes via IS-IS
- [ ] `ping fc00:0:12::1 source fc00:0:1::1` succeeds (5/5)

### Troubleshooting

- [ ] Ticket 1 resolved: all 6 SIDs appear after re-adding `segment-routing srv6 locator P2_LOC` under both IS-IS AFs on P2
- [ ] Ticket 2 resolved: P4's L3 adjacency reappears after re-attaching both `address-family` blocks under P4 Gi0/0/0/0
- [ ] Ticket 3 resolved: PE2's locator Active after correcting prefix from /64 to /48
- [ ] Ticket 4 resolved: all 6 remote SIDs re-populate after restoring the `segment-routing srv6` block

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided (placeholder detected) | All scripts |
| 3 | EVE-NG connectivity or port discovery error | All scripts |
| 4 | Pre-flight check failed (lab not in expected state) | Inject scripts only |
