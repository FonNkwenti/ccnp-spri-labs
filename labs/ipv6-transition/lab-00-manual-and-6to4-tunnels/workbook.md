# Lab 00 — Static IPv6-in-IPv4 and 6to4 Tunnels

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

**Exam Objective:** 1.6 — Describe IPv6 tunneling mechanisms | 1.6.a — Static IPv6-in-IPv4 tunnels | 1.6.b — Dynamic 6to4 tunnels (300-510 SPRI)

This lab establishes the foundational IPv6 transition skill that underpins the entire topic chain. You will build IPv6 reachability across an IPv4-only core by encapsulating IPv6 packets inside IPv4 — first with a statically configured manual tunnel, then with 6to4, which eliminates the explicit destination by embedding the peer's IPv4 address directly in the IPv6 address itself. Both mechanisms let the IPv4 core (R2, R3) remain completely unaware of IPv6, a key exam concept.

### IPv6 Tunneling Fundamentals

Tunneling is the oldest and simplest IPv6 transition strategy: wrap the IPv6 packet in an IPv4 header so it can traverse an IPv4-only network. IOS supports several encapsulation modes selected with `tunnel mode`:

| Mode | IOS Keyword | Encapsulation | Endpoint Discovery |
|------|-------------|---------------|--------------------|
| Manual IPv6-in-IPv4 | `ipv6ip` | IPv4 (proto 41) | Explicit `tunnel destination` |
| 6to4 | `ipv6ip 6to4` | IPv4 (proto 41) | Derived from IPv6 source/destination |
| GRE | `gre ip` | GRE over IPv4 | Explicit `tunnel destination` |
| ISATAP | `ipv6ip isatap` | IPv4 (proto 41) | Derived from last 32 bits of IPv6 |

The SPRI exam focuses on `ipv6ip` (static) and `ipv6ip 6to4` (dynamic). Both use IP protocol 41 — GRE is a separate mechanism that adds 4 bytes of overhead and is not interchangeable.

### Static IPv6-in-IPv4 Tunnels (RFC 4213)

A manual tunnel is a point-to-point logical interface. Both endpoints are explicitly configured:

```
interface Tunnel0
 tunnel mode ipv6ip          ! IP protocol 41 encapsulation
 tunnel source Loopback0     ! local IPv4 endpoint
 tunnel destination 10.0.0.4 ! remote IPv4 endpoint
 ipv6 address 2001:db8:14::1/64
```

The `tunnel source` must match the IPv4 address the remote side uses as `tunnel destination`, and vice versa. A mismatch causes asymmetric forwarding: packets leave one direction but the return path fails because the encapsulated source does not match the configured destination at the far end.

The tunnel interface state follows IPv4 reachability: if `tunnel destination` is unreachable in the IPv4 RIB, the tunnel goes down. Verify with `show interfaces Tunnel0` — the line protocol is the IPv4 reachability check.

### 6to4 Tunnels (RFC 3056)

6to4 is a many-to-many mechanism that eliminates per-peer tunnel configuration by encoding the IPv4 endpoint address inside the IPv6 address itself. The 6to4 prefix is `2002::/16`. A site's /48 is formed as `2002:<IPv4-in-hex>::/48`:

```
IPv4: 10.0.0.1  →  hex: 0a.00.00.01  →  IPv6: 2002:0a00:0001::/48
IPv4: 10.0.0.4  →  hex: 0a.00.00.04  →  IPv6: 2002:0a00:0004::/48
```

IOS derives the tunnel destination from bits 17–48 of the IPv6 destination address. No `tunnel destination` command is needed:

```
interface Tunnel1
 tunnel mode ipv6ip 6to4     ! derive destination from IPv6 dest
 tunnel source Loopback0     ! local IPv4 address (source of encap)
 ipv6 address 2002:0a00:0001::1/16
```

The route `ipv6 route 2002::/16 Tunnel1` sends all 6to4 traffic to the tunnel; IOS automatically calculates the IPv4 destination from the embedded address.

**Exam tip:** 6to4 requires the `tunnel source` IPv4 address to match the embedded IPv4 in the 6to4 IPv6 address. R1's source is 10.0.0.1 → the 6to4 address MUST start with 2002:0a00:0001::.

