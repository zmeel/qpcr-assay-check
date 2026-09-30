# Progress log

Read this alongside `docs/SPEC.md` (authoritative spec) and `docs/ARCHITECTURE.md` (design and
verified NCBI facts) at the start of every session. Newest entry first.

## 2026-09-30 — Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan

- Step 8, Legionella (user, 2026-09-29 22:24 to 2026-09-30 08:54, 11,911 assemblies in one run, about 3.2 s each):
  - Region found 7,341 (2,912 of them detectable from parts), cut by a contig end 4,433,
    not found 104, hidden by N 7, related only 26. So 7,345 genomes (62%) have no whole copy
    (the pre-overhaul run: 6,064 with every copy cut); the rise is drafts whose fragment is not
    assembled at all but whose flank sits at a contig end: now "cut", before "not found".
    2,850 of the 2,912 from parts are all-perfect L. pneumophila drafts.
  - Whole fragment 2023-2026: 95.4% detectable of 2,697 (No flags). Complete genomes 93.3%
    (25 escapes: L. anisa, L. micdadei, F. dumoffii, L. steigerwaltii, L. quinlivanii: genus
    probe LEGgenus likely failure). L. longbeachae complete genomes now detectable (VIC
    perfect); the pre-overhaul run's 49 L. longbeachae failures were misplaced sites.
  - Channels: genus (VIC) 95.8% of 4,337 judged, 7,444 undetermined, 130 drafts without the
    region; L. pneumophila (FAM) 99.8% of 3,982, signal in 2 of 757 other genomes
    (GCF_026191185.1, GCF_026191275.1): Review.
  - Fixed from it: the summary called the channel's Review "a single release year below 80%".
- Enterovirus example in the loci/channels format, with context_accession NC_001612.1
  (RefSeq Enterovirus A; checked live 2026-09-30 against the RefSeq complete genomes: best fit,
  68/74 anchored, identity 0.959; its flanks anchor 150-220 bases in species B, 16-40 in C/D).
- Wiki pages written (user, 2026-09-30) in docs/wiki/ (Home, How it works, Finding the target in
  a genome, Judging primer and probe sites, Specificity search, Data storage and cache, Limits
  and validation, _Sidebar): the session's GitHub access does not reach the wiki repository, so
  the user publishes them.
