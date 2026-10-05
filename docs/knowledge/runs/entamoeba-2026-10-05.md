---
type: Run
title: Entamoeba histolytica, 2026-10-05 10:10Z (first run)
description: Exceeds limit from 62 predicted products in other Entamoeba species; the target itself 84.9% detectable of 73 records, Incomplete for want of recent records.
tags: [run, entamoeba]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-05T11:00:00Z }
sources:
  - id: report
    resource: the user's report of run entamoeba-histolytica-ssu-rrna-20261005T101005Z-55220300 on the NAS, read in the session of 2026-10-05
    title: Report of the run (not in the repository)
  - id: assay
    resource: ../assays/entamoeba-histolytica-ssu.md
    title: Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)
  - id: efetch
    resource: ../ncbi/efetch-pipe-identifiers.md
    title: EFetch returns PDB-derived records under a pipe identifier
  - id: session
    resource: ../sessions/2026-10-05-01-entamoeba-histolytica-assay.md
    title: "Session 2026-10-05: Entamoeba histolytica assay"
---

# Run

The first run of the [assay](../assays/entamoeba-histolytica-ssu.md),[^assay] started from the
browser, tool v2.1.0, inputs hash 5522030…. Numbers as read from the report;[^report] they are
counts over public records, not prevalence. Status **Exceeds limit**, from specificity.

# Other Entamoeba species are amplified

62 predicted off-target products in the exclusivity tier, none of them expected to be detected by
the probe:

| Species | Products | Primer mismatches | Product |
|---|---|---|---|
| E. dispar | 35 | 0 + 0 | 174-175 bp (e.g. AB282661.1) |
| E. moshkovskii | 24 | 3 | 172-175 bp (e.g. MN535795.1) |
| E. bangladeshi | 3 | 0 + 0 | 174 bp (e.g. KR025411.1) |

Both primers match E. dispar and E. bangladeshi perfectly (22 and 20 clean 3' bases), so the
specificity of this assay rests on the probe alone. The closest E. dispar probe sites carry 2-3
mismatches, which [R9](../rules/r9-probes.md) grades likely failure for an MGB probe; that
judgement is expert, not measured ([open item](../open/suss-2009.md) and the theory reviews rank
the probe rules weakest). A wet-lab check against E. dispar and E. moshkovskii DNA is the way to
settle it. E. coli, E. hartmanni, E. polecki and E. gingivalis gave no predicted product.

# Human background: no product

6 critical and 66 warning primer sites in human records, but none facing each other, so nothing
is amplified (Review, not Exceeds limit). Near neighbours were not searched in this run.

# The target itself

- 2,300 of 2,345 listed records assessed; **45 left, so run again**. Region found in 73,
  not found in 2,154 (mostly other genes or short partial records), cut by a record end in 43,
  related regions only in 30.
- Of the 73 records with all three sites: **84.9% detectable** (62), 0% at risk, 13.7% likely
  failure, 1.4% undetermined. Both primers are perfect in 72 of 73 records; every escape is a
  probe variant.
- Escapes: 7 records share one probe variant (2 mismatches plus a gap, e.g. AB426549.1), 2 carry
  6 mismatches (AB845672.1, AB845673.1), 1 carries 2 (AB197936.1). One record (PP275726.1) has a
  single probe mismatch outside the MGB region: undetermined, by
  [R9](../rules/r9-probes.md).
- Status **Incomplete**: only 14 records have a collection year in the 2022-2025 window, far
  below the 100 of `min_genomes_for_verdict`. With so few sequences for this organism that will
  not change; the percentage above is what the data allow.
- 36 of 68 records with the region (52.9%) have no usable collection date.

# The 45 records that were left

A second run the same day (10:26Z) processed none of them: all 45 are PDB-derived records that
EFetch returns under a pipe identifier, which the tool did not match to their accession, so they
were retried for ever ([NCBI fact](../ncbi/efetch-pipe-identifiers.md), fixed 2026-10-05). The
run of [12:49Z](entamoeba-2026-10-05-complete.md) assessed them and completed the coverage: 81
records with the region, 86.4% detectable, the same escapes.

# Worth knowing

69 long records had no BLAST hit and were not scanned directly, so their "not found" rests on
BLAST alone.[^report] The run confirms the variant source chosen in the
[session](../sessions/2026-10-05-01-entamoeba-histolytica-assay.md) works: the filter's records
carry the region where it exists.[^session]

[^report]: Report of the run (not in the repository)
[^assay]: Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)
[^session]: "Session 2026-10-05: Entamoeba histolytica assay"
