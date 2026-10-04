---
type: NCBI Fact
title: NCBI etiquette and limits
description: 10 s between BLAST contacts, one poll per RID per minute, tool and email, off-peak for large batches, E-utilities 3 or 10 requests per second.
tags: [ncbi, etiquette]
status: draft
stale_after: 2027-04-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, NCBI facts (2026-09-20)
  - id: urlapi
    resource: ../sources/ncbi-blast-urlapi.md
    title: NCBI BLAST Common URL API
  - id: eutils
    resource: ../sources/ncbi-eutils.md
    title: NCBI E-utilities documentation
  - id: ncbi-settings
    resource: ../settings/ncbi.md
    title: Settings - ncbi
---

# Rules the code follows

- BLAST: at least 10 s between contacts; at most one poll per RID per minute; `email` and
  `tool` parameters; more than 100 searches per 24 h go to a slower queue; more than 50 searches
  should run off-peak (weekends or 9 pm-5 am US Eastern); merge short queries into one search of
  up to 1,000 bases.[^urlapi][^arch]
- RIDs are kept for about 36 hours (NCBI training material, not the API page).
- E-utilities: 3 requests per second without an API key, 10 with one.[^eutils]
- Datasets: with an API key the response header read `X-Ratelimit-Limit: 10` (2026-09-23).
- Credentials only from the environment (`NCBI_EMAIL`, `NCBI_API_KEY`), never from files.

The settings that implement this (`blast_min_interval_s` 10, `poll_interval_s` 60, retries with
exponential backoff) are in [Settings - ncbi](../settings/ncbi.md).[^ncbi-settings]

[^arch]: docs/ARCHITECTURE.md, NCBI facts (2026-09-20)
[^urlapi]: NCBI BLAST Common URL API
[^eutils]: NCBI E-utilities documentation
[^ncbi-settings]: Settings - ncbi
