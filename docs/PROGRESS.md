# Progress log

Read this alongside `docs/SPEC.md` (authoritative spec) and `docs/ARCHITECTURE.md` (design and
verified NCBI facts) at the start of every session. Newest entry first.

## 2026-09-25 (continued) — Enterovirus assay; taxa excluded from the target

- The user supplied an in-house enterovirus RT-qPCR (two forward primers, degenerate reverse
  and MGB probe, 74 nt fragment; exclusivity: rhinovirus and parechovirus). Oligos checked
  against the fragment (all place; F2 differs at 2 positions). Added as
  docs/examples/enterovirus_realt.yaml.
- Live: the name "rhinovirus" resolves to genus Enterovirus (12059); rhinoviruses are the
  species 3428501/3428503/3428504 plus 169066 (Human rhinovirus sp.) and 364 small unclassified
  taxa (556 records). ESearch and BLAST both honour Entrez NOT (docs/ARCHITECTURE.md).
- User chose option (b): `target.exclude_taxids`. Excluded taxa are searched as near
  neighbours (the user asked that rhinoviruses are checked, not skipped: they are, as
  off-target). Target records: 117,193 in total; 13,796 near-complete genomes
  (6500:8500[SLEN], the example's filter).
- The user started the first enterovirus run (after rebuilding the image; the first attempt
  used an old image without exclude_taxids). Results pending.
- Panel-level escape detection built at the user's request (FEATURE_IDEAS #1): `panel`
  command; panel file = name + assay files; reads the assays' region stores (no NCBI traffic),
  judges each genome per assay by its best copy (new `stored_calls`, shared with the variant
  analysis via `placements`/`open_store`), classifies per genome (every/some/no target,
  undetermined), per year; panel.html/.xlsx/.json; exit 10 if any genome is detected by no
  target. Refuses assays with different targets, exclusions or variant sources. 447 tests pass.
  Not yet run live: needs two assays for the same target with stored regions.
- Live: the enterovirus target search (RID BC6V27N6016) stayed WAITING for over 70 min, and
  restarting only resumed the same RID. Added `ncbi.resubmit_after_minutes` (90) and
  `--resubmit` on run/search; a resumed search is resubmitted at most once per run. 451 tests.
- First enterovirus run (with --resubmit; the new RID was READY in 1 min; all 4 searches READY
  in ~1 min each). Target exclusion confirmed live: the target Nucleotide list and its 1,646
  records with the region hold no rhinovirus. Rhinoviruses (near neighbours): reverse primer
  and probe bind perfectly (e.g. Rhinovirus B KF879883.1, Human rhinovirus sp. PZ504194.1), the
  forward primers do not (F1 2 relevant alignments, closest RV-C 2 mismatches, 4 clean 3' nt;
  forward hit lists not saturated): no product predicted in rhinovirus, parechovirus or human.
  Verdict FAIL comes from critical primer SITES (severity primer_site_critical), not products.
- Variant analysis, 2,000 of 13,796 near-complete genomes: 1,646 with the region, 67.4% with a
  detectable copy. Forward: F1 52.9% / F2 30.1% / none 282 (mostly 262 Poliovirus 2 records of
  one Ugandan 2022 series, UGA_22_*, with F2 at 3 mismatches; plus Enterovirus G, porcine).
  Reverse 84.6%: 121 records with a mismatch 3 nt from the 3' end (example OZ287066.1, isolate
  AUS-EVD68: EV-D68; 1,877 EV-D68 near-complete genomes are in the list); EV-G, SVDV others.
  Probe 99.7%. Region not found 352: mostly animal enteroviruses (EV-E/F/G, SVDV), often
  "polyprotein gene, complete cds" records that may not include the 5' UTR.
- User: human enteroviruses only. Example assay now also excludes (by taxid, checked live)
  the animal species E-L, SVDV (12075, inside EV-B), Rhinovirus NAT001 and 27 unclassified
  taxa whose NCBI name names an animal host (incl. simian/chimpanzee); 41 taxids. Left in
  (host unclear): "Mammalian enterovirus" (MAG), "Enterovirus mbel", "WUHARV Enterovirus".
  Live: 13,066 near-complete records (was 13,796). New exclusions = new region store: the
  first 2,000 records are scanned again on the next run.
- The user asked for a reviewing subagent: a read-only review of v1.3.0..HEAD found 8 points;
  7 confirmed and fixed (panel NOT_FOUND counted as escape; exclusions outside the target not
  checked; resubmission bypassed the confirmation; panel filter/datasets checks; accession
  version; shared client). Not a bug: "panel cache root ignores assay settings" (assay
  settings cannot contain ncbi). Also found: two runner tests mutated the session-scoped cfg
  fixture (now monkeypatched). 460 tests pass.