### Tunnel Interface State and IPv4 Dependency

Both tunnel types track IPv4 reachability to their endpoints. You can observe this with:

```
show interfaces Tunnel0
! Line protocol is up/down — driven by IPv4 reachability to tunnel destination
! IP MTU, encapsulation type (SIT = Simple Internet Transition, i.e., proto 41)

show ip route 10.0.0.4
! If this route is absent, Tunnel0 line protocol goes down
```

The core routers (R2, R3) forward the encapsulated IPv4 packets normally — they see destination 10.0.0.1 or 10.0.0.4 and route via static routes. R2 and R3 never receive or process an IPv6 header.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Static tunnel configuration | Configure a manual point-to-point IPv6-in-IPv4 tunnel with explicit source and destination |
| 6to4 address derivation | Compute the 2002::/16 prefix from an IPv4 address and verify the encoding |
| Tunnel state diagnosis | Interpret tunnel interface state (line protocol up/down) in terms of IPv4 reachability |
| IPv6 static routing | Install IPv6 static routes to direct traffic into tunnel interfaces |
| Asymmetric tunnel troubleshooting | Identify and fix mismatched tunnel source/destination causing one-way traffic |

---

## 2. Topology & Scenario

**Scenario:** A service provider is piloting IPv6 transition for two dual-stack customer edge sites. The IPv4-only provider core (R2, R3) cannot be upgraded yet. Your task is to establish IPv6 connectivity between the two customer sites (R1 and R4) using tunneling — first with a manually configured static tunnel, then with automatic 6to4. The core routers must remain untouched (no IPv6 configuration on R2 or R3).

```
        [IPv6 site A]                [IPv4-only core]               [IPv6 site B]
  ┌──────────────────────┐     ┌──────────────┐  ┌──────────────┐     ┌──────────────────────┐
  │          R1          │     │      R2      │  │      R3      │     │          R4          │
  │  CE/PE — Dual Stack  │     │  P — IPv4    │  │  P — IPv4    │     │  CE/PE — Dual Stack  │
  │  Lo0: 10.0.0.1/32    │     │  Lo0: 10.0.0.2/32 │  Lo0: 10.0.0.3/32 │  Lo0: 10.0.0.4/32    │
  │  Lo0v6: 2001:db8::1  │     │  (no IPv6)   │  │  (no IPv6)   │     │  Lo0v6: 2001:db8::4  │
  │  Lo1v6: 2001:db8:1::/64 │  └──────┬───────┘  └───────┬──────┘     │  Lo1v6: 2001:db8:4::/64 │
  └──────────┬───────────┘          │  L2                │              └──────────┬───────────┘
             │ Gi0/0                │ 10.1.23.0/24       │                        │ Gi0/0
             │ 10.1.12.1/24         │                    │ 10.1.34.0/24           │ 10.1.34.2/24
             │ L1                   │                    │                        │ L3
             └──── 10.1.12.2/24 ────┘                    └──── 10.1.34.1/24 ──────┘
                   Gi0/0 R2                                     Gi0/1 R3

  Tunnel0 (static): R1 Tunnel0 (2001:db8:14::1) ◄────────────────────► R4 Tunnel0 (2001:db8:14::4)
  Tunnel1 (6to4):   R1 Tunnel1 (2002:0a00:0001::1) ◄─────────────────► R4 Tunnel1 (2002:0a00:0004::1)
```

The 6to4 addresses are not arbitrary — they are mathematically derived:
- R1: 10.0.0.1 → `0a.00.00.01` → `2002:0a00:0001::1`
- R4: 10.0.0.4 → `0a.00.00.04` → `2002:0a00:0004::1`

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | Dual-stack CE/PE West | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R2 | IPv4-only P Router | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R3 | IPv4-only P Router | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |
| R4 | Dual-stack CE/PE East | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 | 512 MB |

**Total EVE-NG RAM budget: 2,048 MB (2 GB)**

