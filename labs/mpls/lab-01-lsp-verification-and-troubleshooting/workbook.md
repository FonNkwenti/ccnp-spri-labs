# Lab 01 â€” LSP Verification with MPLS OAM

**Topic:** MPLS Â· **Difficulty:** Intermediate Â· **Time:** 75 minutes
**Blueprint refs:** 4.1.b Â· **Type:** progressive (extends lab-00)
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

**Exam Objective:** 4.1.b â€” Troubleshoot MPLS: LSP verification (LSP ping, LSP traceroute, PHP, MTU)

This lab teaches you how to verify and troubleshoot Label Switched Paths using Cisco's MPLS OAM tools. By the end, you will understand why IP ping cannot detect a broken LSP, how MPLS ping and traceroute expose the data plane hop-by-hop, how PHP removes the label before the egress PE, and why MPLS MTU must be raised above 1500 bytes to prevent label-induced fragmentation.

### MPLS OAM: Why IP Ping Is Not Enough

When an LSP breaks â€” an interface loses `mpls ip`, a label binding is filtered, or an LFIB entry is missing â€” the router's IP forwarding table is still intact. An ordinary `ping` to the destination address succeeds because the router falls back to IP routing and sends the packet natively. The LSP, however, is broken. Traffic that relies on MPLS forwarding (e.g., customer traffic carried on labels) fails silently.

MPLS OAM tools fix this by sending probe packets that travel *on the data plane using the label stack*, while the echo reply returns *out-of-band via UDP/IP*. If any hop drops the labeled packet, the echo never returns and the ping fails. This is the only reliable way to test whether an LSP is actually operational end-to-end.

| Tool | What it tests | Syntax |
|------|--------------|--------|
| `ping mpls ipv4` | Whether the full LSP is up (end-to-end) | `ping mpls ipv4 10.0.0.4/32` |
| `trace mpls ipv4` | Which label each hop swaps + where the LSP breaks | `trace mpls ipv4 10.0.0.4/32` |
| `trace mpls ipv4 ttl N` | Single-hop probe at depth N | `trace mpls ipv4 10.0.0.4/32 ttl 2` |

### The Label Information Base vs. the Forwarding Table

LDP distributes labels for every prefix in the IP routing table. Each router learns *multiple* remote bindings for every prefix â€” one binding from each LDP peer. All of these land in the **Label Information Base (LIB)**, visible with `show mpls ldp bindings`. The LIB is the raw database of all received label advertisements.

The **Label Forwarding Information Base (LFIB)** â€” `show mpls forwarding-table` â€” contains only the *winning* binding: the label advertised by the router that IS the IGP next-hop for that prefix. If P1 advertises label 200 for 10.0.0.4/32 and P2 advertises label 300, and the IGP chooses P1 as the next-hop, the LFIB installs label 200. Label 300 stays in the LIB, unused, until the IGP changes.

This filtering is why a broken LIB entry (e.g., a missing binding from one peer) may not immediately affect forwarding â€” it only matters if that peer is the current IGP next-hop.

### Penultimate Hop Popping (PHP)

The penultimate LSR (the router one hop before the egress PE) **pops** the label before forwarding the packet to the egress PE. This is standard LDP behavior: the egress PE advertises its own loopback labels as `implicit-null` (label value 3), which signals to the penultimate LSR "pop this label before sending to me." The result: the egress PE receives the packet as native IP, avoiding a second LFIB lookup.

```
PE1 â”€â”€[L=200]â”€â”€â–º P1 â”€â”€[L=300]â”€â”€â–º PE2
                  ^
                  Sees implicit-null for 10.0.0.4/32.
                  Pops label, forwards native IP to PE2.
```

PHP is visible in `show mpls forwarding-table` on the penultimate LSR as `Pop Label` in the outgoing label column.

### MPLS MTU and Label Overhead

Each MPLS label adds **4 bytes** to a frame. A standard Ethernet MTU of 1500 bytes leaves only 1496 bytes for the IP payload when one label is in the stack. If the IP payload is 1500 bytes and a label is pushed, the frame is 1504 bytes â€” which exceeds the default 1500-byte interface MTU and causes fragmentation or silent drops.

