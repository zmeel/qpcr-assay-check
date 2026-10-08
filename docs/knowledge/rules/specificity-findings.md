---
type: Grading Rule
title: Specificity findings
description: Off-target sites as critical or warning by mismatches, gaps and clean 3' bases; products paired from facing primer sites; severities per finding.
tags: [specificity, off-target]
status: stable
verified: { by: human:zmeel, at: 2026-10-08T07:41:00Z }
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

Primer sites facing each other on one record within `max_amplicon_size` (2,000 bp) form a
predicted product; a product with a critical probe site inside is "likely detected". Severities:
a critical primer site in a product FAIL, one without a product WARN, a warning site WARN, a
product likely detected FAIL, one not detected WARN, a probe site alone INFO. Must-not-detect taxa
are judged on products; out-of-scope taxa are information only.

These off-target rules are not the graded classes used on the target; one rule set for both is an
[open item](../open/unified-off-target-rules.md).

# What the search can reach

Word size 7 and E-value 1000: a site without a run of 7 matching bases is never reported, and the
smallest reportable score per tier and oligo is computed from the search statistics. The partner
scan finds the second primer and the probe next to a reported primer site.[^arch] See
[BLAST URL API](../ncbi/blast-url-api.md) and [the score-floor decision](../decisions/2026-09-30-expect-1000-score-floor-partner-scan.md).

[^config]: Settings - specificity
[^arch]: docs/ARCHITECTURE.md, NCBI facts and v0.2.0 implementation
