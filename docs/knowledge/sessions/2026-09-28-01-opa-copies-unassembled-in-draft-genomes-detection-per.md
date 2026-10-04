---
type: Session
title: "Opa copies unassembled in draft genomes; detection per assembly level"
description: "Session log of 2026-09-28."
tags: [session]
session_date: 2026-09-28
session_label: "2026-09-28"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-28: Opa copies unassembled in draft genomes; detection per assembly level

- The user checked GCF_000156755.1 (N. gonorrhoeae 1291, Broad 2009 draft, 175 contigs in 42
  scaffolds, 78,472 N): no opa genes. Verified live: NCBI annotates 0 opa genes (complete
  reference GCF_013030075.1: 11); for 6 reference opa loci both flanks lie on one draft
  scaffold with 1,000–2,200 N between them (genes left as gaps); no exact NG-F/NG-R/NG-P1 site
  in the draft. Its only assembled copy is the divergent opa copy that the complete reference
  also carries (~1,478,815; forward site GTTGGCACATCGCTCCA): a false escape. That combination
  is the top "Needs attention" row (1,278 genomes, 2.5%).
- Advisor: step 1 (built) shows detection per assembly level in the coverage section and the
  levels on every whole-fragment row (report and workbook), so the next run shows whether the
  1,278 are drafts. Step 2 (not built, only if they are): "undetermined: copies possibly
  unassembled" for multi-copy targets (best copy fails, fewer than half the typical copies of
  complete genomes in the run, draft with gaps or truncated copies, no complete genome with the
  same failing pattern; setting variants.multicopy_unassembled; store gap_nt and n_truncated).
  Genome files were downloaded to the scratchpad for the check and deleted afterwards.
- Live run with step 1: detectable Complete Genome 95.9% (297), Chromosome 100% (32), Scaffold
  87.0% (405), Contig 79.0% (50,806). The likely-failure rows of 1,278, 903 and 505 genomes have
  no complete genome (Contig 1,269 / 902 / 499); the at-risk row of 2,481 has 10 (real).
- Step 2 built on the user's request: `mark_unassembled` (variants/exhaustive.py), setting
  `variants.multicopy_unassembled`. Evidence of an incomplete draft is "more than one sequence
  or a copy cut by a contig end", not N gaps (contig-level assemblies have none), so nothing is
  downloaded again. Not yet seen on a live run.
