In an Ethernet multi-access link (like a standard LAN), OSPF (Open Shortest Path First) elects a **Designated Router (DR)** and a **Backup Designated Router (BDR)** to manage adjacencies and minimize routing update traffic. Without a DR, every router would have to form a relationship with every other router, leading to a "mesh" of traffic that scales poorly.

Here is the step-by-step breakdown of how that selection process works.

---

### 1. The Eligibility Check

Before the election starts, routers check their interface configuration. A router can only become a DR if:

* Its OSPF **Priority** is set to a value between **1 and 255**.
* If the Priority is set to **0**, the router is ineligible and will remain a **DROther**.

### 2. The Election Criteria

When the "Wait Timer" expires (usually 40 seconds, matching the Dead Interval), the routers on the segment look at two specific pieces of data in the Hello packets:

| Criteria | Description |
| :--- | :--- |
| **OSPF Priority** | The highest priority wins. The default is **1**. |
| **Router ID (RID)** | If priorities are tied, the router with the **highest Router ID** wins. |

> **Note:** The Router ID is determined by the manually configured ID, the highest loopback IP address, or the highest physical interface IP address (in that order).

### 3. The Two-Step Election Logic

The election actually happens "bottom-up" to ensure stability:

1. **BDR Election:** The routers first elect a BDR based on the highest priority/RID.
2. **DR Election:** If no DR already exists, the newly elected BDR is promoted to DR, and a new BDR election is held.

### 4. The "Wait Timer" and Preemption

One of the most important things to remember about DR selection is that it is **not preemptive**.

* **First Come, First Served:** If a router with a Priority of 1 boots up and becomes the DR, and then a "better" router with a Priority of 255 joins the link later, the new router **will not** take over.
* **Stability:** The DR only changes if the current DR fails or the OSPF process is manually cleared/restarted. This prevents the network from constantly recalculating adjacencies every time a high-priority router reboots.

---

### Summary of the Adjacency State

Once the election is over, the routers settle into these roles:

* **DR and BDR:** Form full adjacencies with all other routers.
* **DROther:** Only forms a full adjacency with the DR and BDR. Between two DROthers, the state stays at **2-WAY**, meaning they know each other exist but don't swap detailed routing tables.

$$Total\ Adjacencies = n$$
*(Where $n$ is the number of routers. Without a DR, this would be $\frac{n(n-1)}{2}$)*

To watch the OSPF adjacency process unfold in real-time on a Cisco router, the most effective command is `debug ip ospf adj`.

This command allows you to see the transition through the various OSPF states—from **Down** to **Init**, **2-Way**, **ExStart**, **Exchange**, **Loading**, and finally **Full**.

---

### Key Debug Commands

