# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release is tagged `vX.Y.Z`.

## [Unreleased]

Planned: v0.4.0 taxonomy, organism list, inclusivity and exclusivity; v1.0.0 run history, yearly
diff, Docker, documentation.

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
