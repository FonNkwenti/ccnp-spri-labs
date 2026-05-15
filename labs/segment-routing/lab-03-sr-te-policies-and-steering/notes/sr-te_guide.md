# A Comprehensive Guide to Segment Routing Traffic Engineering (SR-TE)

This guide serves as a foundational resource for students learning how modern networks manage traffic using Cisco IOS-XR. It transitions from traditional shortest-path routing to the intelligent, source-routed world of Segment Routing.

## 1. Segment Routing Traffic Engineering (SR-TE)

### Technical Explanation

Segment Routing Traffic Engineering is a method of steering traffic through a network by utilizing the concept of source routing. In traditional networks, each router along a path makes an independent decision based on its own local routing table (IGP).

In SR-TE, the Ingress Node (the source) determines the entire path for a packet and encodes this path directly into the packet header as an ordered list of instructions called Segments. On the Cisco IOS-XR platform, these segments are typically represented as MPLS labels (in SR-MPLS) or IPv6 addresses (in SRv6).

The midpoints (intermediate routers) do not need to maintain any state information about the individual tunnels passing through them. They simply look at the top segment, perform the instruction (like "forward to next node"), and "pop" the label if necessary. This statelessness allows SR-TE to scale to thousands of paths without taxing the CPU or memory of the core routers.

### The Analogical Breakdown: The Self-Driving Car

Imagine a traditional network as a train system. The train follows a fixed track. If a track is broken or congested, the train just waits because it cannot deviate from the rails laid out by the infrastructure.

SR-TE turns that packet into a Self-Driving Car.

* **The Ingress Router** is the GPS. It looks at the whole map and programs an itinerary.
* **The Segment List** is the turn-by-turn instruction list: "Go to Highway A, then take Exit 5, then arrive at Destination B."
* **The Packet** is the car. It carries the instructions with it.
* **The Midpoint Routers** are just the intersections. They don't need to know where the car started or its final destination; they just read the "current" instruction and point the car in the right direction.

### Visual Representation of the "Instruction Stack"

```
[ INGRESS ] >>> Pushes Stack >>> [ PACKET ]
* [ Segment 1: Node B ] (Midpoint reads & removes)
* [ Segment 2: Node C ] (Midpoint reads & removes)
* [ Segment 3: Egress ]
```

---

## 2. Affinity Maps and Link Constraints

### Technical Explanation

In a complex network, not all links are equal. Some are high-capacity fiber, others might be low-bandwidth satellite links, and some might be physically "unsecured." Affinities (also known as Admin Groups) allow operators to "color" or tag these links based on their physical properties.

The Affinity Map is a 32-bit bitmask where each bit represents a specific attribute. For example, Bit 0 might be "Gold-Link" and Bit 1 might be "Low-Latency." These attributes are advertised throughout the network using link-state protocols like OSPF or IS-IS.

Affinity Constraints are the logic rules applied to an SR-TE policy to filter the topology:

* **Include-Any**: The path must include at least one of the specified colors.
* **Include-All**: The path must include every one of the specified colors.
* **Exclude-Any**: The path must strictly avoid any links with the specified colors.

### The Analogical Breakdown: Painting the Roads

Think of your network as a massive city map. You decide to go out and physically paint the surface of the roads.

* You paint all the high-speed highways Green.
* You paint all the bumpy, dirt roads Brown.
* You paint the bridges over water Blue.

When you program your GPS (the SR-TE Policy), you set a Constraint (Filter). If you tell the GPS "Exclude Brown," it will calculate a path that might be longer in distance but never touches a dirt road. If you say "Include-All Green and Blue," the GPS will only find a path that stays on highways and uses a bridge.

### Cisco IOS-XR Implementation Flow

To implement link constraints on IOS-XR, the flow follows a four-step logical hierarchy:

1. **Global Dictionary Definition**: You first create a global affinity map. This acts as your legend, where you assign a human-readable name (like "GOLD") to a specific bit position in the 32-bit mask.
2. **Interface Application**: You navigate to the specific physical interfaces and assign them to an "admin-group" using the names you defined in your dictionary. This is where the "painting" happens.
3. **IGP Distribution**: You must ensure your routing protocol (IS-IS or OSPF) is configured to "advertise" these link attributes. Without this, other routers won't know which links are "GOLD."
4. **Policy Constraint Logic**: Within the SR-TE policy configuration, you create an attribute set. This is where you define the rule (e.g., "I only want links that are GOLD") which the router uses to calculate the path.

### Visual Flow of Topology Filtering

```
**PHYSICAL NETWORK**
[A] --(RED)-- [B]
|
(GRN)
|
[C] --(GRN)-- [D]

**LOGICAL TOPOLOGY (Constraint: Exclude RED)**
[A]
| (Link Ignored)
(GRN)
|
[B]
(GRN)
|
[C] --(GRN)-- [D] <== Valid Path
```

---

## 3. Color-Based Automated Steering

### Technical Explanation

Once you have defined your paths (SR-TE Policies), you need a way to move traffic into them. Automated Steering is the "glue" between a service (like a L3VPN or a specific BGP route) and an SR-TE policy.

This mechanism relies on the BGP Color Extended Community. When a router at the far end of the network advertises a route, it attaches a "Color" value. The Ingress router receives this route and checks its local SR-TE database. If it finds a policy that matches both the Endpoint (the BGP Next-Hop) and the Color, it automatically steers the traffic into that policy. This is often referred to as On-Demand Next-Hop (ODN) steering.

### The Analogical Breakdown: The VIP Ticket

Imagine a large airport with multiple boarding gates. The SR-TE Policy is a specialized Shuttle waiting at a specific gate. One shuttle goes to "The City" via the "Scenic Route" (Color 100), and another goes to "The City" via the "Express Highway" (Color 200).

The Packet is the passenger. The BGP Route is the passenger's ticket. When the passenger arrives at the terminal, the gate agent (the Ingress Router) looks at their ticket. If the ticket is stamped with "Color 200", the agent doesn't send them to the standard bus; they automatically guide them to the "Express Highway" shuttle. The passenger didn't have to ask for the express route; the Color on their ticket made the decision happen automatically.

### Cisco IOS-XR Implementation Flow

Setting up automated steering on IOS-XR involves aligning the service layer with the transport layer:

1. **Policy Template Creation**: You define a "Policy" in the Segment Routing configuration. This policy is explicitly assigned a numerical Color value (e.g., 100) and a target Endpoint (the IP of the egress router).
2. **Route Policy (BGP) Tagging**: On the Egress router, you create a BGP route-policy. This policy "sets" the color community attribute on specific prefixes before they are advertised to the rest of the network.
3. **Service Mapping**: On the Ingress router, you configure BGP to look for these color communities. When a match is found, the router doesn't just look at its standard routing table; it looks at the SR-TE database.
4. **On-Demand Instantiation**: You can configure the router to "dynamically" build the path the moment it sees a new color, or simply "steer" into a path that you have already pre-defined.

### The Handshake Flow

```
[ SERVICE ROUTE ]
Dest: 10.1.1.0/24
Next-Hop: 5.5.5.5
Color: 200

<-- MATCH? -->

[ SR-TE POLICY ]
Name: "Express"
Endpoint: 5.5.5.5
Color: 200

(AUTOMATED STEER)
```

---

## 4. Why Use This? (SR-TE vs. The Old Way)

In the older "RSVP-TE" model, every router in the middle had to maintain a "state" (a memory) of every single tunnel. This was like a waiter trying to remember 1,000 different drink orders at once. Eventually, the waiter gets overwhelmed.

SR-TE is like a buffet. The waiter (the network) provides the food (the links), but the guest (the...
