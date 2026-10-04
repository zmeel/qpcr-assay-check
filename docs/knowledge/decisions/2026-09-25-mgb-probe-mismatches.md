---
type: Decision
title: "MGB probe mismatches - one undetermined, two or more likely failure"
description: "A single MGB probe mismatch is undetermined (neither detected nor an escape); 2+ mismatches likely failure. Narrowed on 2026-10-02 by the 7-nt MGB region."
tags: [decision]
status: draft
decided_on: 2026-09-25
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-09-25 (continued) — Enterovirus assay; taxa excluded from the target"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

One mismatch in an MGB probe makes the genome undetermined, left out of the percentage. Two or more mismatches in an MGB probe are likely failure, position-free.[^progress][^mismatch-classes]

# Who and why

User: "MGB probe with 1 mismatch = undetermined"; the 2+ rule was the user's proposal, the advisor agreed (2026-09-25, later).

# What followed

Since 2026-10-02 a single mismatch in the 3'-most 7 nt is likely failure ([MGB region](2026-10-02-mgb-region-likely-failure.md)); only one further toward the 5' end stays undetermined ([R9](../rules/r9-probes.md)).

[^progress]: PROGRESS.md, entry 2026-09-25 (continued) — Enterovirus assay; taxa excluded from the target
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
