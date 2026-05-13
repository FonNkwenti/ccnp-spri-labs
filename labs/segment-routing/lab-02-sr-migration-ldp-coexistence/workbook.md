# Lab 02 — SR Migration: LDP Coexistence, Mapping Server, and SR-Prefer

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

**Exam Objective:** 4.2.d — Describe SR migration from LDP, including LDP coexistence, SR mapping server, and SR-prefer

Production service providers do not migrate from LDP to SR overnight. Traffic engineered MPLS networks that have carried customer traffic for years carry operational risk whenever the data plane changes. The industry-standard approach is a phased migration: run LDP and SR concurrently, verify SR reachability while LDP provides fallback, then flip the preference once SR is fully validated. This lab simulates that migration path on a four-router IS-IS SR-MPLS core.

### LDP and SR Label Coexistence

When both LDP and SR are enabled on the same IOS-XR router, each protocol independently builds its label database. LDP discovers neighbors via UDP hellos on each enabled interface and distributes bindings for every IGP-reachable prefix through targeted and link-mode sessions. SR distributes prefix SIDs embedded in IS-IS TLV 135 sub-TLVs. The result is two label entries per destination in the platform label database — one from LDP, one from SR.

IOS-XR uses a label-source preference hierarchy to decide which label enters the FIB:

| Priority | Label Source | Applies to |
|----------|-------------|------------|
| 1 (highest) | SR prefix-SID (native) | IS-IS/OSPF SR-capable prefixes |
| 2 | LDP | All IGP prefixes |

For IS-IS prefixes that have a native prefix-SID advertisement, SR wins by default without any additional configuration. LDP bindings remain in the LDP database but are not programmed into the hardware FIB. This default preference is what makes the initial coexistence phase safe — you enable LDP on all interfaces, verify LDP sessions form, but SR forwarding is not disrupted.

### SR Mapping Server

Not every router in a large SP network can be migrated to SR at the same time. Legacy PEs may not support IOS-XR 24.3.1, or a node may be running IOS-XE which has a different SR feature set. The SR mapping server solves this: an SR-capable router (the mapping server) advertises segment IDs on behalf of prefixes that do not natively advertise prefix SIDs.

On IOS-XR, the mapping server configuration has two parts:

**Part 1 — Define the prefix-to-SID mapping:**
```
segment-routing
 mapping-server
  prefix-sid-map
   address-family ipv4
    192.0.2.0/24 50 range 100
```

The syntax `<prefix> <start-index> range <count>` allocates `<count>` consecutive SID indices starting at `<start-index>` for prefixes within `<prefix>`. Here, 192.0.2.0/24 receives SID index 50 (absolute label = SRGB_base + 50 = 16000 + 50 = 16050). The range of 100 means the mapping server can cover /32 prefixes within that /24 block using indices 50-149.

**Part 2 — Advertise via IS-IS:**
```
router isis CORE
 address-family ipv4 unicast
  segment-routing prefix-sid-map advertise-local
```

This command causes IS-IS to originate SID/Label Binding TLVs (TLV 149) for the mapped prefixes. Peers receive these TLVs in IS-IS LSPs and can build SR FIB entries for the mapped prefixes — even though those prefixes came from a non-SR node that does not know anything about segment routing.

> **Exam tip:** The mapping server is unidirectional — one SR router advertises SIDs on behalf of non-SR prefixes. The non-SR router does not need any configuration changes. The mapping server only needs to be reachable and have the target prefixes in its RIB (learned via IS-IS redistribution or static).

### SR-Prefer and Its Role in Migration

`segment-routing mpls sr-prefer` under IS-IS address-family changes which label source the FIB uses when a prefix has BOTH an LDP binding and an SR-based SID. It is relevant in one specific scenario: **mapping-server-distributed SIDs**.

For native SR prefix-SIDs (advertised by the prefix owner), SR is always preferred over LDP regardless of `sr-prefer` — no configuration needed. The complexity arises with the mapping server: the prefix being mapped (e.g., 192.0.2.0/24) may have an LDP binding (distributed by the legacy PE that owns the prefix) AND an SR SID (distributed by the mapping server via TLV 149). Without `sr-prefer`, IOS-XR may use the LDP binding for the mapped prefix, defeating the purpose of the mapping server.

`sr-prefer` forces the FIB to choose the SR label from the mapping server TLV over the LDP binding, for every prefix where both exist.

```
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls sr-prefer
```

This is a per-router knob — you can apply it selectively during migration as each router's SR configuration is validated. In this lab, all four routers configure `sr-prefer` in the final solution state.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| LDP/SR parallel operation | Enable and verify LDP running alongside SR without disrupting SR forwarding |
| Label source inspection | Read the IOS-XR LFIB to identify whether a forwarding entry uses SR or LDP |
| Mapping server configuration | Allocate SID index ranges for non-native prefixes on an SR-capable router |
| SID/Label Binding TLV verification | Verify IS-IS TLV 149 distribution using database detail commands |
| SR-prefer | Understand when the knob matters and configure it to override LDP preference |
| Migration pattern | Model the phased LDP→SR migration sequence used in production |
| SRGB conflict diagnosis | Detect and fix mismatches between advertised SID indices and SRGB range |

