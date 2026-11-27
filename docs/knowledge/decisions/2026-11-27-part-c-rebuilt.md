---
type: Decision
title: "Part C rebuilt: numbered blocks, tables at full width, nine text corrections"
description: "Part C of the report is seven numbered blocks (C1-C7), mostly tables at the full page width with the remaining prose in short cards; each point stands once; and nine places in its text that were wrong, overstated or pointed nowhere are corrected. No rule, limit or number changed."
tags: [decision, report]
status: draft
decided_on: 2026-11-27
generated: { by: claude-code/agent, at: 2026-11-27T16:00:00Z }
sources:
  - id: advice
    resource: ../../reviews/2026-11-27-part-c-advisor.md
    title: "Advisor: Part C shortened and at full width (2026-11-27)"
  - id: classes
    resource: ../../MISMATCH_CLASSES.md
    title: "docs/MISMATCH_CLASSES.md"
  - id: template
    resource: ../../../src/qpcr_assay_check/report/templates/report.html.j2
    title: "Report template (Part C)"
---

# Decision

Part C ("Methods, rules and limitations") is rebuilt as seven numbered blocks:[^template]

- **C1 Terms and counting rules:** one table (predicted amplicon, check for the opposite primer,
  whole-fragment outcome, share beside a class, status window, percentages, distinct patterns).
  Part B points to it instead of repeating the status window.
- **C2 Mismatch classes:**
  - a classes table that says how each class is counted;
  - a rules table (Rule, Site, Class, Basis), so each reference sits next to its rule;
  - cards for "what a class is", RNA, quantification, ΔTm and "Tm ≤ annealing".
- **C3 What the search could and could not find:** one table. It merges the incomplete queries,
  "what the search cannot find" and the search limitations. A limitation text the record carries
  that this version does not know (an older version's) is printed as "Further limitation".
- **C4 Methods:**
  - software and thermodynamics in one row each;
  - BLAST split into "sent with each search" and "tool settings";
  - the taxon restriction check as a table with the RIDs;
  - a "Variant search" row when `variants.source: blast_partitioned`.
- **C5 Limits and settings:** the search group is dropped (it is in C4), and a "≠ default" tag
  ties a limit to the table of differing settings.
- **C6 Other limitations:** a table.
- **C7 Required statements:** unchanged.

On screen, Part C uses the full width (paragraphs were capped at 46rem). In print it is one
type style at the size of the other tables.

The text corrections, as the advisor listed them (5.1-5.9):[^advice]

1. "Indeterminate" includes a single MGB mismatch only outside the 3′-most 7 nt (under the MGB
   it is likely failure, R9).
2. The classes table says how a gap counts: not detectable, outcome at risk
   (`combination_outcome`); R6 and R9 are undetermined.
3. Three probe steps say they rest on expert judgement, as docs/MISMATCH_CLASSES.md says:
   - MGB with 2 or more mismatches;
   - unmodified probes with 1 mismatch outside the last 5 nt;
   - unmodified probes with 1 mismatch in the last 5 nt.

   The 3-mismatch ceiling already said so.[^classes]
4. "Near 15 dCq" says "read from the figure".
5. R8 reads "≥3 + ≥2, or ≥4 + ≥1", as `pair_fails` does.
6. "Modified probes … are not modelled" now says what is not modelled: the Tm, structure and
   dimer estimates. The oligo QC warns on a declared modification; the classes do grade MGB
   probes.
7. Cross-references that led nowhere are gone or point to a block:
   - "the Rationale";
   - "under 'search'";
   - "Mismatch classes under Inclusivity";
   - "the inputs hash above".
8. An empty setting prints "none" (`tier_waivers`).
9. The Methods name the variant search's own BLAST parameters (word size 11, expect 10, a hit
   list of at least 500; `variants/partitioned.py`).

# Who and why

The user, on the influenza A record of 2026-11-27 09:20Z: "There is a lot of text in the Methods,
rules and limitations section which also seems to be squeezed in 1 kolom. Ask advisor how to
shorten this text (table?) and use the whole width of the page". The advisor proposed the blocks
and the corrections; the user: "Yes build all".

Not built: the advisor's optional three extra rules-table rows for R2, R3 and R3b from
docs/MISMATCH_CLASSES.md.

# Effect

On the sample record (CDC N1, synthetic test data), Part C has 2,403 words instead of 2,445, and
the record stays at 11 A4 pages. The advisor estimated 14% fewer words for influenza A; the
corrections added words back. The gain is in reading: tables, every point once, the full width.

[^advice]: Advisor: Part C shortened and at full width (2026-11-27)
[^classes]: docs/MISMATCH_CLASSES.md
[^template]: Report template (Part C)
