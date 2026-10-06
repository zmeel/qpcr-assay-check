---
type: Run
title: Neisseria gonorrhoeae, 2026-10-02 21:13Z
description: First run with every one of 51,545 genomes assessed; 85.8% detectable by collection year, 89.0% by release year - Review, driven by NG-R's poly-A run.
tags: [run, neisseria]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-02T21:13Z on the NAS (work/results), read in the session of 2026-10-03
    title: Report of the run (not in the repository)
  - id: divergent
    resource: ../open/neisseria-divergent-genomes.md
    title: "The divergent Neisseria genomes: checked, an assembly artefact (closed)"
  - id: progress
    resource: ../sessions/2026-10-02-02-browser-interface-g1-g5-v2-1-0-released.md
    title: "Session 2026-10-02: Browser interface G1-G5; v2.1.0 released"
---

# Run

[Assay](../assays/neisseria-gonorrhoeae-two-probes.md), code with the MGB-region and terminal G2
rules (2026-10-02), status axis collection. Numbers as read from the report;[^report] the
numbers are counts over public genomes, not prevalence.

# Key numbers

- All 51,545 genomes assessed (earlier runs covered 20,000 each).
- Whole fragment, collection years in the window: 85.8% detectable of 8,733; by release year
  89.0%. Status: Review.
- 4,330 escapes, 4,196 of them only by a homopolymer length difference (NG-R poly-A +1, at risk
  under [R5b](../rules/r5b-homopolymer-length.md)).
- Collection years 2024-2026: 80%, 79% and 77% detectable, the rest mostly at risk (poly-A +1).
- Effect of the new rules: the MGB region rule changed 2 genomes (NG-P1 mismatch at -2); the
  terminal G2 rule none.

# The divergent amplicons, checked afterwards

The whole-amplicon map of this run showed a tail far from the reference. Checked on 2026-10-06:
32 amplicons differing by 6 or more site changes, in 1,535 genomes, every one a draft and none of
the 330 finished genomes; 1,504 share one forward site, a single-copy opa paralogue every finished
chromosome also carries. They are counted "possibly unassembled", not escapes, which is right
([checked](../open/neisseria-divergent-genomes.md)). The same check judged the finished genome
NZ_CP098544.1 an escape on the poly-A run alone.

# Earlier findings

Checked with the user on 2026-10-02: GCF_001025995.1 has 3 assembled copies, all with A8/A9 at
NG-R's poly-A 7; the escape comes from the strict homopolymer rule, not from a contig end. A
76-bp product on N. meningitidis CP171264.1 is predicted with both primers and NG-P1
perfect.[^progress]

[^report]: Report of the run (not in the repository)
[^progress]: Session 2026-10-02: Browser interface G1-G5; v2.1.0 released
