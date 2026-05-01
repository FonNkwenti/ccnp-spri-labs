# Fault Injection — Routing-Policy Lab 01

Troubleshooting scenarios for **Routing-Policy Lab 01: Tags, Route Types, Regex, and BGP Communities**.

## Prerequisites

- EVE-NG lab imported and all nodes started (R1, R2, R3, R4)
- Lab in known-good (solution) state before injecting any scenario
- `netmiko` and `requests` installed: `pip install netmiko requests`

## Restore Lab to Known-Good State

Always restore before injecting a new scenario:

```
python3 apply_solution.py --host <eve-ng-ip>
```

Restore a single device only:

```
python3 apply_solution.py --host <eve-ng-ip> --node R1
```

Soft-reset (default interfaces, remove routing processes) before restoring:

```
python3 apply_solution.py --host <eve-ng-ip> --reset
```

---

## Scenario 01

**Target device:** R1

**Inject:**

```
python3 inject_scenario_01.py --host <eve-ng-ip>
```

**Observable symptom:**

Run `show ip bgp 172.20.4.0` on R2. The community attribute shown for routes
received from R4 does not match the expected value defined in the inbound
route-map on R1.

**Success criteria (fault active):**

The community value shown differs from what the route-map permit sequence is
documented to set. Community-list policies that depend on an exact community
match produce unexpected results.

**Restore:**

```
python3 apply_solution.py --host <eve-ng-ip> --node R1
```

---

## Scenario 02

**Target device:** R2

**Inject:**

```
python3 inject_scenario_02.py --host <eve-ng-ip>
```

**Observable symptom:**

Run `show ip route ospf` on R1. IS-IS learned routes no longer appear in the
OSPF routing table. Prefixes that were reachable via IS-IS redistribution become
unreachable from OSPF-domain routers.

**Success criteria (fault active):**

`show ip route ospf` on R1 shows no IS-IS derived routes (O E2 or O E1 entries
that were present before are gone). `show ip route ospf` on R3 similarly loses
IS-IS routes redistributed by R2.

**Restore:**

```
python3 apply_solution.py --host <eve-ng-ip> --node R2
```

---

## Scenario 03

**Target device:** R3

**Inject:**

```
python3 inject_scenario_03.py --host <eve-ng-ip>
```

**Observable symptom:**

Run `show ip as-path-access-list 1` on R3. The regex pattern shown differs from
the production-correct form. In a real network with transit ASes, the incorrect
pattern would admit routes that should be blocked; students must identify the
regex error by comparing the ACL output against expected behavior.

**Success criteria (fault active):**

`show ip as-path-access-list 1` on R3 shows a pattern without the correct
end-of-string anchor. The ACL entry and its implications must be identified
and corrected.

**Restore:**

```
python3 apply_solution.py --host <eve-ng-ip> --node R3
```

---

## Optional: Skip Pre-Flight Check

Each inject script runs a pre-flight check to confirm the lab is in solution
state before injecting. To bypass (use with caution):

```
python3 inject_scenario_01.py --host <eve-ng-ip> --skip-preflight
```

## Optional: Override Lab Path

By default, scripts auto-discover the running lab from EVE-NG. To specify the
lab path explicitly:

```
python3 inject_scenario_01.py --host <eve-ng-ip> --lab-path ccnp-spri/routing-policy/lab-01-tags-regex-communities.unl
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Partial restore failure (`apply_solution.py` only) |
| 2 | `--host` not provided (placeholder value detected) |
| 3 | EVE-NG connectivity or port discovery error |
| 4 | Pre-flight check failed — lab not in expected state |
