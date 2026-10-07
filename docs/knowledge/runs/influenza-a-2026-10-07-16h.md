---
type: Run
title: Influenza A (matrix), 2026-10-07 (16:14Z)
description: "45,000 of 172,768 records: 76.9% detectable, Exceeds limit. Both degenerate-oligo fixes confirmed in the output, and one reverse-primer variant accounts for 97.6% of the failures."
tags: [run, influenza]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-07T18:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-07T16:14:22Z (uploaded in the session of 2026-10-07, not in the repository)
    title: Report of the 16:14Z run
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: Influenza A, matrix gene (two NED probes)
  - id: previous
    resource: influenza-a-2026-10-07-corrected.md
    title: "Influenza A (matrix), 2026-10-07 (14:01Z)"
  - id: fix
    resource: ../open/degenerate-duplex-baseline.md
    title: Degenerate oligos broke the duplex Tm baseline
  - id: sampling
    resource: "live ESearch and EFetch, 2026-10-07: 40 segment-7 records per publication year"
    title: Sampling of the terminal-mismatch share per publication year
  - id: provisional
    resource: ../open/partial-coverage-and-the-inclusivity-limit.md
    title: An inclusivity FAIL on partly assessed records
---

# Run

[Assay](../assays/influenza-a-matrix.md) with the laboratory's 24-mer reverse primer and the
degenerate-oligo fixes of the same day; v2.1.0, 45,000 of the 172,768 listed records
assessed.[^report]

# Key numbers

**Exceeds limit**, 4 of 6 checks flagged, 2 incomplete or not assessed.

- **Whole fragment, collected 2023-2026**: 35,078 records judged, **76.9% detectable**, 77.4%
  including at risk, 22.6% likely failure; 9 undetermined. Exceeds limit because it is below the
  configured 80%. 175 distinct site patterns, 61.1% detectable (information).
- **By release year**: 2026 all 26,560 records assessed, 86.1% detectable, 13.2% likely failure;
  2025 18,440 of 35,909 assessed, **75.2%** detectable, 24.6% likely failure; 2024 and earlier
  not assessed at all. Pooled over the release years: 81.6%.
- **Coverage**: region found in 44,960 of 45,000 assessed, hidden by N in 37, cut by a record end
  in 3. Incomplete: 127,768 records still to assess.
- **Oligo QC**: 0 outside the limit, 6 outside the preferred range (as at 14:01Z).
- **Specificity**: no predicted product in either searched tier; near neighbours not searched.

# One variant decides this assay

Of the 8,186 records in "Needs attention" (85 combinations), **7,989 (97.6%)** are there because
of one reverse-primer site: a **3'-terminal G-A mismatch**, `-1 G-A`, graded likely failure by R1
(type group G1, terminal, "avoid" in Stadhouders Table 1). Its own frequency among all reverse
sites is **17.4%** (7,827 records), with a second form carrying C under the primer's degenerate Y
instead of T (26 records) and a third with an extra mismatch at -18 (98 records). Everything else
in the table is a handful of records.

So the assay's inclusivity rests on one question, and it is a wet-lab question: does this primer
extend over a terminal G-A? A template carrying that site is the single most useful thing to test.

# The figure is still moving

85.4% (15,000 records, short primer) -> 83.6% (20,000) -> **76.9%** (45,000). The release-year
table shows why: the analysis works newest publication year first, so early runs saw mostly 2026
(86.1% detectable) and this one has moved into 2025 (75.2% over the half assessed), with 2024
(22,360 records) and 2023 (14,394) untouched.

It will move again, and not smoothly: NCBI lists records in submission batches, so consecutive
records are strongly correlated. A sample of 40 records per publication year, taken live, gave
0%, 12%, 15% and 0% carrying the terminal mismatch for 2026, 2025, 2024 and 2023 - which is what
batch structure looks like, not a trend.[^sampling] Only 26% of the listed records are assessed,
so 76.9% is provisional; the run must be repeated until coverage completes before the figure
means anything for the assay.[^provisional]

# Both fixes confirmed in the output

- The two rows the user compared at 14:01Z are now told apart and agree: row 1
  `............... T ...` and row 3 `............... C ...` (the base under the primer's Y
  written out in grey), both **ΔTm -0.7 C**, where they read -3.6 and +0.0 before.[^fix]
- The **"Tm <= annealing"** flag fires for the first time on this assay (row 2, ΔTm -7.0 C): it
  was unreachable while the baseline sat below the annealing temperature.
- 111 grey degenerate bases in the report, and `site_changes` names them (`-9 Y=T`), as does the
  forward primer's R position (`..... A ............`).

[^report]: Report of the 16:14Z run
[^previous]: "Influenza A (matrix), 2026-10-07 (14:01Z)"
[^fix]: Degenerate oligos broke the duplex Tm baseline
[^sampling]: Sampling of the terminal-mismatch share per publication year
[^provisional]: An inclusivity FAIL on partly assessed records
