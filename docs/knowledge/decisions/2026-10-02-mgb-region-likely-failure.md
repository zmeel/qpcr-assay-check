---
type: Decision
title: "One mismatch under the MGB is a likely failure"
description: "A single mismatch in the 3'-most 7 nt of an MGB probe is likely failure (Kutyavin 2000); further toward the 5' end it stays undetermined."
tags: [decision]
status: draft
decided_on: 2026-10-02
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-10-02 — Theory-review items 1 and 2: MGB position rule, terminal G2"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

MGB probe, one mismatch at positions -1 to -7: `likely_failure` (`MGB_REGION = 7`); further toward the 5' end: `indeterminate` (undetermined).[^progress][^mismatch-classes]

# Who and why

User: "a single mismatch in the 7 bases at the 3′ end of an MGB probe → likely_failure".

# What followed

Seen live: 2 Neisseria genomes (NG-P1 mismatch at -2) ([R9](../rules/r9-probes.md)).

[^progress]: PROGRESS.md, entry 2026-10-02 — Theory-review items 1 and 2: MGB position rule, terminal G2
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
