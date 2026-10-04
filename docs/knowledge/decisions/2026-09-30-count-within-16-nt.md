---
type: Decision
title: "Mismatch counts within the 3'-most 16 nt; R3b"
description: "R3 and R8 count only mismatches within the 3'-most 16 nt; mismatches beyond get their own rule R3b from Otwell 2025."
tags: [decision]
status: draft
decided_on: 2026-09-30
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-09-30-01-live-runs-fallback-search-blast-blind-spot-wet-lab-classes.md
    title: "Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan"
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
---

# Decision

R3/R8 count within the 3'-most 16 nt (the region Lefever tested); R3b for mismatches beyond (alone up to 4 tolerated, 5 or more at risk; with one inside at least at risk); 3 inside with none in the last 5 likely failure; the 4-adjacent exception only without further mismatches.[^progress][^mismatch-classes]

# Who and why

User decision after the comparison with Otwell et al. 2025.

# What followed

Otwell comparison before: detectable 26, likely failure 52; after: detectable 35, likely failure 9 (all >= +3 Ct or undetected), at risk 88. A calibration, not a validation ([R3](../rules/r3-several-mismatches.md)).

[^progress]: Session 2026-09-30: Live runs; fallback search; BLAST blind spot; wet-lab classes; partner scan
[^mismatch-classes]: docs/MISMATCH_CLASSES.md
