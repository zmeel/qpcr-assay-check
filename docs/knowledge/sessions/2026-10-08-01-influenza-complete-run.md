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

# Related

* [Influenza A (matrix), 2026-10-07 (17:35Z, complete)](../runs/influenza-a-2026-10-07-complete.md)
* [Influenza A, matrix gene (two NED probes)](../assays/influenza-a-matrix.md)