### Loopback Address Table

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, tunnel source endpoint |
| R1 | Loopback1 | 10.1.1.1/24 | Customer IPv4 prefix |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, tunnel source endpoint |
| R4 | Loopback1 | 10.1.4.1/24 | Customer IPv4 prefix |

### Cabling Table

| Link ID | Source | Source IP | Destination | Destination IP | Subnet |
|---------|--------|-----------|-------------|----------------|--------|
| L1 | R1 GigabitEthernet0/0 | 10.1.12.1/24 | R2 GigabitEthernet0/0 | 10.1.12.2/24 | 10.1.12.0/24 |
| L2 | R2 GigabitEthernet0/1 | 10.1.23.1/24 | R3 GigabitEthernet0/0 | 10.1.23.2/24 | 10.1.23.0/24 |
| L3 | R3 GigabitEthernet0/1 | 10.1.34.1/24 | R4 GigabitEthernet0/0 | 10.1.34.2/24 | 10.1.34.0/24 |

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
- Hostnames (R1, R2, R3, R4)
- Domain lookup suppression
- Interface IPv4 addresses on all routed links (GigabitEthernet0/0, GigabitEthernet0/1 where applicable)
- Loopback0 IPv4 address on all devices; Loopback1 IPv4 address on R1 and R4 only

**IS NOT pre-loaded** (student configures this):
- IPv4 static routing across the core
- IPv6 routing globally enabled on edge routers
- IPv6 addresses on loopbacks and tunnel interfaces
- Static IPv6-in-IPv4 tunnel (Tunnel0) on R1 and R4
- Dynamic 6to4 tunnel (Tunnel1) on R1 and R4
- IPv6 static routes directing traffic through the tunnels

---

## 5. Lab Challenge: Core Implementation

### Task 1: Establish IPv4 Reachability Across the Core

On all four routers, add static IPv4 routes so that every Loopback0 address (10.0.0.1–10.0.0.4) is reachable from every other router. Use the directly connected next-hop IP on each link, not the exit interface name.

- Ensure R1 can reach R4's Loopback0 (10.0.0.4) and R4 can reach R1's Loopback0 (10.0.0.1). These are the tunnel endpoints — without this reachability, neither tunnel will come up.
- Also cover the Loopback1 prefixes (10.1.1.0/24 from R1, 10.1.4.0/24 from R4) so end-to-end IPv4 reachability is complete.
- R2 and R3 are transit-only: they need routes toward R1 (west) and R4 (east) but do not need customer routes (Loopback1) for the tunnel lab — include them for completeness.

**Verification:** `show ip route` on each router must show the remote loopbacks as static routes (`S`). `ping 10.0.0.4 source Loopback0` from R1 must succeed. `ping 10.0.0.1 source Loopback0` from R4 must succeed.

---

### Task 2: Enable IPv6 on the Edge Routers

Enable IPv6 forwarding on R1 and R4 only. Do not configure any IPv6 on R2 or R3.

- Add IPv6 addresses to R1 Loopback0 (`2001:db8::1/128`) and Loopback1 (`2001:db8:1::1/64`).
- Add IPv6 addresses to R4 Loopback0 (`2001:db8::4/128`) and Loopback1 (`2001:db8:4::1/64`).
- Verify that R2 and R3 have no IPv6 addresses configured anywhere.

**Verification:** `show ipv6 interface brief` on R1 and R4 must show the loopback IPv6 addresses as up/up. `show ipv6 interface brief` on R2 and R3 must show no IPv6 interfaces.

---

### Task 3: Build the Static IPv6-in-IPv4 Tunnel

On R1 and R4, create a static point-to-point IPv6-in-IPv4 tunnel named Tunnel0. The tunnel uses IP protocol 41 encapsulation (not GRE).

- On R1: create Tunnel0 with IPv6 address `2001:db8:14::1/64`, source from Loopback0, destination set to R4's Loopback0 IPv4 address.
- On R4: create Tunnel0 with IPv6 address `2001:db8:14::4/64`, source from Loopback0, destination set to R1's Loopback0 IPv4 address.
- The `tunnel source` and `tunnel destination` on each side must be exact mirror images of each other.

**Verification:** `show interfaces Tunnel0` on both routers must show line protocol up. `show ipv6 interface Tunnel0` must show the IPv6 address as valid.