The fix is `mpls mtu override 1508` on every core interface, which instructs the router to allow MPLS frames up to 1508 bytes before fragmenting. This accommodates two labels (8 bytes overhead) while keeping the IP payload at 1500 bytes â€” critical for RSVP-TE stacked labels introduced in lab-03.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| MPLS OAM execution | Run `ping mpls` and `trace mpls` to verify LSP end-to-end |
| LSP fault localization | Use TTL-limited traceroute to pinpoint which hop drops the label |
| LIB vs LFIB analysis | Correlate `show mpls ldp bindings` with `show mpls forwarding-table` to explain label selection |
| PHP interpretation | Read PHP (`Pop Label`) entries in the LFIB and explain the optimization |
| MPLS MTU troubleshooting | Diagnose size-sensitive LSP failures and apply the correct MTU fix |
| ECMP over LSPs | Verify multi-path LFIB entries and observe label-based load balancing |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at a Service Provider whose MPLS core (AS 65100) was fully commissioned in lab-00. LDP sessions are up, the LIB is populated, and the LSPs between PE1 and PE2 are supposedly functional. Your job is to *prove* the LSPs work using proper MPLS OAM tools â€” not just IP ping â€” and to identify and fix two operational issues that were discovered during a maintenance window.

```
                  AS 65100 â€” SP Core (IS-IS L2 + MPLS LDP)

          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚        PE1         â”‚         â”‚        P1          â”‚
          â”‚  (SP Edge Router)  â”‚         â”‚  (SP Core Router)  â”‚
          â”‚  Lo0: 10.0.0.1/32  â”œâ”€ L2 â”€â”€â”€â”¤  Lo0: 10.0.0.2/32  â”‚
          â”‚  Gi0/1: 10.10.12.1 â”‚         â”‚  Gi0/0: 10.10.12.2 â”‚
          â”‚  Gi0/2: 10.10.13.1 â”‚         â”‚  Gi0/1: 10.10.23.2 â”‚
          â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â”‚  Gi0/2: 10.10.24.2 â”‚
                   â”‚                     â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                  L3                             L4 (P1â†”P2 cross)
                   â”‚                              â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚        P2          â”‚         â”‚        PE2         â”‚
          â”‚  (SP Core Router)  â”œâ”€ L6 â”€â”€â”€â”¤  (SP Edge Router)  â”‚
          â”‚  Lo0: 10.0.0.3/32  â”‚         â”‚  Lo0: 10.0.0.4/32  â”‚
          â”‚  Gi0/0: 10.10.13.3 â”‚         â”‚  Gi0/1: 10.10.24.4 â”‚
          â”‚  Gi0/1: 10.10.23.3 â”‚         â”‚  Gi0/2: 10.10.34.4 â”‚
          â”‚  Gi0/2: 10.10.34.3 â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

  Link summary:
    L2: PE1 Gi0/1 â†” P1 Gi0/0  (10.10.12.0/24)
    L3: PE1 Gi0/2 â†” P2 Gi0/0  (10.10.13.0/24)
    L4: P1  Gi0/1 â†” P2 Gi0/1  (10.10.23.0/24)
    L5: P1  Gi0/2 â†” PE2 Gi0/1 (10.10.24.0/24)
    L6: P2  Gi0/2 â†” PE2 Gi0/2 (10.10.34.0/24)

  ECMP paths PE1 â†’ PE2:
    Path A: PE1 â†’ P1 (L2) â†’ PE2 (L5)
    Path B: PE1 â†’ P2 (L3) â†’ PE2 (L6)
```

**Key relationships:**

- PE1 and PE2 are the ingress/egress LSRs for any LSP between the two PEs
- P1 and P2 are transit LSRs â€” they swap labels but never inspect the inner IP header
- Two ECMP paths exist (via P1 and via P2); the LFIB at PE1 will show both outgoing interfaces
- PHP occurs at P1 (for the path via P1) and at P2 (for the path via P2)

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge Router (ingress LSR) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | SP Core Router (transit LSR) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | SP Core Router (transit LSR) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | SP Edge Router (egress LSR) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | LDP Router-ID, LSP target source |
| P1 | Loopback0 | 10.0.0.2/32 | LDP Router-ID |
| P2 | Loopback0 | 10.0.0.3/32 | LDP Router-ID |
| PE2 | Loopback0 | 10.0.0.4/32 | LDP Router-ID, LSP ping target |

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

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**

