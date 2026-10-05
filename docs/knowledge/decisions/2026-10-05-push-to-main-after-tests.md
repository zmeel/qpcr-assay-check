---
type: Decision
title: "Push to main after the tests pass, without asking"
description: "Work goes straight to main once ruff and the test suite pass; no pull request and no go-ahead per push. Tags stay the user's."
tags: [decision, workflow]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T14:35:00Z }
decided_on: 2026-10-05
generated: { by: claude-code/agent, at: 2026-10-05T11:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-05-01-entamoeba-histolytica-assay.md
    title: "Session 2026-10-05: Entamoeba histolytica assay"
  - id: claude-md
    resource: ../../../CLAUDE.md
    title: CLAUDE.md, Git section
---

# Decision

Finished work is committed and pushed to `main` directly: no pull request, and no separate
go-ahead for each push. The gate is the checks, not a question: `ruff check .`,
`ruff format --check .` and `pytest -m "not live"` must pass first; when something fails, it is
fixed or reported, and nothing is pushed. Each push is named in the reply. Force-pushing stays
forbidden, and the annotated tags stay the user's to set and push.[^claude-md][^progress]

# Who and why

User, 2026-10-05: "Push to main", then "No, keep pushing to main" and "Yes, update Claude.md to
push to main after running tests". Until then every push needed a go-ahead and went through a
pull request on a working branch, which cost a round trip per change.

# What followed

CLAUDE.md's Git section rewritten accordingly (it had said "Never push without asking me
first"). PRs #72, #73 and #74 were the last ones of the old workflow.

[^progress]: Session 2026-10-05: Entamoeba histolytica assay
[^claude-md]: CLAUDE.md, Git section
