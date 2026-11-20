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
- The user confirmed that NCBI Taxonomy 2759 is Eukaryota; the notes saying it was unchecked
  are updated (default configuration comment, CHANGELOG, status, reviews README).
- At the user's request ("The report is still too long and very text heavy. Have the advisor look
  how to visualize the results more graphically") an advisor subagent reviewed the HTML report
  read-only, rendering the user's HSV-1 and HSV-2 reports; its report is kept verbatim
  ([review](../../reviews/2026-11-20-report-advisor.md)), its mock-up stayed in the session's scratch
  folder. Checked: closed `<details>` sections do not print (reproduced); the page-1 line counts
  an Exceeds-limit row as flagged for review. Nothing built yet.
- The user likes the redesigned report of the mock-up, except its Needs-attention part: the
  current rows with class chips, frequencies, dTm and highlighted mismatches are "much nicer and
  more informative". Recorded as a decision
  ([decision](../decisions/2026-11-20-needs-attention-keeps-its-colours.md)); nothing built yet.
- The report review taken up in full (user: "Yes, all in order", "Build P3 too"): Part A, a
  two-page sign-off (status sentence, required statements in one line, "What was checked" with a
  small figure per row and the tier glyphs in place of a separate tier table, detection per year,
  mismatch maps per oligo, the first Needs-attention rows as today, the findings that need a
  decision, the decision box); Part B, the evidence; Part C, the appendix. Nothing of the record
  folded any more (closed sections did not print). `report/charts.py` and `report/figures.py`
  replace `plots.py`; workbook sheet "Mismatch positions". A QC message on a degenerate oligo
  names its worst variant. Rendered with Chromium: Part A two A4 pages for the test reports.
