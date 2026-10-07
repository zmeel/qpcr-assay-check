---
type: Session
title: "Influenza A matrix-gene assay file, and the README's knowledge base section"
description: "Session log of 2026-10-07 (second page)."
tags: [session]
session_date: 2026-10-07
session_label: "2026-10-07-02"
generated: { by: claude-code/agent, at: 2026-10-07T14:00:00Z }
---

# 2026-10-07: Influenza A assay, README

- README: added a "The knowledge base" section (what `docs/knowledge/` is, a table of the eleven
  folders, traceability and the trust tiers, where to start, the viewer script) and a row in the
  documentation table. The limitations bullet claiming no source covers probe mismatches or gaps
  was out of date and now names what the probe rules actually rest on.
- User supplied an influenza A matrix-gene assay (FfluA, RfluA, two NED/BHQ1 probes differing by
  one base, a 141-nt reference sequence, exclude influenza B). Added as
  [docs/examples/influenza_a_matrix.yaml](../../examples/influenza_a_matrix.yaml) exactly as
  given.
- **The reverse primer does not fit the supplied reference**: 2 mismatches at its 5' end and the
  reference runs on for 2 more bases. The reference is in frame for M1 (CTA AAG ACA AGA);
  inserting `GT` after the primer's leading `TCTT` makes it match over its whole length with no
  mismatch and no gap, which looks like two bases lost in transcription. Nothing was changed and
  the user was asked to check the order sheet; the file's header states this.
- Checked live at NCBI: taxid 11320 "Influenza A virus" (a no-rank node under species 2955291,
  so it covers every subtype), 11520 "Influenza B virus"; 1,676,357 Nucleotide records for 11320
  and 172,768 for `980:1100[SLEN] AND segment 7[TITL]`, the query chosen for the variant source.
  Far beyond one run, so `blast_max_records_per_run: 5000` and the file says the analysis is
  resumed by running again.
- `run --qc-only`: Exceeds limit from the oligos as supplied (FfluA Tm 66.4 C, primers 6.2 C
  apart, a 5-base run in each probe) plus the two site warnings. Product 139 bp, GC 49.6%.
- Both probes are linear NED/BHQ1, so they are the first example assay the unmodified-probe
  ladder of [R9](../rules/r9-probes.md) applies to.
- User asked whether a different exclusion would be better, and agreed to widen it: the panel
  went from influenza B alone to 17 taxa (influenza B, C, D, plus the respiratory differential).
  The mechanical reason is that an assay's own `exclusivity_organisms` replaces the packaged
  clinical organism list, so one name would have made the tier narrower than the default. Every
  name checked live; parainfluenza 1-3 and rhinovirus A written with their current scientific
  names (the older spellings need the `[All Names]` fallback). Nothing inside influenza A is
  excluded.

- User uploaded a Legionella run made with the latest code (09:48Z). The probe-rule change
  landed as predicted: the micdadei row (7 genomes, GCF_000953635.1) now reads likely failure
  for the unmodified LEGpneu probe, every LEGpneu entry in "Needs attention" does, and no
  headline figure moved (94.0% of 1,690 against 93.9% of 1,669 on 2026-10-02, the difference
  being NCBI's growth from 11,174 to 11,952 assemblies). R5c never fires in this assay.
  Written up as [runs/legionella-2026-10-07](../runs/legionella-2026-10-07.md).
- Found a bug in that report: "44.7% if single-base run-length differences were tolerated"
  against 94.0% strict, which is impossible over a fixed cohort. `n_detectable_other_rule`
  omits the `judge_from_parts` term that `n_detectable` has, so the 2,928 genomes judged from
  parts count as not detectable in the bracketing figure. Reproduced with the existing
  `_split_fixture` (75.0% headline, 50.0% bracketing, no bulge anywhere in the fixture).
- Fixed on the user's word ("Execute option 2"): `assess` now also judges from parts under the
  other bulge rule, so a genome detectable from parts only because a run-length difference is
  tolerated is counted as well. `_assess_parts` runs a second time only for a genome with no
  copy detectable under the other rule and a cut copy. A genome with no whole copy at all never
  gets a `GenomeCall`, so it stays outside both figures' cohort either way; the extra case is a
  failing whole copy plus cut copies, the Legionella shape. New test covers both halves and
  fails on the old code ([open item, now closed](../open/bulge-alternative-from-parts.md)).

- First influenza A run (13:08Z, the 22-mer): the user read it as a tool bug ("2 mismatches in
  every reverse primer that are not there in real") and downloaded PZ488030.1 and PZ641704.1.
  Aligned live: the 22-mer gives 3 mismatches in both, the 24-mer 1, and the one left is strain
  variation at a different position in each; the forward primer and PfluA1 match both exactly.
  The report itself gave it away - all 23 reverse variants, over all 14,960 assessed records
  (100%), carried the same 2-base difference, so no record matched the primer perfectly. The
  tool was right against the primer it was given; no code changed.
- The user then gave their own laboratory's primer for the same PCR, the 24-mer
  `TCTTGTCTTTAGCCAYTCCATGAG`, and the assay file now carries it with the provenance of both
  forms. QC falls from Exceeds limit to Review (primer Tm difference 6.2 C to 3.4 C, within the
  limit), the reverse site sits at 118-141 exactly and the product is the whole 141-nt reference.
  Written up as [runs/influenza-a-2026-10-07](../runs/influenza-a-2026-10-07.md).

# Related

* [Influenza A, matrix gene (two NED probes)](../assays/influenza-a-matrix.md)
* [Legionella, 2026-10-07 (09:48Z)](../runs/legionella-2026-10-07.md)
* [The bracketing bulge figure drops the from-parts genomes](../open/bulge-alternative-from-parts.md)
* [Influenza A (matrix), 2026-10-07 (13:08Z)](../runs/influenza-a-2026-10-07.md)
