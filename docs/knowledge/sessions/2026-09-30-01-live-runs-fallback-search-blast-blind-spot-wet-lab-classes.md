---
type: Session
title: "Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan"
description: "Session log of 2026-09-30."
tags: [session]
session_date: 2026-09-30
session_label: "2026-09-30"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan

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
- Enterovirus complete (user, 2026-09-30, max_sites_per_query 6000): 13,109 of 13,109
  records; whole fragment 2023-2026 91.6% detectable, 98.6% with at risk (Review);
  specificity Exceeds limit: 4 predicted rhinovirus products the probe would detect (e.g.
  76 bp on PV178561.1, RV-A102: forward 3-4 mismatches in the 5' half with 12 clean 3' nt,
  probe perfect, reverse 1 mismatch + 1 gap; checked by hand against the record: real, no N);
  the probe's hit list in the rhinovirus tier is still full. max_taxids_per_search 1 split
  every tier (36 out-of-scope searches, one queued over 2 h at NCBI): removed from the example;
  a per-tier split is the proper fix (not built). Bug fixed: "Target on a plasmid: yes" for
  a virus (patent records titled "... and plasmids").
- Theory reviews (user, 2026-10-01): a senior theoretical molecular biologist and the methods
  advisor reviewed independently against the literature and GitHub; kept verbatim in
  docs/reviews/ with a comparison (README.md). Both: sound and novel method, probe rules the
  weakest, terminal mismatch types on one source, Tm should weigh more, redundancy inflates
  percentages. Built for v2 on the user's "add all the small points": R5c probe-site deletions
  from Otwell (re-run: 7 templates at risk -> likely failure, all >= +3 Ct or undetected; FN5446,
  6 nt in C4 ORF8, detected with a delay but graded likely failure because 6 nt failed in Yale
  69/70 del); section 11 called calibration; detection-not-quantification caveat; "Tm <=
  annealing" flag and "ΔTm not applicable" for modified oligos (the FDA 2023 attribution could
  not be verified: fda.gov blocks automated reads); bracketing percentages and
  inclusivity.max_undetermined_percent 25. Deferred (changes results; user decides):
  position-aware MGB rule, third source for terminal types, deduplicated figure, collection date
  as status axis, every locus scanned, unified off-target rules, independent validation.
  Note: Neisseria rerun on 2026-09-30 rescanned because store schema 4 (fallback) changed the
  key, not because of the YAML.
- Legionella with the v2 code (user, 2026-10-01): inclusivity INCOMPLETE (41.1% of the
  window undetermined, mostly 1,852 detectable from parts); the channels were 63-64%
  undetermined because they counted the 4,440 cut genomes and the fragment table did not.
  The "Tm <= annealing" flag fired 88 times because the primers' perfect Tm (59.8/60.0 °C)
  sits at the 60 °C annealing: it now needs a drop across the line. Exclusivity WARN (85
  Coxiella sites); specificity INCOMPLETE (human hit list full).
- User decisions (2026-10-01): "detectable from parts" counts as detected for every assay
  (`variants.judge_from_parts` default `detectable`); genomes whose region is cut by a contig
  end or hidden by N count as undetermined in both the whole-fragment table (and collection
  axis) and the channels. Expected for Legionella: the from-parts genomes move to detected,
  but the cut genomes stay undetermined, so the fragment status will likely still be
  INCOMPLETE.
- Neisseria with this code (user, run 2026-10-01T17:03Z; store reused, 1,283 new): 21,983 of
  51,583 assessed. Whole fragment 2023-2026 89.8% detectable of 17,999 judged (91.9% on
  2026-09-30); bracket 77.7-91.1%; undetermined 2,788 of 20,787 (13%, under the 25% limit),
  23 of them cut or hidden; status Review, Incomplete until every genome is assessed. Fragment
  and channel now agree (channel undetermined 2,990 = 1,603 + 1,345 unassembled + 42 cut or
  hidden). The drop is not in detectable genomes (2025: 4,443 -> 4,445; 2026: 1,919 -> 1,922)
  but in "possibly unassembled" (2025: 642 -> 450; 2026: 481 -> 355) turning into at risk or
  likely failure: complete genomes rose from 160 to 297 (escapes 6 -> 12), and a draft is not
  marked when a complete genome fails with the same sites. Expected behaviour, not a bug. R5c
  seen live (NG-P2, 1-nt deletion -> at risk). "Tm <= annealing" now only on real drops (NG-R
  3' variants, ΔTm -3.1 °C and more); MGB probes "ΔTm not applicable". By collection year,
  the share at risk is 13-17% for samples collected 2024-2026 against 4-9% before (2024
  releases only partly assessed, newest first). Specificity unchanged: one 76-bp product on
  CP171264.1 (N. meningitidis); partner scan 43 windows, nothing added; score floors known.
- Not done yet: two more Neisseria runs (29,582 left), Legionella re-run, then the v2 release.

# Related

* [Mismatch counts within the 3'-most 16 nt; R3b](../decisions/2026-09-30-count-within-16-nt.md)
* [E-value stays 1000; score floor and partner scan built](../decisions/2026-09-30-expect-1000-score-floor-partner-scan.md)
* [Detectable from parts counts as detected; cut genomes undetermined](../decisions/2026-10-01-from-parts-detected-cut-undetermined.md)
* [The small points of the theory reviews](../decisions/2026-10-01-small-review-points.md)
* [E-utilities - what the code relies on](../ncbi/eutils.md)
* [Split taxon lists per tier, not per search](../open/taxid-split-per-tier.md)
* [Publish docs/wiki to the GitHub wiki](../open/wiki-publication.md)
* [Enterovirus, 2026-09-30 (complete)](../runs/enterovirus-2026-09-30.md)
