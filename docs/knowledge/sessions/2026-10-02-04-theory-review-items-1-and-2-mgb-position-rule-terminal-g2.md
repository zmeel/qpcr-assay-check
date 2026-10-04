---
type: Session
title: "Theory-review items 1 and 2: MGB position rule, terminal G2"
description: "Session log of 2026-10-02."
tags: [session]
session_date: 2026-10-02
session_label: "2026-10-02"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-02: Theory-review items 1 and 2: MGB position rule, terminal G2

- User asked for full references; supplied Kutyavin 2000, Klungthong 2010, Kwok 1990, Huang 1992
  (Süß 2009 not obtainable). Read with pdftotext (poppler-utils installed in the session).
- Findings: Klungthong's probe is not MGB and no false negatives are reported (the review
  overstated it); Kwok shows terminal G3 amplifying like a match (the review's G3 claim does not
  hold); terminal G2 sources disagree (Stadhouders avoid 3.8-4.8 Ct, Kwok 1.0, Huang C-T 2e-2).
- User decisions: terminal G2 -> at_risk; one MGB mismatch in the 3'-most 7 nt -> likely_failure.
  Built in oligo/grade.py (R1 G2 exception with notes naming Kwok/Huang, G3 note; R9 MGB_REGION
  = 7 with Kutyavin pages). The fixture F_VARIANT (terminal T-T, now at risk) became -5 and -1
  (R3 likely failure) so the escape tests keep their meaning. Docs: MISMATCH_CLASSES R1/R9 with
  full references, wiki, USER_GUIDE, report and panel text, NG example comment, reviews README.
- Both change results: rerun NG (MGB probes) and enterovirus (MGB probe) to see the effect.

# Related

* [One mismatch under the MGB is a likely failure](../decisions/2026-10-02-mgb-region-likely-failure.md)
* [Terminal G2 mismatches at risk](../decisions/2026-10-02-terminal-g2-at-risk.md)
* [Rerun the enterovirus assay](../open/enterovirus-rerun.md)
