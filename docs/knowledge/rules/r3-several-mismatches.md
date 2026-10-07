---
type: Grading Rule
title: R3 - several mismatches in one primer
description: Counts within the 3'-most 16 nt decide; R3b grades mismatches beyond -16 from Otwell 2025.
tags: [grading, primer, R3, R3b]
status: stable
verified: { by: human:zmeel, at: 2026-10-07T08:37:00Z }
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: lefever
    resource: ../sources/lefever-2013.md
    title: Lefever et al. 2013
  - id: stadhouders
    resource: ../sources/stadhouders-2010.md
    title: Stadhouders et al. 2010
  - id: otwell
    resource: ../sources/otwell-2025.md
    title: Otwell et al. 2025
  - id: d-window
    resource: ../decisions/2026-09-30-count-within-16-nt.md
    title: Decision to count within the 3'-most 16 nt
---

# Rule

Counted within the 3'-most 16 nt (the region Lefever tested) since 2026-09-30.[^d-window]

| Mismatches | Class | Basis |
|---|---|---|
| terminal base plus another in the last 5 | `likely_failure` | Lefever 7.93-12.15 dCq; Stadhouders no amplification with Taq[^lefever][^stadhouders] |
| 2 | at least `at_risk` | Lefever Fig. 6, median about 7.7 dCq (read from the figure) |
| 3 | `likely_failure` | Lefever Fig. 6 median about 15 dCq; Otwell +6 to +7 Ct, 2 of 3 missed at 50 copies[^otwell] |
| 4 | `likely_failure` | Lefever: blocked "almost completely" |
| 4 adjacent, none in the last 5, nothing beyond -16 | `at_risk` | Lefever's 5'-end exception; the size is our choice |

**R3b**, mismatches beyond -16: alone, up to 4 `tolerated` and 5 or more `at_risk`; with at
least one inside the 16 nt, at least `at_risk` (Otwell: one inside plus 3 at -20 to -22, mostly
+3 to +6 Ct, never undetected at 50 copies).[^otwell]

Two or more mismatches carry the note "worse near the limit of detection" (Lefever: input
independence lost at low copy numbers). The counts come from DNA assays and are not relaxed for
the reverse primer of a one-step RT-PCR ([R4](r4-reverse-primer-rt.md)).

[^lefever]: Lefever et al. 2013
[^stadhouders]: Stadhouders et al. 2010
[^otwell]: Otwell et al. 2025
[^d-window]: Decision to count within the 3'-most 16 nt
