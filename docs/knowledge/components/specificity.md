---
type: Component
title: "Specificity search and assessment"
description: "Plans remote BLAST tiers, re-aligns hits over the whole oligo, pairs products, scans for partners and rolls up by taxon."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/search/planner.py
    title: "src/qpcr_assay_check/search/planner.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/search/execute.py
    title: "src/qpcr_assay_check/search/execute.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/search/orchestrate.py
    title: "src/qpcr_assay_check/search/orchestrate.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/specificity/assess.py
    title: "src/qpcr_assay_check/specificity/assess.py"
  - id: code4
    resource: ../../../src/qpcr_assay_check/specificity/sites.py
    title: "src/qpcr_assay_check/specificity/sites.py"
  - id: code5
    resource: ../../../src/qpcr_assay_check/specificity/pairing.py
    title: "src/qpcr_assay_check/specificity/pairing.py"
  - id: code6
    resource: ../../../src/qpcr_assay_check/specificity/scan.py
    title: "src/qpcr_assay_check/specificity/scan.py"
  - id: code7
    resource: ../../../src/qpcr_assay_check/specificity/reach.py
    title: "src/qpcr_assay_check/specificity/reach.py"
  - id: code8
    resource: ../../../src/qpcr_assay_check/specificity/findings.py
    title: "src/qpcr_assay_check/specificity/findings.py"
  - id: code9
    resource: ../../../src/qpcr_assay_check/taxonomy/resolve.py
    title: "src/qpcr_assay_check/taxonomy/resolve.py"
  - id: code10
    resource: ../../../src/qpcr_assay_check/taxonomy/exclusivity.py
    title: "src/qpcr_assay_check/taxonomy/exclusivity.py"
  - id: code11
    resource: ../../../src/qpcr_assay_check/align/realign.py
    title: "src/qpcr_assay_check/align/realign.py"
---

# What it does

Tiers: target, near neighbours, background (human by default), exclusivity organisms and
out-of-scope taxa, each a taxon-restricted remote BLAST. Hits are re-aligned semi-globally over
the whole oligo, classified ([specificity findings](../rules/specificity-findings.md)) and
paired into products; the partner scan fetches the window next to an unpaired primer site and
aligns the partner primers and the probe; `reach.py` computes what each search could have
reported ([BLAST facts](../ncbi/blast-url-api.md)). Taxonomy resolves names to IDs, lineages
and the exclusivity table.

# Code

[`search/planner.py`](../../../src/qpcr_assay_check/search/planner.py), [`search/execute.py`](../../../src/qpcr_assay_check/search/execute.py), [`search/orchestrate.py`](../../../src/qpcr_assay_check/search/orchestrate.py), [`specificity/assess.py`](../../../src/qpcr_assay_check/specificity/assess.py), [`specificity/sites.py`](../../../src/qpcr_assay_check/specificity/sites.py), [`specificity/pairing.py`](../../../src/qpcr_assay_check/specificity/pairing.py), [`specificity/scan.py`](../../../src/qpcr_assay_check/specificity/scan.py), [`specificity/reach.py`](../../../src/qpcr_assay_check/specificity/reach.py), [`specificity/findings.py`](../../../src/qpcr_assay_check/specificity/findings.py), [`taxonomy/resolve.py`](../../../src/qpcr_assay_check/taxonomy/resolve.py), [`taxonomy/exclusivity.py`](../../../src/qpcr_assay_check/taxonomy/exclusivity.py), [`align/realign.py`](../../../src/qpcr_assay_check/align/realign.py)[^code0][^code1][^code2][^code3][^code4][^code5][^code6][^code7][^code8][^code9][^code10][^code11]

[^code0]: src/qpcr_assay_check/search/planner.py
[^code1]: src/qpcr_assay_check/search/execute.py
[^code2]: src/qpcr_assay_check/search/orchestrate.py
[^code3]: src/qpcr_assay_check/specificity/assess.py
[^code4]: src/qpcr_assay_check/specificity/sites.py
[^code5]: src/qpcr_assay_check/specificity/pairing.py
[^code6]: src/qpcr_assay_check/specificity/scan.py
[^code7]: src/qpcr_assay_check/specificity/reach.py
[^code8]: src/qpcr_assay_check/specificity/findings.py
[^code9]: src/qpcr_assay_check/taxonomy/resolve.py
[^code10]: src/qpcr_assay_check/taxonomy/exclusivity.py
[^code11]: src/qpcr_assay_check/align/realign.py