---

## 2. Topology & Scenario

**Scenario:** Your team has completed the TI-LFA rollout across the SP core (lab-01). The next phase of the migration plan is to enable LDP in parallel with SR — this gives the NOC a fallback label path on every link while SR is being validated for production traffic. Simultaneously, a legacy PE at the customer edge (192.0.2.0/24) needs to be reachable via SR label even though it runs an older IOS version that does not support prefix-SID advertisement. R1 will serve as the SR mapping server for that prefix range.

```
                    ┌─────────────────────────┐
                    │           R1            │
                    │   (SP Edge / Mapping    │
                    │        Server)          │
                    │   Lo0: 10.0.0.1/32      │
                    │   SID index: 1 (16001)  │
                    └──┬──────────┬──────────┬┘
             Gi0/0/0/0 │          │Gi0/0/0/1 │Gi0/0/0/2
          10.1.12.1/24 │          │10.1.14.1/│10.1.13.1/24
                 L1    │          │  24  L4  │       L5
          10.1.12.2/24 │          │10.1.14.4/│10.1.13.3/24
             Gi0/0/0/0 │          │Gi0/0/0/1 │Gi0/0/0/2
        ┌──────────────┘          │           └─────────────────┐
        │                         │                             │
┌───────┴─────────────┐           │              ┌──────────────┴──────┐
│         R2          │           │              │         R3          │
│    (SP Core /       │           │              │    (SP Edge)        │
│   TI-LFA PLR)       │           │              │ Lo0: 10.0.0.3/32    │
│ Lo0: 10.0.0.2/32    │           │              │ SID index: 3 (16003)│
│ SID index: 2 (16002)│           │              └──────────┬──────────┘
└──────────┬──────────┘           │                         │Gi0/0/0/1
 Gi0/0/0/1 │                      │              10.1.34.3/24│   L3
10.1.23.2/24│  L2                 │              10.1.34.4/24│
10.1.23.3/24│                     │                 Gi0/0/0/0│
 Gi0/0/0/0 │                      │              ┌───────────┘
        ┌──┘                       └──────────────┤
        └──────────────────────────────────────────┤
                                            ┌──────┴──────────────┐
                                            │         R4          │
                                            │   (SP Core /        │
                                            │  Disjoint Path)     │
                                            │ Lo0: 10.0.0.4/32    │
                                            │ SID index: 4 (16004)│
                                            └─────────────────────┘

Link Table:
  L1: R1 Gi0/0/0/0 ↔ R2 Gi0/0/0/0   10.1.12.0/24   IS-IS L2 + SR-MPLS + LDP
  L2: R2 Gi0/0/0/1 ↔ R3 Gi0/0/0/0   10.1.23.0/24   IS-IS L2 + SR-MPLS + LDP
  L3: R3 Gi0/0/0/1 ↔ R4 Gi0/0/0/0   10.1.34.0/24   IS-IS L2 + SR-MPLS + LDP
  L4: R1 Gi0/0/0/1 ↔ R4 Gi0/0/0/1   10.1.14.0/24   IS-IS L2 + SR-MPLS + LDP
  L5: R1 Gi0/0/0/2 ↔ R3 Gi0/0/0/2   10.1.13.0/24   IS-IS L2 + SR-MPLS + LDP (diagonal)

Mapping Server (R1):
  192.0.2.0/24  → SID index 50, label 16050  (range 100)
```

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP Edge / SR Mapping Server | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R2 | SP Core / TI-LFA PLR | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R3 | SP Edge | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 |
| R4 | SP Core / Disjoint Path | IOS-XRv 9000 | xrv9k-fullk9-x.vrr.vga-24.3.1 |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, SR ingress, LDP router-id |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, LDP router-id |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, SR egress, LDP router-id |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, LDP router-id |

### Cabling

| Link | Source | Source Interface | Dest | Dest Interface | Subnet |
|------|--------|-----------------|------|----------------|--------|
| L1 | R1 | GigabitEthernet0/0/0/0 | R2 | GigabitEthernet0/0/0/0 | 10.1.12.0/24 |
| L2 | R2 | GigabitEthernet0/0/0/1 | R3 | GigabitEthernet0/0/0/0 | 10.1.23.0/24 |
| L3 | R3 | GigabitEthernet0/0/0/1 | R4 | GigabitEthernet0/0/0/0 | 10.1.34.0/24 |
| L4 | R1 | GigabitEthernet0/0/0/1 | R4 | GigabitEthernet0/0/0/1 | 10.1.14.0/24 |
| L5 | R1 | GigabitEthernet0/0/0/2 | R3 | GigabitEthernet0/0/0/2 | 10.1.13.0/24 |

