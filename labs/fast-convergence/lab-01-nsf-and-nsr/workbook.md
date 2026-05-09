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

This lab builds directly on the BFD and timer foundation from lab-00 and adds the high-availability layer that lets a restarting router's neighbors cooperate in minimising the routing disruption. You will configure and verify IS-IS Graceful Restart (NSF), BGP Graceful Restart, IS-IS NSR, and BGP NSR — and measure the difference between a GR-assisted restart and a plain restart.

---

### IS-IS Graceful Restart (NSF)

IS-IS Graceful Restart (GR), also called Nonstop Forwarding in Cisco terminology, is defined in RFC 5306. When an IS-IS router restarts its control plane while its forwarding plane continues to operate, it sends a Hello PDU with the GR restart bit set. Neighboring routers that receive this signal enter **GR helper mode**: they keep the restarting router's LSP alive in the LSDB and suppress route withdrawals for the duration of the stale timer (typically 60–120 seconds).

The result: the rest of the network never sees a topology change, so no SPF runs, no route flaps, and no packet drops — as long as the restarting router's hardware plane keeps forwarding.

```
! Enable IS-IS Graceful Restart (RFC 5306 IETF variant) on R1-R4
router isis
 nsf ietf
```

```
! Verify GR capability is advertised to neighbors
show isis neighbors detail
! Look for: Restart capable: yes
```

Both sides of each adjacency must have `nsf ietf` configured for full GR protection. A one-sided configuration means the non-GR neighbor will still withdraw routes when its peer restarts.

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

**Key difference from IS-IS NSF:** BGP GR is stateless on the forwarding side — BGP does not manage hardware FIB entries directly. The stale timer just prevents immediate withdrawal so the FIB (populated by IS-IS or static routes) remains valid while the BGP control plane reconnects. For eBGP to R5, this matters: if R5's BGP restarts and R1 is a GR helper, R1 keeps 192.0.2.0/24 in its RIB and continues forwarding to R5 during the GR window.

### Nonstop Routing (NSR)

NSR is a fundamentally different HA approach: instead of coordinating with neighbors, the restarting router itself maintains all protocol state on a standby Route Processor (RP). During an RP switchover, the standby takes over seamlessly — protocol adjacencies never drop because the standby RP was already holding them.

```
! Enable IS-IS NSR on R1 (requires dual-RP hardware for full effect)
router isis
 nsr
!
! Enable BGP NSR on R1
router bgp 65100
 bgp nsr
```

**NSR behavioral gap on IOSv:** IOSv has a single virtual RP. The `nsr` and `bgp nsr` commands are accepted for configuration, but there is no standby RP to hold the protocol state. On a production dual-RP platform (ASR 9000, CRS, NCS), NSR allows a switchover that is completely invisible to BGP and IS-IS neighbors — neither peer sees the session flap. The exam tests your ability to configure NSR and understand this distinction.

| Feature | Cooperative | Requires neighbor config | Requires hardware HA |
|---------|-------------|--------------------------|----------------------|
| NSF (IS-IS GR) | Yes — neighbor must be a GR helper | Yes | No |
| BGP GR | Yes — peer must advertise GR capability | Yes | No |
| NSR | No — fully local | No | Yes (standby RP) |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IS-IS Graceful Restart | Configure `nsf ietf`; verify restart capability advertisement |
| BGP Graceful Restart | Configure `bgp graceful-restart`; verify GR capability exchange |
| GR helper behavior | Observe stale-route retention on R1/R3 during R5 BGP restart |
| NSF vs no-GR comparison | Measure BGP route persistence with and without GR enabled |
| IS-IS NSR configuration | Configure `nsr`; document single-RP behavioral gap |
| BGP NSR configuration | Configure `bgp nsr`; interpret IOSv limitation |
| NSF vs NSR analysis | Compare cooperative vs local HA approaches in writing |
| Asymmetric GR troubleshooting | Diagnose one-sided GR config causing disruption on reload |

---

## 2. Topology & Scenario

**Scenario:** Your SP core has BFD and timer tuning in place from lab-00. The operations team now wants to add HA-level protection: control-plane restarts on any router should not cause measurable forwarding disruption. You need to configure IS-IS Graceful Restart across all core routers, BGP Graceful Restart across all BGP speakers, and document the NSR design intent on R1 as a reference for when the team migrates to dual-RP hardware.

