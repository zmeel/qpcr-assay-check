---
type: Grading Rule
title: R6 - ambiguity codes in the genome
description: A code is graded both ways in the last 5 nt; only when it decides between detectable and not is the site undetermined.
tags: [grading, IUPAC, R6]
status: stable
verified: { by: human:zmeel, at: 2026-10-08T07:33:00Z }
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, R6
---

# Rule

A code (R, Y, ...) in the genome that can pair with the oligo base counts as a match beyond the
last 5 nt. In the last 5 nt the site is graded with the code as a match and as a mismatch: when
both results are detectable, or both are not, that class is kept (the worse if both are
detectable); only when the code decides between detectable and not is the site `indeterminate`,
and the genome undetermined. A code that cannot pair is a mismatch. An ambiguity code therefore
never hides a real failure. No source: a presentation of uncertainty, not a
prediction.[^mismatch-classes]

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R6
