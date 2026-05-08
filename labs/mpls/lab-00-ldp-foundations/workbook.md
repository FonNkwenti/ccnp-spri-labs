# Lab 00 — MPLS LDP Foundations and Label Distribution

**Topic:** MPLS · **Difficulty:** Foundation · **Time:** 75 minutes
**Blueprint refs:** 4.1, 4.1.a · **Type:** progressive (chain root)
**Devices:** PE1, P1, P2, PE2

---

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

**Exam Objective:** 4.1, 4.1.a — Configure and verify MPLS forwarding and LDP label distribution

This lab builds the MPLS LDP data plane from scratch. By the end, you will understand how LDP discovers peers and exchanges label bindings, why the LIB contains more entries than the LFIB, how PHP removes the label before the egress PE, and why the LDP router-id must be anchored to a reachable loopback.

### MPLS Forwarding and the Three Planes

MPLS forwarding replaces destination-IP lookup with a fixed-length label swap. Three planes coordinate:

- **Control plane (LDP):** every LSR advertises a local label for every IGP prefix it knows. Peers exchange these bindings over a TCP/646 session preceded by UDP/646 hello discovery.
- **LIB (Label Information Base):** the full collection of bindings — one local binding plus one remote binding per LDP peer per prefix. Most remote bindings are kept but unused.
- **LFIB (Label Forwarding Information Base):** the data-plane subset. Only the binding from the IGP next-hop wins; that becomes the outgoing label written into hardware.

### Penultimate Hop Popping (PHP)

The egress PE advertises its own loopback as `implicit-null`. The upstream LSR pops the label before sending the packet to the PE, so the PE only does an IP lookup once. This is a per-prefix optimisation — each LDP peer decides independently whether to advertise `implicit-null` or a real label for its own prefixes.

### LDP Router-ID

Every LDP peer is identified by a 32-bit ID. By default IOS picks the highest-IP loopback. We override with `mpls ldp router-id Loopback0 force` because the router-id must be **reachable** (so the TCP session can come up) and **stable** (so it does not change when an unrelated loopback is added).

### IGP First, Label Plane Second

LDP can only bind a label to a prefix the IGP has already installed in the RIB. The lab brings up IS-IS L2 across the core *before* enabling LDP.

`★ Insight ─────────────────────────────────────`

- LIB ⊋ LFIB. A 1000-prefix network with 4 LDP peers stores ~5000
  bindings per LSR but only writes 1000 entries to hardware. Knowing
  which subset the LFIB selected is the entire `show mpls forwarding-table`
  vs `show mpls ldp bindings` distinction.
- PHP exists because the egress PE would otherwise do *two* lookups
  for every packet — one MPLS-table lookup to remove its own label,
  then one IP-FIB lookup to forward. PHP collapses these into one.
- `mpls ldp router-id ... force` is required because without `force`,
  IOS waits for the current ID to disappear before swapping. With
  `force`, it switches immediately — which is what you want during
  bring-up when the ID was wrong.
`─────────────────────────────────────────────────`

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IS-IS L2 bring-up | Configure NETs, level-2-only, wide metrics, point-to-point on core links |
| LDP global config | Set label protocol and force router-id to a reachable loopback |
| MPLS interface activation | Enable `mpls ip` on the correct interfaces without touching loopbacks |
| LDP discovery and session verification | Distinguish hello sources (UDP) from sessions (TCP/Oper) |
| LIB vs LFIB analysis | Read `show mpls ldp bindings` vs `show mpls forwarding-table` and explain the difference |
| PHP observation | Identify `imp-null` in the LIB and `Pop Label` in the LFIB; trace which router pops |
| ECMP over LSPs | Confirm two outgoing labels for PE2's loopback when two equal-cost paths exist |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at a Service Provider tasked with commissioning the MPLS core for AS 65100. IP addressing and interface connectivity are already in place. Your job is to bring up IS-IS L2 as the IGP, then enable LDP so the core can forward traffic on label-switched paths rather than native IP. Once the label plane is up, you will inspect the LIB and LFIB to understand how label selection works, confirm ECMP across the diamond topology, and verify that PHP is operating correctly before handing the core off for customer VPN provisioning.

