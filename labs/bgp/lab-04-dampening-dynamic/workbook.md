# BGP Lab 04: Route Dampening and Dynamic Neighbors

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

**Exam Objective:** 300-510 Blueprint 1.5.g (Route dampening) and 1.5.h (Dynamic neighbors)

BGP route dampening and dynamic neighbor provisioning address two operational problems
service providers face at scale. Dampening protects the network from the instability
caused by flapping prefixes; dynamic neighbors remove the operational burden of
pre-configuring every customer session manually. Together they reduce both control-plane
instability and provisioning overhead in large eBGP environments.

### BGP Route Dampening

BGP route dampening suppresses unstable prefixes using a penalty-and-decay model. Each
time a prefix is withdrawn (flap), its penalty increases by 1000 (default). The penalty
decays exponentially with a configurable half-life. When the penalty crosses the
suppress-limit the prefix is hidden from the BGP table; when it decays below the
reuse-limit the prefix is reinstated.

```
Flap penalty accumulation and decay:

  Penalty
  2000 ─ suppress-limit ──────────────────────
          prefix suppressed (shown as 'd')
  1000 ─ (one flap at default) ───────────────
         ← exponential decay →
   750 ─ reuse-limit ────────────────────────
          prefix reinstated

Parameters: half-life  reuse  suppress  max-suppress-time
Defaults:      15 min   750    2000       60 min
Lab config:    15 min   750    2000       60 min  (same as default — explicitly set)
```

Dampening applies only to eBGP-learned prefixes by default. iBGP routes are excluded
because route-reflection already propagates instability control within the AS.

Key IOS commands:

| Command | Effect |
|---------|--------|
| `bgp dampening` | Enable dampening with defaults (15/750/2000/60) |
| `bgp dampening 15 750 2000 60` | Explicit parameters: half-life reuse suppress max-time |
| `bgp dampening route-map RM` | Apply dampening selectively using a route-map |
| `clear ip bgp dampening` | Clear all dampening history |
| `clear ip bgp dampening <prefix>` | Clear dampening for a specific prefix |
| `show ip bgp dampening parameters` | Show current dampening parameters |
| `show ip bgp dampening flap-statistics` | Show penalty and flap counts per prefix |
| `show ip bgp dampening dampened-paths` | Show currently suppressed prefixes |

> **Exam tip:** The 'd' flag in `show ip bgp` means the prefix is dampened/suppressed.
> `dh` (damped, history only) means the prefix has been withdrawn and only history remains.
> Even after a peer re-advertises the prefix, it stays suppressed until the penalty decays
> below the reuse-limit or you manually `clear ip bgp dampening`.

### Dynamic BGP Neighbors

Dynamic BGP neighbors allow a router to accept incoming BGP sessions from any address
within a configured IP prefix range, without requiring a static `neighbor` statement for
each peer. The accepting router applies a peer-group template to all sessions from the range.

This is particularly useful for PE routers serving a large number of customers — instead
of adding a new neighbor statement each time a customer is provisioned, the operator
pre-configures a range with a peer-group and customers self-connect.

```
Static neighbor model:               Dynamic neighbor model:
  neighbor 10.99.0.1 remote-as X      bgp listen limit 10
  neighbor 10.99.0.2 remote-as X      bgp listen range 10.99.0.0/24 peer-group DYN_CUST
  neighbor 10.99.0.3 remote-as X      neighbor DYN_CUST remote-as X
  (one statement per customer)        (one range, unlimited customers)
```

IOS requires the `bgp listen range` command in classic IOS 15.x and IOS-XE. The
peer-group must have `remote-as` configured (for a single-AS range) or use `no-ebgp`
mode for multi-AS. `bgp listen limit` caps the maximum number of concurrent dynamic sessions.

Key IOS commands:

