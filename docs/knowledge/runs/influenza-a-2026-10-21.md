---
type: Run
title: Influenza A (matrix), 2026-10-21 (15:42Z, complete, both reverse primers)
description: "The first run with infa_rev2: 99.6% detectable of the 70,606 records collected 2023-2026 (was 69.0% with infa_rev alone), likely failure 30.6% -> 0.0%; Review, no limit crossed. infa_rev2 is the only working reverse primer for 23,595 records (13.6%)."
tags: [run, influenza, complete]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-23T10:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-21T15:42:44Z (uploaded in the session of 2026-10-23, not in the repository)
    title: Report of the 15:42Z run (complete)
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: "Influenza A (matrix gene)"
  - id: previous
    resource: influenza-a-2026-10-07-complete.md
    title: "Influenza A (matrix), 2026-10-07 (17:35Z, complete)"
  - id: slow-queue
    resource: ../open/blast-slow-queue.md
    title: BLAST searches held for a day by a change at NCBI
---

# Run

[Assay](../assays/influenza-a-matrix.md) with the Erasmus MC protocol's second reverse primer
`infa_rev2` (3'-terminal T), v2.1.0, run `20261021T154244Z`. Complete: all 173,689 records NCBI
listed that day assessed (region found in 173,547, not found in 1, hidden by N in 113, cut by a
record end in 28); 921 of them new in this run, the rest from the region store of earlier
runs, re-judged with the new oligo set.[^report]

**Review, no limit crossed**: 3 of 6 checks flagged for review (oligo QC: 0 outside the limit, 8
outside the preferred range; two off-target tiers with warning or critical primer sites but no
product), near neighbours not searched.

# Detection

| | 2026-10-07, `infa_rev` only | 2026-10-21, `infa_rev` + `infa_rev2` |
|---|---|---|
| Detectable, collected 2023-2026 | 69.0% of 69,688 | **99.6% of 70,606** |
| Including at risk | 69.4% | 100.0% |
| Likely failure | 30.6% | **0.0%** |
| All records, detectable | - | 99.3% (172,340 of 173,547) |

By collection year: 2022 99.3%, 2023 99.4%, 2024 99.6%, 2025 99.5%, 2026 99.8%; before 2017
97.9%. The sweep of the reverse primer's 3'-terminal mismatch that the previous run dated
(40.5% likely failure among 2023 collections) no longer shows in any year.[^previous]

Per role, by the best-binding oligo of each record:

- reverse: `infa_rev` 149,195 (86.0%), **`infa_rev2` 23,595 (13.6%)**, each the only working
  reverse primer for those records; 746 without a detectable reverse site, 11 undetermined.
- probe: `infa_probe1` 171,008 (98.5%), `infa_probe2` 2,414 (1.4%); 104 without, 21
  undetermined.
- forward: `infa_fwd` 173,209 (99.8%); 338 without.

1,175 records (0.7%) escape: 1,156 through mismatches, 19 through a gap. They are spread over
258 site combinations, none dominant; the workbook's "Escapes" sheet lists them. 32 are
undetermined.

# Specificity

No predicted off-target product. Background (human): 137 warning primer sites, none facing
another. Exclusivity: 2 critical primer sites, the closest forward and reverse sites both on
**MW220816.1, an influenza A record** that NCBI's taxon restriction let into the exclusivity
search, which holds no influenza A; the
report drew a wrong conclusion from it ("the forward binds this tier perfectly"). Harmless here
(no product), and fixed on 2026-10-23: hits outside a tier's taxa are now set aside by lineage.

The target tier (RID `DEPS5BKC014`, 1.68 million records) gave nothing but one information line;
since 2026-10-23 it is not searched by default (`search.target_tier`).

# Search times

This run is the one held by NCBI's change of 2026-10-20:[^slow-queue] the target search was
READY after 1147 minutes (submitted 2026-10-20), the human background search after **481
minutes** (2026-10-21, against about 60 minutes before), and the exclusivity search, submitted
last that afternoon, after **2 minutes**. NCBI said the change was being rolled back on the day it
answered; this run cannot tell when that happened.

# What it means for the laboratory

The second reverse primer does what the protocol added it for: the terminal-mismatch variant that
made 30.6% of recent records likely failures is now covered, and detection is above 99% in every
collection year since 2017. What remains is small and scattered. As always, this is in silico:
the assessment does not replace experimental validation, and the laboratory verifies the tool
within its own quality system.

[^report]: Report of the 15:42Z run (complete)
[^previous]: "Influenza A (matrix), 2026-10-07 (17:35Z, complete)"
[^slow-queue]: BLAST searches held for a day by a change at NCBI