- Enterovirus, human-only target (41 exclusions), 4,000 of 13,066 records: ancestry check passed;
  no rhinovirus among 304 predicted near-neighbour products (they are EV-G, SVDV, porcine EVs,
  simian EV-J): the assay amplifies animal enteroviruses, which now count as off-target FAIL.
  To decide with the user: separate "must not detect" (rhinovirus) from "out of scope" (animal).
  71.7% with a detectable copy; reverse 79.8% (EV-D68: 606 records, 17.3%, one mismatch 3 nt
  from the 3' end); forward none 299; probe 99.9%.
- The user asked for an advisor subagent (senior molecular biologist, big-data analysis). Its
  review (sources given where verified, rest labelled opinion) recommends: graded role-specific
  mismatch classes (MGB probes stricter, primer-pair combinations, IUPAC codes in the genome as
  uncertain), haplotype collapsing with study provenance and per-type reporting, collection
  date/country/technology stratification, copy-aware reporting, variant templates for the wet
  lab, and panel refinements (interpretation rule; 'not found' by assembly level; one
  homopolymer rule per panel). Added to FEATURE_IDEAS as proposals; not started.
- Advisor on an "out of scope" list: split is right; out-of-scope findings as INFO in an "also
  detects" list; one list with a role and a reason per taxon; for must-not-detect taxa base
  the verdict on products (a lone primer site WARN). User: build both. Done: `target.taxa`
  (roles must_not_detect | out_of_scope, reason), out_of_scope search tier (INFO only),
  `primer_site_critical_no_product: WARN` (also in the exclusivity table); exclude_taxids moved
  into taxa on loading; enterovirus example converted (5 rhinovirus taxa must_not_detect,
  36 animal taxa out_of_scope, each with a reason). Same NOT query, so the target search and
  the region store are reused. Not done: per-taxon severity override (use must_not_detect to
  make a taxon count). 465 tests pass.
- The user supplied the Stadhouders 2010 full text; the advisor checked it (summary in
  FEATURE_IDEAS #9). Corrections to its abstract-based review: the mild class (A-C, C-A, G-T,
  T-G) was 0.99-1.91 Ct at the terminal position with Taq on DNA; the severe class includes
  G-G (8.29-9.09 Ct). EV-D68 reverse-primer variant: C-A (primer-template) at position -3,
  a type not tested at that position; "acceptable" for Taq + MMLV one-step mixes but "avoid in
  the reverse primer" with rTth, so it depends on the lab's RT-PCR mix. Wet-lab test still
  advised. NG poly-A bulges: not covered by the paper.

## 2026-09-25 — v1.3.0 confirmed live and released

- Live NG run with `fb7ede5` (budget 15,000, overnight): 2026 1,170, 2025 3,083 and 2024 10,747
  scanned; 12,735 of the 15,000 were the rescans of genomes stored with at most 5 copies, 2,265
  were new. No genome is left with capped copies; at most 11 copies per genome. 31 downloads
  failed (retried on the next run); ChunkedEncodingError retries recovered.
- 29,520 of 51,572 assemblies assessed (29,480 multi-copy; best copy not the first found:
  4,725). With a detectable copy: 24,870 (84.2%) strict, 28,795 (97.5%) if homopolymer bulges
  are tolerated; 4,650 escapes (strict). Coverage: NG-F 98.8% (341 none, mostly one 6-mismatch
  variant), NG-R 84.4% (4,617 none), NG-P1 96.0%, NG-P2 3.9% (all "only"), probe none 44.
  Reverse inclusivity 70/78/86% (2026/2025/2024), 91% for 2023 (58 assessed).
- Released as v1.3.0 (CHANGELOG section, version 1.3.0, README status and version table,
  FEATURE_IDEAS #8 done). About 22,000 older assemblies remain for later runs. The user merges
  and tags.
- v1.3.0 merged (PR #19) and tagged by the user (verified: annotated, on main's merge commit
  f03c5be). Next: the user picks the next feature from docs/FEATURE_IDEAS.md.

## 2026-09-24 — v1.1.1 to v1.2.0 released; v1.3.0 step 1 (several oligos per role, named oligos, assay settings)

- v1.1.1 confirmed live (2026-09-24, N1 partitioned, store kept): 882 records assessed; 'not found'
  18 -> 0; hidden by N 31 (the 18 rechecked OZ5582xx plus new OZ5556xx records, and records with
  N inside an oligo site); 851 in the inclusivity tables (851 + 31 = 882). Ready to merge and tag.
- v1.1.1 merged and tagged by the user (annotated, on main's PR #16 merge commit; verified).
- Report change requested before new features: the "Closest off-target sites" list is grouped
  into off-target variants (oligo + exact alignment), with site/record counts, tiers and
  organisms; new "Off-target variants" workbook sheet. 389 tests pass. Not yet seen live.
- Accessions and taxonomy IDs link to NCBI (report and workbook); URL forms /nuccore/<acc> (later /nucleotide/, see below),
  /datasets/genome/<GCx_>/ and Taxonomy Browser ?id= checked live (HTTP 200). The self-contained
  test now allows plain <a href> links to www.ncbi.nlm.nih.gov only. 392 tests pass.
- Live: the user's browser looped endlessly on NCBI's reCAPTCHA "Checking your browser" page for
  the /nuccore/ links. My first URL check had only looked at HTTP 200, not the page content.
  Checked the content: /nuccore/<acc> returned the challenge for 3 of 3 accessions, /nucleotide/
  served the record page for all 3; datasets genome and Taxonomy Browser pages were not
  challenged. Links switched to /nucleotide/. NCBI can change this protection at any time.
- Confirmed live (N1 rerun, 2026-09-24): 78 /nucleotide/ links and 19 taxonomy links, no
  /nuccore/; three sampled links open the record page. Grouped off-target table: 14 rows for the
  49 Influenza A sites. Released as v1.2.0 (CHANGELOG section, version bump); the user merges and
  tags. Next: the user picks features from docs/FEATURE_IDEAS.md.
- v1.2.0 merged and tagged by the user (verified: annotated, on main's PR #17 merge commit).
- Proposal for several oligos per role + oligo names (FEATURE_IDEAS #8), with the user's answers:
  same mix; same-dye probes are alternatives, different dyes = different regions. The user's
  N. gonorrhoeae two-probe assay checked against its fragment and live on three RefSeq genomes
  (multi-copy target, NG-P2 exact in NZ_CP078119.1); added as
  docs/examples/neisseria_gonorrhoeae_two_probes.yaml in the planned v1.3.0 format.
- CLAUDE.md rule changed at the user's request: user-supplied example assays are added as given,
  with provenance stated, instead of requiring a check against the source publication.
- The user added the fragment for NG-P2 (79 nt): NG-P2 exact, forward exact; reverse site has a
  poly-T of 9 (vs 7) and one substitution. The NG-P2 copy in NZ_CP078119.1 has poly-T 10 and no
  substitution. Both fragments are in the example as `reference_amplicons` (planned field).
- v1.2.0 docs PR merged by the user. v1.3.0 step 1 implemented (user go-ahead): `Oligo` and
  `ReferenceAmplicon` models; roles accept a sequence, a named oligo or a list; unique names,
  `_v<n>` reserved; probe reporter/quencher/modifications per probe with assay-level defaults;
  `Assay.role_of(label)` replaces label parsing (make_candidate takes the role). QC per oligo,
  dimers across every pair in the mix, Tm spread per role; amplicon QC places each oligo in its
  best-fitting reference, WARN for an alternative that fits none and for a reference without a
  primer pair. Variant analysis and sampled inclusivity keep the best alternative per record;
  variant rows carry `oligo_name`. NG example: QC places NG-P1 in fragment 1 and NG-P2 in fragment
  2 exactly; fragment 2 has no reverse primer site within 2 mismatches (poly-T), reported as WARN.
  406 tests pass. Known: first run after upgrade reports an assay change once (stored form).
- First live NG two-probe run (user, blast_partitioned with the N1 config's
  nucleotide_query 25000:32000[SLEN], so only 25-32 kb records): names flow through QC, BLAST and
  variant tables (probe rows show NG-P1 / NG-P2). Bug found and fixed: the intended-target
  finding parsed labels, so named oligos read as "no perfect hit for forward, probe, reverse";
  it now sums per oligo name and flags a role only when none of its oligos has a perfect hit.
  Exhaustive inclusivity said "sampled"; now "assessed". Findings for the user: N. meningitidis
  CP171264.1 gives a perfect 76 bp product; NG-R has a 1-base gap (poly-A/T length) in 8 of 25
  records; NG-P2 seen with 1 mismatch in 2 records.
- The user found the separate config files confusing (the N1 nucleotide_query leaked into the
  NG run). Built as proposed and approved: assay-file `settings:` (config.yaml structure, sections
  reaction/oligo/thresholds/search/specificity/organisms/inclusivity/variants; ncbi and report
  rejected as lab-wide), precedence defaults < --config < assay. Report shows the assay's
  settings; inputs hash uses the effective config only (run budgets still excluded). Examples
  updated. 416 tests pass.
- Live: uncommenting only the background_taxids line put it under variants: (error "Extra
  inputs are not permitted"). Examples now offer it as one line to uncomment
  (`search: {background_taxids: []}`; an explicit [9606] would override a lab-wide --config),
  and config errors name the section a misplaced key belongs to.
- Live NG datasets run (2026-09-24): ~17,000 assemblies scanned over 3 years (3011 + 6141 +
  7880 of 10848) before a genome download ended mid-transfer (requests ChunkedEncodingError,
  "Response ended prematurely"), which the HTTP layer did not treat as transient: the run
  crashed. Fixed: ChunkedEncodingError/ContentDecodingError are retried with backoff and become
  an NcbiError (the batch is then counted as failed and retried next run); a damaged zip member
  is an NcbiError too. The region store kept every scanned assembly, so a rerun resumes.
- Rerun with max_assemblies_per_run 5000 looked like a restart ("20 / 5000"), but it resumed:
  the first two years (3011 + 6141, stored) were skipped silently and the third year, cut at
  10848 by the old 20000 budget and crashed at 7880, still had over 5000 unscanned. Reproduced
  with a simulated crash + smaller budget (resume correct). The log now says per year: listed,
  already stored, to scan in this run, and when the per-run maximum is reached.
- User asked (while the NG run continued) for a template assay.yaml with all options explained:
  `examples/assay_template.yaml` (also packaged; `init` writes it instead of the short template).
  Settings options are commented out under active section names (empty sections now read as
  empty); tests: shipped template valid, uncommenting all options == built-in defaults, no option
  missing, init writes the same file. 423 tests pass.
- The user preferred the compact layout of my earlier proposal (flow-style oligos, settings with
  only what differs) over the long commented template: template and NG example rewritten that
  way; every other option moved to a commented reference block at the end of the template
  (tests parse that block: all options present, defaults exact).
- Live NG datasets run finished (22,255 of 51,572 assemblies assessed; 2024 alone lists 41,117):
  region found in all, 22,248 multi-copy; reverse inclusivity 45-70% on the first-found copy.
  NG-P1 perfect 93.8%, NG-P2 covers its lineage. Reverse variants are mostly poly-A/T length.
- v1.3.0 step 2 implemented (user go-ahead): best-binding copy per genome over every stored copy
  and every alternative oligo; CopyCoverage (copies, best-not-first, coverage per oligo/only,
  none per role, probe channels with variants.probe_channels any|all, escapes); homopolymer
  run-length variants aligned as a bulge and labelled; further reference amplicons tried when the
  first finds nothing (store keyed by the first, not-found rechecked once); MAX_LOCI_KEPT 20.
  429 tests pass. Next: user reruns NG (stored regions reused; the new analysis applies to all
  22,255 stored genomes), then v1.3.0 release.
- Live NG run after step 2 (27,255 of 51,572 assessed): 84.6% with a detectable copy, 4,201
  escapes; NG-R covers 84.7%, mostly lost to poly-A 7->8/9 bulges. 12,735 genomes had been stored
  with at most 5 copies. The user chose: (1) a setting for bulges, strict by default, both counts
  shown; (2) download the capped genomes again.
- Done: `variants.homopolymer_bulges_detectable` (default false); report/workbook show both
  counts. Found genomes with fewer stored copies than min(copies found, 20) now need a rescan
  (once; a genome with more than 20 copies is not rescanned every run); the per-year log counts
  only complete entries as "already stored". 434 tests pass. Next: user reruns NG (the ~12,735
  rescans use the per-run budget), then the v1.3.0 release.

## 2026-09-23 — Report states when human background was skipped

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

## 2026-09-23 — Live smoke test finds and fixes a real exclusivity undercount bug

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

## 2026-09-23 — Per-assay exclusivity panels: `assay.yaml` gets its own organism list

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

## 2026-09-23 — Also: all outstanding work merged to `main`; working there from now on

The user asked why the previous three commits weren't visible on `main` (this session had been
developing on its assigned per-session branch, `claude/awesome-sagan-j8mncl`, per this
environment's own branch-isolation convention) and then asked to merge everything and work on
`main` going forward. Opened and merged PR #10 for the one remaining unmerged commit (the two
before it, PRs #8/#9, had already been merged); fast-forwarded the local checkout to `main`. All
further commits in this session go directly to `main` (still asking before each push, per
`CLAUDE.md`), not the per-session branch.

## 2026-09-23 — Pathogen-panel taxonomy IDs resolved live and merged into the doc

The user ran `scripts/resolve_pathogen_panel_taxids.py` locally and pasted back its console
output (137 names). Merged the results into `docs/clinical_pathogen_panels.md`'s "Taxonomy ID"
column, replacing every `pending` placeholder (131 table rows) with the resolved value(s) for that
row's pathogen name(s), via a small positional-replacement script rather than manual editing —
which caught a real bug in the process: a first draft of the replacement list was silently missing
one entry (*Serratia marcescens*, section 1), which a per-section length assertion (26/20/13/19/
10/8/6/8/6/10/4/1) caught before it could quietly shift every later cell in the document by one row.
That mismatch happened to also produce a confusing red herring while debugging it: an intermediate
`grep`/Python count of `"| pending |"` occurrences flip-flopped between 130 and 131 across separate
tool calls on an apparently-unchanged file (confirmed unchanged by a stable md5sum) -- eventually
traced to misreading which assertion actually failed (`len(replacements) == 131`, not the file's
own pending-count), not a real file-race; the fix was to build and validate the replacement list
per-section rather than as one flat, hand-counted list.

Five results came back genuinely unresolved or ambiguous (*Mycoplasma hominis*, *Borrelia
burgdorferi*, *Candida parapsilosis* unresolved -- surprising for such common species and flagged
as worth a follow-up live check, distinct from *Mycoplasma pneumoniae* and *Mycobacterium
chelonae*, whose non-resolution was already expected/documented from prior work; bare genus
*Proteus* ambiguous), plus three cases where two names intended as synonyms (RSV, adenovirus,
parvovirus B19) resolved to two *different* taxonomy IDs -- none of these five situations were
guessed past: the doc's new "Notes on this resolution pass" section records exactly what is and
is not settled, and the table cells themselves say `unresolved`/`ambiguous`/`not queried` rather
than a number wherever that is the honest state, per this project's own "never guess a taxonomy
ID" rule.

## 2026-09-23 — Taxonomy IDs for the pathogen-panel doc: a script, not typed-in numbers

The user asked to add NCBI taxonomy IDs to `docs/clinical_pathogen_panels.md`. Confirmed this
sandbox still cannot reach NCBI (`curl` to `eutils.ncbi.nlm.nih.gov` through the proxy returns
HTTP 403, same as every prior session), so taxids could only come from memory -- which this
project's own rules treat the same way as a primer/probe sequence or an NCBI parameter: never
typed in unverified (`CLAUDE.md`: "NEVER invent... NCBI parameters... never guessed";
`taxonomy/resolve.py`: "never picks a UID out of an ambiguous result: that would be guessing").
A wrong digit in a taxonomy ID is exactly the kind of silent, hard-to-catch error that rule exists
to prevent.

Instead of guessing, added `scripts/resolve_pathogen_panel_taxids.py`: resolves all 137 unique
pathogen names from the doc (some listed under two names -- a current name and a still-common
synonym, e.g. the *Mycoplasma*/*Mycoplasmoides pneumoniae* rename already found live not to
resolve via the `[All Names]` fallback -- so both get tried) through the exact same live Entrez
Taxonomy lookup (`taxonomy/resolve.py`'s `resolve_name`, `[Scientific Name]` then `[All Names]`)
this project already uses for its own exclusivity organism list, using the same
`NcbiHttp`/`Eutils`/`Cache` construction as `scripts/smoke_test.py`. Confirmed the script fails
fast and cleanly without `NCBI_EMAIL` set, before any network call. Added a "Taxonomy ID" column
to every table in the doc, currently `pending` for all 131 rows, and a note at the top explaining
why and how to fill it in (run the script locally, paste back `pathogen_taxid_report.json`).

Not yet done: the script has not been run live, so no taxid in the doc is filled in yet -- waiting
on the user to run it and paste back the report.

## 2026-09-23 — Added a reference doc: pathogens by syndromic real-time PCR panel

The user asked for a compiled list of human pathogens typically detected by real-time PCR, grouped
into syndromic panels, as a doc in the repo. Added `docs/clinical_pathogen_panels.md`: twelve
panels (respiratory, GI, meningitis/encephalitis, bloodstream infection/BCID, STI, vaginitis,
tick-borne, congenital/perinatal, mycobacterial/TB, skin and soft tissue, the now-standard
SARS-CoV-2/flu/RSV combo, and group A strep), each a table of pathogen/type/notes, compiled from
general public knowledge of how commercial syndromic multiplex panels (BioFire FilmArray, Cepheid
Xpert, GenMark ePlex, Seegene Allplex, QIAstat-Dx, and similar) are organised -- without claiming to
reproduce any single product's exact validated target list.

Labelled explicitly as reference material, not verified against NCBI Taxonomy or any package
insert the way this project's own primer/probe sequences must be (`CLAUDE.md`'s "never invent"
rule is about oligo sequences and NCBI parameters specifically, not general pathogen-panel
knowledge) -- distinct in kind from `data/clinical_organisms.yaml`, which is small, deliberately
non-authoritative, and directly wired into the exclusivity search. This new doc is not wired into
the tool at all; it is a broader planning aid for curating that list, linked from README's
Exclusivity section. No code changed.

## 2026-09-22 — Variant summary report added, requested after comparing against a lab's own workflow

The user shared their own pre-existing Excel/VBA workbook (a manual primer/probe conservation
workflow for a *Blastocystis* qPCR assay: BLAST web UI → SAM export → BioEdit alignment →
column-masking → a hand-built "primer/probe report" tab lumping identical sequence variants with
a count and percentage) and asked for a detailed comparison against this project. That comparison
surfaced one real capability gap worth acting on immediately: the workbook's own
`PRIMER_PROBE_RAPPORT` tab -- exactly the kind of report the user built this project to replace --
had no equivalent here, and the user asked for it back, generalised from per-region to the whole
fragment (lump identical forward+probe+reverse combinations, not just one oligo at a time).

Implemented as `specificity/variants.py` (`build_variant_summary`), wired into `pipeline.py`
whenever `specificity` is supplied, with no new required section or verdict -- it is purely a
different view of evidence the specificity assessment already scored (`SiteResult.q_aln`/`s_aln`
carries the exact alignment string needed; grouping by `(q_aln, s_aln)` lumps identical variants
without needing any new NCBI call), the same design already used for `taxonomy/rollup.py`'s
species/genus/family aggregation. Two variant tables: per-oligo (forward/probe/reverse, from the
target tier's own sites) and per-fragment (the target tier's own predicted amplicons, keyed by the
combined forward+probe+reverse variant, only when all three sites were fully re-aligned -- not a
`blast_partial_worst_case` estimate). New report.html section (reuses the existing `aln_html`
Jinja filter for the alignment display, so it looks like the rest of the report rather than the
workbook's plain dot-diff notation) and two new xlsx sheets ("Oligo variants", "Fragment
variants"). 10 new unit tests (`tests/test_variants.py`, in the style of `tests/test_pairing.py`'s
directly-constructed `SiteResult`/`AmpliconResult` fixtures) plus a manual end-to-end smoke check
(constructed a `SpecificityResult` with real target-tier sites/amplicons, rendered both
`report.html` and `results.xlsx`, inspected the actual output) since none of the existing
`render_report` tests exercised target-tier data and so would not have caught a template error in
the new section. 321 tests total (up from 311), `ruff check`/`ruff format --check` both clean.

Not yet done: this is a code-only session (no NCBI access here) -- the new section has not been
seen on a real live run. Also not yet decided: whether/when to tag this as a point release: SPEC.md
scopes the roadmap through v1.0.0 (already tagged) and this is an addition the user asked for
directly in conversation, not one of the originally planned phases -- left for the user to decide
when to version and tag it, per CLAUDE.md's git-tagging convention (annotated tags per phase).

## 2026-09-22 — Exclusivity/target fix confirmed live; history/diff confirmed on real data

The user rebuilt the Docker image with the previous entry's fix and re-ran the exact same full
`run` (same cache, so no new NCBI calls were needed for the unaffected tiers). Both new pieces of
this phase's work — the exclusivity/target-taxid fix and the history/diff feature itself — are now
confirmed working correctly together against real data, in the same report:

- Predicted off-target products dropped from 500 to 0 (that section flipped to `PASS`).
- The "Changes since the previous run" section correctly attributed this to the fix: "6028
  off-target site(s) no longer found" and "500 predicted off-target product(s) no longer found" —
  matching, almost exactly, the bogus counts from the buggy run. The exclusivity table's row for
  SARS-CoV-2 now reads "assay's own intended target — excluded from this search", as designed.
- The run is still `FAIL`, but now for a real reason: documented homology between the CDC N1
  primers and the human genome, found independently by both the `background` tier and the
  `exclusivity` tier (since "Homo sapiens" is *also* separately listed in the packaged organism
  list — the same organism searched twice, for two different reasons; redundant, not wrong).
- The diff also showed 43 "new" minor-severity Influenza A sites, worth a moment's thought before
  concluding they were fine: removing SARS-CoV-2 from the exclusivity tier's taxid list shifted
  which of the remaining ~38 organisms share a `max_taxids_per_search` chunk, which shifted which
  hits rank inside that chunk's own `max_sites_per_query` cap, surfacing hits that were previously
  crowded out. A correct, expected side effect of the fix, not a new issue.

Updated `docs/ARCHITECTURE.md` (added a "retry, with the fix applied" verified section) and
`CHANGELOG.md` (Known limitations: the fix is now confirmed live, not just unit/CLI-tested; the
history/diff feature has now been checked against one real two-run pair, not only the constructed
test world). No code changes this round — this was purely closing the verification loop on the
previous fix.

## 2026-09-22 — First full live run finds and fixes a real exclusivity bug

The user ran a full `run` through the Docker image against real NCBI data (CDC N1 example,
packaged organism list, background tier included) and shared `report.html`. Overall verdict was
`FAIL` — and reading through the rationale found a genuine bug, not a config problem: the packaged
clinical organism list includes "Severe acute respiratory syndrome coronavirus 2" (reasonable for
a respiratory panel), which is also the CDC N1 example's own intended target
(`taxid 2697049`). The exclusivity tier had no exclusion for the assay's own target taxid, so it
searched for and found the assay's own perfect match against itself, and reported every one of
those matches as a critical off-target site or predicted product: 4025 critical primer sites, 2000
critical probe sites, 343 "likely detected" products, all at 0 mismatches (`+0.0 °C vs perfect`)
against records titled "Severe acute respiratory syndrome coronavirus 2" — not a specificity
problem at all, just the assay correctly finding its own target, mislabelled as evidence of
cross-reactivity. This alone flipped the overall verdict from what should have been closer to a
real (background-tier) `WARN` into a misleading `FAIL`.

Confirmed by checking `data/clinical_organisms.yaml` (line 56: SARS-CoV-2 is indeed in the list)
and the report's own search-taxids table (`2697049` present among the exclusivity tier's searched
taxids), then reading `specificity/assess.py` to confirm a secondary, smaller puzzle along the
way: why the "assessed" count (2837) exceeded the documented `max_sites_per_query` default (2000)
— confirmed the cap is applied per search chunk (each BLAST submission), not once per
tier-aggregate query, so two exclusivity chunk-searches (the ~39-organism list split by
`max_taxids_per_search`) can each independently cap near 2000, explaining the observed number
exactly. Not a bug, just a code-reading exercise before writing it into the docs as fact rather
than a guess.

Fixed: `search/execute.py` now filters `assay.target.taxid` out of the exclusivity tier's resolved
taxids before they reach the search planner. Kept the organism-list row visible per the project's
own "never present a sample as the full population" rule (never silently drop an entry) — added
`ExclusivityRow.is_target`, wired through `pipeline.py`, `report/templates/report.html.j2`, and
`report/xlsx.py` so the row reads "assay's own intended target — excluded from this search" rather
than a confusingly-identical "0 sites, resolved" that would look the same as a genuinely-clean
result. Added regression tests reproducing the exact live-run scenario: a unit test in
`tests/test_exclusivity.py` (`build_exclusivity()` with `target_taxid` set, including a
defence-in-depth check that evidence for that taxid is never counted even if somehow present), and
a full CLI end-to-end test in `tests/test_run_full.py` using the constructed world with the
target's own taxid also listed in the organism list — confirms no exclusivity-tier site or
amplicon exists for the target's taxid after the fix. 311 tests total (up from 308), ruff clean.

Not yet done: a fresh full live run with the fix applied, to confirm the corrected verdict looks
right end to end (only checked against the constructed test world and live-run evidence from
*before* the fix so far).

## 2026-09-22 — Docker image built and run successfully by the user

The user built the image on their Synology NAS (Docker running as root) and ran it: `--version`
and `--help` worked immediately. `init` failed on the first try with a `PermissionError` writing
into the bind-mounted `/work` directory -- the image's default user is non-root (uid 1000), which
does not own a directory created/owned by root on the host. Gave two fixes (`--user
"$(id -u):$(id -g)"` on `docker run`, or `chown` the host directory to uid 1000 first); the user
used `--user` and it worked. `run --qc-only` then produced the exact same verdict and rationale
message as the plain-virtualenv install this was first checked against in-sandbox, confirming the
image installs and runs the real package correctly end to end for the offline path.

Updated README.md (Docker section now shows `--user` in every example, explains why, and states
what's confirmed vs. not — a full NCBI network run through the container specifically hasn't been
separately exercised, only through the plain-virtualenv install), docs/ARCHITECTURE.md (moved
Docker from "still unverified" to a new "Verified for v1.0.0" section), and CHANGELOG.md (Known
limitations updated to describe the uid-1000 permission behavior rather than "not built at all").

One thing to note for next time: the first copy-pasted `docker run` command with a trailing `\`
line continuation failed with "docker: invalid reference format" in the user's terminal --
resolved by giving the same command as one line instead. Multi-line backslash-continued shell
commands are apparently not safe to assume will paste correctly into every terminal; prefer
single-line commands (or a documented heredoc, as used for the git tag commands earlier in this
session) when giving copy-paste instructions to run remotely, since round-tripping a fix through
chat is slow.

## 2026-09-22 — v1.0.0 started: run history + diff implemented; Docker written but unverified

User said "Start v1.0.0". Before writing code, checked in on one consequential design decision
(the "history" section's scope): confirmed making it required, like every other section, so a
brand-new assay's first run is honestly `INCOMPLETE` (nothing to compare against yet) rather than
letting history be informational-only and let a first run reach a clean PASS. Recommended and
chosen: required, INCOMPLETE on first run.

Built `history/` (`store.py` finds the previous run by scanning `results/<slug>/*/results.json`
for the most recent `generated_at`, no separate index; `diff.py` compares sections/sites/amplicons/
inclusivity by natural key, not run-local IDs). Wired into `pipeline.evaluate()` (new `history`
field, its own required section, `PLANNED_SECTIONS` removed since it was history's only remaining
entry) and `cli.py` (`find_previous_run()` called before `evaluate()`). Added a "Changes since the
previous run" report section and a "History" xlsx sheet. 13 new tests (natural-key matching unit
tests plus a full two-run CLI end-to-end scenario); found and fixed a real bug along the way in
`report/html.py`'s `pending` filter (`verdict is None` no longer means "not evaluated" now that a
genuinely-evaluated INCOMPLETE section exists) that broke two existing tests, and moved the
"oligos were/were not sent to NCBI" disclosure out of the now-sometimes-empty pending block so it
always renders.

**Near-miss worth remembering**: `.gitignore` had a stale, unscoped `history/` rule from early
project scaffolding (apparently meant for a separate run-history output directory that this
phase's "files, no separate index" design never ended up needing) that was silently ignoring the
entire new `src/qpcr_assay_check/history/` source package the moment it was created. Caught by
running `git status` before the first commit of this phase (a `git status --short --ignored`
specifically, prompted by habit rather than suspicion) and fixed immediately -- nothing was lost,
but it would have quietly excluded the whole feature from every future commit if it had gone
unnoticed. Worth a standing lesson: check `git status --ignored` after creating a new top-level
package directory, especially one whose name might collide with an older, unrelated `.gitignore`
entry.

Wrote `Dockerfile`/`.dockerignore` and attempted to build/run the image in this sandbox. Docker's
CLI and daemon binaries are present but the daemon isn't running by default; started it manually,
then hit the sandbox's outbound-proxy restriction pulling `python:3.12-slim` from Docker Hub's CDN
(`production.cloudfront.docker.com`, HTTP 403). Followed the environment's own documented
workaround for `docker build` exactly (installed `/root/.ccr/ca-bundle.crt` into the system trust
store, passed `HTTPS_PROXY`/`HTTP_PROXY` to the `dockerd` process) and retried both `docker pull`
and `docker build` -- identical failure both times, concluded to be a genuine restriction on this
CDN through the proxy rather than a fixable misconfiguration, so stopped rather than trying further
workarounds (matching the "report, do not work around" guidance for this class of proxy failure).
Reverted the system CA change and stopped the daemon afterward to leave the sandbox as found.
Validated what could be validated instead: `pip install .` into a clean virtualenv (the same
command the Dockerfile's build stage runs) followed by `init` → `validate` → `run --qc-only`
through the installed console-script entry point, end to end, correct output files and exit code.
The Dockerfile itself is therefore unverified as a built image and should be built and run by the
user (or in CI) before being relied on.

Bumped version to 1.0.0 is NOT yet done (deliberately -- CHANGELOG.md's `[Unreleased]` section
holds this phase's work; tagging v1.0.0 is expected to wait for documentation polish, the other
open item in SPEC.md's v1.0.0 phase, and/or explicit user confirmation the Docker image was built
and works).

## 2026-09-22 — v0.4.0 tagged; phase 4b's ESummary date lookup verified live

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

## 2026-09-22 — Phase 4b implemented: inclusivity via target-tier reuse + ESummary date-bucketing

Built inclusivity (SPEC.md step 9) on the redesign forced by the previous session's live finding
(BLAST cannot reliably combine `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter):
instead of a separate, date-windowed BLAST search, inclusivity reuses the "target" tier search
every run already makes, and buckets its own hits into years afterwards via a new `esummary()`
E-utility client method plus `inclusivity/dates.py` (which re-indexes ESummary's UID-keyed JSON
response by each docsum's own `accessionversion`/`caption` field, not by input order). Per year:
sample deterministically (evenly spread, one per accession, capped by `sample_per_window`),
re-align over the full oligo length (`inclusivity/sites.py`, reusing `specificity/sites.py`'s
candidate/window machinery), and aggregate perfect/1-mismatch/2+-mismatch/3'-mismatch counts plus
a per-position mismatch profile (`inclusivity/aggregate.py`). Population size per year comes from
an independent ESearch count, reported next to (never instead of) the sample size. Wired through
`pipeline.py` (new `inclusivity` field on `RunResult`, its own `SectionResult`, rationale lines),
`cli.py` (`keep_tiers` now always includes `"target"`; `compute_inclusivity()` call wrapped in
`try/except NcbiError` so a date-lookup failure degrades gracefully rather than discarding an
otherwise-complete run, matching the `taxonomy_breakdown` fix from phase 4a), the HTML report
(new per-oligo, per-year table) and the xlsx writer (new Inclusivity sheet). 295 tests pass
(`pytest -m "not live"`), `ruff check .` clean.

**Honesty points carried through deliberately**: inclusivity's sample is not a controlled random
sample (it depends on where each year's records fall in BLAST's own hit-list ranking, which is
capped) — stated explicitly in `InclusivityResult.limitations` on every result, not just in docs.
A year with zero sampled hits is reported as zero, not omitted. No target-tier search at all (or
no assay target taxid) gives INCOMPLETE, never a false PASS.

**Still unverified, flagged for the next live smoke test** (`scripts/smoke_test.py` step
`08b_esummary_inclusivity_dates`, added but not yet run): the real nuccore ESummary docsum date
field name (the code tries several candidates from memory of the docs, not an observed response),
and whether the accession re-indexing logic holds for more than one accession in a real response
(only checked against the constructed test world so far). Do not treat inclusivity's date
attribution as confirmed until that step comes back `ok: true` with a sane `esummary_docsum_keys`.

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
