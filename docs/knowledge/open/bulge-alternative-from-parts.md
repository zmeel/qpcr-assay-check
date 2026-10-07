---
type: Open Item
title: The bracketing bulge figure drops the from-parts genomes
description: The "x% if run-length differences were tolerated" figure counted a genome judged from parts as not detectable, so it could fall below the headline. Fixed the same day (option 2).
tags: [open, bug, inclusivity, homopolymer, closed]
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

# Closed: option 2, 2026-10-07

Two fixes were put to the user: carry the same `parts` term into `n_detectable_other_rule`, or
also re-run `_assess_parts` under the other rule so that a genome detectable from parts *only*
because a bulge is tolerated is counted as well. The user chose the second ("Execute option 2").

`assess` now computes, for each genome that gets a `GenomeCall`, the copies detectable under the
other rule and - when none is - the judgement from parts under that rule, with the same guard as
the configured rule (only a detectable judgement counts). `_assess_parts` is called a second time
only for a genome with no copy detectable under the other rule and at least one cut copy, so the
cost falls on the genomes that already needed it.

Reach of the second half: a genome with **no** whole copy and no detectable parts under the
configured rule never gets a `GenomeCall` at all (it counts as cut by a contig end, undetermined,
and is outside both figures' cohort), so the extra case is a genome with a failing whole copy
*and* cut copies whose parts pass only under the lenient rule. That is the Legionella shape.

Covered by `test_the_bulge_alternative_counts_the_genomes_judged_from_parts`, which checks both
halves and fails on the old code (50.0% where 75.0% is right). Reports written before the fix
carry the understated bracketing figure; the headline, the per-year table, the channel figures
and the classes were never affected, so no earlier conclusion changes.

[^run]: "Legionella, 2026-10-07 (09:48Z)"
[^code]: variants/exhaustive.py (n_detectable_other_rule, bulge_alternative)
[^decision]: Decision to take up the small review points
