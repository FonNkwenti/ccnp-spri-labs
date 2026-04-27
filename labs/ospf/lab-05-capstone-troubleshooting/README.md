# Lab 05: OSPF Comprehensive Troubleshooting — Capstone II

**Exam:** 300-510 SPRI | **Chapter:** OSPF | **Difficulty:** Advanced | **Type:** Capstone II — Troubleshooting

---

## Quick Reference

| Item | Value |
|------|-------|
| Estimated time | 120 minutes |
| Devices | R1, R2, R3, R4, R5, R6 |
| Platform | IOSv |
| OSPF process | OSPFv2 process 1 + OSPFv3 process 1 |
| Area 0 | Backbone — R2, R3 |
| Area 1 | Standard — R1, R2 (ABR) |
| Area 2 | Totally Stubby — R3 (ABR), R4 |
| Area 3 | NSSA — R3 (ABR), R5 (ASBR) |
| External | R3 (ASBR) redistributes static to R6; R6 has no OSPF |
| Planted faults | 5 concurrent |

---

## Lab Setup

```bash
# Load pre-broken topology
python3 setup_lab.py --host <eve-ng-ip>
```

After the exercise:

```bash
# Restore known-good state
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

## Design Summary

| Device | Role | Areas |
|--------|------|-------|
| R1 | Area 1 internal — 3x /24 loopbacks for summarization | Area 1 |
| R2 | ABR — summarizes Area 1 to 172.16.0.0/21 (IPv4) + 2001:db8:1::/48 (IPv6) | Area 0 / Area 1 |
| R3 | Triple ABR + ASBR — redistributes static to R6, translates R5 NSSA Type-7 | Area 0 / Area 2 / Area 3 |
| R4 | Totally stubby internal — receives only default route from R3 | Area 2 |
| R5 | NSSA ASBR — redistributes Lo2 (192.168.55.0/24) as Type-7 NSSA external | Area 3 |
| R6 | External AS — no OSPF, has default static route for return-path | External |

---

## Files

```
lab-05-capstone-troubleshooting/
├── README.md                          (this file)
├── workbook.md                        (student-facing lab guide)
├── decisions.md                       (build decisions and fault rationale)
├── meta.yaml                          (provenance)
├── setup_lab.py                       (loads pre-broken topology)
├── initial-configs/                   (broken configs — 5 faults baked in)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg  R6.cfg
├── solutions/                         (clean known-good configs)
│   ├── R1.cfg  R2.cfg  R3.cfg
│   ├── R4.cfg  R5.cfg  R6.cfg
├── topology/
│   ├── topology.drawio
│   └── README.md
└── scripts/fault-injection/
    ├── apply_solution.py
    └── README.md
```
