---
type: Decision
title: "A cut-off for the Needs-attention table"
description: "A combination that is not detectable gets a row of its own when it is one of the 3 most frequent of its outcome, or at or above 0.1% of the records (likely failure 0.01%) and in at least 2 records; at most 20 rows. The rest are counted per outcome; the workbook says for each combination whether and why it is listed. Display only."
tags: [decision, report]
status: draft
decided_on: 2026-11-27
generated: { by: claude-code/agent, at: 2026-11-27T14:00:00Z }
sources:
  - id: advice
    resource: ../../reviews/2026-11-27-needs-attention-cutoff-advisor.md
    title: "Advisor: a cut-off for the Needs-attention table (2026-11-27)"
  - id: merged
    resource: 2026-11-20-variants-per-oligo-merged.md
    title: "Variants per oligo merged into the whole-fragment table"
  - id: code
    resource: ../../../src/qpcr_assay_check/report/grouping.py
    title: "src/qpcr_assay_check/report/grouping.py (fragment_view)"
---

# Decision

The Needs-attention table of the whole fragment lists a combination that is not detectable
when:

- it is one of the **3 most frequent of its outcome** (likely failure, at risk, undetermined,
  not classified), whatever its share; or
- it is in **at least 2 records** and at or above **0.1%** of the records with all three
  sites; or
- it is a **likely failure** in at least 2 records and at or above **0.01%**.

At most **20 rows**: the top ones first, then likely failure, then by records. A combination at
or above the bar that does not fit is counted in its outcome's folded row ("N of them at or
above the bar but beyond the 20-row cap").

- **Folded rows**, one per outcome, give the combinations and records left out, the largest of
  them, where they fail per oligo (records whose site is not detectable), and the main types.
- **The site variants seen only in folded combinations** follow the same bar: per class the 5
  most frequent, and any at or above 0.1% of its oligo's records; the rest are summed per
  class. Tolerated variants are no longer named on the Needs-attention lines (they are not why
  a combination fails); the detectable row keeps them. This changes the selection of the
  [merged-variants decision](2026-11-20-variants-per-oligo-merged.md) of 2026-11-20 for
  the Needs-attention rows.[^merged]
- **The workbook**, sheet "Fragment variants", has a column "Listed in the report": yes or no,
  and why (one of the most frequent, at or above the bar, over the row cap, below the bar).
- **Settings**: `report.needs_attention` (`min_percent`, `likely_failure_min_percent`,
  `min_records`, `top_per_outcome`, `max_rows`), lab-wide like every `report.*` setting. It is
  shown in Part C, "Limits applied", as a display-only group. No status depends on it.
- **Shares below 1%** print with two significant digits (0.087%, not 0.1%), so a row and the
  bar are compared in the same terms.

Part A's layout changes in the same build:

- the status table may break between rows;
- a long oligo-design list (more than 3 checks) moves to the sign-off list, and the status cell
  only counts the checks;
- strain names are grouped under their organism ("Influenza A virus 6 (6 strain names)");
- the inclusivity shares print the count below 1% ("0.025% (18) likely failure", not "0.0%");
- the per-oligo totals use thousands separators.

After the influenza A rerun of 2026-11-27, whose decision box fell alone on page 3, the user
chose two further changes ("Yes build both"):

- Part A shows the first 2 Needs-attention rows instead of 3; Part B keeps all listed rows;
- the sign-off lines are shorter: an off-target amplicon finding is one line ("1 amplicon
  detected by the probe (141 bp on ON845595.1, Influenza B virus)"), and the oligo-design line
  names each check once with its oligos.

The other option offered, grouping the years outside the status window in Part A's year
figure, was not chosen.

# Who and why

The user, on the influenza A record of 2026-11-26: "The Needs attention (272 combinations) is
very large and many of the combinations exist of <0.1% of total. Nobody is going to look in
those. Consult with advisor what would be a good cut-off value for this table." The advisor
recommended this rule;[^advice] the user: "Yes build as recommended".

The rule keeps the 2026-09-25 principle (user): a problem in many genomes is never pushed out
by smaller ones. The top of each outcome always shows, and nothing at or above the bar is
dropped silently. The previous rule listed every combination up to 30 rows.

The cut-off values are the user's choice on the advisor's advice, not a published standard.
They decide only what is printed: every combination stays in the workbook and results.json,
and the status is computed from all records.

# Effect

By the advisor's count, influenza A drops from 30 listed rows to 9 and HSV-1 shows 6. To be
confirmed on the user's next influenza A run.[^code]

[^advice]: Advisor: a cut-off for the Needs-attention table (2026-11-27)
[^merged]: Variants per oligo merged into the whole-fragment table
[^code]: src/qpcr_assay_check/report/grouping.py (fragment_view)
