---
type: Decision
title: "Sign-off on two pages: short gap lines, site maps in Part B, oligos in amplicon order"
description: "Part A lists specificity gaps as one short line per tier and kind, the per-oligo site maps open Part B with only their totals left in Part A, and the report and workbook list oligos forward, probe, reverse."
tags: [decision, report]
status: draft
decided_on: 2026-11-20
generated: { by: claude-code/agent, at: 2026-11-20T23:30:00Z }
sources:
  - id: merged
    resource: 2026-11-20-variants-per-oligo-merged.md
    title: "Variants per oligo merged into the whole-fragment table"
  - id: review
    resource: ../../reviews/2026-11-20-report-advisor-round2.md
    title: Advisor's second report review (2026-11-20)
---

# Decision

The sign-off (Part A) has to fit on two A4 pages, decision box included. The HSV-1 record of
2026-11-20 16:52Z still needed three: four Incomplete specificity lines repeated Part B's full
messages, and the decision box landed alone on page 3.[^review]

- **Short gap lines.** A specificity finding that exceeds a limit or leaves evidence missing
  carries a short wording (`Finding.short`, with `tier` and `about`). On the sign-off, findings
  with the same tier and short wording become one line, listing what they are about. For
  example: "Specificity, Background: relevant alignments cut at max_sites_per_query (FP_v8, P)",
  or "Specificity, Near neighbours: product list cut at max_amplicons, not bounded". The full
  messages stay in Part B ("All findings behind the summary"). A finding without a short wording,
  for example from an older record, is printed in full as before.
- **An oligo check beyond its limit names the oligo** ("HSV-1-gG1-FP: Tm of 72.5 °C is outside
  the limit"). Without the name, the two Tm lines did not say whose Tm they were.
- **Site maps in Part B.** The per-oligo mismatch maps open Part B's target detection, just
  before the whole-fragment table. Part A keeps their totals line and a link to them.
- **The decision box stays together** with its heading and note. The NCBI line moved into the
  header. In print, the year bars are 85% wide and the box's writing space is a little lower.
- **Oligos in amplicon order.** The report and the workbook list oligos forward, probe, reverse,
  as the whole-fragment table reads. This covers the site maps, the totals, the Tm figure, the QC
  matrix, the assay table, the copies table and the "Inputs" and "Oligo variants" sheets. The
  searches keep their own order (`Assay.oligo_list`), so this display change cannot change what
  is submitted to NCBI or how queries are grouped per search.

Measured on the user's HSV-1 report with these changes applied: Part A is two A4 pages with the
decision box. The whole record is 22 pages.

# Who and why

User, 2026-11-20, on the HSV-1 record in the new layout. On the two options offered (short
lines, maps to Part B): "Do both". On the order: "By the 'Where the target differs from the
oligos' section the probe is the last oligo and that is a bit confusion as everywhere else the
reverse primer is the last oligo."

[^merged]: "Variants per oligo merged into the whole-fragment table"
[^review]: Advisor's second report review (2026-11-20)
