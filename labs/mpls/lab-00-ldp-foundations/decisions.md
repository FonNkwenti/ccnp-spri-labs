# Build decisions — MPLS Lab 00 (LDP Foundations)

## 1. Model gate — 2026-04-28

- Difficulty: **Foundation**
- Running model: `claude-opus-4-7`
- Allowed models (per `.agent/skills/model-policy.yaml` → `tiers.Foundation.allowed_models`):
  `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`
- Outcome: **PASS** — running model is in the allowed list, no `--force-model`
  override required. Proceeding with full lab build.

## 2. Command-verification skip — 2026-04-28

The lab uses MPLS LDP (`mpls label protocol ldp`, `mpls ldp router-id`,
`mpls ip`, `show mpls ldp …`, `show mpls forwarding-table`) and IS-IS
(`router isis`, `is-type level-2-only`, `metric-style wide`, `isis network
point-to-point`) commands.

`.agent/skills/reference-data/ios-compatibility.yaml` returns `unknown`
for every one of these strings (the file does not yet enumerate
MPLS/LDP/ISIS coverage for IOSv). Per the lab-assembler "verify-or-skip"
rule, the verifier was **not run**. Rationale: every command used here is
documented and known-good on IOSv 15.9(3)M6 (the platform `meta.yaml`
records); they appear in production CCNP study material and are present
in the existing `labs/isis/lab-00-single-level-isis/solutions/*.cfg`.
Risk of an unverified syntax slipping through is judged low; if a learner
hits a real `% Invalid input` we will round-trip the command into
`ios-compatibility.yaml` rather than blocking this build.

## 3. Topology choices

- **IS-IS L2-only**, NETs `49.0001.0000.0000.000X.00` where X ∈ {1,2,3,4}
  matches the device number. This convention is consistent with
  `labs/isis/`, BUT the IS-IS reference lab uses `is-type level-1` —
  do not copy it verbatim. SP-native practice (and the rest of the MPLS
  topic) is L2; the `is-type level-2-only` line was set deliberately.
- **`mpls ldp router-id Loopback0 force`** rather than letting IOS
  auto-pick the highest loopback. The `force` keyword is required so
  the change takes effect immediately on first apply (without `force`,
  IOS waits for the current ID to disappear before swapping); the lab
  also uses this property in Ticket 1 to plant a flapping session.
- **No `mpls ldp autoconfig`** in the solution. The original baseline
  objective referenced autoconfig in the failure scenario, but the
  taught configuration uses explicit per-interface `mpls ip` because
  that is what the learner needs to read in `show mpls interfaces`.
  Autoconfig appears as a teaching point in lab-01 / capstone, not here.

## 4. Initial-configs scope (first progressive lab)

Per the lab-assembler "first-progressive-lab" rule, `initial-configs/`
contain ONLY:

- hostname, `no ip domain-lookup`
- Loopback0 (`ip address`, `no shutdown`)
- core interfaces (`ip address`, `no shutdown`, descriptions)

No IS-IS, no MPLS, no LDP — those *are* the lab. Stripping the protocol
plane is what makes lab-00 a foundation lab rather than a checklist of
verifications on top of a converged topology.

## 5. Fault selection

Lab-00's baseline objectives 7 and 8 listed two fault scenarios; the
fault-injector subagent built exactly two tickets:

| Ticket | Symptom (workbook §9)                              | Mechanism                                              |
|--------|-----------------------------------------------------|--------------------------------------------------------|
| 1      | One LDP session keeps flapping every ~30 s          | `mpls ldp router-id Loopback99 force` on P1 (no Lo99)  |
| 2      | Three peers see four labels, one peer sees three    | `no mpls ip` on P2 Gi0/2 (toward PE2)                  |

Each ticket heading describes only the **observable symptom**, not the
device or root cause — diagnosis is the lab.
