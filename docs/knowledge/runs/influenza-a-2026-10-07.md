---
type: Run
title: Influenza A (matrix), 2026-10-07 (13:08Z)
description: First influenza A run; its figures describe a reverse primer two bases short, found from the data and corrected the same day, so they are not an assessment of the assay.
tags: [run, influenza]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-07T16:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-07T13:08:43Z (uploaded in the session of 2026-10-07, not in the repository)
    title: Report of the 13:08Z run
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: Influenza A, matrix gene (two NED probes)
  - id: records
    resource: "live EFetch of PZ488030.1 and PZ641704.1, 2026-10-07"
    title: The two records the user downloaded, aligned live
  - id: session
    resource: ../sessions/2026-10-07-02-influenza-a-assay.md
    title: "Session 2026-10-07: Influenza A assay file"
---

# Run

[Assay](../assays/influenza-a-matrix.md) as first written, with the reverse primer as the other
laboratory sent it (22 nt). qpcr-assay-check v2.1.0, 15,000 of the 172,768 listed records
assessed; status **Exceeds limit**.[^report]

# Do not read these figures as an assessment

The run was made with a reverse primer two bases short of the real site, so every reverse site
carried two differences that are not in the genomes. For the record, what it said: 85.4%
detectable, 87.0% including at risk, 13.0% likely failure of 12,848 records collected 2023-2026;
coverage found the region in 14,969 of 15,000 records assessed, 29 hidden by N, 2 cut by a
record end; off-target no predicted product in either searched tier; oligo QC 1 outside the
limit (primer Tm difference 6.2 C) and 5 outside the preferred range.

# How the primer was found out, from the data

- **Every** reverse site was wrong in the same way: all 23 site variants, over all 14,960
  assessed records (100%), carried `-21 C-A, -20 T-C`. Not one record in 15,000 matched the
  primer perfectly, which no real primer does over a taxon this size.
- The user read it the other way round first ("the tool detects 2 mismatches in every reverse
  primer that are not there in real") and downloaded two records to check.
- Those two records, aligned live: the 22-mer gives **3** mismatches in both, the 24-mer
  **1**, and the one left is strain variation at a different position in each (3'-terminal G-T
  in PZ488030.1, G-A at -3 in PZ641704.1). The forward primer and PfluA1 match both exactly, so
  only the reverse primer was off.[^records]
- What the two phantom bases cost the classes: 12,582 records (84.1%) carried **only** them and
  were graded `tolerated` by R3b where they should be perfect; the 1,649 records (11.0%) with a
  real 3'-terminal G-A were `likely failure` (R1+R3b, "plus 2 mismatches beyond -16") where a
  lone terminal G1 mismatch is `at risk`. That is most of the report's 13.0% likely failure.
  Every reverse Tm was about 5.5 C low, which is where the one hard QC failure came from.

The tool was right throughout: the differences were real against the primer it was given. No
code was changed.

# What followed

The user gave their own laboratory's primer for the same PCR, the 24-mer, and the assay file now
carries it. `run --qc-only` with it: the reverse site sits at 118-141 exactly with no mismatch,
the product is the whole 141-nt reference with no flanking bases, and oligo QC falls from
**Exceeds limit** to **Review** (the primer Tm difference is 3.4 C, within the limit; a new
preferred-range warning appears for PfluA2, 4.6 C above the mean primer Tm, because the reverse
primer's Tm rose). A fresh run is needed; the cached regions for this assay must be cleared
first so the reverse sites are re-aligned.

[^report]: Report of the 13:08Z run
[^records]: The two records the user downloaded, aligned live
[^session]: "Session 2026-10-07: Influenza A assay file"
