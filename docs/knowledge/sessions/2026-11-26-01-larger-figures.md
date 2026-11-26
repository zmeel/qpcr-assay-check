---
type: Session
title: "Larger, clearer report figures; oligo design carried over"
description: "Session log of 2026-11-26."
tags: [session]
session_date: 2026-11-26
session_label: "2026-11-26"
generated: { by: claude-code/agent, at: 2026-11-26T10:00:00Z }
---

# 2026-11-26: larger, clearer report figures

- **The record checked.** The user's HSV-1 record of 2026-11-25 17:00Z, the first with the
  third-review figures (commit 0258356): 15 A4 pages, with a 2-page sign-off.
- **The user's verdict:** the year figure, the off-target map and the hairpin strip were too
  small; in the map the species names ran into each other; "before 2017" and "no usable date"
  belong at the top. "The goal is to give meaningful explanations, not fewer pages."
- **Built** ([decision](../decisions/2026-11-25-report-round3-built.md)):
  - the year figures full width, one under the other, the two non-year rows first and not pale;
  - a larger off-target map with numbered marks and a table under it;
  - a larger hairpin and dimer strip.
- **A flaw found in the map:** an organism stood at its fewest-mismatch site even when that site
  was minor. *T. pallidum* showed 2 mm and 2 clean 3′ nt (minor) instead of its warning sites
  (4 mm, 18 clean 3′ nt). Each organism now stands at its highest-level site first.
- **Checked:** the figures were redrawn from the numbers in that record. In print no table is
  wider than the page.
- **HSV-1 with the larger figures** (07:08Z, commit 2e55dba): 15 pages, with a 2-page
  sign-off. *T. pallidum* now sits at its warning site (4 mm, 18 clean 3′ nt).
- **Oligo design made optional** (user: "After the first run oligo design is known and therefore
  not to be repeated in each run"). Asked how a skipped oligo design should count, the user
  chose to carry the earlier result over
  ([decision](../decisions/2026-11-26-oligo-design-carried-over.md)).
  - **Built:** `--skip-oligo-design`, and the GUI option "Evaluate oligo design" (ticked by
    default), whose plan page names the source record.
  - **Matching:** `oligo_design_hash` covers the oligos, reference amplicons, reaction
    conditions and limits; `find_oligo_design` returns the newest matching record.
  - **Report:** Part A names the source record, and Part B shows a notice instead of the QC
    tables.
- **HSV-2 on the newest code** (11:04Z, commit 198650d): 12 pages, with a 2-page sign-off.
  Oligo design was carried over from the record of 2026-11-19; the status is Review (clinical
  list and background primer sites, no amplicon).
- **Year figures:** at the user's request they now stand side by side (600 px each), and the
  collection-year figure runs in time order: no usable date, then before the window, then the
  years. In print they stay stacked. The near-neighbour row without primer sites now has the
  same wording as the other rows.
- **HSV-2 again** (11:40Z, commit b19ffa2): 12 pages, with a 2-page sign-off, and Part A the
  same as at 11:04Z apart from the near-neighbour row's wording. The year figures stand side by
  side and in time order. The figure titles now use the heading font.
