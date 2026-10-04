---
type: Decision
title: "Homopolymer bulges graded; laboratory evidence entries"
description: "Primer run-length differences get class R5b instead of indeterminate; an evidence entry in the assay file can override a class with the lab's result."
tags: [decision]
status: draft
decided_on: 2026-09-26
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-09-25 (later) — Second code review of the unreleased changes"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

A homopolymer length difference in a primer is at risk (one base, run outside the last 3 nt) or likely failure (R5b), with a breakdown of how far to trust run-length variants. The assay file gets `evidence:` entries (rule LAB) for variants the laboratory has tested.[^progress][^mismatch-classes]

# Who and why

Advisor proposal, built on the user's go-ahead.

# What followed

[R5b](../rules/r5b-homopolymer-length.md), [LAB](../rules/lab-evidence.md). No PCR study measured such bulges; the class is ours.

[^progress]: PROGRESS.md, entry 2026-09-25 (later) — Second code review of the unreleased changes
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
