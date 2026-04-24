---
name: drawio
description: Visual style guide and workflow for creating Cisco network topology diagrams in Draw.io. Use when generating a topology diagram, creating or updating a topology.drawio file, exporting a PNG, or when any other skill needs to produce or validate a network diagram.
---

# Draw.io Diagram Skill

-# Instructions

--# 1. Locations

Store diagrams in the following directories based on their type:

- **Topology Diagrams**: `labs/<topic>/lab-NN-<slug>/topology.drawio`
  - Use for network topologies, physical cabling, and logical connectivity.
- **Flow Diagrams**: `labs/<topic>/lab-NN-<slug>/flow-[description].drawio`
  - Use for packet flows, process charts, and logic flows.

--# 2. File Formats & Deliverables

The only required deliverable is:

1.  **Source File (`.drawio`)**: The editable XML format. This is the canonical diagram file.

--# 3. Naming Conventions

- Use **kebab-case** for all filenames.
- **Pattern**: `[lab-name]-[diagram-type].extension`
- **Examples**:
  - `eigrp-basic-adjacency-topology.drawio`
  - `packet-flow-vlan-routing.drawio`

--# 4. Visual Style Guide

This section defines the canonical visual style for all topology diagrams. Every generated `.drawio` file **must** follow these rules.

> **Reference file**: `references/style-guide-reference.drawio` — a complete, validated example diagram. Read it when generating a new diagram to confirm style compliance before producing output.

### 4.1 Canvas & Layout

- **Background**: `#1a1a2e` (dark navy). Set in the `<mxGraphModel background="#1a1a2e">` attribute of the XML root element.
- **Title**: Positioned at the **top center** of the canvas. Bold, 16pt, white text.
- **Legend Box**: Required in every diagram. Positioned at the **bottom-right** corner. Black fill (`#000000`) with white text (`#FFFFFF`), rounded corners, 10pt font.

### 4.2 Device Icons

- Use the **Cisco19** shape library (`mxgraph.cisco19`). Do NOT use the older `mxgraph.cisco` library.
- All devices: `width="60" height="60"` (use `width="50" height="40"` for end hosts/workstations).
- **Style Strings** (include `sketch=0;html=1;aspect=fixed;pointerEvents=1;` on every icon):

  - **Router**:
    ```
    sketch=0;points=[[0.5,0,0],[1,0.5,0],[0.5,1,0],[0,0.5,0],[0.145,0.145,0],[0.8555,0.145,0],[0.855,0.8555,0],[0.145,0.855,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.rect;prIcon=router;fillColor=#FAFAFA;strokeColor=#005073;
    ```
  - **L3 Switch**:
    ```
    sketch=0;points=[[0.015,0.015,0],[0.985,0.015,0],[0.985,0.985,0],[0.015,0.985,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0.25,0],[1,0.5,0],[1,0.75,0],[0.75,1,0],[0.5,1,0],[0.25,1,0],[0,0.75,0],[0,0.5,0],[0,0.25,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.rect;prIcon=l3_switch;fillColor=#FAFAFA;strokeColor=#005073;
    ```
  - **L2 Switch**:
    ```
    sketch=0;points=[[0.015,0.015,0],[0.985,0.015,0],[0.985,0.985,0],[0.015,0.985,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0.25,0],[1,0.5,0],[1,0.75,0],[0.75,1,0],[0.5,1,0],[0.25,1,0],[0,0.75,0],[0,0.5,0],[0,0.25,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.rect;prIcon=workgroup_switch;fillColor=#FAFAFA;strokeColor=#005073;
    ```
  - **Cloud/Internet**:
    ```
    sketch=0;points=[[0,0.64,0],[0.2,0.15,0],[0.4,0.01,0],[0.79,0.25,0],[1,0.65,0],[0.8,0.86,0],[0.41,1,0],[0.16,0.86,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.cloud;fillColor=#6B6B6B;strokeColor=none;
    ```
  - **Workstation/PC/VPC**:
    ```
    sketch=0;points=[[0.03,0.03,0],[0.5,0,0],[0.97,0.03,0],[1,0.4,0],[0.97,0.745,0],[0.5,1,0],[0.03,0.745,0],[0,0.4,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.workstation;fillColor=#005073;strokeColor=none;
    ```

### 4.3 Device Labels

