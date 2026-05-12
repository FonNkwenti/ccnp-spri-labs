# Lab 01 — Nonstop Forwarding (NSF) and Nonstop Routing (NSR)

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

**Exam Objective:** 1.7.b, 1.7.c — Implement Fast Convergence: Nonstop Forwarding (NSF) and Nonstop Routing (NSR) (Fast Convergence topic)

This lab builds directly on the BFD and timer foundation from lab-00 and adds the high-availability layer that lets a restarting router's neighbours cooperate in minimising routing disruption. You will configure and verify IS-IS Graceful Restart (NSF), BGP Graceful Restart, and examine NSR as a conceptual alternative — with a platform-specific note on CSR1000v's single-RP limitation for NSR.

---

### IS-IS Graceful Restart (NSF)

IS-IS Graceful Restart (GR), also called Nonstop Forwarding in Cisco terminology, is defined in RFC 5306. When an IS-IS router restarts its control plane while its forwarding plane continues to operate, it sends a Hello PDU with the GR restart bit set. Neighbouring routers that receive this signal enter **GR helper mode**: they keep the restarting router's LSP alive in the LSDB and suppress route withdrawals for the duration of the stale timer (typically 60–120 seconds).

The result: the rest of the network never sees a topology change, so no SPF runs, no route flaps, and no packet drops — as long as the restarting router's hardware plane keeps forwarding.

```
! Enable IS-IS Graceful Restart (RFC 5306 IETF variant) on R1-R4
router isis
 nsf ietf
```

```
! Verify GR capability is advertised to neighbours
show isis neighbors detail
! Look for: Restart capable: yes
```

Both sides of each adjacency must have `nsf ietf` configured for full GR protection. A one-sided configuration means the non-GR neighbour will still withdraw routes when its peer restarts.

### BGP Graceful Restart

BGP Graceful Restart (RFC 4724) works on the same cooperative model. The restarting speaker advertises the GR capability during OPEN negotiation. When it restarts:
1. Its peers ("GR helpers") keep the Adj-RIB-In stale — they do not withdraw the restarting speaker's routes from the RIB immediately.
2. The restarting speaker reconnects and completes an End-of-RIB exchange within the stale timer.
3. Any stale routes not refreshed after End-of-RIB are then removed.

```
! Enable BGP GR on all speakers
router bgp <ASN>
 bgp graceful-restart
```

```
! Verify GR capability is negotiated
show ip bgp neighbors <peer-ip>
! Look for: Graceful Restart Capability: advertised and received
! And: Graceful restart: enabled
```

**Key difference from IS-IS NSF:** BGP GR is stateless on the forwarding side — BGP does not manage hardware FIB entries directly. The stale timer just prevents immediate withdrawal so the FIB (populated by IS-IS or static routes) remains valid while the BGP control plane reconnects.

### Nonstop Routing (NSR) — Conceptual Reference

NSR is a fundamentally different HA approach: instead of coordinating with neighbours, the restarting router maintains all protocol state on a standby Route Processor (RP). During an RP switchover, the standby takes over seamlessly — protocol adjacencies never drop because the standby RP was already holding them.

**Platform note — CSR1000v (IOS-XE 17.03.05):** The `nsr` (IS-IS) and `bgp nsr` (BGP) commands are **rejected** on CSR1000v, which is a single-RP platform. On production dual-RP hardware (ASR 9000, NCS, CRS running IOS-XR), NSR allows an RP switchover that is completely invisible to BGP and IS-IS neighbours. The exam tests your ability to configure NSR and understand this distinction.

| Feature | Cooperative | Requires neighbour config | Requires hardware HA |
|---------|-------------|--------------------------|----------------------|
| NSF (IS-IS GR) | Yes — neighbour must be a GR helper | Yes | No |
| BGP GR | Yes — peer must advertise GR capability | Yes | No |
| NSR | No — fully local | No | Yes (standby RP) |

**Skills this lab develops:**

| Skill | Mode | Description |
|-------|------|-------------|
| IS-IS Graceful Restart (NSF) | **Live** | Configure `nsf ietf` on R1–R4; verify with `show isis neighbors detail` |
| BGP Graceful Restart | **Live** | Configure `bgp graceful-restart`; verify GR capability exchange |
| GR helper behaviour | **Live** | Observe stale-route retention on R1/R3 during R5 BGP restart |
| NSF vs no-GR comparison | **Live** | Measure BGP route persistence with and without GR enabled |
| IS-IS NSR configuration | Conceptual reference | Understand `nsr`; document why CSR1000v rejects the command |
| BGP NSR configuration | Conceptual reference | Understand `bgp nsr`; document single-RP platform limitation |
| NSF vs NSR analysis | Analytical | Compare cooperative vs local HA approaches in writing |
| Asymmetric GR troubleshooting | **Live** | Diagnose and fix one-sided GR configuration |

