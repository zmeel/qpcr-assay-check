---
type: Open Item
title: "One rule set for off-target sites (partly done)"
description: "Since 2026-11-17 the graded classes decide off-target priming and binding together with the levels; a per-tier amplicon BLAST is still not built."
tags: [open, large, partly-done]
status: draft
origin: "review, larger 2"
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: reviews
    resource: ../../reviews/README.md
    title: "docs/reviews/README.md"
---

# What is open

Off-target sites are critical/warning by counts ([specificity findings](../rules/specificity-findings.md)); the advisor asks for the graded classes there too, plus a reference-fragment BLAST per off-target tier for products where BLAST reported neither primer.[^reviews]

Done 2026-11-17 (user: "fix the remaining issues" of the whole-project review, P3): off-target
sites get the classes of R1-R9 and they decide priming and binding together with the levels
([specificity findings](../rules/specificity-findings.md)). Still open: a reference-fragment BLAST
per off-target tier, for products where BLAST reported neither primer.

# What it needs

For the per-tier BLAST: a design, and the user's go-ahead (more searches at NCBI).

[^reviews]: docs/reviews/README.md
