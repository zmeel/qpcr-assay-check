---
type: Open Item
title: "Split taxon lists per tier, not per search"
description: "max_taxids_per_search 1 split every tier into many searches; a per-tier split is the proper fix."
tags: [open, medium]
status: draft
origin: "since 2026-09-30"
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md"
---

# What is open

With `search.max_taxids_per_search` 1 the enterovirus run made 36 out-of-scope searches, one queued over 2 h at NCBI; the setting was removed from the example.[^progress]

# What it needs

The user's go-ahead.

[^progress]: PROGRESS.md
