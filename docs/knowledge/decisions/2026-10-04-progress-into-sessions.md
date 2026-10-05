---
type: Decision
title: "The progress log moves into the bundle as session pages"
description: "PROGRESS.md becomes one page per session in sessions/, with a short status page read first; CLAUDE.md points to them."
tags: [decision]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T14:35:00Z }
decided_on: 2026-10-04
generated: { by: claude-code/agent, at: 2026-10-04T06:00:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-04-02-progress-log-moved-into-the-bundle.md
    title: "Session 2026-10-04: Progress log moved into the bundle"
---

# Decision

The progress log moves into the bundle: every PROGRESS.md entry becomes its own page in
[sessions/](../sessions/index.md), moved verbatim; [status.md](../status.md) holds the current
state and is read first; `log.md` is generated from the session pages; `docs/PROGRESS.md` stays
as a short pointer. CLAUDE.md now says to read status.md and the newest session pages at the
start of a session, and to update status.md and add a session page before ending one.[^progress]

# Who and why

User: "Is it not more readable if progress moves to the knowledge base?", then "Go ahead
including Claude.md changes". One 1,800-line file was hard to read; decisions, runs and rules were
already split out in the bundle.

# What followed

Concepts that cited a PROGRESS entry now cite its session page, and each session page links back
to them under "Related"; a test checks those back-links. This replaces the part of the
[bundle decision](2026-10-04-knowledge-bundle.md) that kept PROGRESS.md as the session log.

[^progress]: Session 2026-10-04: Progress log moved into the bundle
