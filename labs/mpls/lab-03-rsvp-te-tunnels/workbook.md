# MPLS Lab 03: RSVP-TE Tunnels with Explicit Paths

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

**Exam Objective:** 4.1.e — RSVP-TE tunnels (CCNP SPRI 300-510)

RSVP-TE (Resource Reservation Protocol — Traffic Engineering) lets a service provider signal explicit label-switched paths through the MPLS core while simultaneously reserving bandwidth along each hop. This lab builds directly on the LDP and BGP-free core established in labs 00–02, adding a TE control plane that lets the operator steer traffic away from the default CSPF-chosen path and onto specific network segments.

### MPLS Traffic Engineering Architecture

MPLS TE has four distinct components that must all be in place before a tunnel can signal:

**1. TE topology database (TED)** — IS-IS (or OSPF) floods TE-extended LSAs that carry per-link bandwidth, maximum reservable bandwidth, and TE metric. Every TE-enabled router builds a complete view of the core topology from these extensions. The TED is separate from the regular IS-IS routing table; a router can be in the IS-IS RIB but invisible to TE if it hasn't enabled TE flooding.

**2. CSPF (Constrained Shortest Path First)** — runs on the tunnel headend only. Reads the TED, applies constraints (bandwidth, explicit path, affinity), and selects the path for the tunnel. CSPF prunes any link where available bandwidth < requested bandwidth before running Dijkstra.

**3. RSVP signaling** — the headend sends PATH messages hop-by-hop toward the tail; each transit LSR checks bandwidth admission and forwards the PATH. The tail sends RESV messages back toward the headend, creating the label reservation. No RESV = no tunnel.

**4. Forwarding** — after a successful RESV, the headend installs a label-stack entry for the tunnel. Traffic steered into the tunnel is forwarded as if on a normal LDP LSP, but following the RSVP-reserved path rather than the IGP best path.

```
 Headend            Transit            Tail
  (PE1)              (P1)              (PE2)
    │     PATH ──────►│     PATH ──────►│
    │                 │  (admission ok) │
    │◄──── RESV ──────│◄──── RESV ──────│
    │ (label stacked) │ (label swapped) │
```

All four components must be active on every hop; a single missing piece silently breaks the tunnel.

### IS-IS TE Extensions

To participate in TE topology flooding, every core router needs two additions under `router isis`:

- `mpls traffic-eng level-2` — instructs IS-IS to originate Extended IS Reachability (TLV 22) sub-TLVs carrying TE attributes (link bandwidth, max reservable BW, TE metric). Without this, the router is invisible to CSPF on other nodes even though it appears in the normal IS-IS RIB.
- `mpls traffic-eng router-id Loopback0` — sets the stable TE router ID (must match the loopback used for RSVP SENDER_TEMPLATE). This must be the same loopback as the LDP router-id.

After adding these, verify with `show mpls traffic-eng topology` on any core router — every TE-enabled node and every TE-enabled link appears with bandwidth attributes.

### RSVP Bandwidth and Admission Control

`ip rsvp bandwidth <total-kbps> <max-flow-kbps>` on an interface does two things:
1. Enables RSVP on the interface (required — RSVP is disabled by default)
2. Sets the reservable bandwidth pool for admission control

CSPF reads the TED's "available bandwidth" field (total - already reserved) when selecting paths. If a link has `ip rsvp bandwidth 10` (10 kbps) but a tunnel requests 10,000 kbps (10 Mbps), CSPF eliminates that link from consideration. This is admission control working correctly — it prevents over-subscription.

The `show mpls traffic-eng topology` output shows both configured and available bandwidth per link, making it the definitive diagnostic command for bandwidth-related CSPF failures.

### RSVP-TE Explicit Paths

Dynamic CSPF picks the best path automatically. Explicit paths override CSPF to force specific transit nodes:

```
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3     ! P2 loopback — traverse P2
 next-address loose 10.0.0.4     ! PE2 loopback — end here
```

`loose` means "reach this address via any available path from the current position." `strict` (default, no keyword) means "the next address must be a directly connected neighbor" — which requires the actual interface IP, not the loopback.

Explicit paths are powerful for traffic engineering:
- Pin specific traffic classes to specific physical links for capacity sharing
- Keep high-priority flows off congested paths
- Test alternate paths without disrupting primary traffic

### Traffic Steering with Autoroute

By default, a TE tunnel is a forwarding device but nothing points traffic into it. `tunnel mpls traffic-eng autoroute announce` installs the tunnel's destination prefix (PE2 loopback) into IS-IS as if the tunnel were an IS-IS adjacency, with the tunnel's metric used as the IS-IS route cost. After this, `show ip route 10.0.0.4` on PE1 shows `via Tunnel10` as the outgoing interface. `traceroute 10.0.0.4` will show the first physical hop on the tunnel path with an `[MPLS: Label]` annotation — the tunnel interface itself is transparent to traceroute, but the label confirms the packet was forwarded through the RSVP-TE LSP.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| MPLS TE global enablement | Enable TE on routers and interfaces to activate the TE control plane |
| IS-IS TE extensions | Configure TE LSA flooding for CSPF topology awareness |
| RSVP bandwidth | Set reservable bandwidth pools; understand admission control |
| CSPF dynamic path | Let the headend compute the optimal TE path automatically |
| Explicit path | Force a specific transit node using loose next-address hops |
| Autoroute announce | Steer IS-IS traffic into a TE tunnel automatically |
| Secondary path-option | Configure a hot-standby path for tunnel resilience |
| TE troubleshooting | Diagnose CSPF failures, missing TE topology entries, and RSVP admission errors |

