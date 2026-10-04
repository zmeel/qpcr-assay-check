---
type: Grading Rule
title: R8 - the primer pair
description: 3 mismatches in one primer with 2+ in the other, or 4 with 1+, is likely failure for the pair (Lefever 2013).
tags: [grading, primer, pair, R8]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: lefever
    resource: ../sources/lefever-2013.md
    title: Lefever et al. 2013
---

# Rule

Counted within the 3'-most 16 nt of each primer: 3 mismatches in one with 2 or more in the
other, or 4 with 1 or more, blocked amplification "almost completely": `likely_failure` for the
pair, whatever the single-site classes.[^lefever] Otherwise the pair's class is the worse of its
two primers. Pairs with 4 or more mismatches in total (2/2, 1/3, 1/4: medians about 15-16 dCq,
read from Lefever Fig. 6) may be understated by that; a flag for them is not shown yet
([open item](../open/r7-pair-flag.md)).

[^lefever]: Lefever et al. 2013
