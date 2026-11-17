---
type: Grading Rule
title: R6 - ambiguity codes in the genome
description: A code is graded both ways in the last 5 nt (anywhere in an MGB probe); only when it decides between detectable and not is the site undetermined.
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

In an MGB probe a code anywhere in the site is graded both ways (2026-11-17, code review): one
mismatch anywhere changes an MGB probe's class under [R9](r9-probes.md) (likely failure under
the MGB, the 3'-most 7 nt; undetermined outside it), so a code at -6 or -7 read as a match
could hide a likely failure. The page was verified on 2026-10-08 for the rule without this
addition, so it is back to draft.

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R6