### Console Access Table

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
- Hostnames
- Interface IP addressing (all routed links and Loopback0)
- IS-IS Level-2 process `CORE` with `metric-style wide` on all four routers
- SR-MPLS with SRGB 16000-23999 and per-node prefix SIDs (16001-16004)
- TI-LFA fast-reroute (`per-prefix` and `ti-lfa` knobs) on every IS-IS interface
- BFD with 50ms interval and multiplier 3 on every IS-IS interface

**IS NOT pre-loaded** (student configures this):
- LDP process and interface enablement
- SR mapping server for the 192.0.2.0/24 range
- IS-IS advertisement of mapping server entries (SID/Label Binding TLVs)
- SR-prefer label source override
- SR disable/re-enable anti-pattern exercise (Task 6)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable LDP in Parallel with SR

- Start an LDP process on each of the four core routers, sourcing sessions from Loopback0.
- Enable LDP on every core interface that carries IS-IS traffic: all interfaces participating in links L1 through L5.
- R1 has three active core interfaces (L1, L4, L5); R2 has two (L1, L2); R3 has three (L2, L3, L5); R4 has two (L3, L4).
- After enabling LDP, verify that LDP neighbor sessions form on every link.

**Verification:** `show mpls ldp neighbor` on each router must show an LDP neighbor for every adjacent router. `show mpls ldp bindings` must show LDP-distributed label bindings for all four loopback prefixes (10.0.0.1/32 through 10.0.0.4/32). `show mpls forwarding labels 16001 16004` on R2 must still show SR labels (16001-16004) for the loopback destinations — confirming SR preference is unaffected by enabling LDP.

---

### Task 2: Observe the Default SR/LDP Label Preference

- On R2, run `show route ipv4 10.0.0.3/32 detail`. Look for the `labeled SR` tag and the `Local Label` field — this tells you which label source the routing table chose and what local label R2 assigned for this prefix.
- Run `show mpls forwarding labels 16003 16003 detail` on R2. Confirm the entry shows `SR Pfx (idx 3)` — this is the SR forwarding entry.
- Run `show mpls forwarding prefix 10.0.0.3/32 detail` on R2. Note: this shows the **LDP** forwarding entry (a dynamically-allocated local label from outside the SRGB range). Both SR and LDP entries exist simultaneously; the routing table selects SR by default.
- Run `show mpls ldp bindings 10.0.0.3/32 detail` on R2 to see the LDP label bindings. The remote binding from R3 (ImpNull) and the local binding (dynamic label) will be visible — but neither is the active forwarding entry for IP-originated traffic.

**Verification:**
- `show route ipv4 10.0.0.3/32 detail` on R2 must show `labeled SR` and `Local Label: 16003` — confirming SR is the active label source.
- `show mpls forwarding labels 16003 16003 detail` on R2 must show `SR Pfx (idx 3)` with outgoing label `Pop` via Gi0/0/0/1.
- `show mpls forwarding prefix 10.0.0.3/32 detail` showing a local label outside the SRGB (e.g. 24xxx) is **expected and correct** — that is the LDP entry, which coexists but is not used for IP-originated traffic.

---

### Task 3: Configure R1 as the SR Mapping Server

The SR mapping server assigns SIDs to prefixes that ARE in the IS-IS topology but lack native SR prefix-SIDs — typically prefixes from LDP-only nodes. For the MPLS forwarding entry to be programmed on peers, the prefix must be reachable via IS-IS.

- On R1, create a static route for 192.0.2.0/24 pointing to Null0. This simulates an external or LDP-only prefix entering the SR domain.
- On R1, redistribute static routes into IS-IS CORE so the prefix is flooded to all routers.
- On R1, configure the SR mapping server to allocate SID index 50 with a range of 100 SIDs for the prefix 192.0.2.0/24.
- Verify the local mapping table on R1 — confirm the entry shows index 50 and the correct absolute label (SRGB_base + 50 = 16050).
- Configure IS-IS on R1 to originate SID/Label Binding TLVs for the local mapping entries so that all other routers learn the mapping via IS-IS.

**Verification:** `show segment-routing mapping-server prefix-sid-map ipv4` on R1 must show the 192.0.2.0/24 entry with SID index 50 and range 100. `show route ipv4 192.0.2.0/24` on R2 must show the prefix learned via IS-IS. `show isis database detail R1` on any router must show a SID/Label Binding TLV in R1's LSP for 192.0.2.0/24.

---

### Task 4: Verify Mapping Server Propagation to All Peers

- On R2, R3, and R4, confirm that each router received R1's SID/Label Binding TLV via IS-IS LSP flooding.
- On R2, verify that the FIB has installed a forwarding entry for 192.0.2.0/24 using the SR label 16050 as the outgoing label toward R1 (the mapping server origin).

**Verification:**
- `show isis segment-routing prefix-sid-map active-policy` on R2 must show the 192.0.2.0/24 to SID index 50 mapping received from R1.
- `show route ipv4 192.0.2.0/24 detail` on R2 must show `labeled SR(SRMS)` and `Local Label: 16050`.
- `show mpls forwarding labels 16050 16050 detail` on R2 must show `SR Pfx (idx 50)` with outgoing label `16050` toward R1 (Gi0/0/0/0). Note: `show mpls forwarding prefix 192.0.2.0/24` shows the LDP entry (dynamic local label) — use the label-based command to see the SR entry.

