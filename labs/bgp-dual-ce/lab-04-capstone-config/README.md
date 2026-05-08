# Lab 04 — BGP Dual-CE Full Protocol Mastery (Capstone I)

Topic: `bgp-dual-ce` · Difficulty: **Advanced** · Time: **120 min** · Devices: R1–R6

Build the complete dual-CE / dual-ISP BGP topology from a clean slate. Customer
AS 65001 (R1, R2) is multihomed to two unrelated providers, ISP-A (AS 65100) and
ISP-B (AS 65200). Configure CE-CE iBGP, both eBGP edges, ISP-internal iBGP, transit
prevention, AS-path-prepend inbound TE, LOCAL_PREF outbound TE, and selective /25
advertisement — see `workbook.md` for the full task list.

## Files

| Path | Purpose |
|---|---|
| `workbook.md` | Lab walkthrough, task list, verification cheatsheet, solutions |
| `solutions/{R1..R6}.cfg` | Reference configurations |
| `initial-configs/{R1..R6}.cfg` | Clean-slate baseline (interfaces only, no BGP) |
| `topology/topology.drawio` | Importable EVE-NG topology |
| `topology/README.md` | Topology import notes |
| `setup_lab.py` | Pushes initial configs to all six routers |
| `meta.yaml` | Machine-readable lab metadata |
| `decisions.md` | Build decisions and model-gate provenance |

## Run

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

Open `workbook.md` and start at Section 1.

## Paired troubleshooting capstone

Once you can build the topology cleanly, work the diagnostic counterpart:
[`../lab-05-capstone-troubleshooting`](../lab-05-capstone-troubleshooting/).
