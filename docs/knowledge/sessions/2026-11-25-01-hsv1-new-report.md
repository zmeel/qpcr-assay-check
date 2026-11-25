---
type: Session
title: "HSV-1 on the new code"
description: "Session log of 2026-11-25."
tags: [session]
session_date: 2026-11-25
session_label: "2026-11-25"
generated: { by: claude-code/agent, at: 2026-11-25T09:00:00Z }
---

# 2026-11-25: HSV-1 on the new code

- The user's HSV-1 run on commit `1b135c6` (07:33Z) was checked by printing it to A4 with
  Chromium and comparing it with the run of 2026-11-20 16:52Z, which has the same inputs hash
  ([run](../runs/hsv1-2026-11-25.md)).
- **The record:** 22 pages, with a sign-off of 2 pages, decision box included. No table is wider
  than the page. The site maps are in Part B, and oligos are listed forward, probe, reverse
  throughout.
- **The assessment:** the same as on 2026-11-20. BLAST gave slightly different counts: 151
  instead of 152 critical background primer sites, and 485 instead of 483 sites not reached by
  the partner scan.
- The user asked whether "All findings behind the summary" could become a figure or a table.
  The advice, without building anything: every line in it is printed again elsewhere (QC
  matrix, the off-target "Findings" list), so drop it; show the specificity findings as one
  table with a row per tier; print a QC message only where it adds to the cell. The trade-off:
  the paper record no longer has the findings as one list (the workbook and results.json keep
  it).
- User: "Do all three". Built
  ([decision](../decisions/2026-11-25-findings-condensed.md)). "Other findings" keeps the lines
  that no section shows. Specificity findings gained `kind`, `count` and `site`. Records made
  before this change keep the old list. In print the table fits A4 (two text columns at a
  minimum width, critical sites in two columns). Simulated on the user's HSV-1 HTML: 19 pages
  instead of 22, with a 2-page sign-off.
- **The condensed HSV-1 record** (08:21Z, commit b69a478): 19 pages, with a 2-page sign-off.
  Nothing is wider than the page, and only two QC messages are left. Three faults were found and
  fixed (user: "Yes, fix all 3"):
  - The closest primer site could be a minor site. The clinical list showed CP073535.2 (2
    mismatches, 2 clean 3′ nt); the closest site among its 577 warning sites is CP139307.1.
  - The two information lines under "Other specificity findings" repeated the products
    paragraph.
  - The product table showed raw tier names and chip labels.
- **The HSV-1 record with these fixes** (09:18Z, commit c2dd9cd): 19 pages, with a 2-page
  sign-off, and Part A identical to the 08:21Z run apart from the run stamps. All three fixes
  hold:
  - the clinical list's closest site is CP139307.1 (*T. pallidum*: 4 mismatches, 18 clean 3′
    nt), in the table and in Part A's glyph;
  - "Other specificity findings" no longer appears;
  - the product and site tables say "Near neighbours" and "amplified, not detected".

  In the near-neighbour tier the forward and the reverse site tie (0 mismatches, 22 clean 3′
  nt): Part A's glyph showed the reverse, the table the forward. At the user's request ("Yes
  make them pick the same site") both now use one choice, `figures.closest_by_tier`: warning or
  critical sites, the fewest mismatches and gaps, the longest clean 3′ end, then the lowest
  site id.
- **GUI fix.** The user reported that the links in "What was checked" opened a new tab that asked
  for the GUI login. The cause: the `<base target="_blank">` the GUI adds for NCBI links also
  applied to jumps within the report. A tab opened from the sandboxed frame does not carry the
  login. The GUI now gives links within the report `target="_self"`. Checked in Chromium with a
  frame sandboxed as in the GUI: before, a new tab; after, the frame jumps to the section. NCBI
  links still open a new tab.
- **Explained:** the user asked what "Near neighbours: product list cut at max_amplicons, not
  bounded" means. Answer: 500 HSV-2 products were listed (the limit), and the proof that the
  unlisted ones cannot be detected fails, because near neighbours are read cautiously. The way
  to close it: raise `max_amplicons` for HSV-1, for example to 1,000.
- **Rephrasing:** the user asked for a rephrasing without building. Three options were given,
  with the other gaps in the same style. The user preferred "amplicon" to "product" and found
  "partner primer" uncommon. The user approved the proposal ("Yes build as you propose"), and it
  was built ([decision](../decisions/2026-11-25-plain-words-amplicon-opposite-primer.md)):
  - "amplicon" and "check for the opposite primer" throughout the report, the findings, the
    workbook (sheet "Predicted amplicons"), the GUI progress labels and the user documentation;
  - every gap rewritten as what stopped, at which setting, and what that leaves unknown, with a
    plain note;
  - "not bounded" is gone, and "bounded" now reads "proven".

  Setting names, results.json fields and log lines are unchanged.
- **HSV-1 rerun with `max_amplicons: 1000`** (11:07Z,
  [run](../runs/hsv1-2026-11-25.md)): near neighbours is now Review (634 amplicons, none
  detected). The opposite-primer check now also covers that tier and leaves 906 sites unchecked;
  the user adds `partner_scan_max_windows: 2000`. The near-neighbour Review line pushed the
  decision box to page 3.

  At the user's choice the sign-off's Review lines are now short. An off-target tier reads
  "Specificity, <tier>: N amplicons, none detected by the probe", or the site counts when there is
  no amplicon (`SummaryRow.brief`), and the "(details in Part B)" suffix is dropped. The findings
  list is printed a little smaller. Simulated on that record: a 2-page sign-off, 19 pages in all.
- **HSV-1 with `partner_scan_max_windows: 2000`** (13:33Z, commit 5a38aac): 19 pages, with a
  2-page sign-off. The opposite-primer check is complete: 1,906 sites, 17 sites added, no new
  amplicon. The human background, cut at `max_sites_per_query`, is the only gap left.