Labels are **embedded in the device cell `value`** as HTML — NOT as separate text cells.

- **Format**: `<b style="color:#FFFFFF;">HOSTNAME</b><br><font color="#CCCCCC" style="font-size:10px;">ROLE<br>Lo0: IP/MASK</font>`
- **Hostname**: white bold text.
- **Role and Loopback**: `#CCCCCC` gray, 10px.

Label **position** is controlled by adding these attributes to the device's style string:

| Placement | Style attributes to append |
|-----------|---------------------------|
| **Below** (default) | `verticalLabelPosition=bottom;verticalAlign=top;align=center;labelPosition=center;` |
| **Right** of icon | `verticalLabelPosition=middle;verticalAlign=middle;align=left;labelPosition=right;` |
| **Left** of icon | `verticalLabelPosition=middle;verticalAlign=middle;align=right;labelPosition=left;` |

#### 4.3.1 Smart Label Placement — Empty Side Rule

Labels **must not overlap any connection lines**. Choose the placement based on which side has **no connections**:

| Condition | Placement |
|-----------|-----------|
| All physical neighbors are **below** the device | Label **below** (`verticalLabelPosition=bottom`) |
| All physical neighbors are to the **left** | Label **right** (`labelPosition=right`) |
| All physical neighbors are to the **right** | Label **left** (`labelPosition=left`) |
| Neighbors on both sides or above+below | Label **left** (default fallback) |

**Examples from EIGRP Lab 08:**
- **R2** is at x=500. All neighbors (R1 at x=400, R3 at x=400) are to the LEFT → label goes **RIGHT** (`labelPosition=right`).
- **R6** is at x=200. Its neighbor R1 is at x=400, which is to the RIGHT → label goes **LEFT** (`labelPosition=left`).

### 4.4 Connection Lines

- **Color**: **White** (`#FFFFFF`). Never black.
- **Style String**: `endArrow=none;html=1;strokeWidth=2;strokeColor=#FFFFFF;fillColor=#f5f5f5;`
- **Dashed Links** (tunnels): `endArrow=none;html=1;strokeWidth=2;strokeColor=#FFFFFF;fillColor=#f5f5f5;dashed=1;`
- **Edge Labels** (interface names + subnet): Centered on the link. 10pt. Include interface pair and subnet on separate lines.
  - Example value: `Fa1/0 - Fa0/0\n10.12.0.0/30`

### 4.5 IP Last Octet Labels

- **Required**: Every router interface endpoint must have a small label showing the **last octet** of its IP address (e.g., `.1`, `.2`).
- **Position**: Near the router's side of the connection line, close to the interface.
  - Use the router's X + ~50px (to the right of the icon edge).
  - Y coordinate near the interface exit point on the router.
- **Style**: `edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;`
- **Purpose**: Allows instant identification of which IP belongs to which router without reading the full subnet label.

### 4.6 Legend Box

Every diagram must include a legend box with the following properties:

- **Position**: Bottom-right area of the canvas.
- **Fill**: Black (`#000000`).
- **Font Color**: White (`#FFFFFF`).
- **Border**: Rounded, white stroke.
- **Style**: `rounded=1;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#FFFFFF;fontColor=#FFFFFF;fontSize=10;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;`
- **Content**: Key information for reading the diagram:
  - OSPF Area designations (if applicable)
  - Link type indicators (solid = physical, dashed = tunnel)
  - Any cost or metric annotations
  - Protocol identifiers (OSPF Process ID, EIGRP AS, etc.)

### 4.7 Reference XML Snippets

**Canvas root (always set background):**
```xml
<mxGraphModel background="#1a1a2e">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- zone shapes first, then devices, then links -->
  </root>
</mxGraphModel>
```

**Title Cell:**
```xml
<mxCell id="title" value="&lt;font style=&quot;font-size:16px;&quot; color=&quot;#FFFFFF&quot;&gt;&lt;b&gt;Lab N: Title Here&lt;/b&gt;&lt;/font&gt;" style="text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;strokeColor=none;fillColor=none;" vertex="1" parent="1">
  <mxGeometry x="200" y="20" width="500" height="35" as="geometry" />
</mxCell>
```