```
            AS 65100 — IS-IS L2 + MPLS LDP on every core link

            10.0.0.1                              10.0.0.4
        ┌───────────┐                          ┌───────────┐
        │    PE1    │                          │    PE2    │
        │ Loopback0 │                          │ Loopback0 │
        └─┬───────┬─┘                          └─┬───────┬─┘
       Gi0/1  Gi0/2                           Gi0/1  Gi0/2
          │       │                              │       │
          │L2     │L3                          L5│       │L6
          │       │                              │       │
        Gi0/0  Gi0/0                           Gi0/2  Gi0/2
        ┌─┴─────────┐                          ┌─┴─────────┐
        │    P1     │── L4 (Gi0/1↔Gi0/1) ──────│    P2     │
        │ 10.0.0.2  │     10.10.23.0/24        │ 10.0.0.3  │
        └───────────┘                          └───────────┘
```

| Link | Endpoints                  | Subnet            | Role                     |
|------|----------------------------|-------------------|--------------------------|
| L2   | PE1 Gi0/1 ↔ P1 Gi0/0       | 10.10.12.0/24     | IS-IS + LDP core         |
| L3   | PE1 Gi0/2 ↔ P2 Gi0/0       | 10.10.13.0/24     | IS-IS + LDP core         |
| L4   | P1 Gi0/1 ↔ P2 Gi0/1        | 10.10.23.0/24     | IS-IS + LDP P-cross      |
| L5   | P1 Gi0/2 ↔ PE2 Gi0/1       | 10.10.24.0/24     | IS-IS + LDP core         |
| L6   | P2 Gi0/2 ↔ PE2 Gi0/2       | 10.10.34.0/24     | IS-IS + LDP core         |

Loopbacks: PE1 = 10.0.0.1, P1 = 10.0.0.2, P2 = 10.0.0.3, PE2 = 10.0.0.4
(all `/32`).

**Key relationships**

- The diamond gives PE1 two link-disjoint paths to PE2 (`via P1`, `via P2`)
  — both will appear as ECMP next-hops in the LFIB once IS-IS is up.
- The P1↔P2 cross (L4) is unused for PE-to-PE LSPs in this lab but stays
  in the IS-IS topology so the next labs can build a third path through
  it.
- IS-IS NETs follow `49.0001.0000.0000.000X.00` where `X` matches the
  device number (PE1=1, P1=2, P2=3, PE2=4).

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge Router (ingress/egress LSR) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| P1 | SP Core Router (transit LSR) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| P2 | SP Core Router (transit LSR) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |
| PE2 | SP Edge Router (ingress/egress LSR) | IOSv | vios-adventerprisek9-m.SPA.159-3.M6 |

**Why IOSv:** LDP control plane (`mpls label protocol ldp`, `mpls ldp router-id ... force`) and per-interface `mpls ip` are all native to IOS 15.9. No XRv or CSR boot overhead for a foundations lab. RAM per node: 512 MB (~2 GB total).

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | LDP Router-ID, IS-IS NET anchor |
| P1 | Loopback0 | 10.0.0.2/32 | LDP Router-ID |
| P2 | Loopback0 | 10.0.0.3/32 | LDP Router-ID |
| PE2 | Loopback0 | 10.0.0.4/32 | LDP Router-ID, LSP target |

### Cabling Table

| Link ID | Source | Source Interface | Destination | Destination Interface | Subnet |
|---------|--------|-----------------|-------------|----------------------|--------|
| L2 | PE1 | GigabitEthernet0/1 | P1 | GigabitEthernet0/0 | 10.10.12.0/24 |
| L3 | PE1 | GigabitEthernet0/2 | P2 | GigabitEthernet0/0 | 10.10.13.0/24 |
| L4 | P1 | GigabitEthernet0/1 | P2 | GigabitEthernet0/1 | 10.10.23.0/24 |
| L5 | P1 | GigabitEthernet0/2 | PE2 | GigabitEthernet0/1 | 10.10.24.0/24 |
| L6 | P2 | GigabitEthernet0/2 | PE2 | GigabitEthernet0/2 | 10.10.34.0/24 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| PE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

