---
type: Decision
title: "Per-oligo mismatch maps are not covered by \"no variant graph\""
description: "The user had the per-oligo mismatch maps of the report review built: the decision of 2026-10-03 (no variant graph) does not cover them."
tags: [decision, report]
status: draft
decided_on: 2026-11-20
generated: { by: claude-code/agent, at: 2026-11-20T21:00:00Z }
sources:
  - id: review
    resource: ../../reviews/2026-11-20-report-advisor.md
    title: Advisor review of the HTML report (2026-11-20)
  - id: earlier
    resource: 2026-10-03-no-variant-graph.md
    title: "No graph of the variants for now"
---

# Decision

The report shows, per oligo, where the target genomes differ from it: one column per base, the
share of judged genomes with a mismatch there, by the class of the whole site, counts printed,
the 3' end marked (the specification's per-position mismatch profile, from data already in the
results). The decision of 2026-10-03, no graph of the variants, does not cover it.[^earlier]

# Who and why

User, 2026-11-20, asked whether that decision ruled out the advisor's proposal P3: "Build P3
too".[^review]

[^review]: Advisor review of the HTML report (2026-11-20)
[^earlier]: "No graph of the variants for now"