---

### Task 5: Configure and Verify SR-Prefer

- Configure the IS-IS SR-prefer knob on all four routers.
- On R2, create a test scenario: observe whether `show mpls forwarding prefix 192.0.2.0/24 detail` changes after applying `sr-prefer` (compared to before). Explain why the behavior may or may not change if an LDP binding for 192.0.2.0/24 is absent.
- Document the exact condition under which `sr-prefer` matters: when a prefix has BOTH an LDP binding (from a legacy PE) and an SR SID (from the mapping server), and you want SR to win.

**Verification:** `show running-config router isis CORE` on each router must show `segment-routing mpls sr-prefer` under `address-family ipv4 unicast`. `show mpls forwarding prefix 192.0.2.0/24 detail` on R2 must show an SR-sourced label (not LDP) if both label sources are present.

---

### Task 6: Anti-Pattern — Disable and Re-enable SR on R4

- On R4, remove SR from the IS-IS address-family (remove the `segment-routing mpls` stanza). Observe the effect on R1's view of R4's loopback.
- From R1, check `show mpls forwarding prefix 10.0.0.4/32 detail` — confirm R1 is now using an LDP label to reach R4 (SR label 16004 is gone from the FIB).
- Re-enable SR on R4 (`segment-routing mpls` under IS-IS af) and verify that R1's FIB returns to SR label 16004 for R4's loopback.
- This exercise models the post-migration cleanup scenario where a node is momentarily reverted and then corrected.

**Verification:** After SR is disabled on R4, `show isis database detail R4` on R2 must show no SR sub-TLV in R4's LSP. After re-enabling, `show mpls forwarding prefix 10.0.0.4/32 detail` on R1 must show outgoing label 16004 (SR), not an LDP label.

---

## 6. Verification & Analysis

### Task 1: LDP Neighbor Formation

```
R1# show mpls ldp neighbor

Peer LDP Identifier: 10.0.0.2:0; Local LDP Identifier: 10.0.0.1:0
    TCP connection: 10.0.0.2:646 - 10.0.0.1:20202
    State: Oper; Msgs sent/rcvd: 14/14; Downstream
    Up time: 00:01:12
    LDP discovery sources:
      GigabitEthernet0/0/0/0, Src IP addr: 10.1.12.2   ! ← R2 neighbor via L1

Peer LDP Identifier: 10.0.0.4:0; Local LDP Identifier: 10.0.0.1:0
    State: Oper; Up time: 00:01:10
    LDP discovery sources:
      GigabitEthernet0/0/0/1, Src IP addr: 10.1.14.4   ! ← R4 neighbor via L4

Peer LDP Identifier: 10.0.0.3:0; Local LDP Identifier: 10.0.0.1:0
    State: Oper; Up time: 00:01:08
    LDP discovery sources:
      GigabitEthernet0/0/0/2, Src IP addr: 10.1.13.3   ! ← R3 neighbor via L5
```

### Task 2: SR Preferred Over LDP

On IOS-XR with both SR and LDP active, two separate MPLS forwarding entries exist for the same prefix: one keyed by the SR local label (in the SRGB range), and one keyed by the LDP prefix. The routing table selects SR by default.

**Step 1 — Confirm SR wins in the routing table:**

```
R2# show route ipv4 10.0.0.3/32 detail

Routing entry for 10.0.0.3/32
  Known via "isis CORE", distance 115, metric 10, labeled SR, type level-2
  ...
  Routing Descriptor Blocks
    10.1.23.3, from 10.0.0.3, via GigabitEthernet0/0/0/1, Protected
      Route metric is 10
      Label: 0x3 (3)       ! ← outgoing label 3 = Implicit-null (PHP from R3 via SR)
  ...
  Local Label: 0x3e83 (16003)  ! ← R2's SR local label — inside the SRGB (16000-23999)
```

> `labeled SR` and `Local Label: 16003` confirm SR is the active label source for this prefix.

**Step 2 — View the SR forwarding entry:**

```
R2# show mpls forwarding labels 16003 16003 detail

Local  Outgoing    Prefix             Outgoing     Next Hop
Label  Label       or ID              Interface
------ ----------- ------------------ ------------ ---------------
16003  Pop         SR Pfx (idx 3)     Gi0/0/0/1    10.1.23.3       ! ← SR entry; Pop = PHP (R3 is adjacent)
       16003       SR Pfx (idx 3)     Gi0/0/0/0    10.1.12.1   (!) ! ← TI-LFA backup via R1
```

**Step 3 — View the LDP forwarding entry (coexists, not used for IP traffic):**

