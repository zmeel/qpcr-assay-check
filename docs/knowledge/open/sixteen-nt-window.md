---
type: Open Item
title: "The 3'-most 16 nt window"
description: "R3/R8 count mismatches within the 3'-most 16 nt, which the biologist calls an artefact of Lefever's 20-mers."
tags: [open, small]
status: draft
origin: "review 7"
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: reviews
    resource: ../../reviews/README.md
    title: "docs/reviews/README.md"
---

# What is open

The window follows the region Lefever tested; for oligos much longer than 20 nt it may undercount ([R3](../rules/r3-several-mismatches.md)). Options: keep and say so, or scale with oligo length (no source for scaling).[^reviews]

# What it needs

The user's choice.

[^reviews]: docs/reviews/README.md