---

### Task 4: Route IPv6 Traffic Through the Static Tunnel

Add IPv6 static routes so that R1's customer prefix (`2001:db8:1::1/64`) is reachable from R4, and R4's customer prefix (`2001:db8:4::1/64`) is reachable from R1, via Tunnel0.

- On R1: install a static IPv6 route for `2001:db8:4::1/64` pointing to R4's Tunnel0 address as the next-hop.
- On R4: install a static IPv6 route for `2001:db8:1::1/64` pointing to R1's Tunnel0 address as the next-hop.

**Verification:** `show ipv6 route` on R1 must show `2001:db8:4::/64` as a static route via `2001:db8:14::4`. From R1 `ping ipv6 2001:db8:4::1 source Loopback1` must succeed. A `traceroute ipv6` from R1 must show two hops (R1 Tunnel0, then R4) — the IPv4 core is invisible in the trace.

---

### Task 5: Build the 6to4 Dynamic Tunnel

On R1 and R4, create Tunnel1 using the automatic 6to4 mode. Unlike Tunnel0, no `tunnel destination` is configured — the destination IPv4 address is derived from the IPv6 destination prefix.

- On R1: create Tunnel1 with source from Loopback0 and IPv6 address `2002:0a00:0001::1/16`. The address encodes R1's Loopback0 IPv4 (10.0.0.1 = 0x0a000001).
- On R4: create Tunnel1 with source from Loopback0 and IPv6 address `2002:0a00:0004::1/16`. The address encodes R4's Loopback0 IPv4 (10.0.0.4 = 0x0a000004).
- On both R1 and R4, add an IPv6 static route for the entire `2002::/16` prefix pointing to Tunnel1.