---

## 2. Topology & Scenario

**Scenario:** The SP core (AS 65100) has been running LDP-based forwarding since lab-00. Operations wants to add RSVP-TE tunnels so they can pin high-value customer traffic to specific paths independent of the default IGP route. You are tasked with enabling the TE control plane on all four core routers, verifying the TE topology database, and building two tunnels from PE1 to PE2: one with dynamic CSPF path selection, and a second that explicitly forces transit through P2.

```
                   AS 65100  IS-IS L2 + MPLS LDP + RSVP-TE

              ┌──────────────────────────────────┐
              │        BGP-free core             │
              │                                  │
  AS 65101    │  ┌───────────┐   ┌───────────┐   │   AS 65102
┌──────────┐  │  │    PE1    ├L2─┤    P1     │   │  ┌──────────┐
│   CE1    ├L1┤  │ AS 65100  │   │(BGP-free) │   │L7┤   CE2    │
│10.0.0.11 │  │  │10.0.0.1   │   │10.0.0.2   │   │  │10.0.0.12 │
│192.0.2.1 │  │  └───────────┘   └─────┬─────┘   │  │198.51... │
└──────────┘  │       │ iBGP+LU   L4   │    L5   │  └──────────┘
              │       │                │         │
              │  ┌────┴──────┐   ┌─────┴─────┐   │
              │  │    PE2    ├L6─┤    P2     │   │
              │  │ AS 65100  │   │(BGP-free) │   │
              │  │10.0.0.4   │   │10.0.0.3   │   │
              │  └───────────┘   └───────────┘   │
              │       │ (L3 PE1↔P2, not shown)   │
              └──────────────────────────────────┘
```

Full link table:

| Link | Endpoints | Subnet | Protocol |
|------|-----------|--------|----------|
| L1 | CE1 Gi0/0 ↔ PE1 Gi0/0 | 10.10.111.0/24 | eBGP |
| L2 | PE1 Gi0/1 ↔ P1 Gi0/0 | 10.10.12.0/24 | IS-IS L2 + LDP + RSVP |
| L3 | PE1 Gi0/2 ↔ P2 Gi0/0 | 10.10.13.0/24 | IS-IS L2 + LDP + RSVP |
| L4 | P1 Gi0/1 ↔ P2 Gi0/1 | 10.10.23.0/24 | IS-IS L2 + LDP + RSVP |
| L5 | P1 Gi0/2 ↔ PE2 Gi0/1 | 10.10.24.0/24 | IS-IS L2 + LDP + RSVP |
| L6 | P2 Gi0/2 ↔ PE2 Gi0/2 | 10.10.34.0/24 | IS-IS L2 + LDP + RSVP |
| L7 | CE2 Gi0/0 ↔ PE2 Gi0/0 | 10.10.122.0/24 | eBGP |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| PE1 | SP Edge — RSVP-TE headend, iBGP to PE2 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P1 | SP Core (BGP-free) — IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| P2 | SP Core (BGP-free) — IS-IS L2 + LDP + RSVP-TE transit | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| PE2 | SP Edge — RSVP-TE tail, iBGP to PE1 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE1 | Customer Edge AS 65101 — announces 192.0.2.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer Edge AS 65102 — announces 198.51.100.0/24 | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| PE1 | Loopback0 | 10.0.0.1/32 | Router ID, LDP ID, RSVP headend |
| P1 | Loopback0 | 10.0.0.2/32 | Router ID, LDP ID, TE router-id |
| P2 | Loopback0 | 10.0.0.3/32 | Router ID, LDP ID, TE router-id |
| PE2 | Loopback0 | 10.0.0.4/32 | Router ID, LDP ID, RSVP tail |
| CE1 | Loopback0 | 10.0.0.11/32 | CE router ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix announced via eBGP |
| CE2 | Loopback0 | 10.0.0.12/32 | CE router ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix announced via eBGP |

### Cabling

