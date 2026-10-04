---
type: Decision
title: "Run history as a required section (withdrawn)"
description: "A first run was Incomplete until a previous run existed; withdrawn on 2026-09-29 when the run history was removed."
tags: [decision]
status: deprecated
decided_on: 2026-09-22
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-22-04-v1-0-0-started-run-history-diff-implemented-docker-written.md
    title: "Session 2026-09-22: v1.0.0 started: run history + diff implemented; Docker written but unverified"
---

# Decision

The "history" section (changes since the previous run) is required like every other section, so a brand-new assay's first run is honestly Incomplete.[^progress]

# Who and why

The user agreed with the recommendation.

# What followed

v1.0.0 built the history and diff. On 2026-09-29 the user dropped the run history from the report ([generic assay model](2026-09-29-generic-assay-model.md)); this decision no longer applies.

[^progress]: Session 2026-09-22: v1.0.0 started: run history + diff implemented; Docker written but unverified
