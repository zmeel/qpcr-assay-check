# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release is tagged `vX.Y.Z`.

## [Unreleased]

### Added
- **Report states when human background was not searched** (`pipeline.py`, `search/planner.py`):
  setting `search.background_taxids: []` (e.g. to skip the slow, roughly hour-long human search)
  used to drop the background tier silently. The search plan now warns when human (taxid 9606) is
  not in `background_taxids`, and a full run whose searches (other than the target tier) did not
  cover 9606 adds a "Human background: ... not evaluated" line to the overall rationale and a note
  to the specificity section. The verdict itself is unchanged.

### Fixed
- **Variant summary was always empty on a real run** (`specificity/variants.py`, `cli.py`,
  `pipeline.py`): it filtered the specificity sites for the target tier, but the specificity
  assessment only builds sites for the off-target tiers, so the section (and the "Oligo variants"
  and "Fragment variants" sheets) never appeared. Found in the first live report. New
  `assess_target_sites` assesses every target-tier hit (partial hits fetched and re-aligned, the
  closest site per record and oligo), passed to `evaluate()` separately so it never touches the
  off-target verdict. The whole-fragment table now groups the three oligos per record instead of
  per predicted product, so a primer with a 3'-end mismatch still appears. The report's scope
  note states the hit-list cap.
- **Stale "planned for v0.4.0" texts** (`specificity/findings.py`, `report.html.j2`): the
  specificity scope said hits from the clinical organism list were "not included yet", even when
  the exclusivity tier had just been assessed. It now lists the tiers assessed and any configured
  off-target tier that was not searched in the run. The Methods row on the taxon restriction check
  no longer promises a lineage-based check; it says the counts compare exact taxon IDs only.
- **Inclusivity silently skipped years it could not sample** (`inclusivity/aggregate.py`): a year
  with records at NCBI but none among the target tier's BLAST hits (found live: SARS-CoV-2, 2020,
  47,129 records, 0 sampled) was left out of the verdict without a word, under "Every assessed
  year is at or above the threshold". The rationale now names each such year, its record count and
  the oligos affected, as not assessed. The verdict is unchanged.
- **Exclusivity table undercounted hits on finely-split taxa** (`taxonomy/exclusivity.py`):
  `ExclusivityRow.n_sites` grouped hits by exact taxid equality against the organism-list entry's
  own resolved taxid. A BLAST hit's own `taxid` is whatever specific NCBI Taxonomy record the
  matched sequence is filed under, which for organisms with strain-level splitting (found live:
  Influenza A -- roughly 10% of hits under a species-restricted search carried a distinct, more
  specific descendant taxid, e.g. a named strain) is more specific than the species-level (or
  higher) taxid an organism-list name resolves to, so those hits were silently missing from their
  organism's row and count -- while the overall exclusivity tier verdict (which counts every
  exclusivity-tier hit directly, not grouped by row) was never wrong. Now groups by species name
  when known (`taxonomy.resolve.fetch_lineages`, reusing the same lineage lookup the taxonomy
  breakdown already makes -- no new NCBI calls), falling back to the exact taxid exactly as
  before for anything the lineage lookup doesn't cover, never guessing a match that wasn't
  actually looked up. Found from a fresh live smoke test run (2026-09-23) whose new Influenza A
  restriction check (replacing the old ad-hoc human-background check) exposed the exact-taxid
  vs. taxonomic-subtree discrepancy that a SARS-CoV-2/human-only check would never have surfaced.

### Added
- **Variant summary report** (`specificity/variants.py`): a new report section, requested after
  comparing the tool against a lab's own pre-existing manual spreadsheet workflow for the same
  kind of assessment. Lumps the target tier's own hits into unique sequence variants -- one row
  per distinct alignment, with a count and a percentage of the measured total -- per oligo
  (forward/probe/reverse) and, new relative to that manual spreadsheet, for the whole fragment
  (forward + probe + reverse considered together on the same record). Only sites with a real,
  fully observed alignment (`blast_full`/`realigned`) are counted; `blast_partial_worst_case`
  sites are excluded and the excluded count is reported, never silently folded in as if measured.
  Reuses evidence the specificity assessment already scored (like `taxonomy/rollup.py`'s
  species/genus/family aggregation) -- no new NCBI calls, and no verdict of its own. New "Variant
  summary" report.html section and "Oligo variants"/"Fragment variants" xlsx sheets.
