---
type: Decision
title: "Cut genomes stay undetermined; a fragment not in the assembly is not found"
description: "Option 1 and 2 of the cut-genome breakdown: keep cut genomes undetermined, and count genomes whose fragment is absent from the assembly as region not found."
tags: [decision]
status: draft
decided_on: 2026-10-02
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-03-theory-review-items-3-and-4.md
    title: "Session 2026-10-02: Theory-review items 3 and 4"
---

# Decision

Genomes with a site cut by a contig end stay undetermined (Legionella stays Incomplete, with the bracket); genomes whose every copy is truncated with no seed of the fragment ("fragment not in the assembly") count as region not found (`fragment_not_assembled()`).[^progress]

# Who and why

User: "Go with 1 and 2", after the breakdown of Legionella's 4,441 cut genomes.

# What followed

Legionella: cut 4,441 -> 4,280, not found 259; still Incomplete ([run](../runs/legionella-2026-10-02.md)).

[^progress]: Session 2026-10-02: Theory-review items 3 and 4
