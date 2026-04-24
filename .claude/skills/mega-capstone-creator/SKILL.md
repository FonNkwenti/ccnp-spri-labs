---
name: mega-capstone-creator
description: Generates a multi-domain Mega Capstone lab spanning all chapter domains for an exam series. Use only when invoked via the /mega-capstone command after all chapter capstones are approved. Produces a complete lab package in labs/mega-capstone/.
---

# Mega Capstone Creator Skill

Generates a single integrated multi-domain lab that validates mastery across all topics
simultaneously. This is the final deliverable of the entire lab series.

<!-- TODO: This skill is currently hardcoded to ENARSI with 7 specific chapter paths.
     It needs to be updated to read topics dynamically from specs/topic-plan.yaml
     instead of listing them explicitly. This will make it exam-agnostic.
     See exam-planner/SKILL.md for the topic-plan.yaml schema. -->

-# Instructions

--# Step 1: Read All Chapter Baselines

Before generating anything, read all 7 chapter baseline files:
- `labs/eigrp/baseline.yaml`
- `labs/ospf/baseline.yaml`
- `labs/bgp/baseline.yaml`
- `labs/redistribution/baseline.yaml`
- `labs/vpn/baseline.yaml`
- `labs/infrastructure-security/baseline.yaml`
- `labs/infrastructure-services/baseline.yaml`

Extract per-chapter: IP addressing ranges, device roles, loopback conventions. Use these as reference when assigning Mega Capstone IPs — do NOT reuse the same subnets. Assign a fresh 10.x.x.x addressing plan.

--# Step 2: Define the Mega Capstone Topology

The Mega Capstone uses approximately 10 routers covering all 7 domains. Write `labs/mega-capstone/baseline.yaml` as a standalone topology definition (not chained from any chapter).

**Device roles and zones:**

| Device | Platform | Role | Domain |
|--------|----------|------|--------|
| R1 | iosv | EIGRP Hub / DMVPN Hub | EIGRP, VPN |
| R2 | iosv | EIGRP Branch A / DMVPN Spoke | EIGRP, VPN |
| R3 | iosv | EIGRP Branch B / DMVPN Spoke | EIGRP, VPN |
| R4 | iosv | OSPF ABR (Area 0 / Area 1) / EIGRP-OSPF Redistribution Boundary | OSPF, Redistribution |
| R5 | iosv | OSPF Area 1 Internal | OSPF |
| R6 | iosv | eBGP Edge / OSPF-BGP Redistribution Boundary / Edge Security | BGP, Redistribution, Security |
| R7 | iosv | OSPF Area 0 Internal | OSPF |
| R8 | iosv | Services Router (DHCP server, IP SLA source) | Infrastructure Services |
| R9 | iosv | IP SLA target / SNMP management | Infrastructure Services |
| SW1 | — | VPCS / syslog+SNMP collector (simulated as loopback on R9) | Infrastructure Services |

**Addressing plan (fresh — do not reuse chapter subnets):**
- Loopbacks: 10.100.0.x/32 (megacap devices)
- EIGRP zone transit: 10.200.12.0/30, 10.200.13.0/30, 10.200.23.0/30
- EIGRP↔OSPF boundary: 10.200.14.0/30 (R1-R4)
- OSPF zone transit: 10.200.45.0/30, 10.200.47.0/30, 10.200.46.0/30
- OSPF↔BGP boundary: 10.200.46.0/30 (R4-R6)
- BGP: R6 uses 192.0.2.0/30 toward simulated ISP (loopback on R6)
- DMVPN: 10.200.0.0/24 (mGRE tunnel, R1=hub .1, R2=spoke .2, R3=spoke .3)
- Services: 10.200.99.0/24 (DHCP pool on R8 for simulated clients)
- IPv6: 2001:db8:200::/48 prefix space, per-link /64s