```
              AS 65100 (SP core — IS-IS L2 + iBGP full mesh)

         ┌──────────────────────┐              ┌──────────────────────┐
         │         R1           │── L1 ─────── │         R2           │
         │  SP Edge AS 65100    │  Gi0/0 Gi0/0 │  SP Core AS 65100    │
         │  Lo0: 10.0.0.1/32    │  10.1.12.0   │  Lo0: 10.0.0.2/32    │
         └──┬──────┬──────┬─────┘              └────────────┬─────────┘
        L4  │  L5  │  L6  │ Gi0/3                       L2  │ Gi0/1
      Gi0/1 │ Gi0/2│      │ 10.1.15.0                       │ 10.1.23.0
            │      │      │                                  │
   ┌────────┴──┐   │      │                      ┌───────────┴────────────┐
   │    R4     │   └──────┼──────────────────────►         R3             │
   │  SP Core  │          │            Gi0/2 L5  │  SP Edge AS 65100      │
   │ 10.0.0.4  │          │     Gi0/1 10.1.34.0  │  Lo0: 10.0.0.3/32     │
   │  /32      │◄── L3 ──►│              Gi0/0   │                        │
   └───────────┘  10.1.34 │              L3      └──┬───────────────────┬─┘
                          │                     L7  │ Gi0/3             │ Gi0/2
                          │               10.1.35.0 │                   │
                          │                         │                   │
                          │                ┌────────┴──────────────────┘
                          │                │
                          │       ┌────────┴──────────────────┐
                          └───────►         R5                │
                            L6 Gi0/0│   CE AS 65200           │
                         10.1.15.0  │  Lo0: 10.0.0.5/32      │
                                    │  Lo1: 192.0.2.1/24      │
                                    └────────────────────────-┘
```

**Link reference:**

| Link | Source | Target | Subnet | Purpose |
|------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/24 | SP core — IS-IS L2, iBGP transport |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/24 | SP core — IS-IS L2, iBGP transport |
| L3 | R3 Gi0/1 | R4 Gi0/0 | 10.1.34.0/24 | SP core — IS-IS L2, iBGP transport |
| L4 | R1 Gi0/1 | R4 Gi0/1 | 10.1.14.0/24 | Ring closer — IS-IS L2, LFA alternate |
| L5 | R1 Gi0/2 | R3 Gi0/2 | 10.1.13.0/24 | Diagonal — IS-IS L2, short path R1↔R3 |
| L6 | R1 Gi0/3 | R5 Gi0/0 | 10.1.15.0/24 | eBGP R1 (AS 65100) ↔ R5 (AS 65200) |
| L7 | R3 Gi0/3 | R5 Gi0/1 | 10.1.35.0/24 | eBGP R3 (AS 65100) ↔ R5 (AS 65200) |

**Key relationships:**
- IS-IS NSF adjacency pairs: R1↔R2 (L1), R2↔R3 (L2), R3↔R4 (L3), R1↔R4 (L4), R1↔R3 (L5). Every pair must have `nsf ietf` on both sides.
- BGP GR must be configured on all five BGP speakers — including R5 (the eBGP peer). An eBGP session where only one side advertises GR provides no protection.
- NSR is configured only on R1 for exam reference — the behavioral gap (no standby RP on IOSv) is documented as part of the lab.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image | RAM |
|--------|------|----------|-------|-----|
| R1 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R2 | SP Core — iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R3 | SP Edge — eBGP to AS 65200, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R4 | SP Core — redundant path, iBGP in AS 65100 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |
| R5 | External CE — dual-homed eBGP in AS 65200 | IOSv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB |

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
| L1 | R1 | R2 | 10.1.12.0/24 | GigabitEthernet0/0 | GigabitEthernet0/0 |
| L2 | R2 | R3 | 10.1.23.0/24 | GigabitEthernet0/1 | GigabitEthernet0/0 |
| L3 | R3 | R4 | 10.1.34.0/24 | GigabitEthernet0/1 | GigabitEthernet0/0 |
| L4 | R1 | R4 | 10.1.14.0/24 | GigabitEthernet0/1 | GigabitEthernet0/1 |
| L5 | R1 | R3 | 10.1.13.0/24 | GigabitEthernet0/2 | GigabitEthernet0/2 |
| L6 | R1 | R5 | 10.1.15.0/24 | GigabitEthernet0/3 | GigabitEthernet0/0 |
| L7 | R3 | R5 | 10.1.35.0/24 | GigabitEthernet0/3 | GigabitEthernet0/1 |

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
- IS-IS Graceful Restart on R1–R4
- BGP Graceful Restart on R1–R5
- IS-IS Nonstop Routing on R1
- BGP Nonstop Routing on R1

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IS-IS Graceful Restart on R1–R4

