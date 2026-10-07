---
type: Decision
title: "Probe mismatch ceiling, and the scope of the deletion data"
description: "An unmodified probe with 3 or more mismatches is a likely failure; the probe-deletion classes stay, but say where the one study's data stop."
tags: [decision, probe, grading]
status: draft
decided_on: 2026-10-07
generated: { by: claude-code/agent, at: 2026-10-07T12:00:00Z }
sources:
  - id: session
    resource: ../sessions/2026-10-07-01-probe-rules.md
    title: "Session 2026-10-07: probe rules"
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: r5c
    resource: ../rules/r5c-probe-deletions.md
    title: R5c - deletions in a probe site
  - id: klungthong
    resource: ../sources/klungthong-2010.md
    title: Klungthong et al. 2010
  - id: otwell
    resource: ../sources/otwell-2025.md
    title: Otwell et al. 2025
---

# Decision

Two changes to the probe rules, taken together.

**1. A ceiling for unmodified probes ([R9](../rules/r9-probes.md)).** One mismatch outside the
last 5 nt stays `tolerated`; one in the last 5 nt or two anywhere is `at_risk`; **three or more
is `likely_failure`**. MGB probes are unchanged.[^r9]

**2. The deletion classes stay, but say what they rest on
([R5c](../rules/r5c-probe-deletions.md)).** 1-5 nt stays `at_risk` and 6 nt or more
`likely_failure`. A site now carries a note when it falls outside what was measured: an MGB probe
or a probe shorter than 25 nt ("no measured data"), and a deletion of 2 or 5 nt
("interpolated"). The report states the calibration conditions.[^r5c]

# Who and why

The user read R5c and did not believe that a 1-5 nt deletion in a probe is only at risk, and asked
for a literature search. The same day they read the Legionella run of 2026-10-02 and found a row
where the unmodified 35-nt LEGpneu probe with **11 mismatches and 2 gaps** was graded `at_risk`,
while the 19-nt MGB LEGgenus probe with 7 mismatches on the same genome was `likely_failure`. The
cause was that R9's unmodified branch had no count-based escalation at all: everything beyond one
internal mismatch landed in one `at_risk` fallback. The user chose the cut-off: "2 at risk, 3 or
more likely failure".[^session]

The advisor's search found nothing that would justify moving the deletion thresholds in either
direction, but showed the evidence is far narrower than the rule implied: one study, 15 templates
from 4 assays, 25-28 nt linear probes at 55 C over 50 cycles, with no 2-nt or 5-nt data point and
nothing at all on MGB probes.[^otwell] So the classes stayed and the limits became visible
instead.

# What it rests on

- The 2-mismatch step is measured: an unmodified 30-mer probe with two mismatches detected every
  sample, its mean Ct gap to the reference target widening from 5.58 to 9.28.[^klungthong]
- The ceiling at 3 is **expert judgement with no source**, the same standing as the MGB rule that
  calls 2 or more mismatches a likely failure.
- The deletion thresholds are Otwell's, and the notes now name their limits.[^otwell]

# What followed

The headline detectable percentage does not move: `at_risk` and `likely_failure` both count as
not detected, and both are escapes. What changes is the class shown on a site, the per-year
counts of at risk against likely failure, and the "Needs attention" labels. Of the example
assays, only Legionella has unmodified probes, so only its rows change; the MGB assays
(Neisseria, enterovirus, E. histolytica) are untouched.

[^session]: "Session 2026-10-07: probe rules"
[^r9]: R9 - probe mismatches
[^r5c]: R5c - deletions in a probe site
[^klungthong]: Klungthong et al. 2010
[^otwell]: Otwell et al. 2025
