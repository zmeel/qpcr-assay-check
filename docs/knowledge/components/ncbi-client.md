---
type: Component
title: "NCBI client"
description: "BLAST URL API and E-utilities with throttling, backoff, caching and resumable jobs."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/ncbi/http.py
    title: "src/qpcr_assay_check/ncbi/http.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/ncbi/blast.py
    title: "src/qpcr_assay_check/ncbi/blast.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/ncbi/runner.py
    title: "src/qpcr_assay_check/ncbi/runner.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/ncbi/jobs.py
    title: "src/qpcr_assay_check/ncbi/jobs.py"
  - id: code4
    resource: ../../../src/qpcr_assay_check/ncbi/cache.py
    title: "src/qpcr_assay_check/ncbi/cache.py"
  - id: code5
    resource: ../../../src/qpcr_assay_check/ncbi/eutils.py
    title: "src/qpcr_assay_check/ncbi/eutils.py"
  - id: code6
    resource: ../../../src/qpcr_assay_check/ncbi/parser.py
    title: "src/qpcr_assay_check/ncbi/parser.py"
  - id: code7
    resource: ../../../src/qpcr_assay_check/ncbi/settings.py
    title: "src/qpcr_assay_check/ncbi/settings.py"
---

# What it does

Every request identifies itself (`tool`, `email`), keeps NCBI's intervals and retries with
exponential backoff ([etiquette](../ncbi/etiquette.md)). A search is a resumable state machine
(submit -> poll -> fetch -> cache); an interrupted run resumes instead of starting over, and a
search waiting too long is resubmitted once. `ncbi/settings.py` reads `NCBI_EMAIL` and
`NCBI_API_KEY` from the environment only.

# Code

[`ncbi/http.py`](../../../src/qpcr_assay_check/ncbi/http.py), [`ncbi/blast.py`](../../../src/qpcr_assay_check/ncbi/blast.py), [`ncbi/runner.py`](../../../src/qpcr_assay_check/ncbi/runner.py), [`ncbi/jobs.py`](../../../src/qpcr_assay_check/ncbi/jobs.py), [`ncbi/cache.py`](../../../src/qpcr_assay_check/ncbi/cache.py), [`ncbi/eutils.py`](../../../src/qpcr_assay_check/ncbi/eutils.py), [`ncbi/parser.py`](../../../src/qpcr_assay_check/ncbi/parser.py), [`ncbi/settings.py`](../../../src/qpcr_assay_check/ncbi/settings.py)[^code0][^code1][^code2][^code3][^code4][^code5][^code6][^code7]

[^code0]: src/qpcr_assay_check/ncbi/http.py
[^code1]: src/qpcr_assay_check/ncbi/blast.py
[^code2]: src/qpcr_assay_check/ncbi/runner.py
[^code3]: src/qpcr_assay_check/ncbi/jobs.py
[^code4]: src/qpcr_assay_check/ncbi/cache.py
[^code5]: src/qpcr_assay_check/ncbi/eutils.py
[^code6]: src/qpcr_assay_check/ncbi/parser.py
[^code7]: src/qpcr_assay_check/ncbi/settings.py
