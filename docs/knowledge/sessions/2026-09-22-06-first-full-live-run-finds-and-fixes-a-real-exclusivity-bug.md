---
type: Session
title: "First full live run finds and fixes a real exclusivity bug"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: First full live run finds and fixes a real exclusivity bug

The user ran a full `run` through the Docker image against real NCBI data (CDC N1 example,
packaged organism list, background tier included) and shared `report.html`. Overall verdict was
`FAIL` — and reading through the rationale found a genuine bug, not a config problem: the packaged
clinical organism list includes "Severe acute respiratory syndrome coronavirus 2" (reasonable for
a respiratory panel), which is also the CDC N1 example's own intended target
(`taxid 2697049`). The exclusivity tier had no exclusion for the assay's own target taxid, so it
searched for and found the assay's own perfect match against itself, and reported every one of
those matches as a critical off-target site or predicted product: 4025 critical primer sites, 2000
critical probe sites, 343 "likely detected" products, all at 0 mismatches (`+0.0 °C vs perfect`)
against records titled "Severe acute respiratory syndrome coronavirus 2" — not a specificity
problem at all, just the assay correctly finding its own target, mislabelled as evidence of
cross-reactivity. This alone flipped the overall verdict from what should have been closer to a
real (background-tier) `WARN` into a misleading `FAIL`.

Confirmed by checking `data/clinical_organisms.yaml` (line 56: SARS-CoV-2 is indeed in the list)
and the report's own search-taxids table (`2697049` present among the exclusivity tier's searched
taxids), then reading `specificity/assess.py` to confirm a secondary, smaller puzzle along the
way: why the "assessed" count (2837) exceeded the documented `max_sites_per_query` default (2000)
— confirmed the cap is applied per search chunk (each BLAST submission), not once per
tier-aggregate query, so two exclusivity chunk-searches (the ~39-organism list split by
`max_taxids_per_search`) can each independently cap near 2000, explaining the observed number
exactly. Not a bug, just a code-reading exercise before writing it into the docs as fact rather
than a guess.

Fixed: `search/execute.py` now filters `assay.target.taxid` out of the exclusivity tier's resolved
taxids before they reach the search planner. Kept the organism-list row visible per the project's
own "never present a sample as the full population" rule (never silently drop an entry) — added
`ExclusivityRow.is_target`, wired through `pipeline.py`, `report/templates/report.html.j2`, and
`report/xlsx.py` so the row reads "assay's own intended target — excluded from this search" rather
than a confusingly-identical "0 sites, resolved" that would look the same as a genuinely-clean
result. Added regression tests reproducing the exact live-run scenario: a unit test in
`tests/test_exclusivity.py` (`build_exclusivity()` with `target_taxid` set, including a
defence-in-depth check that evidence for that taxid is never counted even if somehow present), and
a full CLI end-to-end test in `tests/test_run_full.py` using the constructed world with the
target's own taxid also listed in the organism list — confirms no exclusivity-tier site or
amplicon exists for the target's taxid after the fix. 311 tests total (up from 308), ruff clean.

Not yet done: a fresh full live run with the fix applied, to confirm the corrected verdict looks
right end to end (only checked against the constructed test world and live-run evidence from
*before* the fix so far).
