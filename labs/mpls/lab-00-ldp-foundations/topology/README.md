# Topology — MPLS Lab 00 (LDP Foundations)

`topology.drawio` is the canonical source of truth for the lab's
physical layout. View / edit it with [Draw.io Desktop](https://www.drawio.com/)
or the online editor at <https://app.diagrams.net/>.

## Devices

| Hostname | Loopback0     | Role                          | EVE-NG image            |
|----------|---------------|-------------------------------|--------------------------|
| PE1      | 10.0.0.1/32   | SP edge — IS-IS L2 + LDP      | IOSv 15.9(3)M6           |
| P1       | 10.0.0.2/32   | SP core — IS-IS L2 + LDP      | IOSv 15.9(3)M6           |
| P2       | 10.0.0.3/32   | SP core — IS-IS L2 + LDP      | IOSv 15.9(3)M6           |
| PE2      | 10.0.0.4/32   | SP edge — IS-IS L2 + LDP      | IOSv 15.9(3)M6           |

## Links

| ID | Endpoints                       | Subnet         | Notes                |
|----|---------------------------------|----------------|----------------------|
| L2 | PE1 Gi0/1 ↔ P1 Gi0/0            | 10.10.12.0/24  | Core, IS-IS+LDP      |
| L3 | PE1 Gi0/2 ↔ P2 Gi0/0            | 10.10.13.0/24  | Core, IS-IS+LDP      |
| L4 | P1 Gi0/1 ↔ P2 Gi0/1             | 10.10.23.0/24  | P1↔P2 cross          |
| L5 | P1 Gi0/2 ↔ PE2 Gi0/1            | 10.10.24.0/24  | Core, IS-IS+LDP      |
| L6 | P2 Gi0/2 ↔ PE2 Gi0/2            | 10.10.34.0/24  | Core, IS-IS+LDP      |

IP convention: device number = last octet of every IP it terminates.
PE1=`.1`, P1=`.2`, P2=`.3`, PE2=`.4`.

## Importing into EVE-NG

The repository ships only the diagram and the per-device configs;
the `.unl` file is created once on your EVE-NG host:

1. **In the EVE-NG web UI**, create a new lab named
   `lab-00-ldp-foundations` under the folder `ccnp-spri/mpls/`.
2. Drop in 4 IOSv nodes named exactly `PE1`, `P1`, `P2`, `PE2`. The
   names must match — `setup_lab.py` looks them up by hostname.
3. Wire the interfaces per the **Links** table above. Be exact about
   `Gi0/0..Gi0/2` so the `mpls ip` and `ip router isis` lines in the
   solution configs apply to the right physical interface.
4. Start all four nodes.
5. From the repo root, run:

   ```bash
   python3 labs/mpls/lab-00-ldp-foundations/setup_lab.py --host <eve-ng-ip>
   ```

   This pushes `initial-configs/*.cfg` (IP-only baseline). The lab
   itself is what you build on top.

## Refreshing the diagram

`topology.drawio` is hand-maintained. After any topology edit, reopen it in
the draw.io desktop app or app.diagrams.net, make the change, and commit the
updated `.drawio` source. Diagrams are kept as `.drawio` only — no rendered
image is committed.

## Why this topology

- **Diamond** (L2/L3/L5/L6) gives every PE two link-disjoint paths to
  the other PE — visible as ECMP in the LFIB.
- **P1↔P2 cross** (L4) is unused for PE-to-PE LSPs in lab-00 but stays
  in the IS-IS topology so subsequent labs (RSVP-TE in lab-03) can
  build a third explicit path through it.
- **No CEs** in lab-00 — pure label plane. CE1/CE2 boot at lab-02 when
  the topic shifts to "BGP-free core carries customer traffic on labels".
