---
type: Grading Rule
title: R6 - ambiguity codes in the genome
description: A code is graded both ways over a primer's 3'-most 16 nt and the whole probe; only when it decides between detectable and not is the site undetermined.
tags: [grading, IUPAC, R6]
status: draft
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

Changed 2026-11-17 (code review, then the whole-project review): a code is now graded both ways
wherever the rules count mismatches, in a primer's 3'-most 16 nt ([R3](r3-several-mismatches.md))
and anywhere in a probe ([R9](r9-probes.md)). Read as a match beyond the last 5 nt, a code at -8
with a real mismatch at -12 gave tolerated where R3 gives at risk, and an R at -6 under an MGB
hid a likely failure. A lone code beyond the last 5 nt now reads tolerated rather than perfect:
detectable either way. The page was verified on 2026-10-08 for the rule without this change, so
it is back to draft.

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R6
