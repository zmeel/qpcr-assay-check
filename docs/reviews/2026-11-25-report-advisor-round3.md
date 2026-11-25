# Report review, third round: independent advisor, latest changes, simplifications and figures

Requested by the user on 2026-11-25 ("Have the advisor look at the latest changes in the report
and have the advisor look for more simplifications of the report. If data could be more
vizualized then text and tables that would be a hugh plus!") and carried out by a subagent of the
Claude Code session, read-only, on the user's HSV-1 record of 2026-11-25 13:33Z (not in the
repository), printed in Chromium. Its mock-ups stayed in the session's scratch folder.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon are
checked against the code first.

---

# Report review, third round: latest changes, simplifications, figures (2026-11-25)

**Reviewer:** independent advisor (molecular diagnostics, laboratory quality systems, report and data-visualisation design). Read-only: nothing in the repository was changed, nothing committed, no NCBI calls.

**Material:** the user's HSV-1 record `…20261125T133347Z-fb9bb449` (commit 5a38aac; 19 A4 pages, Part A = 2 pages), printed with Chromium (A4, 12 mm) and viewed page by page as images; commits since 2026-11-24, especially d31c2d5 (tier table column merge); `report.html.j2`, `html.py`, `summary.py`, `figures.py`, `charts.py`, `grouping.py`, `xlsx.py`, `specificity/findings.py`, `specificity/sites.py`. No results.json of this run was available, so d31c2d5 is reviewed from code and the old HTML, not re-rendered.

**[V]** = checked in the code or the printed record. **[J]** = my judgement. Page numbers are the 19-page print of the record.

