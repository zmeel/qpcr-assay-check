---
type: Decision
title: "Graded mismatch classes, without a mix setting"
description: "Sites get graded classes from Stadhouders and Lefever on one basis (Taq on DNA) for every laboratory; no switch back to the old rule."
tags: [decision]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T10:07:25Z }
decided_on: 2026-09-25
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-25-02-enterovirus-assay-taxa-excluded-from-the-target.md
    title: "Session 2026-09-25 (continued): Enterovirus assay; taxa excluded from the target"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

Build the graded classes (perfect, tolerated, at risk, likely failure, indeterminate) with the Taq-on-DNA column of Stadhouders Table 1, Lefever's counts and the pair rule; no setting for the reaction mix; the classes replace the old binary rule directly.[^progress][^mismatch-classes]

# Who and why

User: "no lab-specific setting for the mix (the tool is for many labs; it is getting complex)".

# What followed

`oligo/grade.py`; detectable = perfect or tolerated; a fixed caveat about mixes in the report ([classes](../rules/classes.md)).

[^progress]: Session 2026-09-25 (continued): Enterovirus assay; taxa excluded from the target
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
