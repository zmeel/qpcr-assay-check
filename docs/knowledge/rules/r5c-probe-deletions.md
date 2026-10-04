---
type: Grading Rule
title: R5c - deletions in a probe site
description: 1-5 deleted bases at risk, 6 or more likely failure, graded from Otwell 2025's probe-site deletions.
tags: [grading, probe, deletions, R5c]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: otwell
    resource: ../sources/otwell-2025.md
    title: Otwell et al. 2025
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
69/70 del, 6 nt, not detected). One study, unmodified ZEN/IBFQ probes under permissive
conditions; whether MGB probes behave alike is not known. Insertions in a probe site stay
[R5](r5-gaps.md).

[^otwell]: Otwell et al. 2025
[^d-small]: Decision to take up the small review points