- Hostnames
- Interface IP addressing on all core links and loopbacks
- `no ip domain-lookup`
- IS-IS L2 process (NET, level-2-only, wide metrics, point-to-point on core links, Loopback0 passive)
- MPLS LDP globally (`mpls label protocol ldp`, `mpls ldp router-id Loopback0 force`)
- `mpls ip` enabled on every core-facing interface

**IS NOT pre-loaded** (student configures this):

- MPLS MTU override on core interfaces
- LDP label accept filters (used temporarily in Task 3 to simulate an LSP fault)
- Verification â€” running and interpreting MPLS OAM commands is the lab's primary activity

---

## 5. Lab Challenge: Core Implementation

### Task 1: Run MPLS Ping and Traceroute Baseline

From PE1, verify that the LSP to PE2's loopback (10.0.0.4/32) is fully operational using MPLS OAM tools â€” not IP ping.

- Run an MPLS ping targeting PE2's loopback prefix from PE1. Confirm 5/5 successes.
- Run an MPLS traceroute targeting PE2's loopback prefix from PE1. Note the number of hops and confirm the final hop's label is `implicit-null` (PHP).
- Confirm PE1's LFIB has two outgoing interfaces for 10.0.0.4/32 (ECMP via P1 and via P2).

**Verification:** `ping mpls ipv4 10.0.0.4/32 repeat 5` must show `!!!!!`. `trace mpls ipv4 10.0.0.4/32` must show 2 hops (P router + PE2 receives as native IP). `show mpls forwarding-table 10.0.0.4` must list two outgoing labels.

---

### Task 2: Compare IP Ping vs MPLS Ping

Demonstrate why MPLS ping is the correct tool for LSP verification and when IP ping gives a false positive.

- On P1, temporarily filter the LDP binding for PE2's loopback: create a standard ACL that denies 10.0.0.4/32 and apply it as an inbound label accept filter on P1's LDP neighbor session toward **PE2** (`10.0.0.4`). P1 is one hop from PE2 and its IGP next-hop for 10.0.0.4/32 is PE2 directly â€” the winning LFIB binding comes from PE2's own `imp-null` advertisement, not from P2. Filtering P2's binding (10.0.0.3) has no effect because P2's label for 10.0.0.4/32 is never installed in P1's LFIB.
- From PE1, confirm that a plain IP ping to 10.0.0.4 still succeeds (IGP routing fallback is intact).
- From PE1, confirm that `ping mpls ipv4 10.0.0.4/32` now fails on the path through P1.
- Inspect `show mpls forwarding-table 10.0.0.4` on P1 â€” the outgoing label shows `No label` because PE2's `imp-null` binding was filtered.
- Remove the LDP label filter from P1 and confirm the LSP recovers.

**Verification:** After applying the filter: IP ping to 10.0.0.4 succeeds; `ping mpls ipv4` fails or shows partial success (some probes may use the P2 path). After removing the filter: `ping mpls ipv4` returns to 5/5.

---

### Task 3: Label Stack Analysis with TTL-Limited Traceroute

Walk the label stack hop-by-hop using TTL-limited MPLS traceroute probes from PE1 to PE2.

- Run `trace mpls ipv4 10.0.0.4/32` with TTL limited to 1 â€” identify which router responds and what label it reports.
- Run the same trace with TTL 2 â€” identify the next-hop response and label operation.
- Correlate each hop's reported label with `show mpls forwarding-table` on that router to confirm the label values match.
- Explain why the TTL=1 probe shows `[Labels: implicit-null Exp: 0]` at the P router â€” this is PHP in action. `implicit-null` (label value 3) is what PE2 advertised to P1 for its own loopback, signalling "pop before you send to me." `trace mpls` reports the outgoing label for each hop; `implicit-null` here is the same event that `show mpls forwarding-table` displays as `Pop Label`.

**Verification:** TTL=1 probe returns a response from P1 showing `[Labels: implicit-null Exp: 0]` â€” this is PHP; P1 is signalling it will pop the label. TTL=2 probe reaches PE2, which responds as native IP (no label in the stack). `implicit-null` in `trace mpls` and `Pop Label` in `show mpls forwarding-table` describe the same event.

---

### Task 4: Fix MPLS MTU on All Core Interfaces

The SP operations team reports that large frames between PE1 and PE2 are being fragmented or silently dropped. Diagnose the root cause and apply the correct fix.

