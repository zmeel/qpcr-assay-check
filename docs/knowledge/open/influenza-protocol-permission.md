---
type: Open Item
title: Permission to publish the Erasmus MC influenza oligos (given, closed)
description: "The source protocol restricts distribution, so nothing was pushed until its author gave permission. Opened 2026-10-16, permission given 2026-10-20; the oligos in the public history from 2026-10-07 are covered by it. Closed."
tags: [open, question, influenza, licence, provenance, closed]
status: draft
generated: { by: claude-code/agent, at: 2026-10-20T00:00:00Z }
sources:
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: "Influenza A (matrix gene)"
  - id: protocol
    resource: "Protocol for Influenza RT-PCR, Viroscience Erasmus MC (R. Molenkamp), last update 02-02-2026 (supplied by the user 2026-10-16; distribution restricted)"
    title: Erasmus MC Viroscience influenza RT-PCR protocol
  - id: rules
    resource: ../../../CLAUDE.md
    title: Project rules on example assays and their provenance
---

# The question

The influenza A (matrix) example is built from the Erasmus MC Viroscience protocol the user
supplied on 2026-10-16.[^protocol] That protocol states that it may be used by microbiological
and virological laboratories in the Netherlands, and that distribution outside that network or
publication in any form is prohibited without the explicit permission of the original authors,
unless the protocol has been published in a journal.

This repository is public. So the question is not whether the tool may use the sequences — the
laboratory running it may — but whether they may sit in a public example file.[^assay]

# Where it stands

- **2026-10-16.** The second reverse primer was added to
  `docs/examples/influenza_a_matrix.yaml` and committed locally. Nothing was pushed: the commit
  was held back pending an answer, and the holding back was deliberate, not a failure.
- **2026-10-20, morning.** The user said they would obtain the permission of R. Molenkamp, the
  protocol's author. Until then the commit stayed local.
- **2026-10-20.** The user reported that R. Molenkamp **gave** permission. The commit was pushed
  on that basis, and the assay file and the assay concept both record it. The wording of the
  permission and the form it was given in are held by the laboratory, not reproduced here: what
  is written down is the user's report of it, which is what this project has.

# How it was answered

Permission was granted, so the first of the two paths was taken: the commit went up as it stood,
with the assay file and the assay concept recording who gave permission and when, so a reader can
see the sequences are published with the author's consent rather than in spite of the protocol.
Only the five oligos, their names and the reaction conditions are reproduced; the protocol itself
is not redistributed.

Had it been refused, the sequences would have come out of the public file: the example would have
kept the method — the protocol's name, version and author, the reaction conditions, the amplicon
coordinates, what the rules concluded — with the oligo sequences replaced by clearly labelled
placeholders and a note that the real ones are held by the laboratory.

# Already in the public history

Four of the oligos went into the repository on 2026-10-07, before the protocol reached this
project: they were passed on from another laboratory as `FfluA`, `RfluA`, `PfluA1-tq-NED` and
`PfluA2-tq-NED`, and the reverse primer among them was two bases short of the protocol's. They
are in pushed commits and therefore in the public history.

That mattered while the answer was open: removing them from the working tree would not have been
enough, because the history carries them too, and clearing it means rewriting pushed commits and
force-pushing, which the project rules forbid without the user saying so explicitly. The
permission settles it — those four oligos are among the five it covers, so nothing has to be
rewritten and no force-push is needed.

[^assay]: [Influenza A (matrix gene)](../assays/influenza-a-matrix.md)
[^protocol]: Protocol for Influenza RT-PCR, Viroscience Erasmus MC (R. Molenkamp), last update
    02-02-2026; supplied by the user 2026-10-16, distribution restricted.
