# Code review for redundant code (2026-11-26)

Requested by the user on 2026-11-26 ("Have the code reviewer look for redundant code") and
carried out by a subagent of the Claude Code session, read-only, at commit bc5cff8.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon are
checked against the code first.

---

# qpcr-assay-check: review for redundant code

Reviewed on 2026-11-26 at HEAD `bc5cff8`. The review was read-only: no file in the repository changed, and `git status` is clean. The offline suite passed at baseline (`pytest -m "not live"`: 1332 passed).

Scope: `src/` (mainly `report/`, `results.py` and the models), `tests/`, `scripts/`, and `docs/knowledge/decisions/` for the decisions behind each fallback.

Legend:
- **[V]** verified with grep, AST scans or an actual run.
- **[J]** judgement.

Classes:
- **remove**: safe to remove.
- **merge**: duplicated logic.
- **keep**: deliberate fallback or compatibility.
- **unsure**: needs your decision.

Lines saved are rough estimates.

One structural fact underlies several items. **The HTML report and the workbook are only rendered right after a fresh evaluation** (`pipeline.write_outputs`, called from `cli.run` and the GUI). No command re-renders a stored `results.json`, and the GUI serves the `report.html` already on disk. [V] (`grep render_report|write_workbook` finds only `pipeline.py:520/534`). So every "record made before X" branch in the report is reachable only from tests, not in production.

---

## Ranked table (impact × safety)

| # | Item | Class | Lines | Risk | Tag |
|---|------|-------|------:|------|-----|
| 1 | Two workbook sheets are both called "Findings": the second is silently renamed "Findings1", so the report's pointer to sheet "Findings" goes to the wrong sheet | merge (drift, user-visible) | ~1–8 | low | V |
| 2 | Values passed to `render_report` that the template never uses: `groups`, `limits`, `floors`, `rows_shown`, `tolerated_shown`, `assay_settings_yaml`, `charts` (+ `import yaml`, the dead `charts` loop, the `svg.chart` CSS) | remove | ~30 | low | V |
| 3 | `oligo_view`/`OligoView`: only `.total` and `.n_perfect` are still read; the variant selection is duplicated in `_hidden` | remove/merge | ~40 | low | V |
| 4 | `panel.html.j2`: leftover template of the `panel` command removed in v2.0.0; nothing renders it | remove | 141 | low | V |
| 5 | Closest-site rule implemented about 7 times with different keys; the per-species table without charts and the map disagree, and `Finding.site` is stored but never read | merge | ~30 | medium | V/J |
| 6 | Part A year figure (`year_bars`) duplicates Part B's status panel (`year_panels`) and has drifted: no "date not read" bar | merge | ~20 | low | V |
| 7 | Dead chart code: `legend_strip`, `site_glyph` (only tests use it), the `compact` branch of `year_bars`, `_SITE_FILL["perfect"]` | remove | ~45 | low | V |
| 8 | Dead CSS rules (`.rec`, `svg.chart`, `details.qc`, `details.changes` + marker, `.s-evaluated-PASS`, `.s-none`); one rule repeated | remove | ~8 | low | V |
| 9 | Dead or duplicated template code: unreachable `else` in the Amplicon table, `cov`/`nuc`/`n_att` set twice, stale Part A caption, repeated sentences in the two specificity branches | remove/merge | ~15 | low | V |
| 10 | Values recomputed inside `render_report`: `summary_rows` ×2, `spec_overview` ×3, `floor_matrix` ×2, `limits_applied` ×2, `site_by_id` ×3 | merge | ~10 | low | V |
| 11 | Records-made-before branches (old finding list, `primer_warning`, `old_record`, sampled inclusivity, "fingerprint not recorded"): only tests reach them | unsure (decision says keep) | ~60 | medium | V |
| 12 | Model and results.json fields never set or never read (`SectionResult.available_from`, `n_no_date`, `per_position_mismatches`, `example_site_id`, `related_ignored`, `Finding.site`, `CheckResult.value_min/max`, `oligo_design_hash` is recomputed instead of read) | unsure/remove | ~20 | medium (schema) | V |
| 13 | Two different "Nucleotide records or assemblies" tests: a prefix match on the `sample_scheme` sentence (4×) vs `coverage.source == 'blast_partitioned'` | merge | ~6 | low | V |
| 14 | Tier names: `TIER_TITLE.get(t, t)` (5×) vs `tier_name(t)`; Part C prints a raw key in one branch | merge | ~5 | low | V |
| 15 | Label and rank mappings repeated: status labels, QC labels, role titles, chip icons, level and severity ranks | merge | ~25 | low | V |
| 16 | Status window and channel verdict computed in several places (`summary` vs `figures.window`, a Jinja copy of `fragment_window`; channels 3×) | merge | ~15 | low | V |
| 17 | Dead or test-only functions outside the report (`detectable_percent`, `is_mgb`, `load_outcome`, `category_of`, `STATES`, `_SITE_KINDS`, `env.tests["search"]`, plus test-only ones) | remove/unsure | ~60 | low | V |
| 18 | `OligoDesignSource.commit` is always empty (reads `tool["commit"]`; the key is `git_commit`), so its template branch never shows | bug through drift | 1 | low | V |
| 19 | Unused parameters (`xlsx._section_status(result)`, several in `variants/`) | remove | ~8 | low | V |
| K | Deliberate fallbacks to keep: tables shown when charts are off, the full structure table, the exclusivity rows, `merge_binding_variants` | keep | – | – | V |

