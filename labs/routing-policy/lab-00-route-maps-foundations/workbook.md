# Lab 00 — Route-Maps, Prefix-Lists, and ACL Matching

> **Topic:** Routing Policy and Manipulation · **Exam:** 300-510 · **Difficulty:** Foundation · **Time:** 60 minutes

```
┌─ Sections ──────────────────────────────────────────────────────┐
│ 1. Concepts and Skills                                          │
│ 2. Topology                                                     │
│ 3. Device, Loopback, Cabling, and Console Tables                │
│ 4. What This Lab IS / IS NOT                                    │
│ 5. Tasks (numbered)                                             │
│ 6. Verification                                                 │
│ 7. Cheatsheet                                                   │
│ 8. Solutions (collapsed)                                        │
│ 9. Troubleshooting Scenarios                                    │
│ 10. Completion Checklist                                        │
│ 11. Appendix — Exit Codes and Commands                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Concepts and Skills

This lab introduces the **building blocks of policy** in IOS:

- **ACLs** — standard (source-only, by number 1-99 or 1300-1999) and extended (source/dest/proto/port, 100-199 or 2000-2699). Used in many places, including as a `match` clause in route-maps.
- **Prefix-lists** — purpose-built for routing decisions. Match a prefix and length range (`ge`, `le`). The standard tool for filtering routes.
- **Route-maps** — sequenced policy statements. Each sequence has a `permit`/`deny` action, optional `match` clauses (AND across types), and optional `set` clauses. Sequences are evaluated top-to-bottom; first match wins; **implicit deny at the end**.
- **Route-map application points** — applied at a **BGP neighbor** (`neighbor x.x.x.x route-map NAME in|out`) or at **redistribution** (`redistribute <proto> route-map NAME`). Same syntax, different injection point.
- **`continue` clause** — inside a route-map sequence, `continue [seq]` resumes evaluation at the next (or specified) sequence after running this sequence's `set` actions. Without `continue`, evaluation stops at first match.

By the end you will be able to:

1. Write a standard or extended ACL and reference it from `match ip address`.
2. Write a prefix-list with `ge`/`le` and a separate exact-match prefix-list.
3. Apply an inbound route-map on an eBGP session that filters by prefix-list.
4. Predict the outcome of `permit`/`deny` sequences and the implicit deny.
5. Distinguish a route-map applied at `redistribute` from one applied at `neighbor`.

---

## 2. Topology

```
                          AS 65100 (SP core, OSPF area 0 + IS-IS L2 + iBGP full mesh)
                ┌─────────────────────────────────────────────────────────────┐
                │                                                             │
                │     ┌────┐  L1 (10.1.12/24)   ┌────┐                        │
                │     │ R1 ├────────────────────┤ R2 │                        │
                │     │    │                    │    │                        │
                │     └─┬──┘                    └─┬──┘                        │
                │       │ L5 (10.1.13/24)         │ L2 (10.1.23/24)           │
                │       │                         │                           │
                │     ┌─┴──┐ ────────────────────┘                            │
                │     │ R3 │                                                  │
                │     └─┬──┘                                                  │
                └───────┼──────────────────────────────────────────────────────┘
                        │ L3 (10.1.34/24, eBGP)
                        │
                  ┌─────┴───────────┐  L4 (10.1.14/24, eBGP)   to R1
                  │      R4         ├──────────────────────────────►
                  │  AS 65200       │
                  │ Lo1 172.20.4/24 │
                  │ Lo2 172.20.5/24 │
                  └─────────────────┘
