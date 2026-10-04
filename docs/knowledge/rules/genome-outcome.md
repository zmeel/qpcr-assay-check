---
type: Grading Rule
title: Genome outcome
description: How one genome counts - detected, not detected (escape), undetermined, possibly unassembled, or with its region cut, hidden or not found.
tags: [genome, outcome, inclusivity]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: exhaustive-py
    resource: ../../../src/qpcr_assay_check/variants/exhaustive.py
    title: variants/exhaustive.py (genome_outcome, mark_unassembled, cut_kind)
  - id: d-parts
    resource: ../decisions/2026-10-01-from-parts-detected-cut-undetermined.md
    title: Decision on genomes judged from parts and cut genomes
  - id: d-cut
    resource: ../decisions/2026-10-02-cut-genomes-and-unassembled-fragments.md
    title: Decision on cut genomes and unassembled fragments
  - id: d-model
    resource: ../decisions/2026-09-29-generic-assay-model.md
    title: Decision on the generic assay model
---

# Best copy

A genome is judged by its best-binding copy of the locus (multi-copy targets such as the
N. gonorrhoeae opa region carry up to 10). Each copy's three sites are graded
([classes](classes.md)); detection needs a detectable site of every role on one copy, plus the
primer-pair rule ([R8](r8-primer-pair.md)).

# Precedence

One function, `genome_outcome()`, decides for every count:[^exhaustive-py]

1. **Detectable from parts**: only cut copies, but every role has a detectable site on them;
   counted as detected by default (`variants.judge_from_parts: detectable`).[^d-parts] The sites
   may come from different copies, so this is never proof of one amplicon.
2. **Detected**: a copy with every site detectable.
3. **Undetermined**: the deciding site has no published basis ([R6](r6-ambiguity-codes.md),
   [R9](r9-probes.md)).
4. **Possibly unassembled**: a draft whose best copy fails, with fewer than half the copies the
   complete genomes of the run carry, unless a complete genome fails the same way
   (`variants.multicopy_unassembled`).
5. **Not detected**: an escape.

Genomes without a whole copy: **cut by a contig end** or **hidden by N** count as undetermined in
both the whole-fragment table and the channels;[^d-parts] the report breaks the cut ones down by
which sites are cut (`cut_kind()`). A genome whose fragment is not in the assembly at all (every
copy cut with no seed of the fragment) counts as **region not found**.[^d-cut] In a complete
genome, no locus is **not detected** (a possible deletion).[^d-model]

[^exhaustive-py]: variants/exhaustive.py (genome_outcome, mark_unassembled, cut_kind)
[^d-parts]: Decision on genomes judged from parts and cut genomes
[^d-cut]: Decision on cut genomes and unassembled fragments
[^d-model]: Decision on the generic assay model
