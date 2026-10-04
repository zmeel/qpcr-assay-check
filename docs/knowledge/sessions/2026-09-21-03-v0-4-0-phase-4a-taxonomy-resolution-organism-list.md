---
type: Session
title: "v0.4.0 phase 4a: taxonomy resolution, organism list, exclusivity"
description: "Session log of 2026-09-21."
tags: [session]
session_date: 2026-09-21
session_label: "2026-09-21"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-21: v0.4.0 phase 4a: taxonomy resolution, organism list, exclusivity

Started v0.4.0 on the user's go-ahead ("start v0.4.0"). Given the real size of the phase (taxonomy,
organism list, inclusivity, exclusivity), split it into two sub-phases rather than attempting all of
it at once: **4a** (this session) covers taxonomy name resolution, the clinical organism list, a
real exclusivity search tier and report, and a species/genus/family rollup of off-target hits.
**4b** (inclusivity) is deliberately deferred: it needs a new time-windowed search scheme whose core
assumption (combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST
search) is explicitly flagged as unverified in `docs/ARCHITECTURE.md`, and deserved its own,
separately-scoped session rather than being rushed alongside 4a.

What this session built, in dependency order:
- `taxonomy/resolve.py` (Entrez Taxonomy name resolution + lineage parsing) and
  `taxonomy/organisms.py` (the organism-list YAML loader) -- reused the exact ESearch/EFetch query
  shapes the v0.2.1 smoke test already validated live (`f"{name}[Scientific Name]"`, then
  `[All Names]` for synonyms), rather than guessing a new format.
- `data/clinical_organisms.yaml`: a starter list, clearly labelled non-authoritative per SPEC.md's
  explicit requirement.
- Wired organism-list resolution into `search/execute.py` (`_resolve_and_plan`) so the exclusivity
  tier's taxids are resolved once and the confirmation preview (`on_plan`) shows the real,
  resolved plan rather than a stale pre-resolution one. Discovered along the way that resolving
  organism names does not need the same "confirm before sending" gate as oligo sequences (it never
  sends anything proprietary), and adjusted the `declining sends nothing` test accordingly (it now
  checks no BLAST submission happened, not "zero network calls").
- `taxonomy/exclusivity.py`: deliberately reuses the existing v0.3.0 specificity assessment for the
  exclusivity tier's sites/amplicons (just another tier in `specificity.off_target_tiers`) instead
  of a parallel implementation, and only adds the per-organism table view SPEC.md step 8 asks for.
- `taxonomy/rollup.py`: species/genus/family aggregation (SPEC step 6), generic across all
  off-target tiers. Made its failure non-fatal after discovering the naive wiring turned any
  taxonomy EFetch hiccup into a full run-ending `NCBI problem` exit code, even though QC and
  specificity had already produced a valid, complete verdict -- a lineage lookup failure now just
  leaves the breakdown empty.
- Wired both into `pipeline.py`, `report.html.j2`, `report/xlsx.py`, and `results.json`.
- Extended `tests/world.py` with controllable organism-name-to-taxid resolution
  (`World.name(...)`) so a real end-to-end CLI test could exercise resolved-with-a-hit,
  resolved-with-no-hit, and unresolved organisms together, not just the "nothing resolves" default.
- Added `scripts/smoke_test.py` steps `03b` (lineage parsing, the real `resolve_name` synonym
  fallback for "Mycoplasma pneumoniae") and `03c` (the actual packaged-organism-list resolution
  path) -- not yet run live.
- 30 new tests, 280 total; `ruff check` and `ruff format --check` both clean throughout.
- Updated README, `docs/ARCHITECTURE.md`, `CHANGELOG.md` (Unreleased, not tagged: this is a
  sub-phase, not a complete v0.4.0). Did not bump `pyproject.toml`'s version.

Left for the user / next session:
- **Run `scripts/smoke_test.py`** (steps `03b`/`03c` are new) and paste back the report. Lineage
  parsing (`Rank`, `LineageEx`) has never been checked against real NCBI output; only the
  `ScientificName`-only regex check from v0.2.1 has been.
- Local commit(s) on `claude/brave-dirac-1vppye`; not pushed. Ask before pushing, per CLAUDE.md.
- Phase 4b (inclusivity) is next, once 4a is validated live and the user is ready.
