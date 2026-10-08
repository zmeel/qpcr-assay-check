---
type: Run
title: Influenza A (matrix), 2026-10-07 (17:35Z, complete)
description: "All 172,768 records assessed: 69.0% detectable, Exceeds limit on the full population. The per-year tables date the reverse primer's terminal mismatch sweeping in: 0.7% of 2021 collections, 6.9% of 2022, 40.5% of 2023."
tags: [run, influenza, complete]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-08T09:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-07T17:35:09Z (uploaded in the session of 2026-10-07, not in the repository)
    title: Report of the 17:35Z run (complete)
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: Influenza A, matrix gene (two NED probes)
  - id: previous
    resource: influenza-a-2026-10-07-16h.md
    title: "Influenza A (matrix), 2026-10-07 (16:14Z)"
  - id: holdback
    resource: ../open/partial-coverage-and-the-inclusivity-limit.md
    title: An inclusivity FAIL on partly assessed records
  - id: sampling
    resource: "live ESearch and EFetch, 2026-10-08: segment-7 records by release year and host in the title"
    title: Sampling of the terminal-mismatch carriers by period and host
---

# Run

[Assay](../assays/influenza-a-matrix.md), v2.1.0, the **first complete run**: all 172,768
records NCBI listed that day assessed, coverage **No flags** (region found in 172,626, not found
in 1, hidden by N in 113, cut by a record end in 28).[^report]

**Exceeds limit**: 69.0% detectable of 69,688 records collected 2023-2026, 69.4% including at
risk, 30.6% likely failure; 27 undetermined; 238 distinct site patterns, 55.0% of them
detectable. 4 of 6 checks flagged, near neighbours not searched. Oligo QC unchanged (0 outside
the limit, 6 outside the preferred range), no predicted off-target product in either searched
tier.

The hold-back built the same day stood aside correctly: with coverage complete the limits decide
again, so this FAIL is on the whole population and not on a subset.[^holdback]

# The sweep the per-year tables show

One reverse-primer variant decides the assay, as in every run: a **3'-terminal G-A mismatch**,
likely failure by R1, 20,321 records (11.8% of all reverse sites). 97.0% of the records in "Needs
attention" (328 combinations) are there for a reverse site graded likely failure, and the single
largest combination is 19,991 records (11.6%) whose forward primer and probe are perfect and
whose only defect is that base.

By **collection** year, the share of likely failure:

| collected | records with the region | likely failure |
|---|---|---|
| before 2017 | 12,254 | 0.2% |
| 2017-2020 | 6,812 / 8,722 / 11,657 / 3,934 | 0.2% / 0.4% / 0.3% / 0.1% |
| 2021 | 5,264 | 0.7% |
| **2022** | 20,970 | **6.9%** |
| **2023** | 12,012 | **40.5%** |
| 2024 | 23,211 | 30.1% |
| 2025 | 26,444 | 31.3% |
| 2026 | 8,048 | 14.8% |

By **release** year the step lands a year later (0.5% in 2022, 20.6% in 2023, 31.2% in 2024,
26.6% in 2025, 13.2% in 2026), because deposition lags collection. That is exactly what the
collection axis is for, and here it dates the rise to the 2022 season rather than 2023.

# It is an expansion, not an introduction

The variant is not new. The earliest record carrying this exact reverse site was released
**2004-07-08**, and the tolerated reverse variants go back to 2006-2010. What changed is its
frequency.

Two live samples, not the population:[^sampling]

- Of 30 segment-7 records released 2004-2010, **one** carried it, and it was avian:
  A/chicken/Aguascalientes/124-3705/1998 (H5N2). Of 30 released 2011-2016, none did.
- Of 225 records released 2023, 2024 and 2026 (three blocks per year), every one of the 17
  carriers had a human or unstated strain name, and **none of the 111 records whose title names a
  non-human host** (chicken, duck, swine, cattle, dairy and so on) carried it. So the sweep is in
  human-lineage influenza A, not in the avian H5N1 sequencing that fills much of 2023-2024.
  Sampling blocks are batch-correlated, so the proportions are not estimates; the
  0-of-111 contrast is the point.

The 2026 figure (14.8%) may be the clade receding or deposition for recent collections still
filling: 8,048 records collected 2026 against 26,444 for 2025.

# What it means for the laboratory

The assay's inclusivity rests on one wet-lab question: does this reverse primer extend over a
3'-terminal G-A? The in silico class is R1 "avoid" from Stadhouders Table 1, which is published
data on a terminal mismatch of type group G1, not a measurement of this primer. A template
carrying that site would settle 97% of the failures, and the per-year table says the question
became urgent with the 2022-2023 seasons.

[^report]: Report of the 17:35Z run (complete)
[^previous]: "Influenza A (matrix), 2026-10-07 (16:14Z)"
[^holdback]: An inclusivity FAIL on partly assessed records
[^sampling]: Sampling of the terminal-mismatch carriers by period and host