```

Key relationships:

- **R1 ↔ R2 ↔ R3 ↔ R1** form a triangle: OSPF area 0, IS-IS L2, and iBGP full-mesh ride these three SP-core links.
- **R4 has two physical eBGP sessions**: one to R1 (L4) and one to R3 (L3). R2 has no eBGP — it is pure transit.
- The filter target is **R4's Lo2 (172.20.5.0/24)**: an inbound route-map on R1 from R4 denies it; the same prefix is still accepted on R3 from R4 (no filter there).

---

## 3. Device, Loopback, Cabling, and Console Tables

### Device table

| Device | Platform | Image | RAM | Role | ASN |
|--------|----------|-------|-----|------|-----|
| R1 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB | SP core / eBGP edge | 65100 |
| R2 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB | SP core / transit | 65100 |
| R3 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB | SP core / eBGP edge | 65100 |
| R4 | iosv | vios-adventerprisek9-m.SPA.156-2.T | 512 MB | External AS | 65200 |

### Loopback table

| Device | Loopback | Address | Purpose |
|--------|----------|---------|---------|
| R1 | Lo0 | 10.0.0.1/32 | Router-ID, iBGP source |
| R1 | Lo1 | 172.16.1.1/24 | Customer prefix advertised into BGP |
| R2 | Lo0 | 10.0.0.2/32 | Router-ID, iBGP source |
| R3 | Lo0 | 10.0.0.3/32 | Router-ID, iBGP source |
| R4 | Lo0 | 10.0.0.4/32 | Router-ID |
| R4 | Lo1 | 172.20.4.1/24 | External prefix #1 (accepted by R1) |
| R4 | Lo2 | 172.20.5.1/24 | External prefix #2 (filtered at R1) |

### Cabling table

| Link | Endpoints                    | Subnet         | Protocols on link |
|------|------------------------------|----------------|-------------------|
| L1   | R1 Gi0/0 ↔ R2 Gi0/0          | 10.1.12.0/24   | OSPF area 0, IS-IS L2, iBGP transport |
| L2   | R2 Gi0/1 ↔ R3 Gi0/0          | 10.1.23.0/24   | OSPF area 0, IS-IS L2, iBGP transport |
| L3   | R3 Gi0/1 ↔ R4 Gi0/0          | 10.1.34.0/24   | eBGP only |
| L4   | R1 Gi0/1 ↔ R4 Gi0/1          | 10.1.14.0/24   | eBGP only |
| L5   | R1 Gi0/2 ↔ R3 Gi0/2          | 10.1.13.0/24   | OSPF area 0, IS-IS L2, iBGP transport |

### Console-port table

Console ports are visible in the EVE-NG node properties panel after import.

| Device | Console (set after EVE-NG import) |
|--------|-----------------------------------|
| R1 | `telnet <eve-ng-ip> <port>` |
| R2 | `telnet <eve-ng-ip> <port>` |
| R3 | `telnet <eve-ng-ip> <port>` |
| R4 | `telnet <eve-ng-ip> <port>` |

---

## 4. What This Lab IS / IS NOT

**This lab IS:**

- A first hands-on tour of route-maps, prefix-lists, and ACLs as policy primitives.
- A demonstration of the difference between applying a route-map at `redistribute` vs at `neighbor`.
- A clear before/after of how an inbound filter changes the BGP RIB-IN.
- A foundation for everything else in the routing-policy chapter (tags, regex, communities, RPL).

**This lab IS NOT:**

- A study of communities, AS-path regex, or local-preference manipulation — those come in lab-01 and lab-04.
- An RPL (IOS-XR) lab — lab-02 introduces RPL.
- A troubleshooting capstone — three small inject scenarios are provided as practice, not as the lab focus.
- A redistribution mutual-loop study — lab-01 covers tag-based loop prevention.

---

## 5. Tasks

### Task 1 — Bring up the IGP and BGP baseline

Configure OSPF area 0 on Lo0, L1, L2, L5 of R1/R2/R3. Configure IS-IS L2 with `metric-style wide` on the same set of interfaces. Configure BGP AS 65100 iBGP full-mesh between R1, R2, R3 (peer-group `IBGP`, source Lo0, `next-hop-self`). Configure eBGP from R1 to R4 (10.1.14.4) and from R3 to R4 (10.1.34.4). On R1 advertise 172.16.1.0/24; on R4 advertise 172.20.4.0/24 and 172.20.5.0/24.

**Verification:** `show ip ospf neighbor`, `show isis neighbor`, `show ip bgp summary`. All adjacencies up; R1's BGP table should show both R4 prefixes via 10.1.14.4 with AS-path `65200`.

### Task 2 — Build a standard ACL and an extended ACL

On R1, build a standard numbered ACL `10` permitting source 172.20.4.0/24. Build an extended named ACL `ACL_EXT_R4_LO2` permitting `ip 172.20.5.0 0.0.0.255 any`. These will be the match objects for route-maps.

**Verification:** `show access-lists 10`, `show ip access-lists ACL_EXT_R4_LO2`.

### Task 3 — Build prefix-lists with ge/le and exact match

On R1, build `PFX_R4_LE_24` permitting `172.20.0.0/16 ge 24 le 24` (matches any /24 inside 172.20/16). Build `PFX_R4_LO2_EXACT` permitting `172.20.5.0/24` exactly (no `ge`/`le`).

**Verification:** `show ip prefix-list`, `show ip prefix-list detail PFX_R4_LO2_EXACT`.

### Task 4 — Apply an inbound route-map that denies one R4 prefix

On R1, build `route-map FILTER_R4_IN`:

- Sequence 10 — `deny`, `match ip address prefix-list PFX_R4_LO2_EXACT` (drops 172.20.5.0/24).
- Sequence 20 — `permit`, `match ip address prefix-list PFX_R4_LE_24` (allows 172.20.4.0/24).

Apply it inbound on neighbor 10.1.14.4: `neighbor 10.1.14.4 route-map FILTER_R4_IN in`. Soft-reset: `clear ip bgp 10.1.14.4 soft in`.

**Verification:** `show ip bgp neighbors 10.1.14.4 routes` before and after — only 172.20.4.0/24 should appear after.

### Task 5 — Demonstrate match/set/permit/deny semantics with `continue`

Build `route-map DEMO_CONTINUE`:

- Sequence 10 — `permit`, `match ip address prefix-list PFX_R4_LE_24`, `set community 65100:100`, `continue 20`.
- Sequence 20 — `permit`, `set local-preference 200`.

Walk through three scenarios verbally with the workbook: (a) what happens for a 172.20.4.0/24 prefix, (b) what happens for a non-matching 10.0.0.0/8 prefix, (c) what would happen if `continue 20` were removed.

**Verification:** `show route-map DEMO_CONTINUE` — confirm both sequences are visible and the `continue` clause is recorded.

### Task 6 — Contrast route-map applied to redistribution vs to neighbor

Build `route-map DEMO_REDIST` permitting all and setting `tag 100`. Note that the **same syntax** can be applied two ways:

- At a BGP neighbor: `neighbor 10.1.14.4 route-map DEMO_REDIST out` — affects what is **advertised** to the peer.
- At redistribution: `router ospf 1` → `redistribute bgp 65100 subnets route-map DEMO_REDIST` — affects what is **injected** from BGP into OSPF.

Do not actually apply either application — the workbook is asking you to read the configured map and explain where each application point would intercept the route. (Applying redistribution between BGP and OSPF here would create unnecessary churn; the goal is concept clarity.)

**Verification:** `show route-map DEMO_REDIST` — sequence and `set tag` action visible.

---

## 6. Verification

After Task 4, run on R1:

```
R1# show ip bgp neighbors 10.1.14.4 routes
   Network          Next Hop            Metric LocPrf Weight Path