Counts per class (items 1–19, a mixed item counted under its main class):
- **merge:** 9 (1, 5, 6, 10, 13, 14, 15, 16, 18)
- **remove:** 8 (2, 3, 4, 7, 8, 9, 17, 19)
- **unsure:** 2 (11, 12)
- **keep:** 1 group (K)

Rough total if everything except items 11 and 12 is done: about 450 lines, of which `panel.html.j2` is 141.

---

## Details

### 1. Two "Findings" sheets; the second is silently renamed "Findings1" [V] (merge, drift)

**Where:**
- `report/xlsx.py:278-284` writes `_sheet(wb, "Findings", ["Severity","Topic","Message"], spec.findings)` inside `if spec is not None`.
- `report/xlsx.py:563` writes `_sheet(wb, "Findings", ["Finding"], overall.rationale)`.

**Evidence:**
- openpyxl renames the second sheet. A full-run test record (`tests/test_run_full.py` run with `--basetemp` in the scratchpad) has the sheets `[... 'Hits per query', 'Findings', ..., 'Checks', 'Findings1']`. Its "Findings" sheet carries the header `Severity, Topic, Message`; "Findings1" carries `Finding`.
- `report.html.j2:247` says "all N as a list: workbook sheet "Findings"", where N is `len(overall.rationale)`. `:271` says "Every finding of the run ... is listed in workbook sheet "Findings"". `html.other_findings` (docstring, `html.py:499`) and decision `2026-11-25-findings-condensed` say the same.
- Whenever a run has a specificity section, that sheet holds only the specificity findings. The full list sits in "Findings1".
- The Summary sheet (`xlsx.py:124`) also repeats every `overall.rationale` line as "Rationale" rows: a third copy.

**Effect:**
- Pick one name. For example, "Specificity findings" for the first sheet, or merge both into one sheet with a Section column.
- This changes a workbook sheet name, not results.json.
- `tests/test_run_full.py:110` (`"Findings" in sheetnames`) and `tests/test_report.py:112` check the name and may need updating.
- Dropping the Summary sheet's Rationale rows is optional.

### 2. Values passed to `render_report` that the template never uses [V] (remove)

Every keyword of `template.render(...)` (`html.py:718-781`) was checked against `report.html.j2` with a word-boundary regex that skips attribute access. Each hit was then read by hand.

| Variable | html.py | Template use | Note |
|---|---|---|---|
| `groups` | 655-665 (loop, `oligo_groups`), 760 | none (`groups` at 553/592 is a macro parameter; 474 is prose) | The QC tables per oligo were replaced by `qc_matrix`. |
| `limits` | 735 | none | Only `limits_by_group` (736) is used, so `limits_applied` runs twice. |
| `floors` | 744 | none (`floors` at 695 is a CSS class) | `floor_matrix` runs a second time for `floor_sum`. |
| `rows_shown` | 751 | none | |
| `tolerated_shown` | 756 | none | |
| `assay_settings_yaml` | 771-775 | none | The YAML copy was dropped in round 3 (CHANGELOG "Cuts"); `import yaml` (`html.py:9`) exists only for this. |
| `charts` | 668 (always `[]`), 770 | `report.html.j2:720-725` loops over an empty list | The Tm chart prints in Part A only since round 3. The `svg.chart` CSS (`:92`) goes with it. |

