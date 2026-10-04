---
type: Session
title: "Overhaul round 2: a generic assay model (advisor); user decisions"
description: "Session log of 2026-09-29."
tags: [session]
session_date: 2026-09-29
session_label: "2026-09-29"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-29: Overhaul round 2: a generic assay model (advisor); user decisions

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

# Related

* [One generic assay model - loci and channels](../decisions/2026-09-29-generic-assay-model.md)
* [Copy rule (a, b, c)](../rules/copy-rule.md)
