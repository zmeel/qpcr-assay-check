---
type: Session
title: "Exclusivity/target fix confirmed live; history/diff confirmed on real data"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: Exclusivity/target fix confirmed live; history/diff confirmed on real data

The user rebuilt the Docker image with the previous entry's fix and re-ran the exact same full
`run` (same cache, so no new NCBI calls were needed for the unaffected tiers). Both new pieces of
this phase's work — the exclusivity/target-taxid fix and the history/diff feature itself — are now
confirmed working correctly together against real data, in the same report:

- Predicted off-target products dropped from 500 to 0 (that section flipped to `PASS`).
- The "Changes since the previous run" section correctly attributed this to the fix: "6028
  off-target site(s) no longer found" and "500 predicted off-target product(s) no longer found" —
  matching, almost exactly, the bogus counts from the buggy run. The exclusivity table's row for
  SARS-CoV-2 now reads "assay's own intended target — excluded from this search", as designed.
- The run is still `FAIL`, but now for a real reason: documented homology between the CDC N1
  primers and the human genome, found independently by both the `background` tier and the
  `exclusivity` tier (since "Homo sapiens" is *also* separately listed in the packaged organism
  list — the same organism searched twice, for two different reasons; redundant, not wrong).
- The diff also showed 43 "new" minor-severity Influenza A sites, worth a moment's thought before
  concluding they were fine: removing SARS-CoV-2 from the exclusivity tier's taxid list shifted
  which of the remaining ~38 organisms share a `max_taxids_per_search` chunk, which shifted which
  hits rank inside that chunk's own `max_sites_per_query` cap, surfacing hits that were previously
  crowded out. A correct, expected side effect of the fix, not a new issue.

Updated `docs/ARCHITECTURE.md` (added a "retry, with the fix applied" verified section) and
`CHANGELOG.md` (Known limitations: the fix is now confirmed live, not just unit/CLI-tested; the
history/diff feature has now been checked against one real two-run pair, not only the constructed
test world). No code changes this round — this was purely closing the verification loop on the
previous fix.
