---
type: Open Item
title: "R7 note and the pair flag at 4+ mismatches"
description: "Degenerate primers are only a note, and pairs with 4 or more mismatches in total are not flagged yet."
tags: [open, small]
status: draft
origin: "review 11"
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md, section 9"
---

# What is open

[R7](../rules/r7-degenerate-primers.md) has no class effect; [R8](../rules/r8-primer-pair.md) planned a flag for pairs with >= 4 mismatches in total (2/2, 1/3, 1/4), where the worse single class may understate.[^mismatch-classes]

# What it needs

The user's go-ahead.

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, section 9
