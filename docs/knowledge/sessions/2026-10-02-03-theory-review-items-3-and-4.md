---
type: Session
title: "Theory-review items 3 and 4"
description: "Session log of 2026-10-02."
tags: [session]
session_date: 2026-10-02
session_label: "2026-10-02"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-02: Theory-review items 3 and 4

- User: "Start with 3 and 4" (of the deferred review items).
- Item 3, distinct site patterns: `distinct_patterns()` in variants/exhaustive.py groups the
  judged genomes of the status window by their three best-copy sites (role, oligo label,
  aligned genome bases), each pattern counted once; `DistinctPatterns` in
  inclusivity/models.py, `InclusivityResult.distinct`; a rationale line, the summary row's
  result, a paragraph under the whole-fragment table. Information only.
- Item 4, `inclusivity.status_axis: release | collection` (default release). With collection,
  `fragment_verdict` gets the collection-year rows (`status_years()`), undated genomes are
  counted in a "Left out of the status by collection year" line, the release-year figure is
  information; the summary row, the not-located line and the report follow the axis. Channel
  statuses are over all genomes and unchanged.
- User: "Use 25% limit": with `collection`, more than max_undetermined_percent (25%) of the
  genomes with the region (released in the years shown) without a usable collection year gives
  INCOMPLETE. Committed locally after the push; the user first runs Neisseria with the pushed
  code (both axes) before it is pushed.
- tests/test_status_axis.py (6 tests).
- Legionella with the new code and status_axis collection (user, run 2026-10-02T12:22Z, GUI):
  Incomplete, but from the 4,441 cut genomes (48% undetermined in the collection window, 38%
  by release), not from the axis; 313 of 11,174 (2.8%) without a usable collection year.
  Collection 2023-2026 93.9% of 1,669 (2025 87.7%, 2026 90.6%) vs release 97.3% of 4,549;
  3,921 of the genomes released 2017-2026 were collected before 2017. Distinct patterns: 8
  (4 detectable, 3 failing in 100 genomes; the most common one in 1,282 genomes).
- 25% undated limit pushed (user: "Push and make break down"). Breakdown of the cut genomes
  built: `cut_kind()` and `CUT_KINDS` in variants/exhaustive.py, `CutReason` and
  `ExhaustiveCoverage.cut_reasons`, report coverage row, workbook coverage sheet, run_summary.
  No count changes. tests/test_cut_reasons.py.
- Legionella breakdown (user, run 2026-10-02T12:47Z): of 4,441 cut, 4,174 have one or two sites
  cut off with the whole ones detectable (2,632 probe cut off, both primers whole: the contig
  ends fall inside the probe, likely the rRNA-operon repeat), 161 fragment not in the assembly,
  104 a site cut off and a whole one failing, 2 every site whole but not all detectable.
- User decision ("Go with 1 and 2"): keep the cut genomes undetermined (Legionella stays
  Incomplete, with the bracket); count "fragment not in the assembly" as region not found:
  `fragment_not_assembled()` in variants/exhaustive.py before the assessment,
  `ExhaustiveCoverage.not_assembled`, report and workbook rows. Test in test_cut_reasons.py.

# Related

* [Collection year as an optional status axis; 25% undated limit](../decisions/2026-10-02-collection-year-status-axis.md)
* [Cut genomes stay undetermined; a fragment not in the assembly is not found](../decisions/2026-10-02-cut-genomes-and-unassembled-fragments.md)
* [Legionella, 2026-10-02 (12:22Z, 12:47Z, 13:16Z)](../runs/legionella-2026-10-02.md)