---

## 2. Topology & Scenario

**Scenario:** Your SP core has BFD and timer tuning in place from lab-00. The operations team now wants to add HA-level protection: control-plane restarts on any router should not cause measurable forwarding disruption. You need to configure IS-IS Graceful Restart across all core routers, BGP Graceful Restart across all BGP speakers, and document the NSR design intent on R1 as a reference for when the team migrates to dual-RP hardware.

```
              AS 65100 (SP core — IS-IS L2 + iBGP full mesh)

         ┌──────────────────────┐              ┌──────────────────────┐
         │         R1           │── L1 ─────── │         R2           │
         │  SP Edge AS 65100    │   Gi1  Gi1   │  SP Core AS 65100    │
         │  Lo0: 10.0.0.1/32    │  10.1.12.0   │  Lo0: 10.0.0.2/32    │
         └──┬──────┬──────┬─────┘              └────────────┬─────────┘
        L4  │  L5  │  L6  │ Gi4                          L2  │ Gi2
       Gi2  │ Gi3  │      │ 10.1.15.0                       │ 10.1.23.0
            │      │      │                                  │
   ┌────────┴──┐   │      │                      ┌───────────┴────────────┐
   │    R4     │   └──────┼──────────────────────►         R3             │
   │  SP Core  │          │             Gi3 L5   │  SP Edge AS 65100      │
   │ 10.0.0.4  │          │       Gi2 10.1.34.0  │  Lo0: 10.0.0.3/32     │
   │  /32      │◄── L3 ──►│              Gi1     │                        │
   └───────────┘  10.1.34 │              L3      └──┬───────────────────┬─┘
       Gi1 R4            │                     L7  │ Gi4              L5 │ Gi3
                          │               10.1.35.0 │                   │
                          │                         │                   │
                          │                ┌────────┴──────────────────┘
                          │                │
                          │       ┌────────┴──────────────────┐
                          └───────►         R5                │
                            L6 Gi1│   CE AS 65200             │
                         10.1.15.0│  Lo0: 10.0.0.5/32        │
                                    │  Lo1: 192.0.2.1/24      │
                                    └────────────────────────-┘
```

**Link reference:**

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi1 | R2 Gi1 | 10.1.12.0/24 | SP core — IS-IS L2, iBGP transport |
| L2 | R2 Gi2 | R3 Gi1 | 10.1.23.0/24 | SP core — IS-IS L2, iBGP transport |
| L3 | R3 Gi2 | R4 Gi1 | 10.1.34.0/24 | SP core — IS-IS L2, iBGP transport |
| L4 | R1 Gi2 | R4 Gi2 | 10.1.14.0/24 | Ring closer — IS-IS L2, LFA alternate |
| L5 | R1 Gi3 | R3 Gi3 | 10.1.13.0/24 | Diagonal — IS-IS L2, short path R1↔R3 |
| L6 | R1 Gi4 | R5 Gi1 | 10.1.15.0/24 | eBGP R1 (AS 65100) ↔ R5 (AS 65200) |
| L7 | R3 Gi4 | R5 Gi2 | 10.1.35.0/24 | eBGP R3 (AS 65100) ↔ R5 (AS 65200) |

**Key relationships:**
- IS-IS NSF adjacency pairs: R1↔R2 (L1), R2↔R3 (L2), R3↔R4 (L3), R1↔R4 (L4), R1↔R3 (L5). Every pair must have `nsf ietf` on both sides.
- BGP GR must be configured on all five BGP speakers — including R5 (the eBGP peer). An eBGP session where only one side advertises GR provides no protection.
- NSR is a conceptual reference on this CSR1000v topology — the commands are rejected on a single-RP platform. The exam expects you to know the configuration syntax and the dual-RP requirement.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R2 | SP Core — iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R3 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R4 | SP Core — redundant path, iBGP in AS 65100 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |
| R5 | External CE — dual-homed eBGP in AS 65200 | CSR1000v | csr1000vng-universalk9.17.03.05 | 3 GB |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP peering source, BFD multi-hop source |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP peering source, BFD multi-hop source |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, iBGP peering source |
| R5 | Loopback0 | 10.0.0.5/32 | Router ID, eBGP peering source, BFD multi-hop endpoint |
| R5 | Loopback1 | 192.0.2.1/24 | External prefix announced into AS 65100 via eBGP |

### Cabling

