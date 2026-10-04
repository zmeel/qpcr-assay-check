---
type: Reference
title: "Lefever et al. 2013 (Clin Chem)"
description: "Mismatch position beyond the last 5 nt, counts per primer and per pair; basis of R2, R3 and R8."
resource: https://doi.org/10.1373/clinchem.2013.203653
tags: [paper, primer-mismatch]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: paper
    resource: https://doi.org/10.1373/clinchem.2013.203653
    title: "Lefever et al. 2013 (Clin Chem)"
  - id: pubmed
    resource: https://pubmed.ncbi.nlm.nih.gov/24014836/
    title: PubMed record
---

# Citation

Lefever S, Pattyn F, Hellemans J, Vandesompele J. Single-nucleotide polymorphisms and other mismatches reduce performance of quantitative PCR assays. Clin Chem 2013;59(10):1470-1480.[^paper]

DOI [10.1373/clinchem.2013.203653](https://doi.org/10.1373/clinchem.2013.203653); PubMed 24014836.[^pubmed]

# What was checked

Full text supplied by the user (2026-09-25), read by the advisor subagent. Supplementary Fig. 7 not checked.

# Used for

[R2](../rules/r2-single-beyond-five.md), [R3](../rules/r3-several-mismatches.md), [R8](../rules/r8-primer-pair.md).

# What we take from it

- 20-nt forward primers, the 3'-most 16 nt tested, five intercalating-dye mixes, DNA only (p. 1472).
- Terminal mismatch 5-7 dCq depending on the mix; 'almost negligible for position 8 and higher' (p. 1477).
- Terminal plus another in the last 5: 7.93-12.15 dCq (p. 1472).
- 4 in one primer, or 3 + 2 or 4 + 1 across the pair: blocked 'almost completely' (pp. 1476-1478).
- Input independence lost at low copy numbers with 2-3 mismatches (p. 1478).

[^paper]: Lefever et al. 2013 (Clin Chem)
[^pubmed]: PubMed record