- Enterovirus after several runs (user, report 2026-09-30T07:44Z): 12,000 of 13,109 records;
  whole fragment 2023-2026 90.8% detectable (Review); region not found 1,089. Of 10 examples,
  4 are CDS-only records (no 5' UTR: correctly not found) and 6 are EV-C105/C117/HEV-C with
  the region at identity 0.78-0.82 but no 16-mer in common (reverse primer mismatches at
  -4..-2: likely escapes, hidden as "not found").
- Advisor (2026-09-30, measured): 12-base fallback where no copy under the rule, >= 2 blocks in
  the fragment + rule (c); store only passing candidates; masked search stays at 16; classify
  "present, not locatable" (flanks, no copy) with a worst-case inclusivity figure. Built
  (store schema 4, ScanSettings.fallback_k 12 / fallback_min_blocks 2, Candidate.fallback,
  coverage.found_by_fallback / not_located). An extra EV-C reference fragment would find the
  same copies with 16-base seeds (advisor measured 36-72 anchored): the assay-level fix once
  the fallback has shown the clade.
- Code review of the fallback (3 findings, fixed with tests that fail on the old code): the scan
  judged fallback candidates and the trigger with the default rule, not the configured one
  (now: chains with >= 2 fragment blocks stored, rule (c) at assessment; trigger = no candidate
  with masked_below anchored bases, a scan setting); a failed candidate at a fallback copy's
  place counted as a related region beside it (now not, and fallback chains never).
- Intermittent test failure found: tests/test_variants_exhaustive.py plasmid fixture seeded
  chromosomes with hash(acc) % 1000 (per-process); seeds 11/12 recreate AMP's own spacer
  (1 run in ~125). Fixed seeds.
- Comparison with SymbioSeas/assayval (user, 2026-09-30): local BLAST per genome with word
  size 4, count thresholds, gapless hits only; its blind-spot figures for word size 7 reproduced
  exactly (17-mer 2 mm: 10/136; 13-mer 1 mm: 1/13). Word-size check: NCBI's URL API documents
  blastn WORD_SIZE 7, 11, 15 only (https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html,
  read 2026-09-30), so the remote search cannot go below 7. Blind spot for the user's oligos at
  word 7 (uniform placements, sites with the last 5 nt clean): 1 mismatch never missed; 2
  mismatches up to 7.4% (17-mers NG-F, Entero-P); 3 mismatches 15-33% for 17-19-mers, 1-6% for
  21-24-mers, 0 for LEGpneu (35 nt). Affects only the specificity search (off-target sites);
  the genome scan does not use BLAST. Proposed mitigation (not built): re-align the partner
  primer and the probe inside a window around every relevant primer site, so a site hidden
  from BLAST is still found when the other primer's site is visible.
- Advisor on the fix (2026-09-30): from real fixtures, lambda 1.374 / K 0.711 (+1/-3), search
  space 2.6e10-9.6e11: at E 1000 a raw score of 13-15 is needed, so the E-value, not the word
  size, limits short oligos (model: 17-nt with 1 internal mismatch hidden in the larger-space
  tiers). Contradicted in part by the live Neisseria run (a 17-nt NG-F site on N. meningitidis
  with 1 mismatch and 9 clean 3' nt, best score 13, was reported). Done: the limitation text now
  names the E-value; smoke-test step 11 (--expect-sweep) measures E 1e3/1e4/1e5 for NG-F. Next,
  after the user's run: choose EXPECT, then build the partner-primer scan, probe re-alignment
  in every product and a reference-fragment BLAST per off-target tier.
- Wet-lab comparison (user supplied Otwell et al. 2025 and its supplementary Tables 1-2): 132
  DNA templates graded with oligo/grade.py vs measured Ct. Before: detectable 26 (none >= +3 Ct),
  likely failure 52 (7 without shift, all 4 mismatches with 3 at the 5' end). Built on the
  user's decision: R3/R8 count within the 3'-most 16 nt; R3b for mismatches beyond (alone
  tolerated, with one inside at least at risk); 3 inside, none in the last 5 -> likely failure;
  the 4-adjacent exception only without further mismatches. After: detectable 35 (one undetected
  at 50 copies, +1.1 Ct at high copies), likely failure 9 (all >= +3 Ct or undetected), at risk
  88. Probe deletions stay R5 indeterminate. Analysis script and data stay out of the repo;
  table in docs/MISMATCH_CLASSES.md section 11.
- Smoke-test E-value sweep (user run, 2026-09-30, --quick --expect-sweep; all steps ok): NG-F
  (17 nt) vs N. meningitidis, eff_space 8.1e8 (advisor assumed 2.6e10-9.6e11), lambda 1.374,
  K 0.711 (confirmed). E 1e3: 638 hits, min score 10; 1e4: 3,554, min 8; 1e5: 4,999 (list nearly
  full), min 7. ceil(ln(K*space/E)/lambda) predicts 10/8/7 exactly. Human tier not measured
  (`sh scripts/run_smoke.sh --quick --expect-sweep --human`). Mycoplasma pneumoniae unresolved
  is by design (step 03 checks the old name; the list uses Mycoplasmoides pneumoniae).
- Built on the user's "Build 2 and 3": score floor per tier and oligo from the report's own
  statistics (specificity/reach.py, "Reported down to" column, INFO finding, new limitation
  text); partner scan for unpaired off-target primer sites plus probe re-alignment in every
  off-target product without probe signal (specificity/scan.py, source `scanned`,
  `specificity.partner_scan_max_windows` 1000, INCOMPLETE beyond). EXPECT stays 1000. Not
  built: a reference-fragment BLAST per off-target tier (products of which BLAST reported
  neither primer remain unfound; noted in the limitation).
- User request (2026-09-30): ΔTm/ΔG next to each variant's class (built; information only,
  specificity/duplex.site_duplex cached per variant) and collection date next to release year
  (built; sources verified live 2026-09-30: Datasets assembly_info.biosample.collection_date,
  e.g. GCF_022869645.1 "missing"; nuccore ESummary subtype/subname, e.g. LC951483.1 collected
  2021-12-03, created 2026/09/26). Dates live in <store>.dates.json, filled while listing.
  Next: user runs enterovirus, then Neisseria and Legionella, then the v2 release.
- Code review of the 4 new commits (2026-09-30) and fixes on the user's "Make fixes as
  proposed": probe re-alignment adds warning+ sites only; scan de-duplication per tier; invalid
  search statistics -> none; one fetch budget for partner windows and products; cut tiers not
  scanned; no-accession sites counted; 'scanned' label; limitation text per scan setting;
  full-list caveat on the score floor; "no usable date"; R3b: 5+ mismatches beyond -16 at_risk
  (Otwell comparison re-run: totals unchanged).
- Enterovirus live run 2 with the new code (user, 2026-09-30; 4,000 of 13,109 records):
  whole fragment 2023-2026 90.0% detectable (Review); fallback found 38 records (EV-C105/C109,
  mostly not detected); collection axis: 276 of 3,538 collected before 2017, the 2025 release
  year's at-risk bulk (222) was collected in 2022; probe 1-mismatch variant ΔTm -9.0 °C.
  Bug found: the partner scan took a 21-N stretch of PX731700.1 for a perfect reverse primer
  site (1,506-bp product); fixed (unobserved bases are mismatches in the scan). Score floors
  all "not known": no search statistics were read from this run's BLAST results although the
  smoke test's (same runner, JSON2_S) had them; the user checks the cached results.
- Cache check (user, scripts/check_blast_stats.sh, 2026-09-30): every multi-query search
  (enterovirus, Legionella) has stat with eff_space 0 and hsp_len 0, kappa/lambda/db_len
  given. Fixed: the space is derived from the reported alignments (from_hits), or query length
  x db_len (upper_bound). A rerun re-parses the cached results: no new BLAST searches needed.
- Not done yet: the user's live runs with this code (enterovirus, then Neisseria and
  Legionella), then the v2 release. Everything above is pushed (PR #47).

## 2026-09-29 — Overhaul round 2: a generic assay model (advisor); user decisions

- User: everything on the table; no run history in the report; the current cache may go, but
  the tool keeps an incremental cache (only new assemblies downloaded; a locus store is
  discarded only when the locus definition or method changes; BLAST/Taxonomy caches as now).
  One GENERIC tool for (1) one F, one R, one probe; (2) several primers/probes on one region
  (Neisseria); (3) several primers/probes for different regions or target taxa (Legionella,
  true multiplexes).
- Advisor plan: assay = oligos -> loci (primers, probes, reference fragments, optional context
  accession, scan taxon, source) -> channels (one per reporter; probes; target taxon; taxa
  roles). Old files load as one locus + one channel per reporter. Chain locator with context
  (seed step 2, signed coordinates, all candidates kept); store v2 per (assay, locus) with a
  schema/key header (mismatch = discard, re-download); assess through anchor-mapped windows,
  F x R products per locus, detection per channel; lineage membership per genome and channel;
  inclusivity per channel over its own target, complete in-scope exclusivity per channel (e.g.
  the pneumophila channel on other Legionella), BLAST tiers per oligo as today. One outcome enum
  per copy (WHOLE / CUT / MASKED; related = listed, not a copy) and per genome x channel
  (DETECTED / NOT_DETECTED / UNDETERMINED(site_rule | incomplete | possibly_unassembled) /
  NO_LOCUS; non-targets SILENT / SIGNAL / UNDETERMINED). Copy rule: (a) M_amp >= 32, or
  (b) context-anchored M_ctx >= 32 on a side, co-linear, or (c) identity >= 0.75 with M_amp >= 16;
  (b) awaits the context rerun. Build order 1-8 (model; outcome function; chain locator; store
  v2 + sequence_reports; assess v2; report per channel; deletions; live re-downloads).
- User decisions: LEGgenus reporter VIC, LEGpneu FAM; the genus channel targets the genus
  Legionella (taxid choice 444 vs 445 to confirm: NCBI files L. dumoffii and L. gormanii under
  Fluoribacter 461); NO_LOCUS in a complete genome = NOT_DETECTED (possible deletion); the
  panel command and the sampled blast_hits inclusivity source may be removed (SPEC amendment);
  out-of-scope taxa in a channel's scan are shown as information only.

- Step 1 built (user: genus channel target 444): `Locus` and `Channel` in models.py; old files
  derive one locus + one channel per reporter; validation of names, roles, dyes; the locus
  context accession feeds the reference context; a warning for assays with several loci (only
  the first is analysed until step 5). Legionella draft in the new format; templates and SPEC
  amended (loci/channels; history, panel and sampled BLAST-hit inclusivity dropped, removal in
  step 7). tests/test_assay_loci.py.

- Step 2 built: `GenomeOutcome` + `genome_outcome` (variants/exhaustive.py) used by
  copy_coverage, _level_coverage, the sets for the whole-fragment years, and panel.member_states;
  existing tests unchanged (counts pinned), tests/test_genome_outcome.py for the precedence.

- Step 3 built: variants/chain.py (Reference, Candidate, CopyRule, is_copy, locate; two-pass
  context search: step 32 genome-wide, step 8 near a hit). Synthetic tests (tests/test_chain.py):
  plain, 60-nt insertion, minus strand, cut at the contig start, chance seed, two references,
  identity rule, divergent fragment between conserved flanks, one flank (cut vs not), N over the
  fragment, N-runs next to a copy. Timing 2.6 s / 4 Mb genome with context, 1.7 s without. Rule
  (b)'s threshold still awaits the Legionella context rerun (legionella3).

- Legionella context rerun (legionella3) had no context: the user's reference fragment is not
  in NC_002942.5 base for base (the old exact-match rule). Without it, identity cannot separate
  real divergent copies (0.66-0.72, genus probe 0-1 mm; one at 0.658) from look-alike regions
  (0.60-0.66, 9-13 mm under every oligo). Built: chain.context_from takes the flanks around the
  fragment's best whole copy in the context record (rule (a)); the measurement script uses it
  and records the copy it used. Rerun as legionella4.

- Step 4 built: variants/genomestore.py (ScanSettings, store_key/store_file, GenomeStore with
  header check and set-aside, GenomeRecord/StoredCopy, scan_genome, sequence_stats);
  DatasetsClient.sequence_roles + SequenceRole; fake Datasets serves sequence reports. Verified
  live here (curl, 2026-09-29; docs/ARCHITECTURE.md): sequence_reports fields incl. Plasmid,
  paging, one assembly per request. The old store and its rescan code stay until step 5 wires
  the new one in (deletion then / in step 7). Open for step 5: when to fetch sequence reports
  (one request per assembly; e.g. only for assemblies with more than one sequence).
- Measurement: legionella4 (context now from the fragment's best copy in NC_002942.5) running.
  Wrappers mount the checkout's src/ (no image rebuild for the scripts).

- Step 5a/5b built: exhaustive.py collects into GenomeStore (collect/_process/_download with
  halving retries; sequence roles only for >1 sequence), locus_references (context via
  context_from, cached in genomes/context-*.json; fetch failure raises), open_genome_store,
  as_items adapter (copy rule applied; related / related-beside lists), assess(copies_decided)
  with StoredLocus.offset_at (anchor placement) and anchored parts; partitioned.py on the new
  store (BLAST hits relocated with the chain locator, shifted to record coordinates).
  chain.locate: blocks may chain across the whole reference span (flanks around an N-run);
  N-tolerant fallback (masked candidates). Old rescan tests removed; new tests in
  tests/test_variants_step5.py (a test fails when anchor placement is switched off).
  Old variants/*.jsonl stores are no longer read (can be deleted by the user).

- Step 5c built: GenomeCall.channel_state (best state per channel over copies, parts included),
  channel_results/_membership/_genome_channel_state (exhaustive.py), ChannelResult in
  coverage.channel_results; taxonomy.resolve.ancestors (cached lineage ids; outside_target uses
  it); the CLI passes it as ancestors_of. Tests: one channel with complete vs draft genomes
  without the locus; genus + species channels (target, signal, silent); unknown lineages.
  Not yet: report and workbook tables per channel (step 6); per-locus analysis beyond the
  first locus.

- Step 6 built: channels_shown / channel_verdict (exhaustive.py); pipeline folds channel
  statuses into the inclusivity verdict (worst, never better; rationale lines "Channel X: ...");
  summary rows "Detection per channel: <name> (<dye>)"; report table (id "channels", in the
  inclusivity section; replaces the old "Probe channels" counts when shown); workbook sheet
  "Channels"; AmpliconResult.channels (pairing._channels) shown in the product table and the
  "Predicted products" sheet. Tests in tests/test_variants_step5.py and tests/test_pairing.py.

- Step 7 built (deletions, four commits):
  - 7a: run history and the comparison with the previous run removed (history package,
    pipeline's previous_run, the "history" section, summary column, workbook sheet).
  - 7b: the `panel` command removed (panel.py, report/panel.py, its tests).
  - 7c: the old region store (variants/store.py is now only StoredLocus/StoredAssembly, the
    adapter view of store v2), the rescans and the seed-cluster locator (locate.find_loci and
    friends, the implied-offset fallback) removed; scripts/measure_locator.py removed,
    tests/test_measure_borderline.py kept the borderline cases on the chain locator.
  - 7d: the sampled blast_hits inclusivity removed (variants.source blast_hits,
    inclusivity.sample_per_window, inclusivity/dates.py and sites.py, assess_target_sites, the
    "full target hit list" bias note, smoke-test step 08b). When the exhaustive analysis cannot
    run, inclusivity is "Not assessed: <reason>" instead of a sampled fallback. The target BLAST
    tier still runs (its perfect full-length counts feed the specificity findings) but its hits
    are no longer kept.
- legionella4 (context from NC_002942.5; 134 genomes; 55 borderline candidates, 28 found only
  through context, not listed yet). With the tool's rule (a 32 / b 32 / c 0.75 with 16):
  - look-alike regions: identity 0.600-0.658, M 16-17, length unchanged, context 0 on both
    sides, 8-13 mismatches under every oligo (the same region in many species, L. pneumophila
    included): none is a copy. Context separates them cleanly; identity alone does not (a real
    copy with a 71-nt deletion sits at 0.658 too).
  - real divergent copies in other Legionellaceae: identity 0.658-0.727, length -71 to +45,
    context left 40-792, genus probe 0-1 mm: all copies through rule (b) (smallest context 40).
  - L. pneumophila copies cut by a contig end (M 24-26): copies through (b) and/or (c).
  - copies cut at the contig start in other species (identity 0.83-0.95, M 16-18, context 0):
    copies through (c).
  - one miss: GCF_900114725.1 (L. jamestowniensis) copy cut 25 nt from the contig start,
    identity 0.745, M 19, no context: not a copy (just under 0.75); the genome has another
    (cut) copy through (b).
  - Legionella sp. 27cVA30 (GCF_024160945.1): the copy has 680 context bases and F 0 mm but
    R 9 and genus probe 9 mm; a copy through (b), so the genus channel will call it not
    detected (a finding about the assay, not a locator error).
  - the 28 context-only candidates: 27 cut by a contig end, one flank anchored (64-992 bases,
    chance chains reach at most 18), the fragment itself beyond the contig end (0-15 nt of it on
    the contig): contig breaks inside rRNA-operon repeats, in pairs where the left and the right
    flank of one locus sit on two contigs. Copies through (b) as cut; they carry no oligo site,
    do not count in n_copies (whole copies only) and turn "not found" into "cut by a contig end"
    (both undetermined in a draft). None is in a complete genome. One whole candidate
    (GCA_902168255.1, 336 left-flank bases, nothing of the fragment) is not a copy.
  - Defaults kept (32 / 32 / 0.75 / 16).
- Step 8 prepared: scripts/run_assay.sh (a full run in Docker, in the background, with the
  checkout's src/ mounted; log in work/runs/NAME.log) and scripts/run_summary.py (counts,
  verdicts and accessions from results.json, no sequences; written to
  work/runs/NAME-summary.json when the run ends). tests/test_run_summary.py.
- Code review of the whole overhaul (7b202e4^..HEAD): three bugs, all fixed with regression
  tests that fail on the old code: a masked copy dropped by a weak candidate at the same place
  (chain._best_per_place; now chain.copies_of), min_context_bases / the masked fallback not
  following the config at scan time (every chain kept; ScanSettings.masked_below fixed at 32),
  and a gene name over 60 characters breaking the default locus. Store SCHEMA 3: the
  Neisseria run started on schema 2 has to start again.
- Step 8, first live run: Neisseria (user, report 2026-09-29T19:16Z, schema 3 code):
  - 51,583 assemblies listed (2024 alone 41,117); 20,000 scanned in this run (2026 and 2025
    complete, 2024 partly, 20 from 2023 because 20 failed downloads do not use the budget).
  - Region found 19,970, cut 23, related regions only 7, not found 0, hidden by N 0; 19,691
    genomes with more than one copy (median 9 in complete genomes, at most 10).
  - Inclusivity 2023-2026: 91.9% detectable of 16,906 (3,064 undetermined, 1,623 of them
    copies possibly unassembled): Review (< 95%), Incomplete until every genome is scanned.
    By level: Complete 96.2% (6 escapes of 160), Contig 91.8%.
  - Driver: NG-R's poly-A 7 run; homopolymer length variants in 12,863 genomes, copies
    disagree in 11,457 (sequencing/assembly error likely); strict 77.8% vs 93.0% tolerated
    (genomes with a detectable copy).
  - Specificity: one predicted 76-bp product on CP171264.1 (N. meningitidis), both primers and
    NG-P1 perfect: worth checking that record's identity.
  - Report fixes from it: the "no product is predicted" sentence under a tier with a product;
    the set-aside count (nearly all genomes since schema 3) no longer shown.

## 2026-09-28 (overhaul) — Advisor plan; step 0: measurement script

- Advisor (read-only) on the overhaul of the exhaustive variant analysis. Diagnosis: one number
  (identity to one reference fragment) decides both "is this the target locus" and "how well do
  the oligos bind"; probably also seeds grouped within 20 nt and oligo windows +-15 nt around one
  median offset, which split or misplace copies of species whose spacer length differs by > 20 nt
  (to measure); the outcome precedence is written five times. Plan: chain locator (co-linear
  exact blocks, signed coordinates, no cap), store v2 with a schema header (mismatch = discard
  and re-download, no rescans), all rules at assess time, one genome_outcome(); copy rule
  "anchored bases M >= 32 OR identity >= 0.75" (to measure first). Build order 0-6; the
  per-species reference fragment rejected for now. Seven questions to the user (context
  accession, genus scope, store key, history "method changed", old stores, download schedule,
  from-parts default): not yet answered.
- Step 0 built on the user's request: scripts/measure_locator.py (no change to the tool).
  Prototype chain locator vs the current one on real genomes picked from the region store
  (related, single-seed, organism:..., sample) or named; per candidate M at seed steps 1/2/4,
  signed start/end, length difference, cut/N evidence, identity along the chain, the current
  loci matched (split?), and per oligo the mismatches at the chain vs the current placement; a
  null with shuffled/reversed references; timing; an unverified probe of the Datasets
  sequence-report endpoint. tests/test_measure_script.py (synthetic). ~17 s per 4 Mb genome.
  Next: the user runs it on Legionella, Neisseria and enterovirus and pastes back
  measure_report.json.
- First measurement (user, Legionella, 3 named genomes only: the --group options found no
  store, now an explicit error). Confirms the diagnosis. L. longbeachae GCF_000176095.1: 5 copies,
  each 24 nt shorter than the L. pneumophila fragment; the current locator splits every copy into
  two loci (9 seeds 0.746, 6 seeds 0.619) and so sets them aside; the chain (M 130, identity 0.788)
  places forward 0 mm, reverse 1 mm, genus probe 0 mm, where the current single offset gives the
  forward 13 mm. L. dumoffii GCF_000236165.1: 3 copies, +23/+78/+23 nt, all split; chain: F 0,
  R 1, genus probe 0 (current: up to 10 mm, false escapes). GCF_000586155.1: copies cut before the
  amplicon start sit at -222/-234 (current clamps them to 0 and misplaces every oligo, 7-14 mm);
  chain: reverse 0 mm on the part present. Over the 3 genomes: 8 of 12 copies differ > 20 nt in
  length, 27 of 48 oligo sites worse at the current placement. Chance regions M 16-18 (identity
  0.54-0.60), null max M 16 (9 decoys); whole real copies M >= 114, cut ones M 26-38 (identity 1.0).
  Step 2 seeds lose 2-3 bases vs step 1 at half the time (1.6 s vs 3.2 s per genome). Datasets
  /genome/accession/{acc}/sequence_reports verified live: fields role, assigned_molecule_location_type,
  assembly_unit, chr_name, genbank/refseq_accession, length, sequence_name (a genome with a plasmid
  still to be seen).
- Full measurement runs (user, 2026-09-29). Legionella, 134 genomes (groups related,
  single-seed, anisa, micdadei, longbeachae, dumoffii, sample, named): 191 of 283 copies differ
  > 20 nt in length from the L. pneumophila fragment (median 24, max 78); the current locator
  splits 190 of them; 518 of 1,132 oligo sites have more mismatches at the current placement
  than at the chain's. Genomes with a copy, current vs chain rule: related 0 -> 23 of 25,
  longbeachae 1 -> 25/25, dumoffii 1 -> 10/10, anisa 14 -> 25/25, single-seed 9 -> 10,
  micdadei and sample unchanged; the chain never lost a copy the current locator had. Null max
  M 18 (402 decoys). Neisseria, 75 genomes: no copy differs > 4 nt, none split, 0 of 657 sites
  worse; agreement 74/75; null max M 0 (225 decoys); 98 of 299 copies have M 16-23 and pass
  only by identity >= 0.75 (divergent opa copies), and seeds every 4 nt miss some (min M 0),
  every 2 nt do not. Seconds per genome: Legionella current 0.85 / step 2 1.65; Neisseria
  0.27 / 0.28. Still open before the defaults: the ambiguous candidates (Legionella M 24-31
  with identity < 0.65: 2; M < 24 with identity >= 0.65: 26; Neisseria M < 24 with identity
  >= 0.75: 98), whole or cut by a contig end.
- Borderline candidates (user, scripts/measure_borderline.sh). Neisseria: the 98 are one region
  per genome, the divergent opa copy also in the complete reference GCF_013030075.1 (~1,478,815;
  whole, identity 0.80/0.785, NG-F 6, NG-R 12, NG-P1 1 mm), plus copies cut by a contig end
  (M 16-20, identity 1.0 over the part present). Legionella: L. pneumophila copies cut by a
  contig end (M 24-26, identity 1.0; contigs of 726-1,937 nt); divergent-species copies cut
  before the amplicon start with only the reverse end present (M 16-19, identity 0.83-0.95,
  reverse 1-2 mm); WHOLE regions of uncultured / unnamed Legionellaceae with identity 0.66-0.72
  and M 17-21 where the genus probe matches (0-1 mm) and the reverse 2-3 mm, forward 1-13 mm:
  real copies of the target locus that neither arm of the rule catches; GCF_024160945.1
  (Legionella sp.) M 29, identity 0.62, forward 0 but reverse and genus probe 9 mm. Conclusion:
  for a locus-defined assay the conserved flanks identify the locus and amplicon identity only
  measures divergence. Next: rerun Legionella with the reference context from NC_002942.5
  (L. pneumophila Philadelphia 1, complete, 3,397,754 nt; verified at NCBI 2026-09-29), the
  measurement now records context anchoring per side (M_ctx_left/right).

## 2026-09-28 (end) — Threshold hides divergent Legionella species; next: overhaul with advisor

- Legionella rerun on #30 code: the copy-identity threshold (0.75 vs the L. pneumophila reference
  fragment) set aside real copies of other species as "related regions, not the target" (201
  genomes, e.g. L. longbeachae GCF_000176095.1, L. dumoffii GCF_000236165.1). The L. longbeachae
  (49) and L. dumoffii rows vanished from "Needs attention"; target detection read 95.6% "No
  flags": too optimistic, do not rely on it. Measured live (genomes deleted afterwards): real
  L. longbeachae copies identity 0.74 (9 exact seeds) and 0.63 (6), L. dumoffii 0.59-0.74
  (6 seeds), chance regions 0.57 (1 seed). Minimal fix (not built): a copy when identity >= 0.75
  OR >= 3 exact seeds.
- USER DECISION for the next session: consult the advisor on a total overhaul of the code to
  make the solutions built during development more robust. Deleting the cache and starting over
  (re-downloading every genome) is always allowed if that is best for the tool. Ideas to put to
  the advisor: find copies by homology (several chained seeds) instead of one exact seed; store
  per copy its true offset, contig edge / adjacent N-run and contig lengths, and all copies with
  their identity at scan time; build a reference fragment per species automatically for genus
  assays (e.g. Legionella) from complete genomes; then revisit "possibly unassembled", "detectable
  from parts", the identity threshold and the per-channel probes on that richer data.
- Also to discuss (user): every fix of the past week that could be done better with all data
  downloaded again, among them: region hidden by N (partly via N-tolerant seeds, wholly via the
  reference context, v1.1.1); target on a plasmid judged from FASTA descriptions; copies capped
  at 5 then 20 per genome and rescans (copies_capped, refs_checked, needs_rescan); cut by a contig
  end (contig_break) and its clamped offsets; failed downloads counted unavailable after 2 tries;
  best-binding copy per genome; homopolymer run-length variants and their per-level breakdown;
  "possibly unassembled" (inferred from copy counts, no gap data stored); "detectable from parts";
  the copy-identity threshold and the multi-reference fall-through; per-channel probe sites.

## 2026-09-28 (later) — Legionella; probe channels; judged from parts; copy threshold advice

- First Legionella run (Herpers et al. JCM 2003 41:4815-6, 23S-5S spacer, verified at PubMed):
  complete genomes 78.7% detectable vs contigs 96.0% (species mix); likely failures in complete
  genomes of L. longbeachae (49), L. anisa (121), L. dumoffii/quinlivanii (16), L. micdadei (7):
  for the user to compare with the paper's validation panel. 6,064 of 11,911 assemblies had
  every copy cut by a contig end.
- GCF_000586155.1 (user): all true copies split over contig edges; the tool judged the genome by
  an unrelated region (forward 7 mismatches). Built: every reporter channel on the fragment rows
  (e8074d4) and "judged from parts" (setting variants.judge_from_parts, default undetermined as
  the advisor advised). The locator stores a copy cut before the amplicon start with offset 0;
  parts are placed again from exact k-mers.
- Legionella rerun on #29 (user): 40.6% of the whole-fragment records "judged from parts". The
  user found the name hid the finding (were the oligos perfect?): every site of such a genome is
  perfect or tolerated, so the class is now called "detectable from parts" (setting name kept).
- Code review of PR #29, all fixed with tests: judged-from-parts genomes still counted in the
  per-oligo and channel coverage and per-oligo windows (now left out, percentages on the same
  base); older multi-reference stores never rescanned related-only genomes (now flagged once,
  StoredAssembly.rescan / identity_scanned); an N on a cut copy could make a genome "masked"
  (N sites skipped); panel called related-only genomes "unknown" (now not found); identities
  recomputed every run (now StoredLocus.identity, cache 20k); a real copy hidden by N lost to a
  chance-seed region (masked checked first); wording.
- Copy-similarity threshold built on the user's request (variants.min_copy_identity 0.75,
  locate.amplicon_identity: banded alignment, cached; about 9 ms per new 260-nt region). Still
  to verify: the identity of real enterovirus copies across genotypes (the partitioned source
  uses the threshold too), and the effect on the stored Legionella and Neisseria loci.
- Advisor on a copy-similarity threshold: identity of the region to the reference
  amplicon >= 0.75 (measured: true Legionella copies 0.99-1.00, the unrelated region 0.57,
  random 260-nt windows 0.56 +- 0.02; N. gonorrhoeae divergent opa copy 0.80; single-seed random
  76 nt: 0.4% >= 0.75). n_seeds cannot separate them (both 1). Below the threshold: store and
  list as "related region", never the best copy. Verify on the stored loci (and enterovirus)
  before choosing the default.

## 2026-09-28 — Opa copies unassembled in draft genomes; detection per assembly level

- The user checked GCF_000156755.1 (N. gonorrhoeae 1291, Broad 2009 draft, 175 contigs in 42
  scaffolds, 78,472 N): no opa genes. Verified live: NCBI annotates 0 opa genes (complete
  reference GCF_013030075.1: 11); for 6 reference opa loci both flanks lie on one draft
  scaffold with 1,000–2,200 N between them (genes left as gaps); no exact NG-F/NG-R/NG-P1 site
  in the draft. Its only assembled copy is the divergent opa copy that the complete reference
  also carries (~1,478,815; forward site GTTGGCACATCGCTCCA): a false escape. That combination
  is the top "Needs attention" row (1,278 genomes, 2.5%).
- Advisor: step 1 (built) shows detection per assembly level in the coverage section and the
  levels on every whole-fragment row (report and workbook), so the next run shows whether the
  1,278 are drafts. Step 2 (not built, only if they are): "undetermined: copies possibly
  unassembled" for multi-copy targets (best copy fails, fewer than half the typical copies of
  complete genomes in the run, draft with gaps or truncated copies, no complete genome with the
  same failing pattern; setting variants.multicopy_unassembled; store gap_nt and n_truncated).
  Genome files were downloaded to the scratchpad for the check and deleted afterwards.
- Live run with step 1: detectable Complete Genome 95.9% (297), Chromosome 100% (32), Scaffold
  87.0% (405), Contig 79.0% (50,806). The likely-failure rows of 1,278, 903 and 505 genomes have
  no complete genome (Contig 1,269 / 902 / 499); the at-risk row of 2,481 has 10 (real).
- Step 2 built on the user's request: `mark_unassembled` (variants/exhaustive.py), setting
  `variants.multicopy_unassembled`. Evidence of an incomplete draft is "more than one sequence
  or a copy cut by a contig end", not N gaps (contig-level assemblies have none), so nothing is
  downloaded again. Not yet seen on a live run.

## 2026-09-27 — Summary instead of a verdict; v1.5.0 released; Legionella draft

- Overall verdict replaced by "Summary of this year's check" (user: "the tool is not a test that
  fails or passes"; advisor consulted first). User decisions: a review status (No flags /
  Review / Exceeds limit / Incomplete) in the report, workbook and results.json
  (`overall.review_status`; internal PASS/WARN/FAIL/INCOMPLETE codes kept so older records
  still compare); exit codes unchanged, documented as flag levels; first run = baseline; a
  changed assay or config = "not comparable" (neither holds up the status); QC labels within /
  outside preferred / outside limit, rules worded "preferred 18–30 nt; limit 15–40 nt"; grey
  "No flags"; a reviewer's decision box. SPEC.md amended. Code in `report/summary.py`.
- Two code reviews, all findings fixed with tests: `fragment_verdict` said PASS above a WARN and
  let years outside the window raise the status; summary rows could miss a section's status
  (fallback row per required section, `tests/test_summary.py`); target detection now
  Incomplete while not every listed genome is assessed (unless already below the FAIL limit).
- Live Neisseria run with the summary: rows and numbers correct (79.0% of 49,614 genomes
  2023–2026, below the 80% FAIL limit; oligo design (NG-R poly-A 7) and the N. meningitidis
  product on CP171264.1 exceed limits). The old text wrongly named the 95% review limit for a
  FAIL; now fixed.
- Legionella genus + L. pneumophila (next assay, user): draft
  `docs/examples/legionella_genus_pneumophila.yaml`, placeholder sequences, not runnable.
  Verified live at NCBI Taxonomy: target Legionellaceae 444 (NCBI files L. dumoffii 463 and
  L. gormanii 464 under Fluoribacter 461); exclusivity Coxiella burnetii (777), Rickettsiella
  (59195), Aquicella (254245). The tool has one target per file: a second file (pneumophila
  probe only, target 446) would check the pneumophila channel.
- Releases: PR #22 was merged at 639dd89 before the summary work, which went into PR #23;
  the version bump into PR #24. v1.5.0 tagged by the user on 3813754 (verified on the remote).
- One unexplained test run with 3 failures in tests/test_variants_exhaustive.py (after a
  `ruff format`); not reproduced in 10+ runs by me or the reviewer, CI green.
- Open: Legionella sequences, reporters, reference fragment, annealing temperature, source, and
  the second file; CP171264.1 record check (user); MGB zone display; per-assay "acknowledged"
  note for known design issues; simplification.

## 2026-09-26 — v1.4.0 released; inclusivity on the whole fragment

- v1.4.0 released: PR #20 merged (5b56c3f), tag v1.4.0 set by the user on the merge commit. CI
  runs `ruff format --check` too: run it before every commit.
- Inclusivity status on the whole fragment over the last 3 complete years plus the current one
  (advisor; user decision; PR #21). Live runs on it (Neisseria 79.0% of 49,614; enterovirus
  90.7% of 4,503, 99.4% including at risk, mostly the at-risk poliovirus 2 F2 variant) led to
  the per-year table fixes (same base as the status, window row) in PR #22.

## 2026-09-25 (later) — Second code review of the unreleased changes

- The reviewer subagent reviewed `69b53ab..8e30922`: 11 findings, all verified against the code.
  Fixed with a regression test each: worst-case site KeyError (1), R6 hiding real mismatches (2),
  all-undetermined year at 0 % (3), panel undetermined vs escape (4), ungraded fragment rows shown
  as detectable and `blast_hits` target sites not graded (5), out-of-scope fetch failures and
  "no tier searched" (6), rows that can fail cut after 15 (7), non-existent template attribute
  (8), docs vs code in MISMATCH_CLASSES (9), panel refusing different reason text (11).
- Not changed (10): the inclusivity percentage ignores `homopolymer_bulges_detectable` (bulges
  count as not detectable there), while copy coverage and the fragment table honour it; older
  than this diff. R8 applies to genomes, not to the per-role percentage (by design). Both for the
  recap.
- Pushed (ca32c23..e342037). The user's next live run then crashed while writing report.html:
  `VariantRow` had no `grade_rule`, read by `fragment_outcome` for indeterminate sites (the
  tests used stand-in objects). Fixed, with a test on real rows (fails without the fix).
  Lesson: grouping tests should build real models, not SimpleNamespace stand-ins.
- 495 tests pass, ruff clean. Pushed (d6478c1).
- Live enterovirus run with d6478c1 (all 13,066 records now assessed; 11,687 with the region):
  report renders; 92.3% with a detectable copy, 609 escapes, 294 undetermined (297 probe sites,
  nearly all single MGB-probe mismatches; 1 reverse). Fragment table: 135 combinations need
  attention (30 listed, the tail is only undetermined rows), 96 detectable. Forward: F1 covers
  59.4%, F2 36.7%, none 488. report.html is 5.2 MB: to look at in the recap.
- Correction: the grouped tail of "Needs attention" also holds at-risk rows (by design beyond 30
  rows), not only undetermined ones as first reported to the user.
- User feedback: the whole-fragment table is what the program is for. Oligo columns too narrow,
  Types too wide: site lines now in the header's font size (aligned), header oligos no wrap,
  Types capped at 15rem. MGB probe with 2+ mismatches = likely_failure (user proposal; advisor
  agreed, position-free, expert judgement, unmodified probes unchanged).
- User: everything that makes the report more readable is on the table. Built: Part A of the
  fragment table picks rows by records (5 per outcome, then most frequent) so the 283-genome
  Poliovirus 2 at-risk row is listed; the tail is one row per outcome; oligo numbers after the
  header sequence keep the dots aligned; the Tm chart is inline SVG (Plotly dropped: 4.8 MB of
  the 5.1 MB report).
- User proposed dropping the per-oligo tables; advisor: shrink, don't drop (per-site frequency,
  history traceability, blast_hits coverage, full alignment for sign-off). Built points 1-4:
  fragment table first, compact "Variants per oligo" after it, % per non-perfect site in the
  fragment table, coverage line for blast_hits. Cross-links (point 5) left out for simplicity.
- Live run with 660e57f: report 335 kB, new layout works; per oligo still 30-52 rows (risky
  variants always listed, mostly single records). Built: single-record risky variants one row
  per class. Oligo QC (checks, hairpins/dimers, amplicon) folded just before Methods.
- Inclusivity gains a whole-fragment table per year (genome outcome of the three sites);
  the verdict still uses the per-oligo percentages (open question for the recap: base it on
  the genome outcome instead?).
- Specificity section (advisor): overview per tier on top, Searches one row per tier,
  probe sites INFO by default, RIDs cached, limitation on single-primer products. Not built
  (for the recap): rule c (INCOMPLETE -> INFO when the discriminating primers are complete,
  needs an extra lookup of reverse/probe sites on records with a priming forward site),
  year-over-year discrimination margin, single-primer products.
- README rewritten (advisor layout, ~220 lines) with the enterovirus "Needs attention" example
  (user asked for it); old reference text moved to docs/USER_GUIDE.md.
- Neisseria live run (54c144b): 68.9% detectable strict vs 85.7% with homopolymer bulges
  tolerated (reverse NG-R poly-A run); exclusivity FAIL: N. meningitidis CP171264.1 with a
  perfect 76 bp product (record to be checked by the user). History site list condensed.
  Advisor on bulges: no PCR study measured homopolymer bulges; proposes a graded class (1-nt
  bulge outside the last 3 nt = at_risk, larger = likely_failure) and an assembly-artefact
  breakdown; both built on the user's go-ahead (R5b; RunLengthBreakdown). Study (BioProject)
  breakdown not built: the store has no BioProject field.
- Neisseria run on d866fce: 224 kB report; run-length variants in 31,411 genomes, copies
  disagree in 83%, complete genomes carry them more often (77.8%) than contigs (60.8%): points
  to real copy variation (long-read homopolymer errors not excluded). Fixed after it: a gap no
  longer hides failing mismatches (probe variant with 7 mismatches + gap); repeatedly failing
  downloads no longer block completion.
- Advisor on MGB probe mismatch position: only Kutyavin 2000 (abstract) verifiable, strongest
  discrimination in the MGB (3') region; no data by position; keep "undetermined", optionally show
  the zone, and add a lab-evidence override in the assay file (built on the user's request: `evidence:`,
  rule LAB; zone display not built).

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
- Lefever 2013 full text checked by the advisor (summary in FEATURE_IDEAS #9; ">=4 in one
  primer or 3+2" confirmed as an "almost complete" blocking threshold). The lab's enterovirus
  mix, TaqMan Fast Virus 1-Step Master Mix: per its user guide (MAN0028278 Rev. A.0) AmpliTaq
  Fast DNA polymerase plus a thermostable MMLV-derived RT; RT 50 C 5 min, anneal/extend 60 C;
  Mg/Mn not stated. Closest to Stadhouders' Taq + MMLV setup, where all 24 reverse-primer
  mismatches cost < 0.7 Ct (the mismatch acts only in the RT step). EV-D68 (C-A at -3 in the
  reverse primer): a small effect is likely (moderate confidence); test with an RNA template
  (isolate, EQA or in-vitro transcript), not a DNA gBlock, which would overstate the risk.
- Mismatch proposal written at the user's request: docs/MISMATCH_CLASSES.md (classes perfect /
  tolerated / at_risk / likely_failure / indeterminate; rules R1-R9 with sources; setting
  variants.pcr_setup; Stadhouders Table 1 lookup). The advisor checked it against both PDFs:
  corrected R2 (-6 to -8 tolerated, not at_risk: Lefever "can be tolerated", and monotonic),
  R3 (likely_failure needs the terminal base plus another in the last 5; both papers' data
  always include the terminal base), wording ("generally <2,0 Ct", "most likely caused by",
  -4 interpolated), low-input note for >= 2 mismatches, pair flag at >= 4 in total. Not built.
- User: no lab-specific setting for the mix (the tool is for many labs; it is getting complex);
  build the classes, then pause and recap. Built: oligo/grade.py with the Taq-on-DNA column of
  Stadhouders Table 1 + Lefever counts + pair rule; grades on target sites; detectable = perfect
  or tolerated; class counts per year (report, workbook), class chips on variant rows, fixed mix
  caveat. No switch back to the old rule. 479 tests pass. Not yet run live.
- Enterovirus run with the classes (8,000 of 13,066): per-tier product cap works (products
  INCOMPLETE -> PASS). With a detectable copy 90.6% (was 74.4%): reverse 98.5% (EV-D68 C-A at -3
  now tolerated; 2024 60% -> 97%), forward none 389, probe none 196 = MGB probe with 1 mismatch
  (indeterminate, R9) counted as escapes. Found: (1) the class columns and explanation were
  hidden because the template looked at the first year only (empty 2017): fixed, test now
  reproduces it; (2) indeterminate is counted as not detected / escape, while the design says
  it counts as neither: to decide with the user.
- Report made shorter at the user's request (too many endless tables); the advisor advised on a
  clinical sign-off layout. Done: Searches taxa wrapped; products and sites grouped per tier and
  species (report/grouping.py; duplicates from degenerate primer variants counted once);
  taxonomic breakdown table -> workbook; closest variants top 10; rare (< 0.1 %) variants lumped
  only when perfect/tolerated (advisor: rare risky variants must stay visible); class columns
  in the workbook. 482 tests. Not done (advisor ideas, in FEATURE_IDEAS): first-page summary,
  top escape clusters, QC table showing only WARN/FAIL, a --full option.
- User: MGB probe with 1 mismatch = undetermined. Done: site/genome states ok | undetermined |
  fail; undetermined = rule R9 (1 mismatch in an MGB probe) or R6 (ambiguity code in the last 5
  nt); not gaps (a test showed the aligner writing two 3'-end mismatches as a gap); MGB with 2+
  mismatches at_risk. Genomes: escapes exclude undetermined (own row); inclusivity % leaves them
  out of the denominator. 484 tests. In the last enterovirus run this concerns the 196 genomes.
- Enterovirus run with the shorter report (10,000 of 13,066): report 116k characters (was 219k);
  products/sites grouped per species; no product in the must-not-detect taxa (stated); out-of-scope
  250 products in 5 species collapsed; rare safe variants lumped. Undetermined 235 genomes (MGB
  probe, 1 mismatch), escapes 503; probe detectable 100% in every year; 91.5% with a detectable
  copy. Largest remaining table: whole-fragment combinations (106 rows, risky ones never lumped).
- Seen thanks to the per-species sites table: F2 matches rhinovirus A record AF542452.1 exactly
  (Human rhinovirus 13, 5' UTR partial, 330 nt; the record ends 14 nt after F2, so no product can
  be predicted). Checked live: none of 12 complete RV-A13 genomes has the F2 site (best 6
  mismatches); the fragment reads like enterovirus sequence there. Possibly mislabelled or a
  contamination: not verified; to mention to the user as a point of attention, not a finding.
- Layout at the user's request: page 96rem wide; whole-fragment table with one-line (dot)
  alignments against the oligos in the header (alternatives named per cell); no forced minimum
  width on alignment cells; wider organism column in the closest off-target sites. 484 tests.
- Whole-fragment table: the user finds it important; the advisor advised keeping it,
  restructured: summary line; part A needs attention (never lumped below 30 rows); part B
  detectable top 10 + one row; outcome, class per site, pair-rule marker, types per combination.
  Built (report/grouping.fragment_outcome, fragment_view; organisms per combination in
  FragmentVariantRow; workbook columns). Not built: study count (BioProject field to verify),
  history flag per row, copies per genome, template export. 486 tests.
- Enterovirus run with roles (6,000 of 13,066 records): new searches READY in ~1 min each;
  target search from cache. No rhinovirus product; rhinovirus primer sites now "critical
  primer site(s) forming no predicted product" (WARN). All 500 products were out_of_scope and
  hit the shared max_amplicons cap -> products section INCOMPLETE: fixed (cap per tier, a cut
  out-of-scope list is INFO). Overall FAIL now comes from inclusivity: reverse 2024 60% (below
  fail_below_percent 80), driven by EV-D68 (816 of 5,130 records, 15.9%, C-A at -3).
  74.4% with a detectable copy; F1 59.7%, F2 33.3%, none 365; reverse 81.2%; probe 99.9%.

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