| Command | Effect |
|---------|--------|
| `bgp listen limit <N>` | Set maximum concurrent dynamic sessions (default 100) |
| `bgp listen range <prefix> peer-group <name>` | Accept sessions from range, apply peer-group |
| `neighbor <pg> peer-group` | Define a peer-group |
| `neighbor <pg> remote-as <ASN>` | Set the expected remote AS for the peer-group |
| `show ip bgp listen range` | Display configured listen ranges |
| `show ip bgp peer-group <name>` | Display peer-group members and state |

> **Exam tip:** Dynamic neighbors are passive — the PE does NOT initiate the session.
> The customer router must initiate. If the listen range is configured but the session
> stays in Idle/Active, verify that the customer router is sending a OPEN to the PE, not
> waiting for one.

### Route Dampening Interaction with Multihomed Prefixes

When Customer A is dual-homed (R1→R2 primary, R1→R3 backup), dampening on R5 applies
to external prefixes from R6/AS 65002, not to R1's customer prefix received via iBGP.
Dampening only fires on eBGP-learned routes. This is a key distinction: SP operators
must apply dampening on eBGP-facing interfaces (toward external peers), not on iBGP.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| BGP route dampening configuration | Enable and tune dampening parameters on an eBGP-facing PE |
| Dampening verification and clearing | Observe flap penalties, identify suppressed prefixes, restore with `clear` |
| Dynamic BGP neighbor provisioning | Configure listen range and peer-group template on a PE |
| Dynamic session verification | Confirm session establishment without static neighbor config |
| Dampening troubleshooting | Diagnose a prefix that remains suppressed after stability is restored |
| Dynamic neighbor troubleshooting | Diagnose sessions that stay Active due to missing listen range or peer-group activation |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at SP-Core (AS 65100). Customer A (AS 65001,
router R1) is dual-homed to PE East-1 (R2) and PE East-2 (R3). External SP peer AS 65002
(R6) peers with PE West (R5, CSR1000v) and advertises the 172.16.6.0/24 prefix.

In this lab you will enable BGP route dampening on R5 to protect the SP core from
unstable routes received from AS 65002. You will simulate prefix flapping to observe
penalty accumulation, then tune the dampening parameters and reset history.

You will also enable dynamic BGP neighbor provisioning on R2 to support zero-touch
customer onboarding. A new lab link (L8) between R1 and R2 represents a new customer
port in the 10.99.0.0/24 address block. R2 will accept the session automatically via
the listen range and apply the DYN_CUST peer-group template.

```
  AS 65001                   AS 65100 (SP core, OSPF area 0)            AS 65002
                        ┌─────────────────────────────────────────┐
  ┌─────────────────┐   │  ┌──────────────────┐                  │
  │      R1         │   │  │       R4         │  ┌─────────────┐ │   ┌─────────────┐
  │  Customer A CE  ├─L1┤  │  P / RR          │  │     R5      │ │   │     R6      │
  │  AS 65001       │   │  │  AS 65100        ├──┤  PE West    ├─L7──┤  Ext Peer   │
  │ Lo0: 10.0.0.1   │   │  │  Lo0: 10.0.0.4  │  │  CSR1000v   │ │   │  AS 65002   │
  │ Lo1: 172.16.1.1 │   │  └──────┬───────────┘  │ Lo0:10.0.0.5│ │   │Lo0:10.0.0.6 │
  └──┬──────────────┘   │         │               │ dampening   │ │   │Lo1:172.16.6.1│
     │ Gi0/0            │  ┌──────┴────┐  ┌───────┤ (new lab-04)│ │   └─────────────┘
     │ 10.1.12.1        │  │    R2     │  │       └─────────────┘ │
     │              L1  │  │ PE East-1 │  │ L5: 10.1.45.0/24      │
     │ 10.1.12.2 Gi0/0  │  │ AS 65100  │  │                       │
     │            ┌─────┤  │Lo0:10.0.0.2  │                       │
     │            │ R2  │  │dynamic    │  │                       │
     │            │     │  │neighbors  │  │                       │
     │            └──┬──┘  └──┬────────┘  │                       │
     │            Gi0/3    Gi0/2           │                       │
     │         10.99.0.2  10.1.23.2        │                       │
     │ Gi0/2       │                       │                       │
  10.99.0.1  ──L8──┘ ← Dynamic range       │                       │
  (new lab-04)      10.99.0.0/30            │                       │
     │                                     │                       │
     │ Gi0/1                               │  ┌────────────┐       │
     │ 10.1.13.1                     L2    │  │    R3      │       │
     └──────────────────────────────────────  │ PE East-2  │       │
                                L2:10.1.13.0  │ AS 65100   │       │
                                              │Lo0:10.0.0.3│       │
                                              └────────────┘       │
                                        ┌─────────────────────────┘
```

