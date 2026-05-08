# Design Decisions — srv6/lab-00-srv6-control-plane

## Model gate — 2026-05-01
- Difficulty: Foundation
- Running model: claude-sonnet-4-6
- Allowed models: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

---

## Workbook gate — 2026-05-01
- Outcome: PASS-CLEAN
- Items fixed: none
- Notes: n/a

---

## SRv6 on XRv9k — Platform Selection — 2026-05-01

SRv6 requires IOS-XRv 9000 7.1.1 or later. IOSv (IOS 15.9) and CSR1000v
(IOS-XE 17.3.x) do not support SRv6 locators, SID functions, or IS-IS SRv6
extensions. All six nodes are xrv9k with 4096 MB RAM each (24 GB total),
within the 64 GB Dell Latitude 5540 host limit. Per the spec.md platform
decision, this is the only installed platform with SRv6 capability.

---

## IS-IS L2 Dual-Stack from lab-00 — 2026-05-01

IS-IS is configured as dual-stack (IPv4 + IPv6 address-families) from lab-00
even though the blueprint objectives (4.4, 4.4.a) do not explicitly mention
IPv4 IS-IS. Rationale:

1. **SRv6 locators are IPv6** — the IS-IS IPv6 address-family is required
   to carry SRv6 Locator TLVs. IPv4-only IS-IS cannot advertise SRv6 SIDs.
2. **IPv4 address-family for future labs** — later labs (lab-02 BGP SRv6
   L3VPN) need IPv4 underlay reachability for BGP peering between PE1 and PE2.
   Establishing the IPv4 AF in lab-00 avoids a disruptive IS-IS reconfiguration
   mid-chain.
3. **Dual-stack is production standard** — every SP core runs dual-stack IS-IS.
   Teaching SRv6 without IPv4 IS-IS would misrepresent real-world deployment.

## metric-style wide Required for SRv6 — 2026-05-01

`metric-style wide` is enabled under both IS-IS address-families. IS-IS narrow
metrics (TLV 128/130) cannot carry SRv6 Locator TLVs — SRv6 requires wide
metrics (TLV 135 for IPv4, TLV 236/237 for IPv6). Without wide metrics, SRv6
silently fails: the locator is configured and active, but IS-IS never originates
the Locator TLV.

---

## SRv6 Domain: Single Flat /48 Locator Structure — 2026-05-01

All six nodes use a single locator block `fc00:0::/32` with per-node `/48`
sub-allocations. This follows the typical ISP deployment model: a well-known
/32 block, /48 per node, 16 bits of function space. The SID manager allocates:
- `:1::/64` — End SID (assigned to Loopback0 behavior)
- `:2::/64` through `:6::/64` — End.X SIDs (per-adjacency, configured in lab-01)
- `:d4::/64`, `:d6::/64` — End.DT4/End.DT6 service SIDs (configured in lab-02)

---

## Three Troubleshooting Tickets — 2026-05-01

The baseline.yaml specifies three fault scenarios for the SRv6 control plane.
This lab implements them as:

1. **Ticket 1 — P2's locator missing from every SID table:** P2 is missing
   `segment-routing srv6 locator P2_LOC` under both IS-IS address-families.
   The locator is defined at the top-level and Status is Active, but IS-IS
   never originates the Locator TLV. Tests understanding that local locator
   status and IS-IS advertisement are independent toggles.

2. **Ticket 2 — P4 reports only one IS-IS neighbor:** P4's Gi0/0/0/0 (L3 to P3)
   is missing both `address-family` blocks under IS-IS. The interface is
   attached to IS-IS (`point-to-point` is present) but no IS-IS hellos are
   exchanged because no AF is active. Tests ability to distinguish IGP
   adjacency failure from SRv6-specific failure.

3. **Ticket 3 — PE2's locator Status: Down:** PE2's locator prefix is
   configured as `/64` instead of `/48`. A `/64` locator leaves zero
   function bits — the SID manager cannot carve out End SID entries and
   marks the locator Down. Tests understanding of locator prefix-length
   requirements and the relationship between locator length and function space.

---

## Encapsulation Source-Address Required for SID Manager — 2026-05-01

The `encapsulation source-address` command is included in lab-00 even though
no SRH encapsulation occurs until lab-01. This is because the SRv6 SID manager
on IOS-XR 7.x requires a valid source-address before it will allocate any
SIDs — including the End SID. Without it, the locator shows Status: Down
and the SID table is empty. This is documented in the workbook's Ticket 3
diagnosis steps and the cheatsheet failure causes table.

---

## No End.X SIDs in lab-00 — 2026-05-01

End.X SIDs (per-adjacency cross-connect) are intentionally excluded from
lab-00. They are the primary topic of lab-01 (SRv6 data plane). End.X SIDs
are allocated automatically by the SID manager when an interface is configured
with IS-IS — including them in lab-00 would pre-empt lab-01's learning
objectives. The End SID (node-level behavior) is the minimum control-plane
SID required to establish the SRv6 domain.