| Command | Purpose |
| :--- | :--- |
| `debug ip ospf adj` | Shows adjacency events (DR/BDR election, state changes, and DBD exchange). |
| `debug ip ospf hello` | Shows the "Hello" packets being sent/received (useful if neighbors aren't even reaching the **Init** state). |
| `debug ip ospf packet` | A "loud" command that shows detailed information about every OSPF packet type. |

### What to Look For

When you run `debug ip ospf adj`, you will see transitions like these in the console logs:

1. **2-WAY:** You'll see the router recognize a neighbor and decide whether to become a DR, BDR, or DROther.
2. **EXSTART:** The routers decide who is the "Master" and who is the "Slave" for the database exchange (based on Router ID).
3. **EXCHANGE/LOADING:** The routers describe their databases and request specific link-state information.
4. **FULL:** The goal state where the databases are synchronized.

---

### ⚠️ Important Best Practices

1. **Logging to Buffer:** Debugs can overwhelm the CPU and the console line. It is usually safer to log to the local buffer rather than the active terminal:

    ```bash
    conf t
    no logging console
    logging buffered 16384
    end
    debug ip ospf adj
    ```

2. **Turning it Off:** Once you have gathered your data, use `undebug all` (or `un all`) to stop the process immediately.
3. **Terminal Monitor:** If you are connected via SSH or Telnet, remember to type `terminal monitor` to actually see the debug output on your screen.

```bash
R1#debug ip os adj
OSPF adjacency debugging is on
R1#
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Cannot see ourself in hello from 10.0.0.2, state INIT
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Neighbor change event
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: DR/BDR election
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Elect BDR 10.0.0.1
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Elect DR 10.0.0.1
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Elect BDR 0.0.0.0
*Apr 26 11:44:20.549: OSPF-1 ADJ   Gi0/0: Elect DR 10.0.0.1
*Apr 26 11:44:20.550: OSPF-1 ADJ   Gi0/0: DR: 10.0.0.1 (Id)
*Apr 26 11:44:20.550: OSPF-1 ADJ   Gi0/0:    BDR: none
*Apr 26 11:44:20.550: OSPF-1 ADJ   Gi0/0: Remember old DR 10.0.0.2 (id)
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: 2 Way Communication to 10.0.0.2, state 2WAY
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: Neighbor change event
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: DR/BDR election
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: Elect BDR 10.0.0.2
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: Elect DR 10.0.0.1
*Apr 26 11:44:20.554: OSPF-1 ADJ   Gi0/0: DR: 10.0.0.1 (Id)
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0:    BDR: 10.0.0.2 (Id)
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: Nbr 10.0.0.2: Prepare dbase exchange
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: Send DBD to 10.0.0.2 seq 0x3A0 opt 0x52 flag 0x7 len 32
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: Neighbor change event
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: DR/BDR election
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: Elect BDR 10.0.0.2
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: Elect DR 10.0.0.1
*Apr 26 11:44:20.555: OSPF-1 ADJ   Gi0/0: DR: 10.0.0.1 (Id)
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0:    BDR: 10.0.0.2 (Id)
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0: Neighbor change event
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0: DR/BDR election
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0: Elect BDR 10.0.0.2
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0: Elect DR 10.0.0.1
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0: DR: 10.0.0.1 (Id)
*Apr 26 11:44:20.556: OSPF-1 ADJ   Gi0/0:    BDR: 10.0.0.2 (Id)
*Apr 26 11:44:20.557: OSPF-1 ADJ   Gi0/0: Rcv DBD from 10.0.0.2 seq 0x2BB opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Apr 26 11:44:20.557: OSPF-1 ADJ   Gi0/0: NBR Negotiation Done. We are the SLAVE
*Apr 26 11:44:20.557: OSPF-1 ADJ   Gi0/0: Nbr 10.0.0.2: Summary list built, size 3
*Apr 26 11:44:20.558: OSPF-1 ADJ   Gi0/0: Send DBD to 10.0.0.2 seq 0x2BB opt 0x52 flag 0x2 len 92
*Apr 26 11:44:20.561: OSPF-1 ADJ   Gi0/0: Rcv DBD from 10.0.0.2 seq 0x2BC opt 0x52 flag 0x1 len 32  mtu 1500 state EXCHANGE
*Apr 26 11:44:20.561: OSPF-1 ADJ   Gi0/0: Exchange Done with 10.0.0.2
*Apr 26 11:44:20.561: OSPF-1 ADJ   Gi0/0: Synchronized with 10.0.0.2, state FULL
*Apr 26 11:44:20.561: %OSPF-5-ADJCHG: Process 1, Nbr 10.0.0.2 on GigabitEthernet0/0 from LOADING to FULL, Loading Done
*Apr 26 11:44:20.561: OSPF-1 ADJ   Gi0/0: Send DBD to 10.0.0.2 seq 0x2BC opt 0x52 flag 0x0 len 32
R1#u all
```

This is a textbook example of OSPF coming to life! Since you've captured the full sequence, let's break down exactly what happened between **R1** (10.0.0.1) and its neighbor **10.0.0.2** based on those logs.

---

### The Breakdown of Your Debug

#### 1. The Discovery (INIT State)
>
> `Cannot see ourself in hello from 10.0.0.2, state INIT`

R1 received a Hello packet from 10.0.0.2, but 10.0.0.2 hadn't seen R1 yet (R1's ID wasn't in the neighbor list of that Hello packet). This is the definition of the **INIT** state.

#### 2. The DR/BDR Election
>
> `Elect BDR 10.0.0.2`  
> `Elect DR 10.0.0.1`

Notice how it runs the election multiple times in the logs. Since R1 (10.0.0.1) likely has the lower Router ID or was already active, it took the **DR** role, and 10.0.0.2 was elected the **BDR**.

#### 3. Master/Slave Negotiation (EXSTART)
>
> `Rcv DBD from 10.0.0.2 ... state EXSTART`  
> `NBR Negotiation Done. We are the SLAVE`

In the **ExStart** state, the routers decide who controls the database exchange. The router with the **highest Router ID** becomes the **Master**.

* Since **10.0.0.2 > 10.0.0.1**, R1 identifies itself as the **Slave**.
* R1 then adopts the sequence number (`0x2BB`) set by the Master (10.0.0.2).

#### 4. The Handshake (EXCHANGE & LOADING)
>
> `Exchange Done with 10.0.0.2`  
> `Synchronized with 10.0.0.2, state FULL`

R1 sends its Summary List (what it knows) and receives 10.0.0.2's list. Once they've both requested and received any missing pieces, they hit the **FULL** state.

---

### Key Takeaways from your Log

* **Speed:** The entire process from seeing the neighbor to reaching `FULL` took about **12 milliseconds** (`.549` to `.561`).
* **Role:** Your router (R1) is the **DR** for this segment.
* **MTU Check:** You can see `mtu 1500` in the DBD packets. If these numbers didn't match on both sides, the adjacency would have hung at **EXSTART**.