**Key topology facts for lab-04:**
- L8 is a NEW link added in lab-04: R1 Gi0/2 (10.99.0.1/30) ↔ R2 Gi0/3 (10.99.0.2/30)
- R2 listens on 10.99.0.0/24 for dynamic customer connections
- R5 dampening applies to routes received from R6 (AS 65002) via eBGP
- All other links and sessions carry forward from lab-03

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Customer A CE (AS 65001) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | PE East-1 (AS 65100) — dynamic neighbors | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | PE East-2 (AS 65100) — eBGP backup | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | P router / Route Reflector (AS 65100) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | PE West (AS 65100) — dampening host | CSR1000v | csr1000v-universalk9.17.03.05 |
| R6 | External SP peer (AS 65002) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router-ID, BGP peering |
| R1 | Loopback1 | 172.16.1.1/24 | Customer A prefix advertised into BGP |
| R2 | Loopback0 | 10.0.0.2/32 | Router-ID, iBGP peering source |
| R3 | Loopback0 | 10.0.0.3/32 | Router-ID, iBGP peering source |
| R4 | Loopback0 | 10.0.0.4/32 | Router-ID, iBGP peering source, RR cluster-id |
| R5 | Loopback0 | 10.0.0.5/32 | Router-ID, iBGP peering source |
| R6 | Loopback0 | 10.0.0.6/32 | Router-ID |
| R6 | Loopback1 | 172.16.6.1/24 | External peer prefix — dampening target |

### Cabling Table

| Link ID | Source | Interface | IP | Destination | Interface | IP | Subnet |
|---------|--------|-----------|-----|-------------|-----------|-----|--------|
| L1 | R1 | Gi0/0 | 10.1.12.1/24 | R2 | Gi0/0 | 10.1.12.2/24 | 10.1.12.0/24 |
| L2 | R1 | Gi0/1 | 10.1.13.1/24 | R3 | Gi0/0 | 10.1.13.3/24 | 10.1.13.0/24 |
| L3 | R2 | Gi0/1 | 10.1.24.2/24 | R4 | Gi0/0 | 10.1.24.4/24 | 10.1.24.0/24 |
| L4 | R3 | Gi0/1 | 10.1.34.3/24 | R4 | Gi0/1 | 10.1.34.4/24 | 10.1.34.0/24 |
| L5 | R4 | Gi0/2 | 10.1.45.4/24 | R5 | Gi2 | 10.1.45.5/24 | 10.1.45.0/24 |
| L6 | R2 | Gi0/2 | 10.1.23.2/24 | R3 | Gi0/2 | 10.1.23.3/24 | 10.1.23.0/24 |
| L7 | R5 | Gi3 | 10.1.56.5/24 | R6 | Gi0/0 | 10.1.56.6/24 | 10.1.56.0/24 |
| L8 | R1 | Gi0/2 | 10.99.0.1/30 | R2 | Gi0/3 | 10.99.0.2/30 | 10.99.0.0/30 |

