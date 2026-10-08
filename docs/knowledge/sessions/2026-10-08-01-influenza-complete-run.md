---
type: Session
title: "The first complete influenza A run, and what the per-year tables date"
description: "Session log of 2026-10-08."
tags: [session]
session_date: 2026-10-08
session_label: "2026-10-08"
generated: { by: claude-code/agent, at: 2026-10-08T09:00:00Z }
---

# 2026-10-08: the complete influenza A run

- User uploaded the 17:35Z run, the first with every one of the 172,768 records assessed, noting
  that the tool catches the terminal T mismatch in the reverse primer appearing in 2023.
- Confirmed and dated more precisely. By collection year the share of likely failure is 0.2-0.7%
  in every year up to 2021, **6.9% in 2022** and **40.5% in 2023**, then 30.1%, 31.3% and 14.8%.
  By release year the step lands a year later (0.5% -> 20.6% in 2023) because deposition lags
  collection, which is what the collection axis is for. Status Exceeds limit at 69.0% detectable
  of 69,688 records collected 2023-2026, and with coverage complete the hold-back built the day
  before correctly stood aside, so the FAIL is on the whole population.
- Two things checked live, as samples, and one corrects the reading: the variant is **not new**
  (the earliest record carrying that exact reverse site was released 2004-07-08; of 30 records
  released 2004-2010 one carried it, an avian H5N2 chicken strain, and of 30 from 2011-2016
  none). And it is **human-lineage**: of 225 records sampled from 2023, 2024 and 2026, all 17
  carriers had human or unstated strain names and none of the 111 with a non-human host in the
  title carried it - so this is not the avian H5N1 sequencing that fills much of 2023-2024, which
  was my first hypothesis and was wrong.
- Written up as [runs/influenza-a-2026-10-07-complete](../runs/influenza-a-2026-10-07-complete.md).
- User: "Have the code reviewer look at all the new code". The review of `8dce8f3..HEAD` at high
  effort returned 7 findings, all taken up the same day. Four were faults in this session's own
  code: the hold-back's setting released only the FAIL while its comment and the configuration
  claimed a Review too; a **probe channel could still file a crossed limit on partial coverage**,
  because `channel_verdict` knew nothing about coverage and the status is the worst of the
  whole-assay figure and each channel (the Legionella shape; influenza has one channel, which is
  why the runs looked right); the counts line contradicted a deliberately kept Exceeds limit; and
  the degenerate-oligo Tm fix resolved only the oligo, leaving an **ambiguity code in the genome**
  to reach primer3, where one N read as a 13.4 C drop and could trip the "Tm <= annealing" flag
  that the same fix had just unblocked. Three were wrong statements: `grade_probe`'s docstring,
  the deletion note's "1, 3, 4 and 6 nt" against 1, 3, 4, 6, 7 and 8 everywhere else, and
  PfluA2's mismatch put 3 nt from its 3' end where it is at position 21 of 22.
- The hold-back decision now lives in one helper, `variants.exhaustive.hold_back`, used by both
  `fragment_verdict` and `channel_verdict`; two new tests cover the channel case and the genome
  ambiguity code, and the test that encoded the setting's wrong contract was corrected.
- The review also re-derived and confirmed the influenza oligo coordinates, the GT-insertion
  reconstruction of the corrected primer, and the complete run's arithmetic.
- The reviewer was run again on the fixes and found three faults in them, plus a fair criticism
  of one test: a `KeyError` on a gap opposite an ambiguity code; a channel Review raised only by
  a signal outside its target held back although a confirmed signal cannot cross back; and the
  counts line still written before the channels could raise the verdict. The viewer's tier test,
  which I had rewritten as a copy of the viewer's own rule, now checks each tier against the
  YAML on disk instead. All four taken up, with three more regression tests.

# Related

* [Influenza A (matrix), 2026-10-07 (17:35Z, complete)](../runs/influenza-a-2026-10-07-complete.md)
* [Influenza A, matrix gene (two NED probes)](../assays/influenza-a-matrix.md)
* [An inclusivity FAIL on partly assessed records](../open/partial-coverage-and-the-inclusivity-limit.md)
* [Degenerate oligos broke the duplex Tm baseline](../open/degenerate-duplex-baseline.md)