`initial-configs/<device>.cfg` is loaded by `setup_lab.py` before the
lab starts.

**IS pre-loaded (do NOT reconfigure):**

- Hostnames (PE1, P1, P2, PE2) and `no ip domain-lookup`
- Loopback0 with the address from the topology table, `no shutdown`
- All core-facing interfaces with correct IP/mask, descriptions, and
  `no shutdown` — so IP connectivity to a directly attached neighbour
  works as soon as the line protocol comes up

**NOT pre-loaded (your job in this lab):**

- IS-IS routing protocol, NETs, `metric-style wide`, `is-type level-2-only`,
  `passive-interface Loopback0`
- `ip router isis CORE` and `isis network point-to-point` on each core
  interface
- `mpls label protocol ldp` (global)
- `mpls ldp router-id Loopback0 force` (global)
- `mpls ip` on each core-facing interface
- Anything in section 9 (the troubleshooting tickets plant their own
  faults on top of a working configuration)

---

## 5. Lab Challenge: Core Implementation

> The tasks describe outcomes, not commands. Use the cheatsheet
> (section 7) for syntax, and confirm each verification before moving on.

### Task 1: Bring Up IS-IS L2 Across the Core

Configure IS-IS process `CORE` on PE1, P1, P2, and PE2.

- Assign each router a NET following `49.0001.0000.0000.000X.00`, where X matches the device number (PE1=1, P1=2, P2=3, PE2=4).
- Set the process to `level-2-only` and enable `metric-style wide`.
- Mark `Loopback0` passive so it is advertised without forming an adjacency.
- Activate IS-IS on `Loopback0` and on every core-facing interface.
- Set every core interface to network type `point-to-point`.

**Verification:** `show clns neighbors` on every router must list each directly attached peer in `UP` state. From PE1, `ping 10.0.0.2`, `ping 10.0.0.3`, and `ping 10.0.0.4` sourced from `10.0.0.1` must all succeed. `show isis database` must show four LSPs (one per system-id) on every router.

---

### Task 2: Enable MPLS LDP Globally

On all four routers, configure LDP as the label distribution protocol and force the LDP router-id to `Loopback0`.

- Set `mpls label protocol ldp` globally.
- Set `mpls ldp router-id Loopback0 force`. The `force` keyword applies the change immediately rather than waiting for the current ID to age out.

**Verification:** Run `show mpls ldp parameters` on each router — if LDP is initialised, this command returns session and discovery timer output even before any interface has `mpls ip`. Do **not** rely on `show mpls ldp discovery` to confirm Task 2: on IOSv 15.9 that command returns no output until at least one interface is sending LDP hellos (Task 3). The Local LDP Identifier line will appear once you enable `mpls ip` on the first interface.

---

### Task 3: Activate MPLS on Each Core Interface

Enable MPLS forwarding on every core-facing interface on PE1, P1, P2, and PE2. Do **not** enable it on `Loopback0` — labels run on links, not loopbacks.

- On PE1: `GigabitEthernet0/1` (L2) and `GigabitEthernet0/2` (L3).
- On P1: `GigabitEthernet0/0` (L2), `GigabitEthernet0/1` (L4), `GigabitEthernet0/2` (L5).
- On P2: `GigabitEthernet0/0` (L3), `GigabitEthernet0/1` (L4), `GigabitEthernet0/2` (L6).
- On PE2: `GigabitEthernet0/1` (L5) and `GigabitEthernet0/2` (L6).

**Verification:** `show mpls interfaces` on every router must show `Yes (ldp)` in the IP column for each core interface — 2 interfaces on each PE, 3 on each P router (10 endpoints total). `show mpls ldp neighbor` must now list sessions forming.

---

### Task 4: Verify LDP Discovery and Sessions

Inspect the LDP discovery and session state on every router.

