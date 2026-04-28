# BGP Lab 03: Inter-Domain Security and Maximum-Prefix

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

**Exam Objective:** 300-510 SPRI — 1.5.e (BGP TTL Security / GTSM), 1.5.f (BGP authentication and maximum-prefix)

Inter-domain BGP sessions — the TCP connections your router maintains with external ASes — are the highest-value targets in a service provider network. A successful attack that terminates or floods an eBGP session can black-hole customer traffic across multiple autonomous systems. This lab introduces three complementary defenses that are applied at the BGP session layer: Generalized TTL Security Mechanism (GTSM), MD5 TCP authentication, and maximum-prefix enforcement. Mastering these controls is both an exam requirement and a real-world production baseline.

### TTL Security (GTSM — RFC 5082)

GTSM exploits a fundamental property of directly connected eBGP peers: they are exactly one IP hop apart. When GTSM is configured with `hops 1`, the sender sets the IP TTL of every BGP TCP packet to 255, and the receiver accepts only packets arriving with TTL >= 254 (that is, 255 minus 1). A forged BGP packet originating from a remote attacker can travel at most 253 hops before the TTL field falls below the acceptance threshold, and the packet is silently dropped in the kernel before the BGP process even sees it.

This provides denial-of-service protection with essentially zero CPU overhead on production sessions. The mechanism is symmetric: both peers must be configured, and the hop count must match across the session.

```
IOS syntax (router bgp context):
  neighbor <ip> ttl-security hops <1-254>

Verification:
  show ip bgp neighbors <ip> | include TTL|Min TTL
```

GTSM is not a substitute for authentication — it protects against off-path spoofed packets, not on-path attackers. MD5 fills that role.

### MD5 TCP Authentication (RFC 2385)

BGP runs over TCP. Without authentication, an on-path attacker who can inject RST segments or manipulate sequence numbers can tear down any session. `neighbor X password KEY` instructs IOS to generate an HMAC-MD5 signature over each TCP segment, using the configured key. The receiving router verifies the signature; unmatched or unsigned segments are discarded.

The critical operational detail: a key mismatch causes silent segment drops, not a BGP NOTIFICATION. The session simply fails to establish (or drops) and the hold timer expires. This makes mismatched passwords one of the most common, and hardest-to-diagnose, eBGP failures in production.

```
IOS syntax (router bgp context):
  neighbor <ip> password <key-string>

Verification:
  show ip bgp neighbors <ip> | include password|MD5
```

### Maximum-Prefix Enforcement

Route leaks — when a customer accidentally originates thousands of prefixes from a broken routing policy or a misconfigured router — have historically caused major Internet outages. Maximum-prefix enforcement caps the number of prefixes a BGP router will accept from a peer, providing a circuit breaker before a route leak can fill the RIB.

Two enforcement modes matter for this lab:

| Mode | Command Suffix | Behavior |
|------|---------------|----------|
| Session teardown + timed restart | `restart <minutes>` | Session drops when limit exceeded; auto-recovers after the timer |
| Warning-only | `warning-only` | Syslog alert at threshold; session stays up |

The threshold percentage (e.g., `75`) triggers an early warning at 75% of the limit — useful for detecting a growing leak before the hard limit is hit. Without `warning-only`, exceeding the limit shuts down the session and requires either waiting for the restart timer or manually running `clear ip bgp <peer>`.

