---
type: Session
title: "Open review items 8, 6 and 9"
description: "Session log of 2026-10-03."
tags: [session]
session_date: 2026-10-03
session_label: "2026-10-03"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-03: Open review items 8, 6 and 9

- 8: report paragraph "What the search cannot find" (word size, E-value vs Primer-BLAST 30,000),
  with Ye et al. 2012 checked in the full text (PMC3412702): "will miss any targets that have 6 or
  fewer consecutive matches", "about 0.5%", "30,000 for the primer-only case". Wiki updated.
- 6: RNA note in the class paragraph when template_type is RNA (Christopherson 1997, abstract
  checked via PubMed E-utilities). Also fixed the stale probe sentence (still said MGB 1 mismatch
  undetermined).
- 9: bulge_alternative() in variants/exhaustive.py: the status window's detectable share under
  the other homopolymer setting, from GenomeCall.n_detectable_other_rule; rationale line,
  summary row, InclusivityResult.bulge_alternative / bulges_tolerated. Tests in
  test_multi_copy.py and test_report_condensed.py.
- Still open from the list: 5 (exact mismatched-duplex ΔTm), 7 (16-nt window), 10 (Table 1
  check, needs the Stadhouders PDF), 11 (R7), 12 (Süß 2009), 13 (enterovirus rerun), and the
  larger 1-4.
