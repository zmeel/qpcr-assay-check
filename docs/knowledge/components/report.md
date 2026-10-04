---
type: Component
title: "Report and records"
description: "Self-contained HTML report, Excel workbook, results.json and hits.tsv per run."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/report/html.py
    title: "src/qpcr_assay_check/report/html.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/report/templates/report.html.j2
    title: "src/qpcr_assay_check/report/templates/report.html.j2"
  - id: code2
    resource: ../../../src/qpcr_assay_check/report/summary.py
    title: "src/qpcr_assay_check/report/summary.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/report/xlsx.py
    title: "src/qpcr_assay_check/report/xlsx.py"
  - id: code4
    resource: ../../../src/qpcr_assay_check/report/grouping.py
    title: "src/qpcr_assay_check/report/grouping.py"
  - id: code5
    resource: ../../../src/qpcr_assay_check/report/plots.py
    title: "src/qpcr_assay_check/report/plots.py"
  - id: code6
    resource: ../../../src/qpcr_assay_check/results.py
    title: "src/qpcr_assay_check/results.py"
---

# What it does

Each run writes `results.json` (the record), a self-contained HTML report (no scripts, no
external requests, inline SVG), an Excel workbook and `hits.tsv`. The report opens with the
summary (one row per check, review status) and states that in silico analysis does not replace
experimental validation and that the laboratory verifies the software within its own quality
system. The whole-fragment table ("Needs attention") is what the tool is for.

# Code

[`report/html.py`](../../../src/qpcr_assay_check/report/html.py), [`report/templates/report.html.j2`](../../../src/qpcr_assay_check/report/templates/report.html.j2), [`report/summary.py`](../../../src/qpcr_assay_check/report/summary.py), [`report/xlsx.py`](../../../src/qpcr_assay_check/report/xlsx.py), [`report/grouping.py`](../../../src/qpcr_assay_check/report/grouping.py), [`report/plots.py`](../../../src/qpcr_assay_check/report/plots.py), [`results.py`](../../../src/qpcr_assay_check/results.py)[^code0][^code1][^code2][^code3][^code4][^code5][^code6]

[^code0]: src/qpcr_assay_check/report/html.py
[^code1]: src/qpcr_assay_check/report/templates/report.html.j2
[^code2]: src/qpcr_assay_check/report/summary.py
[^code3]: src/qpcr_assay_check/report/xlsx.py
[^code4]: src/qpcr_assay_check/report/grouping.py
[^code5]: src/qpcr_assay_check/report/plots.py
[^code6]: src/qpcr_assay_check/results.py
