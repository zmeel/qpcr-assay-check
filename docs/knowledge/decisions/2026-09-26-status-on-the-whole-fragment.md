---
type: Decision
title: "Inclusivity status on the whole fragment over a window"
description: "The inclusivity status uses the genome outcome of all three sites together, over the last 3 complete years plus the current one."
tags: [decision]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T09:23:00Z }
decided_on: 2026-09-26
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-26-01-v1-4-0-released-inclusivity-on-the-whole-fragment.md
    title: "Session 2026-09-26: v1.4.0 released; inclusivity on the whole fragment"
---

# Decision

The status is based on the whole-fragment genome outcome (forward, reverse and probe together), not per-oligo percentages, over the last `verdict_window_years` (3) complete release years plus the current year.[^progress]

# Who and why

User decision on the advisor's proposal (PR #21).

# What followed

[Inclusivity status](../rules/inclusivity-status.md).

[^progress]: Session 2026-09-26: v1.4.0 released; inclusivity on the whole fragment