- From PE1, generate a large MPLS ping (1500-byte payload) to PE2's loopback and confirm it fails or shows fragmentation.
- Raise the MPLS MTU to 1508 bytes on every core-facing interface on all four routers (PE1, P1, P2, PE2). This accommodates the 4-byte MPLS label overhead while maintaining a 1500-byte IP payload.
- Retest the 1500-byte MPLS ping and confirm end-to-end success.

**Verification:** Before fix: `ping mpls ipv4 10.0.0.4/32 size 1500` shows `.....` or mixed results. After fix: the same command returns `!!!!!`. `show mpls interfaces GigabitEthernet0/1 detail` on PE1 must show `MTU = 1508`. Note: `show interfaces GigabitEthernet0/1` still shows `MTU 1500 bytes` â€” that is the IP MTU, which is unchanged; the MPLS MTU is a separate ceiling raised by `mpls mtu override 1508`.

---

### Task 5: Verify ECMP Load Distribution over LSPs

Confirm that PE1 distributes labeled traffic across both equal-cost LSPs (via P1 and via P2).

- Inspect PE1's LFIB for 10.0.0.4/32 and confirm two entries with different outgoing interfaces (via P1 and via P2). Note: the outgoing label values may be the same or different â€” they come from independent routers' label spaces, so the label value itself is irrelevant. The key observation is two distinct LSPs over different interfaces. Verify with `show mpls ldp bindings 10.0.0.4 32` to confirm the labels are from different peers.
- Run multiple MPLS pings varying the source address to stimulate different hash buckets and observe which path each probe takes (visible in `trace mpls ipv4`).
- Confirm that both P1 and P2 show LFIB activity for 10.0.0.4/32 (`show mpls forwarding-table 10.0.0.4`).

**Verification:** `show mpls forwarding-table 10.0.0.4` on PE1 lists two rows with different outgoing interfaces. Multiple `trace mpls ipv4 10.0.0.4/32` runs (varying source) show different transit P routers.

---

### Task 6: Troubleshoot a Missing `mpls ip` on a Core Interface

The NOC has raised a ticket: from PE1, MPLS traceroute to PE2 occasionally shows `Untagged` at P1's L5 interface (toward PE2), but only on the path via P1. The P2 path works normally.

- Use `show mpls interfaces` on P1 to identify which interface has lost MPLS forwarding.
- Confirm the fault using `show mpls forwarding-table 10.0.0.4 detail` â€” the outgoing label on the affected interface shows `Untagged`.
- Re-enable MPLS IP forwarding on the affected P1 interface and confirm recovery.

**Verification:** After fix: `show mpls interfaces` on P1 shows all core interfaces with MPLS enabled (`Yes` in the IP column). `ping mpls ipv4 10.0.0.4/32 repeat 20` from PE1 returns 20/20 successes.

---

## 6. Verification & Analysis

### Task 1: MPLS Ping and Traceroute Baseline

```
PE1# ping mpls ipv4 10.0.0.4/32 repeat 5
Sending 5, 100-byte MPLS Echos to 10.0.0.4/32,
     timeout is 2 seconds, send interval is 0 msec:
Codes: '!' - success, 'Q' - request not transmitted,
       '.' - timeout, 'U' - unreachable,
       'R' - designated router but not ending router,
       'I' - incomplete traceroute

!!!!! ! â† all 5 probes succeeded; LSP is operational end-to-end

PE1# trace mpls ipv4 10.0.0.4/32
Tracing MPLS Label Switched Path to 10.0.0.4/32, timeout is 2 seconds

Codes: '!' - success, 'Q' - request not transmitted,
       '.' - timeout, 'U' - unreachable,
       'R' - designated router but not ending router,
       'I' - incomplete traceroute

Type escape sequence to abort.
  0 10.10.12.1 MRU 1500 [Labels: 20 Exp: 0]   ! â† PE1 pushes label 20 (example)
L 1 10.10.12.2 MRU 1500 [Labels: implicit-null Exp: 0] 4 ms   ! â† P1 pops (PHP)
! 2 10.0.0.4 4 ms                               ! â† PE2 receives native IP; LSP ends here

PE1# show mpls forwarding-table 10.0.0.4
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
16     20         10.0.0.4/32      0             Gi0/1      10.10.12.2    ! â† via P1
16     19         10.0.0.4/32      0             Gi0/2      10.10.13.3    ! â† via P2 (ECMP)
```

