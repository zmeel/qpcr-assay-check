---
type: Decision
title: "Gaps never hide mismatches; an unpaired end base is a mismatch"
description: "A site whose mismatches already fail keeps that class with a gap; an oligo base without a template partner at an end counts as a mismatch."
tags: [decision]
status: draft
decided_on: 2026-09-26
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-25-03-second-code-review-of-the-unreleased-changes.md
    title: "Session 2026-09-25 (later): Second code review of the unreleased changes"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

A gap can only make a site worse: when the mismatches alone give at risk or likely failure, that class stands, noted "plus a gap". An oligo base at either end without a partner base is a mismatch at that position.[^progress][^mismatch-classes]

# Who and why

User, 2026-09-26, after a probe variant with 7 mismatches and a gap was reported indeterminate.

# What followed

[R5](../rules/r5-gaps.md).

[^progress]: Session 2026-09-25 (later): Second code review of the unreleased changes
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