Measured effect of what follows (simulation on the record's HTML, see §5): **19 → 17 pages with a CSS-only print fix, → 12 pages with the figures and cuts proposed here; Part A stays 2 pages.** [V]

---

## 1. The latest changes

### What works

- **Tier table (p. 9)** [V/J]: one row per tier with amplicons, sites, closest site, the gap and the status reads as a real summary; the numbered gap notes keep the long messages out of the cells. It replaced 11 sentences and is the best single table in Part B. [J]
- **Plain wording** [V]: "amplicon", "check for the opposite primer", gaps that say what stopped, at which setting and what is unknown ("Only the 2,000 strongest alignments checked for … (max_sites_per_query); weaker ones not assessed", p. 2). A reviewer can now act on a gap line without Part C. [J]
- **Short sign-off lines** (5a38aac) [V]: Part A ends on p. 2 with the decision box whole; about 10 % of p. 2 is still free.
- **Amplicon order** [V]: forward, probe, reverse everywhere I looked (site maps, totals, QC matrix, Needs attention, assay table).
- **Site maps opening Part B** (p. 5) [V]: the right place; they explain the Needs-attention rows (the forward −11/−8 columns are visible at once).
- **Condensed findings**: no repeated list in Part B [V].

### What is still unclear or inconsistent

1. **d31c2d5 makes one tier's sites appear with three different counts.** [V]
   - Part A row (p. 1, `summary._tier_rows`): "9607 critical and 820 warning primer sites", counting all primer sites, including those in amplicons.
   - Tier table after d31c2d5 (`html.tier_table`): only sites without an amplicon, e.g. 8,339 critical.
   - "Off-target sites per species" (p. 10): 10,427 sites, 9,607 / 820; for Background 1,538 sites, "151 / 1387", which includes 3 probe sites, against 1,384 in Part A and the tier table.
   - Part C "Sites found" (p. 15): 9,759 critical, 2,785 warning, 16,056 minor, which adds all tiers and the probe sites.
   - Number format differs too: "9607" in Part A, "8,339" in the table.
   - **Fix [J]:** use one basis on paper. Part A should use the tier table's words: "634 amplicons, 0 detected; 8,339 critical / n warning primer sites without amplicon". The species table should then count primer sites only, with probe sites in their own column. Use thousands separators everywhere.
2. **d31c2d5 mislabels the user's own latest record if it is re-rendered.** [V] `cell(fs, "primer_warning_no_product", "primer_warning")` falls back to the old `primer_warning`, which counts warning sites in amplicons as well. The new header "Primer sites without amplicon: critical / warning" then holds a warning count (820 for HSV-1) that includes sites inside amplicons. The 13:33Z record predates the split, so it is affected. **Fix:** for an old record, print the warning count with a note ("all warning sites; this record predates the split"), or a different header.
3. **"Closest primer site" sits beside a "without amplicon" column** but is chosen among all sites (`figures.closest_by_tier`). For near neighbours it is a site inside one of the 634 amplicons. [V] One word in the header fixes it: "Closest primer site (any)". [J]
4. **Part A status reasons** (`summary._tier_rows`):
   - **Background, Incomplete:** the reason shown is "critical primer sites, but no two facing each other (no amplicon)", which says nothing about what is incomplete. The incompleteness (hit list cut for FP_v8 and P) stands in the Scope column. [V] **Fix:** use the gap's short wording as the reason.
   - **Clinical organism list, Review:** no reason at all. `reason` stays empty when there is no amplicon and no critical site. [V] **Fix:** "577 warning primer sites without amplicon; closest: 4 mm, 18 clean 3′ (T. pallidum)".
5. **The Exceeds-limit lines never name the limit.** "HSV-1-gG1-FP: Tm of 72.5 °C is outside the limit (the worst of 8 variants, 68.0–72.5 °C)" (p. 2) gives the variant range but not the limit (54–70 °C, p. 13). [V] The status cell above (p. 1) repeats the same two Tm facts. **Fix [J]:** "FP Tm 72.5 °C (worst of 8 variants) > limit 70 °C". Drop the repeat from the status cell and keep only "outside the limit: FP Tm, RP Tm".
6. **The Tm figure marks the wrong value** (p. 1 and again p. 12). [V] `charts.tm_strip` draws the out-of-limit triangle at the midpoint of the variant range (`mid = (tm_min + tm_max) / 2`): 70.25 °C and 70.5 °C, on the 70 °C limit line. The worst variants that decide the status are at 72.5 °C and 73.0 °C. Only 54, 60 and 70 are labelled, and the preferred band (58–66 °C) carries no number. **Fix:**
   - draw the triangle at the worst value, `tm_max`, or `tm_min` when the low limit is the one crossed;
   - label 58 and 66;
   - add "limit" and "preferred" as text in the figure.
7. **The coverage at-a-glance (p. 1) mixes a filter with a time window.** [V] The bars read 618 listed → 618 assessed → 614 region found → 223 "judged, window". The 223 are not records lost along the way: they are the records released 2023–2026. The last label is also clipped at the cell edge ("judged, window" cut). **Fix [J]:** end the steps at "614 region found". Show the window as a separate, labelled bar: "223 released 2023–2026 (status window)".
8. **The target-detection result text is hard to parse.** [V] "100.0% including at risk, 0.0% likely failure (55.6% of 9 distinct site patterns, information)". **Fix [J]:** "96.0 % detectable, 4.0 % at risk, 0 likely failure; 223 records 2023–2026". The distinct-pattern figure belongs in Part B only.
9. **Raw tier keys survive in places** [V], against the plain-words decision:
   - "near_neighbours, 2 taxa" under each tier name in the tier table (template `{{ t.tier }}`);
   - the Scope sentence ("near_neighbours, background, exclusivity");
   - note 1 ("Tier 'background'");
   - the Searches and "What the searches could report" tables.
10. **Pagination wastes about 2.5 pages and orphans headings.** [V] Print CSS sets `table { break-inside: avoid }`, and `h4` has no `break-after: avoid`. Measured examples:
    - p. 3 half empty: the Coverage table is pushed to p. 4;
    - "Needs attention (8 combinations)" alone at the foot of p. 5, its table on p. 6;
    - "Detectable (6 combinations)" alone at the foot of p. 6;
    - "Off-target specificity" alone at the foot of p. 8;
    - p. 12 half empty;
    - p. 19 holds only Required statements.
11. **Needs attention (user decision, kept)** [V]: in print the Types column breaks mid-word ("alphaherpe / svirus 1 6", p. 2, because of `td { overflow-wrap: anywhere }`). **Fix [J]:** when every record is the target taxon, print the count only ("Human alphaherpesvirus 1: 6", or "target: 6"). This keeps the coloured layout untouched.

---

## 2. Simplifications, section by section

### Must stay in a filed quality record (and why) [J]

| Element | Why it stays |
|---|---|
| Run identity: run ID, code fingerprint, commit, inputs hash, date, NCBI database and RIDs | traceability of what was run on what |
| Required statements (short form on p. 1, full text in Part C) | CLAUDE.md requires them: in silico analysis does not replace experimental validation, and the laboratory verifies the software within its own quality system |
| Reviewer's decision box | the record's purpose |
| Status per check, with its reason and limit | the reviewer signs against these |
| Needs-attention rows | user decision |
| Evidence gaps with their full note | an auditor must see what is unknown |
| Limits applied and settings that differ from the defaults | the acceptance criteria, readable without software |
| Closest off-target alignments | the actual bases behind every off-target statement |
| Scope statements ("every NCBI Nucleotide record", "only the tiers searched") | stop the reader taking a sample, or a partial search, for the whole population |
| Limitations | they bound the claims |

### Part A (stays 2 pages; changes must be space-neutral)

- Fix items 1 and 4–8 above. These change content, not length. [J]
- **Legend line under the table** (3 lines): cut to 1 line once the off-target glyph is replaced (M1b). The glyph explanation is the longest part. [J]
- **"Findings that need a decision"**: keep (user design). Drop the duplicate reasons from the status cells instead (item 5). [J]

### Part B

| Section (page) | Proposal | Why it is safe | Effect |
|---|---|---|---|
| Coverage of the target (pp. 3–4): scope box plus a 10-row table, several rows "0" with long explanations | **M6** accounting figure, plus one line for the zero rows; the explanations (related-region rule, region not found, hidden by N) move to Part C Rules | every count is in the figure, the line, and sheets "Variant coverage" / "Copies and coverage" [V sheets exist] | about −0.9 page |
| Copies, coverage per oligo, escapes (p. 4): 9-line definition paragraph plus two tables | per-oligo bars in M6; one line: "24 escapes = the 8 Needs-attention combinations (24 records)" [V: 6+4+3+3+3+3+1+1 = 24]; the definitions are already in Part C "Mismatch classes" | sheet "Escapes" lists each one | included above |
| Whole fragment legend paragraph (p. 5, 8 lines) | 3 lines: the rest repeats the site-map caption and Part C | – | −0.1 |
| Detectable table (p. 7, 6 rows, about 0.9 page) | **M3** combination chart for all 14 combinations; Needs-attention table untouched | sheet "Fragment variants" has every combination with bases and changes [V]; ask the user first (see §4) | −0.5 |
| Inclusivity (pp. 7–8): chip line, Sampling box, two per-year tables, Rationale bullets, closing paragraph | **M4** two-panel year figure; drop Rationale and the closing paragraph, which repeat Part A, the tables and the Sampling box [V] | numbers in the figure labels and sheet "Inclusivity" (whole fragment, by release and by collection year) [V xlsx.py 503–515] | −0.9 |
| Off-target section header chips ("Incomplete off-target primer and probe sites · Review predicted off-target amplicons", p. 8) | drop: the tier table has a status column | – | small; it also removes the orphaned heading |
| Off-target sites per species (p. 10) and the Exclusivity table (p. 11, 14 rows plus the no-site line) | **M1** site-level map (one mark per organism) plus one line for probe sites and no-site organisms | sheets "Off-target sites", "Exclusivity", "Taxonomy breakdown" [V] | −0.8 |
| Closest off-target sites (p. 10) | **keep** (the bases); cut the Duplex Tm paragraph to one line | – | −0.05 |
| What the searches could report (p. 12, 9 identical rows: "2 mismatch(es), no gap", "from hits") | one sentence plus exceptions ("exclusivity RP: list reached its size limit") | sheet "Hits per query" [V] | −0.3 |
| Oligo QC: Tm strip (p. 12) | drop: it is the same figure as Part A | – | −0.15 |
| QC matrix (p. 13) | keep (categorical, compact, the audit table) | – | – |
| "Amplicon" table (p. 14) | drop: it repeats the "Site in reference amplicon" row and the amplicon block of the QC matrix [V] | – | −0.15 |
| Hairpins and dimers (p. 14, 15 rows each with a worst-case sequence) | **M5** Tm strip; keep the sequence and drawing for flagged structures only (round 2 proposed this, still not done [V]) | sheet "Structures" | −0.5 |

### Part C

| Section | Proposal | Effect |
|---|---|---|
| Queries with incomplete evidence (p. 15) | one line pointing to tier-table note 1, which already gives 2,201 / 5,008 relevant alignments and 2,000 assessed [V] | −0.2 |
| Limits applied (pp. 17–18, 40 one-value rows) | one row per group, settings run on as `key value · key value` (simulated); keep every value | −0.6 |
| "Settings from the assay file" YAML (p. 18) | drop: it repeats the "differ from the defaults" table [V]. `status_axis: release` is the default and needs no listing | −0.1 |
| Mismatch classes (p. 15, one 40-line paragraph) | later: a positional diagram of a primer and a probe (3′-terminal base, last 5 nt, MGB 3′-most 7 nt) with the rule IDs, built only from docs/MISMATCH_CLASSES.md and `variants` code. Keep the citations as text. No mock-up: I did not re-verify every rule boundary | about −0.3 [J] |
| Methods, Limitations, Required statements | keep | – |

---

## 3. Figures instead of text and tables

All mock-ups use the record's printed numbers (pp. 2–14), with the palette and textures of `charts.py`: detectable solid blue, at risk amber with a diagonal hatch, likely failure red with a cross-hatch, undetermined white with dots. They add zone textures: critical red with a cross-hatch, warning amber with a diagonal hatch. They are static inline SVG with `<title>` per mark, no JavaScript and no external resources. I checked each in colour and in greyscale (`mockups-grey.png`). Every number shown is also in a workbook sheet or a printed line.

### M1. Off-target site-level map (Part B). Highest value

- **Data:** `specificity.sites[]` (`tier`, `role`, `n_mismatch`, `n_gap`, `clean_3prime_nt`, `level`, `organism`/`taxid`), the closest primer site per organism. Use the key of `figures.closest_by_tier`, `(n_mismatch + n_gap, -clean_3prime_nt, id)`, grouped per species with `grouping.species_of`. `exclusivity.rows[]` adds the organisms without a site. Zones come from `cfg.specificity.primer_site` (critical: ≤3 mm, 0 gaps, ≥5 clean 3′; warning: ≤5 mm, ≤1 gap, ≥3 clean 3′). These are exactly the tests in `specificity/sites.classify` / `meets`. [V]
- **Form:** x = mismatches (0…6+), y = clean 3′ nt (0…24).
  - The critical and warning zones are shaded with texture.
  - One mark per organism, with the tier as shape: ◆ near neighbours, ■ background, ● clinical list. Hollow marks have gaps.
  - Sites with 2 or more gaps sit in a grey "≥2 gaps → minor" column, so a gapped site never appears inside a zone it does not qualify for.
  - Probe sites (no 3′ rule) are one text line.
- **Why it reads better:** it shows *why* each site has its level, and how far each organism is from the next level. HSV-2 sits in the corner (0 mm, 22 clean 3′) and the human background at 2 mm. Every clinical organism falls outside the critical zone: 4 mm or more, or a broken 3′ end (Molluscipoxvirus 3 mm, 1 clean 3′), or 2 or more gaps (P. ducreyi, Rhadinovirus). Two tables and the level rule text are needed today to see this. One mark per organism avoids the redundancy trap of site counts (round 1: "do not chart site counts per organism"). [J]
- **Replaces:** "Off-target sites per species" and the exclusivity table's "Best site" column (the exclusivity table becomes one line).
- **Greyscale:** the zones differ by texture (cross-hatch versus diagonal); marks are black or hollow; labels are text. [V rendered]
- **Page effect:** −0.8. Effort: medium (one `charts.site_level_map`, one `figures` builder, about 150 lines).

### M1b. Part A "at a glance" for the off-target rows

- **Data:** the same as the current glyph, `figures.closest_by_tier`.
- **Form:** a 120 × 34 px copy of M1's plane with one dot, plus "0 mm / 22 clean 3′" printed beside it.
- **Why:** in today's glyph a match is a light cell, so the worst case (a perfect off-target site) is the emptiest picture: near neighbours shows 22 light cells, the clinical list 4 black cells (p. 1). [V] The dot sits in the zone that decides the level.
- **Replaces:** the glyph and half of the legend line.
- **Space:** neutral. Effort: low once M1 exists.

### M3. Whole-fragment combinations (Part B)

- **Data:** `variant_summary.fragments[]` (`FragmentVariantRow`: `forward/probe/reverse.grade`, `.grade_rule`, `count`, `percent`), with `grouping.fragment_outcome` for the outcome.
- **Form:** one row per combination, grouped by outcome.
  - Three class tiles (F / P / R) carry class and rule ID: perfect outlined, tolerated solid, at risk hatched.
  - A linear bar of records with "n · %" printed.
- **Why:** the structure becomes visible at once.
  - 61 % carry one tolerated forward variant only, and 32 % that variant plus a tolerated probe variant.
  - Every at-risk combination involves an at-risk forward site, except one (at-risk probe, 4 records).

  The table needs 1.8 pages of reading to show this. A linear scale keeps 1-record combinations honest: tiny bars with their count printed. [J]
- **Replaces:** the Detectable table only. The Needs-attention table stays exactly as decided, and the decision's "site variants seen only in these combinations" line must be kept below the chart.
- **Greyscale:** tiles differ by outline, solid fill and hatch. [V rendered]
- **Page effect:** −0.5. Effort: medium. **Ask the user first:** the 2026-11-20 merged-variants decision put rule and changes into these rows.

### M4. Inclusivity per year, release and collection side by side (Part B)

- **Data:** `inclusivity.fragment_years[]` and `inclusivity.collection` (`years`, `earlier`, `undated`) through `figures.year_bars` / `charts.year_bars`. The builder already handles "before …" and "no date" rows when the status axis is collection [V figures.py]; it needs one call with the collection rows for the information panel.
- **Form:** two 100 % bar panels on the same scale.
  - Left: release year, with the window bracketed. Right: collection year, marked "information only".
  - Pale bars are years with fewer than 30 records.
  - "n · k at risk" is printed on each bar.
  - "No usable date" (296 records) and "before 2017" (117) are drawn as bars, as round 1 required.
- **Why:** it replaces two tables (20 rows) and three paragraphs. It also makes the key fact visible: 64 % of these records have no usable collection date. [V 296 of 465]
- **Replaces:** both per-year tables, the Rationale and the closing paragraph.
- **Greyscale:** dark, pale and hatched. [V rendered]
- **Page effect:** −0.9. Effort: low (reuse the existing chart).
- **Honesty:** every count is printed; percentages remain in sheet "Inclusivity". The window total (223, 214, 9) goes into the caption.

### M5. Hairpins and dimers (Part B)

- **Data:** `oligo_qc.structures[]` (`kind`, `label`, `found`, `tm_c`, `status`), and the thresholds in `cfg.thresholds.structures` (47 °C outside preferred, annealing 60 °C outside the limit, as printed on p. 14).
- **Form:** a dot strip per structure on a 0–65 °C axis, with the review and limit zones textured. A flagged structure is a triangle. "none" and "<0" sit in a gutter (not plotted as 0).
- **Why:** 14 of 15 rows say "within". The figure shows they are at least 23.5 °C below the review line (highest: RP self-dimer 23.5 °C), and that the one flag (RP hairpin 56.5 °C) is 3.5 °C under the annealing temperature.
- **Replaces:** the 15-row table, except the flagged structure's sequence and drawing.
- **Greyscale:** zones by texture; marks black. [V rendered]
- **Page effect:** −0.5. Effort: low to medium.

### M6. Coverage and copies accounting (Part B)

- **Data:** `variant_summary.coverage` (`listed_total`, `assessed_total`, `found`, `not_found`, `related_only`, `contig_break`, `masked`), plus the copies table (per oligo, the genomes with a detectable best copy) and the escapes count.
- **Form:** one 100 % bar for the listed records (found / not found / related only), then four aligned 100 % bars of the 614 with the region: forward, probe, reverse, whole fragment (detectable copy / none). The "none" segment is coloured by the escapes' class.
- **Why:** it replaces a 10-row key-value table and a 6-row table spread over two pages. It shows that the forward primer accounts for 20 of the 24 escapes. [V 594/614, 610/614, 614/614, 590/614]
- **Greyscale:** solid, hatch, dots, reverse-hatch. [V rendered]
- **Page effect:** −0.9 together with moving the definitions to Part C. Effort: medium.
- **Caution:** a record can lack a detectable copy for more than one oligo, so the per-oligo "none" segments need not add up to the escapes. The caption must say so.

### Lower priority

- **Part A per-oligo totals line** ("Forward: of 614 records 0 perfect, 594 tolerated, 20 at risk") as three thin 100 % bars in the same three lines. Same space; nice to have. [J]
- **QC matrix as bullet bars:** not recommended. The matrix is already compact, and the values and limits are the audit content. [J]

**Not recommended** (consistent with round 1): pies, gauges, risk scores, log scales, any chart that drops undetermined or undated records.

---

## 4. Ranked: what to build first

| # | Item | Impact | Effort | Pages after (cumulative, from 19) |
|---|---|---|---|---|
| 1 | **Print flow fix** (CSS only): let long tables break between rows, repeat `thead`, keep `h2`–`h4` with the next element, keep Part A's summary, review box and tier table whole | high: −2 pages, no orphaned headings | very low | **17** [V measured] |
| 2 | **Part A correctness**: items 1, 2, 4–8 (one count basis, reasons for Incomplete/Review rows, limit named in the findings, Tm triangle at the worst variant, coverage window label, plain inclusivity text) | high: this is what is signed | low | 17 |
| 3 | **Cuts without new figures**: searches-could-report → line; Amplicon table; duplicate Tm strip; Rationale and closing paragraph; off-target chips line; Part C duplicate queries table and YAML; compact Limits applied; raw tier keys → plain names | medium | low | ≈ 15.5 [J] |
| 4 | **M4** year panels (reuses `year_bars`) | high (visual, honest about undated records) | low | ≈ 14.5 |
| 5 | **M1 + M1b** off-target site-level map and Part A dot | high (explains levels; replaces 2 tables and the glyph) | medium | ≈ 13.5 |
| 6 | **M5** hairpins and dimers | medium | low–medium | ≈ 13 |
| 7 | **M6** coverage and copies accounting | medium | medium | ≈ 12.5 |
| 8 | **M3** combination chart instead of Detectable (ask the user: merged-variants decision) | medium | medium | **≈ 12** |
| 9 | Mismatch-class diagram in Part C (from docs/MISMATCH_CLASSES.md only) | low–medium | medium | ≈ 11.5 |

**Measured:** items 1, 3, 4, 5 (M1), 6, 7 and 8 applied together in the browser to the record's HTML (`simulate.js`): **12 A4 pages, Part A unchanged at 2.** [V] The order 2–8 is my estimate; only the end point and step 1 were measured.

**Tests to add with these** [J]:
- figure numbers equal table or sheet numbers;
- no orphaned heading (a heading's next element on the same page);
- the Part A page count stays 2;
- greyscale contrast between zone textures.

In silico analysis does not replace experimental validation, and the laboratory must verify the software within its own quality system. Nothing above changes that, and both Part A (short line) and Part C (full text) must keep saying it.

---

## 5. Files (scratch only)

All in `/tmp/claude-0/-home-user-qpcr-assay-check/11a8236c-4c6b-584c-a5b6-87a742a716a1/scratchpad/advisor3/`:

| File | Content |
|---|---|
| `mockups.html`, `mockups.png`, `mockups.pdf` | M1, M1b, M3, M4, M5, M6 with the HSV-1 numbers |
| `mockups-grey.html`, `mockups-grey.png` | the same, in greyscale |
| `m1-offtarget-site-levels.svg` | M1 as a standalone SVG |
| `gen/mock.py` | generator (Python, no dependencies) |
| `flow.css`, `flow-all.pdf`, `flow-montage.png` | print flow fix only: 17 pages |
| `simulate.js`, `sim-all.pdf`, `sim-montage.png` | all cuts and figures applied: 12 pages |
| `pagecss.js`, `shot2.js`, `shotfull.js` | render helpers |
