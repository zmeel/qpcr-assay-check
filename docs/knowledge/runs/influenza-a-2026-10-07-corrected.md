---
type: Run
title: Influenza A (matrix), 2026-10-07 (14:01Z)
description: "First run with the corrected reverse primer: 83.6% detectable of 17,058 records, Incomplete only because 152,768 records are still to assess; its first two rows exposed the degenerate-oligo Tm baseline."
tags: [run, influenza]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-07T17:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-07T14:01:52Z (uploaded in the session of 2026-10-07, not in the repository)
    title: Report of the 14:01Z run
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: Influenza A, matrix gene (two NED probes)
  - id: previous
    resource: influenza-a-2026-10-07.md
    title: "Influenza A (matrix), 2026-10-07 (13:08Z)"
  - id: bug
    resource: ../open/degenerate-duplex-baseline.md
    title: Degenerate oligos broke the duplex Tm baseline
---

# Run

[Assay](../assays/influenza-a-matrix.md) with the laboratory's 24-mer reverse primer, the first
run after the correction; v2.1.0, 20,000 of the 172,768 listed records assessed.[^report]

# Key numbers

**Incomplete**, 3 of 6 checks flagged, 3 incomplete or not assessed.

- **Whole fragment, collected 2023-2026**: 17,058 records judged, **83.6% detectable**, 84.5%
  including at risk, 15.5% likely failure; 7 undetermined (4 cut or hidden by N). The
  whole-fragment status is Review (below 95%); the run as a whole is Incomplete because 152,768
  records are still to assess. 111 distinct site patterns, 64.0% detectable (information).
- **Coverage**: region found in 19,964 of 20,000 assessed, hidden by N in 34, cut by a record end
  in 2.
- **Oligo QC**: **0 outside the limit** (it was 1 under the 22-mer), 6 outside the preferred
  range: FfluA Tm 64.3-66.4, PfluA2 Tm 4.6-6.4 above the mean primer Tm, a run of 5 identical
  bases in each probe, the primer Tm difference 3.4 C, and PfluA2's designed single mismatch
  against the reference.
- **Specificity**: no predicted product in either searched tier (clinical list 17/17 names
  resolved, 2 critical primer sites; background 0 critical and 46 warning sites); near neighbours
  not searched.

Against the [13:08Z run](influenza-a-2026-10-07.md) under the short primer, the headline moved
from 85.4% to 83.6%: with the primer in register, the real 3'-terminal mismatch now stands alone
as the reason a record fails, and more records fall to likely failure rather than being carried
by a tolerated reverse site.[^previous] 49 "needs attention" combinations against 67.

# What it exposed

The user compared the first two rows of "Needs attention": identical in every column, ΔTm -3.6 C
against +0.0 C. They are two site variants differing only in the base under the primer's
degenerate Y, which the dot notation hid - and the ΔTm figures themselves turned out to be
measured against a baseline about 15 C too low for any degenerate oligo. Both were fixed the same
day.[^bug]

[^report]: Report of the 14:01Z run
[^previous]: "Influenza A (matrix), 2026-10-07 (13:08Z)"
[^bug]: Degenerate oligos broke the duplex Tm baseline
