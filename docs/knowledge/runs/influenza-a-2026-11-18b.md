---
type: Run
title: Influenza A (matrix), 2026-11-18 (08:15Z, with the re-alignment fix)
description: "The rerun that confirms the fix: the 141 bp product on ON845595.1 is predicted and read as detected, so exclusivity is Exceeds limit. That record is labelled influenza B but its M-gene fragment is 95% identical to the influenza A reference, so it is most likely mislabelled: the user decides. Detection unchanged: 99.5% of 72,698 records, inclusivity No flags."
tags: [run, influenza]
status: draft
stale_after: 2027-02-18T00:00:00Z
generated: { by: claude-code/agent, at: 2026-11-18T11:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-11-18T08:15:48Z (influenza-a-matrix-gene-20261118T081548Z-f1a4a45b, uploaded in the session of 2026-11-18, not in the repository)
    title: Report of the 08:15Z run
  - id: earlier
    resource: influenza-a-2026-11-18.md
    title: The 07:27Z run, before the fix
  - id: ncbi
    resource: "ESummary and EFetch of ON845595.1 (checked live, 2026-11-18)"
    title: ON845595.1 at NCBI
---

# Run

[Assay](../assays/influenza-a-matrix.md), v2.2.0, code `09deea1ca274`, commit `4b5f4f09bb0c`:
the same inputs hash as the [07:27Z run](influenza-a-2026-11-18.md), rerun on the re-alignment
fix of that morning.[^report][^earlier] **Exceeds limit**, on the exclusivity tier.

# What the fix shows

The reverse site on **ON845595.1** is now re-aligned over its whole length, graded (one mismatch
at -3, tolerated under R1) and paired: **a 141 bp product with `infa_fwd`/`infa_rev` (0 + 1
mismatches), read as detected** because `infa_probe1` has one mismatch there, outside the last 5
nt (tolerated under R9). Under the 2.2.0 severities a product the probe detects is Exceeds limit.
Before the fix the same run predicted no product at all, so the fix did what it was meant to.

Everything else is unchanged: human background 137 warning primer sites and no product;
inclusivity **No flags** (99.5% detectable of 72,698 records collected 2023-2026); all 175,891
records assessed.

# The record is most likely mislabelled (the user decides)

`ON845595.1` is titled "Influenza B virus (B/Argentina/def2/2022) segment 7 matrix protein 2
(M2) and matrix protein 1 (M1) genes, complete cds", 982 nt, taxid 11520, released 2023-07-19,
collected 2022-06-26 (nasal swab, Argentina).[^ncbi] Checked live on 2026-11-18: its best match
to the assay's own 141 nt influenza A reference fragment is **134/141 = 95.0% identical** (7
differences). Influenza A and B matrix genes are far more divergent than that, so the sequence in
this record reads as influenza A under an influenza B name and taxon - a known class of database
error, not evidence that the assay detects influenza B.

The tool is right on its own terms: with this record in the exclusivity tier, the product and the
flag follow. Three further checks the same day (the record's own M1 translation is 99.2%
identical to influenza A M1 and 25.0% to influenza B M1; its M1 is 252 aa, as influenza A's is;
it annotates a spliced M2 rather than influenza B's unspliced BM2) settled it, and the user
reported the record to NCBI on 2026-11-18
([open item](../open/on845595-mislabelled.md)). Nothing was changed in the assay file for it: an
example assay is not quietly tuned to make a flag go away.

[^report]: The user's report of the 08:15Z run (not in the repository)
[^earlier]: The 07:27Z run, before the fix
[^ncbi]: ESummary and EFetch of ON845595.1 (checked live, 2026-11-18)
