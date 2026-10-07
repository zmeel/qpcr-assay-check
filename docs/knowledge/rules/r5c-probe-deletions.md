---
type: Grading Rule
title: R5c - deletions in a probe site
description: 1-5 deleted bases at risk, 6 or more likely failure, from Otwell 2025; the notes now say where that study's data stop (25-28 nt linear probes, 55 C, 50 cycles).
tags: [grading, probe, deletions, R5c]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: otwell
    resource: ../sources/otwell-2025.md
    title: Otwell et al. 2025
  - id: advisor
    resource: literature search by an advisor subagent, 2026-10-07 (PubMed and Europe PMC; Otwell's supplementary workbook parsed)
    title: Advisor literature search on probe-site deletions, 2026-10-07
  - id: d-scope
    resource: ../decisions/2026-10-07-probe-rule-ceiling-and-r5c-scope.md
    title: "Probe mismatch ceiling, and the scope of the deletion data"
  - id: d-small
    resource: ../decisions/2026-10-01-small-review-points.md
    title: Decision to take up the small review points
---

# Rule

Probe bases without a template partner, not at the probe's ends: 1-5 nt `at_risk`, 6 nt or
more `likely_failure` (at 6 nt the assays disagree and the worse is taken); a deletion with three
or more mismatches `likely_failure`, with one or two `at_risk` (a combination not
measured).[^otwell] Built 2026-10-01 from the theory reviews.[^d-small]

Basis: Otwell measured deletions in probe sites of SARS-CoV-2 assays (C4 ORF8: up to 6 nt at
most +5 Ct and always detected, 7 nt mean Ct above 40 at 50 copies, 8 nt not detected; Yale
69/70 del, 6 nt, not detected). Insertions in a probe site stay [R5](r5-gaps.md).

# How far the data reach

The user questioned the lenient classes on 2026-10-06 ("hard to believe that a 1-5 nt deletion in
a probe is only at risk") and an advisor searched the literature.[^advisor] A search of PubMed and
Europe PMC for a probe-site deletion returns this one study, and its whole dataset is 15 templates
from 4 assays. The classes stand, because nothing was found that would justify moving them, but
the site notes now say where the data stop:[^d-scope]

- **25-28 nt linear ZEN/IBFQ probes only.** No study has measured a deletion under an MGB or
  other Tm-raising probe, or under a shorter probe. A 26-mer with a 6-nt gap keeps paired arms of
  about 12 and 8 nt; a 19-mer keeps about 6 and 7. Such a site keeps its class and is flagged
  "no measured data".
- **2 nt and 5 nt were never tested** (1, 3, 4, 6, 7 and 8 were), so those two classes are
  interpolated and say so.
- **55 C annealing and 50 cycles**, chosen by the authors to be permissive, so the thresholds are
  upper bounds: the 7-nt template's mean Ct of 41.0 at 50 copies is already a false negative
  under a 40-cycle cut-off.
- **Sequence decides, not length.** At 6 nt the study holds two near-identical geometries with
  opposite outcomes (C4 ORF8, arms 12 + 8, detected at +4.0 Ct; Yale 69/70 del, arms 11 + 8, not
  detected in four templates).
- **The failure is of signal, not amplification:** minimum positive fluorescence falls from
  14,000-27,000 to about 2,900 at 6 nt while the Ct moves only +4, and dim curves were recovered
  for a failing template on fluorescence-focusing plates. Which side of the line a given
  instrument and plate land on is not predictable from sequence.
- **Every real-world case is 6 nt** (the TaqPath S-gene dropout and similar); no clinical case of
  a 1-5 nt probe-site deletion with a measured outcome has been published.

[^otwell]: Otwell et al. 2025
[^d-small]: Decision to take up the small review points
[^advisor]: Advisor literature search on probe-site deletions, 2026-10-07
[^d-scope]: Probe mismatch ceiling, and the scope of the deletion data