**Effect:**
- No output changes: these values are never rendered.
- `_GROUPS` stays for `qc_matrix` (`_GROUPS[3:]`).
- No test refers to these names (grep finds none).
- Saves about 30 lines.

### 3. `oligo_view` / `OligoView` superseded [V] (remove or merge)

**Where:** `grouping.py:367-410` (`OligoView`, `oligo_view`), called at `html.py:706`.

**Evidence:**
- The template uses only `v.total` and `v.n_perfect` (`report.html.j2:234`).
- `OligoView.rows`, `lumped`, `lumped_records` and `singles` are computed and never read in `src`. The field scan gives `lumped` 0 reads and `lumped_records` 0 reads; `singles` and `rows` are read only in `tests/test_report_condensed.py:213-…`.
- Decision `2026-11-20-variants-per-oligo-merged` removed the table per oligo.
- The same selection rule (not tolerated and seen at least `min_records` times, a count per class for the rest, the top 5 tolerated) lives again in `grouping._hidden` (`:187-212`). That is the "old selection" the decision moved into the folded rows: two copies that can drift.

**Effect:**
- Replace the call with `o.total_measured` and `sum(r.count for r in o.rows if _perfect(r))`. `html.py:702-705` already loops over the rows.
- Delete `OligoView`/`oligo_view` and their test (`test_report_condensed.py` around :213). Keep `_perfect` and `_CLASS_ORDER`, which `_hidden` uses.
- No output change. Saves about 40 lines.

### 4. `report/templates/panel.html.j2` is a leftover [V] (remove)

**Evidence:**
- The template reads `p.panel_name` and `p.target_taxid`.
- No Python file, test or script refers to `panel.html` or `panel_name` (grep finds nothing).
- CHANGELOG [2.0.0] (`:684`, `:834`): "the `panel` command ... are gone".
- It is still installed and counted in the code fingerprint.

**Effect:**
- Delete the 141 lines.
- The code fingerprint changes, as any change does. Nothing else is affected.

### 5. "Closest site" picked by about 7 different rules [V]/[J] (merge)

| Where | Key | Filters | Used for |
|---|---|---|---|
| `report/grouping.py:115` `_closeness` | (mm+gap, −clean3′) | – | `group_sites` (species table when charts are off) and `TierOverview.closest` (old-record notice) |
| `report/figures.py:225` `closest_by_tier` | (mm+gap, −clean3′, id), written out twice at :236-240 | primers, warning/critical, no partial worst case | tier table, Part A glyph and the Part A reason |
| `report/figures.py:270` `_site_rank` | (level, mm+gap, −clean3′, id) | no partial worst case | off-target map and its table |
| `specificity/findings.py:84` `_closest` | (mm+gap, −clean3′, id) | partial sites included | `Finding.message` "closest: …" and `Finding.site` |
| `specificity/variants.py:256` `_closeness` | (measured, mm+gap, −clean3′, id) | – | grouping of the closest variants |
| `taxonomy/exclusivity.py:70` `_best` | (level, −(mm+gap)) | no clean3′ tie-break | exclusivity "best site" |
| `specificity/scan.py:159` | (level, mm+gap) | – | partner scan anchors |

**Drift that shows in the report:**
- **Two "closest site" tables pick differently.** The 2026-11-26 fix ("each organism's closest site is its highest-level one", CHANGELOG) went into `_site_rank` only.
  - With `report.include_charts: false`, the table "Off-target sites per species" (`report.html.j2:592-609`, from `group_sites`) still picks by mismatches alone. A warning site with fewer mismatches beats a critical one.
  - So the "closest site" of the same organism depends on whether charts are switched on.
- **The tier table and the map are not level-first in the same way.** The tier table's "Closest primer site" (`closest_by_tier`) does not rank by level, and its legend (`:525`) says so. The organism map does rank by level. For a tier whose best site is a warning site, the tier table and the map mark can name different sites. [J]: whether this is intended.
- **`Finding.site` is stored but not read** (see item 12). The decision `2026-11-25-findings-condensed` says "the table only reads the findings and never re-derives them". Since `c6fcb27` it re-derives with `closest_by_tier`, while the findings still store the `_closest` choice (partial sites included). results.json and the report can therefore name different "closest" sites.