### Task 2: IP Ping vs MPLS Ping (with LDP Filter Applied)

```
PE1# ping 10.0.0.4 repeat 5
!!!!!    ! â† IP ping succeeds â€” IGP route intact, falls back to native IP

PE1# ping mpls ipv4 10.0.0.4/32 repeat 5
.....    ! â† MPLS ping fails on the P1 path â€” LDP binding filtered; LSP broken on that leg

P1# show mpls forwarding-table 10.0.0.4
Local  Outgoing   Prefix           Bytes Label   Outgoing   interface
Label  Label      or Tunnel Id     Switched
20     No label   10.0.0.4/32      0             Gi0/2      10.10.24.2    ! â† "No label" confirms filtered binding
```

### Task 3: TTL-Limited Label Stack Walk

```
PE1# trace mpls ipv4 10.0.0.4/32 ttl 1
  0 10.10.12.1 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.10.12.2 MRU 1500 [Labels: implicit-null Exp: 0] 3 ms   ! â† P1 responds at hop 1; label = pop (PHP)

PE1# trace mpls ipv4 10.0.0.4/32 ttl 2
  0 10.10.12.1 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.10.12.2 [Labels: implicit-null Exp: 0] 3 ms
! 2 10.0.0.4 4 ms   ! â† PE2 responds at hop 2; native IP, no label
```

### Task 4: MPLS MTU â€” Before and After

```
PE1# ping mpls ipv4 10.0.0.4/32 size 1500 repeat 5
.....    ! â† large frames fail before MTU fix (label overhead exceeds 1500-byte interface MTU)

! After configuring mpls mtu override 1508 on all core interfaces:

PE1# ping mpls ipv4 10.0.0.4/32 size 1500 repeat 5
!!!!!    ! â† large frames succeed after MTU fix

PE1# show mpls interfaces GigabitEthernet0/1 detail
Interface GigabitEthernet0/1:
        Type Unknown
        IP labeling enabled (ldp):
          Interface config
        LSP Tunnel labeling not enabled
        BGP labeling not enabled
        MPLS operational
        MTU = 1508                            ! â† MPLS MTU raised; IP MTU (show interfaces) still shows 1500
PE1# show interfaces GigabitEthernet0/1
GigabitEthernet0/1 is up, line protocol is up
  ...
  MTU 1500 bytes, BW 1000000 Kbit/sec, ...   ! â† IP MTU is independent and unchanged
```

### Task 5: ECMP LFIB Entries

```
PE1# show mpls forwarding-table 10.0.0.4
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
16     20         10.0.0.4/32      0             Gi0/1      10.10.12.2    ! â† via P1 (label from peer 10.0.0.2)
16     20         10.0.0.4/32      0             Gi0/2      10.10.13.3    ! â† via P2 (label from peer 10.0.0.3)
! Note: Labels from different routers may be identical (both 20 above) â€”
! each router assigns labels from its own independent label space.
! The key differentiator is the outgoing interface and next-hop, not the label value.
```

### Task 6: Missing `mpls ip` â€” Diagnosis

```
P1# show mpls interfaces
Interface              IP            Tunnel   BGP Static Operational
GigabitEthernet0/0     Yes (ldp)     No       No  No     Yes
GigabitEthernet0/1     Yes (ldp)     No       No  No     Yes
GigabitEthernet0/2     No            No       No  No     No    ! â† MPLS IP not enabled on L5 (toward PE2)

P1# show mpls forwarding-table 10.0.0.4 detail
Local  Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label  Label      or Tunnel Id     Switched      interface
20     Untagged   10.0.0.4/32      0             Gi0/2      10.10.24.2    ! â† "Untagged" confirms no MPLS on Gi0/2

! After re-enabling mpls ip on GigabitEthernet0/2:
P1# show mpls interfaces GigabitEthernet0/2
Interface              IP            Tunnel   BGP Static Operational
GigabitEthernet0/2     Yes (ldp)     No       No  No     Yes    ! â† restored
```

---

## 7. Verification Cheatsheet

### MPLS OAM Commands

```
ping mpls ipv4 10.0.0.4/32
ping mpls ipv4 10.0.0.4/32 repeat 10
ping mpls ipv4 10.0.0.4/32 size 1500
trace mpls ipv4 10.0.0.4/32
trace mpls ipv4 10.0.0.4/32 ttl 1
trace mpls ipv4 10.0.0.4/32 ttl 2
```

