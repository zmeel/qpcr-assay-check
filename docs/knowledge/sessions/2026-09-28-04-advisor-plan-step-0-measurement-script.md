---
type: Session
title: "Advisor plan; step 0: measurement script"
description: "Session log of 2026-09-28 (overhaul)."
tags: [session]
session_date: 2026-09-28
session_label: "2026-09-28 (overhaul)"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-28 (overhaul): Advisor plan; step 0: measurement script

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