**Verification:** `show interfaces Tunnel1` must show line protocol up. `show ipv6 interface Tunnel1` must show the 6to4 address as valid. From R1, `ping ipv6 2002:0a00:0004::1` (R4's 6to4 address) must succeed.

---

### Task 6: Compare Static and 6to4 Tunnel Behavior

Confirm the key behavioral difference: the static tunnel has a fixed destination configured explicitly, while 6to4 computes it dynamically from the IPv6 destination.

- Compare the detailed interface output for Tunnel0 and Tunnel1 side by side. Tunnel0 must show an explicit configured destination (10.0.0.4); Tunnel1 must show no destination line — the peer IPv4 address is derived per-packet from the IPv6 destination.
- From R1, ping R4's Loopback1 IPv6 address (`2001:db8:4::1`) to verify the static tunnel path, and ping R4's 6to4 address (`2002:0a00:0004::1`) to verify the 6to4 path.
- Observe that both tunnel types encapsulate IPv6 into IPv4 (protocol 41) — confirm via the encapsulation type shown in the tunnel interface detail output.

**Verification:** Both pings succeed. `show interfaces Tunnel0` shows `Tunnel source 10.0.0.1, destination 10.0.0.4`. `show interfaces Tunnel1` shows `Tunnel source 10.0.0.1 (Loopback0)` with no destination line.

---

### Task 7: Troubleshoot an Asymmetric Tunnel Source Fault

A colleague reports that after a recent change, the static tunnel (Tunnel0) shows `up/up` but pings from R1 to R4 via the tunnel fail in one direction only. Diagnose and fix the fault.

- Start by checking the tunnel interface state on both R1 and R4. An asymmetric source/destination mismatch typically shows the tunnel up on both sides (because IPv4 reachability exists) but traffic is dropped on the return path.
- On each router, inspect the static tunnel interface detail to compare the configured source and destination addresses. The source address on one side must exactly match the destination address on the other side, and vice versa.
- Identify which router has the mismatched tunnel endpoint parameter and correct it.

**Verification:** After the fix, `ping ipv6 2001:db8:4::1 source Loopback1` from R1 succeeds in both directions. `traceroute ipv6 2001:db8:4::1 source 2001:db8:1::1` from R1 shows R1 Tunnel0 → R4 with no drops.

---

## 6. Verification & Analysis

### Task 1 — IPv4 Reachability

```
R1# show ip route static
S    10.0.0.2/32 [1/0] via 10.1.12.2          ! ← R2 Lo0 reachable
S    10.0.0.3/32 [1/0] via 10.1.12.2          ! ← R3 Lo0 reachable
S    10.0.0.4/32 [1/0] via 10.1.12.2          ! ← R4 Lo0 — tunnel endpoint must appear
S    10.1.4.0/24 [1/0] via 10.1.12.2          ! ← R4 customer prefix

R1# ping 10.0.0.4 source Loopback0 repeat 5
!!!!!                                           ! ← all five pings must succeed
Success rate is 100 percent (5/5)
```

```
R4# ping 10.0.0.1 source Loopback0 repeat 5
!!!!!                                           ! ← confirms bidirectional reachability
Success rate is 100 percent (5/5)
```

### Task 3 — Static Tunnel State

```
R1# show interfaces Tunnel0
Tunnel0 is up, line protocol is up              ! ← line protocol up = IPv4 dest reachable
  Hardware is Tunnel
  MTU 17916 bytes, BW 100 Kbit/sec
  Tunnel source 10.0.0.1 (Loopback0), destination 10.0.0.4   ! ← exact match required
  Tunnel protocol/transport IPv6/IP             ! ← IPv6 over IPv4, protocol 41
  ...

R1# show ipv6 interface Tunnel0
Tunnel0 is up, line protocol is up
  IPv6 is enabled, link-local address is FE80::...
  Global unicast address(es):
    2001:DB8:14::1, subnet is 2001:DB8:14::/64  ! ← tunnel IPv6 address assigned
```

### Task 4 — Static Tunnel IPv6 Routing

```
R1# show ipv6 route static
IPv6 Routing Table - default - 4 entries
S   2001:DB8:4::/64 [1/0]
     via 2001:DB8:14::4, Tunnel0              ! ← R4 Lo1v6 via Tunnel0 next-hop

R1# ping ipv6 2001:db8:4::1 source Loopback1 repeat 5
!!!!!                                           ! ← end-to-end IPv6 across IPv4 core
Success rate is 100 percent (5/5)

R1# traceroute ipv6 2001:db8:4::1 source 2001:db8:1::1
 1  2001:DB8:14::4  <msec>                     ! ← R4 Tunnel0 — one hop, core invisible
```

### Task 5 — 6to4 Tunnel State

```
R1# show interfaces Tunnel1
Tunnel1 is up, line protocol is up
  Tunnel source 10.0.0.1 (Loopback0)           ! ← source present, NO destination line
  Tunnel protocol/transport IPv6 6to4           ! ← 6to4 mode — dest derived dynamically

R1# ping ipv6 2002:0a00:0004::1 repeat 5
!!!!!                                           ! ← 6to4 reachability confirmed
Success rate is 100 percent (5/5)
```

### Task 6 — Side-by-Side Comparison

```
R1# show interfaces Tunnel0
  Tunnel source 10.0.0.1 (Loopback0), destination 10.0.0.4   ! ← STATIC: dest explicit

R1# show interfaces Tunnel1
  Tunnel source 10.0.0.1 (Loopback0)           ! ← 6to4: NO destination configured
  Tunnel protocol/transport IPv6 6to4
```

---

## 7. Verification Cheatsheet

### IPv4 Static Routing

```
ip route <network> <mask> <next-hop>
```

| Command | Purpose |
|---------|---------|
| `show ip route static` | Display all static IPv4 routes |
| `ping <ip> source Loopback0` | Test reachability sourced from Lo0 (tunnel source) |
| `show ip route <ip>` | Confirm specific route and next-hop |

> **Exam tip:** Always test tunnel endpoint reachability (`ping <tunnel-dest> source <tunnel-source>`) before troubleshooting tunnel state. Tunnel line protocol follows IPv4 reachability — if the ping fails, the tunnel cannot come up.

### IPv6 Global Configuration

```
ipv6 unicast-routing
interface Loopback0
 ipv6 address <prefix>/<len>
```

| Command | Purpose |
|---------|---------|
| `show ipv6 interface brief` | Show all IPv6 interfaces and their state |
| `show ipv6 interface <intf>` | Detailed IPv6 interface information |
| `show running-config \| section ipv6` | Review all IPv6 configuration |

### Static IPv6-in-IPv4 Tunnel

```
interface Tunnel0
 tunnel mode ipv6ip
 tunnel source Loopback0
 tunnel destination <peer-Lo0-IPv4>
 ipv6 address <prefix>/<len>
```

| Command | Purpose |
|---------|---------|
| `show interfaces Tunnel0` | State (up/up), source, destination, encap type |
| `show ipv6 interface Tunnel0` | IPv6 address assigned to tunnel |
| `show ipv6 route` | Confirm IPv6 static routes via Tunnel0 |

> **Exam tip:** `tunnel mode ipv6ip` uses IP protocol 41 (Simple Internet Transition / SIT). `tunnel mode gre ip` uses protocol 47 with a GRE header. They are not interchangeable — a SIT tunnel will not talk to a GRE tunnel.

### 6to4 Dynamic Tunnel

```
interface Tunnel1
 tunnel mode ipv6ip 6to4
 tunnel source Loopback0
 ipv6 address 2002:<IPv4-hex>::1/16
ipv6 route 2002::/16 Tunnel1
```

| Command | Purpose |
|---------|---------|
| `show interfaces Tunnel1` | Confirm no destination configured; mode is "6to4" |
| `ping ipv6 2002:<peer-hex>::1` | Direct 6to4 reachability test |

> **Exam tip:** The 6to4 prefix math: take each octet of the IPv4 address, write it in 2-digit hex, concatenate in pairs. 10.0.0.4 → `0a`, `00`, `00`, `04` → `0a00:0004` → prefix is `2002:0a00:0004::/48`.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show interfaces Tunnel0` | `line protocol is up`; source and destination IPs |
| `show interfaces Tunnel1` | `line protocol is up`; protocol shows `IPv6 6to4` |
| `show ipv6 interface brief` | All IPv6 addresses up on R1/R4; nothing on R2/R3 |
| `show ipv6 route` | Static routes via Tunnel0 and Tunnel1 |
| `ping ipv6 <addr> source <intf>` | End-to-end IPv6 connectivity test |
| `traceroute ipv6 <addr>` | Confirm single-hop across the invisible IPv4 core |
| `show ip route 10.0.0.4` | Verify IPv4 reachability to tunnel destination |

### Common IPv6 Tunnel Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Tunnel line protocol down | IPv4 reachability to `tunnel destination` missing |
| Tunnel up but pings fail one-way | Asymmetric `tunnel source`/`tunnel destination` (mismatch) |
| 6to4 tunnel up but no reachability | Missing `ipv6 route 2002::/16 Tunnel1` |
| `ipv6 unicast-routing` not working | Command not entered globally on the edge router |
| Pings succeed from one side only | Return route (`ipv6 route`) missing on remote router |
| `tunnel mode` wrong type | Using `gre ip` instead of `ipv6ip` — protocol 47 vs 41 |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 1: IPv4 Static Routing

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — static routes toward R2/R3/R4
ip route 10.0.0.2 255.255.255.255 10.1.12.2
ip route 10.0.0.3 255.255.255.255 10.1.12.2
ip route 10.0.0.4 255.255.255.255 10.1.12.2
ip route 10.1.23.0 255.255.255.0 10.1.12.2
ip route 10.1.34.0 255.255.255.0 10.1.12.2
ip route 10.1.4.0 255.255.255.0 10.1.12.2
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — transit routes east and west
ip route 10.0.0.1 255.255.255.255 10.1.12.1
ip route 10.1.1.0 255.255.255.0 10.1.12.1
ip route 10.0.0.3 255.255.255.255 10.1.23.2
ip route 10.0.0.4 255.255.255.255 10.1.23.2
ip route 10.1.34.0 255.255.255.0 10.1.23.2
ip route 10.1.4.0 255.255.255.0 10.1.23.2
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — transit routes east and west
ip route 10.0.0.1 255.255.255.255 10.1.23.1
ip route 10.0.0.2 255.255.255.255 10.1.23.1
ip route 10.1.12.0 255.255.255.0 10.1.23.1
ip route 10.1.1.0 255.255.255.0 10.1.23.1
ip route 10.0.0.4 255.255.255.255 10.1.34.2
ip route 10.1.4.0 255.255.255.0 10.1.34.2
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — static routes toward R3/R2/R1
ip route 10.0.0.1 255.255.255.255 10.1.34.1
ip route 10.0.0.2 255.255.255.255 10.1.34.1
ip route 10.0.0.3 255.255.255.255 10.1.34.1
ip route 10.1.12.0 255.255.255.0 10.1.34.1
ip route 10.1.23.0 255.255.255.0 10.1.34.1
ip route 10.1.1.0 255.255.255.0 10.1.34.1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route static
ping 10.0.0.4 source Loopback0
ping 10.0.0.1 source Loopback0
```
</details>

### Objective 2: IPv6 on Edge Routers

<details>
<summary>Click to view R1 and R4 Configuration</summary>

```bash
! R1
ipv6 unicast-routing
interface Loopback0
 ipv6 address 2001:db8::1/128
interface Loopback1
 ipv6 address 2001:db8:1::1/64

! R4
ipv6 unicast-routing
interface Loopback0
 ipv6 address 2001:db8::4/128
interface Loopback1
 ipv6 address 2001:db8:4::1/64
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 interface brief
```
</details>

### Objective 3 & 4: Static IPv6-in-IPv4 Tunnel

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Tunnel0 static IPv6-in-IPv4
interface Tunnel0
 description Static IPv6-in-IPv4 tunnel to R4
 ipv6 address 2001:db8:14::1/64
 tunnel source Loopback0
 tunnel destination 10.0.0.4
 tunnel mode ipv6ip
!
ipv6 route 2001:db8:4::1/64 2001:db8:14::4
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Tunnel0 static IPv6-in-IPv4
interface Tunnel0
 description Static IPv6-in-IPv4 tunnel to R1
 ipv6 address 2001:db8:14::4/64
 tunnel source Loopback0
 tunnel destination 10.0.0.1
 tunnel mode ipv6ip
!
ipv6 route 2001:db8:1::1/64 2001:db8:14::1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show interfaces Tunnel0
show ipv6 interface Tunnel0
show ipv6 route
ping ipv6 2001:db8:4::1 source Loopback1
traceroute ipv6 2001:db8:4::1 source 2001:db8:1::1
```
</details>

### Objective 5: 6to4 Dynamic Tunnel

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Tunnel1 6to4
interface Tunnel1
 description Dynamic 6to4 tunnel
 ipv6 address 2002:0a00:0001::1/16
 tunnel source Loopback0
 tunnel mode ipv6ip 6to4
!
ipv6 route 2002::/16 Tunnel1
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Tunnel1 6to4
interface Tunnel1
 description Dynamic 6to4 tunnel
 ipv6 address 2002:0a00:0004::1/16
 tunnel source Loopback0
 tunnel mode ipv6ip 6to4
!
ipv6 route 2002::/16 Tunnel1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show interfaces Tunnel1
ping ipv6 2002:0a00:0004::1
ping ipv6 2002:0a00:0001::1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>              # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — Static Tunnel Shows Up/Up but IPv6 Pings Fail from R1

A change was recently applied to the tunnels. The static tunnel (Tunnel0) on both R1 and R4 shows `line protocol is up`, but pinging R4's IPv6 addresses from R1 returns no reply. R4 can reach R1 without issue.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `ping ipv6 2001:db8:4::1 source Loopback1` from R1 succeeds in both directions.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Both tunnels are up — IPv4 reachability exists, so the fault is not in the IPv4 core.
2. Run `show interfaces Tunnel0` on R1. Note the `tunnel source` IP.
3. Run `show interfaces Tunnel0` on R4. Compare `tunnel destination` with R1's `tunnel source`.
4. The values will not match — R1's `tunnel source` is Loopback0 (10.0.0.1) but R4's `tunnel destination` points to an incorrect address (e.g. 10.0.0.2).
5. R4 encapsulates return IPv6 traffic toward the wrong IPv4 destination — R2 receives it and discards it (no IPv6 path). R1 never sees the return packet.
</details>

<details>
<summary>Click to view Fix</summary>

On R4, correct the tunnel destination to match R1's Loopback0:

```bash
interface Tunnel0
 tunnel destination 10.0.0.1
```

Verify with `show interfaces Tunnel0` on R4 — destination must read `10.0.0.1`.
Then `ping ipv6 2001:db8:4::1 source Loopback1` from R1 must succeed.
</details>

---

### Ticket 2 — 6to4 Tunnel Pings Fail in Both Directions

The operations team reports that 6to4 reachability between R1 and R4 has broken. The static tunnel (Tunnel0) is working, but `ping ipv6 2002:0a00:0004::1` from R1 fails with 100% loss. Tunnel1 shows `line protocol is up` on both routers.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `ping ipv6 2002:0a00:0004::1` from R1 succeeds; `ping ipv6 2002:0a00:0001::1` from R4 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Tunnel1 is up/up — the issue is not IPv4 reachability.
2. Run `show ipv6 route` on R1. Check whether a route for `2002::/16` or `2002:0a00:0004::/48` is present.
3. The route for `2002::/16 via Tunnel1` will be missing — the inject script removes it.
4. Without this route, IOS does not know to send 2002-addressed traffic to Tunnel1; packets are dropped with "no route to host."
5. Check `show ipv6 route` on R4 as well — the same route may be missing there.
</details>

<details>
<summary>Click to view Fix</summary>

On R1 (and R4 if also missing):

```bash
ipv6 route 2002::/16 Tunnel1
```

Verify with `show ipv6 route` — `S 2002::/16` must appear via Tunnel1.
</details>

---

### Ticket 3 — Tunnel1 Line Protocol Down on R1 After Reconfiguration

After a configuration review, someone changed Tunnel1 on R1. Now `show interfaces Tunnel1` shows `line protocol is down` even though IPv4 routing is intact and Tunnel0 is still up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show interfaces Tunnel1` on R1 shows `line protocol is up` and `ping ipv6 2002:0a00:0004::1` from R1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show interfaces Tunnel1` on R1. Note the tunnel mode — it may show `GRE/IP` instead of `IPv6 6to4`.
2. Run `show running-config interface Tunnel1` on R1. The `tunnel mode` will be missing or set to `gre ip`.
3. Without `tunnel mode ipv6ip 6to4`, IOS treats Tunnel1 as a GRE tunnel. GRE tunnels require a configured `tunnel destination`; without one, the line protocol stays down.
4. The fix is to restore the correct tunnel mode.
</details>

<details>
<summary>Click to view Fix</summary>

On R1:

```bash
interface Tunnel1
 tunnel mode ipv6ip 6to4
```

Verify with `show interfaces Tunnel1` — the protocol line must read `Tunnel protocol/transport IPv6 6to4` and line protocol must be up.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ping 10.0.0.4 source Loopback0` from R1 — 100% success
- [ ] `ping 10.0.0.1 source Loopback0` from R4 — 100% success
- [ ] `show ipv6 interface brief` on R2 and R3 — no IPv6 interfaces
- [ ] `show interfaces Tunnel0` on R1 — line protocol up, destination 10.0.0.4
- [ ] `show interfaces Tunnel0` on R4 — line protocol up, destination 10.0.0.1
- [ ] `ping ipv6 2001:db8:4::1 source Loopback1` from R1 — 100% success
- [ ] `traceroute ipv6 2001:db8:4::1` from R1 — single hop (core invisible)
- [ ] `show interfaces Tunnel1` on R1 — line protocol up, mode IPv6 6to4
- [ ] `ping ipv6 2002:0a00:0004::1` from R1 — 100% success
- [ ] `ping ipv6 2002:0a00:0001::1` from R4 — 100% success

### Troubleshooting

- [ ] Ticket 1: Asymmetric `tunnel destination` on R4 identified and corrected
- [ ] Ticket 2: Missing `ipv6 route 2002::/16 Tunnel1` identified and restored
- [ ] Ticket 3: Incorrect `tunnel mode` on Tunnel1 identified and corrected

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