- **Per-assay exclusivity panels**: `Assay.exclusivity_organisms`, a new optional field in
  `assay.yaml`, lets one assay carry its own exclusivity organism list instead of always using the
  single global/packaged one -- requested because a global panel applied to every assay doesn't
  reflect that different assays have different real near neighbours. New `organisms.source`
  config setting (`"assay"`, the default, prefers the assay's own list when it defines one and
  falls back to the global list otherwise so existing assays keep working unchanged; `"global"`
  always uses the global list regardless of what the assay defines) decides which list a run
  actually uses. `ExclusivityResult.source` and `results.xlsx`'s Summary sheet record which one
  was used, and `report.html`'s Exclusivity section states it explicitly, so this is never
  silently ambiguous after the fact.

## [1.0.0] - 2026-09-22

Run history and a yearly diff report, and a Docker image.

**Live validation (2026-09-22):** the Docker image was built and run by the user on their own
hardware (build, `--version`, `--help`, `init`, `run --qc-only`, and a full network run against
real NCBI all confirmed working). That first full run surfaced a real bug -- the exclusivity tier
had no exclusion for the assay's own target taxid, so a respiratory-panel organism list that also
lists the assay's own target (e.g. SARS-CoV-2) reported the assay's own perfect match as an
off-target FAIL -- fixed, then re-verified live on the same assay: predicted off-target products
dropped from 500 to 0, and the new history/diff feature correctly attributed the change to the
fix (6028 sites and 500 products "no longer found"). This is also the first live confirmation of
history/diff itself, across that same two-run pair. See `docs/ARCHITECTURE.md` and
`docs/PROGRESS.md` for the full account.

### Added
- **Run history and diff** (SPEC.md step 11): every full `run` now finds the most recently
  generated previous run for the same assay (`results/<assay.slug>/*/results.json`, sorted by each
  record's own `generated_at` -- no separate index or database) and diffs the current evaluation
  against it. `history/store.py` locates the previous run; `history/diff.py` compares: per-section
  verdict changes, off-target sites and predicted products that are new or have disappeared
  (matched across runs by accession and position, not by the run-local site ID), and inclusivity
  regressions per oligo/year (including newly-observed mismatch positions). New `history` field on
  `results.json`, a "Changes since the previous run" report section, and a "History" xlsx sheet.
  Like every other section, missing evidence is never a PASS: a first run for an assay has nothing
  to compare against, so it is honestly `INCOMPLETE`, not skipped -- confirmed with the user before
  implementing, since it means a brand-new assay's first run can never itself reach overall `PASS`.
  From the second run onward it is a real `PASS` (nothing concerning changed) or `WARN` (a section
  regressed, a new critical/warning site or product appeared, or inclusivity regressed); it never
  fails a run by itself, since a regression severe enough to fail already fails the specific section
  it belongs to.
- **Dockerfile**: a small multi-stage image (no local BLAST database, just the CLI and its Python
  dependencies), `.dockerignore`, and a Docker section in the README with build/run instructions
  (including the `--user "$(id -u):$(id -g)"` needed for a bind-mounted volume the image's default
  non-root user does not own -- see Known limitations). Built and run successfully by the user.
- 16 new tests: `tests/test_history.py`'s natural-key matching and first-run-INCOMPLETE unit tests,
  `tests/test_run_full.py`'s full two-run CLI end-to-end scenario, and (once the exclusivity/target
  bug below was found) regression tests for it in `tests/test_exclusivity.py` and
  `tests/test_run_full.py`. 311 tests total (up from 295); `ruff check` clean.

### Changed
- `pipeline.PLANNED_SECTIONS` removed: "history" was its only remaining entry and is now a real,
  implemented section like every other one.
