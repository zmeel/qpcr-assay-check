---
type: Run
title: Legionella, 2026-10-02 (12:22Z, 12:47Z, 13:16Z)
description: Three runs with the collection axis and the cut-genome breakdown; Incomplete because thousands of draft genomes have the region cut by a contig end.
tags: [run, legionella]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: PROGRESS.md, entry 2026-10-02 — Theory-review items 3 and 4
  - id: report
    resource: the user's report of run 2026-10-02T13:16Z on the NAS, read in the session of 2026-10-02
    title: Report of the 13:16Z run (not in the repository)
---

# Runs

[Assay](../assays/legionella-genus-pneumophila.md), started from the browser with
`status_axis: collection`.[^progress]

# Key numbers

- **12:22Z**: Incomplete from the 4,441 cut genomes (48% undetermined in the collection
  window), not from the axis; 313 of 11,174 (2.8%) without a usable collection year. Collection
  2023-2026 93.9% of 1,669; release 97.3% of 4,549; 3,921 genomes released 2017-2026 were
  collected before 2017. Distinct site patterns: 8.
- **12:47Z, cut-genome breakdown** of the 4,441: probe site cut with both primers detectable
  2,632 (contig ends inside the probe, likely the rRNA-operon repeat); forward cut 789; reverse
  cut 459; reverse and probe 201; fragment not in the assembly 161; forward and probe 93; a site
  cut with a whole one failing 104; every site whole but not all detectable 2.
- **13:16Z**, after the [decision](../decisions/2026-10-02-cut-genomes-and-unassembled-fragments.md):
  cut 4,280, region not found 259, undetermined 46.1%; still Incomplete.[^report]

Earlier (2026-09-30, overhaul code before v2.0.0): 11,911 assemblies; the 25 complete-genome escapes are other
Legionella species where the genus probe fails (L. anisa, L. micdadei, F. dumoffii and others);
signal of the pneumophila channel in 2 non-pneumophila genomes.

[^progress]: PROGRESS.md, entry 2026-10-02 — Theory-review items 3 and 4
[^report]: Report of the 13:16Z run (not in the repository)
