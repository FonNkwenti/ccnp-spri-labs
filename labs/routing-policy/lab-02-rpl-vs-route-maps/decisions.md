# Design Decisions — lab-02-rpl-vs-route-maps

## Model gate — 2026-04-28
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

---

## XR driver gap — eve_ng.py patched 2026-04-28

`connect_node()` in `labs/common/tools/eve_ng.py` was hardcoded to `cisco_ios_telnet`.
XRv nodes require `cisco_xr_telnet` (no enable mode; candidate-config/commit model).

**Fix:** Added optional `device_type` parameter to `connect_node()` (default `cisco_ios_telnet`).
When `device_type` starts with `cisco_xr`, the `enable()`, `end`, and `no logging console`
steps are skipped — they are IOS-specific and undefined/harmful on XR.

In `setup_lab.py` for this lab, XR1 and XR2 are connected with `device_type="cisco_xr_telnet"`.

---

## XR commit model — push_config() added to eve_ng.py (2026-05-04)

`send_config_set()` with default `exit_config_mode=True` calls `exit_config_mode()` after
sending commands. On IOS-XR, exiting config mode with uncommitted changes triggers:
`Uncommitted changes found, commit them before exiting(yes/no/cancel)?`
Netmiko's XR `exit_config_mode()` responds `no` — silently discarding the candidate config.
`save_config()` then sends `commit` at exec level, where it is a no-op.

**Effect:** `setup_lab.py` and `apply_solution.py` were pushing XR configs but not committing them.

**Fix:** `push_config(conn, commands, device_type)` added to `eve_ng.py`. For XR, it appends
`commit` to the commands list so the commit executes inside config mode before `exit_config_mode()`
fires — matching the pattern the fault-injection scripts already used (explicit `commit` in
`FAULT_COMMANDS`). For IOS, it falls through to the original `send_config_set()` + `save_config()`
path unchanged.

`setup_lab.py` and `apply_solution.py` now call `push_config()` instead of the raw pair.

---

## No XR command compatibility reference data

`labs/common/reference-data/` contains `ios-compatibility.yaml` but no `xr-compatibility.yaml`.
XR commands in this lab cannot be policy-verified against a local reference. All XR syntax was
verified against published IOS-XR 7.x documentation. Known XR-specific requirements:

- `metric-style wide` is under `address-family ipv4 unicast` in `router isis`, not top-level.
- Every activated BGP AF session requires explicit `route-policy NAME in/out`; omitting triggers
  implicit drop once any session policy is configured on that neighbor-group.
- `neighbor-group` replaces IOS `peer-group`; instances use `use neighbor-group NAME`.
- Communities are sent to iBGP by default on XR (no `send-community` equivalent needed).
- `save_config()` in netmiko for `cisco_xr_telnet` sends `commit` — do not include `commit`
  as a literal line in .cfg files (they are pushed via `send_config_set`).

---

## XR nodes run IS-IS only (no OSPF)

XR1 and XR2 join the IS-IS L2 domain via R2 (L6) and R3 (L7) respectively. OSPF is not
configured on XR1/XR2 — XR participation in OSPF adds 300+ lines of config and is not required
by the 3.1 / 3.2.d / 3.2.j objectives covered in this lab. XR loopbacks are reachable via
IS-IS; iBGP sessions use loopback0 as update-source.

---

## iBGP full mesh expanded to 5 routers (R1/R2/R3/XR1/XR2)

From lab-02 onward the AS 65100 iBGP full mesh includes XR1 (10.0.0.5) and XR2 (10.0.0.6).
R1/R2/R3 each add both XR peers to the IBGP peer-group. XR1 and XR2 each peer with all four
other AS 65100 members. `next-hop-self` is configured on R1 and R3 (the eBGP edge routers)
so that iBGP peers receive R1/R3's loopback as next-hop for R4's prefixes rather than R4's
link address. XR1 and XR2 have no eBGP peers and do not configure `next-hop-self` — all
next-hops they receive are already loopback addresses reachable via IS-IS.

---

## RPL scaffolding — PASS policy is mandatory

XR BGP's implicit-pass semantics apply only to sessions where NO policy is configured.
As soon as a `route-policy` is applied to one neighbor in a neighbor-group, XR treats
unmatched routes on that session as implicit drop. Every session in the IBGP neighbor-group
therefore gets explicit `route-policy IBGP_IN in` / `route-policy PASS out` to avoid silent
route loss during workbook experimentation.

---

## EBGP_IN is defined but not applied on a live eBGP session

XR1 has no direct eBGP session to R4 in this topology. `EBGP_IN` (the hierarchical parent
policy demonstrating Objective 4) is defined and referenced in workbook tasks — students apply
it on a demo iBGP session temporarily or inspect it via `show rpl policy EBGP_IN detail`. The
policy is structurally correct and would function on a live eBGP session in a production XR.

---

## Parameterized RPL uses P_TRANSIT as second argument

`CLASSIFY_PREFIXES` instantiates `MATCH_PREFIX_FROM_SET` twice: once with `P_CUSTOMER`
(172.16.0.0/16 le 24) and once with `P_TRANSIT` (172.20.0.0/16 le 24). Both prefix-sets
contain prefixes that exist in the topology (R1/XR1 customer prefixes and R4 externals),
so the workbook mark/verify task produces real hit counters.

---

## Progressive build: initial configs = lab-01 solutions

R1/R2/R3/R4 initial configs are verbatim copies of lab-01 solutions (per lab-assembler
progressive convention). XR1/XR2 initial configs contain IP addressing only (no IS-IS, no BGP)
because they are first-appearance devices. Students bring up protocols during the lab.
