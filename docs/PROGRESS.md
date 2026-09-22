# Progress log

Read this alongside `docs/SPEC.md` (authoritative spec) and `docs/ARCHITECTURE.md` (design and
verified NCBI facts) at the start of every session. Newest entry first.

## 2026-09-22 — Phase 4a verified live; inclusivity's planned design ruled out

The user ran `scripts/smoke_test.py` and pasted back `smoke_report.json` (all steps `ok: true`).
Updated README.md, `docs/ARCHITECTURE.md`, `CHANGELOG.md` and `data/clinical_organisms.yaml` to
reflect the real results rather than leave them marked "unverified." Also clarified for the user
that no pull request exists (none was requested) and re-verified branch/tag/version sync between
local and `origin/claude/brave-dirac-1vppye` before this.

Key results:
- **Taxonomy lineage parsing works**: 5/5 sampled lineages (Homo sapiens, Mus musculus, SARS-CoV-2,
  E. coli, S. aureus) came back with a populated genus and family through the real `resolve.py`
  code, not ad-hoc smoke-test code. One real subtlety worth remembering: SARS-CoV-2's own Taxonomy
  `Rank` is `"no rank"`, not `"species"` -- its species comes from its `LineageEx` ancestor
  (`Betacoronavirus pandemicum`). `Lineage.species` handles this correctly already.
- **The organism-list resolution path works**: 38/40 packaged names resolved through the real
  `resolve_organism_list` function (not a mock). Unresolved: "Mycoplasma pneumoniae" and
  "Mycobacterium chelonae".