| Command | Purpose |
|---------|---------|
| `ping mpls ipv4 <prefix>/32` | Test LSP end-to-end (data-plane only) |
| `trace mpls ipv4 <prefix>/32` | Walk the LSP hop-by-hop, show labels at each hop |
| `trace mpls ipv4 <prefix>/32 ttl N` | Probe exactly N hops into the LSP |
| `ping mpls ipv4 <prefix>/32 size 1500` | Test LSP with jumbo payload (MTU check) |

> **Exam tip:** `ping mpls` sends LSP Echo Requests in-band on the label stack. The reply travels out-of-band as UDP/IP. A plain IP ping tests the control-plane route, not the MPLS data plane.

### LFIB and LIB Inspection

```
show mpls forwarding-table
show mpls forwarding-table 10.0.0.4
show mpls forwarding-table 10.0.0.4 detail
show mpls ldp bindings 10.0.0.4 32
show mpls interfaces
show mpls interfaces GigabitEthernet0/1
```

| Command | What to Look For |
|---------|-----------------|
| `show mpls forwarding-table <prefix>` | Outgoing label, interface, and next-hop for the winning binding |
| `show mpls forwarding-table <prefix> detail` | Confirms `Untagged` when `mpls ip` is missing on the outgoing interface |
| `show mpls ldp bindings <prefix> <len>` | All remote bindings (LIB) â€” more entries than the LFIB |
| `show mpls interfaces` | Confirms MPLS IP enabled per interface; `No` in IP column = fault |

> **Exam tip:** `show mpls forwarding-table` shows *one* label per prefix per path â€” the IGP next-hop's binding. `show mpls ldp bindings` shows *all* bindings including unused ones from non-next-hop peers. Always check the LFIB first when troubleshooting LSP failures.

### MPLS MTU

```
interface GigabitEthernet0/1
 mpls mtu override 1508
```

| Command | Purpose |
|---------|---------|
| `mpls mtu override 1508` (interface) | Allow MPLS frames up to 1508 bytes before fragmenting |
| `show mpls interfaces <intf> detail` | Confirm MPLS MTU value (`MTU = 1508`); this is the authoritative command |
| `show mpls interfaces` | Confirm MPLS is operational on each interface (does not show MTU) |
| `show interfaces <intf>` | Shows IP MTU only (always 1500) â€” do not use to verify MPLS MTU |

> **Exam tip:** The IP MTU and MPLS MTU are independent. `mpls mtu override 1508` raises the MPLS frame ceiling without changing the IP MTU (still 1500). For RSVP-TE with two stacked labels, you need `mpls mtu 1512` â€” but 1508 (one label) is the minimum for LDP-only cores.

### LDP Label Filtering (Used in Task 2 Fault Simulation)

```
ip access-list standard DENY_PE2_LOOPBACK
 deny   10.0.0.4 0.0.0.0
 permit any
!
mpls ldp neighbor 10.0.0.4 labels accept DENY_PE2_LOOPBACK
```

| Command | Purpose |
|---------|---------|
| `mpls ldp neighbor <peer-ldp-id> labels accept <acl>` | Filter which label bindings are accepted from a specific LDP peer |
| `no mpls ldp neighbor <peer> labels accept` | Remove the filter; restore all label bindings from that peer |

> **Exam tip:** LDP label accept filters are inbound â€” they prevent the local router from accepting bindings for certain prefixes from a specific LDP neighbor. They do NOT stop the peer from advertising. The binding is dropped at the receiver, so the LIB entry and LFIB entry disappear locally.

### Verification Commands Quick Reference

| Command | What to Look For |
|---------|-----------------|
| `ping mpls ipv4 10.0.0.4/32` | `!!!!!` = LSP operational; `.....` = LSP broken |
| `trace mpls ipv4 10.0.0.4/32` | Label at each hop; `implicit-null` at penultimate = PHP working |
| `show mpls forwarding-table 10.0.0.4` | Two rows = ECMP; `Untagged` = missing `mpls ip`; `No label` = filtered binding |
| `show mpls interfaces` | `Yes (ldp)` in IP column on every core interface |
| `show mpls ldp bindings 10.0.0.4 32` | Multiple remote bindings; winning binding matches LFIB |