**Router icon — label below (hub/top device):**
```xml
<mxCell id="R1" value="&lt;b style=&quot;color:#FFFFFF;&quot;&gt;R1&lt;/b&gt;&lt;br&gt;&lt;font color=&quot;#CCCCCC&quot; style=&quot;font-size:10px;&quot;&gt;Hub Router&lt;br&gt;Lo0: 10.0.0.1/32&lt;/font&gt;"
  style="sketch=0;points=[[0.5,0,0],[1,0.5,0],[0.5,1,0],[0,0.5,0],[0.145,0.145,0],[0.8555,0.145,0],[0.855,0.8555,0],[0.145,0.855,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.rect;prIcon=router;fillColor=#FAFAFA;strokeColor=#005073;verticalLabelPosition=bottom;verticalAlign=top;align=center;labelPosition=center;"
  vertex="1" parent="1">
  <mxGeometry x="400" y="200" width="60" height="60" as="geometry" />
</mxCell>
```

**Router icon — label to the right:**
```xml
<mxCell id="R2" value="&lt;b style=&quot;color:#FFFFFF;&quot;&gt;R2&lt;/b&gt;&lt;br&gt;&lt;font color=&quot;#CCCCCC&quot; style=&quot;font-size:10px;&quot;&gt;Branch A&lt;br&gt;Lo0: 10.0.0.2/32&lt;/font&gt;"
  style="sketch=0;points=[[0.5,0,0],[1,0.5,0],[0.5,1,0],[0,0.5,0],[0.145,0.145,0],[0.8555,0.145,0],[0.855,0.8555,0],[0.145,0.855,0]];html=1;aspect=fixed;pointerEvents=1;shape=mxgraph.cisco19.rect;prIcon=router;fillColor=#FAFAFA;strokeColor=#005073;verticalLabelPosition=middle;verticalAlign=middle;align=left;labelPosition=right;"
  vertex="1" parent="1">
  <mxGeometry x="600" y="400" width="60" height="60" as="geometry" />
</mxCell>
```

**White Connection Line:**
```xml
<mxCell id="link_R1_R2" value="" style="endArrow=none;html=1;strokeWidth=2;strokeColor=#FFFFFF;fillColor=#f5f5f5;" edge="1" parent="1" source="R1" target="R2">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

**IP Last Octet Label:**
```xml
<mxCell id="R1_Fa0_0_octet" value=".1" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;" vertex="1" connectable="0" parent="1">
  <mxGeometry x="450" y="270" as="geometry" />
</mxCell>
```

**Legend Box:**
```xml
<mxCell id="legend" value="&lt;b&gt;LEGEND&lt;/b&gt;&lt;br&gt;━━━  Physical Link&lt;br&gt;[blue box] Area 0 Backbone&lt;br&gt;OSPF Process ID: 1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#FFFFFF;fontColor=#FFFFFF;fontSize=10;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;arcSize=3;" vertex="1" parent="1">
  <mxGeometry x="620" y="650" width="180" height="100" as="geometry" />
</mxCell>
```

### 4.8 Layout Rules — Avoiding Link Overlap

**Critical Rule**: A connection line must NEVER visually cross through an intermediate device. This happens when three or more devices share the same X coordinate in a vertical chain and a "bypass" link connects non-adjacent devices.

**Problem Pattern** (DO NOT USE when bypass links exist):
```
  R1 (400, 200)    ← bypass link R1→R3 draws a straight
  |                   vertical line through R2
  R2 (400, 400)
  |
  R3 (400, 600)
```

**Solution**: When a bypass link exists between two devices that have intermediate devices at the same X coordinate, **offset the intermediate device(s) horizontally** to create a triangle or staggered layout.

**Correct Pattern** — Offset R2 to create a clear triangle:
```
       R1 (400, 200)
      / \
     /   \              R1→R3 link has clear path on the left
    /     \
  R2 (500, 400)        R2 shifted right by ~100px
    \
     \
      R3 (400, 600)
