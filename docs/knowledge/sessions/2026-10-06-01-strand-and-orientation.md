---
type: Session
title: "Strand and orientation; the divergent Neisseria genomes checked"
description: "Session log of 2026-10-06."
tags: [session]
session_date: 2026-10-06
session_label: "2026-10-06"
generated: { by: claude-code/agent, at: 2026-10-06T08:00:00Z }
---

# 2026-10-06: Strand and orientation of a record

- User asked whether the tool detects a sequence submitted as the reverse complement or in
  another orientation. Answer: yes. The chain locator seeds each record on both strands
  (`chain.py`, `for strand, s in (("+", contig), ("-", reverse_complement(contig)))`), every copy
  carries its strand and the sites are read in the fragment's sense; tests cover a minus-strand
  copy and a minus-strand record end to end, and the E. histolytica run is live evidence (its
  amplicon lies opposite the rRNA; X64142.1 carries it as a reverse complement).
- Written up as [components/strand-and-orientation](../components/strand-and-orientation.md),
  with the two cases orientation does not cover: a record that starts or ends inside the amplicon
  (cut, undetermined) and a circular genome whose start point falls inside it (two cut pieces,
  never joined). Linked from the chain locator page.
- User: "Check the divergent Neisseria's". Re-analysed the whole-amplicon export of the
  2026-10-02 run (oligo-site mismatches per distinct amplicon; the reference scores zero as a
  check): 32 amplicons differ by 6 or more, in 1,535 genomes, all drafts (1,525 contig, 10
  scaffold) and none of the 330 finished genomes; 1,504 share the forward site GTTGGCACATCGCTCCA,
  the opa paralogue found by hand in GCF_000156755.1 on 2026-09-28; 1,534 counted "possibly
  unassembled", 1 detected. Live EFetch of six finished chromosomes: each carries exactly one
  copy of that divergent site next to 5-7 exact forward-primer sites. Conclusion: an assembly
  artefact, the rule handles it as intended, nothing to change.
- One lead left: NZ_CP098544.1 (finished) has no exact forward-primer site; its seven
  probe-bearing copies all carry 1-2 forward mismatches. The ad-hoc window cannot measure its
  reverse sites (it cuts the poly-T run), so it needs a look with the tool itself.

# Related

* [Strand and orientation of a record](../components/strand-and-orientation.md)
* [The divergent Neisseria genomes: checked, an assembly artefact](../open/neisseria-divergent-genomes.md)
