---
type: Session
title: "The BLAST slow queue"
description: "Session log of 2026-10-20 (afternoon) and 2026-10-21."
tags: [session]
session_date: 2026-10-21
session_label: "2026-10-21"
generated: { by: claude-code/agent, at: 2026-10-21T08:30:00Z }
---

# 2026-10-20/21: the BLAST slow queue

- Looked at dnieuw/primer-check at the user's request (a 2020 Shiny app from Erasmus MC
  Viroscience that counts non-conserved oligo positions in a GISAID alignment). Reported only;
  nothing taken from it. It is AGPL-3.0, so no code from it may be copied into this project.
- The influenza A rerun with both reverse primers stayed WAITING on its target-tier search
  through four restarts. First diagnosis: the search is too large (1,680,151 records for
  `txid11320[ORGN]`, counted live). The user doubted it: earlier runs of the same assay finished.
- NCBI's developer page, read again: more than 100 searches in 24 hours go to a slower queue.
  Added `scripts/blast_queue_check.py` to tell a held queue from an oversized search with one
  small control search. The user ran the control by hand on the NAS: one primer against 10,334
  records, still WAITING after 12 minutes, while the web page returned the same search at once.
  So the searches were held, and the first diagnosis was wrong.
- Every restart more than 90 minutes after submission resubmitted the search
  (`resubmit_after_minutes: 90`), adding submissions and discarding the queued RID. With
  `resubmit_after_minutes` and `max_wait_minutes` at 2000 the 2026-10-21 run resumed the RID and
  found it READY after 1147 minutes; the first report fetch failed with NCBI's formatter error and
  a retry worked.
- The code was checked against every usage guideline and complies; a run submits 3 searches. One
  gap: the 10-second limiter is per process, so simultaneous runs are not coordinated. Why the
  searches were held is unknown.
- The user wrote to NCBI (draft from this session): case CAS-1714885-G5R3Z2. Recorded as
  [the slow queue open item](../open/blast-slow-queue.md), with the etiquette concept updated
  and NCBI's developer page added as a source. The user sees this as a real limit on heavy use
  of the tool; the options are listed in the open item, none built.

# Next

- NCBI's answer to the case; then decide on the options in the open item.
- The influenza rerun: background and exclusivity searches still to finish.
