---
type: Decision
title: "One generic assay model - loci and channels"
description: "Oligos, loci and channels for simple, multi-oligo and multiplex assays; run history, panel command and sampled BLAST-hit inclusivity removed."
tags: [decision]
status: draft
decided_on: 2026-09-29
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../../PROGRESS.md
    title: "PROGRESS.md, entry 2026-09-29 — Overhaul round 2: a generic assay model (advisor); user decisions"
  - id: spec
    resource: ../../SPEC.md
    title: "docs/SPEC.md (amendments)"
---

# Decision

One generic tool for one primer pair and probe, several oligos on one region (Neisseria), and several regions or target taxa (Legionella, multiplexes): assay = oligos -> loci -> channels (one per reporter). No run history in the report; the panel command and the sampled BLAST-hit inclusivity are removed; an incremental store per locus is kept. No locus in a complete genome = not detected (possible deletion). Legionella: genus probe VIC, L. pneumophila probe FAM; the genus channel targets taxid 444 (Legionellaceae). Out-of-scope taxa in a channel's scan are information only.[^progress][^spec]

# Who and why

User: "everything on the table"; the advisor's plan.

# What followed

Overhaul steps 1-8 built ([components](../components/index.md)); SPEC amended. Only the first locus of a multi-locus assay is analysed so far ([open](../open/every-locus.md)).

[^progress]: PROGRESS.md, entry 2026-09-29 — Overhaul round 2: a generic assay model (advisor); user decisions
[^spec]: docs/SPEC.md (amendments)
