---
type: Decision
title: "No graph of the variants for now"
description: "Variant maps were shown as mock-ups only; the amplicon export script was removed again."
tags: [decision]
status: draft
decided_on: 2026-10-03
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-10-02 — Visualisation examples (not built)"
---

# Decision

No variant graph in the tool for now. `scripts/export_amplicons.py` and its test were removed (merged in PR #69, removed in PR #70); the published mock-ups stay as examples only.[^progress]

# Who and why

User: "For now no graph of the variants. Remove code" (2026-10-03).

# What followed

Assessment given: the site-pattern map is exploratory only; the whole-amplicon map is the meaningful version, if one is built later.

[^progress]: PROGRESS.md, entry 2026-10-02 — Visualisation examples (not built)
