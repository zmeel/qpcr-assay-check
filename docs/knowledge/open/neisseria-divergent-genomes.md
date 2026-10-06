---
type: Open Item
title: "The divergent Neisseria genomes: checked, an assembly artefact"
description: "Checked 2026-10-06: about 1,500 draft genomes whose only assembled copy is a single-copy opa paralogue every genome carries; the tool counts them undetermined, which is right. One lead left."
tags: [open, small, checked]
status: draft
origin: "offered 2026-10-02, checked 2026-10-06"
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

# The one lead left

Among the six finished chromosomes, **NZ_CP098544.1** had no exact forward-primer site at all:
all seven of its probe-bearing copies carry 1-2 mismatches in the forward site.[^live] Whether
that strain is still detectable depends on its reverse sites, which the ad-hoc window used for
this check cannot measure reliably (the window cuts the poly-T run). It needs a proper look with
the tool, not a script. It is one finished genome, so it cannot change the percentages much, but
a finished genome without a perfect forward site is worth understanding.

[^progress]: Session 2026-10-02: Visualisation examples (not built)
[^export]: Whole-amplicon export of the 2026-10-02 run (not in the repository)
[^live]: Live check of finished chromosomes, 2026-10-06
[^session-2809]: "Session 2026-09-28: Opa copies unassembled in draft genomes"
[^outcome]: Genome outcome
