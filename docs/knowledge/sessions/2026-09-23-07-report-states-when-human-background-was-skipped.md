---
type: Session
title: "Report states when human background was skipped"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Report states when human background was skipped

- The user ran a full live `run` with a per-assay `exclusivity_organisms` list (Chlamydia
  trachomatis, Influenza A virus): 3 searches (target, human background, exclusivity). It ran for
  over 1.5 h, the exclusivity search (txid813 OR txid11320) still running at the time; timing not
  yet reported back. Explained that searches run sequentially and progress lines need `-v`.
- User asked how to skip the human background: `search.background_taxids: []` in a `--config`
  file. That previously dropped the tier silently, so added: a plan warning when 9606 is not in
  `background_taxids`, and a rationale line + specificity-section note in the report when no
  non-target search covered 9606. Verdict unchanged. `ruff check .` clean, 343 tests pass.
- Live report (v1.0.0, CDC N1, target + exclusivity only, human skipped) confirmed: the human
  background line appears; the species-grouping fix works (Influenza A 49 sites = 15 warning + 34
  minor = taxonomy breakdown sum). Fixed from that report: stale "planned for v0.4.0" scope text,
  and inclusivity now states years with records but no sampled hit (2020: 47,129) as not assessed.
- **Found: the Variant summary (the PRIMER_PROBE_RAPPORT replacement) is always empty on real
  runs.** `specificity/assess.py` only builds sites for `off_target_tiers`, so no `tier ==
  "target"` site ever reaches `build_variant_summary`; the section is hidden. The tests
  constructed target sites by hand. Fixed with the user's choice "A": `assess_target_sites`
  assesses every target-tier hit (partials fetched/re-aligned, cached), fragments grouped per
  record. 348 tests pass. **Not yet seen live**: the next full run should show the section; check
  the `-v` log line "Variant summary: N target-tier site(s) for forward, M partial" to see how
  many fetches SARS-CoV-2 costs, and record it in docs/ARCHITECTURE.md.
