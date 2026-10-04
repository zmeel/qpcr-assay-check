---
type: Open Item
title: "One rule set for off-target sites"
description: "Specificity uses its own mismatch heuristics instead of the graded classes; a per-tier amplicon BLAST is not built."
tags: [open, large]
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

# What it needs

The user's go-ahead; changes specificity results.

[^reviews]: docs/reviews/README.md
