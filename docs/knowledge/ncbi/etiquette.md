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
  - id: devinfo
    resource: ../sources/ncbi-blast-developer-info.md
    title: NCBI BLAST developer information and usage guidelines
  - id: slow-queue
    resource: ../open/blast-slow-queue.md
    title: BLAST searches held for a day by a change at NCBI
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

# A held search, seen from the client (2026-10-20/21)

The guidelines were read again on 2026-10-20 from NCBI's developer page, which states them in
full.[^devinfo] From 2026-10-20 the user's API searches were held - by a change at NCBI, which
NCBI then rolled back, not by the slower queue for heavy users - and this is what it looked
like:[^slow-queue]

- **Nothing reports it.** The status stays `WAITING`; no error, no `FAILED`, no message. A held
  search looks exactly like a slow one, so only a small control search tells them apart
  (`scripts/blast_queue_check.py`).
- **The web page is not held.** NCBI gives "priority to interactive users": the same primer
  returned at once in a browser while the API search waited.
- **It lasts.** A held target-tier search was READY after 1147 minutes (about 19 hours).
- **A ready search can still fail to format.** Its first JSON2_S fetch returned HTTP 502 and the
  "SYSTEM CAN'T PROCESS YOUR REQUEST" page; a retry a minute later worked.
- **The limiter is per process.** Two runs at once each keep their own 10-second clock.

A run submitted 3 searches and the code follows every guideline. NCBI's answer (case
CAS-1714885-G5R3Z2): "The developers made a change recently that could account for the slowness
(long WAITING times) you observed. This change is being rolled back sometime today." The slower
queue may look the same from the client; that was not tested.

[^arch]: docs/ARCHITECTURE.md, NCBI facts (2026-09-20)
[^urlapi]: NCBI BLAST Common URL API
[^eutils]: NCBI E-utilities documentation
[^ncbi-settings]: Settings - ncbi
[^devinfo]: NCBI BLAST developer information and usage guidelines
[^slow-queue]: BLAST searches held for a day by a change at NCBI
