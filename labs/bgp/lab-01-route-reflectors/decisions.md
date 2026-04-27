## Model gate — 2026-04-27
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions — 2026-04-27

**Legacy R2↔R5 direct iBGP session retained.** The progressive build rule (only add, never remove) requires keeping the lab-00 direct session on both R2 and R5. In production this session would be removed once the RR is verified stable. The capstone labs start from a clean slate and will omit the legacy session.

**`next-hop-self` stays on ingress PEs, not on the RR.** R2 and R5 apply `next-hop-self` toward all iBGP neighbors (including R4). R4 as RR reflects routes with the next-hop already changed to the originating PE's loopback — it does not need its own `next-hop-self`. Adding it on R4 would be redundant and could mask misconfiguration on the ingress PEs.

**R3's only iBGP peer is R4.** R3 has no legacy direct sessions (it had no BGP in lab-00). This makes R3 the cleanest observable device for RR-client troubleshooting: any fault in the RR fabric immediately surfaces as an empty BGP table on R3, with no fallback path.

**Troubleshooting ticket targeting:** Ticket 1 targets R3 (not R5 as stated in the original baseline objective) because R5 retains the legacy R2 session which would mask the fault. R3 has no fallback path, making the missing `route-reflector-client` immediately observable as an empty table.

**`bgp cluster-id 10.0.0.4`** set to R4's own loopback. Convention for a single-RR design. The baseline.yaml already carried this value in `cluster_id: "10.0.0.4"` for R4.
