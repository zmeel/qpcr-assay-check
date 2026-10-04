---
type: Decision
title: "Variant analysis from every genome assembly"
description: "Both sources: NCBI Datasets genome downloads scanned locally for exhaustive runs, partitioned remote BLAST kept for targets without assemblies."
tags: [decision]
status: draft
decided_on: 2026-09-23
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-23-07-report-states-when-human-background-was-skipped.md
    title: "Session 2026-09-23: Report states when human background was skipped"
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: "docs/ARCHITECTURE.md"
---

# Decision

Both options: stream genome assemblies from NCBI Datasets and scan them for the amplicon region (exhaustive over all assemblies), and keep partitioned remote BLAST for quick checks and targets without assemblies (`variants.source`). Only the extracted target regions are kept, never a genome database (CLAUDE.md hard rule, relaxed for this).[^progress][^arch]

# Who and why

User priority: the variant analysis is the most important part of the tool and must be as exhaustive as possible.

# What followed

Built as v1.1.0. core_nt excludes WGS drafts, where most bacterial assemblies live, so BLAST alone would miss most bacterial data. Every limit is a setting (budget questions were not answered).

[^progress]: Session 2026-09-23: Report states when human background was skipped
[^arch]: docs/ARCHITECTURE.md