- `report.html`'s "Not yet evaluated" section now lists sections that were genuinely skipped or not
  implemented (`state != "evaluated"`), not sections with a `None` verdict -- a section that *was*
  evaluated but concluded `INCOMPLETE` (missing evidence) is no longer miscounted as "not yet
  evaluated". The "oligo sequences were/were not sent to NCBI" disclosure, previously shown only
  inside that (sometimes now-empty) block, is now always shown.

### Fixed
- `.gitignore` had a stale, unscoped `history/` rule (from early scaffolding, apparently intended
  for a since-abandoned separate run-history output directory that this phase's "history as files"
  design never needed) that was silently ignoring the entire new `src/qpcr_assay_check/history/`
  source package. Found and fixed before the first commit of this phase; nothing was ever lost, but
  it would have quietly excluded the whole feature from version control.
- **The exclusivity tier had no exclusion for the assay's own target taxid**, found by the user's
  first full live `run` through Docker: the packaged organism list includes "Severe acute
  respiratory syndrome coronavirus 2" (reasonable for a respiratory panel), which is also the CDC
  N1 example's own target. Without an exclusion, the exclusivity tier's search could only ever find
  the assay's own perfect, intended match against itself, and reported every one of those matches
  as a critical off-target site or a "likely detected" predicted product -- 4025 critical primer
  sites, 2000 critical probe sites and 343 "likely detected" products, all at 0 mismatches, which
  alone flipped the overall verdict to a misleading `FAIL`. Fixed: `search/execute.py` now filters
  `assay.target.taxid` out of the exclusivity search's taxids; the organism-list row for it is
  still shown (never silently dropped), flagged via the new `ExclusivityRow.is_target`, with no
  site/amplicon evidence populated for it even defensively. See `docs/ARCHITECTURE.md`.

### Known limitations
- **Docker's default user is non-root (uid 1000)**: a bind-mounted host directory it does not own
  is not writable from inside the container without `--user "$(id -u):$(id -g)"` on `docker run`
  (or a `chown` of the host directory to uid 1000 beforehand); documented in the README. The image
  itself could not be built in the sandbox this was developed in (no route to Docker Hub through
  its outbound proxy, confirmed with both `docker pull` and `docker build`), so this was found and
  fixed only once the user built and ran the image themselves (2026-09-22). A full network run
  against real NCBI, through the container, was also confirmed by the user and is what surfaced
  the exclusivity/target bug fixed above -- see `docs/ARCHITECTURE.md`.
- The exclusivity/target fix has been re-checked against live NCBI data by re-running the same
  assay: predicted off-target products dropped from 500 to 0, and the history/diff section
  correctly attributed the change (6028 sites and 500 products "no longer found") to the fix. The
  run's overall verdict is still `FAIL`, now for a real reason (human-genome primer homology, a
  known characteristic of this published assay) -- see `docs/ARCHITECTURE.md`.
- **History/diff has been checked against one real two-run pair** (immediately above), stronger
  than the constructed test world alone, though still only one assay. Its natural-key matching
  operates entirely on this tool's own already-verified output (no new NCBI behaviour involved),
  so no live smoke-test step was needed.
- **The previous run is found by assay slug** (derived from the assay name), not by assay content:
  renaming an assay starts its history over, even if the oligos did not change.
- A regression that shows up in history's diff already made the specific section (specificity,
  exclusivity, inclusivity) fail or warn on its own; history's own verdict only ever reaches WARN
  (flagging that something changed, worth a look), never FAIL, to avoid double-counting the same
  evidence into the overall verdict twice.

## [0.4.0] - 2026-09-22

Phases 4a and 4b: taxonomy resolution, the clinical organism list, a real exclusivity tier
and report, and inclusivity (a year-by-year trend of how well the oligos still match the intended
target).