**Note:** L8 is a new link added in lab-04 for the dynamic neighbor demonstration.

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| R1 | 172.16.1.0/24 | eBGP | Customer A aggregate |
| R6 | 172.16.6.0/24 | eBGP | External peer aggregate — dampening target |

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
- Interface IP addressing on all routed links and loopbacks
- `no ip domain-lookup`
- OSPF area 0 on all SP core links (R2, R3, R4, R5)
- eBGP sessions: R1↔R2 (primary), R1↔R3 (backup), R5↔R6
- iBGP sessions: R2/R3/R5 as RR clients to R4 (and legacy R2↔R5 direct iBGP)
- BGP attributes from labs 01–03: LOCAL_PREF, MED, AS-path prepend, GTSM, MD5, maximum-prefix
- Customer A prefix (172.16.1.0/24) advertised by R1; external peer prefix (172.16.6.0/24) advertised by R6
- L8 physical link cabled: R1 Gi0/2 and R2 Gi0/3 are IP-addressed but not in BGP yet

**IS NOT pre-loaded** (student configures this):
- BGP route dampening on R5
- Dampening parameter tuning
- Dynamic BGP neighbor peer-group on R2
- BGP listen range on R2 for 10.99.0.0/24
- R1 BGP peering from the new Gi0/2 (10.99.0.1) toward R2 (10.99.0.2)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable BGP Route Dampening on R5

- Enable BGP route dampening on R5 with explicit parameters: half-life 15 minutes,
  reuse-limit 750, suppress-limit 2000, maximum-suppress-time 60 minutes.
- Dampening should apply globally to all eBGP-learned routes on R5.

**Verification:** `show ip bgp dampening parameters` on R5 must show all four values
matching the configured parameters. `show ip bgp 172.16.6.0` must NOT show the 'd' flag
initially (prefix is stable at this point).

---

### Task 2: Simulate Prefix Flapping and Observe Dampening

- On R6, shut and no-shut Loopback1 five times in quick succession to generate BGP
  withdraw/re-advertise cycles for 172.16.6.0/24.
- After each cycle, check the penalty accumulation on R5.

**Verification:** `show ip bgp dampening flap-statistics` on R5 must show a flap count
of 5 and a penalty above 2000. `show ip bgp 172.16.6.0` must show the 'd' flag (route
is suppressed). The prefix must be absent from `show ip route 172.16.6.0`.

---

### Task 3: Reset Dampening History and Verify Recovery

- Clear the dampening history for the 172.16.6.0/24 prefix on R5.
- Verify the prefix is reinstated in the BGP table after clearing.

**Verification:** After clearing, `show ip bgp 172.16.6.0` must show a valid next-hop
(no 'd' flag). The prefix must reappear in `show ip route`.

---

### Task 4: Configure Dynamic BGP Neighbors on R2

- Create a peer-group named `DYN_CUST` on R2 with remote-AS 65001.
- Set a description `Dynamic-Customer-AS65001` on the peer-group.
- Set a listen limit of 10 concurrent dynamic sessions.
- Configure R2 to accept incoming BGP sessions from the 10.99.0.0/24 range, applying
  the `DYN_CUST` peer-group template to each accepted session.
- Activate the `DYN_CUST` peer-group in the IPv4 unicast address-family and apply the
  `FROM-CUST-A-PRIMARY` inbound route-map (already defined in the base config).

**Verification:** `show ip bgp listen range` on R2 must show `10.99.0.0/24` mapped to
`DYN_CUST`. `show ip bgp peer-group DYN_CUST` must show the peer-group definition.

---

### Task 5: Simulate a Dynamic Customer Connection from R1