```
IOS syntax (address-family ipv4 context):
  neighbor <ip> maximum-prefix <max> [<threshold%>] [warning-only | restart <minutes>]

Verification:
  show ip bgp neighbors <ip> | include Maximum|prefix
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| GTSM configuration | Configure TTL security on eBGP sessions to block off-path spoofed TCP segments |
| MD5 BGP authentication | Apply symmetric key-string authentication to protect session integrity |
| Maximum-prefix warning | Use threshold-based syslog alerting to detect early route-leak signals |
| Maximum-prefix enforcement | Configure session teardown and timed auto-restart as a route-leak circuit breaker |
| Security fault diagnosis | Isolate and resolve TTL-mismatch, password-mismatch, and silent max-prefix outages |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at SP-Core (AS 65100). Following the successful deployment of BGP multihoming in lab-02, your security team has mandated that all inter-domain BGP sessions must be hardened before the next change window. Three controls are required: (1) GTSM on all eBGP links to prevent off-path BGP spoofing; (2) MD5 authentication on the R5↔R6 external peering with AS 65002; (3) maximum-prefix protection on both external-facing sessions to contain damage from route leaks. Customer A's primary CE (R1) already operates dual-homed via R2 and R3; you must harden both customer-facing sessions.

```
              AS 65001
        ┌─────────────────────┐
        │         R1          │
        │    Customer A CE    │
        │  Lo0: 10.0.0.1/32   │
        │  Lo1: 172.16.1.0/24 │
        └────────┬─────┬──────┘
          Gi0/0  │     │ Gi0/1
     10.1.12.1/24│     │10.1.13.1/24
    [GTSM hops 1]│     │[GTSM hops 1]
     10.1.12.2/24│     │10.1.13.3/24
          Gi0/0  │     │ Gi0/0
                 │     │
            AS 65100 (SP-Core)
   ┌─────────────┘     └──────────────┐
   │                                  │
┌──┴──────────────────┐  ┌────────────┴────────────┐
│         R2          │  │           R3             │
│     PE-East-1       │  │       PE-East-2          │
│   Lo0: 10.0.0.2/32  │  │    Lo0: 10.0.0.3/32     │
│  [max-prefix 100    │  │                          │
│   restart 5 ← R1]  │  │                          │
└──────────┬──────────┘  └───────────┬──────────────┘
      Gi0/1│  Gi0/2          Gi0/2   │Gi0/1
  10.1.24.2│  10.1.23.2   10.1.23.3  │10.1.34.3
           │    └──────────┘          │
           │                          │
      ┌────┴──────────────────────────┴────┐
      │                 R4                 │
      │            P / Route Reflector     │
      │          Lo0: 10.0.0.4/32          │
      │        cluster-id: 10.0.0.4        │
      └─────────────────┬──────────────────┘
                   Gi0/2│
               10.1.45.4│
               10.1.45.5│
                    Gi2  │
      ┌─────────────────┴──────────────────┐
      │                R5                  │
      │           PE-West [IOS-XE]         │
      │         Lo0: 10.0.0.5/32           │
      │  [GTSM hops 1, MD5: CISCO_SP,      │
      │   max-prefix 100 75 warning-only]  │
      └─────────────────┬──────────────────┘
                    Gi3 │
             10.1.56.5  │  [GTSM + MD5]
             10.1.56.6  │
                  Gi0/0 │
      ┌─────────────────┴──────────────────┐
      │               R6                   │
      │          External SP Peer          │
      │  Lo0: 10.0.0.6/32                  │
      │  Lo1: 172.16.6.0/24               │
      │  AS 65002                          │
      └────────────────────────────────────┘
