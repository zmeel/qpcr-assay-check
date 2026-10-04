---
type: Session
title: "Per-assay exclusivity panels: `assay.yaml` gets its own organism list"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Per-assay exclusivity panels: `assay.yaml` gets its own organism list

The user pushed back on a real design gap: the exclusivity tier's organism list was always
global (`organisms.list_file`/the packaged starter list), the same panel for every assay, when in
reality a respiratory assay and an STI assay do not share the same real near neighbours. Asked for
an exclusivity list in `assay.yaml` itself, with a config option to prefer it (default) or the
global list.

Found the existing architecture already had almost everything needed: `Assay` already carries
per-assay `near_neighbour_taxids`/`exclusion_taxids` (taxid-based, feeding the separate
`near_neighbours` tier), and the exclusivity tier's name-resolution path
(`taxonomy/organisms.py` → `taxonomy/plan.py` → `search/execute.py`) had exactly one call site
each for `load_organism_list`/`resolve_organism_list` -- a small, contained surface to extend
rather than a redesign.

Added `Assay.exclusivity_organisms: list[str]` (organism names, deduplicated/stripped like the
existing taxid list fields) and `organisms.source: "assay" | "global"` to `OrganismsSettings`
(packaged default `assay`). New `taxonomy/organisms.organism_list_source(cfg, assay)` is the one
place that decides which list wins -- `"assay"` only when `organisms.source` is `"assay"` *and*
the assay's own list is non-empty, `"global"` for every other combination (including the
`source: assay` default with an assay that leaves its list empty, so every existing assay without
one keeps working exactly as before). `load_organism_list(cfg, assay=None)` now branches on that
helper, wrapping the assay's own names in a single synthetic `OrganismCategory` so they resolve
and render exactly like the global list. `OrganismListResolution` and `ExclusivityResult` both
carry the resolved `source`, threaded through with no change needed to `pipeline.py` (it already
passes `organism_resolution` straight into `build_exclusivity`). Also improved `--dry-run`'s
exclusivity note: it now names which list and how many organisms will be searched (a local file
read, no network needed) instead of a generic "resolved when the search runs" placeholder.

Report changes: `report.html`'s Exclusivity section states which list a run used, in its own
notice box (distinct wording for "this assay's own list" vs. "the global list", the latter
keeping the existing non-authoritative-starting-point disclaimer); `results.xlsx`'s Summary sheet
gets an "Exclusivity list source" row. The packaged CDC N1 example (`examples/cdc_2019-nCoV_N1.yaml`)
was deliberately left without an `exclusivity_organisms` field, so its already-live-verified
behaviour (documented throughout this file and `docs/ARCHITECTURE.md`) does not silently change --
the fallback-to-global design exists precisely so this is safe.

12 new tests (`tests/test_organisms.py`, `tests/test_assay_model.py`, `tests/test_exclusivity.py`,
two full CLI end-to-end tests in `tests/test_run_full.py` covering both `organisms.source` values
against the constructed NCBI world). 333 tests total (up from 321), `ruff check`/`ruff format
--check` both clean.

Not yet done: no live run has exercised this (this sandbox has no NCBI access) -- the underlying
name-resolution path itself is already live-verified (phase 4a/4b smoke tests), and this change
only adds a second source for the same list of names, but the wiring itself (which list actually
gets searched under each `organisms.source` value) has only been checked against the constructed
test world so far.
