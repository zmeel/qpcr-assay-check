# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release is tagged `vX.Y.Z`.

## [Unreleased]

Planned: v0.2.0 remote BLAST backend; v0.3.0 re-alignment and amplicon pairing; v0.4.0 taxonomy,
organism list, inclusivity and exclusivity; v1.0.0 run history, yearly diff, Docker, documentation.

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