```
R2# show mpls forwarding prefix 10.0.0.3/32 detail

Local  Outgoing    Prefix             Outgoing     Next Hop
Label  Label       or ID              Interface
------ ----------- ------------------ ------------ ---------------
24008  Pop         10.0.0.3/32        Gi0/0/0/1    10.1.23.3       ! ← LDP entry; local label is dynamic (outside SRGB)
       24010       10.0.0.3/32        Gi0/0/0/0    10.1.12.1   (!) ! ← LDP backup via R1
```

> `show mpls forwarding prefix` always shows the **LDP entry** on IOS-XR — the local label (24xxx) is dynamically allocated outside the SRGB. This entry coexists with the SR entry but is not used for IP-originated traffic. SR wins by default because R3 advertised a native prefix-SID (index 3) via IS-IS.

```
R2# show mpls ldp bindings 10.0.0.3/32 detail
10.0.0.3/32, rev 36
        Local binding: label: 24008          ! ← R2's LDP local label (dynamic, not 16003)
        Remote bindings:
            Peer                Label
            -----------------   ---------
            10.0.0.1:0          24010        ! ← R1's LDP label for 10.0.0.3/32
            10.0.0.3:0          ImpNull      ! ← R3 signals PHP via LDP
```

### Task 3: Mapping Server Local Table

```
R1# show segment-routing mapping-server prefix-sid-map ipv4

Prefix               SID Index    Range        Flags
192.0.2.0/24         50           100          

Number of mapping entries: 1
```

> Note: the Flags column is empty — the `M` (mirror) flag is NOT shown on the local mapping server's own table. It only appears in the IS-IS LSP Binding TLV as `M:0` or `M:1`.

```
R1# show route ipv4 192.0.2.0/24

Routing entry for 192.0.2.0/24
  Known via "static", distance 1, metric 0 (connected)
    directly connected, via Null0
```

> 192.0.2.0/24 must be in R1's routing table (via static → Null0 + redistribute static into IS-IS). Without it, no MPLS forwarding entry will be programmed on any peer.

### Task 4: SID/Label Binding TLV in IS-IS LSP and FIB Programming

```
R2# show isis database detail R1 | include 192.0

  SID Binding:    192.0.2.0/24 F:0 M:0 S:0 D:0 A:0 Weight:0 Range:100
```

```
R2# show isis segment-routing prefix-sid-map active-policy

IS-IS CORE active policy
Prefix               SID Index    Range        Flags
192.0.2.0/24         50           100          

Number of mapping entries: 1
```

```
R2# show route ipv4 192.0.2.0/24 detail

Routing entry for 192.0.2.0/24
  Known via "isis CORE", distance 115, metric 10, labeled SR(SRMS), type level-2
  ...
  Routing Descriptor Blocks
    10.1.12.1, from 10.0.0.1, via GigabitEthernet0/0/0/0, Protected
      Label: 0x3eb2 (16050)           ! ← SR(SRMS) label = SRGB base 16000 + index 50
  Local Label: 0x3eb2 (16050)        ! ← R2 assigns 16050 as its local label for this prefix
```

> `labeled SR(SRMS)` confirms the SR Mapping Server label is active (not LDP). The outgoing label is 16050 — NOT Pop — because R1 is the "origin" of this mapping but not an SR-native node for this prefix, so no PHP applies.

```
R2# show mpls forwarding labels 16050 16050 detail

Local  Outgoing    Prefix             Outgoing     Next Hop
Label  Label       or ID              Interface
------ ----------- ------------------ ------------ ---------------
16050  16050       SR Pfx (idx 50)    Gi0/0/0/0    10.1.12.1       ! ← SR(SRMS) entry; label 16050 imposed toward R1
       16050       SR Pfx (idx 50)    Gi0/0/0/1    10.1.23.3   (!) ! ← TI-LFA backup
```

### Task 6: SR Disabled on R4 — LDP Fallback

```
R1# show mpls forwarding prefix 10.0.0.4/32 detail

! After SR disabled on R4:
Local  Outgoing    Prefix       Outgoing     Next Hop
Label  Label       or ID        Interface
------ ----------- ------------ ------------ ---------------
       100004      10.0.0.4/32  Gi0/0/0/1    10.1.14.4   ! ← LDP label (no SR entry — R4 no longer has SID)

! After SR re-enabled on R4:
16004  Pop         SR Pfx (idx 4)  Gi0/0/0/1    10.1.14.4   ! ← SR label restored; 16004 is penultimate pop
```

---

## 7. Verification Cheatsheet

### LDP Configuration

```
mpls ldp
 router-id <loopback-address>
 interface <interface-name>
 !
```

| Command | Purpose |
|---------|---------|
| `show mpls ldp neighbor` | List all active LDP neighbors and their discovery source interfaces |
| `show mpls ldp bindings` | Show all LDP label bindings (local and remote) |
| `show mpls ldp bindings <prefix>/<len> detail` | Show LDP bindings for a specific prefix |
| `show mpls ldp discovery` | Show LDP hello discovery state per interface |
| `show mpls ldp statistics` | LDP session message counters |