- Confirm one hello-source entry per directly attached core neighbour (UDP/646 hellos).
- Confirm one session per directly attached neighbour in `Oper` state, with the LDP ID equal to the peer's `Loopback0` address.

**Verification:** `show mpls ldp discovery` must list 2 hello sources on each PE and 3 on each P router. `show mpls ldp neighbor` must show 5 sessions total across the topology (one per core link), all in `Oper` state, with each peer's LDP ID matching its `Loopback0` address.

---

### Task 5: Inspect the LIB

Display the full label binding table on PE1 and interpret it.

- Run `show mpls ldp bindings` on PE1.
- For each remote `/32` loopback (10.0.0.2, 10.0.0.3, 10.0.0.4), identify the **one local binding** PE1 has assigned and all **remote bindings** received from LDP peers.
- Note that the number of remote bindings per prefix equals the number of LDP peers, but only one of those will be installed in the LFIB.

**Verification:** For every `/32` in IS-IS, `show mpls ldp bindings` must show one `lib entry` with one local label and one remote binding per LDP peer. Local label values must be in the platform allocation range (typically 16–1048575 on IOSv).

---

### Task 6: Inspect the LFIB

Display the label forwarding table on PE1 and compare it to the LIB from Task 5.

- Run `show mpls forwarding-table` on PE1.
- For each remote loopback, identify the outgoing label installed and the next-hop interface.
- Explain why 10.0.0.4/32 (PE2) shows two outgoing entries when the others show one.

**Verification:** `show mpls forwarding-table` on PE1 must show entries for 10.0.0.2/32, 10.0.0.3/32, and 10.0.0.4/32. The entry for 10.0.0.4/32 must have **two rows** — one via P1 and one via P2 — reflecting ECMP across L2 and L3. Each outgoing label must match the remote binding advertised by that path's next-hop in the LIB.

---

### Task 7: Observe Penultimate Hop Popping

Confirm PHP is operating correctly for PE2's loopback prefix.

- On P1 and P2, run `show mpls ldp bindings 10.0.0.4 32` and locate the remote binding PE2 is advertising for its own loopback. **Do not look for this binding on PE1** — LDP bindings are only exchanged between directly peered LSRs, and PE1 has no direct session with PE2.
- On P1 and P2, run `show mpls forwarding-table 10.0.0.4` and note the outgoing label for the entry toward PE2.
- From PE1, run `traceroute 10.0.0.4` and identify which hop removes the label before delivery to PE2.

**Verification:** `show mpls ldp bindings 10.0.0.4 32` on P1 and P2 must each show a remote binding from PE2 (`lsr: 10.0.0.4:0, label: imp-null`). `show mpls forwarding-table 10.0.0.4` on P1 and P2 must show `Pop Label` in the outgoing label column. Traceroute from PE1 to 10.0.0.4 must show PE2 receiving the packet as native IP (no label stack) — the penultimate P router performs the pop. PE1's own LIB will show bindings only from P1 and P2 (its direct peers) — the absence of a PE2 entry on PE1 is correct.

---

### Task 8: Work the Troubleshooting Tickets

Two faults in section 9 plant control-plane failures on top of the working baseline you just built. Inject each fault, diagnose it using only `show` commands, apply the fix, and confirm the verifier passes before moving to the next ticket.

**Verification:** Ticket 1 verifier reports `LDP session stable`. Ticket 2 verifier reports `LDP bindings symmetric`.

---

## 6. Verification & Analysis

Sample output for the key verification commands. Use this as a
reference when your output looks different from what a task expects.

### Task 1 — IS-IS adjacencies and loopback reachability

```
PE1# show clns neighbors
System Id      Interface   SNPA                State  Holdtime  Type Protocol
P1             Gi0/1       *HDLC*              Up     27        L2   IS-IS
P2             Gi0/2       *HDLC*              Up     25        L2   IS-IS

PE1# ping 10.0.0.4 source 10.0.0.1
!!!!!
```

### Task 2 — Confirm LDP is initialised (before interface MPLS)

