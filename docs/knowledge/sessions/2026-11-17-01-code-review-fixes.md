---
type: Session
title: "Whole-project code review: seven fixes"
description: "Session log of 2026-11-17."
tags: [session]
session_date: 2026-11-17
session_label: "2026-11-17"
generated: { by: claude-code/agent, at: 2026-11-17T12:00:00Z }
---

# 2026-11-17: code review of the whole project, seven fixes

- Correction: the HSV-1 run and assay pages said the status was judged on genomes collected
  2023-2026; the report says 2020-2023 ([run](../runs/hsv1-2026-10-23.md)).
- The code review of `src/`, `scripts/` and `tests/` found seven defects; the user asked to fix
  all seven ("fix 1-7"):
  1. A RID NCBI called UNKNOWN was resubmitted with no limit and no deadline; UNKNOWN is also
     what a status page without a status reads as, so a persistent error page meant a new search
     every minute. Now one resubmission per run, then an error
     ([etiquette](../ncbi/etiquette.md)).
  2. Each degenerate variant of a primer is a query of its own, so one off-target product was
     counted once per pair of variants (up to 64 times with the HSV-1 primers) and filled
     `max_amplicons` and the partner-scan windows. The variants at one site are now one site
     ([specificity](../components/specificity.md)).
  3. `variants.nucleotide_query` is not in the variant store key, and completeness compared counts:
     a narrowed query (as the VZV file suggests) reused the full store and read as complete;
     withdrawn records stayed in the figures. The figures now count the stored records listed in
     this run, and the report says how many were left out
     ([exhaustive analysis](../components/exhaustive-analysis.md)). The store key is unchanged on
     purpose: adding the query would have forced a full rescan of every stored assay, influenza A
     with 173,689 records among them.
  4. In an MGB probe an ambiguity code at -6 or -7 read as a match although one mismatch there is
     likely failure; R6 now grades a code anywhere in an MGB probe both ways
     ([R6](../rules/r6-ambiguity-codes.md), back to draft).
  5. A failed window fetch around a BLAST hit stored the record as "not found" for good; it is now
     left for the next run and counts as unavailable after two failed runs.
  6. Every run summarised every listed record again (ESummary); UID lookups are now kept beside
     the store.
  7. The status window ended at the last year with data, not at the current year as the rule and
     the report say ([inclusivity status](../rules/inclusivity-status.md)). A target no longer
     sequenced now reads Incomplete for want of recent genomes. Window spans in the report now
     name the whole window (e.g. 2023-2026) rather than the years that had data.
- A candidate finding was dropped on checking: N bases in re-aligned partial hits are already
  measured as mismatches.
- The advisor's whole-project evaluation stopped twice on the usage limit and then because the
  model asked for needs usage credits; no report.
