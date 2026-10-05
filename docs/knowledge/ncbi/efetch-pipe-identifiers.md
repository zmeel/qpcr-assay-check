---
type: NCBI Fact
title: EFetch returns PDB-derived records under a pipe identifier
description: A record listed as 9V29_sa comes back as pdb|9V29|sa, so a FASTA record must be matched by both forms of its identifier.
tags: [ncbi, eutils, efetch]
status: draft
stale_after: 2027-04-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-05T12:00:00Z }
sources:
  - id: live
    resource: live EFetch of 9V29_sa, 9V24_lA and X64142.1 against NCBI nuccore, 2026-10-05
    title: Live check in the session of 2026-10-05
  - id: run
    resource: ../runs/entamoeba-2026-10-05.md
    title: "Entamoeba histolytica, 2026-10-05 10:10Z (first run)"
---

# What was measured

EFetch (`db=nuccore`, `rettype=fasta`) for the accessions `9V29_sa`, `9V24_lA` and `X64142.1`
returns all three sequences, but the first two carry the legacy pipe-delimited identifier in
their FASTA header, not the accession that was asked for:[^live]

| Asked for | Header's first field | Title |
|---|---|---|
| `9V29_sa` | `pdb|9V29|sa` | Chain sa, 17S rRNA |
| `9V24_lA` | `pdb|9V24|lA` | Chain lA, 25S rRNA |
| `X64142.1` | `X64142.1` | E.histolytica gene for small subunit rRNA |

These are nuccore records whose sequence comes from a PDB structure; ESearch and ESummary list
them under the `<entry>_<chain>` accession.

# Why it matters

The variant analysis asks EFetch for a batch of accessions and looks each one up in the parsed
FASTA. Matching on the accession alone missed every PDB-derived record: it counted as "EFetch
returned no sequence" and was retried on the next run, for ever, so the record was never
assessed and the coverage could never become complete. Seen in the first E. histolytica
run:[^run] 45 of 2,345 records, and a second run that processed none of them. Since 2026-10-05
`parse_fasta_records` indexes a record under both forms (`variants/datasets.py`, `fasta_ids`).

[^live]: Live check in the session of 2026-10-05
[^run]: Entamoeba histolytica, 2026-10-05 10:10Z (first run)
