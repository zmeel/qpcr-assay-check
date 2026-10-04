---
type: Component
title: "Command line"
description: "The commands validate, run, init, search and gui (set-password, serve); exit codes are flag levels."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/cli.py
    title: "src/qpcr_assay_check/cli.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/verdict.py
    title: "src/qpcr_assay_check/verdict.py"
---

# What it does

`qpcr-assay-check validate` checks an assay file; `run` evaluates an assay (QC, specificity
searches, variant analysis, report) and files the record; `init` writes a template; `search`
runs or resumes the remote searches; `gui set-password` and `gui serve` start the
[browser interface](gui.md). Exit codes (0/10/20/30, 64/70) are flag levels, not pass/fail
([summary decision](../decisions/2026-09-27-summary-instead-of-verdict.md)). In Docker,
`scripts/run_assay.sh` runs a full assay in the background ([scripts](scripts.md)).

# Code

[`cli.py`](../../../src/qpcr_assay_check/cli.py), [`verdict.py`](../../../src/qpcr_assay_check/verdict.py)[^code0][^code1]

[^code0]: src/qpcr_assay_check/cli.py
[^code1]: src/qpcr_assay_check/verdict.py
