---
type: Component
title: "Genome store"
description: "Store v2 - every candidate copy of one locus per genome, incremental, with a schema/key header."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/variants/genomestore.py
    title: "src/qpcr_assay_check/variants/genomestore.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/variants/datasets.py
    title: "src/qpcr_assay_check/variants/datasets.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/variants/store.py
    title: "src/qpcr_assay_check/variants/store.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/variants/collection.py
    title: "src/qpcr_assay_check/variants/collection.py"
---

# What it does

Genome assemblies are listed and downloaded from NCBI Datasets
([facts](../ncbi/datasets-v2.md)), scanned and discarded; only the region plus flanks is kept,
per (assay, locus). The header carries the schema and a key of the locus definition and method;
a mismatch sets the store aside (renamed `.old`) and forces a rescan, so a store is never opened
with a mismatched key. Later runs only process new assemblies. Release and collection dates sit
beside the store (`<store>.dates.json`). Sequence roles (chromosome, plasmid) are fetched only
for assemblies with more than one sequence.

# Code

[`variants/genomestore.py`](../../../src/qpcr_assay_check/variants/genomestore.py), [`variants/datasets.py`](../../../src/qpcr_assay_check/variants/datasets.py), [`variants/store.py`](../../../src/qpcr_assay_check/variants/store.py), [`variants/collection.py`](../../../src/qpcr_assay_check/variants/collection.py)[^code0][^code1][^code2][^code3]

[^code0]: src/qpcr_assay_check/variants/genomestore.py
[^code1]: src/qpcr_assay_check/variants/datasets.py
[^code2]: src/qpcr_assay_check/variants/store.py
[^code3]: src/qpcr_assay_check/variants/collection.py