**Console ports:** Dynamic — assigned by EVE-NG at lab creation. Populate the Console Access Table in workbook.md Section 3 from the EVE-NG web UI after creating the lab.

**`labs/mega-capstone/baseline.yaml` schema:** Same format as chapter baselines. Mark `standalone: true` at the top level to indicate this is not chained from any chapter.

--# Step 3: Write baseline.yaml

Write `labs/mega-capstone/baseline.yaml` with:
- `chapter: mega-capstone`
- `standalone: true`
- `exam: 300-410 ENARSI`
- `blueprint_sections:` — list all 7 chapter domains (1.9, 1.10, 1.11, 1.2–1.8, 2.1–2.4, 3.1–3.4, 4.1–4.7)
- Full `core_topology` with all 9 active devices and all links
- No `optional_devices` (all devices are always active)
- Single lab entry: number 1, type `mega_capstone`, `clean_slate: true`

--# Step 4: Generate workbook.md

Write the full 10-section workbook. Special guidance for this lab:

**Section 1 — Concepts & Skills Covered:**
List all 7 chapter domains and the specific blueprint bullets from each. This lab validates all of them.

**Section 2 — Topology & Scenario:**
Enterprise narrative: "AcmeCorp is consolidating its multi-site network. R1–R3 form the EIGRP WAN core. R4 connects the EIGRP domain to the OSPF campus. R6 connects to the upstream ISP via eBGP. DMVPN tunnels provide encrypted branch connectivity. The network team has been asked to commission the entire infrastructure in a single maintenance window."

Include the full ASCII topology diagram (Unicode box-drawing) showing all 9 routers, zones, and all link IPs.

**Section 3 — Hardware & Environment:**
Full cabling table + Console Access Table for all 9 devices.

**Section 5 — Lab Challenge (multi-domain):**
```markdown
## 5. Lab Challenge: ENARSI Mega Capstone

> This is the final capstone lab. No step-by-step guidance is provided.
> Complete all domain objectives from scratch. IP addressing is pre-configured.
> All 300-410 ENARSI blueprint bullets must be addressed.

### Domain 1: EIGRP (R1, R2, R3, R4)
- Configure EIGRP Named Mode AS 200 on R1, R2, R3
- Enable dual-stack IPv4 + IPv6 address families
- Set R4 as EIGRP stub (connected summary)

### Domain 2: OSPF (R4, R5, R6, R7)
- Configure OSPFv2 on R4 (ABR: Area 0 and Area 1), R5 (Area 1), R6 (Area 0), R7 (Area 0)
- Configure Area 1 as a stub area
- Verify full OSPF convergence and LSA types

### Domain 3: BGP (R6)
- Configure eBGP between R6 (AS 65001) and simulated ISP (AS 65002, R6 loopback)
- Advertise the OSPF summary into BGP
- Apply a route-map to set local-preference for inbound routes

### Domain 4: Redistribution (R4, R6)
- Redistribute EIGRP into OSPF on R4 (set metric-type E2, tag 100)
- Redistribute OSPF into BGP on R6
- Prevent routing loops using route tags

### Domain 5: VPN (R1, R2, R3)
- Configure DMVPN Phase 2 (mGRE + NHRP) on R1 (hub), R2 and R3 (spokes)
- Run EIGRP over the DMVPN tunnel
- Verify spoke-to-spoke traffic takes a direct tunnel path

### Domain 6: Infrastructure Security (R6, R4)
- Apply an inbound ACL on R6's external interface to permit only HTTP, HTTPS, and ICMP from the ISP
- Configure CoPP on R4 to rate-limit OSPF hellos and ICMP to the control plane
- Verify ACL hit counters and CoPP policy statistics

### Domain 7: Infrastructure Services (R8, R9)
- Configure R8 as a DHCP server for the 10.200.99.0/24 pool; exclude the first 10 addresses
- Configure IP SLA on R8 to probe R9's loopback every 10 seconds; set a track object
- Configure SNMP v2c community read-only on R9; set syslog to R9's loopback
- Verify DHCP lease assignment and IP SLA probe status
```