```

**General Rules**:
1. **Detect bypass links**: Before placing devices, check if any link connects two devices that skip over intermediate devices in the vertical chain.
2. **Offset intermediate devices**: Shift the intermediate device(s) horizontally by at least 100px to create visual separation.
3. **Preferred offset direction**: Shift RIGHT (increase X) unless the right side is occupied by another device (R4, R7), in which case shift LEFT.
4. **Label adjustment**: When a device is offset, its label position must follow — labels go to the LEFT of the device icon, or ABOVE if the left side is crowded.
5. **Octet label adjustment**: IP last-octet labels must be repositioned to remain near their respective interface endpoints after any coordinate changes.

**When bypass links are NOT present** (pure linear chain R1→R2→R3 with no R1→R3 link), the standard vertical column layout at the same X is fine.

### 4.9 Overlay / Tunnel Lines

Tunnel overlays represent **logical connections** that run on top of the physical topology. They must be visually distinct from physical links.

#### 4.9.1 Style Rules

| Property | Value |
|----------|-------|
| Stroke width | `1` (thinner than physical `2`) |
| Dash pattern | `dashed=1;dashPattern=1 4;` (tiny dots, wide gaps) |
| Arrow | `endArrow=none;` |
| Exit point | Top center of source: `exitX=0.5;exitY=0;exitDx=0;exitDy=0;` |
| Entry point | Top center of target: `entryX=0.5;entryY=0;entryDx=0;entryDy=0;` |
| Curve | `curved=1;` |

#### 4.9.2 Color Coding by Tunnel Type

| Tunnel Type | Color | Hex |
|-------------|-------|-----|
| GRE | White | `#FFFFFF` |
| MPLS | Orange | `#FF6600` |
| IPsec VPN | Red | `#FF0000` |
| VXLAN | Cyan | `#00AAFF` |
| L2TP | Purple | `#AA00FF` |
| Other/Unknown | Yellow | `#FFFF00` |

#### 4.9.3 Arc Routing — Curving Over Intermediate Devices

Tunnel lines must arc **above** the physical topology, not route through intermediate devices.

**Algorithm**: Use two waypoints that position the line above both endpoints:
- `arc_y = min(source_y, target_y) - 100` (100px above the higher device)
- Waypoint 1: `(source_x + 39, arc_y)` — above source icon center
- Waypoint 2: `(target_x + 39, arc_y)` — above target icon center

**Example XML** (GRE tunnel R1→R6, R1 at 400,200 and R6 at 200,200):
```xml
<mxCell id="tunnel_R1_R6" value="" style="endArrow=none;html=1;strokeWidth=1;strokeColor=#FFFFFF;fillColor=none;dashed=1;dashPattern=1 4;curved=1;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" source="R1" target="R6">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="439" y="100"/>
      <mxPoint x="239" y="100"/>
    </Array>
  </mxGeometry>
</mxCell>
<mxCell id="tunnel_R1_R6_lbl" value="Tunnel8 - Tunnel8&#10;172.16.16.0/30&#10;[GRE]" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;" vertex="1" connectable="0" parent="tunnel_R1_R6">
  <mxGeometry relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>
</mxCell>
```

#### 4.9.4 Tunnel Endpoint Octet Labels

Each tunnel arc endpoint must have a small `.1` / `.2` last-octet label placed **near the top of the device**, at the point where the arc exits/enters.

- **Source device** gets `.1`: position `(source_x + 44, source_y - 15)`
- **Target device** gets `.2`: position `(target_x + 44, target_y - 15)`
- **Style**: `edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;`
- **Parent**: `"1"` (canvas root — same as physical octet labels, NOT parented to the tunnel edge)

**Example XML** (R1 at 400,200 → R6 at 200,200):
```xml
<mxCell id="tunnel_R1_R6_0_src_octet" value=".1"
  style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;"
  vertex="1" connectable="0" parent="1">
  <mxGeometry x="444" y="185" as="geometry" />
</mxCell>
<mxCell id="tunnel_R1_R6_0_dst_octet" value=".2"
  style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;"
  vertex="1" connectable="0" parent="1">
  <mxGeometry x="244" y="185" as="geometry" />
</mxCell>
```

#### 4.9.5 Legend Requirements

The legend box must list each tunnel type present in the diagram:
```
Legend
--- Physical Link
....... GRE Tunnel (white)
....... IPsec VPN (red)
....... MPLS (orange)
EIGRP AS 100
```

#### 4.9.6 Baseline YAML Structure

Tunnel overlays are defined in the `tunnel_overlays` top-level section of `baseline.yaml`, keyed by lab number:

```yaml
tunnel_overlays:
  - lab: 8
    type: gre
    source: R1:Tunnel8
    target: R6:Tunnel8
    subnet: 172.16.16.0/30
    description: GRE Tunnel for EIGRP over VPN
```

