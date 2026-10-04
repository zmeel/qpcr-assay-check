---
type: Session
title: "Live smoke test finds and fixes a real exclusivity undercount bug"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Live smoke test finds and fixes a real exclusivity undercount bug

The user uploaded two smoke-test reports this session. The first was the very first-ever run
(v0.2.0, from 2026-09-21) -- already fully captured in this file and `docs/ARCHITECTURE.md` from
back then, so nothing new to record; flagged this back to the user rather than treating it as
fresh evidence, and they confirmed it was uploaded by mistake. The second was a genuinely fresh
run (v0.4.0-4b, 2026-09-23, `NCBI_API_KEY` set for the first time).

That fresh run mostly reconfirmed existing findings, but its step `06` had changed from the
earlier runs' ad-hoc human-background check to an Influenza A virus restriction check (the human
check moved behind `--human`), and that specific substitution surfaced something the
SARS-CoV-2/human-only checks never would have: `ENTREZ_QUERY` taxon restriction for Influenza A is
genuinely effective by actual ancestry (100% of a 300-hit sample within the requested subtree),
but only 89.5% of hit descriptions carry the *exact* species-level taxid itself -- the rest are
filed under distinct, more specific named-strain taxa (children of the species taxid). Read that
as a real bug rather than a smoke-test curiosity: `taxonomy/exclusivity.py` grouped hits into each
organism-list row by exact taxid equality, so any hit filed under a more specific descendant taxid
than an organism-list name resolved to was silently missing from that row -- a real ~10% undercount
for finely-split taxa like influenza. Confirmed the overall exclusivity tier verdict was never
wrong (it sums every hit directly, not grouped by row) -- only the per-organism table undercounted.

Presented the finding and its evidence to the user with three options (fix now, document as a
known limitation, investigate further first); they chose fix now. Implemented:
`taxonomy/exclusivity.py`'s `build_exclusivity` takes a new `taxon_species: dict[int, str]`
(taxid -> species name) and groups sites/amplicons by species when both a hit's and a row's taxid
resolve to one, falling back to exact-taxid matching (the old behaviour) for anything the map
doesn't cover -- never inventing a match that wasn't actually looked up. `cli.py` builds this map
with one `fetch_lineages()` call covering both every off-target hit's taxid and the exclusivity
list's own resolved taxids; since `fetch_lineages` is cache-backed and the taxonomy breakdown
already fetches lineages for the hit taxids, this adds no new NCBI calls in the common case.
Threaded through `pipeline.evaluate()`'s new `taxon_species` parameter (optional, defaults to
`None`/`{}`, fully backward compatible).

5 new unit tests in `tests/test_exclusivity.py`, directly exercising the fixed mechanism
(including the exact Influenza-A-strain scenario, and a test documenting the old broken behaviour
for contrast). Did not extend the constructed test world's taxonomy EFetch fake (it always returns
an empty `TaxaSet`, by design, for every existing test) to also model real lineage data for an
end-to-end CLI check -- that's a larger, riskier change to shared test infrastructure not asked
for, and the fix is already thoroughly covered at the unit level; a full CLI run through the fake
world does confirm the new code path runs cleanly with `taxon_species` degrading to `{}` (no
crash, identical to pre-fix behaviour), just not the species-matching branch itself. 338 tests
total (up from 333), `ruff check`/`ruff format --check` both clean.

Not yet done: this fix has not itself been checked live (would need a real assay whose exclusivity
list includes a finely-split taxon like influenza, run through the actual NCBI-backed pipeline,
not just the smoke test's own diagnostic-only code path).
