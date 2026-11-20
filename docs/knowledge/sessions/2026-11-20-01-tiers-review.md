---
type: Session
title: "Advisor review of the search tiers"
description: "Session log of 2026-11-20."
tags: [session]
session_date: 2026-11-20
session_label: "2026-11-20"
generated: { by: claude-code/agent, at: 2026-11-20T10:00:00Z }
---

# 2026-11-20: advisor review of the search tiers

- The VZV rerun of 2026-11-19 failed twice in the GUI: NCBI answered a BLAST submission with an
  HTML page and no request ID (the page's own date read 22 October). Not retried by the code (the
  HTTP layer retries only 429 and 5xx; the page came back as a success). The user will try again
  later; nothing built.
- At the user's request ("Have the advisor look at the logic of the tiers") an advisor subagent
  reviewed the tier logic read-only; its report is kept verbatim
  ([review](../../reviews/2026-11-20-tiers-advisor.md)). F1, F2, F3, F5 and F7 were checked
  against the code and hold; the [search tiers](../components/search-tiers.md) page was
  corrected where the review found it wrong or overstated. No code changed: the user decides.
- All nine findings fixed (user: "Fix all. You can decide the order yourself"), in the order F1,
  F7, F2, F6, F5, F3 with F8, F4, F9 (CHANGELOG `[Unreleased]`, [search tiers](../components/search-tiers.md)):
  every searched tier assessed and `specificity.tier_waivers`; missing tiers and unresolved names
  Incomplete above Review; `search/tiers.py` checks tier taxa against the target's lineage and
  each other; balanced searches and the floor per search; lineage in the exclusivity table and
  the restriction check; `probe_scan_max_products` and "not detected (bounded)"; `cautious_tiers`
  (near neighbours: at risk and gapped sites act at warning level; first written for every level,
  narrowed when a test showed a run of N graded at risk); a bounded cut at `max_amplicons` and
  distinct product patterns; the eukaryote note by lineage, default `[9606, 2759]` (2759 =
  Eukaryota, not checked live). Not built: an exhaustive analysis of a near neighbour's records,
  specimen panels, taxonomy-derived near-neighbour suggestions. The fake NCBI in the tests now
  answers Taxonomy EFetch. User guide, wiki page Specificity-search and ARCHITECTURE updated.
