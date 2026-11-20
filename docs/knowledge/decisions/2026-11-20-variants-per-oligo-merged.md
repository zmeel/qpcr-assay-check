---
type: Decision
title: "Variants per oligo merged into the whole-fragment table"
description: "The report no longer has a separate per-oligo variant table: each site cell of the whole-fragment table shows its rule and changes, folded rows name the variants no listed row shows, and the per-oligo totals stand beside the mismatch maps."
tags: [decision, report]
status: draft
decided_on: 2026-11-20
generated: { by: claude-code/agent, at: 2026-11-20T23:00:00Z }
sources:
  - id: review
    resource: ../../reviews/2026-11-20-report-advisor-round2.md
    title: Advisor's second report review (2026-11-20)
  - id: colours
    resource: 2026-11-20-needs-attention-keeps-its-colours.md
    title: "Needs attention keeps its coloured site rows"
---

# Decision

The report shows the target's site variants in one table, the whole-fragment table. What only
the per-oligo table had moves into it: each site that is not perfect shows its class, its rule
(R2, R9...), its frequency over all records, its dTm, the bases, and under them its changes
("-21 C-A, -18 S=C": position from the 3' end and oligo base-template base). A folded row
("N further combinations", "N other detectable combinations") names the site variants that no
listed row shows, by the per-oligo table's old selection (those that can fail when seen twice or
more, those seen once as a count per class, the 5 most frequent tolerated ones). The per-oligo
totals are one line beside the mismatch maps. The full per-oligo list stays in the workbook
(sheet "Oligo variants", with "Changes" and "Rule").[^review]

# Who and why

User, 2026-11-20, on the first HSV-1 record in the three-part layout: "The Variants per oligo
seems redundant because there is also a Whole fragment part." Asked whether the information
only the per-oligo table had could go into the whole-fragment table instead of the advisor's
compact key: "Yes combine them".

[^review]: Advisor's second report review (2026-11-20)
[^colours]: "Needs attention keeps its coloured site rows"