- Second live run with the variant fix (v1.0.0 + PR #12): section now appears, but every target
  hit is a perfect match (5000/5000 forward and probe, 4999/5000 reverse), 0 partial hits, 2,106
  complete fragments / 5,862 excluded. Cause: BLAST's top 5000 by score among ~9 M records. The
  user chose: state the bias whenever the target hit list is full (variant section, xlsx Summary,
  inclusivity rationale), fix the fragment exclusion wording and "<0.1%", and stop underlining the
  probe's 3' end. Done; 353 tests pass.
- **User priority (2026-09-23): variant analysis is the most important part of the tool, it must
  be as exhaustive as possible, and many targets are bacterial species with far more than 5000
  records.** Findings while designing: (1) core_nt excludes WGS (draft) genomes, where most
  bacterial assemblies live, so even an unsaturated core_nt search misses most bacterial data;
  (2) whether the BLAST URL API can search the WGS database with an ENTREZ_QUERY/organism
  restriction is unverified (the BLAST FAQ describes Entrez limiting for non-WGS databases only).
  Options put to the user: partitioned remote BLAST (exhaustive over core_nt only, many searches)
  vs streaming NCBI Datasets genome downloads with a local scan for the amplicon region (exhaustive
  over all assemblies, but needs the "remote NCBI only" hard rule relaxed). **Decision: both**
  (Option 2 for exhaustive runs, Option 1 / the current method kept for quick checks), as v1.1.0.
  Budget questions (bandwidth/time/disk on the NAS) not answered yet: design every limit as a
  config setting. Order: verification step first (smoke-test additions the user runs locally),
  then implementation.
- Verification step written: `scripts/probe_variant_sources.py` (writes `probe_out/probe_report.json`).
  Datasets endpoints/parameters taken from NCBI's published OpenAPI spec
  (raw.githubusercontent.com/ncbi/datasets/master/datasets.openapi.yaml, API v2; reachable from the
  sandbox, api.ncbi.nlm.nih.gov itself is not): `/genome/taxon/{taxons}/dataset_report`
  (page_size max 1000, `page_token`, `total_count`, `filters.assembly_version` default `current`),
  `/genome/accession/{accessions}/download` (max 100 accessions, `include_annotation_type=GENOME_FASTA`,
  `hydrated=DATA_REPORT_ONLY` gives `fetch.txt`), API key as `api-key` header. The spec states no rate
  limit; the probe throttles to 2 requests/s and records 429s and rate headers. Also probes: deep
  random ESearch `retstart`, EFetch `rettype=acc`, BLAST restricted to a 100-accession ENTREZ_QUERY
  (coverage and leaks), BLAST `DATABASE=wgs` with a species ENTREZ_QUERY.
- Probe run by the user (2026-09-23): everything worked except E4 (script bug: the query window
  was past the end of a 7,500 bp plasmid record; fixed to bases 1-300, needs a rerun). Results in
  docs/ARCHITECTURE.md "Verified for the v1.1.0 design". Key numbers: Datasets rate limit header
  10/s with key; 1 Mb genome = 312 KB zipped in 0.6 s; GCA/GCF pairs both listed (de-duplicate);
  assemblies (current, not atypical): C. trachomatis 713, N. gonorrhoeae 53,386, S. pneumoniae
  96,853, M. tuberculosis 16,451, E. coli 492,216. BLAST with 100 [ACCN] terms: 100/100 found,
  43 leaks (filter back to the list). Deep ESearch retstart (3.57 M) works.
- User approved: budget 20,000 assemblies per run (newest first), first target C. trachomatis.
- **Implemented v1.1.0 exhaustive variant analysis (Option 2)**: `variants/` package
  (datasets.py client via the shared NcbiHttp with a new throttled `datasets` service and
  `api-key` header; locate.py seed locator; store.py resumable region store; exhaustive.py
  collect/assess/inclusivity; models.py coverage), wired into `run` (cli.py) and `evaluate`
  (pipeline.py); report + xlsx coverage and first/last release dates. Falls back to BLAST hits
  with a rationale note when no amplicon/assemblies/Datasets error. 364 tests pass (fake Datasets
  server in tests/fake_datasets.py, incl. a CLI end-to-end run). NOT yet run live.
- Live C. trachomatis run (user's cryptic-plasmid assay): 357/357 assemblies processed, 76 with
  the region, 281 not found (see ARCHITECTURE.md). User asked for three changes, all done:
  plasmid split of "not found" (with automatic re-scan of old not-found entries), variant tables
  in words instead of critical/warning, inclusivity title. 367 tests pass. Next live run should
  show ~281 re-downloads, and the report's "Recognised as plasmid" examples must be checked to
  confirm the description rule.
- Second live C. trachomatis run: 2 minutes, 281 re-downloads, 0 failures. The plasmid split did
  NOT show: the 76 'found' entries had no plasmid info (not rescanned), so target_on_plasmid was
  unknown and the split was hidden. Fixed: every entry without plasmid info is rescanned once;
  the split counts are shown whenever recorded. Also: inclusivity for the exhaustive source now
  labels columns 'Assemblies' / 'With region' and explains the gap (e.g. 2021: 154 assemblies,
  0 with region). 369 tests pass. Next live run: ~76 re-downloads.
- Third live run: plasmid split works (281 without a labelled plasmid, 0 with plasmid but no
  region; plasmid descriptions genuine). Report wording now says "labelled as a plasmid".
- History diff of variants done (emerging / newly assessed / no longer seen; WARN on a new
  variant with a primer 3'-end mismatch or 2+ mismatches). 371 tests pass.
- Option 1 done: `variants.source: blast_partitioned` (partitioned BLAST over Nucleotide
  records). 376 tests pass incl. a CLI end-to-end run against a fake NCBI. NOT yet run live:
  suggested first live test is CDC N1 with `nucleotide_query: "25000:32000[SLEN]"` and a small
  `blast_max_records_per_run` (e.g. 300 = 3 searches).
- First live partitioned run: 300/300 newest records without a BLAST hit (likely not yet in
  core_nt); fixed with a direct EFetch scan of records without a hit; old 'not found' entries are
  rescanned once. Variant section now shows its coverage even with zero sites. 379 tests pass.
  Needs one more live run (same config: expect ~300 re-checks, BLAST results from cache).
- Second live partitioned run: 286/300 found, all by direct scan (0 by BLAST): forward 78.3%
  one mismatch (pos 11), probe 99.7% one mismatch (pos 3), reverse 96.9% perfect -- the variants
  the BLAST top-5000 (100% perfect) never showed. User asked for 3 changes, all done: direct scan
  first for records <= 200 kb (BLAST only for longer ones), N-masked regions/sites reported as
  masked, wording ('records', 'record end'). 381 tests pass.
- Third live partitioned run (store kept, 600 records): 582 found by direct scan, 2 hidden by N
  (QB007216.1, QB015174.1), 18 not found (OZ5582xx; the 14 earlier ones were not re-checked since
  the store was kept). Fixed from that report: remaining 'assemblies'/'contig' wording for
  Nucleotide records (inclusivity title and column, gap note, history table, xlsx), and history no
  longer lists "99% -> 99%" lines when only more records were assessed (they stay in the table).
  382 tests pass.
- v1.1.0 closed: CHANGELOG release section, version 1.1.0 in pyproject/README. The annotated tag
  `v1.1.0` is created by the user on main after merging (tag pushes are blocked here, HTTP 403).
  User pushed the tag from their code-server (SSH key there); verified: annotated `v1.1.0` on
  main's PR #15 merge commit.
- Checked the 'not found' examples live (NCBI reachable from this session when the user asked to try again;
  eutils was refused on the first attempt): OZ558241.1 is a complete SARS-CoV-2 genome (29,870 nt) with one N run
  27317-28460 over N1 (~28287-28358); the other nine examples the same (+-15 nt). Not a missing
  region: wholly hidden by N, which v1.1.0's N-tolerant seeds cannot see.
- v1.1.1 (user go-ahead): the reference sequence 1,000 nt on each side of the amplicon (from
  `target.accession`, fetched lazily, cached as `<store>.context.json`) places a wholly masked
  region; >= half N in the expected window -> masked. `context_checked` on stored 'not found'
  entries; those from v1.1.0 are rescanned once (for C. trachomatis Datasets: the 281 not found
  are downloaded once more). Verified on the real OZ558241.1/OZ558247.1 vs NC_045512.2, both
  strands. 387 tests pass. Next: user reruns N1 partitioned (expect the 18 as hidden by N) and,
  optionally, C. trachomatis; then merge and tag v1.1.1.
- User asked for comparable tools (none found combining our scope; SCREENED closest) and for
  improvement ideas: written up in docs/FEATURE_IDEAS.md (7 ideas, recommended first: panel-level
  escape detection and scheduled runs with alerts). None started; waiting for the go-ahead.
- (earlier) Next: user runs a C. trachomatis assay live (needs `ncbi.cache_dir` inside the Docker mount so
  the region store persists). Option 1 (partitioned BLAST for non-assembly targets) not started.
  Not yet done: history diff "new variants since the previous run" (first/last release dates are
  in; a diff against the previous run's variant rows is still to do).
- **Earlier proposal (superseded by the above), not approved:** unbiased variant/inclusivity sampling for targets that
  fill the hit list (e.g. several smaller target searches restricted by submission date or other
  Entrez filters, each under the cap). Check current NCBI docs on what ENTREZ_QUERY supports
  before designing. Also open: make the 5-nt 3'-end window configurable or tie it to
  `primer_site.*.min_clean_3prime_nt` (currently fixed at 5 in code and report text).
- Open: ask the user for the exclusivity search's submitted/finished times from `jobs.json` and
  record the measured duration in `docs/ARCHITECTURE.md`.

# Related

* [Variant analysis from every genome assembly](../decisions/2026-09-23-exhaustive-variant-analysis.md)