**Suggestion:**
- Put one `closeness(s, *, by_level: bool)` key and one `can_prime(s)` filter in one module (e.g. `specificity/models.py`).
- Use them in `group_sites`, `closest_by_tier`, `_site_rank` and `findings._closest`.
- Then drop `Finding.site` or fill it with the same choice.

**Effect:** the per-species table without charts could change its "closest site" column. That is intended (it aligns it with the map). Risk: medium.

### 6. Year figure in Part A vs Part B: duplicated and drifted [V] (merge)

**Where:** `figures.py:86-111` (`year_bars`, Part A, `report.html.j2:228`) and `figures.py:117-157` (`year_panels`, Part B, `:443-451`).

**Evidence:**
- Both build the `YearRow`s the same way (in-window and few flags).
- `year_panels` puts "date not read", "no usable date" and "before <year>" first.
- `year_bars` puts only "no usable date" and "before <year>" first, and adds an `isinstance(extra, FragmentYear)` guard. The history (`git log -L`) shows that `not_read` was always in the panels only.
- On the collection axis with dates still to read, the Part A bar set and its totals differ from Part B's status panel.

**Suggestion:** one helper `_year_rows(inc, w, status_axis_only)` that both call.

**Related stale caption** (`report.html.j2:229`):
- The caption says "The numbers are in the per-year table of Part B".
- That table (`:452-485`) renders only when `year_panels` is `None`, which means charts are off. `figures.years` exists only when charts are on.
- So the caption always points to a table that is not in the report. Point it to the year panels and the "Inclusivity" sheet instead.

### 7. Dead chart code [V] (remove)

- `charts.legend_strip` (`charts.py:284-286`): 0 references in src, tests and scripts.
- `charts.site_glyph` (`charts.py:428-449`): used only by `tests/test_charts.py:39`. `site_dot` replaced it (round 3, M1b). Remove it together with that test line.
- `year_bars(compact=...)` (`charts.py:289-341`): no caller passes `compact`. `year_panels` uses `width=`/`title=`. The `compact` branches (row and left geometry, no legend, "few" vs "few records", the bracket variant, the "fig years panel" class) are dead: about 10 lines.
- `_SITE_FILL["perfect"]` (`charts.py:357`): never looked up. `_SITE_ORDER` has no "perfect", and `figures.mismatch_columns` maps perfect to tolerated (`:195`).

**Effect:** no output change. Saves about 45 lines; `tests/test_charts.py` needs one line changed.

### 8. Dead or repeated CSS in `report.html.j2` [V] (remove)

Each class in the style block was matched against the template body and against the Python that emits HTML (`html.py`, `charts.py`, `ncbi_links.py`); suspects were then grepped by hand.

| Rule | Line | Why dead |
|---|---|---|
| `.rec` (in the `h1, h2, … .rec` selector) | 24 | No `class="rec"` anywhere. |
| `svg.chart` | 92 | No SVG has class `chart` (charts emit `fig …`). |
| `details.qc > summary` | 93 | No `<details class="qc">`. The only `<details>` is `class="more"` (`:685`). |
| `details.changes …` (2 rules) | 94-95 | No `<details class="changes">`. Site changes are now a `span.site-changes`. |
| `.s-evaluated-PASS` | 51 | No chip gets `evaluated-PASS`. |
| `.s-none` | 55 | `chip(none)` would render `s-None` (capital N), so this never matches. [J] |
| `svg.fig.levels, svg.fig.structs, figure svg.fig.years { max-width:100%; height:auto }` | 43 | Repeats `svg.fig { … max-width:100%; height:auto }` at `:108`. |

The print comment at `:129-131` ("what still folds on screen (a variant's three-line alignment)") no longer describes anything: the only fold is the taxa list. A stray comment trails `:48`. Saves about 8 lines; no visual change.

### 9. Dead or duplicated template code [V] (remove or merge)

- **Unreachable `else`** (`:797-801`). The block opens with `{% if qc.amplicon and assay.reference_amplicons | length > 1 %}`, so the inner `{% else %}` row "Reference amplicon …" can never render. It is left over from "The Amplicon table shows only for several reference amplicons" (round 3).
- **`cov` set twice.** `{% set cov = r.variant_summary.coverage %}` (`:308`) repeats `:175`; the value is the same inside the `if`.
- **`nuc` set twice.** `{% set nuc = … %}` (`:420`) repeats `:176`.
- **`n_att` computed twice** (`:237`, `:397`), with the same expression.
- **Repeated in the two specificity branches** (tier table vs the old notice; see item 11):
  - "Discrimination rests on …" is written out twice (`:526` and `:537`). The copies already differ in where "assessed completely" goes.
  - The "Scope." paragraph is identical (`:529`, `:541`).
