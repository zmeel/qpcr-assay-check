---
type: Grading Rule
title: R2 - one mismatch beyond the last 5 nt of a primer
description: Tolerated; moderate at -6 to -8 and almost negligible from -9 on, after Lefever 2013.
tags: [grading, primer, R2]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: lefever
    resource: ../sources/lefever-2013.md
    title: Lefever et al. 2013
---

# Rule

A single mismatch beyond the last 5 nt is `tolerated`, noted "moderate effect, can be
tolerated" at -6 to -8 and "almost negligible" from -9 on (Lefever counts from 0 at the
terminus, so their position 8 is -9 here).[^lefever] Both notes rest on one experiment (one mix,
supplementary data not checked); the report says so. Keeping -6 to -8 at `tolerated` keeps the
classes monotonic, since R1 already gives `tolerated` at -3 to -5 for every group with Taq on
DNA. Lefever tested only the 3'-most 16 nt of 20-mers; farther positions are untested.

[^lefever]: Lefever et al. 2013