| Link | Device A | Interface | IP Address | Device B | Interface | IP Address |
|------|----------|-----------|-----------|----------|-----------|-----------|
| L1 | CE1 | Gi0/0 | 10.10.111.11/24 | PE1 | Gi0/0 | 10.10.111.1/24 |
| L2 | PE1 | Gi0/1 | 10.10.12.1/24 | P1 | Gi0/0 | 10.10.12.2/24 |
| L3 | PE1 | Gi0/2 | 10.10.13.1/24 | P2 | Gi0/0 | 10.10.13.3/24 |
| L4 | P1 | Gi0/1 | 10.10.23.2/24 | P2 | Gi0/1 | 10.10.23.3/24 |
| L5 | P1 | Gi0/2 | 10.10.24.2/24 | PE2 | Gi0/1 | 10.10.24.4/24 |
| L6 | P2 | Gi0/2 | 10.10.34.3/24 | PE2 | Gi0/2 | 10.10.34.4/24 |
| L7 | PE2 | Gi0/0 | 10.10.122.4/24 | CE2 | Gi0/0 | 10.10.122.12/24 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| PE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| P2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames
- Interface IP addressing (all routed links and loopbacks)
- `no ip domain-lookup`
- IS-IS L2 adjacencies (`router isis CORE`, area 49.0001, level-2-only, `metric-style wide`, loopback passive)
- MPLS LDP on all core-facing interfaces (`mpls ip`, `mpls mtu override 1508`, `mpls ldp router-id Loopback0 force`)
- iBGP PE1↔PE2 with `send-label` and `next-hop-self` (lab-02 solution state)
- eBGP PE1↔CE1 and PE2↔CE2 with customer prefix advertisements (lab-02 solution state)

**IS NOT pre-loaded** (student configures this):
- MPLS TE global enablement (`mpls traffic-eng tunnels`)
- MPLS TE on core-facing interfaces (`mpls traffic-eng tunnels` per interface)
- IS-IS TE flooding extensions (`mpls traffic-eng level-2`, `mpls traffic-eng router-id`)
- RSVP reservable bandwidth on core interfaces
- TE tunnel interfaces (Tunnel10 dynamic, Tunnel20 explicit)
- Explicit path definitions
- Autoroute announce on Tunnel10
- Explicit path (PE1-via-P2) for Tunnel20

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable MPLS Traffic Engineering Globally

- Enable MPLS TE on all four core routers (PE1, P1, P2, PE2) at the global configuration level.
- Enable MPLS TE on every core-facing interface of each core router: PE1 Gi0/1 and Gi0/2; P1 Gi0/0, Gi0/1, and Gi0/2; P2 Gi0/0, Gi0/1, and Gi0/2; PE2 Gi0/1 and Gi0/2. Customer-facing interfaces (PE1 Gi0/0, PE2 Gi0/0) do not need TE.

**Verification:** `show mpls interfaces detail` on each core router must show `LSP Tunnel labeling enabled` on each core-facing interface where TE was applied.

> **Note:** `show mpls traffic-eng tunnels` returns **no output at this stage** — that is correct. No tunnel interfaces exist yet (they are created in Tasks 4 and 5). An empty result means the command accepted successfully; an error (`% Invalid input`) would indicate TE is not globally enabled.

---

### Task 2: Enable IS-IS Traffic Engineering Extensions

- On each core router (PE1, P1, P2, PE2), configure the router process to originate TE sub-TLVs by enabling TE flooding for level-2 and specifying Loopback0 as the TE router ID.

**Verification:** `show mpls traffic-eng topology` on PE1 must list all four core routers (PE1, P1, P2, PE2) as TE nodes. Each node entry must include link bandwidth attributes for every connected core interface. If any router is absent from the topology output, its IS-IS TE extensions are not configured.

---

### Task 3: Enable RSVP Bandwidth Reservations on Core Links

- On every core-facing interface of PE1, P1, P2, and PE2 (all five links: L2, L3, L4, L5, L6 — both endpoints of each link), configure 100 Mbps total reservable bandwidth and 100 Mbps maximum per-flow bandwidth.

**Verification:** `show ip rsvp interface` on each core router must show all core-facing interfaces listed with 100,000 kbps allocated and 100,000 kbps maximum per-flow. An interface not listed here has no RSVP — PATH messages traversing it will not generate RESV responses.

---

### Task 4: Build Tunnel10 with Dynamic CSPF Path and Autoroute

All configuration for this task is on **PE1 only**. The transit routers (P1, P2) and the tail (PE2) need no tunnel interface — they were fully prepared in Tasks 1–3. When the tunnel is signalled, PE1 sends an RSVP PATH message hop-by-hop toward PE2; each transit router forwards it and reserves bandwidth; PE2 receives it and automatically sends a RESV back to PE1. No manual intervention is needed on PE2 to accept the tunnel.

- On PE1, create a tunnel interface numbered 10.
- Set the tunnel destination to PE2's loopback address.
- Use IP unnumbered from Loopback0 — no dedicated /30 is needed for each tunnel.
- Set the tunnel mode to MPLS TE.
- Request 10 Mbps of bandwidth. CSPF reads this value during path computation and prunes any link that cannot satisfy it.
- Set the setup priority and hold priority both to 1. Priority controls RSVP-TE preemption: a new tunnel whose setup priority is numerically lower than an existing tunnel's hold priority can tear down that tunnel to claim its bandwidth. The range is 0 (highest) to 7 (lowest); the default is 7/7. Setting both to 1 makes this a high-priority tunnel that can preempt most others and is itself only displaced by a tunnel with setup priority 0.
- Attach a single dynamic path-option — CSPF selects the route automatically based on the TE topology database.
- Enable autoroute announce so IS-IS installs PE2's loopback reachability through the tunnel rather than via the physical core link.