```

**Key eBGP sessions and their security controls:**

| Session | Peers | GTSM | MD5 | Max-Prefix |
|---------|-------|------|-----|------------|
| R2 ↔ R1 | PE-East-1 ↔ Customer CE | hops 1 | — | 100 restart 5 on R2 |
| R3 ↔ R1 | PE-East-2 ↔ Customer CE | hops 1 | — | — |
| R5 ↔ R6 | PE-West ↔ External SP | hops 1 | CISCO_SP | 100 75 warning-only on R5 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE-East-1 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE-East-2 (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE-West (AS 65100) | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP Peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | BGP router-id |
| R1 | Loopback1 | 172.16.1.0/24 | Customer A advertised prefix |
| R2 | Loopback0 | 10.0.0.2/32 | BGP router-id, iBGP update-source |
| R3 | Loopback0 | 10.0.0.3/32 | BGP router-id, iBGP update-source |
| R4 | Loopback0 | 10.0.0.4/32 | BGP router-id, RR update-source |
| R5 | Loopback0 | 10.0.0.5/32 | BGP router-id, iBGP update-source |
| R6 | Loopback0 | 10.0.0.6/32 | BGP router-id |
| R6 | Loopback1 | 172.16.6.0/24 | External SP advertised prefix |

### Cabling Table

| Link ID | Source | Target | Subnet | Purpose |
|---------|--------|--------|--------|---------|
| L1 | R1 Gi0/0 ↔ R2 Gi0/0 | 10.1.12.0/24 | eBGP AS 65001 ↔ AS 65100 primary |
| L2 | R1 Gi0/1 ↔ R3 Gi0/0 | 10.1.13.0/24 | eBGP AS 65001 ↔ AS 65100 backup |
| L3 | R2 Gi0/1 ↔ R4 Gi0/0 | 10.1.24.0/24 | IGP + iBGP R2↔R4 |
| L4 | R3 Gi0/1 ↔ R4 Gi0/1 | 10.1.34.0/24 | IGP + iBGP R3↔R4 |
| L5 | R4 Gi0/2 ↔ R5 Gi2 | 10.1.45.0/24 | IGP + iBGP R4↔R5 |
| L6 | R2 Gi0/2 ↔ R3 Gi0/2 | 10.1.23.0/24 | OSPF IGP only (East PE resilience) |
| L7 | R5 Gi3 ↔ R6 Gi0/0 | 10.1.56.0/24 | eBGP AS 65100 ↔ AS 65002 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP network | Customer A aggregate |
| R6 | 172.16.6.0/24 | eBGP network | External SP aggregate |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R6 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames
- Interface IP addressing (all routed links and loopbacks)
- `no ip domain-lookup`
- OSPF area 0 on all SP-core internal links (R2, R3, R4, R5)
- eBGP sessions on R1↔R2, R1↔R3, and R5↔R6 (no security controls)
- iBGP sessions on AS 65100 with R4 as Route Reflector (R2, R3, R5 as clients)
- Legacy direct iBGP R2↔R5 (from lab-00 continuity)
- Prefix advertisements: R1 Lo1 (172.16.1.0/24), R6 Lo1 (172.16.6.0/24)
- LOCAL_PREF 200 on R2 (inbound from R1) and AS-path prepend on R1 (toward R3)
- MED on R1 (outbound traffic engineering from lab-02)

**IS NOT pre-loaded** (student configures this):
- GTSM (TTL security) on any eBGP session
- MD5 TCP authentication on any session
- Maximum-prefix enforcement (warning or session-teardown mode)

---

## 5. Lab Challenge: Core Implementation

### Task 1: GTSM on All eBGP Sessions

- Enable TTL security with a hop count of 1 on both of R1's eBGP sessions — the primary link to PE-East-1 and the backup link to PE-East-2.
- Enable the matching TTL security on PE-East-1 (toward R1) and PE-East-2 (toward R1).
- Enable TTL security with a hop count of 1 on the external R5↔R6 session. Configure it on both sides.
- Confirm that all three eBGP sessions re-establish after the TTL security configuration is applied.

**Verification:** `show ip bgp neighbors <ip> | include TTL|Min TTL` on each device — the output must show the TTL security configuration is active and sessions are in the Established state.

---

### Task 2: MD5 Authentication on R5↔R6

- Configure TCP MD5 session authentication on the R5↔R6 eBGP session using the key string `CISCO_SP`.
- Apply the same key string on both R5 and R6.
- Confirm that the session re-establishes.

**Verification:** `show ip bgp neighbors 10.1.56.6` on R5 — the output must confirm MD5 is in use and the session is Established.

---

### Task 3: Maximum-Prefix Warning on R5↔R6

- On R5, configure a maximum of 100 prefixes from R6, with a warning threshold of 75 percent and no session teardown.
- Confirm the configuration is active.

**Verification:** `show ip bgp neighbors 10.1.56.6 | include Maximum|prefix` on R5 — the output must reflect the configured limit and warning-only mode.

---

### Task 4: Maximum-Prefix with Timed Restart on R2↔R1

- On R2, configure a maximum of 100 prefixes from R1, with session teardown when the limit is exceeded and an automatic restart timer of 5 minutes.
- Confirm the configuration is active.
- Simulate the fault by temporarily advertising a second prefix from R1 to exceed the limit (you may do this with a network statement or by redistributing a connected route into BGP). Observe the session teardown syslog message on R2.

**Verification:** `show ip bgp neighbors 10.1.12.1 | include Maximum|prefix` — limit and restart timer must be present. During fault simulation: `show ip bgp neighbors 10.1.12.1 | include BGP state|Idle` must show the session in Idle with the restart timer counting down.

---

## 6. Verification & Analysis

### Task 1: GTSM Verification

```
R1# show ip bgp neighbors 10.1.12.2 | include TTL|Min TTL|BGP state
BGP neighbor is 10.1.12.2,  remote AS 65100, external link
BGP state = Established, up for 00:03:21                ! ← Session must be Established
 TTL security enabled (hops = 1), min TTL = 254          ! ← TTL security active; min TTL = 255-1

