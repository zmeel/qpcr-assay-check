---
type: Decision
title: "E-value stays 1000; score floor and partner scan built"
description: "Keep EXPECT 1000, compute what each search could report, and scan for partner primers and probes next to off-target primer sites."
tags: [decision]
status: draft
decided_on: 2026-09-30
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-09-30 — Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan"
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: "docs/ARCHITECTURE.md"
---

# Decision

EXPECT stays 1000 (1e5 nearly filled the 5,000-hit list); build the score floor per tier and oligo from the report's own search statistics, and the partner scan with probe re-alignment in off-target products (`specificity.partner_scan_max_windows` 1000). Not built: a reference-fragment BLAST per off-target tier.[^progress][^arch]

# Who and why

User: "Build 2 and 3", after the smoke-test E-value sweep.

# What followed

[Specificity findings](../rules/specificity-findings.md), [BLAST URL API facts](../ncbi/blast-url-api.md).

[^progress]: PROGRESS.md, entry 2026-09-30 — Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan
[^arch]: docs/ARCHITECTURE.md
