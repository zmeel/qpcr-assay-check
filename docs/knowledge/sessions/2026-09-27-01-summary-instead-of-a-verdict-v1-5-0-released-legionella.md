---
type: Session
title: "Summary instead of a verdict; v1.5.0 released; Legionella draft"
description: "Session log of 2026-09-27."
tags: [session]
session_date: 2026-09-27
session_label: "2026-09-27"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-27: Summary instead of a verdict; v1.5.0 released; Legionella draft

- Overall verdict replaced by "Summary of this year's check" (user: "the tool is not a test that
  fails or passes"; advisor consulted first). User decisions: a review status (No flags /
  Review / Exceeds limit / Incomplete) in the report, workbook and results.json
  (`overall.review_status`; internal PASS/WARN/FAIL/INCOMPLETE codes kept so older records
  still compare); exit codes unchanged, documented as flag levels; first run = baseline; a
  changed assay or config = "not comparable" (neither holds up the status); QC labels within /
  outside preferred / outside limit, rules worded "preferred 18–30 nt; limit 15–40 nt"; grey
  "No flags"; a reviewer's decision box. SPEC.md amended. Code in `report/summary.py`.
- Two code reviews, all findings fixed with tests: `fragment_verdict` said PASS above a WARN and
  let years outside the window raise the status; summary rows could miss a section's status
  (fallback row per required section, `tests/test_summary.py`); target detection now
  Incomplete while not every listed genome is assessed (unless already below the FAIL limit).
- Live Neisseria run with the summary: rows and numbers correct (79.0% of 49,614 genomes
  2023–2026, below the 80% FAIL limit; oligo design (NG-R poly-A 7) and the N. meningitidis
  product on CP171264.1 exceed limits). The old text wrongly named the 95% review limit for a
  FAIL; now fixed.
- Legionella genus + L. pneumophila (next assay, user): draft
  `docs/examples/legionella_genus_pneumophila.yaml`, placeholder sequences, not runnable.
  Verified live at NCBI Taxonomy: target Legionellaceae 444 (NCBI files L. dumoffii 463 and
  L. gormanii 464 under Fluoribacter 461); exclusivity Coxiella burnetii (777), Rickettsiella
  (59195), Aquicella (254245). The tool has one target per file: a second file (pneumophila
  probe only, target 446) would check the pneumophila channel.
- Releases: PR #22 was merged at 639dd89 before the summary work, which went into PR #23;
  the version bump into PR #24. v1.5.0 tagged by the user on 3813754 (verified on the remote).
- One unexplained test run with 3 failures in tests/test_variants_exhaustive.py (after a
  `ruff format`); not reproduced in 10+ runs by me or the reviewer, CI green.
- Open: Legionella sequences, reporters, reference fragment, annealing temperature, source, and
  the second file; CP171264.1 record check (user); MGB zone display; per-assay "acknowledged"
  note for known design issues; simplification.

# Related

* [Legionella genus + L. pneumophila](../assays/legionella-genus-pneumophila.md)
* [A summary with review statuses instead of an overall verdict](../decisions/2026-09-27-summary-instead-of-verdict.md)
* [Check N. meningitidis record CP171264.1](../open/cp171264-record-check.md)
* [Legionella example still has placeholders](../open/legionella-example-sequences.md)