R1# show ip bgp neighbors 10.1.13.3 | include TTL|Min TTL|BGP state
BGP neighbor is 10.1.13.3,  remote AS 65100, external link
BGP state = Established, up for 00:02:54                ! ← Both eBGP sessions Established
 TTL security enabled (hops = 1), min TTL = 254          ! ← GTSM enforced on backup path too

R5# show ip bgp neighbors 10.1.56.6 | include TTL|Min TTL|BGP state
BGP neighbor is 10.1.56.6,  remote AS 65002, external link
BGP state = Established, up for 00:04:05                ! ← R5↔R6 session Established
 TTL security enabled (hops = 1), min TTL = 254          ! ← GTSM on external SP link
```

### Task 2: MD5 Verification

```
R5# show ip bgp neighbors 10.1.56.6 | include password|MD5|BGP state
BGP neighbor is 10.1.56.6,  remote AS 65002, external link
BGP state = Established, up for 00:04:05                ! ← Must be Established (not Active)
  Inherits session attributes:
  TCP MD5 authentication is ENABLED                     ! ← MD5 confirmed active
```

### Task 3: Maximum-Prefix Warning Verification

```
R5# show ip bgp neighbors 10.1.56.6 | include Maximum|prefix|warning
  Maximum prefixes allowed 100, Warning-only at 75%     ! ← Limit and threshold confirmed
  Prefixes received: 1                                  ! ← Well below threshold; no alert
```

### Task 4: Maximum-Prefix Restart Verification

```
R2# show ip bgp neighbors 10.1.12.1 | include Maximum|prefix|restart
  Maximum prefixes allowed 100, Restart interval 5 min  ! ← Teardown mode with 5-min restart

! --- After fault simulation (R1 advertising >100 prefixes) ---

R2# show log | include MAXPFX|Maximum
%BGP-5-ADJCHANGE: neighbor 10.1.12.1 Down BGP Notification sent
%BGP-3-MAXPFX: No. of prefix received from 10.1.12.1 (afi 0) reaches 101,
 max 100                                                ! ← Teardown triggered by prefix limit

