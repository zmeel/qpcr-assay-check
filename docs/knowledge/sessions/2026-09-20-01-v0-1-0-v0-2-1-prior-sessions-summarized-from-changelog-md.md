---
type: Session
title: "v0.1.0–v0.2.1 (prior sessions, summarized from CHANGELOG.md)"
description: "Session log of 2026-09-20/21."
tags: [session]
session_date: 2026-09-20
session_label: "2026-09-20/21"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-20/21: v0.1.0–v0.2.1 (prior sessions, summarized from CHANGELOG.md)

- v0.1.0: skeleton, input parsing, oligo QC (primer3-py), report skeleton. No network use.
- v0.2.0: remote BLAST backend (own `requests` client, not `qblast`, so RIDs can be persisted and
  resumed), throttling/backoff, content-addressed cache, tiered taxon-restricted search planning,
  JSON2 parser, `scripts/smoke_test.py`. Validated only against a simulated NCBI.
- v0.2.1: fixes from the first live run of `scripts/smoke_test.py` — most notably a redaction bug
  (the e-mail could leak into logs in its URL-encoded form during a transient error) and several
  NCBI facts confirmed for the first time (see `docs/ARCHITECTURE.md`'s "Verified in the first live
  smoke run" section): short-oligo BLAST parameters accepted as configured, `JSON2_S` report shape,
  `ENTREZ_QUERY` taxon restriction effective but not airtight, human-restricted `core_nt` searches
  take about an hour.
