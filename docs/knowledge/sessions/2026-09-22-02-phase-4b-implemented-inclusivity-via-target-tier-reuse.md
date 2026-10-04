---
type: Session
title: "Phase 4b implemented: inclusivity via target-tier reuse + ESummary date-bucketing"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: Phase 4b implemented: inclusivity via target-tier reuse + ESummary date-bucketing

Built inclusivity (SPEC.md step 9) on the redesign forced by the previous session's live finding
(BLAST cannot reliably combine `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter):
instead of a separate, date-windowed BLAST search, inclusivity reuses the "target" tier search
every run already makes, and buckets its own hits into years afterwards via a new `esummary()`
E-utility client method plus `inclusivity/dates.py` (which re-indexes ESummary's UID-keyed JSON
response by each docsum's own `accessionversion`/`caption` field, not by input order). Per year:
sample deterministically (evenly spread, one per accession, capped by `sample_per_window`),
re-align over the full oligo length (`inclusivity/sites.py`, reusing `specificity/sites.py`'s
candidate/window machinery), and aggregate perfect/1-mismatch/2+-mismatch/3'-mismatch counts plus
a per-position mismatch profile (`inclusivity/aggregate.py`). Population size per year comes from
an independent ESearch count, reported next to (never instead of) the sample size. Wired through
`pipeline.py` (new `inclusivity` field on `RunResult`, its own `SectionResult`, rationale lines),
`cli.py` (`keep_tiers` now always includes `"target"`; `compute_inclusivity()` call wrapped in
`try/except NcbiError` so a date-lookup failure degrades gracefully rather than discarding an
otherwise-complete run, matching the `taxonomy_breakdown` fix from phase 4a), the HTML report
(new per-oligo, per-year table) and the xlsx writer (new Inclusivity sheet). 295 tests pass
(`pytest -m "not live"`), `ruff check .` clean.

**Honesty points carried through deliberately**: inclusivity's sample is not a controlled random
sample (it depends on where each year's records fall in BLAST's own hit-list ranking, which is
capped) — stated explicitly in `InclusivityResult.limitations` on every result, not just in docs.
A year with zero sampled hits is reported as zero, not omitted. No target-tier search at all (or
no assay target taxid) gives INCOMPLETE, never a false PASS.

**Still unverified, flagged for the next live smoke test** (`scripts/smoke_test.py` step
`08b_esummary_inclusivity_dates`, added but not yet run): the real nuccore ESummary docsum date
field name (the code tries several candidates from memory of the docs, not an observed response),
and whether the accession re-indexing logic holds for more than one accession in a real response
(only checked against the constructed test world so far). Do not treat inclusivity's date
attribution as confirmed until that step comes back `ok: true` with a sane `esummary_docsum_keys`.
