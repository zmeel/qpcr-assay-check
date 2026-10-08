---
type: Open Item
title: Degenerate oligos broke the duplex Tm baseline
description: The perfect-match baseline was computed with the degenerate codes left in, which primer3 cannot pair, so every ΔTm of such an oligo was measured against a reference about 15 C too low. Fixed 2026-10-07.
tags: [open, bug, thermodynamics, degenerate, closed]
status: draft
generated: { by: claude-code/agent, at: 2026-10-07T17:00:00Z }
sources:
  - id: run
    resource: ../runs/influenza-a-2026-10-07-corrected.md
    title: "Influenza A (matrix), 2026-10-07 (14:01Z)"
  - id: code
    resource: ../../../src/qpcr_assay_check/specificity/duplex.py
    title: specificity/duplex.py (estimate_duplex, resolved_oligos)
  - id: records
    resource: "live EFetch of PX851249.1 and PZ038336.1, 2026-10-07"
    title: The two records behind the two rows
---

# What was wrong

The user read the first two rows of "Needs attention" in the 14:01Z influenza run: identical in
every column, yet one said ΔTm -3.6 C and the other +0.0 C.[^run] The rows were in fact two
different site variants, differing only in the base under the reverse primer's degenerate `Y`
(PX851249.1 has T, so an A:T pair; PZ038336.1 has C, so G:C).[^records] Both are matches, so the
compact alignment drew a dot for both and `site_changes` skipped them: the ΔTm was the only sign.

Chasing it found a real fault. ΔTm is the duplex Tm minus the perfect-match Tm, and the baseline
was the oligo against its own reverse complement **with the degenerate codes still in it**:
`...CCAYTCC...` against `...GGARTGG...`. primer3 cannot pair a Y with an R, so it fell back to a
much weaker dimer:

| baseline | Tm | ΔG |
|---|---|---|
| as computed (Y against R) | **49.3 C** | -7.1 |
| the primer with Y as C, exact complement | 64.5 C | -13.1 |
| the primer with Y as T, exact complement | 63.0 C | -12.3 |

The oligo QC section had it right all along (it reports RfluA as 63.0-64.6 C, the two
resolutions), so the report contradicted itself. Consequences: the absolute duplex Tm was not
credible, every ΔTm was positive-biased, which member the template took decided the figure, and
the "Tm <= annealing" flag could never fire for such an oligo - it is suppressed when the
baseline itself is at or below the annealing temperature, and 49.3 C is below 60 C.

# Fixed, 2026-10-07 (both parts, on the user's word)

1. **The estimate resolves a degenerate oligo against the template first** (`resolved_oligos` in
   `specificity/duplex.py`): the template's base where the two are compatible - that member of
   the mix binds there - expanded where the template contradicts it, and the member that binds
   best is the one reported, with its own perfect match as the baseline.[^code] The two rows now
   both read ΔTm **-0.7 C**, at 62.2 and 63.8 C, which is what a lone 3'-terminal mismatch should
   look like.
2. **A match through a degenerate code is written out instead of a dot**: a grey letter in the
   compact alignments, and named by `site_changes` as `-9 Y=T` (against `-9 Y/C` for an
   incompatible one). Two variants differing only there are now visibly different.

Of the example assays this touches influenza A (`FfluA` has R, `RfluA` has Y) and enterovirus
(the reverse primer has R, the probe M); Neisseria and E. histolytica have no degenerate bases.
ΔTm, ΔG and that one flag are the only figures that move, never a class, so no earlier outcome
changes. Reports written before the fix carry the biased ΔTm.

# A third fix, from the code review of 2026-10-08

Only the oligo was resolved. An ambiguity code in the **genome** still reached primer3, which
can pair nothing with it: a template differing by a single N read as a duplex Tm of 50.87 C
against a perfect match of 64.28 C, a 13.4 C drop - and because unblocking the "Tm <= annealing"
flag was part of this very fix, that drop could now trip the flag on a site [R6](../rules/r6-ambiguity-codes.md)
grades a match. `resolved_template` now resolves the template too: an ambiguity code compatible
with the oligo takes the oligo's base, which is what R6 says it is, and one the oligo contradicts
takes a concrete base of its own so the position is a defined mismatch rather than a character
that pairs with nothing. Covered by
`test_an_ambiguity_code_in_the_genome_is_resolved_against_the_oligo`.

[^run]: "Influenza A (matrix), 2026-10-07 (14:01Z)"
[^code]: specificity/duplex.py (estimate_duplex, resolved_oligos)
[^records]: The two records behind the two rows