**Section 8 — Solutions:**
One `<details>` spoiler block per domain (7 blocks), each containing all device configs for that domain.

**Section 9 — Troubleshooting Scenarios:**
7 tickets — one per chapter domain. Each ticket is a standalone fault covering only that domain's protocols.

- Ticket 1: EIGRP — R2 and R3 no longer form adjacency with R1
- Ticket 2: OSPF — R5 (Area 1) is missing routes from Area 0
- Ticket 3: BGP — R6 is not advertising the OSPF summary to the ISP
- Ticket 4: Redistribution — EIGRP routes are appearing in OSPF with metric-type E1 instead of E2
- Ticket 5: VPN — R2 spoke cannot reach R3 spoke directly (all traffic hairpins through R1)
- Ticket 6: Security — Legitimate OSPF traffic is being dropped by CoPP on R4
- Ticket 7: Services — DHCP clients on R8's pool are not receiving addresses; IP SLA probe is down

**Section 10 — Checklist:**
Two groups: "Domain Configuration" (7 checkboxes) and "Troubleshooting Scenarios" (7 checkboxes).

--# Step 5: Generate initial-configs/

> **IOS Compatibility:** Before writing any config in Steps 5 and 6, check commands against `.agent/skills/reference-data/ios-compatibility.yaml`. For commands not in the file, follow the 2a–2f verification sub-steps from `lab-assembler/SKILL.md`.

Clean slate — IP addressing only. No routing protocols, no VPN, no ACLs, no DHCP.

One `.cfg` per active device. Each config contains:
- `hostname [Device]`
- `no ip domain-lookup`
- Interface IP addresses (IPv4 + IPv6)
- `ipv6 unicast-routing`
- Loopback0 with its IPv4/IPv6 address
- `no shutdown` on all configured interfaces
- Console/VTY access (`line con 0` + `line vty 0 4` with `transport input telnet`)

--# Step 6: Generate solutions/

Complete IOS configurations per device implementing all 7 domain objectives. One `.cfg` per device.

--# Step 7: Generate topology.drawio

Full topology diagram following the drawio Visual Style Guide. Use `drawio` skill to validate.

Zones should be visually grouped:
- EIGRP zone (R1-R3): left cluster
- OSPF zone (R4, R5, R7): center cluster
- BGP edge (R6): right edge
- DMVPN cloud: overlay on EIGRP zone
- Services (R8, R9): bottom cluster

--# Step 8: Generate setup_lab.py

Netmiko script connecting to all 9 devices via `cisco_ios_telnet` to EVE-NG host + dynamic ports. Accepts `--host <eve-ng-ip>` argument. Same structure as chapter lab setup scripts.

--# Step 9: Generate scripts/fault-injection/

7 inject scripts — one per domain:
- `inject_scenario_01.py` — EIGRP fault
- `inject_scenario_02.py` — OSPF fault
- `inject_scenario_03.py` — BGP fault
- `inject_scenario_04.py` — Redistribution fault
- `inject_scenario_05.py` — VPN fault
- `inject_scenario_06.py` — Security fault
- `inject_scenario_07.py` — Services fault
- `apply_solution.py` — Restore all 9 devices to known-good (solutions/ state)
- `README.md` — Ops-only (no challenge descriptions; reference workbook.md Section 9)

Invoke the `fault-injector` skill to generate these based on the Section 9 ticket descriptions.

--# Step 10: Write meta.yaml

After the fault-injector skill completes, write `labs/mega-capstone/meta.yaml`.

1. Get `skill_version`: run `git -C .agent/skills log --format="%ci" -1` and take the date portion (YYYY-MM-DD).
2. Get today's date (YYYY-MM-DD).
3. Glob all files created in this lab directory (recursive, relative paths).
4. Write `labs/mega-capstone/meta.yaml`:

