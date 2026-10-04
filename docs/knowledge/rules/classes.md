---
type: Grading Rule
title: Site classes
description: The five classes every primer or probe site on the target gets, and which of them count as detectable.
tags: [grading, classes]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, sections 2 and 7
  - id: grade-py
    resource: ../../../src/qpcr_assay_check/oligo/grade.py
    title: oligo/grade.py
  - id: d-classes
    resource: ../decisions/2026-09-25-graded-classes-without-mix-setting.md
    title: Decision to grade sites without a mix setting
---

# Classes

| Class | Meaning |
|---|---|
| `perfect` | no mismatch, no gap |
| `tolerated` | mismatches expected to cost little |
| `at_risk` | a measurable delay is expected; relevant near the limit of detection |
| `likely_failure` | amplification blocked or strongly delayed in the source data |
| `indeterminate` | no published basis (gaps, ambiguity codes, some probe mismatches) |

**Detectable** = `perfect` or `tolerated`; the inclusivity limits apply to it, and
`at_risk` counts as not detected.[^mismatch-classes] The report shows the class, the rule that
gave it and the source; no Cq value is predicted.

# Undetermined

Two kinds of `indeterminate` site make a genome **undetermined** (neither detected nor an
escape, left out of the percentage): one mismatch in an MGB probe outside its 3'-most 7 nt
([R9](r9-probes.md)) and an ambiguity code in the last 5 nt that decides the class
([R6](r6-ambiguity-codes.md)). Other gaps count as not detected, because an unexplained gap near
a 3' end is often how the aligner writes two mismatches.[^mismatch-classes]

# One basis for every laboratory

No setting for the reaction mix: one column of Stadhouders Table 1 (Taq polymerase on DNA) for
every laboratory, with a fixed caveat in the report.[^d-classes] Code:
`oligo/grade.py`.[^grade-py]

# Rules

[R1](r1-last-five.md), [R2](r2-single-beyond-five.md), [R3](r3-several-mismatches.md),
[R4](r4-reverse-primer-rt.md), [R5](r5-gaps.md), [R5b](r5b-homopolymer-length.md),
[R5c](r5c-probe-deletions.md), [R6](r6-ambiguity-codes.md), [R7](r7-degenerate-primers.md),
[R8](r8-primer-pair.md), [R9](r9-probes.md), [LAB](lab-evidence.md).

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, sections 2 and 7
[^grade-py]: oligo/grade.py
[^d-classes]: Decision to grade sites without a mix setting
