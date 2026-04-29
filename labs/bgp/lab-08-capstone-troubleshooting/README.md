# Lab 08: BGP Comprehensive Troubleshooting — Capstone II

**Exam:** 300-510 SPRI | **Chapter:** BGP | **Difficulty:** Advanced | **Type:** Capstone II — Troubleshooting

---

## Quick Reference

| Item | Value |
|------|-------|
| Estimated time | 120 minutes |
| Devices | R1, R2, R3, R4, R5, R6, R7 |
| Platform | IOSv (R1-R4, R6) + CSR1000v (R5, R7 — for FlowSpec SAFI) |
| ASNs | 65001 (R1), 65100 (R2-R5 SP core), 65002 (R6), 65003 (R7) |
| IGP | OSPF process 1, area 0 — R2/R3/R4/R5 only |
| iBGP | R4 = Route Reflector (cluster-id 10.0.0.4); R2/R3/R5 = clients |
| eBGP sessions | R1↔R2, R1↔R3, R5↔R6, R5↔R7, R1↔R2 dynamic-neighbor |
| Planted faults | 6 concurrent, across 6 fault classes |

---

## Lab Setup

```bash
# Load pre-broken topology (6 faults baked in)
python3 setup_lab.py --host <eve-ng-ip>
```

After the exercise:

```bash
# Restore known-good state
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

---

## Design Summary

| Device | Role | ASN |
|--------|------|-----|
| R1 | Customer A CE — dual-homed to R2 (primary) and R3 (backup) | 65001 |
| R2 | PE East-1 — primary entry; tags Customer-A inbound; dynamic-neighbor listen | 65100 |
| R3 | PE East-2 — backup entry; receives prepended path from R1 | 65100 |
| R4 | P-router / Route Reflector (cluster-id 10.0.0.4) | 65100 |
| R5 | PE West — eBGP to R6 + R7; FlowSpec installer | 65100 |
| R6 | External SP Peer — MD5 + TTL-security; tags `no-export` outbound | 65002 |
| R7 | External FlowSpec originator — only originates, does not install locally | 65003 |

---

## Files

```
lab-08-capstone-troubleshooting/
├── README.md                          (this file)
├── workbook.md                        (student-facing lab guide with 6 fault tickets)
├── decisions.md                       (build decisions + fault rationale)
├── meta.yaml                          (provenance)
├── setup_lab.py                       (loads pre-broken topology)
├── initial-configs/                   (broken configs — 6 faults baked in)
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg
│   ├── R5.cfg  R6.cfg  R7.cfg
├── solutions/                         (clean known-good configs — identical to lab-07)
│   ├── R1.cfg  R2.cfg  R3.cfg  R4.cfg
│   ├── R5.cfg  R6.cfg  R7.cfg
├── topology/
│   ├── topology.drawio
│   └── README.md
└── scripts/fault-injection/
    ├── apply_solution.py
    └── README.md
```