**Live validation (2026-09-22, `scripts/smoke_test.py` steps `03b`/`03c`):** taxonomy lineage
parsing matched real output for all 5 sampled organisms; 38 of the 40 packaged organism-list names
resolved through the real exclusivity-resolution path (2 did not: see Known limitations). Entrez
queries with up to 100 taxids were accepted. One important negative result, which shaped phase 4b's
design: **combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call
does not reliably restrict by date** (4 of 20 checked hit accessions fell outside the requested
window), ruling out this project's originally planned inclusivity design (see
`docs/ARCHITECTURE.md`).

**Further live validation (2026-09-22, `scripts/smoke_test.py` step `08b`):** the renamed organism
`Mycoplasmoides pneumoniae` now resolves live (39 of 40 packaged names resolve; only
`Mycobacterium chelonae` remains unresolved). Phase 4b's own new E-utility usage was also checked:
`Eutils.esummary()`'s JSON shape matched a real response, the nuccore ESummary docsum's date field
is `createdate` (confirmed by extracting the correct year for two real records), and NCBI does key
the result by resolved UID rather than by the input accession (confirmed directly) -- `fetch_years()`
correctly recovers the right years despite this. A bug was found and fixed in the smoke-test
script's own (separate, redundant) findings computation, which had naively assumed the response was
keyed by accession; the shipped `inclusivity/dates.py` code was already correct. See
`docs/ARCHITECTURE.md` for detail.

### Added
- `taxonomy/resolve.py`: resolves organism names to NCBI taxonomy IDs via Entrez Taxonomy
  (`[Scientific Name]`, then `[All Names]` for synonyms), cached; exactly one UID is a resolution,
  more than one is flagged ambiguous, none is unresolved -- never guessed. Also fetches and parses
  taxonomy lineages (species/genus/family), cached per taxid.
- `data/clinical_organisms.yaml`: a small, hand-picked, **non-authoritative starting point** organism
  list (sexually transmitted pathogens, atypical pneumonia bacteria, *M. tuberculosis* complex and
  other mycobacteria, common respiratory/other viruses, human background), grouped by category;
  override with your own file via the new `organisms.list_file` config key.
- `run`'s full pipeline now resolves the organism list and searches it as a real **exclusivity**
  tier, reusing the same specificity assessment as every other off-target tier (no parallel
  implementation). `taxonomy/exclusivity.py` builds SPEC.md step 8's own view over that evidence:
  one row per organism-list entry -- including zero-hit organisms and names that did not resolve --
  plus a tier-scoped verdict. A tier that could not be searched at all (nothing resolved) is
  INCOMPLETE, never a silent PASS.
- `taxonomy/rollup.py`: aggregates every off-target site (all tiers, not only exclusivity) by
  species/genus/family from cached lineages -- SPEC.md step 6, generalised beyond exclusivity. A
  lineage-fetch failure degrades this to empty rather than failing the whole evaluation.
- `report.html`, `results.xlsx` and `results.json` gained Exclusivity and Taxonomy-breakdown
  sections/sheets/fields.
- `scripts/smoke_test.py` steps `03b` (lineage parsing, the `Mycoplasma pneumoniae` synonym
  fallback through the real `resolve_name` function) and `03c` (the actual exclusivity-tier
  resolution path against the packaged organism list) -- now run live, see above.
- **Inclusivity** (SPEC.md step 9, phase 4b): a year-by-year trend of how well the oligos still
  match the intended target. Reuses the "target" tier search every run already makes (no separate,
  date-restricted BLAST search -- see `docs/ARCHITECTURE.md` for why that design was ruled out) and
  buckets its hits into years afterwards via a new `Eutils.esummary()` client method plus
  `inclusivity/dates.py`. Each year: a deterministic, evenly spread sample (capped by the new
  `inclusivity.sample_per_window` config key) is re-aligned over the full oligo length and scored
  for perfect/1-mismatch/2+-mismatch/3'-mismatch counts and a per-position mismatch profile;
  population size per year comes from an independent ESearch count, reported next to (never instead
  of) the sample size. A target tier that was never searched, or a year with no dated hits, is
  INCOMPLETE for that scope rather than a silent PASS. New `inclusivity.*` config section
  (`lookback_years`, `sample_per_window`, `warn_below_percent`, `fail_below_percent`), `report.html`
  section, `results.xlsx` sheet, and `results.json` field.
