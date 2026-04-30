# Fault Injection Scripts -- SR Foundations and SRGB (lab-00-sr-foundations-and-srgb)

Ops-only reference. These scripts inject troubleshooting scenarios into the live
lab environment for exam-style practice. Do not share scenario details with students
before they attempt to diagnose the fault.

## Prerequisites

- EVE-NG lab imported and all nodes started (R1, R2, R3, R4)
- Python 3.8+ with `netmiko` and `requests` installed:
  ```
  pip install netmiko requests
  ```
- Network connectivity from your workstation to the EVE-NG server

## Workflow

1. Restore the lab to the known-good state (always do this before injecting):
   ```
   python3 apply_solution.py --host <eve-ng-ip>
   ```
2. Inject a scenario:
   ```
   python3 inject_scenario_0N.py --host <eve-ng-ip>
   ```
3. Have the student diagnose and resolve the fault.
4. Restore the lab again when done:
   ```
   python3 apply_solution.py --host <eve-ng-ip>
   ```

---

## Scenario 01 -- SR-MPLS disabled on one router

**Target device:** R3

**Fault summary:** Removes `segment-routing mpls` from `address-family ipv4 unicast`
under `router isis CORE` on R3. R3 stops originating SR sub-TLVs in its IS-IS
LSPs, so every router in the domain drops the SID-to-label binding for 10.0.0.3/32.
R3 itself never installs *any* SR labels in its LFIB (it does not advertise any
binding for its peers either, since the af-level toggle gates the entire SR
function on the IS-IS process).

**What the student sees:**
- IS-IS adjacencies all up (5/5).
- IP reachability fully intact (`ping 10.0.0.3` works from R1, R2, R4).
- `show mpls forwarding` on R1 / R2 / R4 has entries for 16001/16002/16004 but
  **no entry for 16003**.
- `show isis segment-routing label table` on R3 returns empty.

**Why this scenario matters:** Distinguishes the per-router SR activation
toggle (this scenario) from the per-prefix SID origination (Scenario 03).

**Inject:**
```
python3 inject_scenario_01.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Scenario 02 -- L3 (R3<->R4) IS-IS adjacency down

**Target device:** R4

**Fault summary:** Removes `address-family ipv4 unicast` from `interface
GigabitEthernet0/0/0/0` under `router isis CORE` on R4. Gi0/0/0/0 is link L3
(R4 <-> R3), so the IS-IS hellos stop carrying the v4 NLRI on that link and the
neighbor flaps down to **Init / Down**. R4 still has Gi0/0/0/1 (link L4) to R1
fully configured, so R4 is **not isolated** -- it just loses its direct path to
R3.

**What the student sees:**
- Total adjacencies in the domain drop from 5 to 4 (L3 is gone, L1/L2/L4/L5
  still up).
- `show isis neighbors` on R3 no longer lists R4; R3 reaches 10.0.0.4 via R2.
- `show isis neighbors` on R4 no longer lists R3; R4 reaches 10.0.0.1 directly
  on L4 and 10.0.0.2/10.0.0.3 via R1.
- All four prefix-SID labels (16001-16004) **remain installed** on every router
  -- this is an IGP topology fault, not an SR fault. The SR data plane simply
  reroutes around the broken link.

**Why this scenario matters:** Reinforces that SR labels follow the IGP -- when
the IGP heals around a link failure, SR labels are recomputed automatically.

**Inject:**
```
python3 inject_scenario_02.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Scenario 03 -- Prefix SID missing on one loopback

**Target device:** R4

**Fault summary:** Removes `prefix-sid index 4` from `interface Loopback0` under
`router isis CORE` on R4. R4 still originates SR sub-TLVs for everything else
(it is fully SR-enabled), but its own `10.0.0.4/32` advertisement carries no
SID. Other routers therefore have no binding for 16004.

**What the student sees:**
- All five IS-IS adjacencies up.
- IP reachability fully intact (`ping 10.0.0.4` works from every router).
- `show mpls forwarding labels 16004` returns nothing on R1 / R2 / R3.
- `show isis database verbose | i 10.0.0.4` shows the prefix in R4's LSP but
  with no `Prefix-SID` sub-TLV.
- Other prefix SIDs (16001/16002/16003) are present and working.

**Why this scenario matters:** Distinguishes per-prefix SID origination (this
scenario -- one loopback's SID gone, rest of SR works) from the per-router SR
activation toggle (Scenario 01 -- the entire SR function on a router goes
silent).

**Inject:**
```
python3 inject_scenario_03.py --host <eve-ng-ip>
```

**Restore:**
```
python3 apply_solution.py --host <eve-ng-ip>
```

---

## Additional Options

All inject scripts support:

| Flag | Description |
|---|---|
| `--host <ip>` | EVE-NG server IP (required) |
| `--lab-path <path>` | Override auto-discovery with a specific .unl path |
| `--skip-preflight` | Bypass pre-injection state check (use with caution) |

`apply_solution.py` additionally supports:

| Flag | Description |
|---|---|
| `--node <name>` | Restore a single device only (e.g. `--node R3` or `--node R4`) |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed -- lab not in expected state |
