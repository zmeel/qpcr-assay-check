---
type: Open Item
title: The bracketing bulge figure drops the from-parts genomes
description: The "x% if run-length differences were tolerated" figure counts a genome judged from parts as not detectable, so it can fall below the headline, which is impossible over a fixed cohort.
tags: [open, bug, inclusivity, homopolymer]
status: draft
generated: { by: claude-code/agent, at: 2026-10-07T15:00:00Z }
sources:
  - id: run
    resource: ../runs/legionella-2026-10-07.md
    title: "Legionella, 2026-10-07 (09:48Z)"
  - id: code
    resource: ../../../src/qpcr_assay_check/variants/exhaustive.py
    title: variants/exhaustive.py (n_detectable_other_rule, bulge_alternative)
  - id: decision
    resource: ../decisions/2026-10-01-small-review-points.md
    title: Decision to take up the small review points
---

# What is wrong

Every report gives the status figure under the other homopolymer-bulge setting, as the interval
the theory reviews asked for.[^decision] In the Legionella run of 2026-10-07 that line reads
**44.7% if single-base run-length differences were tolerated** against **94.0%** with them not
tolerated.[^run] Tolerating more can never lower detectability over a fixed cohort, so the
figure is wrong, not merely surprising.

# Why

In `assess_variants`, a genome whose region is split over contigs but which carries a whole
detectable site of every role is counted as detected through `judge_from_parts`:

```python
n_detectable=sum(all(roles_ok(c, bulges).values()) for c, _a in copies)
+ (parts is not None and parts_rule == "detectable"),
```

`n_detectable_other_rule` recomputes the same thing under `not bulges` but **without that
term**, so a genome detected only from parts is never in the `other_rule` set that
`bulge_alternative` counts in its numerator. Both figures use the same denominator (the
`FROM_PARTS` genomes, those *not* counted, are excluded from both), so the alternative is short
by exactly the genomes counted from parts: 2,928 of them in that run.[^code]

# Reproduced

With the existing `_split_fixture` of `tests/test_variants_exhaustive.py` and the default
`judge_from_parts: detectable`, four judged genomes give a headline of 75.0% detectable and a
bracketing figure of **50.0%**, although no genome in the fixture has a homopolymer bulge at
all. Adding the same `parts` term to `n_detectable_other_rule` makes it 75.0%.

# The decision to take

1. **The one-line fix**: carry the same `parts` term into `n_detectable_other_rule`. Correct
   whenever a genome is judged from parts under both rules, which is the case for every genome
   in the Legionella run.
2. **The fuller fix**: also re-run `_assess_parts` under the other rule, so a genome that would
   be detectable from parts *only* because a bulge is tolerated is counted too. More faithful,
   a little more work per genome, and it moves the figure further.

Option 1 removes the impossible result; option 2 also removes a remaining understatement. Not
built: it changes a number in reports already filed, so the user decides. Reports written
before the fix carry the understated figure; the headline, the per-year table, the channel
figures and the classes are unaffected.

[^run]: "Legionella, 2026-10-07 (09:48Z)"
[^code]: variants/exhaustive.py (n_detectable_other_rule, bulge_alternative)
[^decision]: Decision to take up the small review points
