---
type: Component
title: "Chain locator"
description: "Finds every copy of a locus in a genome by chains of exact co-linear blocks, with context flanks."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/variants/chain.py
    title: "src/qpcr_assay_check/variants/chain.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/variants/locate.py
    title: "src/qpcr_assay_check/variants/locate.py"
---

# What it does

Exact 16-base seeds of the reference fragments (every 2nd position, both strands) are
chained co-linearly with signed coordinates; context flanks from the context accession anchor
divergent copies; a 12-base fallback runs where no copy passes. Every candidate is kept with its
evidence and the [copy rule](../rules/copy-rule.md) decides at assessment. Replaced the single
median offset that split or misplaced copies of species whose spacer length differs (overhaul,
2026-09-28/29). About 2.6 s per 4 Mb genome with context.

Both strands are searched, so a record deposited as the reverse complement is found and judged
like any other: [strand and orientation](strand-and-orientation.md).

# Code

[`variants/chain.py`](../../../src/qpcr_assay_check/variants/chain.py), [`variants/locate.py`](../../../src/qpcr_assay_check/variants/locate.py)[^code0][^code1]

[^code0]: src/qpcr_assay_check/variants/chain.py
[^code1]: src/qpcr_assay_check/variants/locate.py
