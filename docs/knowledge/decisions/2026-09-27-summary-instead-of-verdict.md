---
type: Decision
title: "A summary with review statuses instead of an overall verdict"
description: "No pass/fail verdict: a review status (No flags, Review, Exceeds limit, Incomplete) per check, a reviewer's decision box, first run as baseline."
tags: [decision]
status: draft
decided_on: 2026-09-27
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-27-01-summary-instead-of-a-verdict-v1-5-0-released-legionella.md
    title: "Session 2026-09-27: Summary instead of a verdict; v1.5.0 released; Legionella draft"
  - id: spec
    resource: ../../SPEC.md
    title: "docs/SPEC.md (amendments)"
---

# Decision

Replace the overall verdict by "Summary of this year's check": a review status per row (No flags / Review / Exceeds limit / Incomplete) in report, workbook and results.json; internal PASS/WARN/FAIL/INCOMPLETE codes and exit codes kept as flag levels; QC labels within / outside preferred / outside limit; grey "No flags"; a reviewer's decision box.[^progress][^spec]

# Who and why

User: "the tool is not a test that fails or passes"; advisor consulted first.

# What followed

`report/summary.py`; SPEC amended.

[^progress]: Session 2026-09-27: Summary instead of a verdict; v1.5.0 released; Legionella draft
[^spec]: docs/SPEC.md (amendments)