| Link ID | From | To | Subnet | Interface (From) | Interface (To) |
|---------|------|----|--------|-----------------|----------------|
| L1 | R1 | R2 | 10.1.12.0/24 | GigabitEthernet1 | GigabitEthernet1 |
| L2 | R2 | R3 | 10.1.23.0/24 | GigabitEthernet2 | GigabitEthernet1 |
| L3 | R3 | R4 | 10.1.34.0/24 | GigabitEthernet2 | GigabitEthernet1 |
| L4 | R1 | R4 | 10.1.14.0/24 | GigabitEthernet2 | GigabitEthernet2 |
| L5 | R1 | R3 | 10.1.13.0/24 | GigabitEthernet3 | GigabitEthernet3 |
| L6 | R1 | R5 | 10.1.15.0/24 | GigabitEthernet4 | GigabitEthernet1 |
| L7 | R3 | R5 | 10.1.35.0/24 | GigabitEthernet4 | GigabitEthernet2 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R5 | 192.0.2.0/24 | eBGP network statement | External CE prefix; announced to R1 and R3 via eBGP |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on all five routers
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup` on all routers
- IS-IS L2 on R1–R4 with tuned hello/hold timers (1 s / 3 s) and SPF/PRC throttle
- BFD single-hop on all IS-IS core interfaces (150 ms × 3 = 450 ms detection)
- iBGP full mesh in AS 65100 (R1–R4), loopback-sourced with `next-hop-self` on R1 and R3
- eBGP sessions R1↔R5 and R3↔R5, loopback-sourced with multihop, BFD multi-hop, and tuned timers
- BGP multi-hop BFD templates and peer bindings on R1, R3, and R5

**IS NOT pre-loaded** (student configures this):
- IS-IS Graceful Restart (NSF) on R1–R4
- BGP Graceful Restart on all BGP speakers (R1–R5)
- IS-IS and BGP NSR conceptual documentation (commands rejected on CSR1000v)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IS-IS Graceful Restart (NSF) on R1–R4

- On each of R1, R2, R3, and R4, enable IS-IS Graceful Restart using the IETF variant under the IS-IS process.
- Verify that all IS-IS neighbours now advertise restart capability in their adjacency details.
- Confirm the `Restart capable` flag shows `yes` for every IS-IS neighbour on R1.

**Verification:** `show isis neighbors detail` on R1 must show `Restart capable: yes` for all three neighbours (R2, R3, R4). Also confirm `show isis` output includes `NSF: enabled (IETF)` in the process summary.

---

### Task 2: Enable BGP Graceful Restart on All BGP Speakers

- On each of R1, R2, R3, R4, and R5, enable BGP Graceful Restart under the BGP process.
- Verify that the GR capability has been negotiated with all peers. You may need to reset BGP sessions for the capability to appear.

> After enabling `bgp graceful-restart`, do a soft reset of each BGP session — GR capability is exchanged during the OPEN message, so existing sessions must reconvene. Use the appropriate soft-inbound reset command rather than a hard clear.

**Verification:** `show ip bgp neighbors 10.0.0.5` on R1 must show `Graceful Restart Capability: advertised and received` and `Graceful restart: enabled`. Repeat the check on R5 for neighbours 10.0.0.1 and 10.0.0.3.

---

### Task 3: Test IS-IS NSF and BGP GR in Practice

This task has two parts: an IS-IS NSF capability verification and a BGP GR live test.

**Part A — IS-IS NSF capability advertisement:**

- Run `show isis neighbors detail` on R1. Confirm `Restart capable: yes` appears for all three neighbours (R2, R3, R4).
- Run `show isis database` on R1 — confirm all four IS-IS LSPs are present with non-zero sequence numbers (R1–R4 only; R5 runs no IS-IS process).

**Part B — BGP GR live test:**

> **Pre-condition — disable BFD fall-over before testing:** The pre-loaded config has
> `fall-over bfd multi-hop` on R1 and R3's neighbor 10.0.0.5. When `clear ip bgp *` runs
> on R5, it sends a BFD ADMINDOWN signal. This causes R1 to immediately tear down the BGP
> session via BFD fall-over **without entering GR helper mode**, bypassing GR entirely. You
> must temporarily remove fall-over BFD on both R1 and R3 before this test, then restore it.
>
> ```
> ! On R1 and R3 — before the test
> router bgp 65100
>  neighbor 10.0.0.5 no fall-over bfd
> ```

- From R2, start a sustained extended ping to 192.0.2.1 (R5's Loopback1) sourced from R2's Loopback0. R2 reaches this prefix via iBGP from R1 or R3.
- On R5, issue a hard BGP clear for all neighbours (`clear ip bgp *`). This resets the eBGP sessions R5↔R1 and R5↔R3.
- Observe that R2's ping experiences minimal or no packet loss. With BFD fall-over removed and BGP GR enabled on R1 and R3, they enter GR helper mode and retain the 192.0.2.0/24 route as stale during the GR window (~120 s default), so R2's iBGP path via R1 stays valid.
- Run `show ip bgp 192.0.2.0/24` on R2 during the GR window and confirm the route is still present with a stale marker.

After the test, restore fall-over BFD on R1 and R3:
```
! On R1 and R3 — after the test
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

