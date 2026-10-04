---
type: Component
title: "Site grading"
description: "Graded mismatch classes for one oligo site, rule by rule, with the rule and source in the note."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/oligo/grade.py
    title: "src/qpcr_assay_check/oligo/grade.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/specificity/duplex.py
    title: "src/qpcr_assay_check/specificity/duplex.py"
---

# What it does

`grade_primer`, `grade_probe` and the pair rule implement [the rules](../rules/index.md):
R1-R3, R5, R5b, R5c, R6, R8, R9 and LAB. Constants name their sources (`KWOK`, `HUANG`,
`KUTYAVIN`, `OTWELL`, `MGB_REGION = 7`). `specificity/duplex.py` gives the ΔTm/ΔG shown next
to a class (information only; not applicable to MGB/LNA oligos).

# Code

[`oligo/grade.py`](../../../src/qpcr_assay_check/oligo/grade.py), [`specificity/duplex.py`](../../../src/qpcr_assay_check/specificity/duplex.py)[^code0][^code1]

[^code0]: src/qpcr_assay_check/oligo/grade.py
[^code1]: src/qpcr_assay_check/specificity/duplex.py