Use `show mpls ldp parameters` to confirm LDP has started. On IOSv 15.9,
`show mpls ldp discovery` returns no output at this stage — that is normal.
The Local LDP Identifier only appears once an interface begins sending hellos (Task 3).

```
PE1# show mpls ldp parameters
LDP Feature Set Manager: State Initialized   ! ← LDP running; global config is correct
  ...
```

### Task 3 — LDP router-id visible after interface MPLS is enabled

Once `mpls ip` is on at least one interface, `show mpls ldp discovery` shows
the Local LDP Identifier and the hello sources for each enabled interface.

```
PE1# show mpls ldp discovery
 Local LDP Identifier:
     10.0.0.1:0                       ! ← router-id is Loopback0
 Discovery Sources:
  Interfaces:
    GigabitEthernet0/1 (ldp): xmit/recv
    GigabitEthernet0/2 (ldp): xmit/recv

PE1# show mpls interfaces
Interface              IP            Tunnel   BGP Static Operational
GigabitEthernet0/1     Yes (ldp)     No       No  No     Yes
GigabitEthernet0/2     Yes (ldp)     No       No  No     Yes
```

### Task 4 — LDP sessions

```
PE1# show mpls ldp neighbor
    Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.2.646 - 10.0.0.1.26000
        State: Oper; Msgs sent/rcvd: 14/14; Downstream
    Peer LDP Ident: 10.0.0.3:0; Local LDP Ident 10.0.0.1:0
        TCP connection: 10.0.0.3.646 - 10.0.0.1.30000
        State: Oper; Msgs sent/rcvd: 13/13; Downstream
```

### Task 5 — LIB bindings for PE2's loopback

```
PE1# show mpls ldp bindings 10.0.0.4 32
  lib entry: 10.0.0.4/32, rev 12
        local binding:  label: 18
        remote binding: lsr: 10.0.0.2:0, label: 20    ! ← from P1
        remote binding: lsr: 10.0.0.3:0, label: 19    ! ← from P2
```

### Task 6 — LFIB showing ECMP for PE2

```
PE1# show mpls forwarding-table 10.0.0.4
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
18     20         10.0.0.4/32      0             Gi0/1      10.10.12.2   ! ← via P1
18     19         10.0.0.4/32      0             Gi0/2      10.10.13.3   ! ← via P2 (ECMP)
```

### Task 7 — PHP: imp-null in the LIB, Pop Label in the LFIB

PE2's `imp-null` binding is only visible on its direct LDP peers (P1 and P2).
PE1 has no session with PE2 and will not show this binding.

```
P1# show mpls ldp bindings 10.0.0.4 32
  lib entry: 10.0.0.4/32, rev 8
        local binding:  label: 18
        remote binding: lsr: 10.0.0.4:0, label: imp-null   ! ← PE2 signals PHP to P1

P2# show mpls ldp bindings 10.0.0.4 32
  lib entry: 10.0.0.4/32, rev 18
        local binding:  label: 20
        remote binding: lsr: 10.0.0.4:0, label: imp-null   ! ← PE2 signals PHP to P2

P1# show mpls forwarding-table 10.0.0.4
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
20     Pop Label  10.0.0.4/32      0             Gi0/2      10.10.24.4   ! ← P1 pops before PE2
```

`★ Insight ─────────────────────────────────────`

- A common point of confusion: the *upstream* router pops the label,
  not the egress PE. PE2 receives an unlabelled IP packet because P1
  (or P2) pops it on PE2's behalf — that is the "penultimate" in PHP.
- ECMP for 10.0.0.4/32 is visible from PE1 only because PE1 is two
  hops from PE2 via two link-disjoint paths of equal IS-IS cost. If
  the IGP metrics differed, only one label would appear.
`─────────────────────────────────────────────────`

---

## 7. Verification Cheatsheet

### IS-IS Configuration

```
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
```

