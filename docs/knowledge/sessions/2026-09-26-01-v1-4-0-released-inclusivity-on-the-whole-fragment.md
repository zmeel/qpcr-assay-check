---
type: Session
title: "v1.4.0 released; inclusivity on the whole fragment"
description: "Session log of 2026-09-26."
tags: [session]
session_date: 2026-09-26
session_label: "2026-09-26"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-26: v1.4.0 released; inclusivity on the whole fragment

- v1.4.0 released: PR #20 merged (5b56c3f), tag v1.4.0 set by the user on the merge commit. CI
  runs `ruff format --check` too: run it before every commit.
- Inclusivity status on the whole fragment over the last 3 complete years plus the current one
  (advisor; user decision; PR #21). Live runs on it (Neisseria 79.0% of 49,614; enterovirus
  90.7% of 4,503, 99.4% including at risk, mostly the at-risk poliovirus 2 F2 variant) led to
  the per-year table fixes (same base as the status, window row) in PR #22.

# Related

* [Inclusivity status on the whole fragment over a window](../decisions/2026-09-26-status-on-the-whole-fragment.md)