**Verification:** `show ip bgp neighbors 10.0.0.5` on R1 during the GR window must show `BGP state = Active` with `Graceful restart: enabled` — indicating R1 is holding stale routes while waiting for R5 to reconnect. After R5 reconnects, confirm state returns to `Established` and the stale marker clears from R2's BGP table.

---

### Task 4: Contrast — Disable BGP GR and Repeat

> **Keep BFD fall-over disabled** for this task too (same pre-condition as Task 3 Part B). If fall-over BFD is active, route withdrawal happens via BFD before BGP even has time to withdraw — the contrast is not meaningful because both the GR and no-GR cases would show identical immediate loss.

- Ensure `fall-over bfd` is still removed from R1 and R3's neighbor 10.0.0.5 (from Task 3 pre-condition).
- On R1 and R3, disable BGP Graceful Restart: `no bgp graceful-restart`.
- Repeat Part B of Task 3: ping 192.0.2.1 from R2, then hard-clear BGP on R5.
- Observe that R2's ping drops immediately when R5's BGP sessions reset — because R1 now withdraws 192.0.2.0/24 as soon as R5's session drops, removing it from R2's iBGP table.
- After observing the difference, re-enable BGP Graceful Restart on R1 and R3, and restore fall-over BFD on both:

```
! On R1 and R3
router bgp 65100
 bgp graceful-restart
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

Also re-enable `bgp graceful-restart` on R5 if it was removed during the contrast test.

**Verification:** `show ip bgp 192.0.2.0/24` on R2 immediately after clearing BGP on R5 (without GR) must show the route absent — unlike the GR case where it remained as stale. After restoring GR and fall-over BFD, confirm all sessions are `Established` before proceeding.

---

### Task 5: IS-IS NSR — Conceptual Reference (R1)

> **Platform note:** The `nsr` command is **rejected** under `router isis` on CSR1000v (IOS-XE 17.03.05) — it does not exist in the command set. This task is a conceptual reference exercise only.

- Review the IS-IS NSR configuration syntax below. On a supported dual-RP platform (ASR 9000, NCS, CRS running IOS-XR), this command enables the standby RP to mirror the IS-IS protocol state continuously, so an RP switchover is invisible to IS-IS neighbours.
- Attempt to enter the `nsr` command under `router isis` on R1. Observe that CSR1000v rejects it with an "Unrecognized command" error — this is expected behaviour on a single-RP platform.
- Document the key distinction: NSR is a **local** HA mechanism — it requires no neighbour configuration and is invisible to peers. The trade-off is that it requires standby RP hardware.

**Reference configuration (supported dual-RP platforms only):**
```
router isis
 nsr
```

**Conceptual check:** Answer the following questions:
1. Why does NSR not require any configuration on neighbouring routers (unlike NSF)?
2. What happens to IS-IS adjacencies during an RP switchover on an NSR-enabled router?
3. On a CSR1000v platform (single RP), what would you observe if `nsr` were somehow accepted — and why?

**Verification (reference only):** `show running-config | section router isis` on R1 will NOT show `nsr` (the command was rejected). On a supported dual-RP platform, `show isis nsr` would display NSR state and the standby RP synchronisation status.

---

### Task 6: BGP NSR — Conceptual Reference (R1)

> **Platform note:** The `bgp nsr` command is **rejected** under `router bgp` on CSR1000v (IOS-XE 17.03.05). This task is a conceptual reference exercise only.

- Review the BGP NSR configuration syntax below. On a supported dual-RP platform, this command synchronises BGP session state (TCP connections, peer tables, received prefixes) to the standby RP so that an RP switchover is invisible to BGP peers — no session reset, no route withdrawal.
- Attempt to enter `bgp nsr` under `router bgp 65100` on R1. Observe the rejection — this is the expected single-RP platform behaviour.
- Compare BGP NSR against BGP GR: GR is cooperative (both peers must support it, routes go stale during reconvergence), while NSR is local (peers see nothing, no stale window, but requires standby RP hardware).

**Reference configuration (supported dual-RP platforms only):**
```
router bgp 65100
 bgp nsr