### Common LSP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `ping mpls` fails; IP ping succeeds | LSP broken (missing binding, `mpls ip` off, or LFIB missing) |
| `Untagged` in LFIB outgoing label | `mpls ip` not configured on that outgoing interface |
| `No label` in LFIB | LDP binding filtered (`labels accept`) or LDP session down on that link |
| Large pings fail; small pings succeed | MPLS MTU too low (`mpls mtu override 1508` missing) |
| PHP not observed | Egress PE loopback label is not `implicit-null` â€” check LDP config |
| Only one LFIB entry for a known-ECMP path | One link missing `mpls ip` or LDP session not up on that link |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: MPLS Ping and Traceroute Baseline

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PE1:
ping mpls ipv4 10.0.0.4/32 repeat 5
trace mpls ipv4 10.0.0.4/32
show mpls forwarding-table 10.0.0.4
show mpls ldp bindings 10.0.0.4 32
```

</details>

---

### Task 2: LDP Label Filter â€” Fault Simulation and Restore

<details>
<summary>Click to view P1 Configuration (apply filter)</summary>

```bash
! P1 â€” filter PE2's binding (10.0.0.4 is PE2's LDP ID, the direct next-hop for 10.0.0.4/32)
ip access-list standard DENY_PE2_LOOPBACK
 deny   10.0.0.4 0.0.0.0
 permit any
!
mpls ldp neighbor 10.0.0.4 labels accept DENY_PE2_LOOPBACK
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PE1 â€” with filter applied:
ping 10.0.0.4 repeat 5
ping mpls ipv4 10.0.0.4/32 repeat 5

! On P1:
show mpls forwarding-table 10.0.0.4
show mpls ldp bindings 10.0.0.4 32
```

</details>

<details>
<summary>Click to view P1 Configuration (remove filter)</summary>

```bash
! P1 â€” restore
no mpls ldp neighbor 10.0.0.4 labels accept
no ip access-list standard DENY_PE2_LOOPBACK
```

</details>

---

### Task 3: TTL-Limited Label Stack Walk

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PE1:
trace mpls ipv4 10.0.0.4/32 ttl 1
trace mpls ipv4 10.0.0.4/32 ttl 2
trace mpls ipv4 10.0.0.4/32
```

</details>

---

### Task 4: MPLS MTU Fix

<details>
<summary>Click to view All Device Configurations</summary>

```bash
! PE1
interface GigabitEthernet0/1
 mpls mtu override 1508
interface GigabitEthernet0/2
 mpls mtu override 1508

! P1
interface GigabitEthernet0/0
 mpls mtu override 1508
interface GigabitEthernet0/1
 mpls mtu override 1508
interface GigabitEthernet0/2
 mpls mtu override 1508

! P2
interface GigabitEthernet0/0
 mpls mtu override 1508
interface GigabitEthernet0/1
 mpls mtu override 1508
interface GigabitEthernet0/2
 mpls mtu override 1508

! PE2
interface GigabitEthernet0/1
 mpls mtu override 1508
interface GigabitEthernet0/2
 mpls mtu override 1508
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PE1 â€” before fix:
ping mpls ipv4 10.0.0.4/32 size 1500 repeat 5

! From PE1 â€” after fix:
ping mpls ipv4 10.0.0.4/32 size 1500 repeat 5

! On any device â€” confirm MPLS MTU (not 'show interfaces', which shows IP MTU only):
show mpls interfaces GigabitEthernet0/1 detail
```

</details>

---

### Task 5: ECMP Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PE1 â€” confirm two ECMP LSPs (labels may match â€” they are from different routers):
show mpls forwarding-table 10.0.0.4

! Verify the labels are from different LDP peers:
show mpls ldp bindings 10.0.0.4 32

! Multiple traces with different sources to exercise ECMP hash:
trace mpls ipv4 10.0.0.4/32
trace mpls ipv4 10.0.0.4/32 source 10.0.0.1
```

</details>

---

### Task 6: Restore Missing `mpls ip`

<details>
<summary>Click to view P1 Configuration</summary>

```bash
! P1 â€” re-enable mpls ip on the affected interface (L5 toward PE2)
interface GigabitEthernet0/2
 mpls ip
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On P1:
show mpls interfaces
show mpls forwarding-table 10.0.0.4 detail

