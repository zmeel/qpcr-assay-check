---
type: Grading Rule
title: Copy rule (a, b, c)
description: When a located region counts as a copy of the locus - 32 anchored bases, 32 context bases, or identity 0.75 with 16 anchored.
tags: [locator, copy, chain]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: config
    resource: ../settings/variants.md
    title: Settings - variants
  - id: progress
    resource: ../../PROGRESS.md
    title: PROGRESS.md, entries 2026-09-28 and 2026-09-29 (legionella4 measurement)
---

# Rule

A region found by the [chain locator](../components/chain-locator.md) is a copy of the locus
when any of these holds; weaker regions are listed as "related", never judged:[^config]

- **(a)** at least 32 fragment bases in exact co-linear blocks (`min_anchored_bases`);
- **(b)** at least 32 bases anchored in the context sequence on one side (`min_context_bases`),
  with the fragment touched, flanked on both sides, or cut by a contig end;
- **(c)** identity to the reference fragment of at least 0.75 over the part covered, with at
  least 16 anchored bases (`min_copy_identity`, `min_identity_anchored_bases`).

# Measured basis

On Legionella (legionella4, 2026-09-29): look-alike regions had identity 0.600-0.658, 16-17
anchored bases and no context; real divergent copies in other Legionellaceae 0.658-0.727 with
40-792 context bases. Identity alone could not separate them; context could. Chance regions reach
at most 18 anchored bases; whole real copies 114 or more. The defaults were kept after this
measurement.[^progress]

[^config]: Settings - variants
[^progress]: PROGRESS.md, entries 2026-09-28 and 2026-09-29 (legionella4 measurement)
