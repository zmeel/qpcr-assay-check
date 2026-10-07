---
type: Open Item
title: An inclusivity FAIL on partly assessed records
description: The inclusivity status can read "Exceeds limit" while coverage is still Incomplete, on a subset that is biased by the newest-first order. Whether a FAIL should be held back to Incomplete is the user's call.
tags: [open, question, inclusivity, coverage]
status: draft
generated: { by: claude-code/agent, at: 2026-10-07T18:00:00Z }
sources:
  - id: run
    resource: ../runs/influenza-a-2026-10-07-16h.md
    title: "Influenza A (matrix), 2026-10-07 (16:14Z)"
  - id: rules
    resource: ../rules/inclusivity-status.md
    title: How the inclusivity status is decided
  - id: spec
    resource: ../../SPEC.md
    title: docs/SPEC.md
---

# The question

In the influenza run of 2026-10-07 16:14Z the summary says **Exceeds limit** for target
detection ("below your limit of 80% detectable", 76.9%) while the row under it says coverage is
**Incomplete**, with 127,768 of 172,768 records still to assess.[^run] The overall verdict is
Exceeds limit.

Both rows are honest on their own and each states its scope. The question is whether a FAIL on
inclusivity should be reached at all before coverage completes, because the assessed subset is
not a random one: records are worked newest publication year first, so a partial run is weighted
to the most recent year. In this run 2026 is fully assessed at 86.1% detectable, half of 2025 at
75.2%, and 2024 and earlier not at all; the headline had already moved 85.4% -> 83.6% -> 76.9%
as coverage grew, crossing the limit on the way.

Arguments both ways:

- **Hold it back to Incomplete.** A filed record that says "Exceeds limit" on 26% of the
  population invites a decision that the next run may reverse in either direction. The project's
  own rule is never to present a sample as the full population,[^spec] and the status is meant to
  be the thing a reviewer acts on.
- **Leave it.** The figure being below the limit on 45,000 records is real information now, and
  waiting for a 172,768-record pass to finish could take many runs. An early warning is useful,
  and the Incomplete coverage row is right next to it.

A middle option: keep the FAIL but require coverage, i.e. report Incomplete as the overall
verdict while naming the inclusivity figure and its limit in the same row, so the reviewer sees
the warning without a filed FAIL.

Not built, and nothing was changed: this is a decision about what the status means, not a
defect.[^rules]

[^run]: "Influenza A (matrix), 2026-10-07 (16:14Z)"
[^rules]: How the inclusivity status is decided
[^spec]: docs/SPEC.md
