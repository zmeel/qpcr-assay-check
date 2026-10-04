---
type: Decision
title: "Enterovirus assay - human enteroviruses only; taxa roles"
description: "Animal enteroviruses are out of scope (information only) and rhinoviruses must not be detected; one list with a role and reason per taxon."
tags: [decision]
status: draft
decided_on: 2026-09-25
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-25-02-enterovirus-assay-taxa-excluded-from-the-target.md
    title: "Session 2026-09-25 (continued): Enterovirus assay; taxa excluded from the target"
---

# Decision

The enterovirus target is human enteroviruses only. `target.taxa` gives each excluded taxon a role (`must_not_detect` or `out_of_scope`) and a reason: rhinoviruses must not be detected (judged on products, a lone primer site WARN), animal enteroviruses are out of scope (an INFO-only search tier).[^progress]

# Who and why

User, after the first enterovirus runs; the advisor proposed the split.

# What followed

The example assay lists 5 rhinovirus taxa as must-not-detect and 36 animal taxa as out of scope ([assay](../assays/enterovirus-realt.md)).

[^progress]: Session 2026-09-25 (continued): Enterovirus assay; taxa excluded from the target