- **Repeated in the amplicon branches:**
  - The sentences about `n_primer_only` and the partner scan appear twice (`:568`, `:577`).
  - "No amplicon predicted in the taxa the assay must not detect" appears twice (`:571`, `:578`).
- **Chip icon map repeated.** The summary table writes out the icon map and the chip markup again (`:222`) instead of the `chip` macro (`:168`), because the row label differs ("Not assessed", "Waived", "Information only"). A `label=` argument on `chip` would merge them. The legend at `:227` lists the icons a third time.

**Effect:** no output change. Saves about 15 lines.

### 10. Values recomputed in `render_report` [V] (merge)

- `summary_rows(...)` runs at `:731` for `decisions` and again at `:778`.
- `spec_overview(...)` runs at `:716`, `:732` and `:779`.
- `floor_matrix(spec)` runs at `:744` and `:745`.
- `limits_applied(result.config)` runs at `:735` and `:736`.
- `{s.id: s for s in spec.sites}` is built at `:680`, `:743` and `:767`.

All of these are pure functions (no I/O; `figures.closest_by_tier` is deterministic). Compute each once. Saves about 10 lines; no output change.

### 11. Branches for records made before a field existed [V] for reachability (unsure)

**Branches:**
- `html.tier_table` returns empty rows (`:440-444`), and the template falls back to the old notice and findings list (`report.html.j2:532-549`).
- `summary._tier_rows` `old_record` (`:134-149`), together with `crit`/`warn`/`primer`, which only that branch uses.
- The `primer_warning` kind (`html.py:478-479`, `:492`; `report.html.j2:527`). `grep` finds no producer in `src`.
- `code_line` "code fingerprint not recorded (record made before it was added)" (`:172`).
- Sampled inclusivity:
  - `summary._inclusivity_row` (`:254-265`): "Target detection (sampled)", "per oligo and year".
  - `pipeline._inclusivity_title` (`:102-107`).
  - The template's 'sampled' wording (`:421`).

  `InclusivityResult` is only ever built with `exhaustive=True` (`variants/exhaustive.py:1731-1733`, the only constructor).

**Evidence:** the report is rendered only from a result the current code has just produced (see the intro). The current code always sets `kind`, `short` and `tier`, never emits `primer_warning`, always records the fingerprint, and never builds sampled inclusivity. Only tests reach these branches: `test_report_findings_table.py:105-111` (fields stripped), `test_report_sign_off.py:38` and fixtures.

**Decision context:**
- `2026-11-25-findings-condensed` says "Records made before this change keep the old list".
- The round-3 decision says "A record made before warning sites were split by amplicon says so".

Both assume old records get re-rendered, and nothing re-renders them.

**Your call:**
- (a) add a re-render command, which makes these branches useful; or
- (b) remove them (about 60 lines in `src`, plus about 3 tests).

Until then: keep.

### 12. Model and results.json fields that are never set or never read [V] (unsure/remove; results.json schema)

Found with an AST scan of model fields (`scratchpad/codereview/tools/fields.py`), then grepped by hand. Pydantic result models do not forbid extra keys (only config and assay models use `extra="forbid"`), so removing a field does not break loading old records. The key disappears from new records.

| Field | Set at | Read at | Suggest |
|---|---|---|---|
| `SectionResult.available_from` (`results.py:120`) | never | never | remove (always `null` in a real record) |
| `InclusivityOligoResult.n_no_date` (`inclusivity/models.py:48`) | never | never | remove (sampled-era field) |
| `WindowStats.per_position_mismatches` (`:36`) | `aggregate.py:69` | never (the site maps use the variant rows) | remove, or keep as data [J] |
| `VariantRow.example_site_id` (`specificity/variants.py:62`) | `:220` | never | keep as a provenance link, or remove [J] |
| `ExhaustiveCoverage.related_ignored` (`variants/models.py:326`) | `exhaustive.py:2176` | never in src | unsure |
| `Finding.site` (`specificity/models.py:123`) | `findings.py:257` | never (the tier table uses `closest_by_tier`) | remove, or fill with the displayed choice (item 5) |
| `CheckResult.value_min/value_max` (`results.py:29-30`) | `oligo/qc.py:79-80` | never in src | keep (results.json data for external use) [J] |
| `RunResult.oligo_design_hash` (`results.py:162`) | `pipeline.py:505` | never: `find_oligo_design` recomputes `oligo_design_hash(old.assay, old.config)` (`:92`), deliberately, so records that predate it can still match | keep (documented in CHANGELOG), but it is write-only |
| `search/assess.py` saturation and restriction extras (`min_relevant_identity`, `requested_taxids`, `fraction_in_requested`; `top_organisms` is read only by `scripts/smoke_test.py`) | `:55`, `:100-106` | never in src | keep; low value |

