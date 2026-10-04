---
type: Session
title: "Whole-fragment table width"
description: "Session log of 2026-10-03."
tags: [session]
session_date: 2026-10-03
session_label: "2026-10-03"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-03: Whole-fragment table width

- User: in the Neisseria report of 2026-10-02T21:13Z (latest code) "Needs attention (119
  combinations)" grew too wide. Measured: 1,843 px; each site column ~380 px because the cell
  was nowrap with class, ΔTm, "Tm ≤ annealing" and frequency on one line, which squeezed the
  types column to its minimum and made rows ~230 px tall. Fixed in report.html.j2 (site-tm line,
  wrapping cells, wider types, unbroken dates); previewed on the real report: fits at 1,440 px.
  Test in test_report_condensed.py.
