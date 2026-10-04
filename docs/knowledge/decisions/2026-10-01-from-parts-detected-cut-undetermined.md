---
type: Decision
title: "Detectable from parts counts as detected; cut genomes undetermined"
description: "Genomes with every site seen whole on cut copies count as detected; genomes with the region cut or hidden by N are undetermined everywhere."
tags: [decision]
status: draft
decided_on: 2026-10-01
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-30-01-live-runs-fallback-search-blast-blind-spot-wet-lab-classes.md
    title: "Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan"
---

# Decision

"Detectable from parts" counts as detected for every assay (`variants.judge_from_parts: detectable`); genomes whose region is cut by a contig end or hidden by N count as undetermined in both the whole-fragment table (and collection axis) and the channels.[^progress]

# Who and why

User decisions (2026-10-01).

# What followed

Expected and seen for Legionella: the from-parts genomes moved to detected, the cut ones kept it Incomplete ([genome outcome](../rules/genome-outcome.md)).

[^progress]: Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan
