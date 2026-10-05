---
type: Session
title: "Entamoeba histolytica assay"
description: "Session log of 2026-10-05."
tags: [session]
session_date: 2026-10-05
session_label: "2026-10-05"
generated: { by: claude-code/agent, at: 2026-10-05T08:30:00Z }
---

# 2026-10-05: Entamoeba histolytica assay

- The user marked eight decisions in the bundle on main as verified (status stable, `verified` by
  human:zmeel); merged into the working branch. PR #74 (viewer) still open.
- User supplied an E. histolytica assay: forward, reverse, FAM-MGB probe, a 173-nt fragment and
  six exclusivity organisms. Written as `docs/examples/entamoeba_histolytica_ssu.yaml` with
  placeholder names Eh-F, Eh-R, Eh-P.
- Checked: oligo positions in the fragment (F 1-22, P 44-65 same strand, R site 154-173, each
  exactly once); NCBI Taxonomy for the target and the six names (all species; E. moshkovskii
  41668 also resolves, not added: not in the user's list); the fragment lies in the SSU rRNA
  gene, on the strand opposite the rRNA, exactly in 23 of 35 full-length SSU records, among them
  X64142.1 (reverse complement at 88-260), used as target.accession.
- Variant source chosen (to confirm by the user): only 13 current assemblies, so Nucleotide
  records (`blast_partitioned`) with the filter
  `ribosomal OR rRNA OR 18S OR SSU OR "small subunit" OR 16S-like` (2,345 records; the narrower
  18S/SSU filter, 626 records, missed AP023147.1, the rDNA episome, and PDB "17S rRNA" chains),
  `blast_max_records_per_run` 2500 to cover them in one run.
- `validate`: OK. QC-only run: Review (MGB probe Tm below the primers in the model, probe G>C by
  one, amplicon 173 bp and GC 34.1% outside preferred). Test in tests/test_examples.py.

# Related

* [Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)](../assays/entamoeba-histolytica-ssu.md)
