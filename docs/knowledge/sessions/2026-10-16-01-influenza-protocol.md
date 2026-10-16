---
type: Session
title: "The Erasmus MC influenza protocol, and the primer that answers the sweep"
description: "Session log of 2026-10-16."
tags: [session]
session_date: 2026-10-16
session_label: "2026-10-16"
generated: { by: claude-code/agent, at: 2026-10-16T13:00:00Z }
---

# 2026-10-16: the influenza protocol

- User supplied the Erasmus MC Viroscience influenza RT-PCR protocol (R. Molenkamp, last update
  02-02-2026), the authoritative source for the influenza A matrix assay, with an added reverse
  primer.
- It confirms all four sequences the file already held, the 24-mer reverse primer among them, so
  the 22-mer that arrived from another laboratory on 2026-10-07 was indeed a transcription error.
  It also corrects two labels the file carried on hearsay: the probes are **FAM**-BHQ1, not NED,
  and the names are infa_fwd, infa_rev, infa_probe1, infa_probe2. Cycling: 50 C 5 min, 95 C 20 s,
  then 45 x (95 C 3 s, 60 C 30 s), so the 60 C the file had assumed is right.
- **infa_rev2** is the new one: `TCTTGTCTTTAGCCAYTCCATGAT`, differing from infa_rev only in its
  3'-terminal base, G to T. That is exactly the escape the complete run of 2026-10-07 was built
  around - the 3'-terminal G-A mismatch that was 97.0% of the "Needs attention" records and swept
  from 0.7% of 2021 collections to 40.5% of 2023. The laboratory has answered the finding with a
  second primer.
- Added as a second reverse primer (the format takes several oligos per role), with the
  protocol's names, dyes and cycling. QC: Review, 0 outside the limit; infa_rev2 shows its single
  designed mismatch against the reference, as infa_probe2 does. A rerun should turn most of the
  30.6% likely failure into detectable, since a copy is judged by the best-binding oligo of each
  role.
- **Raised, not decided:** the protocol says it may be used by laboratories in the Netherlands
  and that distribution outside that network or publication in any form needs the author's
  permission. These sequences have been in a public repository since 2026-10-07. Whether they
  stay is the laboratory's call, so nothing was pushed on 2026-10-16.

# Related

* [Influenza A, matrix gene (Erasmus MC Viroscience protocol)](../assays/influenza-a-matrix.md)