```yaml
# Auto-generated — do not edit manually. Use /tag-lab to stamp external agent runs.
lab: mega-capstone
chapter: mega-capstone
created:
  date: "[YYYY-MM-DD]"
  agent: claude-sonnet-4-6
  skill: mega-capstone
  skill_version: "[YYYY-MM-DD]"
  files:
    - baseline.yaml
    - workbook.md
    - topology.drawio
    - setup_lab.py
    - initial-configs/R1.cfg
    # ... one entry per device
    - solutions/R1.cfg
    # ... one entry per device
    - scripts/fault-injection/inject_scenario_01.py
    # ... one per scenario
    - scripts/fault-injection/apply_solution.py
    - scripts/fault-injection/README.md
updated: []
```

List every file actually created — adjust device names and inject script count to match.

--# Step 11: Update Progress & Mindmap

1. Update `memory/progress.md` — add a Mega Capstone row with status "Review Needed".
2. Update the `README.md` mindmap — add a Mega Capstone branch with `◉ Mega Capstone`.

-# Output Directory

```
labs/mega-capstone/
├── baseline.yaml
├── workbook.md
├── topology.drawio
├── initial-configs/
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── R5.cfg
│   ├── R6.cfg
│   ├── R7.cfg
│   ├── R8.cfg
│   └── R9.cfg
├── solutions/
│   └── [same per-device structure]
├── setup_lab.py
└── scripts/fault-injection/
    ├── inject_scenario_01.py
    ├── inject_scenario_02.py
    ├── inject_scenario_03.py
    ├── inject_scenario_04.py
    ├── inject_scenario_05.py
    ├── inject_scenario_06.py
    ├── inject_scenario_07.py
    ├── apply_solution.py
    └── README.md
```

-# Common Issues

--# Chapter baseline not found
- **Cause:** One or more chapter labs were never generated; baseline.yaml doesn't exist.
- **Solution:** Stop. The `/mega-capstone` command pre-flight check should have caught this. Return to the `/mega-capstone` command and report which chapter baselines are missing.

--# IP address conflict with chapter labs
- **Cause:** Mega Capstone IPs overlap with a chapter's baseline addressing (both use 10.0.0.x loopbacks).
- **Solution:** Use the 10.100.0.x/32 loopback range and 10.200.x.x/30 transit ranges reserved exclusively for the Mega Capstone. Never reuse chapter IP ranges.

--# Too many devices — EVE-NG resource planning
- **Cause:** 9 IOSv nodes × 512 MB = ~4.5 GB RAM. Within the 64 GB host capacity but worth noting.
- **Solution:** All 9 nodes should run comfortably on the Dell i7-1370P/64 GB host. If resource contention occurs, run in two segments: EIGRP+VPN (R1-R3) first, then OSPF+BGP (R4-R7) separately. Note: boot time for 9 IOSv nodes is approximately 2–3 minutes total.

-# Examples

User: "/mega-capstone" (via the mega-capstone slash command, all chapter capstones approved)

Actions:
1. Read all 7 chapter baseline.yaml files for IP reference.
2. Write `labs/mega-capstone/baseline.yaml` with 9-device standalone topology.
3. Write `labs/mega-capstone/workbook.md` — 10 sections, 7-domain challenge, 7 troubleshooting tickets.
4. Generate `initial-configs/` (IP addressing only, 9 devices).
5. Generate `solutions/` (full 7-domain configs, 9 devices).
6. Generate `topology.drawio` via `drawio` skill.
7. Generate `setup_lab.py` for 9 devices with `--host <eve-ng-ip>` and dynamic ports (populated from EVE-NG web UI).
8. Invoke `fault-injector` skill to generate 7 inject scripts + `apply_solution.py`.
9. Update `memory/progress.md` — add Mega Capstone row with status Review Needed.
