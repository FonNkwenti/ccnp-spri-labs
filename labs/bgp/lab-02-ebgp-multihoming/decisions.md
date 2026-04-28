## Model gate — 2026-04-27
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions — 2026-04-27

**`next-hop-self` added to R3 in lab-02 (not present in lab-01).** In lab-01 R3 had no eBGP sessions — only an iBGP peering to R4. Now that R3 receives Customer A routes directly from R1 via eBGP, it must apply `next-hop-self` toward R4. Without it, R4 receives the route with next-hop 10.1.13.1 (R1's CE-PE physical IP), which is not reachable via OSPF. This is a natural progressive addition, not a modification of lab-01 configs.

**MED applied alongside AS-path prepend in a single route-map clause.** Objective 4 (MED) and objective 3 (AS-path prepend) both apply to R1's outbound advertisements toward R3. They are combined into the single `TO-R3-BACKUP` route-map permit clause rather than creating separate route-maps. This mirrors real SP practice — operators don't normally run two separate route-maps when both policies target the same neighbor and prefix.

**Ticket 1 targets R3 (next-hop-self), Ticket 2 targets R2 (LOCAL_PREF), Ticket 3 targets R1 (AS-path prepend).** Each ticket exercises one of the three core traffic-engineering mechanisms independently. Tickets 2 and 3 together represent the "both paths active-active" scenario from the baseline objective — individually, each breaks one layer of the defense-in-depth, demonstrating that the other mechanism still partially maintains preference, which is a more nuanced and realistic troubleshooting exercise than a single compound fault.

**`find_open_lab` replaced with `DEFAULT_LAB_PATH` in all fault-injection scripts.** The fault-injector subagent generated scripts using `find_open_lab` for lab path auto-discovery. This was corrected to use `DEFAULT_LAB_PATH = "bgp/lab-02-ebgp-multihoming.unl"` with a static default, consistent with lab-01 and per lesson learned from OSPF labs 03–05 (commit 4130af1) where `find_open_lab` caused EVE-NG 412 errors.