- On R1, bring up the new Gi0/2 interface (10.99.0.1/30) in BGP AS 65001 by adding a
  neighbor toward 10.99.0.2 (R2's Gi0/3 address).
- Activate this neighbor in the IPv4 unicast address-family.

**Verification:** On R2, `show ip bgp peer-group DYN_CUST` must show 10.99.0.1 as an
established dynamic member. The BGP session must reach the Established state. R2 must
receive 172.16.1.0/24 from the dynamic session.

---

## 6. Verification & Analysis

### Task 1: Dampening Parameters

```
R5# show ip bgp dampening parameters
dampening is enabled
  Half-life time      : 15 mins       ! ← must match configured value
  Reuse             : 750             ! ← prefix reinstated when penalty drops below this
  Suppress          : 2000            ! ← prefix hidden when penalty exceeds this
  Max suppress time : 60 mins         ! ← absolute maximum suppression duration
```

### Task 2: Flap Statistics and Suppression

```
R5# show ip bgp dampening flap-statistics
BGP table version is 5, local router ID is 10.0.0.5
Status codes: s suppressed, d damped, h history, * valid, > best
Origin codes: i - IGP, e - EGP, ? - incomplete

   Network          From             Flaps Duration Reuse    Path
*d 172.16.6.0/24   10.1.56.6        5     00:02:15  00:11:30 65002   ! ← 'd' means suppressed; Reuse time shows when prefix will return
```

```
R5# show ip bgp 172.16.6.0
BGP routing table entry for 172.16.6.0/24, version 4
Paths: (1 available, no best path)
  Not advertised to any peer
  65002
    10.1.56.6 from 10.1.56.6 (10.0.0.6)
      Origin IGP, metric 0, localpref 100, valid, external, dampened   ! ← "dampened" keyword confirms suppression
      Dampinfo: penalty 4000, flapped 5 times in 00:02:10, reuse in 00:11:30
```

```
R5# show ip route 172.16.6.0
% Network not in table                ! ← suppressed prefix is absent from RIB
```

### Task 3: Clear and Verify Recovery

```
R5# clear ip bgp dampening 172.16.6.0
R5# show ip bgp 172.16.6.0
BGP routing table entry for 172.16.6.0/24, version 6
Paths: (1 available, best #1, table Default-IP-Routing-Table)
  Advertised to update-groups:
     1
  65002
    10.1.56.6 from 10.1.56.6 (10.0.0.6)
      Origin IGP, metric 0, localpref 100, valid, external, best   ! ← "best" with no 'd' flag — prefix reinstated
```

### Task 4: Listen Range Configuration

```
R2# show ip bgp listen range
BGP listen range entry:
  peer-group DYN_CUST, listen range 10.99.0.0/24   ! ← listen range must show here

R2# show ip bgp peer-group DYN_CUST
BGP peer-group is DYN_CUST, remote AS 65001
  BGP version 4
  Default minimum time between advertisement runs is 0 seconds
  Members (count: 0):                               ! ← 0 until R1 connects from Gi0/2
```

### Task 5: Dynamic Session Established

```
R2# show ip bgp peer-group DYN_CUST
BGP peer-group is DYN_CUST, remote AS 65001
  BGP version 4
  Members (count: 1):
    10.99.0.1                                       ! ← R1's Gi0/2 address — dynamic member

R2# show ip bgp neighbors 10.99.0.1 | include BGP state
BGP state = Established, up for 00:01:42            ! ← session must be Established

R2# show ip bgp | include 172.16.1
* i172.16.1.0/24    10.1.12.1      0    200    0 65001 i   ! ← from static eBGP
*>  172.16.1.0/24   10.99.0.1      0    200    0 65001 i   ! ← from dynamic session (best path — same local-pref 200)
```

---

## 7. Verification Cheatsheet

### BGP Dampening Configuration

```
router bgp 65100
 bgp dampening 15 750 2000 60
```

| Command | Purpose |
|---------|---------|
| `bgp dampening` | Enable dampening with defaults (15/750/2000/60) |
| `bgp dampening <h> <r> <s> <m>` | Explicit: half-life, reuse, suppress, max-suppress-time |
| `no bgp dampening` | Disable dampening; existing penalties cleared |

> **Exam tip:** Dampening only applies to eBGP-learned routes. iBGP routes are never
> dampened. Configuring dampening under a specific neighbor is NOT supported in classic IOS —
> it applies globally. Use a route-map with `bgp dampening route-map` for selective dampening.

### Dampening Verification and Control

```
show ip bgp dampening parameters
show ip bgp dampening flap-statistics
show ip bgp dampening dampened-paths
show ip bgp <prefix>
clear ip bgp dampening
clear ip bgp dampening <prefix/len>
```

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp dampening parameters` | Confirm half-life, reuse, suppress, max-suppress values |
| `show ip bgp dampening flap-statistics` | Flap count, current penalty, time until reuse |
| `show ip bgp dampening dampened-paths` | All currently suppressed prefixes |
| `show ip bgp <prefix>` | 'd' flag = dampened; "Dampinfo" block shows penalty and reuse timer |
| `clear ip bgp dampening` | Reset all penalties immediately — prefix returns to active state |

### Dynamic BGP Neighbor Configuration

```
router bgp 65100
 bgp listen limit 10
 bgp listen range 10.99.0.0/24 peer-group DYN_CUST
 neighbor DYN_CUST peer-group
 neighbor DYN_CUST remote-as 65001
 neighbor DYN_CUST description Dynamic-Customer-AS65001
 !
 address-family ipv4
  neighbor DYN_CUST activate
  neighbor DYN_CUST route-map FROM-CUST-A-PRIMARY in
```

| Command | Purpose |
|---------|---------|
| `bgp listen limit <N>` | Max concurrent dynamic sessions (default 100) |
| `bgp listen range <pfx> peer-group <pg>` | Accept sessions from range and apply peer-group |
| `neighbor <pg> peer-group` | Declare peer-group |
| `neighbor <pg> remote-as <ASN>` | Require all dynamic peers to be from this AS |
| `neighbor <pg> activate` | Activate peer-group in IPv4 unicast AF |
| `show ip bgp listen range` | Confirm range-to-peer-group mapping |
| `show ip bgp peer-group <pg>` | List dynamic members and session state |

> **Exam tip:** The PE with `bgp listen range` is passive — it does NOT initiate the
> session. The customer router must be configured to connect outbound. Dynamic sessions
> do NOT appear in `show ip bgp summary` by default until they are established; use
> `show ip bgp peer-group` to see members.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip bgp summary` | State of all static BGP sessions; dynamic sessions appear once established |
| `show ip bgp listen range` | Configured listen range and associated peer-group |
| `show ip bgp peer-group DYN_CUST` | Members of the dynamic peer-group and session state |
| `show ip bgp dampening parameters` | Active dampening parameters |
| `show ip bgp dampening flap-statistics` | Per-prefix flap counts and current penalties |
| `show ip bgp dampening dampened-paths` | Prefixes currently suppressed |
| `show ip bgp <prefix>` | Full BGP path entry including dampening info |

### Common BGP Dampening Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Prefix shows 'd' flag even after peer is stable | Penalty still above reuse-limit; use `clear ip bgp dampening` |
| `bgp dampening` configured but no flap data | No flaps have occurred yet; must withdraw/re-advertise to accumulate |
| Dampening not taking effect on a prefix | Prefix is iBGP-learned (dampening does not apply to iBGP) |
| `bgp dampening route-map` not matching | Route-map permit clause missing; routes fall through without penalty |

### Common Dynamic Neighbor Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Dynamic session stays Active | `bgp listen range` missing or wrong range; PE is not listening for the customer address |
| Session established but no routes received | `neighbor DYN_CUST activate` missing in address-family |
| Dynamic peer appears but routes have wrong attributes | Route-map not applied to peer-group in AF; `neighbor DYN_CUST route-map` missing |
| Too many dynamic sessions refused | `bgp listen limit` set too low; increase limit |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 3: BGP Route Dampening on R5

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — add dampening under router bgp (CSR1000v / IOS-XE)
router bgp 65100
 bgp dampening 15 750 2000 60
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp dampening parameters
show ip bgp 172.16.6.0
show ip bgp dampening flap-statistics
show ip bgp dampening dampened-paths
! After simulating flaps on R6 (shut/no-shut Lo1 x5):
clear ip bgp dampening 172.16.6.0
show ip bgp 172.16.6.0
```
</details>

---

### Task 2: Simulate Flapping on R6

<details>
<summary>Click to view R6 Flap Simulation Commands</summary>

```bash
! Run this sequence 5 times on R6 to accumulate penalty above suppress-limit
interface Loopback1
 shutdown
!
interface Loopback1
 no shutdown
! Repeat 4 more times, then check R5:
! R5# show ip bgp dampening flap-statistics
! R5# show ip bgp 172.16.6.0
```
</details>

---

### Task 4 & 5: Dynamic BGP Neighbors on R2 and R1

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — add dynamic neighbor support
interface GigabitEthernet0/3
 description Dynamic-Customer range link to R1 (L8 lab-04)
 ip address 10.99.0.2 255.255.255.252
 no shutdown
!
router bgp 65100
 bgp listen limit 10
 bgp listen range 10.99.0.0/24 peer-group DYN_CUST
 neighbor DYN_CUST peer-group
 neighbor DYN_CUST remote-as 65001
 neighbor DYN_CUST description Dynamic-Customer-AS65001
 !
 address-family ipv4
  neighbor DYN_CUST activate
  neighbor DYN_CUST route-map FROM-CUST-A-PRIMARY in
```
</details>

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — add new interface and BGP peer from Gi0/2 toward R2's dynamic port
interface GigabitEthernet0/2
 description Dynamic-Neighbor demo link to R2 (L8 lab-04)
 ip address 10.99.0.1 255.255.255.252
 no shutdown
!
router bgp 65001
 neighbor 10.99.0.2 remote-as 65100
 neighbor 10.99.0.2 description R2-DynamicRange-port-L8
 !
 address-family ipv4
  neighbor 10.99.0.2 activate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R2:
show ip bgp listen range
show ip bgp peer-group DYN_CUST
show ip bgp neighbors 10.99.0.1 | include BGP state
show ip bgp summary
show ip bgp
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>              # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — 172.16.6.0/24 Is Missing from R5 and the Rest of the Network

The NOC reports that external prefix 172.16.6.0/24 (from AS 65002) cannot be reached
from any SP core router. R6 is confirmed stable and advertising the prefix.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** 172.16.6.0/24 appears in R5's BGP table (no 'd' flag) and in the
IP routing table of all SP core routers.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check if prefix is in R5's BGP table at all
R5# show ip bgp 172.16.6.0
! Look for: 'd' flag = suppressed; "Dampinfo" block with penalty and reuse timer

! Step 2 — confirm dampening is the cause
R5# show ip bgp dampening dampened-paths
! 172.16.6.0/24 should appear here

! Step 3 — check flap statistics
R5# show ip bgp dampening flap-statistics
! Flap count > 0 with high penalty confirms dampening triggered

! Step 4 — verify R6 is still advertising the prefix
R6# show ip bgp neighbors 10.1.56.5 advertised-routes
! 172.16.6.0/24 should be in the output — prefix is stable on R6's side
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! The prefix was dampened by accumulated penalty; R6 is now stable.
! Manual clear is required because the penalty is still above the reuse-limit.
R5# clear ip bgp dampening 172.16.6.0

! Verify recovery
R5# show ip bgp 172.16.6.0
! Expect: "valid, external, best" — no 'd' flag

R5# show ip route 172.16.6.0
! Expect: B 172.16.6.0/24 [20/0] via 10.1.56.6
```
</details>

---

### Ticket 2 — New Customer Session from 10.99.0.1 Stays in Active State

A new customer has cabled their router to R2's Gi0/3 port (10.99.0.0/30 subnet) and
configured BGP in AS 65001. Their router is sending OPEN messages but the session never
reaches Established. R2 shows the peer in the Active state.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** Session between 10.99.0.1 (R1) and R2 reaches Established state.
`show ip bgp peer-group DYN_CUST` shows 10.99.0.1 as a member.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check if listen range is present
R2# show ip bgp listen range
! If empty or 10.99.0.0/24 is missing, the router is not accepting connections from range

! Step 2 — verify the peer-group exists
R2# show ip bgp peer-group DYN_CUST
! If command fails or shows no peer-group, DYN_CUST was removed

! Step 3 — check BGP summary for dynamic peer
R2# show ip bgp summary | include 10.99.0.1
! If peer is listed as Active: R2 is trying to connect outbound (wrong — PE must be passive)
! If peer is not listed: R2 doesn't know about the session at all — listen range is missing

! Step 4 — confirm R1 Gi0/2 is up and configured
R1# show interface GigabitEthernet0/2
R1# show ip bgp neighbors 10.99.0.2 | include BGP state
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! The listen range was removed. Re-add it on R2.
R2# configure terminal
R2(config)# router bgp 65100
R2(config-router)# bgp listen range 10.99.0.0/24 peer-group DYN_CUST

! Verify
R2# show ip bgp listen range
! Expect: peer-group DYN_CUST, listen range 10.99.0.0/24

! Session should establish automatically since R1 is already sending OPENs
R2# show ip bgp peer-group DYN_CUST
! Expect: Members (count: 1): 10.99.0.1
```
</details>

---

### Ticket 3 — Dynamic Customer Session Is Up but No Routes Received on R2

The dynamic BGP session from 10.99.0.1 (Customer A via L8) is established and showing
in the BGP summary as Established. However, R2 is not receiving the 172.16.1.0/24
customer prefix through this dynamic session.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R2's BGP table shows 172.16.1.0/24 received from 10.99.0.1 (in
addition to the existing static eBGP session via 10.1.12.1).

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — confirm session is Established
R2# show ip bgp neighbors 10.99.0.1 | include BGP state
! Expect: BGP state = Established

