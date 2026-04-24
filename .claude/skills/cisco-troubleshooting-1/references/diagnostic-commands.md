# Phase III: Diagnostic Execution — Full Reference

## Connecting to EVE-NG Routers via Netmiko

Use this pattern to connect to any router. Console ports are dynamic — read from the workbook's Console Access Table (populated from EVE-NG web UI after lab creation).

```python
from netmiko import ConnectHandler

conn = ConnectHandler(
    device_type="cisco_ios_telnet",  # or "cisco_ios" for SSH
    host="<eve-ng-ip>",              # EVE-NG server IP
    port=32768,                      # dynamic port from Console Access Table
    username="",
    password="",
    secret="",
    timeout=10,
)

output = conn.send_command("show ip route")
print(output)
conn.disconnect()
```

For interactive troubleshooting, connect directly via telnet:
```bash
telnet localhost 5001   # R1
telnet localhost 5002   # R2
```

---

## CLI Command Library

### Interface & Physical Layer
```
show interfaces [interface-id]
show ip interface brief
show interfaces status
show interfaces trunk
show cdp neighbors detail
```

### Routing — General
```
show ip route
show ip route [prefix]
show ip protocols
show route-map
show ip prefix-list
```

### EIGRP
```
show ip eigrp neighbors
show ip eigrp topology
show ip eigrp topology all-links
show ip eigrp interfaces
show ip eigrp traffic
debug eigrp packets
```

### OSPF
```
show ip ospf neighbor
show ip ospf interface
show ip ospf database
show ip ospf interface [interface]
debug ip ospf adj
debug ip ospf events
```

### BGP
```
show ip bgp summary
show ip bgp neighbors
show ip bgp [prefix]
show ip bgp neighbors [ip] advertised-routes
show ip bgp neighbors [ip] received-routes
debug ip bgp [ip] updates
```

### Layer 2
```
show mac address-table
show vlan brief
show spanning-tree
show interfaces trunk
```

### Security & ACLs
```
show ip access-lists
show access-lists
show ip nat translations
show ip nat statistics
```

### System
```
show version
show logging
show clock
```

---

## Gathering Evidence from Both Sides

For adjacency or reachability issues, always connect to both sides:

```bash
# Check OSPF neighbor state on both sides
telnet localhost 5001   # R1 — show ip ospf neighbor
telnet localhost 5002   # R2 — show ip ospf neighbor
```

Compare outputs side-by-side to identify mismatches (timers, authentication, area IDs, network statements, K-values, etc.).

---

## Baseline Comparison Pattern

| Source | Use For |
|--------|---------|
| `initial-configs/[device].cfg` | What was pre-configured (starting state) |
| `solutions/[device].cfg` | What the correct end-state should look like |
| `workbook.md` Verification section | Expected `show` command outputs |

Cross-reference live output against these files to identify what is missing or wrong.

---

## Evidence Table Template

| Component | Expected | Observed | Status |
|-----------|----------|----------|--------|
| Interface Fa0/0 | Up/Up | Up/Up | ✓ OK |
| EIGRP neighbor R2 | Peer state | Down | ✗ FAULT |
| Route 10.5.0.0/16 | Present | Missing | ✗ FAULT |

---

## Hypothesis Template

```
Hypothesis: [e.g., "OSPF neighbor failing due to Hello timer mismatch"]
Test:        show ip ospf interface on both sides
Expected:    Matching hello/dead intervals
Actual:      R1 hello=10, R2 hello=20
Conclusion:  Confirmed — timer mismatch preventing adjacency
```

Iterate through hypotheses until root cause is confirmed.