### 4.10 Protocol Domain Zones (Area / AS Overlays)

Domain zones represent logical groupings of devices and links that share a routing boundary — OSPF areas, BGP autonomous systems, VRFs, MPLS domains, etc. They are drawn as **dashed, semi-transparent colored ellipses** that sit visually behind all routers and links.

#### 4.10.1 Drawing Order — Zones First

Zone shapes **must be placed before** (earlier in the XML than) all router cells and link cells. Draw.io renders cells in document order; placing zones first ensures they appear behind devices and lines.

#### 4.10.2 Zone Shape Style

All zone shapes share the same base style pattern:

```
rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeWidth=2;opacity=35;
fontSize=12;fontStyle=1;fontColor=#FFFFFF;
strokeColor=<COLOR>;fillColor=<DARK_FILL>;
verticalAlign=<top|bottom>;spacingTop=6;
```

- `rounded=1;arcSize=5` — slightly rounded rectangle (NOT `ellipse`; `arcSize=5` gives barely-softened corners)
- `dashed=1` — boundary is always dashed (never solid)
- `opacity=35` — semi-transparent so routers and links show through
- `fontColor=#FFFFFF` — white text so label reads against dark canvas
- `fillColor` — a dark-tinted version of the stroke color (see table below)
- `verticalAlign` — place label at `top` if devices occupy the bottom of the zone, `bottom` if devices are near the top

#### 4.10.3 Color Table by Domain Type

| Domain Type            | strokeColor | fillColor | Label example              |
|------------------------|-------------|-----------|----------------------------|
| OSPF Area 0 (Backbone) | `#1565C0`   | `#1a3a5c` | `Area 0 (Backbone)`        |
| OSPF Area N (Normal)   | `#2E7D32`   | `#1b3d27` | `Area 1`                   |
| OSPF Stub              | `#E65100`   | `#4a1e00` | `Area 2 (Stub)`            |
| OSPF Totally Stubby    | `#E65100`   | `#4a1e00` | `Area 2 (Totally Stubby)`  |
| OSPF NSSA              | `#6A1B9A`   | `#2e0d40` | `Area 3 (NSSA)`            |
| BGP AS (first/local)   | `#00838F`   | `#003d45` | `AS 65001 (iBGP)`          |
| BGP AS (peer 2)        | `#F57F17`   | `#4a2700` | `AS 65002`                 |
| BGP AS (peer 3)        | `#AD1457`   | `#45072a` | `AS 65003`                 |
| BGP AS (peer 4+)       | `#558B2F`   | `#243d13` | `AS 65004`                 |
| VRF instance           | `#4527A0`   | `#1a0f40` | `VRF CUSTOMER-A`           |
| MPLS domain            | `#37474F`   | `#1a2226` | `MPLS Core`                |

> **Rule:** Each distinct domain gets a unique color from the table. When multiple OSPF areas are present, Area 0 is always blue; assign subsequent normal areas green; assign stub/NSSA areas orange/purple. For BGP, assign one color per AS — rotate through the BGP rows in order.

#### 4.10.4 Zone Sizing and Positioning

- The ellipse must **fully enclose** all devices and links that belong to the zone, with at least 20–30px of padding around the outermost device edges.
- Zones that **share a device** (e.g., an ABR in Area 0 and Area 1) will **overlap** — this is correct and expected. The semi-transparent fills stack and show the shared boundary visually.
- Zones for larger areas (backbone Area 0) are typically wider and taller; peripheral areas (stub, NSSA) are smaller ellipses containing only their few devices.

#### 4.10.5 Zone Label Placement

- The label text inside the ellipse identifies the zone name and type.
- Use `verticalAlign=top` to place the label at the top of the ellipse when devices sit in the lower portion.
- Use `verticalAlign=bottom` to place the label at the bottom when devices sit near the top of the ellipse.
- Never center the label vertically if it would overlap a router icon.

#### 4.10.6 Reference XML Snippet — Zone Shapes

**OSPF Area 0 (Backbone) — blue:**
```xml
<!-- Draw zones FIRST — before any router or link cells -->
<mxCell id="area0_shape" value="Area 0&#10;(Backbone)"
  style="rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeColor=#1565C0;strokeWidth=2;fillColor=#1a3a5c;opacity=35;fontSize=12;fontStyle=1;verticalAlign=top;fontColor=#FFFFFF;spacingTop=6;"
  vertex="1" parent="1">
  <mxGeometry x="10" y="80" width="555" height="260" as="geometry" />
</mxCell>
```