```

**Verification (reference only):** `show running-config | section router bgp` on R1 will NOT show `bgp nsr` (command rejected).

| Feature | Configuration command | Available on CSR1000v? | Requires |
|---------|-----------------------|------------------------|---------|
| IS-IS GR (NSF) | `nsf ietf` | **Yes** — fully functional | Neighbour GR-helper enabled |
| BGP GR | `bgp graceful-restart` | **Yes** — fully functional | Peer GR capability (software-only mechanism) |
| IS-IS NSR | `nsr` | No — command rejected | Standby RP hardware |
| BGP NSR | `bgp nsr` | No — command rejected | Standby RP hardware |

---

### Task 7: NSF vs NSR Comparison

In the space below (or in your lab notes), write a short comparison of NSF and NSR covering:
- Which protocol peers are aware of the restart event in each case
- What hardware is required for each mechanism
- What happens if the stale timer expires before the restarting router recovers (NSF)
- Whether either mechanism protects against a link failure (vs. a control-plane restart)

> There is no configuration output to verify for this task — it is an analytical exercise that reinforces the exam-level distinctions between the two approaches.

**Verification:** You can self-check using `show isis neighbors detail` to confirm GR restart capability advertisement and `show ip bgp neighbours` for BGP GR. Confirm `nsf ietf` is present under `router isis` on R1, and `bgp graceful-restart` is present under `router bgp 65100` on R1. Note that `nsr` and `bgp nsr` are NOT present — they are rejected on CSR1000v.

---

### Task 8: Troubleshoot Asymmetric GR Configuration (Guided)

> This task simulates a fault planted by the operations team. Use the inject script in Section 9 to introduce the fault, then diagnose and fix it.

- After injecting Ticket 1's fault, observe that reloading R2 causes R1 to immediately withdraw R2's routes (IS-IS LSP removed from LSDB on R1) rather than entering GR helper mode.
- Examine the IS-IS GR configuration on both R1 and R2 using `show running-config` and `show isis neighbors detail`.
- Identify which router is missing its IS-IS Graceful Restart configuration, and restore the symmetric setup so both sides have the IETF GR variant enabled.

**Verification:** After the fix, `show isis neighbors detail` on R1 must show `Restart capable: yes` for R2. Trigger another IS-IS process reset on R2 and confirm R1 enters GR helper mode (R2 remains in neighbour table in a GR/recovering state rather than disappearing immediately).

---

## 6. Verification & Analysis

### Task 1 — IS-IS GR Capability Advertisement

```
R1# show isis neighbors detail
System Id      Interface   SNPA               State  Holdtime  Type Protocol
R2             Gi1         xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R2 Up
  Area Address(es): 49.0001
  SNPA: xxxx.xxxx.xxxx
  State Changed: never
  Last LSP ID: R2.00-00
  BFD IPv4 Session State: Up           ! ← BFD still active from lab-00
  Restart capable: yes                 ! ← IS-IS GR advertised by R2
  Suppressing adjacency: no            ! ← not in a restart event
R4             Gi2         xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R4 Up
  Restart capable: yes
  Suppressing adjacency: no
R3             Gi3         xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R3 Up
  Restart capable: yes
  Suppressing adjacency: no
```

```
R1# show isis | include NSF
  NSF: enabled (IETF)                                  ! ← IS-IS NSF active
```

### Task 2 — BGP GR Capability Exchange

```
R1# show ip bgp neighbors 10.0.0.5
BGP neighbor is 10.0.0.5,  remote AS 65200, external link
  BGP state = Established, up for 00:10:00
  ...
  Graceful Restart Capability: advertised and received    ! ← both sides have GR
    Remote Restart timer is 120 seconds
    Address families advertised by peer:
      IPv4 Unicast (was not preserved)
  Graceful restart: enabled                               ! ← GR active for this session

R1# show ip bgp neighbors 10.0.0.2
BGP neighbor is 10.0.0.2,  remote AS 65100, internal link
  BGP state = Established, up for 00:10:00
  Graceful Restart Capability: advertised and received    ! ← iBGP peer also GR-capable
  Graceful restart: enabled
```

### Task 3 — BGP GR Live Test

```
! During GR window (after clearing BGP on R5, before R5 reconnects)
R1# show ip bgp neighbors 10.0.0.5
BGP neighbor is 10.0.0.5,  remote AS 65200, external link
  BGP state = Active                                      ! ← reconnecting
  Graceful restart: enabled
  GR State: Stale routes retained                         ! ← GR helper keeping stale routes

