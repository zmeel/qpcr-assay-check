---
type: Run
title: Entamoeba histolytica, 2026-10-05 12:49Z (complete)
description: Every one of the 2,345 records assessed after the EFetch fix; 86.4% detectable of 81 records; still Exceeds limit from the products in other Entamoeba species.
tags: [run, entamoeba]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-05T13:30:00Z }
sources:
  - id: report
    resource: the user's report of run entamoeba-histolytica-ssu-rrna-20261005T124919Z-55220300 on the NAS, read in the session of 2026-10-05
    title: Report of the run (not in the repository)
  - id: first
    resource: entamoeba-2026-10-05.md
    title: "Entamoeba histolytica, 2026-10-05 10:10Z (first run)"
  - id: efetch
    resource: ../ncbi/efetch-pipe-identifiers.md
    title: EFetch returns PDB-derived records under a pipe identifier
  - id: assay
    resource: ../assays/entamoeba-histolytica-ssu.md
    title: Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)
---

# Run

The [assay](../assays/entamoeba-histolytica-ssu.md)[^assay] with the EFetch fix of the same
day.[^efetch] It is the first run in which every listed record was assessed. Numbers as read from
the report;[^report] they are counts over public records, not prevalence. Status still **Exceeds
limit**, from specificity.

# What the fix changed

| | [10:10Z](entamoeba-2026-10-05.md)[^first] | 12:49Z |
|---|---|---|
| Records assessed | 2,300 of 2,345 | **2,345 of 2,345** |
| Coverage status | Incomplete | **No flags** |
| Records with the region | 73 | 81 |
| Detectable | 62 (84.9%) | 70 (**86.4%**) |
| Escapes | 10 | 10 |
| Undetermined | 1 | 1 |

The 45 records that could not be fetched before are now assessed. Eight of them carry the target
region and all eight are detectable, so the figure rose while the escapes stayed exactly the
same. They are ribosome structure records (17S rRNA chains of PDB entries), which is why their
sites match the reference.

# Unchanged

- **Specificity**: the same 62 predicted products in other Entamoeba species (E. dispar 35,
  E. moshkovskii 24, E. bangladeshi 3), none expected to be detected by the probe; both primers
  perfect on E. dispar and E. bangladeshi. Human background: 6 critical primer sites, no product.
  Near neighbours not searched.
- **Inclusivity status Incomplete**: still 14 records in the 2022-2025 collection window against
  the 100 of `min_genomes_for_verdict`; 44 of 76 records with the region (57.9%) carry no usable
  collection date.
- **The escapes**: 7 records with one probe variant (2 mismatches plus a gap), 2 with 6
  mismatches, 1 with 2; one record undetermined (a single probe mismatch outside the MGB region).
  Both primers stay perfect in all but one record.

The whole fragment over the 81 records: 86.4% detectable, 0% at risk, 12.3% likely failure,
1.2% undetermined.

[^report]: Report of the run (not in the repository)
[^first]: Entamoeba histolytica, 2026-10-05 10:10Z (first run)
[^efetch]: EFetch returns PDB-derived records under a pipe identifier
[^assay]: Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)
