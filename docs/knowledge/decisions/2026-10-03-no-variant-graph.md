---
type: Decision
title: "No graph of the variants for now"
description: "Variant maps were shown as mock-ups only; the amplicon export script was removed again."
tags: [decision]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T14:34:00Z }
decided_on: 2026-10-03
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-05-visualisation-examples-not-built.md
    title: "Session 2026-10-02: Visualisation examples (not built)"
---

# Decision

No variant graph in the tool for now. `scripts/export_amplicons.py` and its test were removed (merged in PR #69, removed in PR #70); the published mock-ups stay as examples only.[^progress]

# Who and why

User: "For now no graph of the variants. Remove code" (2026-10-03).

# What followed

Assessment given: the site-pattern map is exploratory only; the whole-amplicon map is the meaningful version, if one is built later.

[^progress]: Session 2026-10-02: Visualisation examples (not built)
