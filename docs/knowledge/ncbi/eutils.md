---
type: NCBI Fact
title: E-utilities - what the code relies on
description: ESearch paging past a million records, EFetch accession lists, ESummary dates, taxonomy lookups, and nuccore collection dates.
tags: [ncbi, eutils]
status: draft
stale_after: 2027-04-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: eutils
    resource: ../sources/ncbi-eutils.md
    title: NCBI E-utilities documentation
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, v1.1.0 design, target exclusions
  - id: progress
    resource: ../sessions/2026-09-30-01-live-runs-fallback-search-blast-blind-spot-wet-lab-classes.md
    title: "Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan"
---

# Measured live

- ESearch `retstart` beyond a million (up to 3,571,940, the last SARS-CoV-2 2022 record) returned
  exactly one UID each (2026-09-23).[^arch]
- EFetch `rettype=acc` by POST with 100 UIDs returned one accession.version per UID.
- ESearch honours `NOT` exactly when subtracting excluded taxa (enterovirus, 2026-09-25).
- Taxonomy names can mislead: the name "rhinovirus" resolves to the genus Enterovirus (12059)
  itself, so rhinoviruses must be given by taxonomy ID.
- nuccore ESummary `subtype`/`subname` carries the collection date (e.g. LC951483.1 collected
  2021-12-03), checked 2026-09-30.[^progress]

Request limits and identification: [etiquette](etiquette.md).[^eutils]

[^eutils]: NCBI E-utilities documentation
[^arch]: docs/ARCHITECTURE.md, v1.1.0 design, target exclusions
[^progress]: Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan
