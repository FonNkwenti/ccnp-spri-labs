# Lab 00 — PIM-SM Foundations

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

**Exam Objective:** 2.1 / 2.1.a / 2.1.b / 2.2.a / 2.2.c / 2.2.f / 2.3 / 2.4.a — Multicast Routing: PIM-SM Foundations

This lab establishes the multicast foundation used in every subsequent lab in the chapter. You configure IS-IS L2 as the unicast underlay, enable PIM-SM with a static Rendezvous Point (RP) on all four routers, and observe the full lifecycle of a multicast session: IGMP join from a real Linux receiver, shared-tree (*, G) state creation at the RP, source registration by the first-hop router, and automatic SPT switchover at the last-hop router. The chapter uses two Ubuntu 20.04 VMs — SRC1 and RCV1 — to generate and receive real UDP multicast traffic, making IGMP timing, PIM Register messages, and SPT switchover directly observable in a way that loopback-ping simulation cannot replicate.

### PIM Sparse Mode Architecture

Protocol Independent Multicast Sparse Mode (PIM-SM) is defined in RFC 7761. It is "protocol independent" because it does not build its own unicast routing table — instead, it relies on the existing unicast RIB for the Reverse Path Forwarding (RPF) check that determines which interface multicast traffic must arrive on to be forwarded.

PIM-SM uses a Rendezvous Point (RP) as a meeting place between senders and receivers. A router that has receivers for a group sends a PIM Join message toward the RP; a router that has sources registers those sources with the RP via PIM Register unicast messages. Once the RP has both a sender and receiver, traffic flows down the Rendezvous Point Tree (RPT), also called the shared tree.

Key PIM-SM control-plane messages:

| Message | Direction | Purpose |
|---------|-----------|---------|
| Hello | Multicast (224.0.0.13) | Discover PIM neighbors; elect Designated Router (DR) |
| Join/Prune | Toward RP | Build or teardown (*,G) shared tree state |
| Register | Unicast to RP | First-hop router encapsulates source data; signals RP |
| Register-Stop | Unicast to first-hop | RP stops encapsulation once (S,G) native path is built |
| Assert | Multicast segment | Elect forwarder when multiple routers are on the same LAN |

The Designated Router (DR) on a multi-access segment is responsible for sending PIM Joins toward the RP on behalf of IGMP-joined receivers. DR election uses the highest IP address (after any priority tie-breaking).

### Multicast Distribution Trees: RPT vs. SPT

PIM-SM builds two distinct tree types:

**Rendezvous Point Tree (RPT) — shared tree:**
- Root at the RP (R1 = 10.0.0.1 in this lab)
- Identified by (*,G) notation — any source, one group
- Built when a receiver joins: last-hop router sends PIM Join (*, G) toward RP
- Traffic path: Source → first-hop router → RP → all receivers on the shared tree

**Shortest Path Tree (SPT) — source-specific tree:**
- Root at the source subnet (R2's Gi0/2 segment in this lab)
- Identified by (S,G) notation — specific source IP, specific group
- Built when last-hop router triggers SPT switchover after receiving the first packet via RPT
- Traffic path: Source → first-hop router → directly toward last-hop router (bypasses RP)

SPT switchover sequence at R4 (the last-hop router):
1. RCV1 sends IGMP Report → R4 sends (*,G) Join toward RP
2. First multicast packet arrives at R4 via RPT (through R1)
3. R4 immediately sends (S,G) Join toward the source (192.168.2.10 via R2)
4. R4 receives traffic on the SPT; it sends (*,G) Prune toward RP to stop shared-tree traffic
5. R1 (RP) sends Register-Stop to R2 once the (S,G) native path is established

After switchover, R1 carries no multicast data — only R2 and R4 remain in the forwarding path.

### IGMP and Host-to-Router Signaling

Internet Group Management Protocol (IGMP) is used between a host (RCV1) and its local router (R4) to signal group membership. When PIM sparse-mode is enabled on an interface, IOS automatically enables IGMP on that interface and elects the router as the IGMP Querier (the router with the lowest IP address on the segment).

**IGMPv2 operation** (default on IOSv):

| Message | Sender | Purpose |
|---------|--------|---------|
| General Query | IGMP Querier | Solicits membership reports for all groups |
| Membership Report | Host | Signals join for a specific group |
| Leave Group | Host | Signals intent to leave; querier sends Group-Specific Query to confirm |
| Group-Specific Query | IGMP Querier | Verifies remaining members after a Leave is received |

When RCV1 runs `mcjoin -g 239.1.1.1 -i ens3`, the Linux kernel sends an IGMPv2 Membership Report for 239.1.1.1 out ens3. R4 receives this report on Gi0/1, creates an IGMP group table entry, and triggers a PIM (*,G) Join toward the RP (10.0.0.1 = R1).

### Multicast IP-to-MAC Address Mapping

**Blueprint 2.2.a** — Every IPv4 multicast address maps to a Layer-2 Ethernet multicast MAC address using a fixed rule defined in RFC 1112:

1. Start with the IANA-reserved OUI prefix: **01:00:5e**
2. Clear the top bit of the 4th byte: always **0**x in the 4th byte
3. Map the lower **23 bits** of the multicast IP address into the last 3 bytes of the MAC

For group **239.1.1.1**:
- 239.1.1.1 in hex = EF.01.01.01
- Lower 23 bits = 0x010101 (mask 0x007FFFFF applied to 0xEF010101)
- MAC = **01:00:5e:01:01:01**

The 23-bit mapping creates a 32:1 address collision — 32 different IP multicast groups map to the same MAC. For example, 239.1.1.1 and 7.1.1.1 both map to 01:00:5e:01:01:01. IGMP snooping-aware switches use the MAC to flood frames to the correct ports; IP-level disambiguation happens at the router.

Verify with `tcpdump` on RCV1 once traffic is flowing:
```bash
sudo tcpdump -i ens3 ether host 01:00:5e:01:01:01 -v -c 5
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IS-IS L2 unicast underlay | Configure IS-IS level-2-only as the routing foundation for the multicast domain |
| PIM-SM global and interface activation | Enable multicast routing globally; configure PIM sparse-mode on all interfaces |
| Static RP configuration | Assign a static Rendezvous Point address on all PIM routers |
| IGMP verification | Read IGMP group tables to confirm receiver signaling |
| Multicast state table interpretation | Distinguish (*,G) shared tree entries from (S,G) source-specific entries |
| SPT switchover observation | Recognize when the last-hop router switches from shared tree to source tree |
| RPF troubleshooting | Use `show ip rpf` to diagnose multicast forwarding failures |
| MAC-address mapping | Derive the L2 multicast MAC from an IPv4 group address |

---

## 2. Topology & Scenario

**Scenario:** You are a service provider network engineer deploying IP multicast for the first time in AS 65100. The core consists of four IOSv routers running IS-IS L2. Two Ubuntu 20.04 VMs — SRC1 (a content source) and RCV1 (a subscriber) — are connected to the edge. Your task is to enable PIM-SM throughout the domain, configure R1 as the static RP, and verify that a live UDP multicast stream from SRC1 reaches RCV1 with correct IGMP signaling, shared-tree state, and SPT switchover.

```
                 ┌──────────────────────────────────────┐
                 │                SRC1                  │
                 │   Ubuntu 20.04 · 192.168.2.10/24     │
                 │         default gw 192.168.2.1       │
                 └─────────────────┬────────────────────┘
                                   │ ens3
                                   │ 192.168.2.0/24 (L6)
                             Gi0/2 │ 192.168.2.1
                 ┌─────────────────┴────────────────────┐
                 │                 R2                    │
                 │          Lo0: 10.0.0.2/32             │
                 │   first-hop PIM router for SRC1       │
                 └──────────┬────────────────────┬───────┘
                      Gi0/0 │ 10.10.12.2   Gi0/1 │ 10.10.23.1
                            │                    │
              L1 10.10.12.0/30      L2 10.10.23.0/30
                            │                    │
                      Gi0/0 │ 10.10.12.1   Gi0/0 │ 10.10.23.2
         ┌──────────────────┴──┐           ┌─────┴───────────────┐
         │          R1          │    L3     │          R3          │
         │   Lo0: 10.0.0.1/32  ├───────────┤   Lo0: 10.0.0.3/32  │
         │   Static RP (all)   │10.10.13.0 │   IS-IS L2 transit  │
         │   Gi0/1 10.10.13.1  │    /30    │   Gi0/1 10.10.13.2  │
         └──────────┬──────────┘           └─────────────────────┘
               Gi0/2│ 10.10.14.1
                    │ L4 10.10.14.0/30
               Gi0/0│ 10.10.14.2
         ┌──────────┴──────────┐
         │          R4          │
         │   Lo0: 10.0.0.4/32  │
         │   last-hop PIM / IGMP querier for RCV1  │
         └──────────┬──────────┘
               Gi0/1│ 192.168.4.1
                    │ 192.168.4.0/24 (L7)
                    │ ens3
                 ┌──┴───────────────────────────────────┐
                 │                RCV1                  │
                 │   Ubuntu 20.04 · 192.168.4.10/24     │
                 │         default gw 192.168.4.1       │
                 └──────────────────────────────────────┘
```

**Link Summary:**

| Link | Devices | Subnet |
|------|---------|--------|
| L1 | R1 Gi0/0 ↔ R2 Gi0/0 | 10.10.12.0/30 |
| L2 | R2 Gi0/1 ↔ R3 Gi0/0 | 10.10.23.0/30 |
| L3 | R1 Gi0/1 ↔ R3 Gi0/1 | 10.10.13.0/30 |
| L4 | R1 Gi0/2 ↔ R4 Gi0/0 | 10.10.14.0/30 |
| L6 | R2 Gi0/2 ↔ SRC1 ens3 | 192.168.2.0/24 |
| L7 | R4 Gi0/1 ↔ RCV1 ens3 | 192.168.4.0/24 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | Static RP; IS-IS L2 hub | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | First-hop PIM router; SRC1 gateway | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | IS-IS L2 transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | Last-hop PIM router; IGMP querier for RCV1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| SRC1 | Multicast source (mcjoin) | Linux | linux-ubuntu-server-20.04 | 1024 MB |
| RCV1 | Multicast receiver (mcjoin / tcpdump) | Linux | linux-ubuntu-server-20.04 | 1024 MB |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID; static RP address; PIM-enabled |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID; IS-IS advertisement |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID; IS-IS advertisement |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID; IS-IS advertisement |

### Cabling

| Link | Local Device | Local Interface | Remote Device | Remote Interface | Subnet |
|------|-------------|-----------------|---------------|------------------|--------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.10.12.0/30 |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.10.23.0/30 |
| L3 | R1 | Gi0/1 | R3 | Gi0/1 | 10.10.13.0/30 |
| L4 | R1 | Gi0/2 | R4 | Gi0/0 | 10.10.14.0/30 |
| L6 | R2 | Gi0/2 | SRC1 | ens3 | 192.168.2.0/24 |
| L7 | R4 | Gi0/1 | RCV1 | ens3 | 192.168.4.0/24 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SRC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| RCV1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on R1, R2, R3, R4
- DNS lookup disabled on all routers
- Interface IP addressing on all routed links (Loopback0, Gi0/0–Gi0/2 as applicable per device)
- Source segment IP on R2 Gi0/2 (192.168.2.1/24) and receiver segment IP on R4 Gi0/1 (192.168.4.1/24)

**IS NOT pre-loaded** (student configures this):
- IS-IS routing process and neighbor adjacencies
- IS-IS interface activation on all routers
- Multicast routing (globally)
- Static Rendezvous Point address
- PIM sparse-mode on all interfaces (including Loopback0 and stub segments)
- Default routes and mcjoin tool on SRC1 and RCV1
- Any IGMP, mroute, or PIM verification state

> **SRC1 and RCV1 are Linux VMs.** Their IP addressing and default gateway are configured manually after boot — they are not pushed by `setup_lab.py`. See Task 4 for the Linux configuration procedure.

---

## 5. Lab Challenge: Core Implementation

### Task 1: IS-IS L2 Underlay

- Enable IS-IS level-2-only on R1, R2, R3, and R4 using process tag `1`.
- Assign each router its IS-IS NET address from the table below. The area is `49.0001`; the system ID encodes the router number in the last segment.

| Router | NET Address |
|--------|-------------|
| R1 | 49.0001.0000.0000.0001.00 |
| R2 | 49.0001.0000.0000.0002.00 |
| R3 | 49.0001.0000.0000.0003.00 |
| R4 | 49.0001.0000.0000.0004.00 |

- Enable IS-IS on Loopback0 and on all point-to-point links between routers (L1, L2, L3, L4). Also enable IS-IS on the stub segments (R2 Gi0/2, R4 Gi0/1), but mark them as passive interfaces — IS-IS will advertise the stub prefix into the link-state database without sending Hello PDUs toward the Linux hosts. This is required so that all routers can perform RPF lookups against the source subnet (192.168.2.0/24) and the receiver subnet (192.168.4.0/24).
- Verify all four IS-IS L2 adjacencies form and that all loopback addresses appear in the IS-IS RIB on every router.

**Verification:** `show isis neighbors` must show State=UP for every expected neighbor pair. `show ip route isis` on any router must show all four /32 loopback prefixes with `[115/10]` or similar IS-IS metric.

---

### Task 2: Enable Multicast Routing and Configure the Static RP

- Enable IP multicast routing globally on R1, R2, R3, and R4.
- Configure all four routers to use 10.0.0.1 (R1 Loopback0) as the static Rendezvous Point for all groups.

**Verification:** `show ip pim rp mapping` on any router must show RP 10.0.0.1 for group 224.0.0.0/4 (or "all groups").

---

### Task 3: Enable PIM Sparse Mode on All Interfaces

- Enable PIM sparse-mode on every interface of R1, R2, R3, and R4 — including Loopback0, all IS-IS transit links, and the stub segments toward SRC1 (R2 Gi0/2) and RCV1 (R4 Gi0/1).
- Enabling PIM sparse-mode on Loopback0 of R1 is required so that the RP address is PIM-reachable from within the domain.

**Verification:** `show ip pim interface` must show all relevant interfaces as PIM-enabled. `show ip pim neighbor` on R1 must show neighbors on Gi0/0 (R2), Gi0/1 (R3), and Gi0/2 (R4). Confirm DR election on each transit link.

---

### Task 4: Prepare the Linux Traffic Hosts

- On **SRC1**: configure a default route pointing to 192.168.2.1 (R2 Gi0/2). Install `mcjoin` via the Ubuntu package manager. Confirm that SRC1 can ping R2 at 192.168.2.1.
- On **RCV1**: configure a default route pointing to 192.168.4.1 (R4 Gi0/1). Install `mcjoin`. Confirm that RCV1 can ping R4 at 192.168.4.1.
- Verify that R2 can ping SRC1 at 192.168.2.10, and that R4 can ping RCV1 at 192.168.4.10.

**Verification:** `ping 192.168.2.1` from SRC1 succeeds. `ping 192.168.4.1` from RCV1 succeeds. `ping 192.168.2.10` from R2 succeeds. `ping 192.168.4.10` from R4 succeeds.

---

### Task 5: Join the Multicast Group and Verify IGMP State

- On **RCV1**, run the `mcjoin` tool in receive mode, joining group 239.1.1.1 on interface ens3. Leave the receiver running in the background while you verify state on the routers.
- On **R4**, verify that an IGMP membership entry for 239.1.1.1 has been created on the Gi0/1 interface.
- On **R1** (the RP), verify that a (*,G) shared-tree entry for 239.1.1.1 has been created. At this point there is no source, so the Outgoing Interface List (OIL) should show the downstream path toward R4.

**Verification:** `show ip igmp groups` on R4 must show group 239.1.1.1 on GigabitEthernet0/1. `show ip mroute 239.1.1.1` on R1 must show a (*,239.1.1.1) entry with RPF neighbor pointing to the RP itself (Null RPF for the RP) and an OIL entry toward R4 via Gi0/2.

---

### Task 6: Source Traffic and Verify End-to-End Delivery

- On **SRC1**, run the `mcjoin` tool in transmit mode for group 239.1.1.1 on interface ens3, sending one UDP packet per second at TTL 16. Leave the sender running for the remainder of this task.
- Observe (S,G) state creation across the domain. On R2 (first-hop router), an (S,G) entry for (192.168.2.10, 239.1.1.1) should appear. R2 will register the source with R1 using PIM Register unicast messages.
- On R4 (last-hop router), verify that the SPT switchover occurs: the (*,G) entry should be supplemented or replaced by an (S,G) entry once traffic arrives via the shortest path. The SPT flag indicates the switchover is complete.
- On **RCV1**, confirm that multicast packets are being received (mcjoin will print received packet counts).

**Verification:** `show ip mroute 239.1.1.1` on R1 must show both (*,239.1.1.1) and (192.168.2.10, 239.1.1.1) entries. On R4, the (S,G) entry must appear with the SPT flag set and incoming interface Gi0/0 (toward R2 via IS-IS shortest path). On R2, `show ip mroute 239.1.1.1` must show the (S,G) entry with Gi0/2 as the incoming interface and OIL toward R1.

---

### Task 7: Verify the Multicast Layer-2 Address Mapping

- On **RCV1**, capture live multicast frames using `tcpdump` and examine the destination Ethernet MAC address of arriving multicast packets.
- For group 239.1.1.1, calculate the expected MAC address using the 23-bit IP-to-MAC mapping rule described in Section 1. Confirm that the MAC address on received frames matches your calculation.

**Verification:** `sudo tcpdump -i ens3 ether host 01:00:5e:01:01:01 -v -c 5` on RCV1 must capture 5 frames with destination MAC 01:00:5e:01:01:01. This confirms the lower 23 bits of 239.1.1.1 (0x010101) correctly map to the Ethernet multicast MAC.

---

## 6. Verification & Analysis

### IS-IS Underlay Verification

```
R1# show isis neighbors

IS-IS Level-2 Adjacencies:
System Id       Type Interface          IP Address       State Holdtime Circuit Id
R2              L2   Gi0/0              10.10.12.2       UP    25       R1.01        ! ← R2 must appear — State=UP required
R3              L2   Gi0/1              10.10.13.2       UP    23       R1.02        ! ← R3 must appear — State=UP required
R4              L2   Gi0/2              10.10.14.2       UP    27       R1.03        ! ← R4 must appear — State=UP required

R1# show ip route isis
      10.0.0.0/32 is subnetted, 4 subnets
i L2     10.0.0.2 [115/20] via 10.10.12.2, Gi0/0    ! ← R2 loopback reachable via IS-IS
i L2     10.0.0.3 [115/20] via 10.10.13.2, Gi0/1    ! ← R3 loopback reachable via IS-IS
i L2     10.0.0.4 [115/20] via 10.10.14.2, Gi0/2    ! ← R4 loopback reachable via IS-IS
```

### PIM-SM and RP Verification

```
R1# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 224.0.0.0/4
  RP 10.0.0.1 (?), v2v1, static    ! ← RP must be 10.0.0.1 (R1 Lo0), type=static

R1# show ip pim neighbor
PIM Neighbor Table
Mode: B - Bidir Capable, DR - Designated Router, N - Default DR Priority,
      P - Proxy Capable, S - State Refresh Capable, G - GenID Capable, L - DR Load-balancing Capable
Neighbor          Interface                Uptime/Expires    Ver   DR
Address                                                            Prio/Mode
10.10.12.2        GigabitEthernet0/0       00:02:13/00:01:27 v2    1 / DR    ! ← R2 (Gi0/0) — PIM neighbor confirmed
10.10.13.2        GigabitEthernet0/1       00:02:11/00:01:25 v2    1 / DR    ! ← R3 (Gi0/1) — PIM neighbor confirmed
10.10.14.2        GigabitEthernet0/2       00:02:09/00:01:23 v2    1 / S     ! ← R4 (Gi0/2) — PIM neighbor confirmed
```

### IGMP State Verification (after Task 5)

```
R4# show ip igmp groups
IGMP Connected Group Membership
Group Address    Interface        Uptime    Expires   Last Reporter   Group Accounted
239.1.1.1        Gi0/1            00:01:43  00:04:17  192.168.4.10    ! ← 239.1.1.1 on Gi0/1 — last reporter is RCV1 (192.168.4.10)

R1# show ip mroute 239.1.1.1
IP Multicast Routing Table
Flags: D - Dense, S - Sparse, B - Bidir Group, s - SSM Group, C - Connected,
       L - Local, P - Pruned, R - RP-bit set, F - Register flag,
       T - SPT-bit set, J - Join SPT, M - MSDP created entry, E - Extranet
Outgoing interface flags: H - Hardware switched, A - Assert winner
 Timers: Uptime/Expires
 Interface state: Interface, Next-Hop or VCD, Expire

(*,239.1.1.1), 00:01:43/00:03:26, RP 10.0.0.1, flags: S     ! ← (*,G) entry exists — shared tree state; RP=10.0.0.1
  Incoming interface: Null, RPF nbr 0.0.0.0                  ! ← Null incoming — R1 IS the RP (traffic arrives at RP, not via upstream)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:01:43/00:03:26    ! ← OIL toward R4 — downstream receiver path
```

### Multicast Forwarding Verification (after Task 6)

```
R1# show ip mroute 239.1.1.1
(*,239.1.1.1), 00:03:12/00:02:55, RP 10.0.0.1, flags: S         ! ← Shared tree still present at RP
  Incoming interface: Null, RPF nbr 0.0.0.0
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:03:12/00:02:55

(192.168.2.10,239.1.1.1), 00:01:10/00:02:48, flags: T            ! ← (S,G) entry — source specific; T flag = SPT registered at RP
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.10.12.2      ! ← Incoming from R2 direction (RPF correct)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:01:10/00:02:48

R4# show ip mroute 239.1.1.1
(*,239.1.1.1), 00:03:12/00:02:14, RP 10.0.0.1, flags: SC         ! ← C flag — connected member (RCV1 on Gi0/1)
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.10.14.1
  Outgoing interface list:
    GigabitEthernet0/1, Forward/Sparse, 00:03:12/00:02:14

(192.168.2.10,239.1.1.1), 00:01:10/00:02:45, flags: FT            ! ← FT flags — F=Register-flag resolving, T=SPT switchover complete
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.10.14.1      ! ← Traffic arriving from R1/R2 via SPT — not via RP shared tree
  Outgoing interface list:
    GigabitEthernet0/1, Forward/Sparse, 00:01:10/00:02:45         ! ← Forwarding to RCV1 on Gi0/1 — delivery confirmed
```

### MAC Address Mapping Verification (Task 7)

```
RCV1$ sudo tcpdump -i ens3 ether host 01:00:5e:01:01:01 -v -c 5
tcpdump: listening on ens3, link-type EN10MB (Ethernet), capture size 262144 bytes
12:34:01.000001 00:50:56:xx:xx:xx > 01:00:5e:01:01:01, ethertype IPv4 (0x0800), length 56:   ! ← dst MAC 01:00:5e:01:01:01 confirmed
    192.168.2.10 > 239.1.1.1: UDP, length 14                                                  ! ← src=SRC1, dst=239.1.1.1 — multicast packet received
12:34:02.000012 00:50:56:xx:xx:xx > 01:00:5e:01:01:01, ethertype IPv4 (0x0800), length 56:
    192.168.2.10 > 239.1.1.1: UDP, length 14
5 packets captured
5 packets received by filter
0 packets dropped by kernel
```

---

## 7. Verification Cheatsheet

### IS-IS Underlay

```
router isis 1
 net <area-id>.<system-id>.00
 is-type level-2-only
!
interface <GigX/Y>
 ip router isis 1
```

| Command | Purpose |
|---------|---------|
| `show isis neighbors` | Verify IS-IS L2 adjacency state (must be UP) |
| `show ip route isis` | Confirm all loopback /32 routes are in the RIB |
| `show isis database` | View the IS-IS link-state database |

> **Exam tip:** IS-IS requires **`ip router isis <tag>`** on each interface — there is no `network` statement like OSPF. The tag must match the process tag (`router isis 1`). Omitting the interface command is the most common IS-IS adjacency failure cause.

### Multicast Routing and PIM-SM

```
ip multicast-routing
!
interface <GigX/Y>
 ip pim sparse-mode
!
ip pim rp-address <rp-ip>
```

| Command | Purpose |
|---------|---------|
| `show ip multicast` | Confirm multicast routing is globally enabled |
| `show ip pim rp mapping` | Verify RP address and mapping method (static/Auto-RP/BSR) |
| `show ip pim interface` | List PIM-enabled interfaces and their mode |
| `show ip pim neighbor` | Show PIM neighbor adjacencies and DR status |

> **Exam tip:** PIM sparse-mode must be enabled on **Loopback0 of the RP** — if it is missing, PIM Join messages routed toward the RP loopback will arrive on a non-PIM interface and be silently discarded. This is a common silent failure in Foundation labs.

### IGMP Management

```
interface <GigX/Y>
 ip pim sparse-mode      ! automatically enables IGMP on this interface
 ip igmp version 2       ! default; override to 3 for SSM (lab-02)
```

| Command | Purpose |
|---------|---------|
| `show ip igmp interface <GigX/Y>` | Confirm IGMP is active, version, and querier status |
| `show ip igmp groups` | List IGMP group membership entries on all interfaces |
| `show ip igmp groups detail` | Include reporter address and join time |

> **Exam tip:** Enabling `ip pim sparse-mode` on an interface implicitly enables IGMP. You do not need a separate `ip igmp enable` command. Removing PIM from an interface also disables IGMP on that interface — this is a common fault vector (Ticket 2 in this lab).

### Multicast Forwarding Table

```
show ip mroute                          ! full multicast routing table
show ip mroute 239.1.1.1               ! single-group detail
show ip mroute 192.168.2.10 239.1.1.1  ! single (S,G) entry
show ip rpf 192.168.2.10               ! RPF check for a source address
```

| Command | What to Look For |
|---------|-----------------|
| `show ip mroute 239.1.1.1` | (*,G) entry present; OIL non-empty; (S,G) appears after source starts |
| `show ip rpf <source-ip>` | Correct RPF interface and next-hop; RPF neighbor must match unicast path |
| `show ip mroute count` | Packet counts — confirm traffic is actually flowing, not just state |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip pim rp mapping` | RP address = 10.0.0.1, type = static |
| `show ip igmp groups` | 239.1.1.1 on R4 Gi0/1 after RCV1 joins |
| `show ip mroute 239.1.1.1` | (*,G) at R1 with OIL toward R4; (S,G) with T-flag after SPT switchover |
| `show ip rpf 192.168.2.10` | RPF interface points toward R2; RPF neighbor = 10.10.12.2 (on R1, R3) |
| `show ip pim interface` | All transit and stub interfaces show PIM sparse-mode |
| `show isis neighbors` | All four L2 adjacencies in UP state |

### Common PIM-SM Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show ip pim neighbor` shows no neighbors | PIM sparse-mode not enabled on the interface, or `ip multicast-routing` missing globally |
| (*,G) entry missing on RP | RP address not configured (`ip pim rp-address`), or PIM not on RP's Loopback0 |
| (S,G) entry missing after source starts | First-hop router RPF check fails for source subnet; check `show ip rpf <source>` |
| RCV1 receives no traffic; R4 shows no IGMP members | `ip pim sparse-mode` missing on R4 Gi0/1 — IGMP is not active without PIM |
| Traffic flows via RP but SPT switchover never happens | `ip pim spt-threshold infinity` set on last-hop router — removes automatic switchover |
| RPF failure on a transit router | IS-IS metric imbalance — transit router prefers a longer path to the source subnet; fix with `show ip rpf <source>` + metric correction |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 1: IS-IS L2 Underlay

<details>
<summary>Click to view R1–R4 IS-IS Configuration</summary>

```bash
! R1
router isis 1
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
!
interface Loopback0
 ip router isis 1
!
interface GigabitEthernet0/0
 ip router isis 1
!
interface GigabitEthernet0/1
 ip router isis 1
!
interface GigabitEthernet0/2
 ip router isis 1

! R2
router isis 1
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 passive-interface GigabitEthernet0/2
!
interface Loopback0
 ip router isis 1
!
interface GigabitEthernet0/0
 ip router isis 1
!
interface GigabitEthernet0/1
 ip router isis 1
!
interface GigabitEthernet0/2
 ip router isis 1

! R3
router isis 1
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
!
interface Loopback0
 ip router isis 1
!
interface GigabitEthernet0/0
 ip router isis 1
!
interface GigabitEthernet0/1
 ip router isis 1

! R4
router isis 1
 net 49.0001.0000.0000.0004.00
 is-type level-2-only
 passive-interface GigabitEthernet0/1
!
interface Loopback0
 ip router isis 1
!
interface GigabitEthernet0/0
 ip router isis 1
!
interface GigabitEthernet0/1
 ip router isis 1
```

</details>

<details>
<summary>Click to view IS-IS Verification Commands</summary>

```bash
show isis neighbors
show ip route isis
show isis database
```

</details>

---

### Objective 2: Multicast Routing and Static RP

<details>
<summary>Click to view R1–R4 Multicast Global Configuration</summary>

```bash
! All routers (R1, R2, R3, R4)
ip multicast-routing
ip pim rp-address 10.0.0.1
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim rp mapping
show ip multicast
```

</details>

---

### Objective 3: PIM Sparse Mode on All Interfaces

<details>
<summary>Click to view R1 PIM Interface Configuration</summary>

```bash
! R1
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
```

</details>

<details>
<summary>Click to view R2 PIM Interface Configuration</summary>

```bash
! R2
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
```

</details>

<details>
<summary>Click to view R3 PIM Interface Configuration</summary>

```bash
! R3
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
```

</details>

<details>
<summary>Click to view R4 PIM Interface Configuration</summary>

```bash
! R4
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim interface
show ip pim neighbor
```

</details>

---

### Objective 4: Linux Host Preparation

<details>
<summary>Click to view SRC1 and RCV1 Setup Commands</summary>

```bash
# SRC1 (Ubuntu 20.04)
sudo ip route add default via 192.168.2.1
sudo apt-get install -y mcjoin
ping 192.168.2.1 -c 3

# RCV1 (Ubuntu 20.04)
sudo ip route add default via 192.168.4.1
sudo apt-get install -y mcjoin
ping 192.168.4.1 -c 3
```

</details>

---

### Objective 5: IGMP Join and Shared Tree State

<details>
<summary>Click to view RCV1 Join Command and Router Verification</summary>

```bash
# RCV1 — join group (leave running in a separate terminal)
sudo mcjoin -g 239.1.1.1 -i ens3

# R4 — verify IGMP
show ip igmp groups

# R1 — verify (*,G) shared tree
show ip mroute 239.1.1.1
```

</details>

---

### Objective 6: Source Traffic and SPT Switchover

<details>
<summary>Click to view SRC1 Send Command and End-to-End Verification</summary>

```bash
# SRC1 — start sending (1 pkt/sec, TTL 16)
sudo mcjoin -s -g 239.1.1.1 -p 5001 -i ens3 -t 1

# R1 — verify (S,G) entry
show ip mroute 239.1.1.1

# R4 — verify SPT flag in (S,G)
show ip mroute 239.1.1.1

# R2 — verify first-hop (S,G)
show ip mroute 239.1.1.1
```

</details>

---

### Objective 7: Layer-2 MAC Address Mapping

<details>
<summary>Click to view tcpdump Capture on RCV1</summary>

```bash
# RCV1 — capture 5 frames with multicast MAC for 239.1.1.1
sudo tcpdump -i ens3 ether host 01:00:5e:01:01:01 -v -c 5
```

Expected MAC calculation:
- 239.1.1.1 → 0xEF010101
- Lower 23 bits: 0xEF010101 & 0x007FFFFF = 0x00010101
- MAC = 01:00:5e:**01:01:01**

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and one targeted fix.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>      # restore
```

---

### Ticket 1 — RCV1 Joins the Group But No Shared Tree State Appears at the RP

RCV1 is running `mcjoin` in receive mode and `show ip igmp groups` on R4 confirms the group membership is recorded locally. IS-IS is fully converged and all PIM neighbor adjacencies are up. However, `show ip mroute 239.1.1.1` on R1 shows no (*,G) entry — the RP is not building any shared tree state even though R4 has an active receiver.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip mroute 239.1.1.1` on R1 shows a (*,G) entry with an OIL entry toward R4. `show ip pim interface` on R1 shows Loopback0 as PIM sparse-mode enabled.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip igmp groups` — 239.1.1.1 is present on GigabitEthernet0/1 (RCV1 has joined). IGMP signaling is working correctly at R4.
2. On R4: `show ip mroute 239.1.1.1` — a (*,G) entry may appear in a Joined state, but no traffic is flowing. R4 sent a PIM (*,G) Join toward 10.0.0.1, but the Join is not being processed at the RP.
3. On R1: `show ip mroute 239.1.1.1` — no (*,G) entry exists. The RP has not accepted any Join for this group.
4. On R1: `show ip pim interface` — Loopback0 is **absent** from the PIM interface table. This is the root cause: PIM Join messages routed toward the RP address (10.0.0.1) arrive on a non-PIM interface and are silently discarded by IOS.
5. On R1: `show ip pim neighbor` — Gi0/0, Gi0/1, and Gi0/2 neighbors are present. PIM is working on transit interfaces; only Loopback0 has PIM disabled.

</details>

<details>
<summary>Click to view Fix</summary>

On R1, re-enable PIM sparse-mode on Loopback0. The RP address must be a PIM-enabled interface or inbound Joins are silently dropped.

```bash
! R1
interface Loopback0
 ip pim sparse-mode
```

Verify:
```bash
R1# show ip pim interface Loopback0
Address          Interface                Ver/   Nbr    Query  DR     DR
                                          Mode   Count  Intvl  Prior
10.0.0.1         Loopback0                v2/S   0      30     1      10.0.0.1    ! ← Lo0 is now PIM-enabled; DR=itself

R1# show ip mroute 239.1.1.1
(*,239.1.1.1), .../..., RP 10.0.0.1, flags: S
  Incoming interface: Null, RPF nbr 0.0.0.0          ! ← (*,G) entry now exists at RP
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, ...           ! ← OIL toward R4 populated
```

</details>

---

### Ticket 2 — RCV1 Does Not Receive Multicast and R4 Shows No IGMP Group Members

A network change was made on R4. Now RCV1 is unable to receive any multicast traffic despite running mcjoin in receive mode. The operator notices that no IGMP group entries appear on R4 at all.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip igmp groups` on R4 shows 239.1.1.1 on GigabitEthernet0/1. Multicast traffic reaches RCV1. `show ip pim interface` on R4 shows Gi0/1 as PIM sparse-mode enabled.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On RCV1: confirm mcjoin is running (`sudo mcjoin -g 239.1.1.1 -i ens3`) and that the kernel has a multicast socket open (`netstat -gn`).
2. On R4: `show ip igmp groups` — no entries for 239.1.1.1. This confirms the IGMP report from RCV1 is not being processed.
3. On R4: `show ip igmp interface GigabitEthernet0/1` — the interface shows no IGMP activity or shows IGMP is not running on this interface.
4. On R4: `show ip pim interface` — Gi0/1 is absent from the PIM interface table. This is the root cause: without PIM sparse-mode on Gi0/1, IGMP is not enabled on that segment. R4 is not acting as IGMP querier for the RCV1 segment.
5. Cross-reference: `show ip mroute 239.1.1.1` on R4 — no (*,G) entry, because no downstream IGMP join has been processed to trigger a PIM Join toward the RP.

</details>

<details>
<summary>Click to view Fix</summary>

On R4, re-enable PIM sparse-mode on GigabitEthernet0/1. This restores IGMP operation on the RCV1 segment.

```bash
! R4
interface GigabitEthernet0/1
 ip pim sparse-mode
```

Verify:
```bash
R4# show ip pim interface GigabitEthernet0/1
Address          Interface                Ver/   Nbr    Query  DR     DR
                                          Mode   Count  Intvl  Prior
192.168.4.1      GigabitEthernet0/1       v2/S   0      30     1      192.168.4.1   ! ← Gi0/1 is PIM-enabled; R4 is DR

R4# show ip igmp groups
239.1.1.1        Gi0/1   ...   192.168.4.10    ! ← group entry created after RCV1 re-joins
```

</details>

---

### Ticket 3 — SRC1 Is Sending But No Shared Tree State Appears at the RP

All router adjacencies are up and IS-IS is fully converged. SRC1 is actively transmitting to group 239.1.1.1 and RCV1 is running mcjoin in receive mode. However, `show ip mroute` on R1 shows no (*,G) entry for 239.1.1.1, and RCV1 receives nothing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip pim rp mapping` on all routers shows RP = 10.0.0.1 (R1 Loopback0). (*,G) and (S,G) entries for 239.1.1.1 appear on R1. RCV1 receives traffic from SRC1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip pim rp mapping` — note the RP address. If it shows 10.0.0.2 instead of 10.0.0.1, all PIM Joins from R4 are being sent toward R2 instead of R1.
2. On R2: `show ip pim rp mapping` — observe the same misconfigured RP address (10.0.0.2).
3. On R1: `show ip mroute 239.1.1.1` — no state. R1 is not the RP that routers are joining toward, so no shared tree is built at R1.
4. On R2: `show ip mroute 239.1.1.1` — a (*,G) entry may appear with R2 as the apparent RP (Incoming interface: Null), but R2 has no receivers since R4's Joins are going to a different address, and no source registration succeeds.
5. The fault: `ip pim rp-address 10.0.0.2` was configured on R2 (and possibly other routers) instead of `ip pim rp-address 10.0.0.1`. All routers must agree on the same RP address for shared-tree convergence.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, correct the static RP address to 10.0.0.1.

```bash
! R2
no ip pim rp-address 10.0.0.2
ip pim rp-address 10.0.0.1
```

Verify on all routers:
```bash
show ip pim rp mapping
! RP 10.0.0.1 (?), v2v1, static    ! ← must show 10.0.0.1 on every router
```

After correction, R4 sends (*,G) Joins toward R1, the shared tree rebuilds, and SRC1's traffic reaches RCV1 via the normal shared-tree and SPT switchover sequence.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS L2 adjacencies are UP on all four expected neighbor pairs (R1↔R2, R1↔R3, R1↔R4, R2↔R3)
- [ ] All four loopback /32 addresses appear in `show ip route isis` on every router
- [ ] `ip multicast-routing` is enabled globally on R1, R2, R3, R4
- [ ] `ip pim rp-address 10.0.0.1` is configured on all four routers
- [ ] `ip pim sparse-mode` is enabled on all interfaces including Loopback0 and stub segments
- [ ] SRC1 and RCV1 have default routes to their respective gateways and can ping them
- [ ] `show ip igmp groups` on R4 shows 239.1.1.1 after RCV1 runs mcjoin
- [ ] `show ip mroute 239.1.1.1` on R1 shows (*,G) entry with OIL toward R4
- [ ] After SRC1 starts sending: (S,G) entry appears on R1, R2, R4 with T-flag at R4
- [ ] RCV1 receives multicast packets (mcjoin shows received count > 0)
- [ ] `tcpdump` on RCV1 confirms destination MAC = 01:00:5e:01:01:01 for group 239.1.1.1

### Troubleshooting

- [ ] Ticket 1 resolved: PIM sparse-mode restored on R1 Loopback0; (*,G) entry appears at RP with OIL toward R4
- [ ] Ticket 2 resolved: PIM sparse-mode restored on R4 Gi0/1; IGMP group entry reappears
- [ ] Ticket 3 resolved: RP address corrected to 10.0.0.1 on all routers; shared tree rebuilds

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