! Step 2 — check if any routes are received from the dynamic peer
R2# show ip bgp neighbors 10.99.0.1 received-routes
! If empty: R2 is not receiving any prefixes from 10.99.0.1

! Step 3 — check peer-group AF activation
R2# show ip bgp peer-group DYN_CUST
! Look for: "For address family: IPv4 Unicast" — if this section is absent,
! the peer-group is not activated in the IPv4 AF

! Step 4 — verify address-family config directly
R2# show running-config | section address-family ipv4
! Look for: "neighbor DYN_CUST activate" — if missing, routes are not exchanged
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! DYN_CUST peer-group is missing "activate" in IPv4 unicast AF.
! The session is established (TCP/OPEN handshake works) but no NLRI is exchanged.
R2# configure terminal
R2(config)# router bgp 65100
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor DYN_CUST activate

! Verify
R2# show ip bgp neighbors 10.99.0.1 received-routes
! Expect: 172.16.1.0/24 via 10.99.0.1

R2# show ip bgp
! Expect: two entries for 172.16.1.0/24 — one via 10.1.12.1 (static), one via 10.99.0.1 (dynamic)
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R5 dampening parameters confirmed: half-life 15, reuse 750, suppress 2000, max 60
- [ ] Prefix 172.16.6.0/24 shows 'd' flag in R5 BGP table after 5 flaps on R6
- [ ] `clear ip bgp dampening 172.16.6.0` reinstates the prefix on R5
- [ ] R2 `bgp listen range 10.99.0.0/24 peer-group DYN_CUST` confirmed in `show ip bgp listen range`
- [ ] Dynamic session from 10.99.0.1 reaches Established state on R2
- [ ] R2 receives 172.16.1.0/24 from the dynamic session (10.99.0.1)

### Troubleshooting

- [ ] Ticket 1: Identified dampened prefix via `show ip bgp dampening dampened-paths`; fixed with `clear ip bgp dampening`
- [ ] Ticket 2: Identified missing `bgp listen range`; restored and confirmed session establishment
- [ ] Ticket 3: Identified missing `neighbor DYN_CUST activate` in AF; restored and confirmed route reception

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
