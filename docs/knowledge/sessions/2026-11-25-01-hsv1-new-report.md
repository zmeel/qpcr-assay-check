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
