---
type: Session
title: "v0.4.0 tagged; phase 4b's ESummary date lookup verified live"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: v0.4.0 tagged; phase 4b's ESummary date lookup verified live

The user ran `scripts/smoke_test.py` again and pasted back a new `smoke_report.json` (all steps
`ok: true`, including the new `08b_esummary_inclusivity_dates`). Also bumped the version to 0.4.0,
closed out the CHANGELOG's Unreleased section into a dated `[0.4.0]` entry, and created an
annotated tag `v0.4.0`. Pushing the branch commit worked; pushing the tag itself hit the same
HTTP 403 from the agent proxy seen in an earlier session for tag pushes (an organisation policy
restriction on tag refs, not transient) -- gave the user the exact commands to recreate and push
the tag from their own machine rather than retrying or routing around it.

Key results from the live run:
- **The renamed organism `Mycoplasmoides pneumoniae` now resolves live.** Organism-list resolution
  went from 38/40 (previous run) to 39/40; only `Mycobacterium chelonae` remains unresolved. This
  confirms the phase-4a fix (renaming "Mycoplasma pneumoniae" directly rather than relying on the
  `[All Names]` synonym fallback, which does not catch this rename) actually works.
- **Inclusivity's ESummary-based date lookup works for the common case.** `Eutils.esummary()`'s
  JSON shape matched a real response (`result.uids` + one object per UID); the nuccore docsum's
  date field is `createdate` (format `"YYYY/MM/DD"`), the first candidate `year_from_docsum()`
  tries; and NCBI does key the result by its own resolved UID, not the input accession (confirmed
  directly -- the response for `id=NC_045512.2,NC_000007.14` came back keyed `"1798174254"`/
  `"568815591"`). `fetch_years()` correctly recovered both years (2020, 2002) despite this.
- **Found and fixed a bug in the smoke-test script itself, not in shipped code.** Step `08b`'s own
  findings computation (`esummary_docsum_keys`, `esummary_reindexed_by_accession_correctly`)
  naively indexed the UID-keyed `esummary()` response by accession directly -- the same mistake the
  production `fetch_years()` code was specifically written to avoid. This silently produced empty
  findings (`{}`) even though `fetch_years_result` itself was correct throughout, since
  `fetch_years()` does its own correct re-indexing internally and never went through the buggy
  path. Fixed the smoke-test step to re-index the same way, and tightened the constructed test
  fakes (`tests/world.py`'s `WorldFake`, `tests/test_smoke_script.py`'s `SmokeFake`) to use a
  synthetic UID that deliberately differs from the accession, so a UID/accession mix-up like this
  would now fail the test suite too, not only surface on a live run. All 295 tests still pass after
  this tightening -- confirming `inclusivity/dates.py` was already correct.
- `blast_date_window_restriction_honoured: false` reconfirmed (BLAST+`[PDAT]` still unreliable, as
  in the previous run) -- expected, not a new finding, just re-verifying the ruled-out design stays
  ruled out.

Updated `docs/ARCHITECTURE.md` (moved phase 4b's ESummary items from "Still unverified" to a new
"Verified" section, updated the top status line to drop "not yet tagged/released"), `CHANGELOG.md`
(closed `[0.4.0]`, updated Known limitations/Fixed), `README.md` (status blurb, third-live-run
paragraph, Limitations bullets, dropped "in progress" from the Exclusivity/Inclusivity section
headers and fixed the now-changed anchor link).
