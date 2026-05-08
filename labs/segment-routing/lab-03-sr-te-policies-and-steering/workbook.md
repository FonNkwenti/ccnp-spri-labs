# Lab 03: SR-TE Policies, Constraints, and Automated Steering

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

**Exam Objective:** 4.3.a (Configure and verify SR-TE policies), 4.3.b (Implement SR-TE traffic steering) — Topic: Segment Routing Traffic Engineering

This lab introduces SR Traffic Engineering (SR-TE) on IOS-XRv 9000. You will build SR-TE policies that control the path data-plane traffic takes through the SR-MPLS core — going beyond IGP shortest-path to enforce operator-defined routing intent. By the end of this lab, you will have configured dynamic and explicit SR-TE policies, applied affinity-based path constraints, and enabled color-based automated steering so that BGP prefixes self-select their SR-TE path based on an extended community.

### SR-TE Policy Architecture

An SR-TE policy is a named, local construct on a headend router (the ingress PE). Each policy identifies a **color** (a 32-bit value) and an **end-point** (the egress PE's loopback address). The policy says: "when steering traffic toward this endpoint using this color, use this specific path through the SR domain."

A policy contains one or more **candidate paths**, each with a preference (higher preference wins). A candidate path is either:
- **Dynamic** — the headend runs local CSPF (Constrained Shortest Path First) over the TE topology database to compute the best SID list automatically. Constraints such as metric type, bandwidth, and affinity are applied during CSPF.
- **Explicit** — the operator supplies a fixed ordered list of SIDs (node SIDs or adjacency SIDs). The headend imposes exactly this label stack, bypassing CSPF.

```
segment-routing
 traffic-eng
  segment-list EXPLICIT_R4_R3         ← reusable named SID list
   index 10 address ipv4 10.0.0.4     ← node SID: route via R4 (label 16004)
   index 20 address ipv4 10.0.0.3     ← node SID: exit at R3  (label 16003)
  !
  policy COLOR_10
   color 10 end-point ipv4 10.0.0.3   ← matches color:10, heading to R3
   candidate-paths
    preference 200                     ← higher pref wins when UP
     explicit segment-list EXPLICIT_R4_R3
    !
    preference 100
     dynamic
      metric type igp                  ← CSPF minimizes IGP metric sum
     !
    !
   !
  !
```

> **Node SIDs vs adjacency SIDs in segment-lists:** Node SIDs (a router's loopback, resolved to its prefix-SID label) are preferred in explicit segment-lists because they survive single link failures — TI-LFA still protects the hop toward that node. Adjacency SIDs lock to one specific link and fail if that link goes down.

### Candidate Paths and Preferences

When multiple candidate paths are configured, IOS-XR installs the active path with the **highest preference** that is currently valid (its SID list resolves end-to-end). If the primary fails (e.g., a link in the explicit SID list becomes unreachable), the router falls back to the next lower preference automatically. This creates a resilient failover model without requiring external control.

| State | Meaning |
|-------|---------|
| UP | Active candidate path selected; traffic is being steered |
| INACTIVE | A candidate path that lost to a higher preference |
| DOWN | SID list cannot be resolved (unreachable node or constraint violated) |

### Affinity Constraints and Affinity-Map

Affinity (also called administrative group or link-coloring) is a mechanism to tag links with user-defined attributes and then include or exclude those tagged links from CSPF path computation. It is a policy control: instead of raising the IGP metric on a link, you assign it a color and tell the policy to avoid that color.

**Configuration pattern (IOS-XR):**

Step 1 — Define the global affinity map (consistent across all SR-TE capable nodes):
```
segment-routing
 traffic-eng
  affinity-map
   name RED  bit-position 0   ← bit 0 in the affinity bitmask
   name BLUE bit-position 1   ← bit 1 in the affinity bitmask
```

Step 2 — Tag interfaces on both endpoints of a link:
```
segment-routing
 traffic-eng
  interface GigabitEthernet0/0/0/1
   affinity
    name RED
```

Step 3 — Reference the affinity in a candidate path constraint:
```
  policy COLOR_20
   ...
    dynamic
     metric type igp
     constraints
      affinity
       exclude-any
        name RED      ← CSPF will not use any link tagged RED
```

> **Both endpoints must carry the affinity tag.** IS-IS TE floods affinity bits in Extended IS Reachability TLV sub-TLVs. CSPF reads both the local and remote endpoint's affinity. If only one end is tagged, the constraint enforcement is inconsistent — a classic misconfiguration ticket.

### Color-Based Automated Steering (On-Demand Next-Hop / ODN)

Manual SR-TE policies bind a headend router to specific prefixes via static configuration. **Automated steering** uses BGP extended communities to dynamically map prefixes to SR-TE policies — without statically listing each prefix.

When a BGP prefix carries the **color extended community** (type 0x030B, RFC 9012), the receiving router matches that color value to an SR-TE policy (or ODN template) with the same color and the BGP next-hop as the end-point. If a match exists, the prefix is steered into the SR-TE policy automatically.

```
Color extended community format: color:<value>
Example: color:10  → value 10 → matches policy with color 10

Flow:
CE2 announces 198.51.100.0/24 via eBGP to R3 (egress PE)
R3's inbound route-policy attaches color:10 (IOS-XR RPL):
  extcommunity-set opaque COLOR_10
   10
  end-set
  route-policy RP_CE2_IN
   set extcommunity color COLOR_10 additive
   pass
  end-policy
R3 advertises 198.51.100.0/24 with color:10 to R1 via iBGP
R1's on-demand color 10 template matches → instantiates SR-TE policy
R1 steers traffic to 198.51.100.0/24 into the color:10 SR-TE path
```

> **IOSv limitation:** IOSv 15.9 (CE devices in this lab) does NOT support `set extcommunity color` — that command is an IOS-XR RPL extension. In real SP deployments, the PE (R3, which is IOS-XR) is always responsible for attaching the color community, not the CE. This lab follows that operational model exactly.

### IOS-XR TE Metric vs IGP Metric

IOS-XR SR-TE supports two metric types for CSPF:

| Metric Type | Source | Config |
|-------------|--------|--------|
| `igp` | IS-IS link metric (default, same as routing metric) | `dynamic metric type igp` |
| `te` | Separate TE administrative weight per interface | `dynamic metric type te` |

To set a TE administrative weight on an interface in IOS-XR (note: this is NOT the IOS-XE syntax `mpls traffic-eng administrative-weight`):

```
segment-routing
 traffic-eng
  interface GigabitEthernet0/0/0/0
   metric 1000    ← TE metric override; IGP metric is unchanged
```

IS-IS must advertise TE extensions for CSPF to read these TE metrics. This requires `mpls traffic-eng level-2-only` and `mpls traffic-eng router-id Loopback0` under the IS-IS address-family — both pre-loaded in this lab's initial-configs.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| SR-TE policy configuration | Build dynamic and explicit candidate paths with color and end-point |
| Affinity constraint enforcement | Tag links with affinity names; exclude them from CSPF |
| Explicit segment-list design | Compose node-SID-based segment-lists for deterministic paths |
| Color-based automated steering | Use BGP color extended communities to dynamically bind prefixes to SR-TE paths |
| ODN template configuration | Configure on-demand color templates for dynamic policy instantiation |
| TE metric tuning | Override per-interface TE weight to influence CSPF path selection |
| SR-TE troubleshooting | Diagnose policy-down states, missing color communities, and affinity misconfiguration |

---

## 2. Topology & Scenario

**Scenario:** TelSP's engineering team has completed the SR-MPLS migration (lab-02). The next project is SR Traffic Engineering: using the SR label stack to force traffic onto specific paths rather than following the IGP shortest path. Two customer edges have now been added — CE1 (AS 65101) announcing `192.0.2.0/24` and CE2 (AS 65102) announcing `198.51.100.0/24`. The SP needs to steer CE1→CE2 traffic via different core paths depending on the traffic class: low-latency (via R3 direct) and high-capacity (via R4 transit). BGP color communities will carry the steering intent automatically.

**Note:** R1's mapping server from lab-02 is removed at startup via the teardown block in R1's initial-config. CE1 is now the real owner of `192.0.2.0/24`, which eliminates the conflict.

```
                   ┌──────────────────────┐
                   │        CE1           │
                   │     (AS 65101)       │
                   │  Lo0: 10.0.0.11/32   │
                   │  Lo1: 192.0.2.1/24   │
                   └────────┬─────────────┘
                      Gi0/0 │ 10.1.11.11/24
                            │ L7 — 10.1.11.0/24
                  Gi0/0/0/3 │ 10.1.11.1/24
          ┌─────────────────┴────────────────────────────┐
          │                    R1                         │
          │           (SP Edge / Ingress PE)              │
          │           Lo0: 10.0.0.1/32  SID: 16001       │
          └──┬──────────────────────┬────────────────┬───┘
   Gi0/0/0/0 │ 10.1.12.1/24  Gi0/0/0/1│ 10.1.14.1/24 │ Gi0/0/0/2
      L1     │               L4       │               │ 10.1.13.1/24
  10.1.12.0/24│           10.1.14.0/24│            L5 │ 10.1.13.0/24
             │                        │    (diagonal)  │
   10.1.12.2 │ Gi0/0/0/0   10.1.14.4 │ Gi0/0/0/1      │ 10.1.13.3 Gi0/0/0/2
  ┌──────────┴───────┐  ┌─────────────┴────────┐        │
  │       R2          │  │        R4             │        │
  │    (SP Core)      │  │     (SP Core)         │        │
  │ Lo0:10.0.0.2/32   │  │  Lo0:10.0.0.4/32      │        │
  │   SID: 16002      │  │    SID: 16004          │        │
  └──────┬────────────┘  └────────────┬──────────┘        │
  Gi0/0/0/1 │ 10.1.23.2  Gi0/0/0/0 │ 10.1.34.4           │
       L2   │               L3      │                      │
  10.1.23.0/24│         10.1.34.0/24│                      │
             │                      │                      │
  10.1.23.3  │ Gi0/0/0/0  10.1.34.3 │ Gi0/0/0/1            │
  ┌──────────┴──────────────────────┴──────────────────────┴───┐
  │                             R3                              │
  │                   (SP Edge / Egress PE)                     │
  │                   Lo0: 10.0.0.3/32  SID: 16003             │
  └─────────────────────────┬───────────────────────────────────┘
                   Gi0/0/0/3│ 10.1.33.3/24
                             │ L8 — 10.1.33.0/24
                       Gi0/0 │ 10.1.33.12/24
                   ┌─────────┴──────────────┐
                   │        CE2             │
                   │     (AS 65102)         │
                   │  Lo0: 10.0.0.12/32     │
                   │  Lo1: 198.51.100.1/24  │
                   └────────────────────────┘
```

**Link summary:**

| Link ID | Endpoints | Subnet | Purpose |
|---------|-----------|--------|---------|
| L1 | R1 Gi0/0/0/0 ↔ R2 Gi0/0/0/0 | 10.1.12.0/24 | SP core, SR-MPLS + LDP |
| L2 | R2 Gi0/0/0/1 ↔ R3 Gi0/0/0/0 | 10.1.23.0/24 | SP core; BLUE affinity |
| L3 | R3 Gi0/0/0/1 ↔ R4 Gi0/0/0/0 | 10.1.34.0/24 | SP core; RED affinity |
| L4 | R1 Gi0/0/0/1 ↔ R4 Gi0/0/0/1 | 10.1.14.0/24 | Ring closer, TI-LFA alternate |
| L5 | R1 Gi0/0/0/2 ↔ R3 Gi0/0/0/2 | 10.1.13.0/24 | Diagonal; TI-LFA PQ anchor |
| L7 | R1 Gi0/0/0/3 ↔ CE1 Gi0/0 | 10.1.11.0/24 | eBGP PE-CE (new in lab-03) |
| L8 | R3 Gi0/0/0/3 ↔ CE2 Gi0/0 | 10.1.33.0/24 | eBGP PE-CE (new in lab-03) |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | SP Edge / Ingress PE | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R2 | SP Core | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R3 | SP Edge / Egress PE | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| R4 | SP Core | IOS-XRv 9000 | xrv9k-fullk9-x.vrr-7.3.2 |
| CE1 | Customer Edge (AS 65101) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |
| CE2 | Customer Edge (AS 65102) | IOSv | vios-adventerprisek9-m.SPA.156-2.T |

### Loopback Addresses

| Device | Interface | Address/Prefix | Purpose |
|--------|-----------|----------------|---------|
| R1 | Loopback0 | 10.0.0.1/32 | Router ID, iBGP source, SR-TE end-point |
| R2 | Loopback0 | 10.0.0.2/32 | Router ID, IS-IS passive |
| R3 | Loopback0 | 10.0.0.3/32 | Router ID, iBGP source, SR-TE end-point |
| R4 | Loopback0 | 10.0.0.4/32 | Router ID, IS-IS passive |
| CE1 | Loopback0 | 10.0.0.11/32 | CE router ID |
| CE1 | Loopback1 | 192.0.2.1/24 | Customer prefix advertised via eBGP |
| CE2 | Loopback0 | 10.0.0.12/32 | CE router ID |
| CE2 | Loopback1 | 198.51.100.1/24 | Customer prefix steered via SR-TE |

### Cabling

| Link | Device A | Interface | IP Address | Device B | Interface | IP Address |
|------|----------|-----------|------------|----------|-----------|------------|
| L1 | R1 | Gi0/0/0/0 | 10.1.12.1/24 | R2 | Gi0/0/0/0 | 10.1.12.2/24 |
| L2 | R2 | Gi0/0/0/1 | 10.1.23.2/24 | R3 | Gi0/0/0/0 | 10.1.23.3/24 |
| L3 | R3 | Gi0/0/0/1 | 10.1.34.3/24 | R4 | Gi0/0/0/0 | 10.1.34.4/24 |
| L4 | R1 | Gi0/0/0/1 | 10.1.14.1/24 | R4 | Gi0/0/0/1 | 10.1.14.4/24 |
| L5 | R1 | Gi0/0/0/2 | 10.1.13.1/24 | R3 | Gi0/0/0/2 | 10.1.13.3/24 |
| L7 | R1 | Gi0/0/0/3 | 10.1.11.1/24 | CE1 | Gi0/0 | 10.1.11.11/24 |
| L8 | R3 | Gi0/0/0/3 | 10.1.33.3/24 | CE2 | Gi0/0 | 10.1.33.12/24 |

### Advertised Prefixes

| Device | Prefix | Protocol | Notes |
|--------|--------|----------|-------|
| CE1 | 192.0.2.0/24 | eBGP → R1 → iBGP → R3 | Customer ingress prefix; sourced from CE1 Loopback1 |
| CE2 | 198.51.100.0/24 | eBGP → R3 → iBGP (with color:10) → R1 | Steered prefix; R3 attaches color:10 community |

### Console Access

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| CE2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py`:

**IS pre-loaded:**
- Hostnames on all devices
- Interface IP addressing on all routed links and loopbacks (including L7 and L8)
- IS-IS Level-2 process on R1–R4 with wide metrics and SR-MPLS forwarding
- IS-IS TE extensions (required for CSPF affinity and TE-metric computation)
- Prefix SIDs: R1=index 1 (16001), R2=index 2 (16002), R3=index 3 (16003), R4=index 4 (16004)
- TI-LFA fast-reroute on all core IS-IS interfaces
- BFD on all core IS-IS interfaces
- LDP on all core interfaces (coexistence from lab-02)
- SR-prefer under IS-IS (SR labels win over LDP labels for SP prefixes)
- Global SRGB 16000–23999
- Mapping server **removed** from R1 (teardown block at top of R1 initial-config)
- CE1 and CE2 IP addressing on loopbacks and uplinks

**IS NOT pre-loaded** (student configures this):
- eBGP sessions between R1↔CE1 and R3↔CE2
- iBGP session between R1 and R3
- Opaque extended community set and route policies on R1 and R3
- SR-TE global affinity-map on R1–R4
- Interface affinity tagging (RED on L3, BLUE on L2)
- SR-TE segment-lists and named policies
- ODN (on-demand color) templates
- SR-TE interface TE metric overrides

---

## 5. Lab Challenge: Core Implementation

### Task 1: Bring Up BGP Sessions and Customer Prefixes

- Boot CE1 and CE2 nodes in EVE-NG and wait for IOS boot (approximately 3 minutes).
- Establish eBGP sessions: R1 as AS 65100 peering with CE1 (AS 65101) over L7 using the directly connected link addresses; R3 as AS 65100 peering with CE2 (AS 65102) over L8 using the directly connected link addresses.
- Establish an iBGP session between R1 and R3 within AS 65100, sourced from their Loopback0 interfaces.
- Configure CE1 to originate `192.0.2.0/24` into BGP using a network statement.
- Configure CE2 to originate `198.51.100.0/24` into BGP using a network statement.
- Apply a pass-through inbound route policy on R1 for iBGP prefixes received from R3. Apply a pass-through inbound route policy on R1 for eBGP prefixes received from CE1. Apply a pass-through inbound route policy on R3 for iBGP prefixes received from R1.

**Verification:** `show bgp summary` on R1 must show two established sessions (one to R3, one to 10.1.11.11). `show bgp ipv4 unicast` on R1 must show both `192.0.2.0/24` and `198.51.100.0/24` in the BGP table.

---

### Task 2: Build a Dynamic SR-TE Policy with IGP Metric

- Define a global affinity-map on R1 with two names: `RED` at bit-position 0 and `BLUE` at bit-position 1. (This is required for subsequent tasks — configure it now for consistency.)
- On R1, configure a named SR-TE policy called `COLOR_10` with color value `10` and end-point `10.0.0.3` (R3's loopback).
- Add a single candidate path at preference 100 using dynamic CSPF with IGP metric.
- Verify the policy comes up and CSPF has computed a SID list toward R3.

**Verification:** `show segment-routing traffic-eng policy color 10` on R1 must show the policy as `UP` with an active SID list. The SID list should reflect the IGP shortest path to R3 (via L5 direct, label 16003, or L1+L2 via R2, labels 16002+16003).

---

### Task 3: Add an Explicit Segment-List at Higher Preference

- Define a named segment-list called `EXPLICIT_R4_R3` on R1. The list must contain exactly two entries: first, the node SID for R4 (`10.0.0.4`), and second, the node SID for R3 (`10.0.0.3`). This forces the path R1→R4→R3.
- Add a second candidate path to `COLOR_10` at preference 200, referencing `EXPLICIT_R4_R3` as an explicit path.
- Confirm that preference 200 (explicit) is now active and preference 100 (dynamic) becomes inactive.

**Verification:** `show segment-routing traffic-eng policy color 10` must show preference 200 as the active candidate path with a SID list of `[16004, 16003]`. Preference 100 must show as INACTIVE. Run `traceroute mpls ipv4 10.0.0.3/32 source 10.0.0.1` from R1 to confirm the path visits R4 as a transit hop.

---

### Task 4: Constrained Path with Affinity Exclusion

- On R1, R2, R3, and R4, configure the global affinity-map with the same two names defined in Task 2 (`RED` at bit-position 0, `BLUE` at bit-position 1). The affinity-map must be identical on all nodes for CSPF to honor constraints correctly.
- Tag L3 (R3↔R4) with the `RED` affinity on both endpoints: R3's Gi0/0/0/1 and R4's Gi0/0/0/0.
- Tag L2 (R2↔R3) with the `BLUE` affinity on both endpoints: R2's Gi0/0/0/1 and R3's Gi0/0/0/0.
- On R1, define a new SR-TE policy called `COLOR_20` with color value `20` and end-point `10.0.0.3`.
- Add a dynamic candidate path at preference 100 with IGP metric and an `exclude-any` affinity constraint that excludes links tagged `RED`.
- Verify that CSPF avoids L3 (the R3↔R4 link) even though it may be part of the IGP shortest path. The SID list must route via L1+L2 (R1→R2→R3) or via L5 (R1→R3 diagonal) — not via R4.

**Verification:** `show segment-routing traffic-eng policy color 20` on R1 must show the policy UP. The active SID list must NOT contain label 16004 (R4's SID). Compare to `show isis route 10.0.0.3/32` to confirm the IGP shortest path would have used R4 — the constraint is overriding it.

---

### Task 5: SR-TE Policy with TE Metric

- On R1, define a new SR-TE policy called `COLOR_30` with color value `30` and end-point `10.0.0.3`.
- Add a dynamic candidate path at preference 100 using TE metric instead of IGP metric.
- To demonstrate TE metric influence, set the TE metric on R1's Gi0/0/0/0 (the L1 link toward R2) to `1000`. This makes the R1→R2 TE cost very high without changing the IGP routing metric.
- Observe that `COLOR_30` now avoids L1 (since the TE cost is high) and selects a different path compared to `COLOR_10`.

> **Syntax note for IOS-XR:** The TE metric override is configured under `segment-routing / traffic-eng / interface <name> / metric <value>`. This is different from the IOS-XE syntax (`mpls traffic-eng / interface <name> / administrative-weight <value>`). The IOS-XR command sets the metric used by local CSPF only — it does not change the IS-IS IGP metric.

**Verification:** `show segment-routing traffic-eng policy color 30` must show the policy UP with a SID list that avoids the R1→R2 hop (no label 16002 as the first SID). Compare the SID list to `COLOR_10` (which uses IGP metric and may go via R2). `show segment-routing traffic-eng topology` on R1 will show the TE link attributes including the overridden metric.

---

### Task 6: Color-Based Automated Steering

- On R3, define an opaque extended community set named `COLOR_10` with value `10`.
- On R3, create a route policy `RP_CE2_IN` that attaches the `COLOR_10` opaque extended community to all prefixes received from CE2 and passes them. Apply this policy as the inbound route policy for the eBGP session with CE2.
- On R1, configure an on-demand color `10` template under `segment-routing traffic-eng`. Use a dynamic candidate path with IGP metric. This template tells IOS-XR: "when a BGP prefix arrives with color:10 and a next-hop that is reachable, instantiate an SR-TE policy automatically."
- Create an opaque extended community set named `COLOR_10` with value `10` on R1 as well (needed for route-policy matching).
- Create a pass-through inbound route policy for R1's iBGP session with R3 (`RP_R3_IN`) and apply it. This policy must NOT strip or modify extended communities — the color must pass through intact.
- Verify that `198.51.100.0/24` arrives at R1 with the `color:10` extended community, and that R1 automatically creates an SR-TE policy to steer traffic into it.

**Verification:**
- `show bgp ipv4 unicast 198.51.100.0/24` on R1 must show `Extended Community: Color:10 RT:...` in the attributes.
- `show segment-routing traffic-eng policy` on R1 must show a dynamically instantiated ODN policy (named `srte_c_10_ep_10.0.0.3` or similar) in addition to the static `COLOR_10` policy.
- `traceroute 198.51.100.1 source 192.0.2.1` from CE1 must show the path traversing the SR-TE SID stack.

---

### Task 7: Dual-Preference Resilience

- Add a second candidate path to the static `COLOR_10` policy on R1 at preference 50. This lower-preference path should use a different explicit segment-list or dynamic computation as a backup. For this task, configure preference 50 as a dynamic path using IGP metric (this ensures it will always resolve, unlike the explicit path which could be broken by a specific link failure).
- Verify that preference 200 (explicit EXPLICIT_R4_R3) is active, preference 100 (dynamic IGP) is inactive, and preference 50 (dynamic IGP backup) is also inactive — multiple inactive fallbacks are valid.
- Shut the L4 link (R1 Gi0/0/0/1 or R4 Gi0/0/0/1) to simulate the explicit path becoming invalid. Observe the policy fall back to the next valid preference.

**Verification:** While L4 is shut, `show segment-routing traffic-eng policy color 10` must show preference 200 as DOWN and preference 100 as active. Re-enable L4 and confirm preference 200 becomes active again within ~30 seconds (CSPF re-evaluation interval).

---

## 6. Verification & Analysis

### Task 1 Verification: BGP Sessions

```
R1# show bgp summary
BGP router identifier 10.0.0.1, local AS number 65100
...
Neighbor        Spk    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.0.0.3          0 65100      45      45       15    0    0 00:12:34          1  ! ← iBGP to R3, 1 prefix received
10.1.11.11        0 65101      30      30       15    0    0 00:10:22          1  ! ← eBGP to CE1, 1 prefix received

R1# show bgp ipv4 unicast
Network          Next Hop        Metric LocPrf Weight Path
*> 192.0.2.0/24   10.1.11.11           0      0      0 65101 i   ! ← CE1's prefix, best path
*>i198.51.100.0/24 10.0.0.3             0    100      0 65102 i   ! ← CE2's prefix via R3 iBGP (i = iBGP)
```

### Task 2 Verification: Dynamic SR-TE Policy (color 10)

```
R1# show segment-routing traffic-eng policy color 10
SR-TE policy database
Color: 10, End-point: 10.0.0.3
  Name: COLOR_10
  Status:
    Admin: up  Oper: up for 00:05:30 (since ...)    ! ← policy is UP
  Candidate-paths:
    Preference: 100 (configuration) (active)         ! ← preference 100 is active
      Name: COLOR_10-100
      Requested BSID: dynamic
      Constraints:
        Protection Type: protected-preferred
        Maximum SID Depth: 10
      Dynamic (valid)
        Metric Type: IGP,   Path Accumulated Metric: 10
        SID[0]: 16003  ! ← label 16003 = R3's prefix SID
                            ! verify this is the direct L5 path (one hop)
                            ! or 16002/16003 for the R2 path (two hops)
```

### Task 3 Verification: Explicit SID List Active

```
R1# show segment-routing traffic-eng policy color 10
  Candidate-paths:
    Preference: 200 (configuration) (active)         ! ← explicit path wins
      Name: COLOR_10-200
      Explicit: segment-list EXPLICIT_R4_R3 (valid)
        Metric Type: None
        SID[0]: 16004  ! ← R4's node SID (forces R1 → R4 hop)
        SID[1]: 16003  ! ← R3's node SID (forces R4 → R3 hop)
    Preference: 100 (configuration) (inactive)       ! ← lost to higher preference
```

```
R1# traceroute mpls ipv4 10.0.0.3/32 source 10.0.0.1
...
 1  10.1.14.4 [MPLS: Labels 16004/16003 Exp 0]   ! ← R4 is transit, label stack pushed
 2  10.1.34.3 [MPLS: Label 3 Exp 0]              ! ← R3 pops (PHP/implicit-null)
 3  10.0.0.3
```

### Task 4 Verification: Affinity Constraint

```
R1# show segment-routing traffic-eng policy color 20
  Candidate-paths:
    Preference: 100 (configuration) (active)
      Dynamic (valid)
        Metric Type: IGP,   Path Accumulated Metric: 20
        SID[0]: 16002   ! ← R2 (L1→L2 path via R2, avoids RED-tagged L3/R4)
        SID[1]: 16003   ! ← R3 exit
                        ! confirm: label 16004 (R4) does NOT appear here
```

Confirm that `show isis route 10.0.0.3/32` on R1 shows the IGP shortest path going via R4 (the constraint is indeed overriding it):
```
R1# show isis ipv4 unicast topology 0.0.0.3
...
10.0.0.3/32  Metric: 20 IS-IS level-2
   via 10.1.14.4, GigabitEthernet0/0/0/1, R4    ! ← IGP would use R4
```
The COLOR_20 SID list does not use R4 — the `exclude-any RED` constraint is enforced.

### Task 5 Verification: TE Metric Policy

```
R1# show segment-routing traffic-eng topology
...
  Link[0]:
    Local: 10.1.12.1 (GigabitEthernet0/0/0/0)
    Remote: 10.1.12.2
    Admin Weight (TE): 1000    ! ← overridden TE metric on L1
    Admin Weight (IGP): 10     ! ← IGP metric unchanged
```

```
R1# show segment-routing traffic-eng policy color 30
  Candidate-paths:
    Preference: 100 (configuration) (active)
      Dynamic (valid)
        Metric Type: TE, Path Accumulated Metric: ...
        SID[0]: 16003   ! ← direct L5 path (TE cost lower than going via R2 on L1)
                        ! COLOR_30 avoids L1 (TE cost=1000) while COLOR_10 uses it
```

### Task 6 Verification: Automated Steering

```
R1# show bgp ipv4 unicast 198.51.100.0/24
BGP routing table entry for 198.51.100.0/24
  ...
  Extended Community: Color:10 0x0000000a   ! ← color:10 community present
  ...
  Nexthop: 10.0.0.3                         ! ← iBGP next-hop is R3's loopback
  SR-TE policy:
    Color: 10, Endpoint: 10.0.0.3
    Policy Status: Active                    ! ← ODN policy is steering this prefix
```

```
R1# show segment-routing traffic-eng policy
...
  Name: srte_c_10_ep_10.0.0.3 (Color: 10, End-point: 10.0.0.3)  ! ← ODN-instantiated
    Status: UP
    Admin: up  Oper: up
```

### Task 7 Verification: Dual Preferences

```
R1# show segment-routing traffic-eng policy color 10
  Candidate-paths:
    Preference: 200 (configuration) (active)      ! ← explicit R4_R3 path wins
    Preference: 100 (configuration) (inactive)    ! ← dynamic IGP, standby
    Preference: 50  (configuration) (inactive)    ! ← dynamic IGP backup, standby

! After shutting L4 (R1-R4 link):
    Preference: 200 (configuration) (down)        ! ← SID 16004 unresolvable via R4
    Preference: 100 (configuration) (active)      ! ← dynamic falls back to L5 or L1-L2
    Preference: 50  (configuration) (inactive)
```

---

## 7. Verification Cheatsheet

### BGP Session Verification

```
show bgp summary
show bgp ipv4 unicast
show bgp ipv4 unicast <prefix>
show bgp ipv4 unicast neighbors <ip> advertised-routes
show bgp ipv4 unicast neighbors <ip> received-routes
```

| Command | What to Look For |
|---------|-----------------|
| `show bgp summary` | All neighbors in `Established` state (non-idle St column) |
| `show bgp ipv4 unicast` | `192.0.2.0/24` and `198.51.100.0/24` present with `>` best-path marker |
| `show bgp ipv4 unicast <prefix>` | `Extended Community: Color:10` for the steered prefix |

> **Exam tip:** In IOS-XR, iBGP carries extended communities by default — no `send-community extended` is needed on iBGP neighbors.

### SR-TE Policy Verification

```
show segment-routing traffic-eng policy
show segment-routing traffic-eng policy color <N>
show segment-routing traffic-eng policy name <NAME>
```

| Command | What to Look For |
|---------|-----------------|
| `show segment-routing traffic-eng policy` | All policies listed; each must show `Oper: up` |
| `show segment-routing traffic-eng policy color 10` | Active candidate path, valid SID list |
| `show segment-routing traffic-eng policy color 20` | SID list must NOT contain label 16004 (R4) |

### Affinity and TE Topology

```
show segment-routing traffic-eng topology
show segment-routing traffic-eng topology detail
```

| Command | What to Look For |
|---------|-----------------|
| `show segment-routing traffic-eng topology` | Each link shows `Admin Weight (TE)` and affinity bits |
| `show segment-routing traffic-eng topology detail` | Per-link affinity bitmask populated from IS-IS TE |

### Color-Based Automated Steering

```
show segment-routing traffic-eng policy
show bgp ipv4 unicast <prefix>
show route ipv4 <prefix> detail
```

| Command | What to Look For |
|---------|-----------------|
| `show bgp ipv4 unicast 198.51.100.0/24` | `Extended Community: Color:10` present |
| `show segment-routing traffic-eng policy` | ODN policy `srte_c_10_ep_10.0.0.3` is UP |
| `show route ipv4 198.51.100.0/24 detail` | Next-hop shows SR-TE label stack, not plain IGP |

### Explicit Segment-List

```
show segment-routing traffic-eng segment-list
```

| Command | What to Look For |
|---------|-----------------|
| `show segment-routing traffic-eng segment-list` | `EXPLICIT_R4_R3` listed with SIDs 16004 and 16003, both `Resolved` |

### Common SR-TE Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Policy stays DOWN | End-point not reachable in CSPF TE topology; missing IS-IS TE extensions |
| Explicit SID list shows `UNRESOLVED` | One of the node loopbacks is unreachable via IS-IS |
| `COLOR_20` SID list contains label 16004 | Affinity-map not configured on R3 or R4; RED affinity missing from one endpoint of L3 |
| BGP prefix missing `Color:10` at R1 | RP_CE2_IN on R3 not attached or missing `set extcommunity` action |
| ODN policy not instantiated | `on-demand color 10` template not configured; or `RP_R3_IN` strips the color community |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 1: BGP Sessions

<details>
<summary>Click to view R1 BGP Configuration</summary>

```bash
! R1 — route policies and BGP
extcommunity-set opaque COLOR_10
 10
end-set
!
route-policy PASS
 pass
end-policy
!
route-policy RP_CE1_IN
 pass
end-policy
!
route-policy RP_R3_IN
 pass
end-policy
!
router bgp 65100
 bgp router-id 10.0.0.1
 address-family ipv4 unicast
 !
 neighbor 10.0.0.3
  remote-as 65100
  update-source Loopback0
  description iBGP to R3
  address-family ipv4 unicast
   route-policy RP_R3_IN in
   route-policy PASS out
  !
 !
 neighbor 10.1.11.11
  remote-as 65101
  description eBGP to CE1
  address-family ipv4 unicast
   route-policy RP_CE1_IN in
   route-policy PASS out
  !
 !
!
```
</details>

<details>
<summary>Click to view R3 BGP Configuration</summary>

```bash
! R3 — route policies and BGP
extcommunity-set opaque COLOR_10
 10
end-set
!
route-policy PASS
 pass
end-policy
!
route-policy RP_CE2_IN
 set extcommunity color COLOR_10 additive
 pass
end-policy
!
router bgp 65100
 bgp router-id 10.0.0.3
 address-family ipv4 unicast
 !
 neighbor 10.0.0.1
  remote-as 65100
  update-source Loopback0
  description iBGP to R1
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
  !
 !
 neighbor 10.1.33.12
  remote-as 65102
  description eBGP to CE2
  address-family ipv4 unicast
   route-policy RP_CE2_IN in
   route-policy PASS out
  !
 !
!
```
</details>

<details>
<summary>Click to view CE1 BGP Configuration</summary>

```bash
! CE1 (IOSv)
router bgp 65101
 bgp router-id 10.0.0.11
 bgp log-neighbor-changes
 neighbor 10.1.11.1 remote-as 65100
 !
 address-family ipv4
  neighbor 10.1.11.1 activate
  network 192.0.2.0 mask 255.255.255.0
 exit-address-family
!
```
</details>

<details>
<summary>Click to view CE2 BGP Configuration</summary>

```bash
! CE2 (IOSv)
router bgp 65102
 bgp router-id 10.0.0.12
 bgp log-neighbor-changes
 neighbor 10.1.33.3 remote-as 65100
 !
 address-family ipv4
  neighbor 10.1.33.3 activate
  network 198.51.100.0 mask 255.255.255.0
 exit-address-family
!
```
</details>

### Objective 2: Dynamic SR-TE Policy (color 10, IGP metric)

<details>
<summary>Click to view R1 SR-TE Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  affinity-map
   name RED bit-position 0
   name BLUE bit-position 1
  !
  policy COLOR_10
   color 10 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      metric type igp
     !
    !
   !
  !
 !
!
```
</details>

### Objective 3: Explicit Segment-List at Preference 200

<details>
<summary>Click to view R1 Explicit SID List Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  segment-list EXPLICIT_R4_R3
   index 10 address ipv4 10.0.0.4
   index 20 address ipv4 10.0.0.3
  !
  policy COLOR_10
   color 10 end-point ipv4 10.0.0.3
   candidate-paths
    preference 200
     explicit segment-list EXPLICIT_R4_R3
    !
    preference 100
     dynamic
      metric type igp
     !
    !
   !
  !
 !
!
```
</details>

### Objective 4: Affinity-Constrained Path (color 20)

<details>
<summary>Click to view Affinity Configuration on All Nodes</summary>

```bash
! R2 — BLUE on L2 (Gi0/0/0/1 toward R3)
segment-routing
 traffic-eng
  affinity-map
   name RED bit-position 0
   name BLUE bit-position 1
  !
  interface GigabitEthernet0/0/0/1
   affinity
    name BLUE
   !
  !
 !
!

! R3 — BLUE on L2 (Gi0/0/0/0 toward R2); RED on L3 (Gi0/0/0/1 toward R4)
segment-routing
 traffic-eng
  affinity-map
   name RED bit-position 0
   name BLUE bit-position 1
  !
  interface GigabitEthernet0/0/0/0
   affinity
    name BLUE
   !
  !
  interface GigabitEthernet0/0/0/1
   affinity
    name RED
   !
  !
 !
!

! R4 — RED on L3 (Gi0/0/0/0 toward R3)
segment-routing
 traffic-eng
  affinity-map
   name RED bit-position 0
   name BLUE bit-position 1
  !
  interface GigabitEthernet0/0/0/0
   affinity
    name RED
   !
  !
 !
!

! R1 — COLOR_20 policy with exclude-any RED
segment-routing
 traffic-eng
  policy COLOR_20
   color 20 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      metric type igp
      constraints
       affinity
        exclude-any
         name RED
        !
       !
      !
     !
    !
   !
  !
 !
!
```
</details>

### Objective 5: TE Metric Policy (color 30)

<details>
<summary>Click to view R1 TE Metric Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  interface GigabitEthernet0/0/0/0
   metric 1000
  !
  policy COLOR_30
   color 30 end-point ipv4 10.0.0.3
   candidate-paths
    preference 100
     dynamic
      metric type te
     !
    !
   !
  !
 !
!
```
</details>

### Objective 6: Color-Based Automated Steering (ODN)

<details>
<summary>Click to view R1 ODN Template Configuration</summary>

```bash
! R1
segment-routing
 traffic-eng
  on-demand color 10
   dynamic
    metric type igp
   !
  !
 !
!
```
</details>

### Objective 7: Dual-Preference Resilience

<details>
<summary>Click to view R1 Preference 50 Backup Configuration</summary>

```bash
! R1 — add preference 50 backup to COLOR_10
segment-routing
 traffic-eng
  policy COLOR_10
   color 10 end-point ipv4 10.0.0.3
   candidate-paths
    preference 200
     explicit segment-list EXPLICIT_R4_R3
    !
    preference 100
     dynamic
      metric type igp
     !
    !
    preference 50
     dynamic
      metric type igp
     !
    !
   !
  !
 !
!
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

> **Prerequisite:** Fault injection scripts require the **solution state** — BGP sessions established, SR-TE policies UP, and R3 attaching color:10 to CE2 prefixes. Run `python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>` first if starting from initial-configs.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # establish solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>     # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>         # restore
python3 scripts/fault-injection/inject_scenario_02.py --host <ip>     # Ticket 2
python3 scripts/fault-injection/apply_solution.py --host <ip>         # restore
python3 scripts/fault-injection/inject_scenario_03.py --host <ip>     # Ticket 3
python3 scripts/fault-injection/apply_solution.py --host <ip>         # restore
```

---

### Ticket 1 — Traffic to 198.51.100.0/24 Is Not Using the SR-TE Policy

An operator reports that after a recent route-policy cleanup on R1, traffic from CE1 to CE2's prefix is no longer following the SR-TE path. The SR-TE policy COLOR_10 shows as UP, but the prefix seems to be taking the plain IGP path.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show bgp ipv4 unicast 198.51.100.0/24` on R1 shows `Extended Community: Color:10` and the routing table shows the prefix being forwarded via the SR-TE policy, not via the plain next-hop.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check whether the SR-TE policy itself is healthy:
   ```
   R1# show segment-routing traffic-eng policy color 10
   ```
   If the policy is UP, the issue is not in the SR-TE policy configuration — it's in the BGP steering.

2. Inspect the BGP prefix and its extended communities:
   ```
   R1# show bgp ipv4 unicast 198.51.100.0/24
   ```
   Look for the `Extended Community` attribute. If `Color:10` is absent, the community was either never attached (R3 fault) or was stripped in transit (R1 inbound policy fault).

3. Check whether R3 is advertising the prefix with the community. SSH to R3 and inspect the outbound BGP update to R1:
   ```
   R3# show bgp ipv4 unicast 198.51.100.0/24
   ```
   If R3's local BGP table shows `Color:10` in the extended communities, R3 is doing its job — the community is being stripped at R1.

4. Inspect R1's inbound route policy for the iBGP session with R3:
   ```
   R1# show rpl route-policy RP_R3_IN
   ```
   Look for any `delete extcommunity` or community-manipulation action. A `delete extcommunity in COLOR_10` line is the injected fault.
</details>

<details>
<summary>Click to view Fix</summary>

The injected fault adds a `delete extcommunity in COLOR_10` action to R1's `RP_R3_IN` policy. This strips the color:10 community from all iBGP prefixes received from R3 before they enter R1's BGP RIB.

Fix on R1:
```bash
route-policy RP_R3_IN
 pass
end-policy
```

Remove the `delete extcommunity in COLOR_10` line and leave only `pass`. After committing, verify:
```
R1# show bgp ipv4 unicast 198.51.100.0/24
```
`Extended Community: Color:10` must appear. The ODN or static COLOR_10 policy will then steer the prefix automatically.
</details>

---

### Ticket 2 — COLOR_20 Policy Is Routing Traffic Through R4

An operator configured `COLOR_20` to avoid the L3 link (R3↔R4) using the `exclude-any RED` affinity constraint. However, a traceroute from R1 toward R3 via the color-20 policy is still showing R4 as a transit hop — the affinity constraint appears to have no effect.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show segment-routing traffic-eng policy color 20` on R1 shows a SID list that does NOT include label 16004 (R4's node SID). The active path avoids L3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the current active SID list for COLOR_20:
   ```
   R1# show segment-routing traffic-eng policy color 20
   ```
   If the SID list contains 16004 (R4), CSPF is not excluding L3 as expected.

2. Verify R1's affinity-map and that the RED constraint is configured:
   ```
   R1# show segment-routing traffic-eng affinity-map
   ```
   Confirm `RED` maps to bit-position 0.

3. Check the TE topology to see whether L3 links are carrying the RED affinity bit:
   ```
   R1# show segment-routing traffic-eng topology detail
   ```
   Look for the links with endpoints `10.1.34.3` (R3 side) and `10.1.34.4` (R4 side). Each must show `Affinity: 0x1` (bit 0 set = RED). If one endpoint shows `Affinity: 0x0`, the affinity is missing on that endpoint.

4. SSH to R4 and verify the RED affinity on Gi0/0/0/0:
   ```
   R4# show segment-routing traffic-eng topology detail
   ```
   The R4-side link entry for L3 must show the RED affinity bit. If it is absent, the fault is on R4.
</details>

<details>
<summary>Click to view Fix</summary>

The injected fault removes the RED affinity tag from R4's Gi0/0/0/0 (the R4 endpoint of L3). Without affinity on both endpoints, CSPF does not see L3 as a RED-tagged link and routes through it anyway.

Fix on R4:
```bash
segment-routing
 traffic-eng
  interface GigabitEthernet0/0/0/0
   affinity
    name RED
   !
  !
 !
!
```

After committing, allow ~10 seconds for IS-IS TE to re-flood the affinity sub-TLV and for R1's CSPF to re-evaluate the topology:
```
R1# show segment-routing traffic-eng policy color 20
```
The SID list must no longer contain 16004. The path should now go R1→R2→R3 (labels 16002, 16003) or R1→R3 via L5 (label 16003 direct).
</details>

---

### Ticket 3 — 198.51.100.0/24 Reaches R1 Without the Color Community

An operator reports the same end symptom as Ticket 1 — `198.51.100.0/24` is not being steered by the SR-TE policy. However, checking R1's `RP_R3_IN` policy shows it is clean (no community stripping). The color community appears to be absent even before it reaches R1.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show bgp ipv4 unicast 198.51.100.0/24` on both R3 and R1 shows `Extended Community: Color:10`. Traffic from CE1 to CE2 traverses the SR-TE path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm R1 is not stripping the community (rule out Ticket 1 fault type):
   ```
   R1# show rpl route-policy RP_R3_IN
   ```
   If the policy only contains `pass`, R1 is not the culprit.

2. Check R1's BGP table for the prefix:
   ```
   R1# show bgp ipv4 unicast 198.51.100.0/24
   ```
   If `Color:10` is absent, but RP_R3_IN is clean, the community was never advertised by R3.

3. SSH to R3 and inspect the prefix locally:
   ```
   R3# show bgp ipv4 unicast 198.51.100.0/24
   ```
   If `Extended Community` shows nothing (or is absent), R3 never attached the color community.

4. On R3, check the inbound policy for CE2:
   ```
   R3# show rpl route-policy RP_CE2_IN
   ```
   If `set extcommunity color COLOR_10 additive` is missing, the color is never being applied. This is the injected fault.

5. Verify the extcommunity-set is defined on R3:
   ```
   R3# show rpl extcommunity-set COLOR_10
   ```
   If the set is missing or empty, that is also part of the fault.
</details>

<details>
<summary>Click to view Fix</summary>

The injected fault removes the `set extcommunity color COLOR_10 additive` action from R3's `RP_CE2_IN` route policy. Without this action, CE2's prefix enters R3's BGP RIB without any color community and is advertised to R1 without color.

Fix on R3:
```bash
extcommunity-set opaque COLOR_10
 10
end-set
!
route-policy RP_CE2_IN
 set extcommunity color COLOR_10 additive
 pass
end-policy
```

After committing, clear the eBGP session with CE2 to trigger a BGP update:
```
R3# clear bgp 65102 soft in
```

Then verify on R3:
```
R3# show bgp ipv4 unicast 198.51.100.0/24
```
`Extended Community: Color:10` must now appear. Within a few seconds, R1 will receive the updated BGP advertisement and the ODN/COLOR_10 policy will steer the prefix.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] eBGP session R1↔CE1 established; CE1 advertising `192.0.2.0/24` to R1
- [ ] eBGP session R3↔CE2 established; CE2 advertising `198.51.100.0/24` to R3
- [ ] iBGP session R1↔R3 established; both prefixes visible in R1's BGP table
- [ ] R3 `RP_CE2_IN` attaches color:10 to `198.51.100.0/24`
- [ ] `COLOR_10` policy UP on R1 with preference 100 (dynamic IGP) active
- [ ] `EXPLICIT_R4_R3` segment-list resolves; preference 200 active for `COLOR_10`
- [ ] `COLOR_20` policy UP; SID list excludes label 16004 (no R4 transit)
- [ ] RED affinity on L3 both endpoints; BLUE affinity on L2 both endpoints
- [ ] `COLOR_30` policy UP; active SID list avoids L1 (TE metric=1000)
- [ ] ODN color 10 template configured; `198.51.100.0/24` at R1 shows `Color:10` in BGP table
- [ ] ODN policy `srte_c_10_ep_10.0.0.3` dynamically instantiated and UP
- [ ] Preference 50 backup added to `COLOR_10`; failover verified by shutting L4

### Troubleshooting

- [ ] Ticket 1 diagnosed (color stripped by RP_R3_IN) and fixed
- [ ] Ticket 2 diagnosed (missing RED affinity on R4) and fixed
- [ ] Ticket 3 diagnosed (set extcommunity missing in RP_CE2_IN on R3) and fixed

---

## 11. Appendix: Script Exit Codes

| Code | Meaning | Applies to |
|------|---------|------------|
| 0 | Success | All scripts |
| 1 | Partial failure — one or more devices failed | `apply_solution.py` only |
| 2 | `--host` not provided | All scripts |
| 3 | EVE-NG connectivity error | All scripts |
| 4 | Pre-flight check failed (solution state not present) | Inject scripts only |