! From PE1:
ping mpls ipv4 10.0.0.4/32 repeat 20
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>          # reset to known-good state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 â€” MPLS Ping to PE2 Fails Intermittently from PE1

The NOC reports that MPLS health probes from PE1 to PE2 are showing packet loss â€” roughly half the probes succeed and half time out. IP reachability to 10.0.0.4 is reported as normal.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `ping mpls ipv4 10.0.0.4/32 repeat 20` from PE1 returns 20/20 `!`. Both P1 and P2 show valid (non-`Untagged`, non-`No label`) LFIB entries for 10.0.0.4/32.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From PE1: `ping mpls ipv4 10.0.0.4/32 repeat 20` â€” observe that roughly half fail (the P1 path).
2. From PE1: `trace mpls ipv4 10.0.0.4/32` multiple times â€” one run shows the fault at hop 1 (P1 can't forward), another succeeds via P2.
3. On P1: `show mpls forwarding-table 10.0.0.4` â€” look for `Untagged` or `No label` on the Gi0/2 (L5) outgoing entry.
4. On P1: `show mpls interfaces` â€” confirm which interface has MPLS disabled.
5. The fault is `no mpls ip` on P1's GigabitEthernet0/2 (L5 toward PE2).

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On P1:
interface GigabitEthernet0/2
 mpls ip
```

Verify: `show mpls interfaces` on P1 shows `Yes (ldp)` on all core interfaces. `ping mpls ipv4 10.0.0.4/32 repeat 20` from PE1 returns 20/20.
</details>

---

### Ticket 2 â€” Large Pings Across the LSP Fail; Small Pings Succeed

Users are reporting that 1500-byte frames transiting the MPLS core are being dropped. Connectivity is fine for small packets. The fault appears to be size-sensitive.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `ping mpls ipv4 10.0.0.4/32 size 1500 repeat 10` from PE1 returns 10/10 `!`. All core interfaces show `mpls mtu override 1508` in their running config.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From PE1: `ping mpls ipv4 10.0.0.4/32 size 100 repeat 5` â€” succeeds (`!!!!!`).
2. From PE1: `ping mpls ipv4 10.0.0.4/32 size 1500 repeat 5` â€” fails (`.....`).
3. On each core router: `show run interface GigabitEthernet0/X` â€” look for `mpls mtu override 1508`. The fault router is missing it on at least one interface.
4. The label overhead (4 bytes per label) pushes the 1500-byte frame to 1504+ bytes, exceeding the default MPLS MTU of 1500 bytes on the faulted interface.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On the faulted router (check all core interfaces):
interface GigabitEthernet0/<X>
 mpls mtu override 1508
```

Verify: `ping mpls ipv4 10.0.0.4/32 size 1500 repeat 10` from PE1 returns 10/10.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] Task 1: `ping mpls ipv4 10.0.0.4/32` from PE1 returns 5/5 successes
- [x] Task 1: `trace mpls ipv4 10.0.0.4/32` shows 2 hops; penultimate shows `implicit-null` (PHP)
- [x] Task 1: `show mpls forwarding-table 10.0.0.4` on PE1 shows two ECMP entries (via P1 and P2)
- [x] Task 2: With LDP filter applied on P1: IP ping to 10.0.0.4 succeeds; MPLS ping fails
- [x] Task 2: P1 LFIB shows `No label` or `Untagged` for 10.0.0.4/32 after filter applied
- [x] Task 2: Filter removed; MPLS ping recovers to 5/5
- [x] Task 3: TTL=1 probe returns ICMP from P1 with label reported; TTL=2 shows PHP (`implicit-null`)
- [x] Task 4: `ping mpls ipv4 10.0.0.4/32 size 1500` fails before MTU fix; succeeds after
- [x] Task 4: All core interfaces on all 4 routers show `MTU = 1508` in `show mpls interfaces <intf> detail`
- [x] Task 5: Two LFIB entries for 10.0.0.4/32 on PE1 with different outgoing interfaces
- [x] Task 6: P1's Gi0/2 MPLS restored; `show mpls interfaces` shows all interfaces operational

### Troubleshooting

- [ ] Ticket 1 injected; fault diagnosed as `no mpls ip` on P1 Gi0/2; fixed; 20/20 MPLS pings pass
- [ ] Ticket 2 injected; fault diagnosed as missing `mpls mtu override 1508`; fixed; large pings pass

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
