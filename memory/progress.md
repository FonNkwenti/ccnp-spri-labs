# Lab Build Progress — CCNP SPRI (300-510)

Last updated: 2026-04-30 (segment-routing lab-03-sr-te-policies-and-steering built)

## Build Order

1. ospf
2. isis
3. bgp
4. routing-policy ← **active**
5. ipv6-transition
6. fast-convergence
7. mpls
8. multicast
9. segment-routing
10. srv6

---

## ospf

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-single-area-ospfv2 | Single-Area OSPFv2 Foundations | Built ✓ |
| lab-01-multiarea-ospfv2 | Multiarea OSPFv2 and LSA Propagation | Built ✓ |
| lab-02-ospfv3-dual-stack | OSPFv3 Dual-Stack Multiarea | Built ✓ |
| lab-03-summarization-stub-nssa | Summarization, Stub, and NSSA | Built ✓ |
| lab-04-capstone-config | OSPF Full Protocol Mastery — Capstone I | Built ✓ |
| lab-05-capstone-troubleshooting | OSPF Comprehensive Troubleshooting — Capstone II | Review Needed |

## isis

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-single-level-isis | Single-Level IS-IS Foundations | Review Needed |
| lab-01-multilevel-isis | Multilevel IS-IS and Route Advertisement | Review Needed |
| lab-02-dual-stack-summarization | Dual-Stack IS-IS with Summarization and Route Leaking | Review Needed |
| lab-03-capstone-config | IS-IS Full Protocol Mastery — Capstone I | Not Started |
| lab-04-capstone-troubleshooting | IS-IS Comprehensive Troubleshooting — Capstone II | Not Started |

## bgp

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-ebgp-ibgp-foundations | eBGP and iBGP Foundations | Built ✓ |
| lab-01-route-reflectors | iBGP Route Reflectors and Cluster IDs | Built ✓ |
| lab-02-ebgp-multihoming | eBGP Multihoming and Traffic Engineering | Built ✓ |
| lab-03-interdomain-security | Inter-Domain Security and Maximum-Prefix | Review Needed |
| lab-04-dampening-dynamic | Route Dampening and Dynamic Neighbors | Review Needed |
| lab-05-communities-flowspec | BGP Communities and FlowSpec | Review Needed |
| lab-06-confederations | BGP Confederations | Review Needed |
| lab-07-capstone-config | BGP Full Protocol Mastery — Capstone I | Review Needed |
| lab-08-capstone-troubleshooting | BGP Comprehensive Troubleshooting — Capstone II | Review Needed |

**Note (2026-04-28):** All BGP workbooks (lab-00 through lab-08) have been reviewed and improved for clarity:
- Clarified `show ip bgp <prefix>` (detailed view) vs `show ip bgp` (table view) command output formats
- Explained where AS-path appears in each format (unlabeled first line in detailed view, Path column in table view)
- Standardized terminology and added exam tips across all labs
- Addresses student confusion about AS-path visibility in detailed output

## routing-policy

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-route-maps-foundations | Route-Maps, Prefix-Lists, and ACL Matching | Review Needed |
| lab-01-tags-regex-communities | Tags, Route Types, Regex, and BGP Communities | Review Needed |
| lab-02-rpl-vs-route-maps | RPL vs Route-Maps — Policy Sets and Hierarchical Policies | Built ✓ |
| lab-03-igp-route-manipulation | Route Manipulation for IS-IS and OSPF | Review Needed |
| lab-04-bgp-filtering-steering | BGP Route Filtering and Traffic Steering | Review Needed |
| lab-05-capstone-config | Routing Policy Full Mastery — Capstone I | Not Started |
| lab-06-capstone-troubleshooting | Routing Policy Comprehensive Troubleshooting — Capstone II | Not Started |

## mpls

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-ldp-foundations | MPLS LDP Foundations and Label Distribution | Review Needed |
| lab-01-lsp-verification-and-troubleshooting | LSP Verification with MPLS OAM | Review Needed |
| lab-02-bgp-free-core-and-unified-bgp | BGP-Free Core and Unified BGP (Labeled Unicast) | Review Needed |
| lab-03-rsvp-te-tunnels | RSVP-TE Tunnels with Explicit Paths | Built ✓ |
| lab-04-capstone-config | MPLS Full Mastery — Capstone I | Not Started |
| lab-05-capstone-troubleshooting | MPLS Comprehensive Troubleshooting — Capstone II | Not Started |

## bgp-dual-ce (supplemental topic)

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-dual-ce-ibgp-baseline | Dual-CE iBGP Architecture and Baseline | Review Needed |
| lab-01-transit-prevention | Transit Prevention Policy | Review Needed |
| lab-02-inbound-traffic-engineering | Inbound Traffic Engineering Across Two ISPs | Review Needed |
| lab-03-selective-advertisement | Outbound Policy and Selective Prefix Advertisement | Review Needed |
| lab-04-capstone-config | BGP Dual-CE Full Protocol Mastery — Capstone I | Built ✓ |
| lab-05-capstone-troubleshooting | BGP Dual-CE Comprehensive Troubleshooting — Capstone II | Not Started |

## segment-routing

| Lab | Title | Status |
|-----|-------|--------|
| lab-00-sr-foundations-and-srgb | SR-MPLS Foundations, SRGB, and Prefix SIDs | Review Needed |
| lab-01-ti-lfa | Topology-Independent Loop-Free Alternate (TI-LFA) | Review Needed |
| lab-02-sr-migration-ldp-coexistence | SR Migration — LDP Coexistence, Mapping Server, SR-Prefer | Built ✓ |
| lab-03-sr-te-policies-and-steering | SR-TE Policies, Constraints, and Automated Steering | Review Needed |
| lab-04-pce-srlg-tree-sid | PCE Path Computation, SRLG, and Tree SID | Review Needed |
| lab-05-ospf-sr-standalone | OSPF Segment Routing Extensions (standalone) | Review Needed |
| lab-06-capstone-config | SR Full Mastery — Capstone I | Not Started |
| lab-07-capstone-troubleshooting | SR Comprehensive Troubleshooting — Capstone II | Not Started |
