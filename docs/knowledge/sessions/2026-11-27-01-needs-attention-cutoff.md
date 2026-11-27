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