- On each of R1, R2, R3, and R4, enable IS-IS Graceful Restart using the IETF standard variant under the IS-IS process.
- Verify that the restart capability is now being advertised to all IS-IS neighbors.

**Verification:** `show isis neighbors detail` on R1 must show `Restart capable: yes` for all three neighbors (R2, R3, R4). The `Suppressing adjacency` field must show `no` (normal state, not in a restart).

---

### Task 2: Enable BGP Graceful Restart on All BGP Speakers

- On each of R1, R2, R3, R4, and R5, enable BGP Graceful Restart under the BGP process.
- Verify that the GR capability has been negotiated with all peers. You may need to reset BGP sessions for the capability to appear.

> After enabling `bgp graceful-restart`, do a soft reset of each BGP session — GR capability is exchanged during the OPEN message, so existing sessions must reconvene. Use the appropriate soft-inbound reset command rather than a hard clear.

**Verification:** `show ip bgp neighbors 10.0.0.5` on R1 must show `Graceful Restart Capability: advertised and received` and `Graceful restart: enabled`. Repeat the check on R5 for neighbors 10.0.0.1 and 10.0.0.3.

---

### Task 3: Test IS-IS NSF and BGP GR in Practice

This task has two parts: an IS-IS NSF observation and a BGP GR live test.

**Part A — IS-IS NSF capability advertisement:**
- Run `show isis neighbors detail` on R1 and confirm that all three neighbors (R2, R3, R4) advertise restart capability.
- Run `show isis database` on R1 — confirm all five IS-IS LSPs are present with non-zero sequence numbers.
- Simulate a graceful IS-IS restart on R2 by issuing the IS-IS process reset command on R2. Immediately switch to R1 and run `show isis neighbors` repeatedly. Observe that R2 briefly appears in a restarting/recovering state rather than disappearing immediately.

