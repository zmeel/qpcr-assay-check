---
type: Session
title: "v0.3.0 pushed; pruning bounds validated live"
description: "Session log of 2026-09-21."
tags: [session]
session_date: 2026-09-21
session_label: "2026-09-21"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-21: v0.3.0 pushed; pruning bounds validated live

- Pushed the v0.3.0 commit to `origin/claude/brave-dirac-1vppye` (user confirmed).
- Created an annotated `v0.3.0` tag locally, but **pushing it was blocked**: the sandbox's egress
  proxy returned an HTTP 403 specifically for the tag ref (the branch push to the same host had just
  succeeded), which the proxy's own guidance identifies as an organization policy denial, not a
  transient failure — so it was not retried or routed around. Also discovered the "no git tags
  exist" note from the previous session was wrong: v0.1.0/v0.2.0/v0.2.1 tags do exist on the remote;
  this sandbox's clone had just never fetched them. Told the user to pull the branch and push (and
  tag) themselves from their own machine (a Synology NAS running code-server in Docker), where the
  restriction likely doesn't apply.
- The user ran `scripts/validate_assessment.py` live (CDC N1 example, `--tier background`) and
  pasted back `validation_out/validation_report.json`: 905 relevant alignments, 244 ruled out
  without fetching, 661 needing a fetch (replaces the earlier unmeasured "about 1,500" guess),
  80-hit sample checked (40 fetchable, 40 ruled out), **0 contradictions**. Updated README.md,
  `docs/ARCHITECTURE.md` and `CHANGELOG.md` to reflect this: the pruning bounds are no longer
  described as "unverified," but as checked once, on a sample, for one assay's background tier —
  not exhaustive proof, and worth re-running for other tiers/assays or after logic changes.
- `scripts/smoke_test.py` still has not been re-run since 0.2.1 — still open.