### 13. Two tests for "Nucleotide records vs assemblies" [V] (merge)

- **One test matches a human-readable sentence:** `sample_scheme.startswith("Every NCBI Nucleotide record")`, at `report.html.j2:176` and `:420`, `summary.py:266` and `pipeline.py:104`.
- **The other is structural:** `coverage.source == 'blast_partitioned'`, about 20 times in the template, plus `summary.py:357` and `figures.py:376`.

If the sentence's wording changes, `nuc` flips silently while the coverage wording does not. Suggestion: an `InclusivityResult` (or coverage) property, or derive the `nuc` checks from `coverage.source`. No output change.

### 14. Two tier-name mappings [V] (merge)

- `grouping.tier_name(t)` maps with a capitalised fallback ("target" → "Target").
- `TIER_TITLE.get(t, t)` keeps the raw key: `summary.py:215, 222`; `html.py:557`; `grouping.py:443` (`gap_text`) and `:511`.
- `report.html.j2:850` prints a raw `{{ t.tier }}` in the exact-ID branch of the taxon restriction check, while the lineage branch on the same line uses `tier_name`. Search rows include the `target` tier, so Part C can read "target: …" next to "Background: …".

Use `tier_name` everywhere. This changes the wording only for keys missing from `TIER_TITLE`.

### 15. Repeated label and rank mappings [V] (merge, low)

- **Status labels:**
  - `verdict.STATUS_LABEL` (source of truth).
  - The `chip` macro's dict (`report.html.j2:168`).
  - `gui/runs.py:38` `REVIEW_EXIT_CODES` (derivable from `EXIT_CODES` and `STATUS_LABEL`).
  - The fill keys in `xlsx._FILL` (`:27-32`).
- **QC labels:** `gui/assay_routes.py:35` `QC_LABEL` and the `qc_chip` macro (`report.html.j2:169`) hold the same dict.
- **Role titles** ("Forward primer"/"Reverse primer"/"Probe"):
  - `html.py:526` (`decision_lines`), `:656` (dead `groups`, item 2), `:279` (short form) and `:253`.
  - `report.html.j2:276`.
- **Level rank** `{"critical": 0, "warning": 1, "minor": 2}`:
  - `specificity/variants.py:39`, `specificity/scan.py:32`, `report/figures.py:267`.
  - Inverted in `taxonomy/exclusivity.py:23`.
  - As a tuple index in `charts.py:556`.
- **Severity rank** `{"FAIL": 0, "INCOMPLETE": 1, "WARN": 2, "INFO": 3}`: identical in `html.py:421` (`_SEV_RANK`) and `specificity/assess.py:664` (`_RANK`).
- **Two functions named `_worst`:** `summary._worst` takes `Verdict`s and `html._worst` takes severity strings, so the same name has two meanings.

### 16. Status window and channel verdict computed in several places [V] (merge)

- **`summary.py:253` and `figures.window()` (`:49-56`):** both call `fragment_window(status_years(inc), window_years, status_last_year(inc))`. Call `figures.window`.
- **Jinja copy of `fragment_window`:** the per-year table shown when charts are off recomputes the window and the pooled sums (`report.html.j2:459-468`, `:478-479`, `frag_cells`). It currently matches `fragment_window` on both axes, so this is a drift risk only. Pass the `FragmentWindow` in instead. The table itself is a deliberate fallback; keep it.
- **Channel verdict computed three times:** `summary._channel_rows`, `html._channel_table` and the xlsx "Channels" sheet. The xlsx copy builds `rules` from `result.config` through `SimpleNamespace` (`xlsx.py:478`); the HTML copies use `cfg`. They are equal today because `cfg` is what the record stores.
- **Percent formatting differs:**
  - The template's `pct` macro writes "<0.1%" for small values.
  - `summary.py:271-272` writes `f"{x:.1f}%"`, so Part A can print "0.0% likely failure" where Part B prints "<0.1%".

  [J] Unify through one helper.