- **A hypothesis from the previous session was wrong, and worth remembering as a lesson**: I
  assumed (docs/ARCHITECTURE.md, `taxonomy/resolve.py`'s docstring) that the `[All Names]` synonym
  fallback would catch "Mycoplasma pneumoniae"'s 2018 genus rename to *Mycoplasmoides*. It does
  not -- both terms returned zero hits. Fixed by renaming the organism-list entry to
  "Mycoplasmoides pneumoniae" directly (itself not yet confirmed live) rather than relying on the
  fallback. Updated the docstring and ARCHITECTURE.md to stop claiming the fallback would catch
  this, and to note synonym resolution is not as complete as assumed.
- **Significant, unprompted finding from a pre-existing smoke-test check (step 08, not written this
  session): combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call
  does not reliably restrict by date** (`blast_date_window_restriction_honoured: false` -- 4 of 20
  checked hit accessions fell outside the requested window). This directly rules out the inclusivity
  design SPEC.md step 7 describes and this project had assumed for phase 4b ("BLAST the reference
  amplicon against nt restricted to the target taxid, stratified into time windows via `ENTREZ_QUERY`
  date filters"). ESearch's own `[PDAT]` filtering is independently confirmed reliable, so phase 4b
  must get each window's accession list from ESearch and work from that list directly, not lean on
  BLAST for the date filtering. This is a design-level finding that must be read before starting 4b.
- Also newly confirmed: Entrez queries with 11/40/100 taxids are all accepted by the BLAST URL API
  (true upper limit still unknown, but 100 is now a safe planning number).
- Did not bump `pyproject.toml` or tag anything: phase 4a's *code* was already committed and pushed
  in the previous session; this session only updated documentation to match the live results, plus
  one data fix (the organism-list rename). Committed and pushed (user asked directly both times).

Left for the user / next session:
- **"Mycoplasmoides pneumoniae" and "Mycobacterium chelonae" still need a live re-check** (a
  smaller, targeted smoke-test run, or just watch the next full run's `exclusivity.unresolved`).
- **Phase 4b (inclusivity) needs a redesign before implementation starts**, per the `[PDAT]`+BLAST
  finding above -- do not start coding phase 4b against the old SPEC.md step 7 description without
  first working out the ESearch-based alternative.
- `--human`/`--probe-databases` smoke-test options still not run; alternative database timing for
  the human background tier remains unmeasured beyond the original 61-minute `core_nt` figure.

## 2026-09-21 — v0.4.0 phase 4a: taxonomy resolution, organism list, exclusivity

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

## 2026-09-21 — v0.3.0 pushed; pruning bounds validated live

- Pushed the v0.3.0 commit to `origin/claude/brave-dirac-1vppye` (user confirmed).
- Created an annotated `v0.3.0` tag locally, but **pushing it was blocked**: the sandbox's egress
  proxy returned an HTTP 403 specifically for the tag ref (the branch push to the same host had just
  succeeded), which the proxy's own guidance identifies as an organization policy denial, not a
  transient failure — so it was not retried or routed around. Also discovered the "no git tags
  exist" note from the previous session was wrong: v0.1.0/v0.2.0/v0.2.1 tags do exist on the remote;
  this sandbox's clone had just never fetched them. Told the user to pull the branch and push (and
  tag) themselves from their own machine (a Synology NAS running code-server in Docker), where the
  restriction likely doesn't apply.
- The user ran `scripts/validate_assessment.py` live (CDC N1 example, `--tier background`) and
  pasted back `validation_out/validation_report.json`: 905 relevant alignments, 244 ruled out
  without fetching, 661 needing a fetch (replaces the earlier unmeasured "about 1,500" guess),
  80-hit sample checked (40 fetchable, 40 ruled out), **0 contradictions**. Updated README.md,
  `docs/ARCHITECTURE.md` and `CHANGELOG.md` to reflect this: the pruning bounds are no longer
  described as "unverified," but as checked once, on a sample, for one assay's background tier —
  not exhaustive proof, and worth re-running for other tiers/assays or after logic changes.
- `scripts/smoke_test.py` still has not been re-run since 0.2.1 — still open.

## 2026-09-21 — v0.3.0: specificity assessment integrated

Picked up a work-in-progress snapshot (`qpcr-assay-check-v0.3.0-WIP-snapshot.zip`, built in a
separate sandbox without NCBI access) that implemented phase 3 of the roadmap: full-length
re-alignment (`align/realign.py`), amplicon pairing and site classification (`specificity/`), and
wired them into `run`. State at handoff: 249/250 tests passing, one ruff E501.

What this session did:
- Diffed the snapshot against the repo, scanned it for anything suspicious (network calls, eval/exec,
  unexpected URLs) before integrating — clean — then copied it in file by file.
- Fixed the one failing test. Root cause: `tests/world.py`'s "realistic BLAST hit" guard only checked
  that the first base beyond a partial alignment mismatched. That is too weak — with match +1 /
  mismatch -3 scoring, BLAST's alignment is locally maximal, so *no prefix* of the unaligned flank
  (read outward from the alignment boundary) may sum to a positive score, or BLAST would have
  extended over it. Rewrote the guard to check every prefix, and fixed the handful of test scenarios
  (`f=[10,16]`+`trim3=5`, `r=[7,23]`+`trim5=7`, and two `human_world()` cases) that had relied on the
  weaker check — each needed one more mismatch placed adjacent to the alignment boundary to stay
  realistic. Confirmed the fix by re-deriving each affected assertion (n_mismatch, defect_positions,
  clean_3prime_nt, level) from `specificity/sites.py`'s actual classification rules rather than
  guessing.
- Fixed the ruff E501 (a docstring line in `tests/test_validation_script.py`).
- `ruff check .` and `pytest -m "not live"` are both clean: 250 passed.
- Updated README.md (status banner, privacy note — `run` now sends oligos and hit accessions to
  NCBI, not just `search`; new Specificity assessment and live-validation sections; limitations;
  roadmap), `docs/ARCHITECTURE.md` (status, v0.3.0 design decisions, moved the now-verified
  minus-strand coordinate fact out of "still unverified", added the v0.3.0 unverified-pruning-bounds
  note), and `CHANGELOG.md` (0.3.0 entry).
- Did not run `scripts/smoke_test.py` or `scripts/validate_assessment.py` live — this sandbox has no
  NCBI access, per CLAUDE.md. Both need to be run locally and their output pasted back (see below).
- Applied the user's go-ahead on the license question: proceeded with the already-committed
  Apache-2.0 (`LICENSE`, `pyproject.toml`) rather than treating it as still open.

Left for the user / next session:
- **Run `scripts/validate_assessment.py` live** (needs `NCBI_EMAIL`; background tier can take about
  an hour, cached 7 days after). Paste back `validation_out/validation_report.json`. If it reports a
  contradicted rule, the pruning in `specificity/sites.py` (`can_reach_warning` / `Candidate.lower_bound`)
  needs fixing before the specificity verdict can be trusted — do not treat the "world" as necessarily
  wrong this time; the script tests the rule, not just the constructed data.
- `scripts/smoke_test.py` is unchanged (wire protocol only) but has not been re-run since 0.2.1.
- Local commit created on `claude/brave-dirac-1vppye`; not pushed. CLAUDE.md requires asking before
  any push — waiting for that go-ahead.
- Still open from the previous session: no git tags exist locally even though CHANGELOG documents
  0.1.0–0.2.1 as released — worth reconciling before the next tag is cut.
- No annotated tag has been cut for 0.3.0 yet.

## 2026-09-20/21 — v0.1.0–v0.2.1 (prior sessions, summarized from CHANGELOG.md)

- v0.1.0: skeleton, input parsing, oligo QC (primer3-py), report skeleton. No network use.
- v0.2.0: remote BLAST backend (own `requests` client, not `qblast`, so RIDs can be persisted and
  resumed), throttling/backoff, content-addressed cache, tiered taxon-restricted search planning,
  JSON2 parser, `scripts/smoke_test.py`. Validated only against a simulated NCBI.
- v0.2.1: fixes from the first live run of `scripts/smoke_test.py` — most notably a redaction bug
  (the e-mail could leak into logs in its URL-encoded form during a transient error) and several
  NCBI facts confirmed for the first time (see `docs/ARCHITECTURE.md`'s "Verified in the first live
  smoke run" section): short-oligo BLAST parameters accepted as configured, `JSON2_S` report shape,
  `ENTREZ_QUERY` taxon restriction effective but not airtight, human-restricted `core_nt` searches
  take about an hour.

## Open questions carried across sessions

- License: resolved — proceed with Apache-2.0 (already committed). CLAUDE.md's "Open items" note
  that it was unchosen is stale.
- Git tags: resolved — v0.1.0/v0.2.0/v0.2.1 exist on the remote; a prior session's local clone had
  just never fetched them. **v0.3.0 needs the user to tag and push it themselves** (this sandbox's
  egress policy blocks tag pushes even though branch pushes work).
- `scripts/smoke_test.py` has not been re-run since 0.2.1; the wire protocol is unchanged but this
  is still worth doing before the next release.
