---
type: Open Item
title: "The divergent Neisseria genomes: checked, an assembly artefact (closed)"
description: "Checked 2026-10-06: about 1,500 draft genomes whose only assembled copy is a single-copy opa paralogue every genome carries; the tool counts them undetermined, which is right. Closed."
tags: [open, small, checked]
status: draft
origin: "offered 2026-10-02, checked and closed 2026-10-06"
generated: { by: claude-code/agent, at: 2026-10-06T10:00:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-05-visualisation-examples-not-built.md
    title: "Session 2026-10-02: Visualisation examples (not built)"
  - id: export
    resource: the user's whole-amplicon export of the 2026-10-02 Neisseria run (51,200 genomes judged on a whole copy, 167 distinct 76-bp amplicons), re-analysed in the session of 2026-10-06
    title: Whole-amplicon export of the 2026-10-02 run (not in the repository)
  - id: live
    resource: live EFetch of six finished N. gonorrhoeae chromosomes (NZ_CP098536.1, NZ_CP098544.1, NZ_CP098460.1, NZ_CP145053.1, NZ_CP145037.1, NZ_CP078119.1), 2026-10-06
    title: Live check of finished chromosomes, 2026-10-06
  - id: session-2809
    resource: ../sessions/2026-09-28-01-opa-copies-unassembled-in-draft-genomes-detection-per.md
    title: "Session 2026-09-28: Opa copies unassembled in draft genomes"
  - id: tool
    resource: judged with the package's scan_genome, as_items, assess and genome_outcome on the nuccore record, session of 2026-10-06
    title: NZ_CP098544.1 judged with the tool, 2026-10-06
  - id: outcome
    resource: ../rules/genome-outcome.md
    title: Genome outcome
---

# What was open

The whole-amplicon map of the 2026-10-02 run showed a tail of amplicons far from the reference,
in about 1,500 genomes: real divergence, or an assembly artefact?[^progress]

# Checked (2026-10-06)

Re-analysed from the export, counting the mismatches and gaps of each distinct amplicon's three
oligo sites (the reference amplicon scores zero, as a check):[^export]

- **32 amplicons differ by 6 or more, in 1,535 genomes.** Every one of them is a **draft**:
  1,525 contig-level and 10 scaffold-level. None of the 330 finished genomes in the store (297
  complete, 33 chromosome-level) has such a best copy.
- **1,504 of the 1,535 share one forward site, `GTTGGCACATCGCTCCA`** against the primer's
  `GTTGAAACACCGCCCGG`. That is the diverged opa copy the user identified by hand in
  GCF_000156755.1 on 2026-09-28.[^session-2809]
- **Outcome: 1,534 counted "possibly unassembled", 1 detected.** So they are undetermined, not
  escapes, and they do not lower the detectable percentage.[^outcome]
- **Live check of six finished chromosomes:** each carries **exactly one** copy of that divergent
  site, next to 5-7 exact forward-primer sites.[^live] The paralogue is a normal single-copy
  feature of the species, present in strains the assay detects.

So these genomes are not an assay problem and not real escapes: they are drafts whose true opa
copies collapsed or were left unassembled, leaving the one paralogue as the only assembled copy.
The `multicopy_unassembled` rule handles them exactly as intended. Nothing to change.

# The lead, followed up with the tool

Among the six finished chromosomes, **NZ_CP098544.1** (strain 10296) had no exact forward-primer
site.[^live] Judged with the tool's own functions (scan, copy rule, grading, genome outcome) on
the record fetched from nuccore:[^tool] 9 copies kept, **not detected**, so an escape. Its best
copy is forward 1 mismatch (`A` for `G` at the 5' end, graded *tolerated*), probe perfect,
reverse with the **poly-A run 7 to 8** (at risk, [R5b](../rules/r5b-homopolymer-length.md)).
Under the lenient homopolymer setting one copy would be detectable and the genome detected.

So the forward site was a red herring: the mismatch sits at the 5' end and is tolerated. This is
the assay's known NG-R poly-A escape in a finished genome, consistent with the run's largest
escape group (4,196 of 4,330 escapes fail on run length only). A finished genome with the same
failure is also why these drafts are not marked "possibly unassembled" wrongly: that rule asks
whether a complete genome fails the same way. For comparison, NZ_CP098536.1 is detected, with 6
of its 9 copies detectable.

Nothing open here either; whether NG-R primes over an A8 template stays the wet-lab question it
already was.

[^progress]: Session 2026-10-02: Visualisation examples (not built)
[^export]: Whole-amplicon export of the 2026-10-02 run (not in the repository)
[^live]: Live check of finished chromosomes, 2026-10-06
[^session-2809]: "Session 2026-09-28: Opa copies unassembled in draft genomes"
[^outcome]: Genome outcome
