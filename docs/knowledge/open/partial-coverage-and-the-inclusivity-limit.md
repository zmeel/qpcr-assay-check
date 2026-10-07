---
type: Open Item
title: An inclusivity FAIL on partly assessed records
description: The inclusivity status could read "Exceeds limit" while coverage was still Incomplete, on a subset biased by the newest-first order. The user chose to hold a crossed limit back; built 2026-10-07.
tags: [open, question, inclusivity, coverage, closed]
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

# Decided: hold it back, 2026-10-07

The user chose the middle option ("Keep incomplete for now"). While genomes or records are still
to assess, a crossed limit no longer decides the status: the verdict is Incomplete and the
sentence names what the limit would have made it, for example

> Status: Incomplete (Exceeds limit (below 80%) on the collected genomes assessed so far, held
> back while genomes are still to assess: the newest are assessed first, so this subset is
> weighted to the most recent year; setting inclusivity.limits_need_complete_coverage)

so the reviewer sees the warning without a filed Review or Exceeds limit, and the counts line
("127,768 of 172,768 listed records not assessed yet") stays beside it. The new setting
`inclusivity.limits_need_complete_coverage` (default true) turns it off for a laboratory that
wants the genomes assessed so far judged as they stand.

This reverses a deliberate earlier rule: the guide used to say the status is Incomplete "unless
the figure is already below the FAIL limit", and the code kept a FAIL (code review 2026-09-27
had asked only that missing evidence never read as no flags). The phrasing lives in
`fragment_verdict`, which has the limits to name; `pipeline.py` adds the counts as before.[^rules]

Covered by `test_a_crossed_limit_is_held_back_while_genomes_are_still_to_assess`: both a FAIL and
a WARN held back with the sentence naming them, a PASS untouched, the limits deciding again once
coverage completes, and the setting turning the hold-back off.

[^run]: "Influenza A (matrix), 2026-10-07 (16:14Z)"
[^rules]: How the inclusivity status is decided
[^spec]: docs/SPEC.md