**OSPF Area 1 (Normal) — green:**
```xml
<mxCell id="area1_shape" value="Area 1"
  style="rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeColor=#2E7D32;strokeWidth=2;fillColor=#1b3d27;opacity=35;fontSize=12;fontStyle=1;verticalAlign=bottom;fontColor=#FFFFFF;spacingTop=6;"
  vertex="1" parent="1">
  <mxGeometry x="55" y="290" width="510" height="400" as="geometry" />
</mxCell>
```

**OSPF Stub / Totally Stubby Area — orange:**
```xml
<mxCell id="area2_shape" value="Area 2&#10;(Totally Stubby)"
  style="rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeColor=#E65100;strokeWidth=2;fillColor=#4a1e00;opacity=35;fontSize=12;fontStyle=1;verticalAlign=top;fontColor=#FFFFFF;spacingTop=6;"
  vertex="1" parent="1">
  <mxGeometry x="448" y="335" width="310" height="125" as="geometry" />
</mxCell>
```

**BGP Autonomous System — teal (local AS) and orange (peer AS):**
```xml
<!-- Local AS -->
<mxCell id="as65001_shape" value="AS 65001&#10;(iBGP)"
  style="rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeColor=#00838F;strokeWidth=2;fillColor=#003d45;opacity=35;fontSize=12;fontStyle=1;verticalAlign=top;fontColor=#FFFFFF;spacingTop=6;"
  vertex="1" parent="1">
  <mxGeometry x="20" y="55" width="420" height="340" as="geometry" />
</mxCell>

<!-- Peer AS -->
<mxCell id="as65002_shape" value="AS 65002"
  style="rounded=1;arcSize=5;whiteSpace=wrap;html=1;dashed=1;strokeColor=#F57F17;strokeWidth=2;fillColor=#4a2700;opacity=35;fontSize=12;fontStyle=1;verticalAlign=top;fontColor=#FFFFFF;spacingTop=6;"
  vertex="1" parent="1">
  <mxGeometry x="500" y="55" width="280" height="240" as="geometry" />
</mxCell>
```

#### 4.10.7 Legend Requirements for Zones

When zone shapes are present, the legend box must list each zone with its color. Format:

```
Legend
--- Physical Link
[blue dashed] Area 0 (Backbone)
[green dashed] Area 1 (Normal)
[orange dashed] Area 2 (Totally Stubby)
OSPF Process ID: 1
```

Since Draw.io legend cells are plain text, describe colors in words or use Unicode colored indicators where possible. At minimum, name each zone and its type.

#### 4.10.8 When to Apply Zone Shapes

| Lab type                          | Zones to draw                                           |
|-----------------------------------|---------------------------------------------------------|
| OSPF single-area                  | One Area 0 ellipse enclosing all devices                |
| OSPF multi-area                   | One ellipse per area; ABRs sit inside overlapping zones |
| OSPF stub / totally stubby / NSSA | Area 0 + any normal areas + stub/NSSA area (orange/purple) |
| BGP single-AS                     | One AS ellipse around all iBGP peers                    |
| BGP multi-AS (eBGP)               | One ellipse per AS; eBGP links cross zone boundaries    |
| EIGRP                             | One ellipse per AS number if multiple ASes present      |
| VRF / MPLS                        | One ellipse per VRF or MPLS domain if topologically relevant |
| Single-protocol flat topology     | Zone shapes optional but recommended for clarity        |

--# 5. Workflow

