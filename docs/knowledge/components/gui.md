---
type: Component
title: "Browser interface"
description: "FastAPI app for one user - assays with live validation, confirmed runs in a queue, results, settings."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/gui/app.py
    title: "src/qpcr_assay_check/gui/app.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/gui/auth.py
    title: "src/qpcr_assay_check/gui/auth.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/gui/assays.py
    title: "src/qpcr_assay_check/gui/assays.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/gui/form.py
    title: "src/qpcr_assay_check/gui/form.py"
  - id: code4
    resource: ../../../src/qpcr_assay_check/gui/runs.py
    title: "src/qpcr_assay_check/gui/runs.py"
  - id: code5
    resource: ../../../src/qpcr_assay_check/gui/results_routes.py
    title: "src/qpcr_assay_check/gui/results_routes.py"
  - id: code6
    resource: ../../../src/qpcr_assay_check/gui/settings_routes.py
    title: "src/qpcr_assay_check/gui/settings_routes.py"
---

# What it does

One user behind a scrypt password, sessions signed and ended on a password change, strict
CSP; assay files edited with a round-trip YAML form and live validation; runs planned as a
dry run, confirmed by hash and executed one at a time by the command line itself; reports served
in a sandboxed frame; settings and password changes with history. Docker compose on the NAS
(`QAC_UID`, `QAC_GID`, `QAC_PORT`). Released in v2.1.0
([decision](../decisions/2026-10-02-gui-one-user.md)).

# Code

[`gui/app.py`](../../../src/qpcr_assay_check/gui/app.py), [`gui/auth.py`](../../../src/qpcr_assay_check/gui/auth.py), [`gui/assays.py`](../../../src/qpcr_assay_check/gui/assays.py), [`gui/form.py`](../../../src/qpcr_assay_check/gui/form.py), [`gui/runs.py`](../../../src/qpcr_assay_check/gui/runs.py), [`gui/results_routes.py`](../../../src/qpcr_assay_check/gui/results_routes.py), [`gui/settings_routes.py`](../../../src/qpcr_assay_check/gui/settings_routes.py)[^code0][^code1][^code2][^code3][^code4][^code5][^code6]

[^code0]: src/qpcr_assay_check/gui/app.py
[^code1]: src/qpcr_assay_check/gui/auth.py
[^code2]: src/qpcr_assay_check/gui/assays.py
[^code3]: src/qpcr_assay_check/gui/form.py
[^code4]: src/qpcr_assay_check/gui/runs.py
[^code5]: src/qpcr_assay_check/gui/results_routes.py
[^code6]: src/qpcr_assay_check/gui/settings_routes.py
