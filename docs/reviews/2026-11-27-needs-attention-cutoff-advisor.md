# Advice: a cut-off for the Needs-attention table (2026-11-27)

Requested by the user on 2026-11-27 on the influenza A record of 2026-11-26 15:21Z ("The Needs
attention (272 combinations) is very large and many of the combinations exisist of <0.1% of
total. Nobody is going to look in those. Consult with advisor what would be a good cut off value
for this table") and given by a subagent of the Claude Code session, read-only.

This file holds that advisor's report as delivered, unedited. It is an opinion, not a project
decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and in
the knowledge bundle's session pages.

---

# Needs attention: a listing cut-off. Advice of 2026-11-27

Advisor: molecular diagnostics, in silico qPCR assay evaluation, laboratory quality systems, report design.
I worked read-only and made no network calls. [V] means I checked it in the code or in the two records.
[J] means it is my judgement.

Material:
- Influenza A record: run 2026-11-26 15:21Z, commit b19ffa2, 25 A4 pages, Part A 4 pages.
- HSV-1 record: 15 pages, Part A 2 pages.
- Code: `report/grouping.py` (`fragment_view`, `_hidden`), `report/html.py`, `report.html.j2`,
  `config.py`, `pipeline.py` (`inputs_hash`), `specificity/variants.py` (`FragmentVariantRow`).

---

## 0. What the numbers show [V]

The influenza A record has 176,383 records with all three sites. At 0.1%, the listing bar would be 176 records.

| Outcome | Combinations | Records | Share | Listed today | Largest |
|---|---|---|---|---|---|
| likely failure | 23 | 42 | 0.024% | 5 (9, 6, 3, 2, 2) | 9 (0.005%) |
| at risk | 217 | 1,163 | 0.66% | 20 (154 … 9) | 154 (0.087%) |
| undetermined | 32 | 92 | 0.052% | 5 (28, 20, 6, 3, 3) | 28 (0.016%) |
| **total** | **272** | **1,297** | **0.74%** | **30 + 3 folded rows** | |

- **No influenza combination that fails to be detectable reaches 0.1%.** The largest is 154 records, which is 0.087%.
  A plain "≥ 0.1%" rule would therefore list nothing. The report prints 154, 147 and 98 records as "0.1%"
  only because the `pct` macro rounds any value ≥ 0.05 up to one decimal (`report.html.j2:167`).
  87 records (0.049%) is printed as "<0.1%".
- Today the rule picks 5 rows per outcome. It then fills the table up to 30 rows with the next most frequent
  combinations. In this record that adds 15 more at-risk rows of 9 to 49 records each.
  - Today's rows cover 912 of the 1,297 records that are not detectable (70%).
  - The tail is long: 197 at-risk combinations hold 333 records, and none has more than 9.
- In print, Needs attention runs from page 7 to page 15. That is about 8.5 of the 25 pages, about 3.5 rows per page.
- HSV-1 has 614 records and 8 combinations, all of them at risk: 6, 4, 3, 3, 3, 3, 1 and 1 records,
  or 0.98% to 0.16% each, 24 records (3.9%) in total. All 8 are listed.

## 1. Recommended rule

### 1.1 The rule

A combination that is not detectable gets its own row in Part B when it meets **any** of these:

1. **Top of its class.** It is one of the **3** most frequent combinations of its outcome.
   The outcomes are likely failure, at risk, undetermined and not classified.
   This applies always, whatever its share.
2. **Share bar.** It is **≥ 0.1%** of the records with all three sites (the table's own denominator)
   **and** it is seen in **≥ 2 records**.
3. **Lower bar for likely failure.** It is a likely failure at **≥ 0.01%** of those records, again in **≥ 2 records**.
4. **Status window** (once the data carry it, see §1.3). Either:
   - its share of the **status-window** records is ≥ 0.1%, with ≥ 2 records; or
   - it is a likely failure with ≥ 2 records inside the window.

**Hard cap: 20 rows.** When the cap applies, rows are filled in this order:
- first the guaranteed top-3 of each class, worst class first;
- then the rows that pass a bar: likely failure first, then by records.

A combination that passed a bar but did not fit under the cap is named as such in the folded row (§2).
The cap must never silently drop such a row.

### 1.2 Why [J]

- **A share, not a record count.**
  - Over large targets, record counts measure sequencing effort, not prevalence. One surveillance study can deposit
    hundreds of near-identical isolates. For example, "Influenza A virus 147", released 2025-02 to 2026-10,
    looks like one project.
  - What a laboratory decides on is the proportion of the target population the assay might miss. That is also the
    scale of the inclusivity limits: Review at 95%, Exceeds at 80%.
  - 0.1% is 1/50 of the 5% margin before Review. A single combination below it cannot move the status on its own.
    The class totals, which are never hidden, show what the tail adds up to.
  - It matches the user's own sense of "nobody looks below 0.1%".
- **A record count only as a floor (≥ 2).** One record does not establish a variant. It may be a sequencing or
  assembly error, or a mis-called base. The code already uses this floor for site variants:
  `_hidden(min_records=2)`, "can fail when seen twice or more".
  - The floor matters only for small targets. Below 1,000 records, a single record already passes 0.1%.
  - It does not apply to the top-3 rule, so a class made only of singletons is still shown.
- **Top 3 per class.** Without it, a large and diverse target would show no rows at all (influenza A today).
  - Every class that occurs gets a face in the report: its leading combinations, with the coloured site cells
    the user wants to keep.
  - It is also what Part A draws from.
- **Likely failure gets a lower bar (one tenth).** This class predicts a false negative. At risk predicts a Cq shift
  that most samples above the LoD still survive.
  - A predicted failure is worth seeing at a tenth of the prevalence.
  - The ≥ 2-record floor keeps one-off artefacts out.
  - In the influenza record the 0.01% bar (18 records) adds nothing beyond the top 3. In a 20,000-record target it
    lists every likely failure seen twice or more.
- **Undetermined and not classified are treated like at risk.**
  - Undetermined is mostly ambiguity codes in the record (K, R), so it is about sequence quality, not biology.
  - Not classified is a gap in the tool's grading. The top 3 keeps it visible.
  - Their totals already appear on the status line.
- **A hard cap of 20.**
  - After the Types fix (§5) a row takes about 1/6 to 1/4 of a page, so 20 rows is about 3–4 A4 pages.
  - The guaranteed rows use at most 4 × 3 = 12, so the cap only ever cuts rows that passed a bar.
  - The validator should enforce `max_rows ≥ 4 × top_per_outcome`.

### 1.3 The status window [V]/[J]

- [J] It should weigh in, as an "or" criterion. The status is judged on the window (influenza A: collection years
  2023–2026, 73,327 records). An emerging lineage can be rare over 40 years of records but not rare recently.
  - The likely-failure row PX851121.1 is an example: 9 records, a probe failure with ΔTm −22 °C,
    released 2026-01 to 2026-04. It is the most decision-relevant row in the influenza record.
    It is listed under any version of the rule, through the top-3.
- [V] The data do not support this criterion yet.
  - `FragmentVariantRow` has no per-year or in-window count. It has only first and last release dates,
    through `forward.first_seen` and `last_seen`.
  - The influenza status axis is the collection year, while the table's dates are release dates.
- [J] Do not approximate by "last release in the window". Many old lineages are still being released, so that test
  would list the wrong rows and mislabel them as recent.
  - Instead, add a per-combination `count_window`, counted on the status axis, when the next data change happens.
  - Until it exists, criterion 4 is simply off. The folded row must not claim anything about recency.
  - With the window counts in place, influenza A would gain an estimated 0–2 rows (estimate only).

## 2. What the report must say about what is not listed

### 2.1 The folded row, one per class [J]

It already exists. It should name the bar, the share and the largest combination left out. Proposed wording:

> **at risk**: 214 further combinations below the listing bar (each under 0.1% of the 176,383 records and not among
> the 3 most frequent): 764 records (0.43%); the largest 87 records (0.049%). Where they fail (the site that is at
> risk, a record can count twice): forward n, probe n, reverse n. Every combination: workbook sheet "Fragment
> variants", column "Listed in the report".

- **"The largest folded" is the most useful single number.** It tells the reviewer the ceiling of what was not shown.
- **"Where they fail" by oligo** is what a redesign or monitoring decision needs from a long tail.
  It is cheap to compute from the folded combinations.
- **Over-cap rows get their own sentence:** "N combinations at or above the bar are not listed because of the
  20-row cap (`report.needs_attention.max_rows`)".
- **Workbook.** "Fragment variants" gets a column "Listed in the report" with one of:
  `yes: top 3`, `yes: ≥ bar`, `no: below the bar`, `no: over the cap`.
  The reviewer can then reconcile the report against the workbook row by row.

### 2.2 "Site variants seen only in these combinations" for large targets: it must change

[V] Today `_hidden` names every variant that is not tolerated and is seen at least twice, plus the 5 most frequent
tolerated ones, with no limit.
- In the influenza record the at-risk line already names about 45 variants and fills a third of a page.
- With 9 rows listed instead of 30, even more variants are hidden, so the line would roughly double.

[J] Proposal:
- **Apply the same bar to the line.** Name a site variant when it is one of the 5 most frequent of that class, or
  ≥ 0.1% of its oligo's records. For likely failure, name it when seen in ≥ 2 records.
  Summarise the rest as a count: "38 further at-risk variants in 210 records, each ≤ 15 records".
  Keep "N … seen in 1 record each".
- **Leave tolerated variants out of the Needs-attention lines.** They are not why a combination fails. They belong on
  the detectable folded line.
  - Today the same tolerated variant appears on several lines, for example reverse −9 Y=T, −3 G-T (838 records)
    is named on both the likely-failure and the at-risk line.
  - Each hidden variant should be named once.
- This changes the selection that the 2026-11-20 decision "Variants per oligo merged into the whole-fragment table"
  carried over. The user has to confirm it, and that decision page needs a follow-up.
- Nothing is lost: every variant stays in the sheet "Oligo variants", and the per-oligo totals and site maps stay in
  the report.

### 2.3 Heading and method sentence [J]

- **Part A heading:** "Needs attention: 272 combinations, 1,297 records (0.74%); 9 listed in Part B, the first 3 here".
- **Part B, one sentence under the heading:** "Listed: the 3 most frequent combinations of each outcome, and any other
  in at least 2 records and at or above 0.1% of the records with all three sites (likely failure 0.01%); at most 20
  rows. The rest are counted per outcome below; every combination is in the workbook."
- **Shares must be printed so that they can be compared with the bar.** Today 154 records prints as "0.1%", which
  invites "why is a 0.1% row a row and an 87-record row not?".
  - Below 1%, print two significant digits ("0.087%", "0.049%"), and "<0.001%" for very small shares.
  - At least do this in the Records column and in the folded rows.

## 3. The rule applied to the two records

### Influenza A (176,383 records; bar 176 records, likely-failure bar 18, floor 2)

| Outcome | Listed | Folded |
|---|---|---|
| likely failure | 3: 9, 6, 3 records (PX851121.1, KU379630.1, HE584751.1) | 20 combinations, 24 records (0.014%), largest 2 |
| at risk | 3: 154 (0.087%), 147 (0.083%), 98 (0.056%) (GQ907295.2, PV149304.1, MK676846.1) | 214 combinations, 764 records (0.43%), largest 87 (0.049%) |
| undetermined | 3: 28, 20, 6 (KP413892.1, PV376197.1, KC893165.1) | 29 combinations, 38 records (0.022%), largest 3 |
| **total** | **9 rows** (today 30), 471 records | 263 combinations, 826 records |

- No row passes the 0.1% bar. All 9 rows come from the top-3 rule. The likely-failure bar adds none.
- The at-risk rows listed are exactly the three that the report prints as "0.1%".
- If the status-window criterion is added later, perhaps 0–2 more rows (estimate only).
- **Part B:** the Needs-attention table shrinks from about 8.5 pages to about 2.5–3 pages at today's row heights.
  The folded lines need the trimming in §2.2.
  - The record would go from 25 pages to about 19–20.
  - With the Types fix of §5 it would be about 17–18 (estimate only).
- **Part A:** the rule alone changes nothing. The "first 3" are likely failure 9, 6 and 3 both today and under the rule.
  The four pages come from the layout (§5), not from the number of rows.
  - Optional [J]: in Part A show the **largest combination of each class**, so here LF 9, at risk 154 and
    undetermined 28, instead of the first 3 in worst-first order.
  - Today the sign-off never shows the 154-record and 147-record at-risk lineages, which hold 12 times more records
    than all the likely failures listed. Showing one per class gives the reviewer the whole picture in three rows.

### HSV-1 (614 records; bar 0.6 records, so the floor of 2 decides)

| Outcome | Listed | Folded |
|---|---|---|
| at risk | 6: 6 (0.98%), 4 (0.65%), 3, 3, 3, 3 (0.49% each) | 2 combinations, 2 records (0.33%), largest 1 (HM585509.2, KF498959.1) |

- [J] This is the only place where the floor bites: two single records from 2011 and 2013.
  - If the user prefers HSV-1 unchanged, set `min_records: 1`. All 8 rows are then listed, because 1 record is 0.16%.
  - The cost is small either way.
- Part A is unchanged: rows 6, 4 and 3. The record stays at about 15 pages (estimate only).

## 4. Configuration and how to record it

### 4.1 Make it a setting [J]

A laboratory with a different risk appetite, or a smaller target set, must be able to change it. Suggested keys in
`default_config.yaml`, under the existing `report:` block:

```yaml
report:
  include_charts: true
  needs_attention:              # which non-detectable combinations get their own row (display only)
    min_percent: 0.1            # share of the records with all three sites (and of the status window, when known)
    likely_failure_min_percent: 0.01
    min_records: 2              # the share bars never list a combination seen in fewer records
    top_per_outcome: 3          # always listed per outcome (>= 1)
    max_rows: 20                # safety net; must be >= 4 x top_per_outcome
```

Validation:
- both percentages must be 0–100, with `likely_failure_min_percent` ≤ `min_percent`;
- `top_per_outcome` must be ≥ 1, so a class is never shown without a face;
- `max_rows` must be ≥ 4 × `top_per_outcome`.

The keys replace the constants `cap=30`, `per_outcome=5` and `top=10` in `fragment_view`. `top=10` belongs to the
detectable table. It can stay a constant or become `report.detectable_top`.

### 4.2 Record it in the report [V]/[J]

- [V] `inputs_hash` leaves out the whole `report` section (`pipeline.py:43–46`).
  - This is right: changing the cut-off changes what is printed, not any result. A record re-rendered with another
    cut-off is still "the same evaluation".
- [V] `differing_settings` also skips `report.*` (`html.py:395`). A laboratory's own cut-off would therefore show
  nowhere in Part C.
- [J] So add a group to `LIMITS_SHOWN`:
  "Report listing (display only; no status depends on it)", containing the five `report.needs_attention.*` keys.
  - It then always prints in **Part C, Limits applied**, whatever the value.
  - The bar is also written in words in the Part B method sentence and in each folded row (§2).
- Keep it in results.json `config` and in the workbook sheet "Configuration", as for every other setting.
- A Decision page belongs in docs/knowledge.
  - It records the cut-off as the user's choice. It also notes how it relates to the user's rule of 2026-09-25,
    "a problem in hundreds of genomes is never pushed out by single-genome failures".
  - The new rule still respects that rule: a row that passes a bar is never displaced by a smaller one, and the
    folded row names its largest member.
  - However, a 100-record combination in a 176,000-record target is now below the bar. The user should confirm this
    explicitly.

## 5. Other reasons why the influenza A Part A takes 4 pages [V]/[J]

1. **Page 1 is almost empty** [V].
   - Cause: `table.summary { break-inside: avoid; }` (`report.html.j2:122`). The "What was checked" table does not fit
     under the header, so the whole table moves to page 2 and about two thirds of page 1 stays blank.
   - The table is tall because:
     - the Scope and Result columns are narrow, so the Coverage row's Result wraps to 9 lines;
     - the Oligo-design Status cell lists all 8 "outside the preferred range" items. *Findings that need a decision*
       repeats that list word for word (Part A lines 21 and 91 of the text).
   - Suggestions [J]:
     - let the table break between rows (`tr { break-inside: avoid }` is already set);
     - shorten that cell to "8 outside the preferred range, listed under Findings";
     - give Scope and Result more width than "At a glance".
2. **The Types column wraps one character at a time** [V, rendered page 3].
   - Nucleotide organism names are strain names, for example "Influenza A virus (A/swine/Oklahoma/A01798209/2015(H1N1))".
   - With `hyphens: auto` in a narrow column, the second Part A row alone takes about half a page, and the third row
     spills onto page 4. It is the same in Part B, where it causes about 3.5 rows per page.
   - Suggestion [J]: for Nucleotide sources, group the names by species. Strip the parenthesised strain, or use the
     taxonomy `species_of` already used for off-target rows, and print "Influenza A virus 6 (6 strain names)".
     The full names are in the workbook.
   - This is probably the largest single gain, in Part A and in Part B.
3. **"0.0% likely failure"** [V].
   - The Part A inclusivity row says 0.0% for 18 records in the window. The cause is `summary.py:272`, which uses
     `:.1f`, whereas the table macro prints "<0.1%".
   - A reviewer may read 0.0% as "none". Print "<0.1% (18)" instead.
4. **Minor** [V]:
   - the per-oligo totals line has no thousands separators (176383), unlike the rest of the record (176,383);
   - Part A uses two denominators, the window (73,327) and all records (176,383). Name the denominator in the
     Needs-attention heading.

Estimate [J]:
- With fixes 1 and 2, Part A should fit on 2 pages, or 3 at worst: header, checks table, year figure, totals,
  3 Needs-attention rows, findings and the decision box.
- The cut-off alone does not shorten Part A.

---
In silico analysis does not replace experimental validation. The laboratory must verify the software within its
own quality system, and that includes the display settings above.
