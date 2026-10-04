---
type: Reference
title: "Otwell et al. 2025 (Front Cell Infect Microbiol)"
description: "Wet-lab Ct shifts for 132 mismatched DNA templates of 16 SARS-CoV-2 assays; the calibration set for R3b, R5c and section 11."
resource: https://doi.org/10.3389/fcimb.2025.1524025
tags: [paper, wet-lab, calibration]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: paper
    resource: https://doi.org/10.3389/fcimb.2025.1524025
    title: "Otwell et al. 2025 (Front Cell Infect Microbiol)"
  - id: pubmed
    resource: https://pubmed.ncbi.nlm.nih.gov/41245249/
    title: PubMed record
---

# Citation

Otwell T, Knight B, Coryell M, Stone J, Davis P, Necciai B, Carlson P, Sozhamannan S. Reality check: testing the in silico predictions of false negative results due to mutations in SARS-CoV-2 PCR assays using templates with mismatches in vitro. Front Cell Infect Microbiol 2025;15:1524025 (CC BY 4.0).[^paper]

DOI [10.3389/fcimb.2025.1524025](https://doi.org/10.3389/fcimb.2025.1524025); PubMed 41245249.[^pubmed]

# What was checked

Article and supplementary Tables 1-2 supplied by the user (2026-09-30); every DNA template graded with oligo/grade.py and compared with its measured Ct (MISMATCH_CLASSES section 11). A calibration set, not a validation: the rules were changed after seeing it.

# Used for

[R3](../rules/r3-several-mismatches.md), [R5c](../rules/r5c-probe-deletions.md).

# What we take from it

- 16 assays, synthetic DNA templates at 50-50,000 copies, permissive conditions (TaqPath 1-Step, annealing 55 C, 50 cycles).
- After the 2026-09-30 changes: detectable 35, likely failure 9 (all >= +3 Ct or undetected), at risk 88.

[^paper]: Otwell et al. 2025 (Front Cell Infect Microbiol)
[^pubmed]: PubMed record