> **Exam tip:** LDP router-id determines which loopback address is used for the LDP session TCP connection. On IOS-XR, if router-id is not set explicitly, LDP picks the highest loopback IP — always set it explicitly for predictability.

### SR Mapping Server Configuration

```
segment-routing
 mapping-server
  prefix-sid-map
   address-family ipv4
    <prefix>/<len> <start-index> range <count>

router isis CORE
 address-family ipv4 unicast
  segment-routing prefix-sid-map advertise-local
```

| Command | Purpose |
|---------|---------|
| `show segment-routing mapping-server prefix-sid-map ipv4` | Show locally configured mapping entries |
| `show segment-routing mapping-server prefix-sid-map ipv4 detail` | Show mapping entries with SRGB-resolved absolute labels |
| `show isis database detail <router-id>` | Inspect IS-IS LSP for SID/Label Binding TLVs (TLV 149) |
| `show isis segment-routing prefix-sid-map active-policy` | Show all active mapping entries received from mapping servers |

> **Exam tip:** The mapping server entry syntax `<prefix> <start-index> range <count>` does NOT automatically mean the non-SR node has that prefix in its RIB. The mapping server only creates the SID → prefix binding in IS-IS; the prefix must arrive via IS-IS redistribution or another mechanism for the FIB entry to be installed.

### SR-Prefer Configuration

```
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls sr-prefer
```

| Command | Purpose |
|---------|---------|
| `show mpls forwarding <prefix>/<len> detail` | Show which label source (SR or LDP) is active in the FIB |
| `show running-config router isis CORE` | Confirm sr-prefer is present under address-family |

> **Exam tip:** `sr-prefer` only matters when a prefix has BOTH an LDP binding and an SR SID from the mapping server. For native SR prefix-SIDs, SR always wins over LDP without any `sr-prefer` configuration. The command is specifically for the mapping-server coexistence scenario.

### MPLS Forwarding Verification

```
! Show SR label for a specific prefix
show mpls forwarding labels 16001 16004

! Show forwarding detail (label source identification)
show mpls forwarding <prefix>/<len> detail
```

| Command | Purpose |
|---------|---------|
| `show mpls forwarding` | Full LFIB table — outgoing labels, interfaces, next-hops |
| `show mpls forwarding labels <start> <end>` | Show forwarding entries for a label range |
| `show mpls forwarding <prefix>/<len>` | Show forwarding entry for a specific IP prefix |
| `show mpls forwarding <prefix>/<len> detail` | Include label source (SR, LDP) and programming details |

### Common LDP/SR Coexistence Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| LDP neighbor not forming on an interface | LDP not enabled on that interface; check `show mpls ldp discovery` |
| LDP label in FIB instead of SR for native SR prefix | SR not enabled under IS-IS af on one peer; `segment-routing mpls` missing |
| Mapping server entry not in peers' active policy | `segment-routing prefix-sid-map advertise-local` missing under IS-IS af on mapping server |
| Mapping server label conflict on a peer | Peer's SRGB too small for the advertised SID index; check `show running-config segment-routing` for the `global-block` range |
| SR label for mapped prefix not in FIB | `sr-prefer` not configured when LDP binding for same prefix exists |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Enable LDP in Parallel with SR

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
mpls ldp
 router-id 10.0.0.1
 interface GigabitEthernet0/0/0/0
 !
 interface GigabitEthernet0/0/0/1
 !
 interface GigabitEthernet0/0/0/2
 !
!
commit
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
mpls ldp
 router-id 10.0.0.2
 interface GigabitEthernet0/0/0/0
 !
 interface GigabitEthernet0/0/0/1
 !
!
commit
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
mpls ldp
 router-id 10.0.0.3
 interface GigabitEthernet0/0/0/0
 !
 interface GigabitEthernet0/0/0/1
 !
 interface GigabitEthernet0/0/0/2
 !
!
commit
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
mpls ldp
 router-id 10.0.0.4
 interface GigabitEthernet0/0/0/0
 !
 interface GigabitEthernet0/0/0/1
 !
!
commit
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp neighbor
show mpls ldp bindings
show mpls forwarding labels 16001 16004
```
</details>

---

### Task 2: Observe the Default SR/LDP Label Preference

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R2 — confirm SR label is active for R3's loopback
R2# show mpls forwarding prefix 10.0.0.3/32 detail
! Look for: Outgoing label = 16003 (SR) or Pop (penultimate R2), source = SR Pfx

! On R2 — confirm LDP binding exists but is NOT the active FIB entry
R2# show mpls ldp bindings 10.0.0.3/32 detail
! Look for: Remote binding with a non-16003 label from peer 10.0.0.3

! Summary: SR label wins because R3 has a native prefix-SID (index 3).
! No sr-prefer configuration is needed for native SR prefix-SIDs.
```
</details>

---

### Task 3: Configure R1 as SR Mapping Server

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
segment-routing
 mapping-server
  prefix-sid-map
   address-family ipv4
    192.0.2.0/24 50 range 100
   !
  !
 !
