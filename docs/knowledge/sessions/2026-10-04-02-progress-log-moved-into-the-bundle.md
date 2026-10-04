---
type: Session
title: "Progress log moved into the bundle"
description: "Session log of 2026-10-04 (later)."
tags: [session]
session_date: 2026-10-04
session_label: "2026-10-04 (later)"
generated: { by: claude-code/agent, at: 2026-10-04T06:00:00Z }
---

# 2026-10-04 (later): Progress log moved into the bundle

- PR #72 (review items 8, 6, 9 and the knowledge bundle) merged by the user; the branch was
  restarted from main for this work.
- User: "Is it not more readable if progress moves to the knowledge base?" Advice given (one page
  per session, a status page, log.md generated from the pages, PROGRESS.md as a pointer, CLAUDE.md
  changed); user: "Go ahead including Claude.md changes".
- Moved the 39 dated PROGRESS.md entries verbatim into `docs/knowledge/sessions/`
  (`<date>-<nn>-<slug>.md`, `nn` in order within a day; checked by script that every body is
  word for word in the old file). The old file's "Open questions carried across sessions" went
  into status.md (the licence note to open/license-note.md; the smoke-test and tag notes were
  outdated and are marked so).
- Concepts that cited PROGRESS entries now cite the session pages; entries cited by date range
  were mapped to the session that holds the cited facts. Each session page lists its citing
  concepts under "Related"; tests/test_knowledge_bundle.py checks the back-links.
- New: status.md (read first), decision
  [2026-10-04-progress-into-sessions](../decisions/2026-10-04-progress-into-sessions.md).
  build_knowledge.py writes log.md from the session pages. CLAUDE.md lines 3-4 changed to point
  to status.md and the session pages; docs/PROGRESS.md is a pointer; references in
  ARCHITECTURE.md, clinical_pathogen_panels.md and probe_variant_sources.py updated (the
  reviews in docs/reviews/ are verbatim and still say PROGRESS.md).
- User: "Make the viewer" (after the advice on what to do with the bundle). Built
  `scripts/knowledge_viewer.py` + `knowledge_viewer.html`: one self-contained HTML file
  (`work/knowledge-viewer.html`, gitignored; about 580 kB with IBM Plex embedded from the GUI's
  fonts) with a map of the concepts (colour and shape per folder, a ring for concepts verified by
  a person), a list with review state, search, and a reading panel (rendered text, sources, links
  out, cited by, GitHub link). Checked in Chromium (desktop light/dark, 400 px phone; no console
  errors, no sideways scroll). tests/test_knowledge_viewer.py. Also published as a private
  artifact for a first look.

# Related

* [The progress log moves into the bundle as session pages](../decisions/2026-10-04-progress-into-sessions.md)