| Command | Purpose |
|---------|---------|
| `router isis CORE` | Enter IS-IS process (process name must match on all routers) |
| `net 49.0001.0000.0000.000X.00` | Set NSAP address — X = device number |
| `is-type level-2-only` | Restrict to L2 adjacencies only; no L1 overhead in a transit-only core |
| `metric-style wide` | Enable 32-bit metrics required for TE extensions in later labs |
| `passive-interface Loopback0` | Advertise the loopback into IS-IS without forming an adjacency on it |
| `ip router isis CORE` | Activate IS-IS on the interface |
| `isis network point-to-point` | Disable DIS election on point-to-point links; faster convergence |

> **Exam tip:** Without `metric-style wide`, IS-IS defaults to narrow metrics (max 63 per link). Wide metrics are mandatory for any lab that introduces RSVP-TE or traffic-engineering extensions.

### MPLS LDP Configuration

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/1
 mpls ip
```

| Command | Purpose |
|---------|---------|
| `mpls label protocol ldp` | Select LDP as the label distribution protocol (global) |
| `mpls ldp router-id Loopback0 force` | Pin the LDP ID to a reachable, stable loopback immediately |
| `mpls ip` (interface) | Enable LDP label distribution and MPLS forwarding on this link |

> **Exam tip:** `mpls ip` on an interface triggers LDP hello discovery on that link. Without it, no LDP session forms across that link even if LDP is configured globally. Loopback0 must **not** have `mpls ip` — labels are exchanged on transit links, not loopbacks.

### LDP Discovery and Session Verification

```
show mpls ldp discovery
show mpls ldp neighbor
show mpls interfaces
show clns neighbors
```

| Command | What to Look For |
|---------|-----------------|
| `show mpls ldp discovery` | Local LDP ID equals `Loopback0` address; hello sources per interface. **Note:** on IOSv 15.9 this command returns no output until at least one interface has `mpls ip` — use `show mpls ldp parameters` to confirm Task 2 instead |
| `show mpls ldp neighbor` | Each directly attached peer in `Oper` state; peer LDP ID matches peer's `Loopback0` |
| `show mpls interfaces` | `Yes (ldp)` in the IP column for every core interface |
| `show clns neighbors` | Every core peer in `Up` state before enabling LDP |

### LIB and LFIB Inspection

```
show mpls ldp bindings
show mpls ldp bindings 10.0.0.4 32
show mpls forwarding-table
show mpls forwarding-table 10.0.0.4
```

| Command | What to Look For |
|---------|-----------------|
| `show mpls ldp bindings` | One local binding + one remote per LDP peer for every IGP prefix |
| `show mpls ldp bindings <prefix> <len>` | Confirm `imp-null` remote binding from the egress PE's own loopback |
| `show mpls forwarding-table` | One LFIB entry per prefix per equal-cost path; label matches IGP next-hop's binding |
| `show mpls forwarding-table <prefix>` | Two rows for PE2 loopback = ECMP; `Pop Label` = PHP active |

> **Exam tip:** `show mpls ldp bindings` shows *all* remote bindings (LIB). `show mpls forwarding-table` shows only the *winning* binding — the one from the current IGP next-hop. A binding present in the LIB but absent from the LFIB is normal; a prefix absent from the LFIB but present in the routing table means MPLS is broken on the outgoing interface.

### Verification Commands Quick Reference

| Command | What to Look For |
|---------|-----------------|
| `show clns neighbors` | All core peers `Up` before enabling MPLS |
| `show mpls ldp discovery` | LDP ID = `Loopback0`; hello sources per core interface |
| `show mpls ldp neighbor` | All peers `Oper`; total = 5 sessions (one per core link) |
| `show mpls interfaces` | `Yes (ldp)` on every core interface; `No` = fault |
| `show mpls ldp bindings 10.0.0.4 32` | `imp-null` from PE2 confirms PHP signalling |
| `show mpls forwarding-table 10.0.0.4` | Two rows = ECMP; `Pop Label` = PHP; `Untagged` = missing `mpls ip` |

### Common LDP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No LDP session on a link | `mpls ip` missing on that interface |
| LDP ID is not the loopback address | `mpls ldp router-id Loopback0 force` missing or applied without `force` |
| Missing remote binding in LIB | LDP session not up to that peer, or binding filtered |
| `Untagged` in LFIB outgoing label | `mpls ip` not running on the outgoing interface |
| Only one LFIB entry for a known-ECMP prefix | One of the equal-cost links missing `mpls ip` or LDP session down |
| LDP session flapping | LDP router-id not reachable (ID points to a missing/transient interface) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS L2 Configuration

<details>
<summary>Click to view All Device Configurations</summary>

```bash
! PE1
router isis CORE
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point