!
router isis CORE
 address-family ipv4 unicast
  segment-routing prefix-sid-map advertise-local
 !
!
commit
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show segment-routing mapping-server prefix-sid-map ipv4
show isis database detail R1
```
</details>

---

### Task 4: Verify Mapping Server Propagation to All Peers

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R2 — confirm R1's SID/Label Binding TLV is present in the IS-IS database
R2# show isis database detail R1
! Look for SID/Label Binding section: FEC prefix 192.0.2.0/24, SID Index 50, Range 100

! On R2 — confirm the active mapping policy shows the entry received from R1
R2# show isis segment-routing prefix-sid-map active-policy
! 192.0.2.0/24 should appear with SID 50 (label 16050), attributed to R1 (M flag = mapping server)

! On R2 — confirm the MPLS FIB has an entry for the mapped prefix
R2# show mpls forwarding prefix 192.0.2.0/24
! An MPLS forwarding entry must be present; next-hop will be toward R1 via L1 (Gi0/0/0/0)
! or via L5/L4 depending on IGP path — outgoing label encodes the SR path to the mapping server origin
```
</details>

---

### Task 5: Configure SR-Prefer on All Routers

<details>
<summary>Click to view R1-R4 Configuration</summary>

```bash
! Apply on R1, R2, R3, R4 (same config on each)
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls sr-prefer
 !
!
commit
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config router isis CORE
show mpls forwarding prefix 192.0.2.0/24 detail
```
</details>

---

### Task 6: Anti-Pattern — Disable and Re-enable SR on R4

<details>
<summary>Click to view R4 Configuration — SR Disable (fault state)</summary>

```bash
! R4 — remove SR from IS-IS address-family
router isis CORE
 address-family ipv4 unicast
  no segment-routing mpls
 !
!
commit
! Observe: R4's prefix-SID sub-TLV disappears from IS-IS LSP; peers fall back to LDP label
```
</details>

<details>
<summary>Click to view Verification Commands (fault state)</summary>

```bash
! On R2 — confirm R4's LSP no longer contains an SR sub-TLV
R2# show isis database detail R4
! SR-Algorithm and prefix-SID sub-TLVs should be absent from R4.00-00

! On R1 — confirm R1 is now using an LDP label to reach R4's loopback
R1# show mpls forwarding prefix 10.0.0.4/32 detail
! Outgoing label will be an LDP-assigned label (NOT 16004); label source = LDP
```
</details>

<details>
<summary>Click to view R4 Configuration — SR Re-enable (fix state)</summary>

```bash
! R4 — restore SR under IS-IS address-family
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls
 !
!
commit
! Verify:
! On R1:
show mpls forwarding prefix 10.0.0.4/32 detail
! Outgoing label must return to Pop or 16004 (SR Pfx idx 4); label source = SR Pfx
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

> **Prerequisite:** Complete Tasks 1-5 before injecting faults. The inject scripts
> require the full solution state (LDP running, mapping server configured, sr-prefer active).
> `setup_lab.py` pushes initial-configs (no LDP, no mapping server) — use `apply_solution.py`
> to reach the solution state needed for troubleshooting.

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # reset to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>         # restore after each
```

---

### Ticket 1 — R3 Cannot Install the Mapping Server Label for 192.0.2.0/24

The operations team updated the SRGB configuration on R3 during a change window. Shortly after, a monitoring script reports that the mapping server label for 192.0.2.0/24 is not being installed on R3. The prefix is reachable via IP, but SR-based label switching to the customer prefix is broken on R3.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show segment-routing mapping-server prefix-sid-map ipv4` on R3 shows the 192.0.2.0/24 mapping entry with label 16050 installed (no conflict). `show mpls forwarding prefix 192.0.2.0/24` on R3 shows an MPLS forwarding entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Check mapping server active policy on R3
R3# show isis segment-routing prefix-sid-map active-policy
! Look for 192.0.2.0/24 — is the entry present or missing/conflicted?

! Step 2: Check the SRGB on R3
R3# show running-config segment-routing
! Look at global-block start/end — is 16050 (base + index 50) within the range?

! Step 3: Check SRGB configuration directly
R3# show running-config segment-routing
! Look at global-block values — the end label determines the maximum allocatable SID

! Step 4: Check label table for allocation conflicts
R3# show mpls label table
! Look for 16050 — if absent, the SRGB is too small to reach that label
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3's SRGB was shrunk below index 50 (label 16050 = SRGB_base + 50 = 16000 + 50)
! Fix: restore the full SRGB range so label 16050 falls within the block
R3# conf t
segment-routing
 global-block 16000 23999
!
commit
! Verify on R3 (the peer that had the SRGB conflict):
R3# show isis segment-routing prefix-sid-map active-policy
! 192.0.2.0/24 should now appear with SID index 50 — no conflict flag
R3# show mpls forwarding prefix 192.0.2.0/24
! Outgoing label should be 16050 (SRGB base 16000 + index 50)
```
</details>

---