- `scripts/smoke_test.py` step `08b_esummary_inclusivity_dates`: checks the real nuccore ESummary
  docsum date field name(s) and the accession re-indexing logic live -- now run, see above.
- 15 new tests for phase 4b (ESummary date extraction/re-indexing, inclusivity site assessment,
  end-to-end date-bucketing/sampling/verdict aggregation, one full CLI end-to-end scenario with a
  dated target-tier hit). 295 tests total (250 before phase 4a, 280 after phase 4a, 295 after
  phase 4b); `ruff check`/`ruff format --check` clean.

### Changed
- README's privacy note: organism-list *names* (never the oligo sequences) are now sent to Entrez
  Taxonomy automatically, before the send-oligos confirmation, since they are not proprietary.
- `specificity.off_target_tiers` default now includes `exclusivity`.
- `run`'s full pipeline now always keeps the "target" tier's own search results (previously
  discarded once specificity had used them), since inclusivity needs them too.

### Fixed
- `data/clinical_organisms.yaml`: "Mycoplasma pneumoniae" does not resolve live, and (unlike the
  hypothesis in the first draft) the `[All Names]` synonym fallback does not catch its 2018 genus
  rename either. Renamed the entry to "Mycoplasmoides pneumoniae" directly; confirmed live in a
  later run in this same release (see above): it resolves.
- `scripts/smoke_test.py` step `08b`'s own findings computation indexed ESummary's UID-keyed
  response by accession directly, silently producing empty findings even though the shipped
  `inclusivity/dates.py` code (which re-indexes correctly) was unaffected. Fixed, and the
  constructed test fakes (`tests/world.py`, `tests/test_smoke_script.py`) were tightened to use a
  UID that deliberately differs from the accession, so this class of bug is now caught by the test
  suite, not only by a live run.

### Known limitations
- The packaged organism list is a small sample, not a claim of completeness for any assay; every
  laboratory must review and edit it (or supply its own file) before relying on the exclusivity
  report. Checked live: 39 of 40 packaged names resolve; "Mycobacterium chelonae" currently does
  not (cause unknown).
- Organism-name resolution can silently regress after an NCBI Taxonomy update (a name that used to
  resolve stops resolving, as apparently happened for "Mycoplasma pneumoniae"); the `[All Names]`
  synonym fallback does not catch every rename. Review `results.json`'s `exclusivity.unresolved`
  after every run, not just when first setting up an organism list.
