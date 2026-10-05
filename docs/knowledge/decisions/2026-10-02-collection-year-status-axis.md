---
type: Decision
title: "Collection year as an optional status axis; 25% undated limit"
description: "inclusivity.status_axis release | collection; with collection, more than 25% undated genomes gives Incomplete."
tags: [decision]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T14:30:00Z }
decided_on: 2026-10-02
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-03-theory-review-items-3-and-4.md
    title: "Session 2026-10-02: Theory-review items 3 and 4"
---

# Decision

`inclusivity.status_axis: release | collection` (default release); with collection, genomes without a usable collection year are left out and counted, and more than `max_undetermined_percent` (25%) of them gives Incomplete. Distinct site patterns are shown as information.[^progress]

# Who and why

User: "Start with 3 and 4", then "Use 25% limit".

# What followed

Legionella (collection axis): Incomplete from the cut genomes, 2.8% undated. Neisseria: 85.8% by collection year vs 89.0% by release ([runs](../runs/index.md)).

[^progress]: Session 2026-10-02: Theory-review items 3 and 4