R2# show ip bgp neighbors 10.1.12.1 | include BGP state|Idle
BGP state = Idle (PfxCt)                               ! ← Idle due to prefix count violation
```

---

## 7. Verification Cheatsheet

### GTSM (TTL Security)

```
neighbor <ip> ttl-security hops <1-254>
```

| Command | Purpose |
|---------|---------|
| `show ip bgp neighbors <ip> \| inc TTL\|Min TTL` | Confirm GTSM is active and hop count |
| `show ip bgp neighbors <ip> \| inc BGP state` | Verify session remains Established |
| `show ip bgp summary` | Confirm all expected sessions are up |

> **Exam tip:** Both peers must configure matching `ttl-security hops` values. A mismatch causes the session to fail silently — no NOTIFICATION, just a hold-timer expiry. If `hops` differ by even 1, one side's TTL check rejects all incoming packets.

### MD5 Authentication

```
neighbor <ip> password <key-string>
```

| Command | Purpose |
|---------|---------|
| `show ip bgp neighbors <ip> \| inc MD5\|password` | Confirm MD5 is enabled |
| `show ip bgp neighbors <ip> \| inc BGP state` | Verify Established state |
| `debug ip bgp <ip> events` | Observe authentication failures (use briefly, undebug all after) |

> **Exam tip:** A password mismatch causes silent TCP segment drops, not a BGP NOTIFICATION. The session goes to Active, times out at the hold timer, and retries — indefinitely. `show ip bgp neighbors` shows BGP state as Active; `debug ip bgp events` shows repeated connection attempts.

### Maximum-Prefix

```
! In address-family ipv4:
neighbor <ip> maximum-prefix <max> [<threshold%>] [warning-only | restart <minutes>]
```

| Command | Purpose |
|---------|---------|
| `show ip bgp neighbors <ip> \| inc Maximum\|prefix` | Show limit, threshold, and mode |
| `show log \| inc MAXPFX\|Maximum` | Show syslog alert when threshold is crossed |
| `clear ip bgp <ip>` | Manually reset a session stuck in Idle (PfxCt) |

> **Exam tip:** Without `warning-only`, a session that hits the maximum-prefix limit goes `Idle (PfxCt)` and does NOT recover until either the `restart` timer fires or you manually run `clear ip bgp`. With `restart 5`, the session auto-recovers after 5 minutes. The restart timer is not a penalty — it is an intentional circuit-breaker to prevent a route-leak from immediately flooding back.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp neighbors <ip> \| inc TTL` | GTSM enabled and hop count |
| `show ip bgp neighbors <ip> \| inc MD5` | MD5 authentication status |
| `show ip bgp neighbors <ip> \| inc Maximum` | Prefix limit, threshold, and mode |
| `show ip bgp neighbors <ip> \| inc BGP state` | Established vs Active/Idle |
| `show ip bgp summary` | All session states at a glance |
| `show log \| inc MAXPFX` | Maximum-prefix syslog events |

### Common BGP Session Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Session stays in Active (cycling) | TTL mismatch; MD5 password mismatch; ACL/firewall blocking TCP 179 |
| Session stuck in Idle (PfxCt) | Maximum-prefix limit exceeded; use `clear ip bgp` or wait for restart timer |
| Session flaps shortly after coming up | Hold-timer mismatch or aggressive keepalive; check `bgp timers` |
| GTSM configured but session fails | One side missing `ttl-security hops` or hop count mismatch |
| MD5 configured but session fails | Key-string mismatch or one side not configured — check both peers |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: GTSM on All eBGP Sessions

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — add ttl-security to both eBGP neighbors
router bgp 65001
 neighbor 10.1.12.2 ttl-security hops 1
 neighbor 10.1.13.3 ttl-security hops 1
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — add ttl-security toward Customer A CE
router bgp 65100
 neighbor 10.1.12.1 ttl-security hops 1
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — add ttl-security toward Customer A CE
router bgp 65100
 neighbor 10.1.13.1 ttl-security hops 1
```
</details>

<details>
<summary>Click to view R5 and R6 Configuration</summary>

```bash
! R5 — ttl-security on external SP link
router bgp 65100
 neighbor 10.1.56.6 ttl-security hops 1

! R6 — matching ttl-security
router bgp 65002
 neighbor 10.1.56.5 ttl-security hops 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R1# show ip bgp neighbors 10.1.12.2 | include TTL|BGP state
R1# show ip bgp neighbors 10.1.13.3 | include TTL|BGP state
R5# show ip bgp neighbors 10.1.56.6 | include TTL|BGP state
```
</details>

---

### Task 2: MD5 Authentication on R5↔R6

<details>
<summary>Click to view R5 and R6 Configuration</summary>

```bash
! R5 — MD5 key on eBGP session to R6
router bgp 65100
 neighbor 10.1.56.6 password CISCO_SP

! R6 — matching key (must be identical, case-sensitive)
router bgp 65002
 neighbor 10.1.56.5 password CISCO_SP
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip bgp neighbors 10.1.56.6 | include MD5|password|BGP state
```
</details>

---

### Task 3: Maximum-Prefix Warning on R5↔R6

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — warning-only; session stays up at threshold and limit
router bgp 65100
 address-family ipv4
  neighbor 10.1.56.6 maximum-prefix 100 75 warning-only
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R5# show ip bgp neighbors 10.1.56.6 | include Maximum|prefix
```
</details>

