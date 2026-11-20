# Review of the HTML report: independent advisor (molecular diagnostics, laboratory quality systems, data visualisation, report design)

Review requested by the user on 2026-11-20 ("The report is still too long and very text heavy.
Have the advisor look how to visualize the results more graphically.") and carried out by a
subagent of the Claude Code session, which read the project's documentation, code and tests
read-only and rendered the user's HSV-1 and HSV-2 reports of 2026-11-19 (not in the repository)
with Chromium. Its mock-up files lived in the session's scratch folder and are not in the
repository.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon are
checked against the code first.

---

# Report review: shorter, more visual, still a record (2026-11-20)

**Reviewer:** independent advisor (molecular diagnostics, laboratory quality systems, scientific data visualisation, report design). This review was read-only. Nothing in the repository was changed and no NCBI calls were made.

**Material read:**
- Docs: SPEC.md, USER_GUIDE.md and CLAUDE.md.
- Report code: `report/` (html.py, plots.py, summary.py, grouping.py, xlsx.py, `report.html.j2`).
- Models: `results.py`, `inclusivity/models.py`, `specificity/models.py`, `specificity/variants.py`.
- Knowledge bundle: the report sessions (2026-09-25, 2026-10-02-05, 2026-10-03-01, 2026-11-19), decisions 2026-09-27 and 2026-10-03, FEATURE_IDEAS "Report layout", and the 2026-11-17 review.
- Tests: `tests/test_report*.py`, `tests/test_run_full.py`.
- The user's two reports, rendered with Chromium 157 through Playwright:
  - HSV-2, Review: hsv-2-detection-gd-20261119T104519Z-7c154c85
  - HSV-1, Exceeds limit: hsv-1-…-20261119T114155Z-9992cf4b

Both reports were made at commit 4b5f4f0. Since then the template has changed in only two places (the exclusivity row note and the taxon-restriction text), so none of the conclusions below depend on that difference. [Verified: `git diff 4b5f4f0 HEAD`]

Every claim is marked **[V]** (verified in the code or in the rendered reports) or **[J]** (my judgement).

---

## 1. Diagnosis

### 1.1 Size of the record

| | HSV-2 (Review) | HSV-1 (Exceeds limit) |
|---|---|---|
| Page height at 1,440 px wide | 17,430 px | 20,577 px |
| A4 pages as printed (closed `<details>` not printed) | 24 | 31 |
| A4 pages with the closed sections printed | 38 | 53 |
| Words | 6,548 | 8,428 |
| Words in prose / in tables | ≈ 3,860 / 2,520 (60 / 40 %) | ≈ 5,120 / 3,130 (62 / 38 %) |
| Graphics | 1 SVG (the Tm chart), inside a closed section | the same |
| Prose that is identical to the other report except for its numbers | – | 20.7k of 36.8k characters (56 %) |

[V: measured with Playwright: `page.pdf` on A4 with 12 mm margins, word counts per section, and a line-by-line comparison of the two text dumps]

**Most of the prose is boilerplate.** More than half of the long paragraphs in the HSV-1 report appear word for word in the HSV-2 report. They are explanations of method, not findings. [V]

**There are no graphics in the printed record.** The single chart is inside "Show the oligo checks…". [V]

**Closed sections do not print.** The print stylesheet tries to show closed sections with `details:not([open]) > *:not(summary) { display: block; }`. That rule has no effect in current Chromium, because closed content sits in the element's internal content slot. As a result the printed PDF leaves out all of these [V]:
- the oligo QC tables;
- the Tm chart;
- "All findings behind this summary";
- "Hits and alignments per oligo";
- the effective configuration.

For HSV-1 this means the printed record does not contain the evidence for its one "Exceeds limit" row (primer Tm above 70 °C). Adding `@media print { details::details-content { content-visibility: visible; display: block; } }` fixed it in this Chromium: page counts went from 31 to 53 and from 24 to 38. [V] I have not tested Firefox or Safari. [J]

The rule is new in recent browser versions, so the safer design is to keep record content out of `<details>` altogether: screen readers then fold it, and print always shows it. [J]

### 1.2 Where the length comes from, by section

A4 pages at print width, closed sections not printed:

| Section | HSV-2 | HSV-1 | Main cause |
|---|---|---|---|
| Summary + decision box | 1.4 | 1.4 | fine |
| Assay as evaluated | 0.5 | 0.6 | fine |
| Specificity | 2.1 | **4.5** | The findings list. Each score-floor finding is one sentence of about 2,550 characters per tier, listing every degenerate variant. |
| Predicted off-target products | 0.1 | 0.4 | fine |
| Variant summary | 4.1 | **6.1** | 5 explanatory paragraphs (0.8–1.2k characters each), the whole-fragment table, per-oligo tables |
| Exclusivity | 1.3 | 1.4 | 23 organism rows; 10 of them in HSV-2 have 0 sites |
| Inclusivity | **4.9** | 4.7 | 3 per-oligo × per-year tables of 12 columns; "Mismatch classes" as one 3,855-character paragraph; "Distinct site patterns" written twice |
| Off-target sites per species | 0.6 | 1.1 | |
| Closest off-target sites | 1.5 | 1.3 | Three-line alignments. In HSV-1, 9 of the 10 rows are the same perfect HSV-2 primer match, differing only in N bases. |
| Oligo QC | 0.2 | 0.2 | (the contents do not print) |
| Methods / Limitations / Statements | 2.3 | 2.4 | Mostly reference material |

[V for the sizes and contents. "Mostly reference" is J.]

**The sections are interleaved.** In page order: Specificity → Products → Variant summary (inclusivity) → Exclusivity (specificity) → Inclusivity → Sites per species (specificity) → Closest sites (specificity). Specificity evidence is split across five sections with inclusivity in between. [V: template line order 192–576]

### 1.3 What a reviewer must read today to decide (HSV-1)

1. Page 1, the summary. It shows "Exceeds limit" above the line "2 of 6 checks flagged for review, 2 with evidence incomplete". That line counts an "Exceeds limit" row as "flagged for review", which is ambiguous. [V]
2. The Tm detail. On screen it is near the end (about page 22 of 31) inside a closed section; in print it is absent. [V]
3. Near neighbours "Incomplete": Specificity and Products, pages 3–8. [V]
4. Inclusivity at 4 % at risk: "Needs attention", 8 combinations, pages 8–10. [V]
5. Clinical list "Review": the findings list and the exclusivity table on page 12. [V]

That is five places spread over about 20 pages. [V]

The statements that in silico analysis does not replace experimental validation and that the lab must verify the software appear only at the very end. Page 1 has neither. (The validation sentence appears once, buried in the whole-fragment paragraph.) This repeats the 2026-11-17 review's point. [V]

### 1.4 What the reviewer needs first, and what is reference material

**Needed first** [J]:
- the status per check with its single decisive number;
- for each non-"No flags" row, the evidence in one figure or a few rows;
- the whole-fragment "Needs attention" rows (the user's own priority, 2026-10-02);
- the limits that were applied;
- the required statements;
- the decision box.

**Reference material: keep it in the record, but in an appendix, printed** [J]:
- Mismatch classes text
- Methods
- BLAST parameters
- RIDs
- Taxon-restriction counts
- Effective configuration
- Limitations
- Score-floor detail
- Hits and alignments per oligo

**Move to the workbook, with a one-line pointer** [J]:
- the 3 per-oligo × per-year tables (the whole-fragment table per year decides the status; per oligo they are diagnostics, as the report itself says);
- the full exclusivity rows with 0 sites;
- every closest-site variant beyond the first 5.

---

## 2. Visual proposals, ranked by value for the reviewer

**Palette** (checked with the dataviz validator, light mode):

| Class | Fill |
|---|---|
| detectable | #2F6FA8 (blue) |
| at risk | #E0A526 (amber) with a diagonal hatch |
| likely failure | #B8322F (red) with a cross-hatch |
| undetermined | white with grey dots and an outline |

- The three colours pass the CVD and normal-vision checks. Amber is 2.14:1 against white, so it always carries a text label. [V]
- In greyscale, blue (L* 45) and red (L* 42) look the same, so the textures are required, not decoration. [V: computed; mock-up checked in greyscale]
- I did not use green for "detectable", to stay consistent with the 2026-09-27 decision that "No flags" is neutral rather than "passed". [J]
- Order is always detectable → at risk → likely failure → undetermined, and every chart has a legend.

### P1. Page-1 status table with "at a glance" micro-graphics (highest value)

**What it shows.** The existing six-row summary, with shorter result text and a fifth column holding one small figure per row:

| Row | Figure |
|---|---|
| Oligo design | A Tm dot-and-range strip per oligo against the preferred band and the limit band, with the annealing line. An out-of-limit oligo gets a ▲ mark. |
| Target detection | One bar for the pooled status window (detectable / at risk / likely failure), with the configured limits as ticks ("95 % Review", "80 % Exceeds"). |
| Coverage | Aligned bars on one scale: listed → assessed → region found → in the status window. |
| Off-target rows | No figure. They point to P4 on the same page. |

**Data:**
- The rows: `summary_rows()` (`SummaryRow`).
- Tm: `oligo_qc.oligos[].tm_c_min`, `.tm_c_max`; `cfg.thresholds.primer.tm_c.pass_range` and `.fail_range`; `cfg.reaction.annealing_temp_C`.
- Window: `fragment_window(status_years(inc), cfg.inclusivity.verdict_window_years, status_last_year(inc))`, giving `detectable`, `at_risk`, `likely_failure`, `undetermined` and `possible_deletion`; limits from `cfg.inclusivity.warn_below_percent` and `.fail_below_percent`.
- Coverage: `variant_summary.coverage.listed_total`, `.assessed_total`, `.found`, `.not_found`, `.masked`, `.contig_break`, `.related_only`.

**Why this form.**
- Tm has no true zero, so the current bars, which start from an arbitrary axis floor, mean nothing as lengths. A dot with a range is honest. [J]
- One ratio against a limit is a meter. A donut or a gauge would only add decoration. [J]
- The coverage steps are bars on one baseline, not a funnel shape: funnel shapes distort widths. [J]

**Print and greyscale.** The ticks and labels are black, and the status chips keep their words. [V in the mock-up]

**Accessibility.** Every figure repeats a number given in the Result column. `role="img"` with an `aria-label`. Chips gain an icon (○ △ ▲ ◌) as well as the word. [J]

**Honesty.**
- The window bar uses the status's own base (undetermined genomes left out) and prints "0 undetermined", or the count, next to it.
- `possible_deletion` must be its own segment, because the status counts it as not detected.

### P2. Target detection per release year (stacked 100 % bars)

**What it shows.**
- One horizontal bar per year, split into detectable / at risk / likely failure / undetermined, plus "region missing where expected" when there are possible deletions.
- The count is printed at the right, with the non-detectable classes named ("107 · 7 at risk").
- The status window is marked with a bracket.
- Years below `min_genomes_per_year` (30) are drawn pale and labelled "few records". They are shown but not judged alone, which matches the current rule.

**Data:**
- `inclusivity.fragment_years[]`: `year`, `with_region`, `detectable`, `at_risk`, `likely_failure`, `undetermined`, `possible_deletion`, `population_size`.
- `cfg.inclusivity.min_genomes_per_year`.
- `inclusivity.status_axis`.
- The window from `fragment_window`.

**Why this form.** It is part-to-whole changing over time, which the stacked bar handles. Percent bars make small years look as solid as large ones, so the printed n and the pale treatment for small years are what keep the chart honest. [J]

**Do not:**
- draw a line of % per year: 1-record years produce artificial cliffs;
- hide undetermined genomes.

**Collection axis.** It can be a second small panel with the same scale. It must then show "collected before" and "no usable date" as bars: in HSV-2, 245 of 527 records have no usable date; in HSV-1, 296 of 465. Without those bars the panel would imply a dated time series that does not exist. [V for the numbers, J for the design]

The per-year table stays: either in Part B or as the figure's own table, as the "no figure-only values" rule requires.

### P3. Oligo-site maps: where the target genomes differ from each oligo

**What it shows.**
- One panel per oligo; one column per base, 5′→3′, with the oligo sequence printed underneath.
- The height of each column is the share of judged genomes with a mismatch at that base, split by the class of the whole site.
- The genome count is printed above every non-zero column.
- The primer 3′ end (last 5 nt) is bracketed.
- Gaps get a tick of their own below the axis.

**Why it matters, shown on HSV-1** (numbers from the report's own rows [V]):
- Today the forward primer reads "Perfect in 0 of 614 records (0.0 %)", which sounds alarming.
- The map shows instead that 613 genomes carry one tolerated mismatch at −21, at the 5′ end, and that the at-risk variants (12 at −11, 13 at −8) sit away from the 3′ end.
- The probe map shows 202 genomes with a mismatch at −11.

**Data.** `variant_summary.oligos[].rows[]`: `oligo_name`, `q_aln`, `s_aln`, `midline`, `count`, `grade`, `n_gap`, aggregated in Python per oligo name. These rows cover every genome, unlike the report's lumped rows.
- `inclusivity.oligos[].windows[].per_position_mismatches` also exists. It is never rendered (not in the report, not in the workbook) [V].
- It is not suitable for this map: it is per role, its length is the longest oligo, and several oligos of one role are pooled. [V: `exhaustive.py:1650–1659`]

**SPEC.** Pipeline step 7 and OUTPUT ask for a "per-position mismatch profile" and an "inclusivity with mismatch heatmap". Neither is in the report today. [V]

**Relation to the 2026-10-03 decision ("No graph of the variants for now").** That decision removed the variant landscape views (PCoA site-pattern maps, the whole-amplicon map) and the amplicon export script. This map is a different thing: the SPEC's own per-position profile, drawn from data already in results.json, with no clustering. I still recommend asking the user before building it, because "no graph of the variants" can be read broadly. [V for what was decided, J for the distinction]

**Caveats.**
- The colour is the class of the whole site, not the effect of that one base. The caption must say so.
- A base that matches through a degenerate code is not a mismatch.
- Use a linear 0–100 % scale with count labels. Do not use a log scale, which makes 2 genomes look substantial. [J]

### P4. Off-target search per tier: one compact table with a closest-site glyph

**What it shows.** One row per tier:
- searched completely, or why not (hit list full for which oligos; products cut at the cap);
- primer sites, critical / warning;
- products;
- products with probe signal (and "bounded" where it applies);
- the closest primer site as a glyph: one cell per oligo base, mismatch black, N grey, 3′ end underlined, with oligo, organism, mismatch count and clean 3′ nt in text;
- status.

**Data:**
- `spec_overview(...)`, or directly `specificity.counts[]` (`tier`, `query`, `truncated`);
- `specificity.score_floors[]` (`list_full`);
- `specificity.amplicons[]` (`tier`, `classification`);
- `specificity.sites[]` (`tier`, `level`, `role`, `q_aln`, `s_aln`, `n_mismatch`, `clean_3prime_nt`, `organism`);
- `specificity.partner_scan`.

**Why this form.** It stays a table, because the numbers are the content. The glyph gives the binding pattern at a glance, and the exact bases remain in "Closest off-target sites". [J]

**Do not:** draw a bar chart of site counts per organism. Site counts measure database redundancy, not risk: in HSV-2, 1,444 Listeria sites come from 722 records. [V for the numbers, J for the rule]

### P5. Score floor as a small matrix, not a gauge

Replace the three findings of about 2,550 characters each with a table: tier × oligo → "always reported up to N mismatches", plus "list full" and the source of the search space. Degenerate variants collapse to a min–max range.

**Data.** `specificity.score_floors[]`: `tier`, `query`, `length`, `min_score`, `max_mismatches_reported`, `list_full`, `space_source`, `per_search`.

**Why not a gauge.** A gauge suggests a good zone and a reading against a target. The floor is a detection limit of the search, and a gauge would make it look like a score of the assay. [J]

### P6. Exclusivity organism table, compressed

- One line for all organisms with 0 sites ("0 sites: 10 organisms", names listed).
- For the remaining rows, the closest-site glyph and mismatch count instead of internal IDs such as "minor S879" or "critical S3249", which mean nothing to a reviewer. [V that the IDs are printed]

**Data.** `exclusivity.rows[]`: `n_sites`, `best_site_level`, `best_site_id` → look up `specificity.sites`; plus `amplicon_predicted`.

### Not recommended

- Pies or donuts of taxonomy.
- Sunbursts.
- A "risk score" gauge.
- Per-oligo trend lines.
- A heatmap of year × position (too sparse; the per-year profile is a diagnostic for the workbook).
- Any chart that silently drops undetermined genomes, undated records, or "region not found".

[J]

---

## 3. Constraints and how the proposals meet them

| Constraint | How it is met |
|---|---|
| **Self-contained** | Inline SVG strings and inline CSS only. Pattern `<defs>` appear once with fixed IDs. **No JavaScript at all.** `test_report_with_charts_is_self_contained` already asserts `"<script" not in html` [V], and nothing here needs interaction: a `<title>` per mark gives hover text for free. [J] |
| **A4 printable** | `@page { size: A4; margin: 12 mm }`. The sign-off part is fixed at two pages and Part B starts with `break-before: page`. `break-inside: avoid` on figures. Fix the `<details>` print bug (§1.1). [J; the fix is V in Chromium] |
| **Deterministic** | Python f-strings with fixed precision, sorted input, no random IDs, no time stamps inside the SVG. Plotly was dropped for size (4.8 MB of 5.1 MB [V: session 2026-09-25]), and matplotlib's SVG output carries ids and metadata that are awkward to keep stable. [J] |
| **Required statements** | A one-line version under the title on page 1; the full text in the appendix and footer. |
| **Decision box** | Stays, on page 2, after "Findings that need a decision". |
| **No figure-only values** | Every chart sits beside or above a table, or names its workbook sheet, holding the same numbers. P1's numbers are in the Result column. |
| **No false certainty** | n printed on every bar; "few records" pale; undetermined drawn; possible deletions drawn; "≥ 500 (list cut at the cap)" rather than "500"; "bounded" where the probe search hit its cap; coverage steps show records that leave the denominator. |

---

## 4. Proposed page order and page 1

**Part A: sign-off (exactly 2 A4 pages)**

Page 1:
1. Title and record line (record ID, version, commit, short inputs hash).
2. One status sentence, for example "1 check exceeds a limit, 1 needs review, 2 have incomplete evidence". This replaces "2 of 6 checks flagged for review".
3. A one-line required-statements box.
4. "What was checked" with the P1 micro-graphics.
5. P2, target detection per year.
6. P4, the tier overview.

Page 2:
1. P3 site maps.
2. "Needs attention": the first 3–5 rows of the whole-fragment table (the user's priority).
3. "Findings that need a decision": only Exceeds limit, Review and Incomplete, each with its page. Info findings collapse to one count.
4. The reviewer's decision box.

**Part B: evidence, in the order of the summary rows**
- **B1 Target detection:** the whole-fragment table (in full); variants per oligo; the per-year table; the collection-year table; coverage.
- **B2 Off-target:** predicted products; closest sites, with N-only variants merged; sites per species; exclusivity (P6); searches with the P5 floor matrix.
- **B3 Oligo design:** flagged checks first, the Tm strip, structures, amplicon. This is the "only WARN/FAIL rows first" idea already in FEATURE_IDEAS.

**Part C: reference appendix (printed, compact type)**
- Mismatch classes (rules text)
- Methods and BLAST parameters
- RIDs
- Taxon-restriction check
- Limitations
- Full required statements
- Effective configuration and assay settings

**Wireframe of pages 1–2** (HSV-1 numbers; a working mock-up follows below):

```
┌─ page 1 ─────────────────────────────────────────────────────────────┐
│ HSV-1 detection (gG, Ryncarz 1999)        record … · v2.2.0 · 4b5f4f0│
│ [▲ Exceeds limit] 1 exceeds a limit, 1 review, 2 incomplete evidence │
│ ▌In silico analysis does not replace experimental validation; the    │
│ ▌lab verifies this software in its own quality system (full p. N)    │
│ WHAT WAS CHECKED                                                     │
│ Check        Scope        Result               Status   At a glance  │
│ Oligo design 3 oligos     both primers >70 °C  ▲Exceeds  ·──●▲ │50–80│
│ Target det.  223 genomes  96.0 % · 9 at risk   ○No flags ████████▒|| │
│ Coverage     618 listed   region in 614        ○No flags ▬▬▬▬ 618…223│
│ Near neighb. 2 taxa       ≥500 products, 0 sig ◌Incompl.            │
│ Clinical     23/23        577 warning sites    △Review              │
│ Background   1 taxon      152 critical, none … ◌Incompl.            │
│ TARGET DETECTION PER RELEASE YEAR   ■ det ▨ at risk ▩ fail ⁘ undet. │
│ 2017 ░░░░░░░░░░░░░░░░░░░░░░ 4 · few records                          │
│ 2018 ████████████████████▨ 107 · 4 at risk                           │
│ …                                                                    │
│[2023 ███████████████████▨▨ 107 · 7 at risk      ┐ status window     │
│[2026 ██████████████████████ 57                  ┘                    │
│ OFF-TARGET PER TIER  sites crit/warn · products · signal · glyph      │
│ Near neighbours  9,607/820  ≥500  0 (bounded) □□□□□□□□□□□□  ◌        │
├─ page 2 ─────────────────────────────────────────────────────────────┤
│ WHERE THE TARGET DIFFERS FROM THE OLIGOS (best copy, 614 genomes)    │
│ FP  613                12      13                                    │
│     █                   ▁       ▁                                    │
│     T C C T S G T T C C T M A C K G C [C T C C C] 3′                 │
│ P / RP  …                                                            │
│ NEEDS ATTENTION (8)  first 3 rows, all in B1                         │
│ FINDINGS THAT NEED A DECISION  ▲ Tm … p.9 · ◌ NN cap … p.5 · …       │
│ REVIEWER'S DECISION  ☐ No action ☐ Monitor ☐ Wet-lab ☐ Redesign      │
└──────────────────────────────────────────────────────────────────────┘
```

**Mock-up files** (static HTML with inline SVG; A4; prints as exactly 2 pages; checked in colour and greyscale; kept in the session's scratch folder, not in the repository):
- mockup-signoff.html, mockup-signoff.pdf
- mockup-page1.png, mockup-page2.png, mockup-page1-grey.png
- make_mockup.py (the generator, showing the proposed helper style)

The mock-up is layout only. Its numbers are copied from the HSV-1 report, and it is labelled "MOCK-UP" on each page. Its known simplifications:
- Two closest-site glyphs are drawn from the mismatch counts and clean 3′ lengths the report gives, not from full alignments. The clinical-list row has no glyph.
- Page 1's footnote is clipped at the page edge.

---

## 5. Prose to remove or shorten (quoted from the real reports)

1. **"Mismatch classes"**: one paragraph of 3,855 characters, the same in every report ("Each oligo site on the target gets a class (docs/MISMATCH_CLASSES.md): perfect; tolerated … Bru et al. 2008: up to 1000-fold …"). Move it verbatim to Part C as "Rules applied (rules version X)". In the evidence section keep one line: "Classes: perfect, tolerated, at risk, likely failure, undetermined; detectable = perfect or tolerated (rules, appendix C2)." [V for the text, J for the move]

2. **The primer-pair sentence appears twice** (Variant summary and Inclusivity): "R8: 3 + ≥2 or 4 + 1 mismatches across the two primers; as 3 in one primer are already a likely failure under R3, it rarely decides, and a pair with 2 + 2, which Lefever's Fig. 6 puts near 15 dCq, is flagged in the Rationale, its class unchanged". Keep it once, in the rules appendix. [V]

3. **"Distinct site patterns" is written twice**, at 443 and 483 characters (under the per-year table and in the Rationale). Keep it once, as one row in the per-year table ("distinct patterns: 9, of which 5 detectable"), with the caveat in the appendix. [V]

4. **Score-floor findings**: "Info Tier 'background': with the E-value cut-off 1000 this search reports only alignments scoring at least: HSV-1-gG1-FP_v1 (22 nt): score >= 13, sites with up to 2 mismatch(es) always reported (search space derived from the reported alignments); …", about 2,550 characters per tier. Replace with the P5 matrix. [V]

5. **Status legend under the summary**: "Status: No flags, no limit crossed; Review, a review (WARN) limit you configured was crossed; …". Replace it with the chip icons and one line: "Limits: Methods; missing evidence never counts as no flags." [V for the text, J for the change]

6. **Whole-fragment paragraphs**: "Only this table shows which site variants occur together on one template, …" and "The summary and the inclusivity status use this outcome, pooled over the last 3 complete release years …" are about 1,220 characters each. Cut them to two sentences in the figure or table caption: what a row is, and which rows decide the status. Move the rest to the appendix. [V]

7. **Exclusivity source notice**: "This run used the exclusivity_organisms list from this assay's own assay.yaml (organisms.source: assay, the default, prefers it over the global list whenever the assay defines one)". Shorten to "List: this assay's own (assay.yaml); not claimed complete." [V]

8. **Closest off-target sites** (HSV-1): of the 10 rows shown, 9 are the same perfect HSV-2 primer match, differing only in N positions. Merge variants that differ only by N, and show 5 rows plus a count. [V]

9. **Forward primer headline** (HSV-1): "Perfect in 0 of 614 records (0.0 %)." This is technically true but misleading. Write "No genome matches perfectly; 594 tolerated (one 5′-end mismatch at −21), 19 at risk", and let P3 show it. [V for the counts]

10. **The 3 per-oligo × per-year tables** (12 columns × 10 years each): move to the workbook. The report itself says they "explain the status but do not decide it". [V]

11. **Oligo QC figure inconsistency.** The same quantity is shown as three different numbers, and a dot-and-range strip makes the difference between them visible:
    - the summary says "Tm (68.0–72.5)";
    - the chart labels 70.3;
    - the check table says "Tm of 70.2 °C".

    Decide which statistic the check uses and state it. [V for the three numbers; the cause is not investigated]

---

## 6. Implementation notes

- **Module.** Extend `report/plots.py`, or add `report/charts.py`, with pure functions such as:

  ```python
  def year_bars(rows: list[YearRow], window: tuple[int, int], few_below: int) -> str: ...
  def window_meter(det: int, risk: int, fail: int, und: int, warn: float, fail_lim: float) -> str: ...
  def coverage_steps(steps: list[tuple[str, int]]) -> str: ...
  def tm_strip(oligos: list[TmRow], pref: tuple[float, float], lim: tuple[float, float], anneal: float) -> str: ...
  def site_map(name: str, seq: str, total: int, columns: dict[int, dict[str, int]]) -> str: ...
  def site_glyph(q_aln: str, s_aln: str, tail: int) -> str: ...
  ```

  The inputs are small dataclasses built from `RunResult` in a view layer, as `grouping.py` already does, so tests can feed plain numbers. Escape names with `html.escape`. Pass results to the template as `Markup`, the same way the Tm chart is passed now. The mock-up generator shows the style.

- **No new dependency.** Each chart is a few kB. [J]

- **CSS.**
  - Pattern `<defs>` once, near the top of `<body>`.
  - `@page` A4.
  - Part A followed by a page break.
  - The `<details>` print fix, or better, no `<details>` around record content.
  - Status and outcome colours as `:root` tokens next to the existing `--pass` and `--warn`.
  - No dark mode needed: this is a filed A4 record. [J]

- **Workbook.**
  - Add the per-oligo × per-year tables, which are currently report-only.
  - Add a sheet "Mismatch positions" with oligo, position (from the 3′ end), class and genomes, so that P3 has its table.
  - Make sure every chart's caption names its sheet.

- **Tests:**
  - Each helper produces well-formed XML (`xml.etree` parses it).
  - Segment widths add up to the plot width (±0.1).
  - A zero segment is omitted.
  - An undetermined count above 0 is drawn.
  - A "few records" flag appears below `min_genomes_per_year`.
  - n is printed on every bar.
  - **No figure-only values:** every number in a chart's `<title>`/`aria-label` also appears in the report's table text or the workbook rows.
  - Deterministic: render twice and get byte-identical output.
  - Golden snapshot of a small SVG.
  - The existing self-contained test (no `<script`, no remote `src`/`href`) keeps passing.
  - The required statements are present in the page-1 HTML.
  - Optional, and not a network test: a Playwright print test skipped when Chromium is missing. It asserts that Part A is 2 A4 pages and that the PDF text contains the required statements and the QC table, which guards the `<details>` regression found here.

- **Order of work** [J]:
  1. Fix the print bug (independent of everything else).
  2. Add the page-1 statement line.
  3. P1 + P2 + the page reorder.
  4. P5 and the prose cuts (§5).
  5. P4 and P6.
  6. P3, after the user confirms that the 2026-10-03 decision does not cover it.