### Creating a New Diagram
1.  Open Draw.io (Desktop or Web).
2.  Create the diagram following the Visual Style Guide (Section 4).
3.  **Validation Checklist**:
    - [ ] Canvas background is `#1a1a2e` (set in `<mxGraphModel background="#1a1a2e">`).
    - [ ] Title is at the top center, bold, 16pt, **white text**.
    - [ ] All device icons use `mxgraph.cisco19.rect;prIcon=<type>` — NOT the old `mxgraph.cisco.routers.router` shapes.
    - [ ] Device labels are **embedded in the device cell `value`** as HTML (white bold hostname + gray role/IP). No separate label cells.
    - [ ] Label position uses `labelPosition=` / `verticalLabelPosition=` attributes, following the Empty Side Rule (Section 4.3.1).
    - [ ] All connection lines are **white** (`#FFFFFF`), strokeWidth=2.
    - [ ] Every device has a hostname, role, and Loopback IP.
    - [ ] Every link has interface names on BOTH ends.
    - [ ] Every interface has a **last octet** label (`.1`, `.2`) near the router.
    - [ ] Subnet ID is visible on every link (centered edge label).
    - [ ] **No link visually crosses through an intermediate device** (see Section 4.8).
    - [ ] **Tunnel overlays** use thin colored dotted lines and arc above physical devices (see Section 4.9).
    - [ ] **Tunnel endpoint octets** (`.1` / `.2`) are placed near the top of source/target devices (see Section 4.9.4).
    - [ ] **Protocol domain zones** (OSPF areas, BGP AS, VRFs) drawn as `rounded=1;arcSize=5` dashed semi-transparent boxes — placed FIRST in XML so they render behind routers and links (see Section 4.10). Do NOT use `ellipse`.
    - [ ] Each zone uses the correct color from the §4.10.3 table (blue=backbone, green=normal, orange=stub, teal=BGP local AS, etc.).
    - [ ] Zone boxes fully enclose their member devices with ≥20px padding; overlapping zones are correct at ABR/ASBR boundaries.
    - [ ] **Legend box** is present (black fill, white text, bottom-right) and lists zone types and tunnel colors where applicable.
4.  Save the editable file as `.drawio` in the appropriate subdirectory.

### Updating a Diagram
1.  Open the existing `.drawio` file.
2.  Make necessary modifications.
3.  Validate against the checklist above.
4.  Save the `.drawio` file.

-# Common Issues

--# Zone ellipses cover (obscure) routers and links

- **Cause:** Zone shape cells were placed after router and link cells in the XML, causing them to render on top of everything.
- **Solution:** Move all zone `mxCell` elements to appear before the first router cell in the XML. Draw.io renders in document order — zones must come first.

--# Zone ellipse does not enclose all member devices

- **Cause:** Ellipse geometry was sized for the routers but did not account for labels or link endpoints extending beyond the icon bounds.
- **Solution:** Extend the ellipse by at least 20–30px beyond the outermost device icon on every side. Check that interface octet labels near the zone boundary are also inside the ellipse.

--# Device icons look wrong (plain circle/router silhouette instead of Cisco19 style)
- **Cause:** Old `mxgraph.cisco.routers.router` shape used instead of `mxgraph.cisco19.rect;prIcon=router`.
- **Solution:** Replace the device style with the cisco19 string from §4.2. The cisco19 shapes render as a white/light rectangle with a teal border and an embedded icon — they do NOT look like the old blue-filled silhouettes.

--# Zone shapes are ovals instead of boxes
- **Cause:** `ellipse` style used instead of `rounded=1;arcSize=5`.
- **Solution:** Replace `ellipse;` with `rounded=1;arcSize=5;` in the zone cell style. `arcSize=5` gives barely-softened rectangular corners — the shapes should look like boxes, not ovals.

--# Connection lines are black instead of white
- **Cause:** Default Draw.io line color was used without applying the style guide.
- **Solution:** Select all connection lines and apply `strokeColor=#FFFFFF;strokeWidth=2` from Section 4.4. Run `scripts/generate_topo.py` to auto-generate a compliant diagram from `baseline.yaml`.

--# Link visually crosses through an intermediate device
- **Cause:** Three or more devices share the same X coordinate and a bypass link connects non-adjacent ones.
- **Solution:** Offset the intermediate device(s) horizontally by at least 100px to create a triangle or staggered layout. See Section 4.8 for the full rule and example.

--# Device label overlaps a connection line
- **Cause:** Label was placed on the same side as one or more connected links.
- **Solution:** Apply the Empty Side Rule (Section 4.3.1) — place the label on the side with no connections exiting the icon.

--# generate_topo.py produces incorrect output
- **Cause:** `baseline.yaml` is missing required fields (`links`, device coordinates, or interface definitions).
- **Solution:** Verify `baseline.yaml` has complete `core_topology.links` with `source`, `target`, and `subnet` for every link. Check for missing `loopback0` values on devices.