---

### Task 4: Maximum-Prefix with Timed Restart on R2↔R1

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — session teardown with 5-minute auto-restart
router bgp 65100
 address-family ipv4
  neighbor 10.1.12.1 maximum-prefix 100 restart 5
```
</details>

<details>
<summary>Click to view Fault Simulation (R1)</summary>

```bash
! R1 — temporarily advertise a large number of host routes to exceed limit
! (In the lab, inject_scenario_03.py handles this automatically)
! Manual simulation: redistribute connected into BGP to add prefixes

router bgp 65001
 address-family ipv4
  redistribute connected
```
After R2 drops the session, remove the redistribution and wait 5 minutes for auto-restart,
or run: clear ip bgp 10.1.12.1 on R2 to recover immediately.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R2# show ip bgp neighbors 10.1.12.1 | include Maximum|prefix|BGP state|Idle
R2# show log | include MAXPFX|Maximum
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only `show` commands and the lab verification steps. Avoid looking at the fault scripts before diagnosing.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip> # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore
```

---

### Ticket 1 — R3 Reports Neighbor 10.1.13.1 Is Not Establishing

You receive a call that Customer A's backup path through PE-East-2 (R3) has been down for 10 minutes. R3's eBGP session with R1 was working before this morning's maintenance window, during which only BGP security hardening was applied.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.13.1` on R3 and `show ip bgp neighbors 10.1.13.3` on R1 both show BGP state = Established.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Check the session state on both sides
R3# show ip bgp neighbors 10.1.13.1 | include BGP state|TTL|Min TTL
!   BGP state = Active
!   TTL security enabled (hops = 1), min TTL = 254

R1# show ip bgp neighbors 10.1.13.3 | include BGP state|TTL|Min TTL
!   BGP state = Active
!   (no TTL security line — GTSM is not configured on R1 for this neighbor)

! Step 2: Interpret the asymmetry
! R3 has ttl-security hops 1, so it expects incoming packets with TTL >= 254.
! R1 has no ttl-security, so it sends BGP packets with the eBGP default TTL of 1.
! When R1's SYN reaches R3, TTL=1 — well below R3's minimum of 254. R3 drops it.
! The session never progresses past Active on either side.

! Step 3: Confirm R1 is missing the ttl-security statement
R1# show running-config | section router bgp
!   neighbor 10.1.13.3 remote-as 65100
!   neighbor 10.1.13.3 ... (no ttl-security line present)

! Root cause: ttl-security hops 1 was removed from R1 toward 10.1.13.3.
! R3 is enforcing GTSM; R1 is not — the session fails silently, hold timer expires.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — restore ttl-security toward R3
router bgp 65001
 neighbor 10.1.13.3 ttl-security hops 1

! Verify recovery (allow up to 30 seconds for BGP to re-establish)
R1# show ip bgp neighbors 10.1.13.3 | include BGP state|TTL
!   BGP state = Established
!   TTL security enabled (hops = 1), min TTL = 254

R3# show ip bgp neighbors 10.1.13.1 | include BGP state|TTL
!   BGP state = Established
!   TTL security enabled (hops = 1), min TTL = 254
```
</details>

---

### Ticket 2 — R5 Cannot Establish BGP Session with R6 Despite Correct Peering Config

The NOC reports that the R5↔R6 eBGP session has been bouncing for the past 30 minutes. The session goes to Active but never reaches Established. IP connectivity between R5 and R6 is confirmed working via ping.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.56.6` on R5 shows BGP state = Established; `show ip bgp neighbors 10.1.56.5` on R6 shows Established.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm the session is stuck in Active
R5# show ip bgp neighbors 10.1.56.6 | include BGP state
BGP state = Active                                  ! ← Not Established

! Step 2: Rule out TTL — GTSM is symmetric, check if both agree
R5# show ip bgp neighbors 10.1.56.6 | include TTL
 TTL security enabled (hops = 1), min TTL = 254    ! ← R5 GTSM looks correct

R6# show ip bgp neighbors 10.1.56.5 | include TTL
 TTL security enabled (hops = 1), min TTL = 254    ! ← R6 GTSM also matches

