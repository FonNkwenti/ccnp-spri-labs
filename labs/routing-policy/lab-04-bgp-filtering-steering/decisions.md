## Model gate — 2026-04-28
- Difficulty: Intermediate
- Running model: claude-sonnet-4-6
- Allowed models: claude-sonnet-4-6, claude-opus-4-7
- Outcome: PASS

## Design decisions

### aggregate-address without summary-only in final state
Task 2 uses `summary-only` as a transient demo to show complete more-specific suppression.
The final solution removes `summary-only` so that 172.16.1.0/24 (specific) remains
advertised to R4. This is necessary for Task 4 (AS-path prepend on the specific) and
Task 5 (MED on the aggregate) to produce observable, distinct results at R4. If
`summary-only` were kept in the final state, only the aggregate would be visible at R4
and prepend comparisons would be impossible.

### STEER_R4_IN replaces FILTER_R4_ASPATH on R3
The lab-03 FILTER_R4_ASPATH allowed only AS 65200 routes and set community 65100:200.
Lab-04 Task 3 adds LOCAL_PREF 200 for 172.20.4.0/24 specifically. Replacing the
route-map entirely (rather than modifying in-place) makes the diff clear and avoids
a conflict where the community-setting clause (seq 10 in FILTER_R4_ASPATH) could
shadow the LOCAL_PREF sequence.

### SET_COMMUNITY_AND_PREPEND applied on IBGP neighbor-group in XR1
Task 6 is a syntax-comparison demo, not an eBGP production policy. Applying it on
the IBGP group means R2 will observe the effect (community 65100:300 + longer AS-path
on 172.16.11.0/24) without needing a separate eBGP peer. In a real network this would
be applied outbound on an eBGP neighbor; the demo placement on IBGP is intentional
and noted in the workbook.

### Conditional advertisement tracks 172.16.0.0/16 (aggregate), not a specific
TRACK_PRIMARY matches the R3-originated 172.16.0.0/16 aggregate. This is the cleanest
proxy for "R3 is up and advertising": if R3's aggregate disappears from the BGP table
(R3 fails or R3's eBGP session to R4 drops), R1 should surface the backup /24.
Tracking a specific (172.16.1.0/24 from R3) would also work but requires R3 to
originate that specific — since R3 does not have a Loopback1, this approach avoids
adding unnecessary state to R3.
