# Lab 01: Multiarea OSPFv2 — EVE-NG Topology Guide

## Topology Summary

**Device count:** 5 (R1–R5, all IOSv)  
**Link count:** 4 point-to-point Gigabit links  
**Topology type:** Multiarea OSPF hub-and-spoke around backbone (Area 0)  

| Area | Devices | Role |
|------|---------|------|
| 0 (Backbone) | R2, R3 | Direct backbone link (R2↔R3) |
| 1 | R1, R2 | R1 internal; R2 is ABR |
| 2 | R3, R4 | R4 internal; R3 is ABR |
| 3 | R3, R5 | R5 internal; R3 is ABR |

## EVE-NG Import Instructions

1. **Download the lab file** (if not already present):
   - Lab `.unl` file: `labs/ospf/lab-01-multiarea-ospfv2/` (created in EVE-NG)

2. **Import into EVE-NG:**
   - Open EVE-NG Web UI → File → Import
   - Select the `.unl` file and confirm
   - EVE-NG auto-creates the 5 IOSv nodes and 4 links

3. **Verify import:**
   - Check the Topology tab; you should see R1, R2, R3, R4, R5
   - All links should show green when nodes boot successfully

## Node Configuration Reference

| Device | EVE-NG Template | RAM (MB) | Image |
|--------|-----------------|----------|-------|
| R1 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R2 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R3 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R4 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |
| R5 | Cisco IOSv | 512 | vios-adventerprisek9-m.SPA.156-2.T |

> **Note:** If you do not have the `vios-adventerprisek9-m.SPA.156-2.T` image, substitute any recent IOSv image (e.g., 16.9.4, 17.3.1). OSPF behavior is consistent across recent IOS versions.

## Starting the Lab

1. **Start all nodes:**
   - In EVE-NG UI, right-click on the topology → **Start all nodes**
   - Wait 2–3 minutes for all routers to fully boot (watch for green node icons)

2. **Open a console:**
   - Right-click on each router → Console
   - Default credentials: `cisco` / `cisco` (or empty password, depending on image)

3. **Verify connectivity:**
   - Ping between adjacent routers on direct links:
     ```
     R1# ping 10.1.12.2
     R2# ping 10.1.23.3
     ```
   - All pings should succeed (links operational)

## Exporting the Lab

After you make topology changes in EVE-NG (e.g., add a device, change IP addresses):

1. **Export to file:**
   - Right-click on the topology → File → Export
   - Save as `lab-01-multiarea-ospfv2.unl` in the same directory

2. **Version control (optional):**
   - Commit the `.unl` file to the lab repository so team members can import your changes

## File Locations

```
labs/ospf/lab-01-multiarea-ospfv2/
├── topology.drawio               # Cisco-style diagram (read-only, auto-generated)
├── topology/
│   ├── README.md                 # This file
│   └── lab-01-multiarea-ospfv2.unl   # EVE-NG import file (created in EVE-NG)
├── initial-configs/              # Pre-loaded configs (IP + hostnames only)
├── solutions/                    # Complete OSPF solution configs
├── workbook.md                   # Lab exercises and solutions
└── setup_lab.py                  # Automated config deployment script
```

## Troubleshooting EVE-NG Import

| Problem | Solution |
|---------|----------|
| "IOSv image not found" | Download the image from Cisco or substitute a compatible IOSv version |
| "Import fails with XML error" | Ensure `.unl` file is valid XML; re-export from a working EVE-NG instance |
| "Nodes boot but links stay red" | Verify cables are connected in EVE-NG; sometimes requires reboot of nodes |
| "Can't telnet to node after boot" | Check EVE-NG console port in the Web UI; use `telnet <eve-ng-ip> <port>` |

---

For detailed lab instructions, see `workbook.md` in the parent directory.