! Step 3: Check MD5 — this is the classic silent failure mode
R5# show ip bgp neighbors 10.1.56.6 | include MD5|password
  TCP MD5 authentication is ENABLED                ! ← MD5 is on; key is hidden

! → IP reachable but TCP session never completes = MD5 password mismatch
! The fault script changes R6's password to a different value

! Confirm by checking R6
R6# show ip bgp neighbors 10.1.56.5 | include MD5|password
  TCP MD5 authentication is ENABLED                ! ← Both have MD5 enabled

! The only remaining possibility: mismatched key strings. You cannot see the
! key in show output. This is diagnosed by elimination — GTSM and connectivity
! are confirmed OK; MD5 mismatch is the only remaining cause.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R6 — correct the password to match R5
router bgp 65002
 neighbor 10.1.56.5 password CISCO_SP

! Verify — both sessions must reach Established within seconds
R5# show ip bgp neighbors 10.1.56.6 | include BGP state|MD5
R6# show ip bgp neighbors 10.1.56.5 | include BGP state|MD5
```
</details>

---

### Ticket 3 — R2 Shows Neighbor 10.1.12.1 as Idle; Customer A Traffic on Backup Path Only

Network operations is seeing all Customer A traffic flowing via R3 (backup path). R2's session with R1 appears Idle in BGP summary. No changes were made to the multihoming policy.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip bgp neighbors 10.1.12.1` on R2 shows BGP state = Established; `show ip bgp summary` on R4 shows both R2 and R3 paths to 172.16.1.0/24 in the RIB.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Determine why R2's session is Idle
R2# show ip bgp neighbors 10.1.12.1 | include BGP state|Idle|prefix
BGP state = Idle (PfxCt)                           ! ← Idle due to prefix count violation

! Step 2: Check the maximum-prefix configuration
R2# show ip bgp neighbors 10.1.12.1 | include Maximum|prefix
  Maximum prefixes allowed 100, Restart interval 5 min   ! ← Config is correct

! Step 3: Check syslog
R2# show log | include MAXPFX|Maximum
%BGP-3-MAXPFX: No. of prefix received from 10.1.12.1 reaches 101, max 100

! Diagnosis: R1 was advertising more than 100 prefixes (fault injected via
! redistribution or extra network statements). The session hit the hard limit,
! was shut down, and is now waiting for the 5-minute restart timer.

! Step 4: Confirm R1's current prefix count
R1# show ip bgp | begin Network
! → Will show the excess prefixes that triggered the limit

! Step 5: Options — wait for restart timer, or clear the fault
! Waiting for the timer verifies the auto-restart mechanism works.
! To recover now: clear ip bgp after removing the excess prefixes from R1.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — remove the excess prefixes (injected by the fault script)
! The script will have added redistribution or extra network statements.
! Remove those:
router bgp 65001
 address-family ipv4
  no redistribute connected

! Wait for R2's 5-minute restart timer, or force recovery:
R2# clear ip bgp 10.1.12.1

! Verify recovery
R2# show ip bgp neighbors 10.1.12.1 | include BGP state
R4# show ip bgp 172.16.1.0/24
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] GTSM (hops 1) configured on R1 toward both R2 and R3
- [ ] GTSM (hops 1) configured on R2 and R3 toward R1
- [ ] GTSM (hops 1) configured on R5 and R6 toward each other
- [ ] All three eBGP sessions show BGP state = Established after GTSM applied
- [ ] MD5 key `CISCO_SP` configured on both R5 and R6
- [ ] R5↔R6 session is Established with MD5 confirmed in show output
- [ ] R5: maximum-prefix 100 75 warning-only toward R6 active
- [ ] R2: maximum-prefix 100 restart 5 toward R1 active
- [ ] Maximum-prefix enforcement on R2: session teardown + syslog observed (Task 4 simulation)

### Troubleshooting

- [ ] Ticket 1: Missing ttl-security on R1 toward R3 identified and corrected
- [ ] Ticket 2: MD5 password mismatch diagnosed by elimination and corrected
- [ ] Ticket 3: Silent max-prefix session teardown root-caused and session recovered

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
