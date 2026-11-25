---
type: Decision
title: "Findings condensed: no repeated list, specificity as a table per tier"
description: "The report drops \"All findings behind the summary\" (each line was printed elsewhere too), shows the specificity findings as one table with a row per tier, and prints a QC message only where it adds to the table cell."
tags: [decision, report]
status: draft
decided_on: 2026-11-25
generated: { by: claude-code/agent, at: 2026-11-25T12:00:00Z }
sources:
  - id: twopages
    resource: 2026-11-20-sign-off-two-pages-amplicon-order.md
    title: "Sign-off on two pages: short gap lines, site maps in Part B, oligos in amplicon order"
---

# Decision

- **No "All findings behind the summary".** In the HSV-1 record of 2026-11-25, its 21 lines all
  appeared a second time: the 10 oligo-design lines in the QC matrix, the 11 specificity lines
  word for word in the off-target "Findings" list. The full list stays in the workbook sheet
  "Findings" and in results.json (`overall.rationale`), and Part A points there. Lines that no
  section of Part B shows are still printed, under "Other findings": unsearched tiers, the human
  background not searched, unresolved organism names, variant-analysis notes, LNA probes and
  "not evaluated".
- **Specificity findings as one table, a row per tier.** The table has these columns:
  - products, detected / amplified, with the number of distinct patterns;
  - primer sites without amplicon, critical / warning (one column since 2026-11-25: "critical in
    a product" was roughly twice the amplicon count, and warning sites are now split by amplicon
    as critical ones are);
  - probe sites;
  - the closest primer site;
  - the evidence missing;
  - the tier's status.

  Each count is shown in the colour of its finding. A gap shows its short wording in the table,
  and its full message is a numbered note below the table. Gaps of no single tier, such as the
  partner scan, go in an "All tiers" row. Findings that fit no column are listed under "Other
  specificity findings". The per-tier notes and the "Findings" sentences are dropped, but the
  remark on which primer carries the discrimination is kept. The findings carry `kind`, `count`
  and `site` for this, so the table only reads the findings and never re-derives them. Records
  made before this change keep the old list.
- **QC messages only where they add something.** A message that only restates the cell ("…is
  outside the preferred range…", "…outside the limit…") is not printed under the QC matrix or
  the pair and amplicon table. Messages that add a reason remain, such as "the 3′ end may be too
  stable" or the reference-amplicon mismatch.

Simulated on the user's HSV-1 HTML: 19 printed pages instead of 22, with a 2-page sign-off.
The user's run of 2026-11-25 08:21Z confirmed it: 19 pages, with a 2-page sign-off.

That run showed three faults, fixed at the user's request ("Yes, fix all 3"):

- **The closest primer site could be a minor site.** It is now chosen among sites at warning or
  critical level, in the table and in Part A's glyph.
- **Two information lines were printed twice.** They are also in the products paragraph and are
  no longer listed separately.
- **Raw labels in the product and site tables.** The tier and the probe signal are now named in
  words.

# Who and why

User, 2026-11-25, on "All findings behind the summary": "Is it possible to reduce this section
by presenting it graphically or a table?" Three steps were proposed (drop the repeated list, a
tier table, shorter QC messages), with the trade-off that the paper record no longer holds the
findings as one list. The user's answer: "Do all three".

[^twopages]: "Sign-off on two pages: short gap lines, site maps in Part B, oligos in amplicon order"