**Part B — BGP GR live test:**
- From R2, start a sustained extended ping to 192.0.2.1 (R5's Loopback1) sourced from R2's Loopback0. R2 reaches this prefix via iBGP from R1 or R3.
- On R5, issue a hard BGP clear for all neighbors. This resets the eBGP sessions R5↔R1 and R5↔R3.
- Observe that R2's ping experiences minimal or no packet loss. With BGP GR enabled on R1, R1 retains the 192.0.2.0/24 route as stale during the GR window (~120 s default), so R2's iBGP path via R1 stays valid.
- Run `show ip bgp 192.0.2.0/24` on R2 during the GR window and confirm the route is still present with a stale marker.

**Verification:** `show ip bgp neighbors 10.0.0.5` on R1 during the GR window must show `BGP state = Active (GR)` or `Idle (GR)` — indicating R1 is in GR helper mode waiting for R5 to reconnect. After R5 reconnects, confirm state returns to `Established`.

---

### Task 4: Contrast — Disable BGP GR and Repeat

- On R1 and R3, disable BGP Graceful Restart.
- Repeat Part B of Task 3: ping 192.0.2.1 from R2, then hard-clear BGP on R5.
- Observe that R2's ping drops immediately when R5's BGP sessions reset — because R1 now withdraws 192.0.2.0/24 as soon as R5's session drops, removing it from R2's iBGP table.
- After observing the difference, re-enable BGP Graceful Restart on R1 and R3. Also re-enable on R5 to restore the full GR-capable state.

**Verification:** `show ip bgp 192.0.2.0/24` on R2 immediately after clearing BGP on R5 (without GR) must show the route absent — unlike the GR case where it remained as stale. Confirm BGP GR is re-enabled on R1, R3, and R5 before proceeding.

---

### Task 5: Configure IS-IS NSR on R1

- On R1, enable IS-IS Nonstop Routing under the IS-IS process.
- Verify the configuration is accepted by the router.

> The NSR configuration command lives directly under the IS-IS router process. On a platform with a standby RP, NSR would also require `nsr` to be enabled globally, but on IOSv the `router isis` sub-command is all that is accepted.

**Verification:** `show running-config | section router isis` on R1 must show the `nsr` command present. `show isis` or `show isis nsr` (if supported) should confirm NSR configuration. Note that no functional state change will be observable on IOSv — document this as the IOSv single-RP behavioral gap.

---

### Task 6: Configure BGP NSR on R1

- On R1, enable BGP Nonstop Routing under the BGP process.
- Verify the configuration is accepted.

**Verification:** `show running-config | section router bgp` on R1 must show `bgp nsr` present. Document the expected behavior on a dual-RP platform and the IOSv limitation in the table below.

| Feature | Configuration command | Functional on IOSv? | Requires |
|---------|-----------------------|--------------------|---------| 
| IS-IS GR (NSF) | `nsf ietf` | Yes | Neighbor GR-helper enabled |
| BGP GR | `bgp graceful-restart` | Yes | Peer GR capability |
| IS-IS NSR | `nsr` | Config only | Standby RP |
| BGP NSR | `bgp nsr` | Config only | Standby RP |

---

### Task 7: NSF vs NSR Comparison

In the space below (or in your lab notes), write a short comparison of NSF and NSR covering:
- Which protocol peers are aware of the restart event in each case
- What hardware is required for each mechanism
- What happens if the stale timer expires before the restarting router recovers (NSF)
- Whether either mechanism protects against a link failure (vs. a control-plane restart)

> There is no configuration output to verify for this task — it is an analytical exercise that reinforces the exam-level distinctions between the two approaches.

**Verification:** You can self-check using `show isis neighbors detail` to confirm GR restart capability advertisement and `show ip bgp neighbors` for BGP GR. Confirm both `nsf ietf` and `nsr` are present under `router isis` on R1, and both `bgp graceful-restart` and `bgp nsr` under `router bgp 65100` on R1.

---

### Task 8: Troubleshoot Asymmetric GR Configuration (Guided)

> This task simulates a fault planted by the operations team. Use the inject script in Section 9 to introduce the fault, then diagnose and fix it.

- After injecting Ticket 1's fault, observe that reloading R2 causes R1 to immediately withdraw R2's routes (IS-IS LSP removed from LSDB on R1) rather than entering GR helper mode.
- Examine the IS-IS GR configuration on both R1 and R2 using `show running-config` and `show isis neighbors detail`.
- Identify which router is missing its IS-IS Graceful Restart configuration, and restore the symmetric setup so both sides have the IETF GR variant enabled.

**Verification:** After the fix, `show isis neighbors detail` on R1 must show `Restart capable: yes` for R2. Trigger another IS-IS process reset on R2 and confirm R1 enters GR helper mode (R2 remains in neighbor table in a GR/recovering state rather than disappearing immediately).

---

## 6. Verification & Analysis

### Task 1 — IS-IS GR Capability Advertisement

```
R1# show isis neighbors detail
System Id      Interface   SNPA               State  Holdtime  Type Protocol
R2             Gi0/0       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R2 Up
  Area Address(es): 49.0001
  SNPA: xxxx.xxxx.xxxx
  State Changed: never
  Last LSP ID: R2.00-00
  BFD IPv4 Session State: Up           ! ← BFD still active from lab-00
  Restart capable: yes                 ! ← IS-IS GR advertised by R2
  Suppressing adjacency: no            ! ← not in a restart event
R4             Gi0/1       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R4 Up
  Restart capable: yes
  Suppressing adjacency: no
R3             Gi0/2       xxxx.xxxx.xxxx     Up     2         L2   M-ISIS  ! ← R3 Up
  Restart capable: yes
  Suppressing adjacency: no
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
      IPv4 Unicast (was not preserved
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

### Task 5 and 6 — NSR Configuration

```
R1# show running-config | section router isis
router isis
 net 49.0001.0000.0000.0001.00
 is-type level-2-only
 metric-style wide
 passive-interface Loopback0
 spf-interval 5 50 200
 prc-interval 5 50 200
 nsf ietf                                                 ! ← IS-IS GR (lab-01 Task 1)
 nsr                                                      ! ← IS-IS NSR (lab-01 Task 5)

R1# show running-config | section router bgp
router bgp 65100
 bgp router-id 10.0.0.1
 bgp log-neighbor-changes
 bgp graceful-restart                                     ! ← BGP GR (lab-01 Task 2)
 bgp nsr                                                  ! ← BGP NSR (lab-01 Task 6)
 neighbor 10.0.0.2 remote-as 65100
 ...
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
| `show isis neighbors detail` | Check `Restart capable: yes` per neighbor |
| `show isis` | Confirm NSF enabled in process summary |
| `debug isis adj-packets` | Watch Hello PDUs with restart bit during GR event |

> **Exam tip:** IS-IS `nsf ietf` must be configured on BOTH sides of each adjacency. A router that is not GR-capable will tear down the adjacency normally on its peer's restart — it does not know to stay as a helper.

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

### IS-IS NSR

```
router isis
 nsr
```

| Command | Purpose |
|---------|---------|
| `show running-config | section router isis` | Confirm `nsr` is present |
| `show isis nsr` | NSR state (not all IOS versions support this show) |

> **Exam tip:** NSR is local — it requires no configuration on any neighbor. The trade-off: NSR requires standby RP hardware; NSF works with any adjacent GR-capable router.

### BGP NSR

```
router bgp <ASN>
 bgp nsr
```

| Command | Purpose |
|---------|---------|
| `show running-config | section router bgp` | Confirm `bgp nsr` is present |
| `show ip bgp summary` | Verify sessions remain up (functional only with standby RP) |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show isis neighbors detail` | `Restart capable: yes` for all IS-IS adjacencies |
| `show isis` | `NSF: enabled (IETF)` in process summary |
| `show ip bgp neighbors X | include Graceful` | `Graceful Restart Capability: advertised and received` |
| `show ip bgp X.X.X.X/nn` | `(stale)` marker present during GR window |
| `show run | section router isis` | Both `nsf ietf` and `nsr` present on R1 |
| `show run | section router bgp` | Both `bgp graceful-restart` and `bgp nsr` present on R1 |

### Common NSF/NSR Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| IS-IS LSP removed immediately on neighbor restart | `nsf ietf` missing on one or both sides of adjacency |
| BGP route withdrawn immediately on peer session reset | `bgp graceful-restart` missing on one or both sides |
| `bgp graceful-restart` shows `advertised` but not `received` | Peer has not been reset since GR was enabled — hard-clear required |
| `nsr` accepted but no functional difference | Expected on IOSv — single RP, no standby to hold state |
| `bgp nsr` accepted but no functional difference | Same IOSv single-RP limitation |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: IS-IS Graceful Restart on R1–R4

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
show isis
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

### Tasks 5 and 6: IS-IS NSR and BGP NSR on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router isis
 nsr
!
router bgp 65100
 bgp nsr
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config | section router isis
show running-config | section router bgp
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                       # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>         # restore
```

---

### Ticket 1 — R2 Routes Disappear Immediately When R2 IS-IS Restarts

A colleague reports that during a planned IS-IS process restart on R2, the operations team observed that R2's loopback (10.0.0.2) vanished from R1's IS-IS routing table instantly — despite claiming that Graceful Restart was "enabled on R2." The expected behavior was for the route to remain during R2's stale timer.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show isis neighbors detail` on R1 shows `Restart capable: yes` for R2. After an IS-IS process reset on R2, R1 enters GR helper mode and R2's LSP remains in R1's LSDB for the stale timer duration.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis neighbors detail` on R1 — check the entry for R2. Look at the `Restart capable` field. It will show `no`, meaning R1 is not receiving GR capability from R2 OR R1 is not configured as a GR helper.
2. Run `show running-config | section router isis` on R1 — observe that `nsf ietf` is absent from R1's IS-IS process. R1 is not configured to be a GR helper.
3. Run the same command on R2 — R2 has `nsf ietf` present. R2 is advertising GR capability, but R1 does not have it, so R1 ignores the GR signal.
4. Confirm the failure mode: trigger an IS-IS process restart on R2. Watch `show isis neighbors` on R1 — R2 disappears immediately rather than staying in a GR helper state, because R1 treats R2's restart as a normal failure.
5. Root cause: `nsf ietf` was removed from R1's IS-IS process. GR requires both sides configured — R2 restarts gracefully, but R1 never received the GR helper configuration, so it withdraws R2's routes immediately.

</details>

<details>
<summary>Click to view Fix</summary>

On R1, restore IS-IS Graceful Restart:

```bash
! On R1
router isis
 nsf ietf
```

After applying, run `show isis neighbors detail` on R1 and confirm `Restart capable: yes` appears for R2. Trigger another IS-IS process restart on R2 and observe that R2 remains in R1's neighbor table in a recovering state for the duration of the stale timer.

</details>

---

### Ticket 2 — BGP Session to R5 Reconverges Slowly After R5 BGP Restart

The monitoring system shows that after R5 performed a BGP process restart, R2's route to 192.0.2.0/24 disappeared for approximately 3 minutes before returning — far longer than the 15-second BGP hold timer configured in lab-00. The operations team suspects the GR stale timer is set too high.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** After R5 BGP restart, R2's route to 192.0.2.0/24 disappears immediately (no GR stale retention) — correctly indicating that the BGP GR mechanism is now broken. The fix restores `bgp graceful-restart` so the stale window applies again, and route reconvergence completes within the stale timer period.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip bgp neighbors 10.0.0.5` on R1 — look at the `Graceful Restart Capability` line. It shows `advertised` but NOT `received` — R5 is not advertising GR capability back to R1.
2. Run `show running-config | section router bgp` on R5 — confirm `bgp graceful-restart` is absent from R5's BGP process. R5 lost its GR configuration.
3. Run the same check on R1 — R1 has `bgp graceful-restart` present and is a GR-capable speaker, but because R5 does NOT advertise GR capability, R1 will NOT enter GR helper mode when R5's session resets.
4. Root cause: `bgp graceful-restart` was removed from R5. BGP GR is cooperative — both peers must advertise the capability. R1 advertises GR but R5 does not, so when R5 resets, R1 processes the session drop as a normal failure and withdraws the stale routes.

</details>

<details>
<summary>Click to view Fix</summary>

On R5, restore BGP Graceful Restart:

```bash
! On R5
router bgp 65200
 bgp graceful-restart
```

After applying, hard-reset the BGP sessions on R5 (`clear ip bgp *`) to re-exchange the GR capability in OPEN. Verify with `show ip bgp neighbors 10.0.0.1` on R5 showing `Graceful Restart Capability: advertised and received`. Now repeat the BGP restart test — R1 should enter GR helper mode and retain 192.0.2.0/24 as stale for R2.

</details>

---

### Ticket 3 — IS-IS Convergence on R4's Links Is Unaffected by GR Configuration

A network audit shows that when R4 restarts its IS-IS process, its neighbors (R1 and R3) immediately remove R4's LSP from the LSDB — despite IS-IS NSF being deployed across the rest of the core. The audit notes that R4 is "missing from the GR deployment list."

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show isis neighbors detail` on R1 shows `Restart capable: yes` for R4. After an IS-IS process reset on R4, R1 and R3 enter GR helper mode and R4's LSP remains in the LSDB for the stale timer duration.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show isis neighbors detail` on R1 — compare the `Restart capable` field for R2, R3, and R4. R2 and R3 show `yes`; R4 shows `no`.
2. Run `show running-config | section router isis` on R4 — confirm `nsf ietf` is absent.
3. Run the same on R1 — R1 has `nsf ietf`. R1 is a valid GR helper for any neighbor that advertises GR capability. But R4 is not advertising it.
4. Root cause: `nsf ietf` was removed from R4. IS-IS GR is advertised per-router in Hello PDUs — any router missing `nsf ietf` will not signal GR capability to its neighbors, so those neighbors will not act as GR helpers when R4 restarts.

</details>

<details>
<summary>Click to view Fix</summary>

On R4, restore IS-IS Graceful Restart:

```bash
! On R4
router isis
 nsf ietf
```

After applying, run `show isis neighbors detail` on R1 and confirm `Restart capable: yes` now appears for R4. Trigger an IS-IS process restart on R4 and confirm R4's LSP remains in R1's LSDB during the stale timer.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IS-IS GR (NSF) enabled on R1–R4: `show isis neighbors detail` shows `Restart capable: yes` for all adjacencies
- [ ] BGP GR enabled on R1–R5: `show ip bgp neighbors` shows `Graceful Restart Capability: advertised and received` for all sessions
- [ ] IS-IS NSR configured on R1: `nsr` present under `router isis`
- [ ] BGP NSR configured on R1: `bgp nsr` present under `router bgp 65100`
- [ ] BGP GR live test (Task 3): R2's ping to 192.0.2.1 survives R5 BGP clear with GR active
- [ ] BGP GR contrast (Task 4): Route disappears immediately after R5 BGP clear without GR; GR re-enabled after test
- [ ] NSF vs NSR comparison (Task 7): Written summary covering cooperative vs local, hardware requirements, stale timer behavior

### Troubleshooting

- [ ] Ticket 1: R1 missing `nsf ietf` identified and restored; R2 GR helper behavior verified after fix
- [ ] Ticket 2: R5 missing `bgp graceful-restart` identified and restored; GR capability re-exchanged
- [ ] Ticket 3: R4 missing `nsf ietf` identified and restored; GR helper behavior on R4 restart verified

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
