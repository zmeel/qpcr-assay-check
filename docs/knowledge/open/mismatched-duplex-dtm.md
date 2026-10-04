---
type: Open Item
title: "Exact Tm of the mismatched duplex"
description: "Compute ΔTm on the actual mismatched duplex instead of the current estimate; check primer3's documentation first."
tags: [open, medium]
status: draft
origin: "review 5"
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: reviews
    resource: ../../reviews/README.md
    title: "docs/reviews/README.md"
---

# What is open

ΔTm next to a class is an estimate; the molecular biologist asked for the Tm of the mismatched duplex itself. Information only either way; the class stays the judgement.[^reviews]

# What it needs

Check what primer3-py documents for mismatched duplexes before building anything (hard rule: no invented API behaviour).

[^reviews]: docs/reviews/README.md
