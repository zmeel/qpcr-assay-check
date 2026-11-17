---
type: Component
title: "Exhaustive variant analysis and inclusivity"
description: "Grades every genome's copies, decides each genome's outcome and builds the whole-fragment and channel statuses."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/variants/exhaustive.py
    title: "src/qpcr_assay_check/variants/exhaustive.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/variants/partitioned.py
    title: "src/qpcr_assay_check/variants/partitioned.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/variants/models.py
    title: "src/qpcr_assay_check/variants/models.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/inclusivity/models.py
    title: "src/qpcr_assay_check/inclusivity/models.py"
  - id: code4
    resource: ../../../src/qpcr_assay_check/inclusivity/aggregate.py
    title: "src/qpcr_assay_check/inclusivity/aggregate.py"
  - id: code5
    resource: ../../../src/qpcr_assay_check/pipeline.py
    title: "src/qpcr_assay_check/pipeline.py"
---

# What it does

For each genome: the copies from the [genome store](genome-store.md), sites placed through
anchor mapping, graded ([grading](grading.md)), the best copy chosen, the
[genome outcome](../rules/genome-outcome.md) decided once, then per channel. Aggregates per
release and collection year, the [inclusivity status](../rules/inclusivity-status.md), escape
reasons, the cut-genome breakdown, distinct site patterns and the homopolymer alternative.
`partitioned.py` is the source for targets without assemblies (remote BLAST over accession
lists). Only the first locus of a multi-locus assay is analysed ([open](../open/every-locus.md)).

The figures and the coverage check count the stored records NCBI lists in this run (2026-11-17,
code review): a stored record no longer listed (withdrawn, replaced, or outside a narrowed
`variants.nucleotide_query`, which is not part of the store key) is left out and counted in the
report. When the per-run budget cut the listing short, every stored record is counted and the
coverage is never complete. Nucleotide UIDs looked up once are kept beside the store, so a
later run summarises only new records; a record whose fetch failed is not stored and is tried
again, and counts as unavailable after two failed runs.

# Code

[`variants/exhaustive.py`](../../../src/qpcr_assay_check/variants/exhaustive.py), [`variants/partitioned.py`](../../../src/qpcr_assay_check/variants/partitioned.py), [`variants/models.py`](../../../src/qpcr_assay_check/variants/models.py), [`inclusivity/models.py`](../../../src/qpcr_assay_check/inclusivity/models.py), [`inclusivity/aggregate.py`](../../../src/qpcr_assay_check/inclusivity/aggregate.py), [`pipeline.py`](../../../src/qpcr_assay_check/pipeline.py)[^code0][^code1][^code2][^code3][^code4][^code5]

[^code0]: src/qpcr_assay_check/variants/exhaustive.py
[^code1]: src/qpcr_assay_check/variants/partitioned.py
[^code2]: src/qpcr_assay_check/variants/models.py
[^code3]: src/qpcr_assay_check/inclusivity/models.py
[^code4]: src/qpcr_assay_check/inclusivity/aggregate.py
[^code5]: src/qpcr_assay_check/pipeline.py
