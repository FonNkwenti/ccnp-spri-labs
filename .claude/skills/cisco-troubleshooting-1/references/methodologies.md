# Troubleshooting Methodologies — Full Reference

## 1. Top-Down

**When to use:**
- Problem appears at the application layer (Layer 7)
- Application-specific symptoms: DNS failures, web server errors, email issues
- Lower layers confirmed working (ping succeeds)

**Process:** Start at Layer 7, work down.
Application → Presentation → Session → Transport → Network → Data Link → Physical

**Example sequence:** Check web server logs → Verify HTTP service → Check TCP ports → Verify IP connectivity → Check switching → Verify cables

**Best for:** "Users can ping the server but can't access the website"

---

## 2. Bottom-Up

**When to use:**
- Suspected physical layer failure
- "Cable unplugged" or "link light off" scenarios
- New hardware installation issues
- Total connectivity loss

**Process:** Start at Layer 1, work up.
Physical → Data Link → Network → Transport → Session → Presentation → Application

**Example sequence:** Check cable → Verify interface status → Check switch port → Verify VLAN → Test IP connectivity → Verify routing

**Best for:** "The new switch installation isn't working" or "Link light is off"

---

## 3. Divide and Conquer (Default)

**When to use:**
- Unknown problem location
- Complex multi-layer issues
- Default when other methods aren't clearly indicated

**Process:** Start at Layer 3 (Network). Test with `ping`.
- Ping succeeds → Problem is in upper layers
- Ping fails → Problem is in lower layers

Continue dividing the remaining layers until root cause is found.

```
ping target
├─ SUCCESS → Check upper layers
│  ├─ Telnet/SSH port test
│  ├─ Application logs
│  └─ Service status
└─ FAIL → Check lower layers
   ├─ Check routing table
   ├─ Check ARP cache
   ├─ Check interface status
   └─ Check physical connectivity
```

**Best for:** "User can't reach the file server" (unclear which layer is failing)

---

## 4. Follow the Traffic Path

**When to use:**
- Multi-hop routing issues
- WAN connectivity problems
- ACL or firewall blocking suspected
- Need to find the exact failure point in the packet path

**Process:** Trace hop-by-hop from source to destination using `traceroute`.
At each hop examine: routing table, interface status, ACLs, NAT translations, QoS policies.

**Example:**
```
User PC → Switch A → Router A → WAN Link → Router B → Switch B → Server

1. Verify User PC can reach Switch A (default gateway)
2. Verify Router A has route to destination
3. Check WAN link status
4. Verify Router B receives packets
5. Check ACLs on Router B
6. Verify Server is reachable from Switch B
```

**Best for:** "Remote office can't access headquarters resources"

---

## 5. Compare Configurations

**When to use:**
- One device works, another doesn't (similar setup)
- Suspected misconfiguration
- After configuration changes
- Standardisation checking

**Process:**
1. Identify a working reference device
2. Compare section by section: interfaces, routing protocols, ACLs, VLANs, QoS
3. Flag discrepancies for investigation
4. Use `show running-config`, config diff

**Best for:** "Router A works fine but Router B with identical setup doesn't"
