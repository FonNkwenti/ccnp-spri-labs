# INC-2026-0001 — iBGP Peer-Group Activation Failure (AS 65100)

## 1. Incident Summary

| Field | Value |
|-------|-------|
| Lab | `labs/routing-policy/lab-00-route-maps-foundations` |
| Task | Task 1 — IGP and BGP Baseline |
| Devices | R1, R2, R3 |
| Symptom | iBGP sessions between R1/R2/R3 not establishing; `neighbor IBGP activate` rejected in address-family ipv4 |
| Severity | High — Task 1 blocks all subsequent tasks |

## 2. Methodology Applied

**Divide and Conquer** — adjacency failure at BGP layer; physical and IGP layers were healthy (OSPF/IS-IS up). Started at Layer 3 BGP session state, then examined address-family configuration.

## 3. Diagnostic Log

| Time | Action | Finding |
|------|--------|---------|
| T+0 | `show ip bgp summary` on R1 | Only 10.1.14.4 (eBGP to R4) Established; 10.0.0.2 and 10.0.0.3 absent |
| T+1 | `show running-config | section router bgp` on R1/R2/R3 | address-family ipv4 missing `activate` for all iBGP peers |
| T+2 | `show ip bgp summary` on R2 | No BGP sessions at all; address-family ipv4 completely empty |
| T+3 | Attempted `neighbor IBGP activate` in af-ipv4 on all routers | Rejected: `% Activation failed : configure "bgp listener range" before activating peergroup` |
| T+4 | Applied individual `neighbor 10.0.0.X activate` per member | Commands accepted without error |
| T+5 | Wait ~15s for BGP Open/Keepalive exchange | All 3 sessions Established on each router |
| T+6 | Removed stray `neighbor 10.1.23.1 peer-group IBGP` from R2 | R2 now clean; no orphan neighbor entries |

## 4. Root Cause Analysis

**Primary cause:** `neighbor IBGP activate` in `address-family ipv4` is rejected on IOSv 15.6(2)T (image: `vios-adventerprisek9-m.SPA.156-2.T`) with the error:

```
% Activation failed : configure "bgp listener range" before activating peergroup
```

On this platform, activating a **peer-group template** in an address-family requires the BGP Dynamic Neighbors feature (`bgp listen range`) to be enabled first. This is a platform-specific restriction that does NOT exist on IOS-XE or physical IOS platforms — the command is accepted there without a listener range.

**Secondary cause (R2):** A stray `neighbor 10.1.23.1 peer-group IBGP` entry was present. IP 10.1.23.1 does not belong to any device's loopback and would never form a session.

**Exam relevance:** On the CCNP SP exam and in production IOS-XE environments, `neighbor PEER-GROUP activate` works as expected. This is a known IOSv quirk in EVE-NG labs only.

## 5. Resolution Actions

### R1

```
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.3 activate
```

### R2

```
router bgp 65100
 no neighbor 10.1.23.1 peer-group IBGP
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.3 activate
```

### R3

```
router bgp 65100
 address-family ipv4
  neighbor 10.0.0.1 activate
  neighbor 10.0.0.2 activate
```

**Key difference from workbook solution:** Replace `neighbor IBGP activate` with individual `neighbor 10.0.0.X activate` per member. All peer-group attributes (remote-as 65100, update-source Loopback0, next-hop-self) are still inherited — only the address-family activation must be done per-member on this IOSv image.

## 6. Testing & Verification

```
R1# show ip bgp summary
Neighbor        V  AS     MsgRcvd MsgSent  TblVer  State/PfxRcd
10.0.0.2        4  65100       4       6       4    0
10.0.0.3        4  65100       5       7       4    2
10.1.14.4       4  65200      13      10       4    2

R2# show ip bgp summary
Neighbor        V  AS     MsgRcvd MsgSent  TblVer  State/PfxRcd
10.0.0.1        4  65100       6       4       4    3
10.0.0.3        4  65100       6       5       4    2

R3# show ip bgp summary
Neighbor        V  AS     MsgRcvd MsgSent  TblVer  State/PfxRcd
10.0.0.1        4  65100       7       5       4    3
10.0.0.2        4  65100       5       6       4    0
10.1.34.4       4  65200      11      10       4    2
```

All iBGP sessions Established. Full mesh confirmed.

## 7. Lessons Learned

**Trap:** On IOSv 15.6(2)T in EVE-NG, `neighbor PEER-GROUP activate` is rejected inside `address-family ipv4` unless `bgp listen range` is configured. This command works on IOS-XE and production hardware without restriction.

**Rule:** When using `no bgp default ipv4-unicast` on IOSv in EVE-NG: activate each peer-group member individually (`neighbor 10.0.0.X activate`) rather than activating the peer-group template. The peer-group still provides all other attribute inheritance.

**Prevention:** Workbook solution for Task 1 should document this IOSv-specific workaround alongside the standard IOS-XE syntax.
