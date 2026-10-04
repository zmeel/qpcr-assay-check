---
type: Session
title: "v1.1.1 to v1.2.0 released; v1.3.0 step 1 (several oligos per role, named oligos, assay settings)"
description: "Session log of 2026-09-24."
tags: [session]
session_date: 2026-09-24
session_label: "2026-09-24"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-24: v1.1.1 to v1.2.0 released; v1.3.0 step 1 (several oligos per role, named oligos, assay settings)

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
