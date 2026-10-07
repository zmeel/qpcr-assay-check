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

# Related

* [Influenza A, matrix gene (two NED probes)](../assays/influenza-a-matrix.md)