*> 172.20.4.0/24    10.1.14.4                0             0 65200 i
! Note: 172.20.5.0/24 is absent — denied by FILTER_R4_IN seq 10.
```

```
R1# show ip bgp
*> 172.20.4.0/24    10.1.14.4                0             0 65200 i
*>i172.20.5.0/24    10.0.0.3                 0    100      0 65200 i
! Note: 172.20.5.0/24 is still in the BGP table via R3 (iBGP) — only the R1↔R4 path is filtered.
```

```
R1# show route-map FILTER_R4_IN
route-map FILTER_R4_IN, deny, sequence 10
  Match clauses:
    ip address prefix-lists: PFX_R4_LO2_EXACT
  Set clauses:
  Policy routing matches: 0 packets, 0 bytes
route-map FILTER_R4_IN, permit, sequence 20
  Match clauses:
    ip address prefix-lists: PFX_R4_LE_24
  Set clauses:
! Implicit deny at end is what would drop a non-matching prefix; here seq 20 catches 172.20.4/24.
```

---

## 7. Cheatsheet

| Goal | Command |
|------|---------|
| Show all route-maps | `show route-map` |
| Show one route-map | `show route-map FILTER_R4_IN` |
| Show prefix-list contents | `show ip prefix-list` |
| Show prefix-list detail | `show ip prefix-list detail NAME` |
| Show ACL counters | `show access-lists` |
| Show neighbor's RIB-IN before policy | `show ip bgp neighbors X received-routes` (requires `soft-reconfiguration inbound`) |
| Show neighbor's RIB-IN after policy | `show ip bgp neighbors X routes` |
| Soft-clear inbound | `clear ip bgp X soft in` |
| Show BGP table | `show ip bgp` |

Common pitfalls:

- **Implicit deny** at the end of every route-map drops anything not explicitly permitted — always end with `permit` if you want pass-through.
- **`route-map ... permit` with no `match`** matches everything — useful as a final catch-all.
- **`match ip address NN`** uses an ACL when `NN` is numeric; **`match ip address prefix-list NAME`** uses a prefix-list. They are different match types.
- **`ge`/`le` semantics** — `ge X le Y` means "prefix-length between X and Y inclusive." Without `ge` or `le`, the prefix-list matches the exact length only.
- **Direction matters** — `route-map ... in` filters incoming updates; `route-map ... out` filters outgoing advertisements. Wrong direction silently does nothing visible on the local RIB-IN.

---

## 8. Solutions

<details>
<summary>R1 — full configuration</summary>

See `solutions/R1.cfg`.

</details>

<details>
<summary>R2 — full configuration</summary>

See `solutions/R2.cfg`.

</details>

<details>
<summary>R3 — full configuration</summary>

See `solutions/R3.cfg`.

</details>

<details>
<summary>R4 — full configuration</summary>

See `solutions/R4.cfg`.

</details>

---

## 9. Troubleshooting Scenarios

Three small fault-injection scripts are provided so you can practice diagnosis on the same topology. Each fault is on R1 only, fully reversible with `apply_solution.py`. Apply one at a time.

### Workflow per scenario

1. Run `python scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip>`.
2. Read the symptom from the ticket below; do **not** read past the ticket until you have a hypothesis.
3. Diagnose using `show` commands. Note the exact command that revealed the fault.
4. Compare your diagnosis with the troubleshooting key further below.
5. Run `python scripts/fault-injection/apply_solution.py --host <eve-ng-ip> --node R1` to reset.

### Ticket 1 — "All R4 prefixes have disappeared"

> Operator opened a ticket: after the change-window on R1, **none** of R4's prefixes appear in R1's BGP RIB-IN. Other PEs still have them. Was working before. Find the cause and fix.

### Ticket 2 — "Filter is over-matching"

> Operator opened a ticket: the inbound filter on R1 from R4 was supposed to drop **only** 172.20.5.0/24, but somehow 172.20.4.0/24 is also getting dropped. Identify what changed and restore correct behavior.

### Ticket 3 — "Filter has no effect"

> Operator opened a ticket: the inbound filter on R1 from R4 was supposed to drop 172.20.5.0/24, but the prefix is still showing up in R1's BGP RIB-IN. The configuration looks "almost" right. Find the misapplication.

### Troubleshooting key (read after diagnosis)

| Ticket | Fault | Diagnosis command | Fix |
|--------|-------|-------------------|-----|
| 1 | `route-map FILTER_R4_IN permit 20` was removed; only `deny 10` remains; **implicit deny** drops 172.20.4/24 too. | `show route-map FILTER_R4_IN` — only one sequence visible. | Re-add `route-map FILTER_R4_IN permit 20` with `match ip address prefix-list PFX_R4_LE_24`. |
| 2 | `PFX_R4_LO2_EXACT` was changed from `172.20.5.0/24` exact to `172.20.0.0/16 le 24` — now matches both /24s. | `show ip prefix-list PFX_R4_LO2_EXACT` — wrong boundary. | Restore exact match: `ip prefix-list PFX_R4_LO2_EXACT seq 5 permit 172.20.5.0/24`. |
| 3 | `neighbor 10.1.14.4 route-map FILTER_R4_IN out` instead of `in` — filter applied on outbound; inbound RIB-IN unfiltered. | `show ip bgp neighbors 10.1.14.4` — direction confirms outbound. | Change to `neighbor 10.1.14.4 route-map FILTER_R4_IN in`; soft-clear inbound. |

---

## 10. Completion Checklist

- [ ] All OSPF, IS-IS, and BGP adjacencies up between R1/R2/R3; eBGP up R1↔R4 and R3↔R4.
- [ ] R1 advertises 172.16.1.0/24; R4 advertises 172.20.4.0/24 and 172.20.5.0/24.
- [ ] Standard ACL `10` and extended ACL `ACL_EXT_R4_LO2` exist on R1.
- [ ] Prefix-lists `PFX_R4_LE_24` (ge/le 24) and `PFX_R4_LO2_EXACT` (exact) exist on R1.
- [ ] `route-map FILTER_R4_IN` applied inbound on R1's neighbor 10.1.14.4.
- [ ] `show ip bgp neighbors 10.1.14.4 routes` shows only 172.20.4.0/24 from R4.
- [ ] `show ip bgp 172.20.5.0` on R1 shows the prefix only via iBGP from R3 (next-hop 10.0.0.3).
- [ ] `route-map DEMO_CONTINUE` and `route-map DEMO_REDIST` defined on R1.
- [ ] At least one of the three troubleshooting scenarios exercised.

---

## 11. Appendix — Exit Codes and Commands

### Inject and restore commands

```
python scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
python scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
python scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip> --node R1
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>            # all 4 devices
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip> --reset    # also clears BGP/OSPF state
```

### Setup command

```
python setup_lab.py --host <eve-ng-ip>
```

### Exit codes (all scripts)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Authentication failed (bad EVE-NG creds) |
| 2 | Lab path not found in EVE-NG |
| 3 | Node not found by name |
| 4 | Configuration push failed (timeout or device error) |
| 5 | Argument error (e.g., `--node` without value) |