> **Context help:** All RSVP-TE tunnel parameters — bandwidth, path-option, autoroute, priority — live under the `tunnel mpls traffic-eng` command tree, not `mpls traffic-eng`. From inside a tunnel interface, try `tunnel mpls traffic-eng ?` to explore the available sub-commands.

**Verification:** `show mpls traffic-eng tunnels tunnel10` must show `Admin: up  Oper: up`. `show ip route 10.0.0.4` on PE1 must show the tunnel interface as the outgoing interface.

---

### Task 5: Build Tunnel20 with an Explicit Path via P2

Explicit paths let you override CSPF and pin an RSVP-TE tunnel to a specific set of transit nodes. They are named path definitions created in global configuration and then referenced by name inside the tunnel interface.

- On PE1, define a named explicit path called `PE1-via-P2` that forces transit through P2's loopback before reaching PE2's loopback. Use loose next-address hops — CSPF resolves the physical route between each waypoint automatically.
- Create a tunnel interface numbered 20, destined for PE2's loopback.
- Use the same IP unnumbered, tunnel mode, bandwidth, and priority settings as Tunnel10.
- Attach the explicit path as the sole path-option. There is no dynamic fallback — if P2 or its links become unavailable, Tunnel20 goes down by design.
- Do not add autoroute announce. Tunnel10 already handles reachability to PE2; Tunnel20 is reserved for explicit traffic steering.

> **Context help:** Explicit path definitions use `ip explicit-path name <name> enable` followed by `next-address` sub-commands. This is a **global config** command — enter it at `(config)#`, not inside the tunnel interface. Use `next-address ?` (before typing the address) to see the available hop-type keywords — they precede the IP address, not follow it.

**Verification:** `show mpls traffic-eng tunnels Tunnel20` must show `Oper: up` and the explicit path name in use. The ERO hops in the same output must include P2's address, confirming the path transits through P2 rather than P1.

---

### Task 6: Compare Tunnel10 and Tunnel20 Paths

