# Lab 01 — Tags, Route Types, Regex, and BGP Communities

**Chapter:** Routing Policy | **Exam:** 300-510 SPRI | **Difficulty:** Foundation | **Time:** 75 min

## Overview

Extends lab-00 with four advanced routing policy tools used in real SP environments:

1. **Route tags** for OSPF↔IS-IS mutual redistribution loop prevention (R2 tags, R3 filters)
2. **Route-type matching** (`external type-1`, `external type-2`, `internal`) during redistribution
3. **AS-path regex** (`_65200$`) to scope eBGP policy to routes originating in AS 65200
4. **BGP communities** — setting `65100:100` and `65100:200` at entry; propagating via iBGP with `send-community both`; matching with standard and expanded community-lists

## Quick Start

```bash
# Push lab-00 solution state as the starting baseline
python3 setup_lab.py --host <eve-ng-ip>

# Run fault injection for troubleshooting section
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>
python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>

# Restore known-good solution
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

## Files

```
lab-01-tags-regex-communities/
├── workbook.md                  ← Student workbook (start here)
├── setup_lab.py                 ← Pushes initial-configs to EVE-NG
├── initial-configs/             ← lab-00 solutions (progressive starting point)
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── solutions/                   ← Complete lab-01 reference configs
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   └── R4.cfg
├── topology/
│   ├── topology.drawio
│   └── README.md
└── scripts/fault-injection/
    ├── README.md
    ├── apply_solution.py
    ├── inject_scenario_01.py    ← Wrong community value on R1
    ├── inject_scenario_02.py    ← Redistribution broken on R2
    └── inject_scenario_03.py    ← AS-path ACL too broad on R3
```

## Topology

Four IOSv routers. Same physical layout as lab-00.

```
        [R1] 10.0.0.1/32
       / L1  \ L5
     [R2]   [R3]
       \ L2  /
        [--]
         │ L2
        [R3] 10.0.0.3/32
         │ L3
        [R4] AS 65200
```

See `topology/README.md` for the full IP table.

## Blueprint Coverage

| Ref | Objective |
|-----|-----------|
| 3.2.c | Route tags in redistribution |
| 3.2.e | Route-type matching |
| 3.2.h | AS-path regular expressions |
| 3.2.i | BGP communities — standard, expanded, well-known |
