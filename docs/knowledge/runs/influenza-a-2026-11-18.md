---
type: Run
title: Influenza A (matrix), 2026-11-18 (07:27Z)
description: "The first run on v2.2.0: Review, no limit crossed; 99.5% of 72,698 records collected 2023-2026 detectable, all 175,891 records assessed; no predicted off-target product, but a reverse site on an influenza B record was left unassessed by a filter the graded rules made wrong (fixed the same day; a rerun is needed)."
tags: [run, influenza]
status: draft
stale_after: 2027-02-18T00:00:00Z
generated: { by: claude-code/agent, at: 2026-11-18T10:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-11-18T07:27:13Z (influenza-a-matrix-gene-20261118T072713Z-f1a4a45b, uploaded in the session of 2026-11-18, not in the repository)
    title: Report of the 07:27Z run
  - id: previous
    resource: influenza-a-2026-10-21.md
    title: The run of 2026-10-21 (v2.1.0)
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: Influenza A matrix assay
---

# Run

[Assay](../assays/influenza-a-matrix.md), v2.2.0, code `8c96d8f13b5d`, commit `493ccad110b6`;
both reverse primers.[^report] **Review, no limit crossed**, as in the run of
2026-10-21.[^previous] All 175,891 records NCBI listed that day assessed (region found in
175,748; hidden by N in 114, cut by a record end in 28, not found in 1); coverage No flags.

# Detection

**99.5% detectable of 72,698 records collected 2023-2026**, 100.0% including at risk, 0.0%
likely failure (34 undetermined). Per role, by the best-binding oligo: `infa_rev` 151,006
(85.9%), `infa_rev2` 23,906 (13.6%), each the only working reverse primer for those records;
`infa_probe1` 173,190 (98.5%), `infa_probe2` 2,430 (1.4%); `infa_fwd` 175,402 (99.8%).
Inclusivity **No flags**, the first time for this assay.

New in 2.2.0: 80.0% of the 240 distinct site patterns are detectable, against 99.5% of the
records (a few lineages dominate the database); and **87 records in the window fail through the
reverse primer alone** - in one-step RT-PCR that primer also primes the reverse transcription,
where Stadhouders measured all 24 reverse-primer mismatches under 0.7 Ct, so the laboratory's
mix decides (R4, not encoded). If they all amplified, 99.6% would be detectable.

# Specificity, and a filter the graded rules made wrong

No predicted off-target product. Human background: 137 warning primer sites, none facing
another. Exclusivity: 4 sites on **ON845595.1, an influenza B record** (segment 7, genuinely in
the tier, unlike the influenza A leak of 2026-10-21): the forward primer binds it **perfectly**,
and both probes bind (1 and 2 mismatches). The report's own sentence is right: discrimination
rests on the reverse primer.

Checked here against the record fetched live: the reverse primer `infa_rev` has **one mismatch at
-3** there, which R1 grades **tolerated**, and `infa_rev2` two (3'-terminal, likely failure). A
product of about 141 bp with `infa_rev` is therefore plausible, but none was predicted. The cause
is a filter from before the one-rule-set change: a partial BLAST hit whose best full-length
alignment could only stay "minor" by the mismatch counts was never fetched and re-aligned, so it
never got a class and could not prime. With 3 bases unaligned at the 3' end that is exactly this
site. Fixed on 2026-11-18 (`sites.worth_realigning`): when the classes decide, only the mismatch
bound rules a hit out. **A rerun is needed to see whether the product is predicted**; the
conclusion that detection rests on the reverse primer stands either way, and in the laboratory
influenza B is a separate assay.

[^report]: The user's report of the 07:27Z run (not in the repository)
[^previous]: The run of 2026-10-21 (v2.1.0)