### 17. Dead or test-only functions outside the report [V] (remove/unsure)

AST scan of top-level definitions (`scratchpad/codereview/tools/defs.py`). Decorator-registered CLI commands and pydantic validators were excluded as false positives.

**Never used:**
- `report/html.py:422` `_SITE_KINDS`.
- `report/html.py:637` `env.tests["search"]` (no `is search` in any template).
- `inclusivity/aggregate.py:16` `detectable_percent` (sampled era).
- `oligo/grade.py:491` `is_mgb`. `Oligo.has_mgb` (`models.py:208`) supersedes it, and the two have drifted: `is_mgb` ignores the reporter and quencher names.
- `search/orchestrate.py:218` `load_outcome`.
- `taxonomy/organisms.py:49` `category_of`.
- `gui/runs.py:36` `STATES`.

**Used only by tests:**
- `charts.site_glyph` (item 7).
- `models.py:638` `Assay.channel_of`.
- `models.py:642` `Assay.locus_of`.
- `variants/chain.py:124` `Candidate.length_difference`.
- `variants/chain.py:132` `Candidate.forward_span`.
- `taxonomy/resolve.py:137` `parse_taxonomy_xml`.
- `search/planner.py:78` `is_offpeak`: possibly meant for NCBI etiquette later. Unsure; ask.

Removing the test-only functions means removing their tests too.

### 18. `OligoDesignSource.commit` is never filled [V] (drift between key spellings; a bug)

- `pipeline.py:96` reads `old.tool.get("commit", "")`.
- `provenance.py:83` writes the key `"git_commit"`, which the xlsx (`:114`) and the CLI (`:110`) read.

As a result, `report.html.j2:711` `{% if od.commit %}…commit …{% endif %}` never renders for a carried-over design. Use `"git_commit"`. This changes results.json (the `oligo_design_from.commit` value) for new records only.

### 19. Unused parameters [V] (remove, low)

- `xlsx._section_status(result, section)`: `result` is unused (`:89`).
- `variants/exhaustive.py`: `assess(amplicon)` (`:508`), `_align(rules)` (`:934`), `_run_length_breakdown(bulges)` (`:972`), `_membership(scan_taxon)` (`:1963`).
- `variants/chain._candidate(max_indel)` (`:281`).
- `variants/partitioned._record(uid)` (`:67`).
- `ncbi/runner.run(query_fasta)` (`:131`). Unsure: it may be part of an interface.

The GUI's `user` and `exc` arguments are FastAPI dependencies and handler signatures; keep them. Found with `ruff --select ARG`.

### K. Deliberate fallbacks to keep [V]

Each is confirmed by CHANGELOG "Without charts, the tables remain" and the round-3 decision:
- The per-year tables (`report.html.j2:452-485`).
- The table "Off-target sites per species" (`:591-610`), but fix its closest-site rule (item 5).
- The full hairpin/dimer table (`:773-790`).
- The `site_maps` section and the totals line in Part A: the A/B split is deliberate (decision `2026-11-20-sign-off-two-pages`).
- `merge_binding_variants`/`_Merged` (used).
- `TierOverview.closest`, used only by the old notice (item 11).
- `figures.coverage_steps` (Part A) vs `coverage_accounting` (Part B): different figures, not duplicates.

---

## Notes on method

- Template variables: a regex on the keywords passed to `render()`, each hit then read by hand.
- CSS: each class in the style block grepped in the template body and in the Python that emits HTML.
- Dead definitions: `tools/defs.py`. Model fields: `tools/fields.py`. Finding attribution: `tools/finds.py`. All in this scratchpad folder.
- Workbook sheet names: read from a record produced by `tests/test_run_full.py`, run with `--basetemp` in the scratchpad.
- Reproduce with `python -I <tool> /home/user/qpcr-assay-check`.
- Any removal must leave `ruff check .`, `ruff format --check .` and `pytest -m "not live"` passing (CLAUDE.md). Items 3, 7, 11, 12 and 17 change tests.
