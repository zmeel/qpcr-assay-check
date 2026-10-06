---
type: Grading Rule
title: R5b - homopolymer length differences in a primer site
description: One extra or missing base in a run of 3+ is at risk with the run outside the last 3 nt, otherwise likely failure; our class, no PCR study.
tags: [grading, primer, homopolymer, R5b]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, R5b
  - id: zhu-wartell
    resource: ../sources/zhu-wartell-1999.md
    title: Zhu and Wartell 1999
  - id: tanaka
    resource: ../sources/tanaka-2004.md
    title: Tanaka et al. 2004
  - id: elbrecht
    resource: ../sources/elbrecht-2018.md
    title: Elbrecht et al. 2018
  - id: divergent
    resource: ../open/neisseria-divergent-genomes.md
    title: "The divergent Neisseria genomes: checked, an assembly artefact (closed)"
  - id: d-bulges
    resource: ../decisions/2026-09-26-homopolymer-bulges-graded.md
    title: Decision to grade homopolymer bulges
---

# Rule

A single gap block that only changes the length of a run of at least 3 identical bases in the
primer: one base with the run ending outside the last 3 nt is `at_risk`; two or more bases, or a
run reaching the last 3 nt, `likely_failure`; with further mismatches, the worse of this and
their class.[^mismatch-classes] **The class is ours**: no PCR study measured such bulges.[^d-bulges]
What exists: single bulges inside a run are comparatively stable,[^zhu-wartell][^tanaka] and
primers slip across homopolymers;[^elbrecht] abstracts read by the advisor only.

Setting `variants.homopolymer_bulges_detectable` (default false) counts a run-length variant
without mismatch as detectable instead. The report gives the status figure under both settings
(since 2026-10-03), and a breakdown of how far to trust the variants (copies that disagree,
assembly level), since run length is a known sequencing and assembly error.

Live: the N. gonorrhoeae reverse primer NG-R crosses a poly-A 7 run; A8/A9 variants drive most of
that assay's escapes (see [the Neisseria runs](../runs/neisseria-2026-10-02.md)). The rule decides real genomes on its own:
NZ_CP098544.1, a **finished** N. gonorrhoeae chromosome, escapes only because of it (forward
1 mismatch at the 5' end, tolerated; probe perfect; reverse poly-A 7 to 8), and is detected under
the lenient setting ([checked with the tool](../open/neisseria-divergent-genomes.md)).

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R5b
[^zhu-wartell]: Zhu and Wartell 1999
[^tanaka]: Tanaka et al. 2004
[^elbrecht]: Elbrecht et al. 2018
[^d-bulges]: Decision to grade homopolymer bulges
