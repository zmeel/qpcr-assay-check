---
type: Grading Rule
title: Specificity findings
description: Off-target sites as critical or warning by counts, and graded by R1-R9; a site graded likely failure never primes or binds; products paired from facing primer sites; severities per finding.
tags: [specificity, off-target]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: config
    resource: ../settings/specificity.md
    title: Settings - specificity
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, NCBI facts and v0.2.0 implementation
---

# Rule

BLAST hits are re-aligned over the whole oligo and classified (defaults):[^config]

| Level | Primer site | Probe site |
|---|---|---|
| critical | at most 3 mismatches, no gap, 5 clean 3' nt | at most 3 mismatches, no gap |
| warning | at most 5 mismatches, 1 gap, 3 clean 3' nt | at most 5 mismatches, 1 gap |

Since 2026-11-17 (whole-project review, P3; `specificity.graded_off_target: true`) every
off-target site also gets the class the target's sites get ([R1-R9](index.md); MGB rules for an
MGB probe; an unread base N counts as a mismatch). A site graded **likely failure never primes or
binds** (e.g. 3 primer mismatches in the 3'-most 16 nt, R3; one mismatch under an MGB, R9); one
graded **perfect or tolerated always does** (e.g. a terminal G3 mismatch, which the counts called
minor); at risk and indeterminate ones need the level that acted before (critical or warning for
a primer, `probe_binds_if` for a probe). The classes rest on near-identical target sequences and
count primer mismatches only in the 3'-most 16 nt, so for distant sequence the levels still bound
the rest.

Primer sites that can prime, facing each other on one record within `max_amplicon_size` (2,000
bp), form a predicted product; a product with a probe site that binds inside is "likely
detected". Severities: a critical primer site in a product WARN (FAIL before 2026-11-17: priming
alone; Exceeds limit now comes from detection), one without a product WARN, a warning site WARN,
a product likely detected FAIL, one not detected WARN, a probe site alone INFO. Must-not-detect
taxa are judged on products; out-of-scope taxa are information only.

The page was verified on 2026-10-08 for the count-based rule alone, so it is back to draft.

# What the search can reach

Word size 7 and E-value 1000: a site without a run of 7 matching bases is never reported, and the
smallest reportable score per tier and oligo is computed from the search statistics. The partner
scan finds the second primer and the probe next to a reported primer site.[^arch] See
[BLAST URL API](../ncbi/blast-url-api.md) and [the score-floor decision](../decisions/2026-09-30-expect-1000-score-floor-partner-scan.md).

[^config]: Settings - specificity
[^arch]: docs/ARCHITECTURE.md, NCBI facts and v0.2.0 implementation
