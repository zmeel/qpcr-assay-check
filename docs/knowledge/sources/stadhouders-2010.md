---
type: Reference
title: "Stadhouders et al. 2010 (J Mol Diagn)"
description: "Single primer-template mismatches in the last 5 nt by type, position and PCR setup; Table 1 is the R1 lookup."
resource: https://doi.org/10.2353/jmoldx.2010.090035
tags: [paper, primer-mismatch]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: paper
    resource: https://doi.org/10.2353/jmoldx.2010.090035
    title: "Stadhouders et al. 2010 (J Mol Diagn)"
  - id: pubmed
    resource: https://pubmed.ncbi.nlm.nih.gov/19948821/
    title: PubMed record
---

# Citation

Stadhouders R, Pas SD, Anber J, Voermans J, Mes THM, Schutten M. The effect of primer-template mismatches on the detection and quantification of nucleic acids using the 5' nuclease assay. J Mol Diagn 2010;12(1):109-117.[^paper]

DOI [10.2353/jmoldx.2010.090035](https://doi.org/10.2353/jmoldx.2010.090035); PubMed 19948821.[^pubmed]

# What was checked

Full text supplied by the user (2026-09-25), read by the advisor subagent; the PDF is not stored in the repository (copyright). Whether `oligo/grade.py` encodes Table 1 exactly is still unchecked.

# Used for

[R1](../rules/r1-last-five.md), [R3](../rules/r3-several-mismatches.md), [R4](../rules/r4-reverse-primer-rt.md).

# What we take from it

- Positions 1, 2, 3 and 5 from the 3' end were mutated, not 4 (p. 110).
- Table 1 (p. 116): 'acceptable' (generally < 2.0 Ct) or 'avoid' per type group x position x setup (Taq on DNA; Taq + MMLV one-step; rTth one-step).
- Terminal G1 8.29-9.09 Ct, G2 3.77-4.75 Ct, G3 0.99-1.91 Ct with Taq on DNA (pp. 111-113).
- Several mismatches in the last 3 nt including the terminal one: no amplification with the Taq setups (pp. 113-114).
- Taq + MMLV: all 24 reverse-primer mismatches < 0.7 Ct (p. 113).

[^paper]: Stadhouders et al. 2010 (J Mol Diagn)
[^pubmed]: PubMed record