- **Inclusivity's originally planned design (SPEC.md step 7) does not work as specified**: combining
  `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call does not reliably
  restrict by date (checked live: 4 of 20 checked hit accessions fell outside the requested window).
  Implemented instead: reuse the target tier's own search and bucket by date afterwards via
  ESummary (see `docs/ARCHITECTURE.md`), now itself checked live for the common case (a record with
  a `createdate` field).
- **Inclusivity's yearly sample is not a controlled random sample of the population**: it comes from
  whatever the target-tier BLAST search's own hit list (capped by `search.hitlist_size`) returned
  for that year, so a well-sequenced target can under- or over-represent some years depending on
  BLAST's own ranking. Reported honestly: `population_size` (an independent ESearch count) is always
  shown next to `sample_size`, and this limitation is stated on every `InclusivityResult`.
- **Inclusivity's ESummary-based date lookup has not been checked live yet** (the real nuccore
  docsum date field name, and the accession re-indexing logic for more than one accession at once
  are both taken from documentation/memory or checked only against the constructed test world).
  `scripts/smoke_test.py` step `08b_esummary_inclusivity_dates` checks this; run it before trusting
  inclusivity's year attribution.

## [0.3.0] - 2026-09-21

Full-length re-alignment, amplicon pairing and a real specificity verdict.

**Live validation (2026-09-21, `scripts/validate_assessment.py`, CDC N1 example, background
tier):** the two pruning bounds that decide which BLAST hits can skip an `efetch` call were
checked against a sample of 80 real hits (40 that would be fetched, 40 ruled out) out of 905
relevant alignments — **0 contradictions**. A full run of this tier on this assay would make 661
`efetch` calls (905 relevant alignments, 244 ruled out without fetching), superseding the earlier
unverified "about 1,500" estimate. This is a sample check, not exhaustive proof, and covers one
assay's background tier; re-run it after any change to the alignment or pruning logic.

### Added
- `run` (without `--qc-only`) now performs the full pipeline by default: tiered remote BLAST search,
  full-length re-alignment of every relevant hit, amplicon prediction, and a genuine
  PASS/WARN/FAIL specificity verdict — not just `INCOMPLETE`. The overall verdict still ends
  `INCOMPLETE` until exclusivity, inclusivity and run history exist (v0.4.0/v1.0.0).
- `align/realign.py`: an affine-gap semi-global aligner (own implementation, no new dependency) for
  fitting a whole oligo into a fetched subject window.
- `specificity/`: turns BLAST hits into full-length binding sites and predicted products.
  - Three site sources, most to least certain: `blast_full` (BLAST's own alignment already spans
    the oligo), `realigned` (a fetched window re-aligned in full), `blast_partial_worst_case` (not
    re-aligned — provably cannot reach a reportable level, or the fetch failed — assumed to match
    as well as BLAST's own scoring allows, the risk-conservative choice).
  - Two BLAST-scoring-derived bounds decide which partial hits can be skipped without an `efetch`
    call: a mismatch lower bound and a clean-3'-nt cap. Checked against a live sample of real hits
    with `scripts/validate_assessment.py`: 0 contradictions (see above).
  - Forward/reverse hits on the same accession, facing each other within `specificity.max_amplicon_size`,
    are paired into predicted products and classified likely detected / amplified but not detected /
    primer-only, depending on whether the probe also binds; genomic-DNA products are flagged for
    RNA assays in eukaryotic targets.
  - Duplex Tm/ΔG for a mismatched site, verified against primer3 directly (a 3'-terminal mismatch is
    treated as an unpaired overhang: 61.6 vs 61.2 °C); priming risk is judged from mismatch
    positions and clean-3'-nt count, never from Tm alone.
  - A target tier without a perfect full-length hit for every oligo is a WARN: the assay's own
    positive control is missing.
  - Saturation, the `specificity.max_sites_per_query` cap and a failed window fetch all make the
    result INCOMPLETE, never a silent PASS.
- `report.html`, `results.xlsx` and the new `hits.tsv` (one row per assessed site, with alignments,
  mismatch positions and duplex Tm/ΔG) now cover specificity and predicted products.
- `scripts/validate_assessment.py`: samples real BLAST hits of one tier, re-aligns them over the
  full oligo (including hits the assessment would skip), and reports every case where reality
  contradicts a pruning bound, plus the number of `efetch` calls a real run makes.
- Real minus-strand NCBI hit data as a test fixture (`tests/fixtures/real_hits_strands.json`):
  confirms that for a Minus hit `hit_from > hit_to`, `query_strand` is always `Plus`, and `hseq` is
  written in the oligo's own orientation.
- A constructed end-to-end test world (`tests/world.py`) with a real-BLAST-behaviour guard: a hit
  cannot leave an unaligned flank where any prefix (read outward from the alignment boundary) would
  have scored positive under BLAST's own match(+1)/mismatch(-3) scoring, because BLAST would then
  have extended the alignment over it.
- 250 tests (up from 160); `ruff check` and `ruff format --check` clean.

### Changed
- README's privacy note: a full `run` (not only `search`) now sends oligo sequences to NCBI, and
  also sends hit accessions to E-utilities to fetch sequence windows.
- `results.xlsx` gained "Off-target sites", "Predicted products" and "Findings" sheets.

### Fixed
- An earlier deleted `offtarget/` package name is retired for good; the current implementation is
  `align/` + `specificity/`. (Internal only — never released.)

### Known limitations
- The pruning bounds were checked live on one assay's background tier, on a sample of 80 of 905
  relevant alignments (see above), not exhaustively and not on the near-neighbour or target tiers;
  re-run `scripts/validate_assessment.py` (a different `--tier`, a larger `--sample`) periodically
  and whenever the alignment or pruning logic changes.
- Amplicon pairing only expands the primary record of a BLAST hit group; sequences merged into one
  hit by core_nt (observed: up to ~39 descriptions per hit) are not, so a product on a merged record
  can be missed.
- Specificity covers only the tiers actually searched (intended target, near neighbours,
  background); the clinical organism list, inclusivity and history arrive in v0.4.0/v1.0.0.

## [0.2.1] - 2026-09-21

Fixes from the first live run of `scripts/smoke_test.py` (results reviewed 2026-09-21).

### Security / privacy
- **Fixed: the e-mail address could appear in logs and error messages.** HTTP-library errors
  quote the request URL, in which the address is URL-encoded (`%40`); the old redaction only
  matched the plain address, so it leaked into a log line during a transient DNS failure. Redaction
  now masks the `email=` and `api_key=` parameters whatever the encoding, and also every encoded
  form of the address and key. If you ran v0.2.0, check your saved logs for `email=`.

### Verified against the live NCBI servers (first run, one assay)
- The BLAST URL API accepted the configured parameters, and the real `JSON2_S` report parsed
  without changes. Details in `docs/ARCHITECTURE.md`.
- The CDC N1 oligos match NC_045512.2 exactly (72 bp product, positions 28287-28358).

### Fixed
- E-utilities requests were spaced at NCBI's documented limit and still drew HTTP 429 (recovered by
  retry); they are now spaced at about 2 requests/s without an API key and 6-7 with one.
- The parser no longer falls back to matching queries by position. Real reports number queries
  with a global counter (`Query_1830923`), so position was never usable; titles are always
  echoed.
- `search.json` restriction summaries include `fraction_in_requested`; documented that
  `ENTREZ_QUERY` filters on the record's organism index (1 of 3,715 human hits was a "synthetic
  construct" carrying a human source feature): effective, not airtight.
- A saturated hit list in the intended-target tier is now informational (a note, exit code 0): a
  well-sequenced target always fills the list with perfect hits. Saturation elsewhere still warns.
- Default `ncbi.max_wait_minutes` raised from 120 to 240: a human-restricted `core_nt` search took
  61 minutes.
- Poll log lines show the minutes since submission; the runner's clock is resolved at call time.

### Added
- The example assay now ships its verified 72 bp `reference_amplicon` (fetched from the record).
- Real NCBI hit objects as test fixtures (`tests/fixtures/real_hit_*.json`).

### Changed (smoke test only)
- The report is written after every step, so it exists even if the run is interrupted.
- `--max-wait-minutes` (default 30) makes a stuck search fail its step without blocking the rest.
- The human search is opt-in (`--human`); `--probe-databases` tries alternative databases.
- Restriction is judged as "effective" (at least 99 % of hit taxa inside the requested subtree,
  lineages fetched from Entrez Taxonomy) instead of an all-or-nothing test.
- An influenza A restriction check replaces the human negative control; the heavy genomes (human,
  mouse) are kept out of the multi-taxa list test.

## [0.2.0] - 2026-09-21

Remote BLAST backend. **The client is tested against a simulated NCBI only; the live smoke test
(`scripts/smoke_test.py`) has not been run yet.**

### Added
- `qpcr-assay-check search`: tiered, taxon-restricted BLAST searches (intended target, near
  neighbours and exclusion taxa, background taxa) writing `hits.tsv`, `search.json`, `jobs.json`.
  `--dry-run` shows exactly what would be sent and needs no credentials; sending requires
  confirmation (`--yes` to skip).
- NCBI client: own `requests`-based BLAST URL API client (submit, poll, fetch), minimal
  E-utilities client, identification (`tool`, `email`, optional `api_key`), throttling (BLAST at
  least 10 s between requests, one poll per RID per minute, E-utilities 3 or 10 requests/s),
  exponential backoff with `Retry-After`, secrets redacted from errors.
- Resumable jobs: RIDs are persisted before polling; an interrupted run continues with the same
  command; RIDs older than the retention window and unknown RIDs are resubmitted.
- Content-addressed cache with per-kind expiry (BLAST results 7 days, so a yearly re-run never
  receives last year's answer), atomic writes, corrupt entries treated as misses.
- Parser for BLAST JSON2 reports that fails loudly on unexpected structure and never matches
  queries to oligos by guesswork.
- Relevance-based hit-list saturation detection, and a summary of what a taxon-restricted search
  actually returned.
- Search planning: degenerate oligos sent as separate variants, batches of at most 1,000 bases,
  taxon groups chunked to a configurable limit, off-peak check (US Eastern) and search-budget
  warning.
- `scripts/smoke_test.py`: checks the unverified NCBI assumptions on the real servers and verifies
  the CDC N1 oligos against the SARS-CoV-2 reference record; writes a secret-free report.
- Configuration sections `ncbi` and `search`; credentials only from `NCBI_EMAIL` / `NCBI_API_KEY`.
- 160 tests (mocked NCBI; live tests remain opt-in).

### Changed
- The inputs hash now covers the search settings and excludes operational settings (`ncbi`,
  `report`), so it differs from v0.1.0 hashes for the same assay.
- The "specificity" section of a full run is now planned for v0.3.0 (assessment needs
  re-alignment); v0.2.0 only collects hits.

### Known limitations
- `ENTREZ_QUERY` taxon restriction is outside NCBI's documented URL API and is verified only by
  the smoke test; the taxid-list size limit, the maximum `HITLIST_SIZE`, and the exact JSON2 layout
  are unverified until then. The default `max_taxids_per_search` (20) is a conservative guess.
- The restriction check counts hit taxa against the requested set; a strict lineage-based check
  arrives with taxonomy in v0.4.0.

## [0.1.0] - 2026-09-20

First release: project skeleton, input handling, oligo quality control and a report skeleton.
**No sequence is searched against any database in this version, and nothing is sent to NCBI.**

### Added
- Assay definition from a YAML file and/or command-line options, with validation and actionable
  error messages (uracil, dye names in sequences, bad accessions, unknown fields, length limits).
- IUPAC handling with degenerate expansion under a configurable cap; every variant is evaluated and
  the worst result decides each status.
- Oligo QC with primer3-py: length, GC%, Tm (SantaLucia nearest-neighbour, salt-corrected),
  G/C in the last 5 nt, informational 3'-end nearest-neighbour ΔG, homopolymer and G runs,
  hairpins, self-dimers, primer-primer and primer-probe dimers (including extendable 3'-end
  dimers), primer Tm difference, probe Tm relative to the primers, 5' G next to FAM-type reporters,
  probe G/C balance, and a Tm-reliability warning for MGB/LNA/ZEN-type probes.
- Optional `reference_amplicon`: locates the oligos, checks orientation, amplicon length and GC,
  probe position and primer/probe overlap.
- Fully documented default configuration (`data/default_config.yaml`); user files are merged over
  it and unknown keys are rejected.
- Verdict model PASS / WARN / FAIL / INCOMPLETE where missing evidence is never a PASS, and process
  exit codes (0 / 10 / 20 / 30; 64 invalid input).
- Outputs: self-contained `report.html` (Jinja2 + inline Plotly, no external requests),
  `results.json` (schema version 1), `results.xlsx`. Every record carries a timestamp, the tool
  version, a SHA-256 hash of the inputs, and the required validation/QMS statements.
- CLI: `run`, `validate`, `init`, `--version`.
- Example assay (CDC 2019-nCoV N1) with a documented verification record, and an example
  configuration override.
- Test suite (93 tests), ruff configuration, GitHub Actions workflow (ruff + pytest), `--run-live`
  marker infrastructure for future live NCBI tests.

### Known limitations
- Full runs (without `--qc-only`) end as INCOMPLETE by design, because the remote analyses do not
  exist yet.
- Structure detection depends on the evaluation temperature (see the report's limitations).
- The CI workflow has not yet run on GitHub; it is untested until the first push.