- From PE1, run `show mpls traffic-eng tunnels` to display both tunnels side by side. Note which physical path each tunnel uses (one should go via P1, the other via P2 — they represent two disjoint paths through the diamond core).
- Run `traceroute 10.0.0.4` from PE1 to confirm traffic is flowing through the tunnel. Hop 1 will show the first physical router on the tunnel path (P1's interface address) with an `[MPLS: Label]` annotation — that annotation is the evidence the packet was MPLS-encapsulated by the tunnel. Tunnel interfaces are transparent to traceroute; you will not see `Tunnel10` listed as a hop address.
- From CE1, ping 198.51.100.1 sourced from 192.0.2.1 to confirm end-to-end customer reachability is still intact with TE in place.

**Verification:** `show mpls traffic-eng tunnels` must show both tunnels `UP`. `traceroute 10.0.0.4` from PE1 must show `[MPLS: Label ...]` annotated on hop 1 — this confirms the probe was MPLS-encapsulated via the tunnel. The hop 1 address will be the first physical router on the tunnel path (P1), not the tunnel interface name — tunnel interfaces are transparent to traceroute. CE1-to-CE2 ping must succeed 5/5.

---

## 6. Verification & Analysis

### Task 1 & 2: TE Global and IS-IS TE Verification

```
PE1# show mpls traffic-eng topology
...
My_System_id: 0000.0000.0001.00 (isis CORE)
Prio    BW[0]       BW[1]       BW[2]       BW[3]       BW[4]       BW[5]       BW[6]       BW[7]
 Link[0]: Point-to-Point, Nbr Node id 1, gen 3, node id 1, Link id 1
   frag_id 0, Intf Address: 10.10.12.1, Nbr Intf Address: 10.10.12.2
   Intf id 0, Nbr Intf id 0
   Admin. Weight: 10, Attribute Flags: 0x0
   BW[0]: 100000        100000        100000        100000        100000  ! ← 100 Mbps on L2
...
 Link[1]: Point-to-Point, Nbr Node id 2, gen 3, node id 2, Link id 2
   frag_id 0, Intf Address: 10.10.13.1, Nbr Intf Address: 10.10.13.3
   BW[0]: 100000        100000        100000        100000        100000  ! ← 100 Mbps on L3

! ← Every core node (PE1, P1, P2, PE2) must appear. If P2 is missing,
!    its IS-IS TE extensions are not configured.

PE1# show mpls interfaces detail
Interface GigabitEthernet0/1:
        Type Unknown
        IP labeling enabled (ldp):
          Interface config
        LSP Tunnel labeling enabled      ! ← confirms TE active on this interface
        IP FRR labeling not enabled
        BGP labeling not enabled
        MPLS operational
        MTU = 1500
Interface GigabitEthernet0/2:
        Type Unknown
        IP labeling enabled (ldp):
          Interface config
        LSP Tunnel labeling enabled      ! ← both core PE1 interfaces must show this
        IP FRR labeling not enabled
        BGP labeling not enabled
        MPLS operational
        MTU = 1500

! IOSv 15.9 reports TE enablement as 'LSP Tunnel labeling enabled'.
! IOS-XE / documentation may show 'Traffic Engineering: enabled' — same state, different label.
```

### Task 3: RSVP Interface Verification

```
PE1# show ip rsvp interface
            allocated  i/f max  flow max
Gi0/1          0         100000   100000  ! ← 100,000 kbps (100 Mbps) allocated
Gi0/2          0         100000   100000  ! ← both core PE1 interfaces

P1# show ip rsvp interface
            allocated  i/f max  flow max
Gi0/0          0         100000   100000  ! ← L2 toward PE1
Gi0/1          0         100000   100000  ! ← L4 toward P2
Gi0/2          0         100000   100000  ! ← L5 toward PE2
```

### Task 4: Tunnel10 Dynamic Path

```
PE1# show mpls traffic-eng tunnels tunnel10
Name:PE1_t10                             (Tunnel10) Destination: 10.0.0.4
  Status:
    Admin: up         Oper: up     Path: valid       Signalling: connected  ! ← must be 'up'/'connected'

    path option 10, type dynamic (Basis for Setup, path weight 2)
    Path info (PCE disabled):
      Explicit Route: 10.10.12.2 10.10.24.2 10.0.0.4  ! ← CSPF-selected path (via P1: PE1→P1→PE2)

PE1# show ip route 10.0.0.4
Routing entry for 10.0.0.4/32
  Known via "isis", distance 115, metric 30, type level-2
  Redistributing via isis CORE
  Routing Descriptor Blocks:
  * directly connected, via Tunnel10    ! ← autoroute installed PE2 loopback via tunnel
```

### Task 5: Tunnel20 Explicit Path

```
PE1# show mpls traffic-eng tunnels Tunnel20
Name:PE1_t20                             (Tunnel20) Destination: 10.0.0.4
  Status:
    Admin: up         Oper: up     Path: valid       Signalling: connected

    path option 10, type explicit PE1-via-P2
    Path info (PCE disabled):
      Explicit Route: 10.10.13.3 10.10.34.3 10.0.0.4  ! ← P2 (10.0.0.3) loopback
      ! ← confirms transit via P2, NOT via P1

PE1# show mpls traffic-eng tunnels
Tunnel10  10.0.0.4  path option 10  dynamic  UP  (path via P1)
Tunnel20  10.0.0.4  path option 10  explicit PE1-via-P2  UP  (path via P2)
! ← both tunnels UP on distinct paths — demonstrates RSVP-TE path diversity
```

### Task 6: End-to-End Verification

```
PE1# traceroute 10.0.0.4 source Loopback0
Type escape sequence to abort.
Tracing the route to 10.0.0.4
VRF info: (vrf in name/id, vrf out name/id)
  1 10.10.12.2 [MPLS: Label 21 Exp 0] 2 msec 1 msec 1 msec
  ! ↑ hop 1 is P1's interface (10.10.12.2) — tunnel interfaces are transparent to traceroute.
  !   The [MPLS: Label] annotation confirms the probe was forwarded via the RSVP-TE tunnel.
  !   Without the tunnel, hop 1 would show no MPLS annotation (or an LDP label, not an RSVP label).
  2 10.10.24.4 1 msec
  ! ↑ PE2's Gi0/1 — P1 performed PHP, so PE2 received native IP with no label.

CE1# ping 198.51.100.1 source 192.0.2.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 198.51.100.1, timeout is 2 seconds:
Packet sent with a source address of 192.0.2.1
!!!!!    ! ← 5/5 success; customer reachability intact with TE active
```

---

## 7. Verification Cheatsheet

### MPLS TE Global Enablement

```
mpls traffic-eng tunnels           ! global (all routers)
interface GigabitEthernet0/1
 mpls traffic-eng tunnels          ! per core-facing interface
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng tunnels` | List all TE tunnels and their state |
| `show mpls interfaces detail` | Verify TE is enabled on each interface — look for `LSP Tunnel labeling enabled` (IOSv 15.9) |
| `show mpls traffic-eng topology` | View full TE topology database |

> **Exam tip:** `mpls traffic-eng tunnels` must be configured at BOTH the global level AND per interface. Missing either one disables TE on those interfaces — the global command alone is not sufficient.

### IS-IS TE Extensions

```
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng topology` | Verify all routers visible in TED |
| `show isis database verbose` | Confirm TE sub-TLVs in IS-IS LSPs |

> **Exam tip:** A router in IS-IS but missing `mpls traffic-eng level-2` is invisible to CSPF. Its links won't appear in the TE topology, so no tunnel can be routed through it.

### RSVP Interface Configuration

```
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000   ! 100 Mbps total / 100 Mbps per-flow
```

| Command | Purpose |
|---------|---------|
| `show ip rsvp interface` | List RSVP-enabled interfaces and bandwidth |
| `show ip rsvp request` | Show active RSVP PATH states (headend) |
| `show ip rsvp reservation` | Show active RESV states (bandwidth reserved) |
| `show ip rsvp sender` | Show RSVP SENDER_TEMPLATE entries |

> **Exam tip:** RSVP is disabled on all interfaces by default. `ip rsvp bandwidth` is not optional — without it, no tunnel PATH can traverse the interface.

### TE Tunnel Configuration (PE1 headend)

```
! Explicit paths are global config — defined BEFORE the tunnel interface references them
ip explicit-path name PE1-via-P2 enable     ! Task 5: primary path for Tunnel20
 next-address loose 10.0.0.3               ! P2 loopback waypoint
 next-address loose 10.0.0.4               ! PE2 loopback destination
!
! Tunnel10: dynamic CSPF primary, autoroute announces PE2 loopback via the tunnel
interface Tunnel10
 ip unnumbered Loopback0
 tunnel mode mpls traffic-eng
 tunnel destination 10.0.0.4
 tunnel mpls traffic-eng autoroute announce
 tunnel mpls traffic-eng bandwidth 10000   ! TE bandwidth — NOT the interface bandwidth command
 tunnel mpls traffic-eng priority 1 1
 tunnel mpls traffic-eng path-option 10 dynamic
```

| Command | Purpose |
|---------|---------|
| `show mpls traffic-eng tunnels tunnel10` | Tunnel state, active path, path-options |
| `show mpls traffic-eng tunnels Tunnel10` | ERO hops, RSVP session details — specifying a single tunnel returns full detail automatically on IOSv |
| `show mpls forwarding-table tunnel 10` | Label forwarding entry for the tunnel |
| `show ip route 10.0.0.4` | Confirm autoroute installed PE2 via tunnel |

> **Exam tip:** `tunnel mpls traffic-eng` and `mpls traffic-eng` are two separate command trees, both available under `(config-if)#`. The `tunnel mpls traffic-eng` tree (bandwidth, path-option, autoroute, priority) is only present on tunnel interfaces. The `mpls traffic-eng` tree (admin-weight, SRLG, attribute-flags) applies to physical links and sets IS-IS TE LSA attributes. Use `tunnel mpls traffic-eng ?` — not `mpls traffic-eng ?` — when configuring tunnel behavior.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show mpls traffic-eng topology` | All 4 core nodes present; bandwidth > 0 on every core link |
| `show mpls traffic-eng tunnels` | Both tunnels in `UP` / `connected` state |
| `show ip rsvp interface` | All 5 core links (L2–L6, both endpoints) RSVP-enabled at 100,000 kbps |
| `show mpls traffic-eng tunnels detail` | ERO shows expected hops; bandwidth and priority correct |
| `traceroute 10.0.0.4` from PE1 | Hop 1 shows `[MPLS: Label ...]` — confirms the probe was forwarded via the tunnel; the address shown is P1's physical interface (tunnel interfaces are transparent to traceroute) |

### Common RSVP-TE Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Tunnel stays `DOWN` after configuration | IS-IS TE extensions missing on a transit router — CSPF has no path |
| Tunnel UP but `show ip route` shows physical interface | `autoroute announce` missing on tunnel |
| Secondary path never comes up | RSVP bandwidth too low on a transit link; CSPF pruned the path |
| P2 not in `show mpls traffic-eng topology` | `mpls traffic-eng level-2` missing under `router isis` on P2 |
| Tunnel goes DOWN after `shut` on transit link | Normal behavior; RSVP tears down and the tunnel reoptimizes if an alternate path is available |
| `show ip rsvp interface` shows interface missing | `ip rsvp bandwidth` not configured on that interface |
| Tunnel stays `DOWN` with `no path options defined` | `tunnel mpls traffic-eng path-option` commands are missing — path-options must be added explicitly |
| `show mpls traffic-eng tunnels` shows `Bandwidth: 0 kbps` | `bandwidth` (interface command) was used instead of `tunnel mpls traffic-eng bandwidth` — the TE bandwidth requires the `tunnel mpls traffic-eng` prefix |
| `ip explicit-path` rejected with `Invalid input` | Command entered inside a tunnel interface — `ip explicit-path` is a **global config** command; exit to `(config)#` before entering it |
| `next-address <IP> ?` shows only `<cr>` — `loose` seems missing | The hop-type keyword precedes the address: `next-address loose <IP>`, not `next-address <IP> loose`. Use `next-address ?` before typing the address to see available keywords |
| `tunnel mpls traffic-eng autoroute` / `path-option` not found | Inside the wrong interface — `tunnel mpls traffic-eng` sub-commands only exist on tunnel interfaces (`interface TunnelX`). On physical interfaces, `mpls traffic-eng` shows a different command tree (admin-weight, SRLG) — enter `interface Tunnel10` first |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: MPLS TE Global and Interface Enablement

<details>
<summary>Click to view PE1 Configuration</summary>

```bash
! PE1
mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
```
</details>

<details>
<summary>Click to view P1 Configuration</summary>

```bash
! P1
mpls traffic-eng tunnels
!
interface GigabitEthernet0/0
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
```
</details>

<details>
<summary>Click to view P2 Configuration</summary>

```bash
! P2 — same as P1
mpls traffic-eng tunnels
!
interface GigabitEthernet0/0
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
```
</details>

<details>
<summary>Click to view PE2 Configuration</summary>

```bash
! PE2
mpls traffic-eng tunnels
!
interface GigabitEthernet0/1
 mpls traffic-eng tunnels
!
interface GigabitEthernet0/2
 mpls traffic-eng tunnels
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls interfaces detail
show mpls traffic-eng tunnels
```
</details>

---

### Task 2: IS-IS TE Extensions

<details>
<summary>Click to view All Core Routers Configuration</summary>

```bash
! PE1, P1, P2, PE2 — same additions under router isis CORE
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng topology
show isis database verbose | include TE
```
</details>

---

### Task 3: RSVP Bandwidth Configuration

<details>
<summary>Click to view RSVP Configuration — All Core Routers</summary>

```bash
! PE1
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! P1
interface GigabitEthernet0/0
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! P2
interface GigabitEthernet0/0
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000

! PE2
interface GigabitEthernet0/1
 ip rsvp bandwidth 100000 100000
interface GigabitEthernet0/2
 ip rsvp bandwidth 100000 100000
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip rsvp interface
```
</details>

---

### Tasks 4 & 5: Tunnel10 (Dynamic) and Tunnel20 (Explicit)

<details>
<summary>Click to view PE1 Tunnel and Explicit Path Configuration</summary>

```bash
! ── Task 4: Tunnel10 — dynamic CSPF primary with autoroute ───────
interface Tunnel10
 ip unnumbered Loopback0
 tunnel mode mpls traffic-eng
 tunnel destination 10.0.0.4
 tunnel mpls traffic-eng autoroute announce
 tunnel mpls traffic-eng bandwidth 10000
 tunnel mpls traffic-eng priority 1 1
 tunnel mpls traffic-eng path-option 10 dynamic
!
! ── Task 5: explicit path + Tunnel20 — explicit-only via P2 ──────
! Step 1: define the path in global config (not inside the tunnel interface)
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3    ! P2 loopback — forces path via L3 → P2 → L6 → PE2
 next-address loose 10.0.0.4    ! PE2 loopback — destination
!
! Step 2: tunnel interface — no autoroute; Tunnel20 is for explicit traffic steering only
interface Tunnel20
 ip unnumbered Loopback0
 tunnel mode mpls traffic-eng
 tunnel destination 10.0.0.4
 tunnel mpls traffic-eng bandwidth 10000
 tunnel mpls traffic-eng priority 1 1
 tunnel mpls traffic-eng path-option 10 explicit name PE1-via-P2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show mpls traffic-eng tunnels
show mpls traffic-eng tunnels Tunnel10
show mpls traffic-eng tunnels Tunnel20
show ip route 10.0.0.4
traceroute 10.0.0.4
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

---

### Ticket 1 — Tunnel20 DOWN After Routine Maintenance

Tunnel20 (explicit path via P2) went down after a maintenance window on PE1. Tunnel10 is unaffected and customer traffic continues to flow. IS-IS adjacencies, LDP sessions, and RSVP interfaces are all fully intact. The operator reports that the change script touched "explicit path policy" on the headend.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel20` shows `Admin: up  Oper: up  Signalling: connected`. `show ip explicit-paths` on PE1 lists `PATH PE1-via-P2` with two `next-address loose` entries (10.0.0.3 and 10.0.0.4).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel20` — `Oper: down`, `Path: not valid`, `Signalling: Down`. Path-option 10 is configured as `explicit PE1-via-P2`.
2. Check IS-IS and RSVP — both are intact. The fault is not in the transport or RSVP bandwidth layer. Focus on the explicit path reference itself.
3. Inspect the explicit path definition: `show ip explicit-paths` on PE1 — `PATH PE1-via-P2` is absent from the output. Without this definition, CSPF has no waypoint list to compute from; path-option 10 immediately fails.
4. Confirm: `show mpls traffic-eng tunnels Tunnel20` — the `Active Path Option Parameters` section shows no state (tunnel cannot establish any LSP). Tunnel10 is unaffected because it uses a dynamic path-option with no explicit path reference.
</details>

<details>
<summary>Click to view Fix</summary>

On PE1 — recreate the explicit path definition:
```bash
ip explicit-path name PE1-via-P2 enable
 next-address loose 10.0.0.3
 next-address loose 10.0.0.4
```

Tunnel20 re-runs CSPF within seconds and re-signals via P2. Verify: `show mpls traffic-eng tunnels Tunnel20` returns `Oper: up  Signalling: connected` and the ERO confirms P2 (10.0.0.3) as a transit hop.
</details>

---

### Ticket 2 — Tunnel20 Flapping After Core Maintenance

Tunnel20 (explicit path via P2) has been flapping since a P2 maintenance operation. It was working before the window. Tunnel10 (via P1) is unaffected. The operations team made "only IS-IS changes" on P2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel20` shows `Oper: up` and `Signalling: connected`. `show mpls traffic-eng topology` includes P2 (10.0.0.3) as a TE node.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel20` — `Oper: down`, path-option 10 shows `[failed]`.
2. Inspect the TE topology: `show mpls traffic-eng topology` on PE1 — P2 (10.0.0.3) is absent from the node list even though P2 is reachable via IS-IS (`show ip route 10.0.0.3` returns valid).
3. Connect to P2 and check IS-IS TE config: `show running-config | section isis` on P2 — `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` are missing.
4. Confirm the root cause: without TE flooding enabled, P2 does not send Extended IS Reachability TLVs. Other routers build the TE topology without P2's links, so CSPF has no path through P2.
</details>

<details>
<summary>Click to view Fix</summary>

On P2:
```bash
router isis CORE
 mpls traffic-eng level-2
 mpls traffic-eng router-id Loopback0
```

IS-IS TE LSAs propagate within a few seconds. Verify on PE1: `show mpls traffic-eng topology` — P2 reappears with its L3, L4, and L6 links. Tunnel20 re-signals automatically and returns to `Oper: up`.
</details>

---

### Ticket 3 — Tunnel10 Down After Routine Config Push

Tunnel10 went down after a routine config push to P1. All IS-IS adjacencies on P1 are intact and LDP sessions are up. The LDP-based LFIB forwarding path PE1→P1→PE2 is working (confirmed by `ping mpls ipv4 10.0.0.4/32`). The RSVP-TE tunnel, however, is not signalling.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show mpls traffic-eng tunnels tunnel10` shows `Admin: up Oper: up` and `Signalling: connected`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show mpls traffic-eng tunnels tunnel10` — `Oper: down`, `Signalling: Down`.
2. Check the RSVP PATH flow: the headend PE1 sends PATH toward P1. On P1, check: `show ip rsvp interface` — the interfaces toward PE1 and PE2 are not listed. RSVP is not enabled on P1 at all.
3. Verify P1 global TE state: `show mpls traffic-eng tunnels` on P1 — returns without output (no tunnels on a transit P router, this is expected). `show mpls interfaces detail` on P1 — interfaces show `LSP Tunnel labeling not enabled` instead of `LSP Tunnel labeling enabled`.
4. Check P1 running config: `show running-config | include traffic-eng` — the global `mpls traffic-eng tunnels` command is missing. Without it, P1 drops RSVP PATH messages silently.
</details>

<details>
<summary>Click to view Fix</summary>

On P1:
```bash
mpls traffic-eng tunnels
```

The single global command re-enables TE on P1. All previously-configured per-interface `mpls traffic-eng tunnels` settings become active. RSVP PATH messages now pass through P1, RESV returns, and Tunnel10 re-establishes within seconds.

Verify: `show ip rsvp interface` on P1 shows all three core interfaces listed. `show mpls traffic-eng tunnels tunnel10` shows `Oper: up`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `mpls traffic-eng tunnels` configured globally on PE1, P1, P2, PE2
- [ ] `mpls traffic-eng tunnels` configured on every core-facing interface (L2–L6, both endpoints)
- [ ] `mpls traffic-eng level-2` and `mpls traffic-eng router-id Loopback0` configured on PE1, P1, P2, PE2
- [ ] `show mpls traffic-eng topology` shows all 4 core nodes with bandwidth attributes
- [ ] `ip rsvp bandwidth 100000 100000` on all 5 core links (L2–L6), both endpoints
- [ ] `show ip rsvp interface` shows 100,000 kbps on all core-facing interfaces
- [ ] Tunnel10 UP with dynamic path-option 10 and `autoroute announce` — `show ip route 10.0.0.4` exits via Tunnel10
- [ ] Tunnel20 UP with explicit path `PE1-via-P2` — ERO confirms P2 transit
- [ ] `traceroute 10.0.0.4` from PE1 shows `[MPLS: Label]` on hop 1, confirming RSVP-TE tunnel forwarding
- [ ] CE1-to-CE2 ping (192.0.2.1 → 198.51.100.1) succeeds

### Troubleshooting

- [ ] Ticket 1 resolved: Tunnel20 restored after RSVP bandwidth corrected on L3 (PE1 Gi0/2)
- [ ] Ticket 2 resolved: Tunnel20 restored after IS-IS TE extensions re-added on P2
- [ ] Ticket 3 resolved: Tunnel10 restored after `mpls traffic-eng tunnels` re-added globally on P1

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed | Inject scripts only |
