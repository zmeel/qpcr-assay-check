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
