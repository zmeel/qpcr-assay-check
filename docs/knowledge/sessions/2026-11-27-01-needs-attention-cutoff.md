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
