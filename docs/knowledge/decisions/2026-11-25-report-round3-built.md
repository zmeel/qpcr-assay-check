---
type: Decision
title: "Third report review built, except the combination chart (M3)"
description: "Print flow, sign-off corrections, cuts and four figures (year panels, off-target site-level map with a Part A dot, hairpin/dimer strip, coverage accounting) built from the advisor's third review; the whole-fragment combination chart (M3) is not, so the Detectable table keeps its rows."
tags: [decision, report]
status: draft
decided_on: 2026-11-25
generated: { by: claude-code/agent, at: 2026-11-25T19:00:00Z }
sources:
  - id: review
    resource: ../../reviews/2026-11-25-report-advisor-round3.md
    title: Advisor's third report review (2026-11-25)
  - id: merged
    resource: 2026-11-20-variants-per-oligo-merged.md
    title: "Variants per oligo merged into the whole-fragment table"
---

# Decision

Built from the advisor's third review:[^review]

1. **Print flow.** Long tables break between rows and repeat their header, and h2–h4 headings
   stay with what follows. The status table, the decision box and the off-target table stay
   whole.
2. **Sign-off corrections:**
   - The off-target rows count primer sites the way the off-target table does: without an
     amplicon, critical / warning, with thousands separators.
   - An Incomplete tier row names its gap. A tier row without an amplicon names its closest
     primer site.
   - The Exceeds-limit lines name the limit ("limit 54–70 °C"). The oligo-design row lists the
     checks only, without repeating their values.
   - The Tm figure marks the worst variant and names its bands ("preferred 58–66", "limit").
   - The coverage figure draws the status window as a separate, hatched bar, not as a step.
   - The Part A inclusivity text reads "96.0% detectable, 4.0% at risk, 0.0% likely failure".
   - Tier keys are written as names everywhere.
   - A record made before warning sites were split by amplicon says so under the off-target
     table.
3. **Cuts:**
   - "What the searches could report" is one sentence plus the rows that differ; the workbook's
     "Hits per query" sheet keeps every row.
   - The Tm figure prints in Part A only. The Amplicon table shows only for several reference
     amplicons.
   - The inclusivity Rationale shows only when the status is not No flags.
   - The off-target heading chips and the YAML copy of the assay settings are dropped.
   - The incomplete queries in Part C are one line.
   - Limits applied is one row per group.
4. **M4, year panels:** by release year and by collection year side by side, the status axis
   bracketed, records collected earlier or without a usable date as bars of their own. They
   replace the two per-year tables. Without charts the tables remain.
5. **M1, off-target site-level map:** each organism once per tier at its closest primer site
   (mismatches across, clean 3′ end up), on the critical and warning count limits.
   - **The fill is the site's own level.** The R1–R9 classes can set a site apart from its zone,
     so the zone alone would mislead (the review's own caution).
   - Probe sites are one line below the map.
   - It replaces the per-species table; without charts the table remains. The exclusivity table
     keeps its best-site column, because the organism list's resolution is audit content.
   - **M1b:** the Part A off-target rows show the closest site as a dot on the same zones. The
     old glyph showed a perfect match as the emptiest picture.
6. **M5, hairpin/dimer strip:** every structure against 47 °C and the annealing temperature, with
   "none" and "<0" in a gutter. Only flagged structures keep their row and drawing.
7. **M6, coverage accounting:** where every listed record went, and per oligo and for the whole
   fragment the genomes with a detectable copy. Coverage rows that are 0 are folded into one
   line; non-zero rows keep their explanations.

Not built:
- **M3** (the 14 combinations as a chart instead of the Detectable table), so the merged-variants
  decision stands.[^merged]
- The mismatch-class diagram (item 9), which was not part of the choice put to the user.

Measured:
- The sample full-run record: 13 to 11 pages, Part A 2 pages.
- The user's HSV-1 record of 13:33Z, with the new Part A rows and dots applied: Part A stays 2
  pages.
- The whole HSV-1 record needs a rerun to count.

# Changed after the first record (2026-11-26)

The user, on the HSV-1 record of 2026-11-25 17:00Z: the year figure, the off-target map and the
hairpin strip were too small; in the map the species names ran into each other; "before 2017"
and "no usable date" belong at the top. "The goal is to give meaningful explanations, not fewer
pages."

- **Year figures:** both are full width, one under the other. The two non-year rows come
  first and are not pale.
- **Off-target map:** a larger map, numbers beside the marks, and a table under it: number,
  organism, tier, closest primer site, mismatches, gaps, clean 3′ end, level.
- **Closest site per organism:** each organism now stands at its highest-level site. Before,
  the fewest mismatches decided, and *T. pallidum* showed a minor site although it has 577
  warning sites.
- **Hairpin and dimer strip:** larger.

# Who and why

User, 2026-11-25: "Have the advisor look at the latest changes in the report and have the
advisor look for more simplifications of the report. If data could be more vizualized then text
and tables that would be a hugh plus!" After the review: "Build everything except M3".

[^review]: Advisor's third report review (2026-11-25)
[^merged]: "Variants per oligo merged into the whole-fragment table"
