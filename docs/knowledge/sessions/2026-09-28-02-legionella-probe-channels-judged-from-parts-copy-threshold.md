---
type: Session
title: "Legionella; probe channels; judged from parts; copy threshold advice"
description: "Session log of 2026-09-28 (later)."
tags: [session]
session_date: 2026-09-28
session_label: "2026-09-28 (later)"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-28 (later): Legionella; probe channels; judged from parts; copy threshold advice

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

# Related

* [Genomes judged from parts; copies possibly unassembled; copy identity](../decisions/2026-09-28-judge-from-parts-and-unassembled-copies.md)
