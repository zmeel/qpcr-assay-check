---
type: Session
title: "Enterovirus assay; taxa excluded from the target"
description: "Session log of 2026-09-25 (continued)."
tags: [session]
session_date: 2026-09-25
session_label: "2026-09-25 (continued)"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-25 (continued): Enterovirus assay; taxa excluded from the target

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

# Related

* [Graded mismatch classes, without a mix setting](../decisions/2026-09-25-graded-classes-without-mix-setting.md)
* [Enterovirus assay - human enteroviruses only; taxa roles](../decisions/2026-09-25-human-enteroviruses-only.md)
* [MGB probe mismatches - one undetermined, two or more likely failure](../decisions/2026-09-25-mgb-probe-mismatches.md)
