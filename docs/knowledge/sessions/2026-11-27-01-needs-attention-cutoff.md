---
type: Session
title: "A cut-off for the Needs-attention table"
description: "Session log of 2026-11-27."
tags: [session]
session_date: 2026-11-27
session_label: "2026-11-27"
generated: { by: claude-code/agent, at: 2026-11-27T10:00:00Z }
---

# 2026-11-27: a cut-off for the Needs-attention table

- **The record.** The user's influenza A rerun on the newest code (2026-11-26 15:21Z, commit
  b19ffa2): 25 A4 pages, with a 4-page sign-off. Needs attention: 272 combinations, 30 listed
  (the cap), most of them under 0.1%.
- **Advice.** The user asked for a cut-off; the advisor's report is kept verbatim
  ([advice](../../reviews/2026-11-27-needs-attention-cutoff-advisor.md)).
  - **Checked before reporting:**
    - the largest combination is 154 of 176,383 records (0.087%); the report's percentage
      macro prints it as "0.1%";
    - `report.*` settings are left out of "Settings that differ from the defaults".
  - **Recommended rule:** the top 3 per outcome; then any combination of at least 0.1% and
    at least 2 records; then likely failure from 0.01% and 2 records; a cap of 20.
  - **Row counts:** influenza A 9 rows, HSV-1 6 rows.
  - **Part A at 4 pages** comes from the layout: the status table is kept whole and moves to
    page 2, and the Types column breaks strain names.
  - Nothing built yet: the user decides.
- **Built** (user: "Yes build as recommended";
  [decision](../decisions/2026-11-27-needs-attention-cutoff.md)):
  - **Listing rule:** the top 3 per outcome; others from 0.1% and 2 records, likely failure
    from 0.01%; at most 20 rows. The folded row per outcome names the records left out, the
    largest of them, the rows over the cap, and where they fail per oligo.
  - **Site variants seen only in folded combinations:** the same bar. Tolerated variants are
    left off the Needs-attention lines.
  - **Workbook:** a column "Listed in the report" with the reason.
  - **Settings:** `report.needs_attention`, shown under Limits applied as display-only.
  - **Shares below 1%:** two significant digits.
  - **Part A:**
    - the status table breaks between rows;
    - more than 3 oligo-design checks are named on the sign-off list only;
    - strain names are grouped per organism;
    - "0.025% (18)" instead of "0.0%";
    - thousands separators.
  - **Checked:**
    - a SYNTHETIC flu-sized render (272 problem combinations): 6 rows listed, the rest in two
      folded rows, Part A on 2 A4 pages;
    - ruff, ruff format and `pytest -m "not live"` pass.
  - **Open:** the user's influenza A rerun on this code, to confirm the row count (advisor's
    estimate: 9) and the Part A length.
- **Influenza A rerun on this code** (2026-11-27 08:46Z, commit 28e93ed):
  - **Listed:** 9 of 272 combinations (the advisor's estimate), 1,297 records (0.74%).
  - **Statuses unchanged:** clinical list Exceeds limit (ON845595.1), background Review, near
    neighbours not searched, inclusivity No flags (99.5% of 73,362), coverage No flags.
  - **Length:** 16 A4 pages (25 before). The decision box alone went to page 3.
  - **Found in it:**
    - the variant table was 26 px wider than the page, so the browser printed everything 3.6%
      smaller;
    - "Influenza" broke as "Influen za" in the Types column;
    - strain names without a space before the bracket, or "Influenza A Virus", were not
      grouped.
  - **Fixed:** all three. Checked by putting the new stylesheet into the user's three latest
    reports: influenza A 15 pages at full size, HSV-1 15 and HSV-2 12 unchanged, no table
    wider than the page.
  - **Left to the user:** the decision box of influenza A is still on page 3. Getting it back
    on page 2 takes a content choice (shorter sign-off lines, fewer years in the Part A figure,
    or fewer rows), not layout.
- **The user chose two of them** ("Yes build both"):
  - **Built:** 2 Needs-attention rows in Part A; a one-line off-target amplicon finding on the
    sign-off; the oligo-design line names each check once with its oligos.
  - **Not chosen:** grouping the years in Part A's year figure.
  - **Checked:** a simulation on the user's influenza A HTML (new stylesheet, two rows, the new
    oligo-design line) gives 14 A4 pages at full size, with the decision box back on page 2.
    It still had the old, longer amplicon line, so the real record has a line to spare. To be
    confirmed on the next influenza A run.
- **Influenza A rerun** (2026-11-27 09:20Z, commit 103b95d): confirmed.
  - **Length:** 14 A4 pages at full size; sign-off on 2 pages, decision box included; no table
    wider than the page.
  - **Found in it:**
    - the outcome label broke letter by letter ("likel y fail ure");
    - "0.0051 %" split from its percent sign;
    - "24251 strain names" without a thousands separator.
  - **Fixed:** the labels in the variant tables print at the table's size and break only
    between words, shares stay whole, the cell padding is narrower, and the separator is added.
  - **Checked:** the new stylesheet in the user's influenza A, HSV-1 and HSV-2 reports gives
    14, 15 and 12 pages, the decision box on page 2, and no table wider than the page.
- **Part C.** The user: "There is a lot of text in the Methods, rules and limitations section
  which also seems to be squeezed in 1 kolom. Ask advisor how to shorten this text (table?) and
  use the whole width of the page". Advice kept verbatim
  ([advice](../../reviews/2026-11-27-part-c-advisor.md)).
  - **Proposal:** seven numbered blocks, mostly tables, with repeats removed; 2,533 to 2,188
    words, about the same paper (2.74 to 2.64 A4 pages).
  - **Corrections it flags:** nine points in the current text. Checked before reporting:
    - the "indeterminate" definition includes a single MGB mismatch, which R9 grades as
      likely failure;
    - R8 is "≥3 with ≥2, or ≥4 with ≥1" in the code;
    - the record says modified probes are "not modelled";
    - `tier_waivers` prints empty;
    - the variant search of long records uses its own BLAST settings (word size 11, expect 10,
      hit list at least 500).
  - Nothing built yet: the user decides.
- **Part C built** (user: "Yes build all"; [decision](../decisions/2026-11-27-part-c-rebuilt.md)):
  - **Built:** the seven numbered blocks and all nine text corrections.
  - **Not built:** the optional R2, R3 and R3b rows.
  - **Checked:**
    - the sample record: 2,445 to 2,403 words, still 11 A4 pages, no table wider than the page,
      the screen view at full width;
    - ruff, ruff format and `pytest -m "not live"` pass.
  - **Open:** the user's next run, to see Part C on a real record.
- **Influenza A rerun** (2026-11-27 10:28Z): the new Part C on a real record.
  - **The user:** text and tables were not page wide on screen ("All text fields/tables should
    be page wide").
  - **The caps removed:** paragraphs 46rem, the statement box 60rem, the decision box 52rem,
    the year panels 600px each.
  - **Also found:**
    - the count beside a year bar was cut off on the right; the figure now grows to fit its
      longest line;
    - the record's footer stood alone on a 15th A4 page; Part C is now set slightly tighter in
      print.
  - **Checked:** the new stylesheet in the user's influenza A, HSV-1 and HSV-2 reports gives 14,
    15 and 12 pages and no table wider than A4; on screen only the figures stay narrower than
    the page.
- **Influenza A rerun** (2026-11-27 10:50Z, commit 8f4ddb0): confirmed.
  - 14 A4 pages, no table wider than the page.
  - On screen every text and table is page wide; the year panels share the width.
  - The year counts are no longer cut off.
  - **One fix:** the counts in Part B's year texts got thousands separators.

