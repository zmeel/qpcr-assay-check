---
type: Session
title: "Second code review of the unreleased changes"
description: "Session log of 2026-09-25 (later)."
tags: [session]
session_date: 2026-09-25
session_label: "2026-09-25 (later)"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-25 (later): Second code review of the unreleased changes

- The reviewer subagent reviewed `69b53ab..8e30922`: 11 findings, all verified against the code.
  Fixed with a regression test each: worst-case site KeyError (1), R6 hiding real mismatches (2),
  all-undetermined year at 0 % (3), panel undetermined vs escape (4), ungraded fragment rows shown
  as detectable and `blast_hits` target sites not graded (5), out-of-scope fetch failures and
  "no tier searched" (6), rows that can fail cut after 15 (7), non-existent template attribute
  (8), docs vs code in MISMATCH_CLASSES (9), panel refusing different reason text (11).
- Not changed (10): the inclusivity percentage ignores `homopolymer_bulges_detectable` (bulges
  count as not detectable there), while copy coverage and the fragment table honour it; older
  than this diff. R8 applies to genomes, not to the per-role percentage (by design). Both for the
  recap.
- Pushed (ca32c23..e342037). The user's next live run then crashed while writing report.html:
  `VariantRow` had no `grade_rule`, read by `fragment_outcome` for indeterminate sites (the
  tests used stand-in objects). Fixed, with a test on real rows (fails without the fix).
  Lesson: grouping tests should build real models, not SimpleNamespace stand-ins.
- 495 tests pass, ruff clean. Pushed (d6478c1).
- Live enterovirus run with d6478c1 (all 13,066 records now assessed; 11,687 with the region):
  report renders; 92.3% with a detectable copy, 609 escapes, 294 undetermined (297 probe sites,
  nearly all single MGB-probe mismatches; 1 reverse). Fragment table: 135 combinations need
  attention (30 listed, the tail is only undetermined rows), 96 detectable. Forward: F1 covers
  59.4%, F2 36.7%, none 488. report.html is 5.2 MB: to look at in the recap.
- Correction: the grouped tail of "Needs attention" also holds at-risk rows (by design beyond 30
  rows), not only undetermined ones as first reported to the user.
- User feedback: the whole-fragment table is what the program is for. Oligo columns too narrow,
  Types too wide: site lines now in the header's font size (aligned), header oligos no wrap,
  Types capped at 15rem. MGB probe with 2+ mismatches = likely_failure (user proposal; advisor
  agreed, position-free, expert judgement, unmodified probes unchanged).
- User: everything that makes the report more readable is on the table. Built: Part A of the
  fragment table picks rows by records (5 per outcome, then most frequent) so the 283-genome
  Poliovirus 2 at-risk row is listed; the tail is one row per outcome; oligo numbers after the
  header sequence keep the dots aligned; the Tm chart is inline SVG (Plotly dropped: 4.8 MB of
  the 5.1 MB report).
- User proposed dropping the per-oligo tables; advisor: shrink, don't drop (per-site frequency,
  history traceability, blast_hits coverage, full alignment for sign-off). Built points 1-4:
  fragment table first, compact "Variants per oligo" after it, % per non-perfect site in the
  fragment table, coverage line for blast_hits. Cross-links (point 5) left out for simplicity.
- Live run with 660e57f: report 335 kB, new layout works; per oligo still 30-52 rows (risky
  variants always listed, mostly single records). Built: single-record risky variants one row
  per class. Oligo QC (checks, hairpins/dimers, amplicon) folded just before Methods.
- Inclusivity gains a whole-fragment table per year (genome outcome of the three sites);
  the verdict still uses the per-oligo percentages (open question for the recap: base it on
  the genome outcome instead?).
- Specificity section (advisor): overview per tier on top, Searches one row per tier,
  probe sites INFO by default, RIDs cached, limitation on single-primer products. Not built
  (for the recap): rule c (INCOMPLETE -> INFO when the discriminating primers are complete,
  needs an extra lookup of reverse/probe sites on records with a priming forward site),
  year-over-year discrimination margin, single-primer products.
- README rewritten (advisor layout, ~220 lines) with the enterovirus "Needs attention" example
  (user asked for it); old reference text moved to docs/USER_GUIDE.md.
- Neisseria live run (54c144b): 68.9% detectable strict vs 85.7% with homopolymer bulges
  tolerated (reverse NG-R poly-A run); exclusivity FAIL: N. meningitidis CP171264.1 with a
  perfect 76 bp product (record to be checked by the user). History site list condensed.
  Advisor on bulges: no PCR study measured homopolymer bulges; proposes a graded class (1-nt
  bulge outside the last 3 nt = at_risk, larger = likely_failure) and an assembly-artefact
  breakdown; both built on the user's go-ahead (R5b; RunLengthBreakdown). Study (BioProject)
  breakdown not built: the store has no BioProject field.
- Neisseria run on d866fce: 224 kB report; run-length variants in 31,411 genomes, copies
  disagree in 83%, complete genomes carry them more often (77.8%) than contigs (60.8%): points
  to real copy variation (long-read homopolymer errors not excluded). Fixed after it: a gap no
  longer hides failing mismatches (probe variant with 7 mismatches + gap); repeatedly failing
  downloads no longer block completion.
- Advisor on MGB probe mismatch position: only Kutyavin 2000 (abstract) verifiable, strongest
  discrimination in the MGB (3') region; no data by position; keep "undetermined", optionally show
  the zone, and add a lab-evidence override in the assay file (built on the user's request: `evidence:`,
  rule LAB; zone display not built).

# Related

* [Gaps never hide mismatches; an unpaired end base is a mismatch](../decisions/2026-09-26-gaps-and-unpaired-ends.md)
* [Homopolymer bulges graded; laboratory evidence entries](../decisions/2026-09-26-homopolymer-bulges-graded.md)
