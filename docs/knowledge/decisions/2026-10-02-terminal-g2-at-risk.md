---
type: Decision
title: "Terminal G2 mismatches at risk"
description: "A single terminal T-T, T-C or C-T primer mismatch is at risk instead of likely failure, after Kwok 1990 and Huang 1992."
tags: [decision]
status: draft
decided_on: 2026-10-02
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-04-theory-review-items-1-and-2-mgb-position-rule-terminal-g2.md
    title: "Session 2026-10-02: Theory-review items 1 and 2: MGB position rule, terminal G2"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

Terminal G2 (T-T, T-C, C-T) is `at_risk`, not `likely_failure`. G1 and G3 unchanged.[^progress][^mismatch-classes]

# Who and why

User: "make terminal G2 mismatches at_risk".

# What followed

Sources disagree (Stadhouders avoid 3.8-4.8 Ct, Kwok yield 1.0, Huang C-T 2x10^-2): a delay, not a block. No effect on the Neisseria run of 2026-10-02 ([R1](../rules/r1-last-five.md)).

[^progress]: Session 2026-10-02: Theory-review items 1 and 2: MGB position rule, terminal G2
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
