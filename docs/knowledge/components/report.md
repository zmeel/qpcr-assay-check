---
type: Component
title: "Report and records"
description: "Self-contained HTML report in three parts (two-page sign-off with figures, evidence, appendix), Excel workbook, results.json and hits.tsv per run."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-11-20T23:00:00Z }
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
    resource: ../../../src/qpcr_assay_check/report/charts.py
    title: "src/qpcr_assay_check/report/charts.py"
  - id: code7
    resource: ../../../src/qpcr_assay_check/report/figures.py
    title: "src/qpcr_assay_check/report/figures.py"
  - id: review
    resource: ../../reviews/2026-11-20-report-advisor.md
    title: Advisor review of the HTML report (2026-11-20)
  - id: merged
    resource: ../decisions/2026-11-20-variants-per-oligo-merged.md
    title: "Variants per oligo merged into the whole-fragment table"
  - id: decision
    resource: ../decisions/2026-11-20-needs-attention-keeps-its-colours.md
    title: "Needs attention keeps its coloured site rows"
  - id: twopages
    resource: ../decisions/2026-11-20-sign-off-two-pages-amplicon-order.md
    title: "Sign-off on two pages: short gap lines, site maps in Part B, oligos in amplicon order"
  - id: condensed
    resource: ../decisions/2026-11-25-findings-condensed.md
    title: "Findings condensed: no repeated list, specificity as a table per tier"
  - id: plain
    resource: ../decisions/2026-11-25-plain-words-amplicon-opposite-primer.md
    title: "Plain words: amplicon, the opposite primer, and gaps that say what is unknown"
  - id: code6
    resource: ../../../src/qpcr_assay_check/results.py
    title: "src/qpcr_assay_check/results.py"
---

# What it does

Each run writes `results.json` (the record), a self-contained HTML report (no scripts, no
external requests, inline SVG), an Excel workbook and `hits.tsv`.

Since 2026-11-20 (advisor's report review, taken up in full)[^review] the report is in three
parts, printable on A4:

- **Part A, sign-off (about two pages):** the status sentence (how many checks exceed a limit,
  need review, lack evidence); one line with the required statements; "What was checked" with a
  small figure per row (Tm per oligo against the primer bands, the status window against the
  limits, coverage steps, each off-target tier's closest primer site as a glyph); target detection
  per year as stacked bars with the status window bracketed; per oligo the totals per class (the
  mismatch maps themselves open Part B); the first "Needs attention" rows, in their coloured
  layout (user decision);[^decision] the findings that need a decision, where specificity gaps
  are one short line per tier and kind;[^twopages] the reviewer's decision box, kept on one page.
- **Part B, evidence:** the findings no section below shows ("Other findings"; the full list is the
  workbook's sheet "Findings");[^condensed] assay; target detection (coverage, copies,
  the mismatch maps per oligo, the whole-fragment tables, in which each site shows its rule and changes and folded rows name
  the site variants no listed row shows; inclusivity per year and by collection year,
  rationale); off-target specificity (one table with a row per tier: products, primer sites by level, probe
  sites, closest primer site, evidence missing with numbered notes, status;[^condensed] products, sites per species, closest
  sites with binding-identical variants merged, organism table with the organisms without a site
  on one line, searches and a score-floor table); oligo design (a matrix: a row per check, a
  column per oligo, the limit once).
- **Part C, appendix:** rules text, queries with incomplete evidence, methods, limits applied,
  settings that differ from the defaults, limitations, required statements in full. The full
  configuration and every query's hits are workbook sheets ("Configuration", "Hits per query").

The report says "amplicon" (not "product") and "check for the opposite primer" (not "partner
scan"); each evidence gap names what stopped, at which setting, and what that leaves unknown.[^plain]

Oligos are listed in their order on the amplicon, forward, probe, reverse (`Assay.amplicon_list`),
in the report and the workbook alike; the searches keep `Assay.oligo_list`.[^twopages]

Tables wrap in print instead of being cut off at the page edge (the print rules come last in the
style sheet). Decisions: the coloured Needs-attention rows[^decision] and the merged variant
tables.[^merged]

Nothing of the record is folded in a closed `<details>` any more (closed sections did not print).
The figures are inline SVG from `report/charts.py` (pure functions of numbers; colour plus texture
per class, so they read in greyscale) fed by `report/figures.py`; every number in a figure is
also in a table of Part B or in the workbook (sheets "Inclusivity", "Mismatch positions"). The
per-oligo tables per year moved to the workbook.

# Code

[`report/html.py`](../../../src/qpcr_assay_check/report/html.py), [`report/templates/report.html.j2`](../../../src/qpcr_assay_check/report/templates/report.html.j2), [`report/summary.py`](../../../src/qpcr_assay_check/report/summary.py), [`report/xlsx.py`](../../../src/qpcr_assay_check/report/xlsx.py), [`report/grouping.py`](../../../src/qpcr_assay_check/report/grouping.py), [`report/charts.py`](../../../src/qpcr_assay_check/report/charts.py), [`report/figures.py`](../../../src/qpcr_assay_check/report/figures.py), [`results.py`](../../../src/qpcr_assay_check/results.py)[^code0][^code1][^code2][^code3][^code4][^code5][^code7][^code6]

[^code0]: src/qpcr_assay_check/report/html.py
[^code1]: src/qpcr_assay_check/report/templates/report.html.j2
[^code2]: src/qpcr_assay_check/report/summary.py
[^code3]: src/qpcr_assay_check/report/xlsx.py
[^code4]: src/qpcr_assay_check/report/grouping.py
[^code5]: src/qpcr_assay_check/report/charts.py
[^code7]: src/qpcr_assay_check/report/figures.py
[^review]: Advisor review of the HTML report (2026-11-20)
[^decision]: "Needs attention keeps its coloured site rows"
[^merged]: "Variants per oligo merged into the whole-fragment table"
[^twopages]: "Sign-off on two pages: short gap lines, site maps in Part B, oligos in amplicon order"
[^condensed]: "Findings condensed: no repeated list, specificity as a table per tier"
[^plain]: "Plain words: amplicon, the opposite primer, and gaps that say what is unknown"
[^code6]: src/qpcr_assay_check/results.py
