# Lab 01: Multiarea OSPFv2 and LSA Propagation

Single-lab quick-reference guide for OSPF multiarea operations. Configure ABRs, observe Type-3 LSA propagation, and troubleshoot area mismatches.

## Blueprint Coverage

- **1.2:** Troubleshoot OSPF multiarea operations
- **1.2.a:** Route advertisement across backbone and non-backbone areas

## Prerequisites

- **Prior lab:** Lab 00 (Single-Area OSPFv2 Foundations) — this lab extends it
- **Python deps:** `netmiko` (see `labs/common/tools/eve_ng.py` for EVE-NG integration)

## Quick Start

### 1. Import Topology into EVE-NG

```bash
# In EVE-NG Web UI:
# File → Import → select topology/lab-01-multiarea-ospfv2.unl
# Start all nodes; wait for green icons (~2–3 minutes)
```

### 2. Deploy Initial Configs

```bash
python3 setup_lab.py --host <eve-ng-ip>
# Returns: 0 (full success), 1 (partial failure), 3 (EVE-NG connection error)
```

### 3. Open Lab Workbook

```bash
# Then follow the 5 lab tasks in:
cat workbook.md
```

## Files

```
lab-01-multiarea-ospfv2/
├── README.md                      # This file
├── workbook.md                    # Full lab guide (10 sections, 600+ lines)
├── setup_lab.py                   # Automated deployment script
├── topology.drawio                # Cisco topology diagram (read-only)
├── topology/
│   ├── README.md                  # EVE-NG import/export guide
│   └── lab-01-multiarea-ospfv2.unl    # EVE-NG lab file (created in EVE-NG)
├── initial-configs/
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   └── R5.cfg
└── solutions/
    ├── R1.cfg
    ├── R2.cfg
    ├── R3.cfg
    ├── R4.cfg
    └── R5.cfg
```

## What You'll Learn

- **ABR configuration:** Place routers in multiple areas
- **Type-3 LSA propagation:** Trace inter-area route advertisements
- **Area mismatches:** Diagnose and fix `area` statement errors
- **Dual-stack:** Configure OSPFv3 alongside OSPFv2 (prerequisite for lab-02)

---

**Full details:** See `workbook.md` (Section 2: Topology, Section 5: Lab Tasks, Section 9: Troubleshooting).