! P1
router isis CORE
 net 49.0001.0000.0000.0002.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
interface GigabitEthernet0/0
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point

! P2
router isis CORE
 net 49.0001.0000.0000.0003.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
interface GigabitEthernet0/0
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point

! PE2
router isis CORE
 net 49.0001.0000.0000.0004.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
!
interface Loopback0
 ip router isis CORE
interface GigabitEthernet0/1
 ip router isis CORE
 isis network point-to-point
interface GigabitEthernet0/2
 ip router isis CORE
 isis network point-to-point
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show clns neighbors
show isis database
ping 10.0.0.4 source 10.0.0.1
```

</details>

---

### Tasks 2 + 3: MPLS LDP Global and Interface Configuration

<details>
<summary>Click to view All Device Configurations</summary>

```bash
! PE1
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/1
 mpls ip
interface GigabitEthernet0/2
 mpls ip

! P1
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
interface GigabitEthernet0/1
 mpls ip
interface GigabitEthernet0/2
 mpls ip

! P2
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/0
 mpls ip
interface GigabitEthernet0/1
 mpls ip
interface GigabitEthernet0/2
 mpls ip

! PE2
mpls label protocol ldp
mpls ldp router-id Loopback0 force
!
interface GigabitEthernet0/1
 mpls ip
interface GigabitEthernet0/2
 mpls ip
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls ldp discovery
show mpls interfaces
show mpls ldp neighbor
```

</details>

---

### Tasks 4–7: Verification Only (no configuration required)

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Task 4 — LDP discovery and sessions
show mpls ldp discovery
show mpls ldp neighbor

! Task 5 — LIB
show mpls ldp bindings
show mpls ldp bindings 10.0.0.4 32

! Task 6 — LFIB
show mpls forwarding-table
show mpls forwarding-table 10.0.0.4

! Task 7 — PHP
show mpls ldp bindings 10.0.0.4 32
show mpls forwarding-table 10.0.0.4   ! run on P1 and P2
traceroute 10.0.0.4
```

</details>

---

Per-device complete configurations are also available in `solutions/`:

- `solutions/PE1.cfg`
- `solutions/P1.cfg`
- `solutions/P2.cfg`
- `solutions/PE2.cfg`

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                      # reset to known-good state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>     # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>     # Ticket 2
```

---

### Ticket 1 — One LDP Session Keeps Flapping

A user reports that `traceroute` from PE1 to PE2 sometimes takes the path `via P1` and sometimes fails for ~30 seconds at a time. Looking at `show mpls ldp neighbor` on more than one router, one session repeatedly cycles between `Oper` and not-present. The IS-IS adjacencies on the same link are stable.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show mpls ldp neighbor` on all routers shows all sessions stable in `Oper` state. Verifier reports `LDP session stable`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On each router, run `show mpls ldp neighbor` — identify which session is cycling in and out.
2. Check `show mpls ldp discovery` on the router with the flapping peer — if the Local LDP Identifier line is absent, LDP has no reachable anchor for its router-id.
3. Run `show running-config | include mpls ldp router-id` on the same router — this shows what interface the router-id is configured to use. **Note:** on IOSv 15.9, `show mpls ldp parameters` does not display the LDP router-id; use the running-config check instead.
4. Cross-check the configured interface with `show ip interface brief` — if the interface does not exist or is down, every TCP session sourced from that address will reset as soon as the address disappears.
5. The fault is the LDP router-id pointing to a non-existent interface, so the router-id address is unreachable and the TCP session cannot stay up.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On the affected router — redirect the LDP router-id back to the correct loopback:
mpls ldp router-id Loopback0 force
```

Verify: `show running-config | include mpls ldp router-id` shows `Loopback0`. `show mpls ldp discovery` shows the Local LDP Identifier equal to the router's Loopback0 address. `show mpls ldp neighbor` shows all sessions in `Oper` state with no cycling over 60 seconds.
</details>

---

### Ticket 2 — Three Peers See Four Labels, One Peer Sees Three

On three of the four core routers, `show mpls ldp bindings` returns a remote binding from every other LDP peer for every `/32` in the IGP. On the fourth router, one of the bindings is permanently absent. IS-IS reachability and `show ip route` are identical to the working routers. The interface shows no MPLS errors and `mpls ip` appears in the running-config.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** All four routers show a complete and symmetric LIB — one local binding and one remote binding per peer for every `/32`. Verifier reports `LDP bindings symmetric`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On each router, run `show mpls ldp bindings` and count the remote bindings for a known `/32` (e.g., 10.0.0.4/32). The router with only 1 remote binding (instead of 2) is the fault location.
2. On that router, run `show mpls interfaces` — confirm which interface shows `No` in the IP column.
3. Run `show running-config interface <X>` — `mpls ip` may appear in the wrong context (under a subinterface, or applied before the interface was fully configured) or may be absent from the actual running state despite appearing in `show run`.
4. The fault is `mpls ip` missing from a core-facing interface, so LDP never formed a session across that link, and the binding from the peer on that link is absent.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On the affected router and interface:
interface GigabitEthernet0/<X>
 mpls ip
```

Verify: `show mpls interfaces` shows `Yes (ldp)` on all core interfaces. `show mpls ldp bindings 10.0.0.4 32` on the previously affected router now shows two remote bindings.
</details>

---

## 10. Lab Completion Checklist

Mark each item only when the corresponding `show`/`ping` actually confirms the state. Stop and re-check the cheatsheet for any item that does not pass on the first try.

### Core Implementation

- [x] Task 1: IS-IS L2 adjacency `UP` on every core link (5 links → 5 adjacencies)
- [x] Task 1: PE1 can ping 10.0.0.2, 10.0.0.3, and 10.0.0.4 sourced from 10.0.0.1
- [x] Task 1: `show isis database` shows four LSPs (one per system-id) on every router
- [x] Task 2: LDP router-id on every device equals its `Loopback0` address
- [x] Task 3: `mpls ip` enabled on every core interface (10 endpoints total); `show mpls interfaces` shows `Yes (ldp)` on all
- [x] Task 4: LDP sessions `Oper` on every directly attached pair (5 sessions total)
- [x] Task 5: LIB on PE1 contains a local binding and one remote binding per LDP peer for each remote `/32`
- [x] Task 6: LFIB on PE1 has **two** outgoing entries (ECMP) for 10.0.0.4/32
- [x] Task 7: P1 and P2 each show `remote binding: lsr: 10.0.0.4:0, label: imp-null` for 10.0.0.4/32 (PE2 signals PHP to its direct peers only); P1 and P2 show `Pop Label` for 10.0.0.4/32 in the LFIB

### Troubleshooting

- [x] Ticket 1 injected; fault diagnosed; session stable; verifier reports `LDP session stable`
- [x] Ticket 2 injected; fault diagnosed; bindings symmetric; verifier reports `LDP bindings symmetric`

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success — every check passed | All scripts |
| 1 | Generic failure — unexpected exception (read stderr) | All scripts |
| 2 | EVE-NG host unreachable or login failed | All scripts |
| 3 | Lab path not found on EVE-NG host (`Lab not found` from API) | All scripts |
| 4 | Required node not found in lab | All scripts |
| 5 | Verifier check failed — actual state does not match expected | Verifier scripts only |
| 6 | Fault injection failed — could not plant the configured fault | Inject scripts only |

CI uses these codes to distinguish "the lab is broken" (0/5) from "the runner is broken" (2/3/4) — they should never be conflated.
