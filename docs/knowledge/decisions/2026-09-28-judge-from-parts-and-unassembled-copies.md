---
type: Decision
title: "Genomes judged from parts; copies possibly unassembled; copy identity"
description: "Introduced the 'detectable from parts' class, 'copies possibly unassembled' for multi-copy drafts and the 0.75 copy-identity threshold."
tags: [decision]
status: draft
decided_on: 2026-09-28
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-28-02-legionella-probe-channels-judged-from-parts-copy-threshold.md
    title: "Session 2026-09-28 (later): Legionella; probe channels; judged from parts; copy threshold advice"
---

# Decision

Genomes whose copies are all cut but carry detectable sites of every role get their own class (setting `judge_from_parts`, then default undetermined); multi-copy draft genomes with fewer copies than complete genomes and a failing best copy are "copies possibly unassembled" (`multicopy_unassembled`); a region counts as a copy only above identity 0.75 to the reference.[^progress]

# Who and why

User requests after the first Legionella and Neisseria runs; defaults on the advisor's advice.

# What followed

The from-parts default changed to detectable on 2026-10-01 ([decision](2026-10-01-from-parts-detected-cut-undetermined.md)); the identity threshold became rule (c) of the [copy rule](../rules/copy-rule.md).

[^progress]: Session 2026-09-28 (later): Legionella; probe channels; judged from parts; copy threshold advice
