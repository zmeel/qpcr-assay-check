---
type: Grading Rule
title: Inclusivity status
description: The whole-fragment status over the last 3 complete years plus the current one - 95% review, 80% exceeds limit, Incomplete above 25% undetermined.
tags: [inclusivity, status]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: config
    resource: ../settings/inclusivity.md
    title: Settings - inclusivity
  - id: d-window
    resource: ../decisions/2026-09-26-status-on-the-whole-fragment.md
    title: Decision on the whole-fragment status
  - id: d-summary
    resource: ../decisions/2026-09-27-summary-instead-of-verdict.md
    title: Decision on the summary
  - id: d-axis
    resource: ../decisions/2026-10-02-collection-year-status-axis.md
    title: Decision on the status axis
  - id: d-small
    resource: ../decisions/2026-10-01-small-review-points.md
    title: Decision to take up the small review points
---

# Rule

Over the genomes of the **status window** (the last `verdict_window_years` = 3 complete years
plus the current one: the latest release year listed, on either axis; never the last year that
has data, so a target no longer sequenced is not judged on old years, code review 2026-11-17)
whose region was found, the share **detectable** by the
[genome outcome](genome-outcome.md) decides:[^config][^d-window]

| Condition | Status |
|---|---|
| fewer than 100 genomes with the region in the window | Incomplete |
| more than 25% of them undetermined (`max_undetermined_percent`) | Incomplete[^d-small] |
| collection axis: more than 25% without a usable collection year | Incomplete[^d-axis] |
| below 80% (`fail_below_percent`) | Exceeds limit |
| below 95% (`warn_below_percent`), or one year of 30+ genomes below 80% | Review |
| otherwise | No flags |

Not every listed genome assessed yet: Incomplete, and a crossed limit (Review or Exceeds limit)
is held back until coverage is complete (`limits_need_complete_coverage`, since 2026-10-07);
more unavailable records than `max_undetermined_percent` also keep it Incomplete. Possible
deletions (a complete assembly without the region, or a record with the sequence on both sides
but no copy of it) count as likely failure (since 2026-11-17). The statuses
are flag levels, not pass/fail: the tool is not a test that fails or passes.[^d-summary]

# Axis

`status_axis: release` (default) groups genomes by NCBI release year; `collection` by the year
the sample was collected, as its submitter recorded it. The other axis is shown as
information.[^d-axis]

# Information beside the status

- Bracketing: the figure if every undetermined genome were an escape, and if every one were
  detected.
- Distinct site patterns: genomes with identical sites counted once, against the redundancy of
  public data.
- The figure under the other homopolymer setting ([R5b](r5b-homopolymer-length.md)).
- Detection per channel, each over its own target, folded in: the worst status wins.

[^config]: Settings - inclusivity
[^d-window]: Decision on the whole-fragment status
[^d-summary]: Decision on the summary
[^d-axis]: Decision on the status axis
[^d-small]: Decision to take up the small review points
