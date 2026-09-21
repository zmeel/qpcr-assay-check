# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release is tagged `vX.Y.Z`.

## [Unreleased]

Planned: v0.3.0 re-alignment and amplicon pairing; v0.4.0 taxonomy,
organism list, inclusivity and exclusivity; v1.0.0 run history, yearly diff, Docker, documentation.

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
