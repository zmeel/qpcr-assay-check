---
type: Grading Rule
title: R5 - gaps (bulges)
description: A gap is indeterminate unless the site's mismatches already give at risk or likely failure; an unpaired end base is a mismatch.
tags: [grading, gaps, R5]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, R5
---

# Rule

Neither Stadhouders nor Lefever tested insertions or deletions, so a gap is `indeterminate`.
A gap can only make a site worse: when the mismatches alone already give `at_risk` or
`likely_failure`, that class stands, noted "plus a gap" (user, 2026-09-26, after a probe variant
with 7 mismatches and a gap was reported indeterminate). An oligo base at either end without a
partner base in the genome is read as a mismatch at that position, not as a gap (user,
2026-09-26).[^mismatch-classes]

Exceptions with their own rules: homopolymer length differences in a primer
([R5b](r5b-homopolymer-length.md)) and deletions in a probe site
([R5c](r5c-probe-deletions.md)). For inclusivity an `indeterminate` gap counts as not detected
([classes](classes.md)).

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R5