### Ticket 2 — R2 Is Forwarding 192.0.2.0/24 via LDP Instead of SR

A traffic-engineering audit shows that traffic destined to the legacy customer prefix 192.0.2.0/24 is not following the SR path on R2. The intent of the mapping server was to enable SR-based steering for this prefix, but R2 appears to be ignoring the SR label.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show mpls forwarding prefix 192.0.2.0/24 detail` on R2 shows the SR mapping-server label (not an LDP label) as the outgoing label.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Check what label R2 is actually using for 192.0.2.0/24
R2# show mpls forwarding prefix 192.0.2.0/24 detail
! Note the label source: is it SR (from mapping server) or LDP?

! Step 2: Verify the mapping server entry is present
R2# show isis segment-routing prefix-sid-map active-policy
! 192.0.2.0/24 should appear — if it's missing, the issue is IS-IS flooding, not sr-prefer

! Step 3: Check LDP binding for 192.0.2.0/24
R2# show mpls ldp bindings 192.0.2.0/24 detail
! If an LDP binding exists for this prefix AND sr-prefer is missing, LDP wins

! Step 4: Inspect IS-IS sr-prefer config
R2# show running-config router isis CORE
! Look for 'segment-routing mpls sr-prefer' under address-family ipv4 unicast
! If absent, LDP label is being used for the mapped prefix instead of SR
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! sr-prefer was removed from R2's IS-IS address-family
! Fix: restore the knob so SR labels win over LDP for mapping-server prefixes
R2# conf t
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls sr-prefer
 !
!
commit
! Verify:
show mpls forwarding prefix 192.0.2.0/24 detail
! Outgoing label should now be 16050 (SR mapping-server), not an LDP label
```
</details>

---

### Ticket 3 — R4 Reports No LDP Neighbor on the R1 Link

The NOC received an alert that LDP adjacency between R4 and R1 on link L4 is missing. All IS-IS adjacencies and SR forwarding are intact on L4, but LDP label distribution for R1's prefixes is not occurring via L4.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show mpls ldp neighbor` on R4 shows R1 (10.0.0.1) as an LDP neighbor with discovery source GigabitEthernet0/0/0/1. `show mpls ldp bindings 10.0.0.1/32` on R4 shows a remote binding from R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
! Step 1: Confirm R4's LDP neighbor list
R4# show mpls ldp neighbor
! R1 (10.0.0.1) should appear as a neighbor — if absent, LDP is not discovering on L4

! Step 2: Check LDP discovery on L4
R4# show mpls ldp discovery detail
! Look for GigabitEthernet0/0/0/1 — is it listed as an LDP discovery interface?
! If the interface is absent from discovery, it is not enabled under 'mpls ldp'

! Step 3: Inspect R4's LDP configuration
R4# show running-config mpls ldp
! Verify GigabitEthernet0/0/0/1 appears under 'mpls ldp'
! If missing, LDP hellos are not sent on L4 and no session can form

! Step 4: Confirm IS-IS and IP are still up on L4
R4# show isis adjacency
R4# show interface GigabitEthernet0/0/0/1 brief
! IS-IS adjacency to R1 should still be up — confirms only LDP is affected
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! GigabitEthernet0/0/0/1 was removed from LDP on R4
! Fix: re-add the interface to the LDP process
R4# conf t
mpls ldp
 interface GigabitEthernet0/0/0/1
 !
!
commit
! Verify:
show mpls ldp neighbor
! R1 (10.0.0.1) must appear with GigabitEthernet0/0/0/1 as discovery source
show mpls ldp bindings 10.0.0.1/32
! Remote binding from 10.0.0.1 must be present
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] LDP process running on R1, R2, R3, R4 with Loopback0 as router-id
- [ ] LDP neighbors formed on all five core links (L1-L5)
- [ ] SR labels (16001-16004) remain active in R2's FIB after LDP is enabled
- [ ] LDP label for R3's loopback visible in `show mpls ldp bindings` but NOT in the FIB (SR wins)
- [ ] SR mapping server configured on R1 for 192.0.2.0/24, start index 50, range 100
- [ ] IS-IS advertisement of mapping server entries enabled on R1
- [ ] Peers (R2, R3, R4) show 192.0.2.0/24 in `show isis segment-routing prefix-sid-map active-policy`
- [ ] `segment-routing mpls sr-prefer` configured under IS-IS af on R1, R2, R3, R4
- [ ] SR disabled/re-enabled on R4 — LDP fallback observed and corrected

### Troubleshooting

- [ ] Ticket 1: R3 SRGB conflict diagnosed via `show running-config segment-routing`; fixed by restoring `global-block 16000 23999`
- [ ] Ticket 2: R2 sr-prefer missing diagnosed via `show running-config router isis CORE`; fixed by restoring `segment-routing mpls sr-prefer`
- [ ] Ticket 3: R4 LDP interface missing diagnosed via `show mpls ldp discovery detail`; fixed by re-adding GigabitEthernet0/0/0/1 to `mpls ldp`

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