R2# show ip bgp 192.0.2.0/24
BGP routing table entry for 192.0.2.0/24, version 7
Paths: (1 available, best #1, table default, Stale)       ! ← route retained as stale
  Not advertised to any peer
  Refresh Epoch 2
  65200, (stale)
    10.0.0.1 from 10.0.0.1 (10.0.0.1)                    ! ← via R1 next-hop-self
      Origin IGP, localpref 100, valid, internal, best
```

### Task 4 — Contrast Without GR

```
! Immediately after clearing BGP on R5, with GR disabled on R1
R2# show ip bgp 192.0.2.0/24
% Network not in table                                    ! ← route immediately withdrawn
```

### Tasks 5 and 6 — NSR Configuration (Reference Only)

> **Platform note:** `nsr` (IS-IS) and `bgp nsr` (BGP) are **rejected** on CSR1000v (IOS-XE 17.03.05). Only `bgp graceful-restart` is configurable on this topology. The reference output below shows what a supported dual-RP platform would look like.

```
! What CSR1000v shows after Task 1 and Task 2 (no nsr):
R1# show running-config | section router isis
router isis
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
 spf-interval 5 50 200
 prc-interval 5 50 200
 nsf ietf                                                 ! ← IS-IS GR (Task 1 — live, available on CSR1000v)
! Note: no "nsr" line — the nsr command was rejected

! What CSR1000v shows after Task 2:
R1# show running-config | section router bgp
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 bgp graceful-restart                                     ! ← BGP GR (Task 2 — live)
 neighbor 10.0.0.2 remote-as 65100
 ...
! Note: no "bgp nsr" line — the bgp nsr command was rejected
```

---

## 7. Verification Cheatsheet

### IS-IS Graceful Restart (NSF)

```
router isis
 nsf ietf       ! IETF standard variant (RFC 5306)
```

| Command | Purpose |
|---------|---------|
| `show isis neighbors detail` | Check `Restart capable: yes` per neighbour |
| `show isis` | Confirm `NSF: enabled (IETF)` in process summary |
| `debug isis adj-packets` | Watch Hello PDUs with restart bit during GR event |

> **Exam tip:** `nsf ietf` must be configured on BOTH sides of each adjacency. A router that is not GR-capable will tear down the adjacency normally on its peer's restart — it does not know to stay as a helper.

### BGP Graceful Restart

```
router bgp <ASN>
 bgp graceful-restart
```

| Command | Purpose |
|---------|---------|
| `show ip bgp neighbors X | include Graceful\|GR` | Confirm capability advertised and received |
| `show ip bgp X.X.X.X/nn` | Check for `(stale)` marker during GR window |
| `clear ip bgp X soft in` | Trigger inbound soft reset (does NOT break GR) |
| `clear ip bgp X` | Hard reset — triggers a GR event if both sides are GR-capable |

> **Exam tip:** BGP GR capability is exchanged in the OPEN message. If you enable `bgp graceful-restart` on an existing session, you must reset the session (hard clear or bounce) before the capability appears in `show ip bgp neighbors`. A soft reset does not re-exchange OPEN.

### IS-IS NSR (Conceptual — CSR1000v rejects this command)

```
! Supported platforms: IOS-XR, ASR 9000, NCS, CRS (dual-RP required)
router isis
 nsr
```

| Command | Purpose |
|---------|---------|
| `show running-config | section router isis` | Confirm `nsr` is present (supported platforms only) |
| `show isis nsr` | NSR state (supported platforms only) |

> **Exam tip:** NSR is local — it requires no configuration on any neighbour. The trade-off: NSR requires standby RP hardware; NSF works with any adjacent GR-capable router.

### BGP NSR (Conceptual — CSR1000v rejects this command)

```
! Supported platforms: IOS-XR, ASR 9000, NCS, CRS (dual-RP required)
router bgp <ASN>
 bgp nsr
```

| Command | Purpose |
|---------|---------|
| `show running-config | section router bgp` | Confirm `bgp nsr` is present (supported platforms only) |
| `show ip bgp summary` | Verify sessions remain up (functional only with standby RP) |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis neighbors detail` | `Restart capable: yes` for all IS-IS adjacencies |
| `show isis` | `NSF: enabled (IETF)` in process summary |
| `show ip bgp neighbors X | include Graceful` | `Graceful Restart Capability: advertised and received` |
| `show ip bgp X.X.X.X/nn` | `(stale)` marker present during GR window |
| `show run | section router isis` | `nsf ietf` present; note no `nsr` (rejected on CSR1000v) |
| `show run | section router bgp` | `bgp graceful-restart` present; note no `bgp nsr` (rejected) |

### Common NSF/NSR Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| IS-IS LSP removed immediately on neighbour restart | `nsf ietf` missing on one or both sides of adjacency |
| BGP route withdrawn immediately on peer session reset | `bgp graceful-restart` missing on one or both sides |
| `bgp graceful-restart` shows `advertised` but not `received` | Peer has not been reset since GR was enabled — hard-clear required |
| `nsr` / `bgp nsr` rejected with "Unrecognized command" | CSR1000v (IOS-XE 17.03.05) single-RP platform — use IOS-XR / ASR 9000 / NCS / CRS for live NSR |
| `nsr` accepted but no functional difference | Expected on platforms that accept the command but have no standby RP |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS Graceful Restart (NSF) on R1–R4

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router isis
 nsf ietf
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router isis
 nsf ietf
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router isis
 nsf ietf
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router isis
 nsf ietf
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show isis neighbors detail
show isis | include NSF
```

</details>

---

### Task 2: BGP Graceful Restart on R1–R5

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router bgp 65100
 bgp graceful-restart
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router bgp 65100
 bgp graceful-restart
```

</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router bgp 65100
 bgp graceful-restart
```

</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router bgp 65100
 bgp graceful-restart
```

</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router bgp 65200
 bgp graceful-restart
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp neighbors 10.0.0.5 | include Graceful|GR
show ip bgp neighbors 10.0.0.2 | include Graceful|GR
```

</details>

---

### Task 3: BGP GR Live Test

<details>
<summary>Click to view Pre-condition — Remove fall-over BFD</summary>

```bash
! On R1 and R3 — required before the test
router bgp 65100
 neighbor 10.0.0.5 no fall-over bfd
```

</details>

<details>
<summary>Click to view Post-test — Restore fall-over BFD</summary>

```bash
! On R1 and R3 — after test completes
router bgp 65100
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp neighbors 10.0.0.5 | include State|graceful|GR|Stale
show ip bgp 192.0.2.0/24
```

</details>

---

### Task 4: Contrast — Disable BGP GR

<details>
<summary>Click to view Removing GR on R1 and R3</summary>

```bash
! On R1 and R3
router bgp 65100
 no bgp graceful-restart
```

</details>

<details>
<summary>Click to view Restoring GR and fall-over BFD</summary>

```bash
! On R1 and R3 — after observing contrast
router bgp 65100
 bgp graceful-restart
 neighbor 10.0.0.5 fall-over bfd multi-hop
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp 192.0.2.0/24
```

</details>

---

### Tasks 5 and 6: IS-IS NSR and BGP NSR (Conceptual Reference)

<details>
<summary>Click to view Reference Configuration (dual-RP platforms only)</summary>

```bash
! IS-IS NSR — requires dual-RP hardware (IOS-XR, ASR 9000, NCS, CRS)
! Rejected on CSR1000v (IOS-XE 17.03.05) — single-RP platform
router isis
 nsr

! BGP NSR — requires dual-RP hardware
! Rejected on CSR1000v (IOS-XE 17.03.05)
router bgp 65100
 bgp nsr
```

</details>

<details>
<summary>Click to view Conceptual Check Answers</summary>

1. **Why no neighbour config?** NSR synchronises protocol state to the standby RP locally. When the switchover occurs, the standby RP is already in the correct state — neighbours never see the adjacency drop, so they have nothing to configure. The mechanism is invisible at the protocol level.

2. **Adjacencies during switchover:** On an NSR-enabled dual-RP router, IS-IS adjacencies never drop. The standby RP continues sending and receiving Hellos at the same rate, with the same timers, so neighbours do not detect a disruption.

3. **CSR1000v single-RP:** If `nsr` were somehow accepted on a single-RP CSR1000v, no state synchronisation would occur — there is no second RP to hold the mirrored state. An RP switchover is impossible on single-RP hardware (the router simply reloads), so NSR would never be invoked.

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>            # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore
```

---

### Ticket 1 — IS-IS Graceful Restart Not Protecting the R1↔R2 Adjacency

After a maintenance window where R2's IS-IS process was restarted, the operations team notes that R1 immediately removed R2's LSP from the LSDB and flapped all routes via R2. IS-IS GR was configured on R2 but something is missing. BGP sessions via R1 and R3 remain stable — the surface symptom is a 30-second IS-IS reconvergence spike after each R2 restart.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show isis neighbors detail` on R1 must show `Restart capable: yes` for R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis neighbors detail` on R1 — examine the R2 entry. The `Restart capable` field shows `no` or is absent.
2. Run `show run | section router isis` on R1 — confirm `nsf ietf` is present.
3. Run `show run | section router isis` on R2 — observe that `nsf ietf` is missing from R2's IS-IS process.
4. The asymmetric GR means R1 is GR-capable (can be a helper), but R2 never advertises GR capability (because `nsf ietf` is missing), so R1 does not enter helper mode when R2 restarts.

</details>

<details>
<summary>Click to view Fix</summary>

On R2, restore the missing IS-IS Graceful Restart configuration:

```bash
! On R2
router isis
 nsf ietf
```

Run `show isis neighbors detail` on R1 — the R2 entry should now show `Restart capable: yes`.

</details>

---

### Ticket 2 — BGP Session to R5 Loses Routes Immediately on Peer Restart

The external BGP peer R5 undergoes a maintenance reload. R1 withdraws the 192.0.2.0/24 prefix immediately when R5's BGP session drops, causing a forwarding interruption on R2. BFD fall-over is not active on this session (removed for testing), so the withdrawal is coming from BGP directly, not BFD.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** After R5 re-establishes BGP with R1, `show ip bgp neighbors 10.0.0.5` on R1 must show `Graceful Restart Capability: advertised and received` and the 192.0.2.0/24 route must survive a BGP reset on R5 without dropping.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp neighbors 10.0.0.5` on R1 — examine the GR capability lines. Note that GR capability is advertised by R1 but **not received** from R5.
2. Run `show run | section router bgp` on R5 via console — observe that `bgp graceful-restart` is missing from R5's BGP config.
3. Without BGP GR on R5, even though R1 is GR-capable, R5 never advertises GR capability in its OPEN message. R1 treats the session as non-GR and withdraws routes immediately when R5 disconnects.

</details>

<details>
<summary>Click to view Fix</summary>

On R5, restore the missing BGP Graceful Restart configuration:

```bash
! On R5
router bgp 65200
 bgp graceful-restart
```

After applying, run `clear ip bgp *` on R5 to re-establish sessions with GR capability advertised. Verify with `show ip bgp neighbors 10.0.0.5` on R1 that `Graceful Restart Capability: advertised and received` is now shown for both directions.

</details>

---

### Ticket 3 — R1 Not Acting as GR Helper for R4 Restart

R4 experiences a control-plane restart. R1 immediately removes R4 from the IS-IS neighbour table and withdraws R4's loopback from the RIB. R3 also drops R4. The result is a 30-second IS-IS reconvergence event affecting all destinations that transit R4. R2's loopback (10.0.0.2) transit-ing via R4 is also affected, creating a wider service impact than expected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show isis neighbors detail` on R1 must show `Restart capable: yes` for R4. After reapplying the missing GR configuration, a controlled IS-IS process restart on R4 should not trigger immediate LSP removal on R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis neighbors detail` on R1 — examine the R4 entry (Gi2). `Restart capable` shows `no` or is absent.
2. Run `show run | section router isis` on R4 — observe that `nsf ietf` is missing.
3. Run the same check on R3 — the R4 entry also shows `Restart capable: no`. R4 has no IS-IS GR configured at all, so it cannot participate in GR with any peer.
4. Since R1, R2, and R3 all have `nsf ietf` enabled, they will be helpers for each other, but none of them can help R4 — R4 never advertises GR capability.

</details>

<details>
<summary>Click to view Fix</summary>

On R4, restore the missing IS-IS Graceful Restart configuration:

```bash
! On R4
router isis
 nsf ietf
```

Run `show isis neighbors detail` on R1 — the R4 entry (Gi2) should now show `Restart capable: yes`. Repeat on R3 to confirm the same.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] IS-IS NSF (`nsf ietf`) configured on R1, R2, R3, R4
- [x] `show isis neighbors detail` shows `Restart capable: yes` for all IS-IS adjacencies
- [x] `show isis` shows `NSF: enabled (IETF)` in process summary
- [x] BGP GR (`bgp graceful-restart`) configured on R1, R2, R3, R4, R5
- [x] GR capability exchanged: `Graceful Restart Capability: advertised and received` on all BGP sessions
- [x] BGP GR live test performed: R2 ping to 192.0.2.1 survives R5 BGP reset with BFD fall-over temporarily removed
- [x] Contrast test performed: without GR, ping drops immediately on R5 BGP reset
- [x] IS-IS NSR (`nsr`) attempted on R1 — confirmed **rejected** on CSR1000v (single-RP limitation documented)
- [x] BGP NSR (`bgp nsr`) attempted on R1 — confirmed **rejected** on CSR1000v (single-RP limitation documented)
- [x] NSF vs NSR comparison completed in writing

### Troubleshooting

- [ ] Ticket 1: R1↔R2 IS-IS GR restored — `Restart capable: yes` on both sides; root cause (missing `nsf ietf` on R2) identified and corrected
- [ ] Ticket 2: R5 BGP GR restored — GR capability exchanged bidirectionally; root cause (missing `bgp graceful-restart` on R5) identified and corrected
- [ ] Ticket 3: R4 IS-IS GR restored — all four core routers now GR-capable; root cause (missing `nsf ietf` on R4) identified and corrected

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
