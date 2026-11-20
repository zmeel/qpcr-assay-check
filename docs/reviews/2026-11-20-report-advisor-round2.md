# Report review, second round: independent advisor, on the user's five comments

Requested by the user on 2026-11-20 after the first HSV-1 report in the three-part layout ("I like
to hear your opinion and the opinion of the advisor on my comments before we decide what to
remove or move") and carried out by a subagent of the Claude Code session, read-only, with the
user's report (not in the repository) printed in Chromium.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon are
checked against the code first.

---

# Report review, second round: the user's five comments on the three-part report (2026-11-20)

**Reviewer:** independent advisor (molecular diagnostics, laboratory quality systems, report design). I worked read-only: nothing in the repository was changed, nothing was committed, and no NCBI calls were made.

**Material:**
- The user's HSV-1 report `…20261120T134914Z-18b4dfe5`, made at commit bbd8e96. I printed it with Chromium/Playwright (A4, 12 mm margins) and got 30 pages, the same as the user. I read the PDF text page by page and rendered pages 6, 7, 8, 16, 22 and 26 as images.
- The code: `report.html.j2`, `report/html.py`, `grouping.py`, `xlsx.py`, `specificity/variants.py`, `search/assess.py`, `results.py` and `pipeline.inputs_hash`.

**[V]** means I checked it in the code or the report. **[J]** means it is my judgement.

---

## 1. "There is a Part B · Evidence but not a Part A." Agree.

- **[V]** The template has `.part-b` and `.part-c` labels but no Part A label. Page 1 also sends readers to "Methods (appendix)" and "Required statements, appendix" instead of naming Part C.
- **Change [J]:**
  - Add "Part A · Sign-off" above "What was checked", in the same style as the other part labels.
  - Under the title, add one line: "Part A Sign-off · Part B Evidence · Part C Appendix (rules, limits, methods, required statements)".
  - Use "Part C" wherever the report now says "appendix".

## 2. "Variants per oligo seems redundant with the Whole fragment part." Partly agree.

These facts are all **[V]**:
- **Same population.** Both tables come from the same target-tier sites: each genome's best copy, measured alignments only (`build_variant_summary`). The per-oligo denominator is the measured sites of that one oligo. The fragment denominator is the records where all three sites were measured. These can differ, but in HSV-1 both are 614.
- **The frequencies are already in the fragment table.** Next to every site that is not perfect, the whole-fragment table prints its per-oligo frequency over all records (`site_frequency`, e.g. "at risk 1.1%"), together with its class and ΔTm.
- **Every variant already appears there.** HSV-1 has 14 combinations, and all of them are shown (8 Needs attention, 6 detectable; the limits are 30 and 10). Each of the 11 per-oligo variants that are not perfect appears in at least one fragment row. The forward variant the per-oligo table lumps as "1 other at risk variant" (`.T..C......C.TT`, 0.2%) is shown in full only in the fragment table.
- **The per-oligo totals are partly duplicated.** "Forward: 0 perfect, 594 tolerated, 20 at risk" repeats "Covers 594 (96.7%)" in the Copies table.
- **What only the per-oligo table carries:**
  - the change notation ("-21 C-A, -18 S=C, -11 M=C, -8 K/A");
  - the rule (R2+R3b, R9) with its literature note;
  - the three-line alignment;
  - the record count, an example accession and the first/last release.
- **The change notation is in no workbook sheet.** The "Oligo variants" sheet has a "Class rule" column but no changes column.
- **Part of the table does not print.** In print, the forward and probe tables lose their Records, Example and Release columns and the end of each note at the right edge (pages 7–8).

**Change [J]:**
- Replace the 1.6-page section with a compact **"Site variant key"**, about 0.4 page: one line per variant that is not perfect, with oligo, short ID (F1, P2…), class, rule ID, changes, records and %.
- Keep the same selection as now (`oligo_view`). This preserves the guarantee that a variant missing from a capped fragment table still appears in the record.
- In each oligo heading, keep its totals line.
- Drop the alignments and the literature sentences. Part C "Mismatch classes" already explains the rules by ID, and the fragment cells already show the bases.
- Optionally, put the variant ID next to the frequency in each fragment cell.
- Add a "Changes" column to the "Oligo variants" sheet.
- Point the site-map caption on page 1 to the key.

## 3. "The first column of the Oligo quality control tables is too small." Agree. It is the main reason the section runs to 3.6 pages.

- **[V] The cause.** The Value cell is `td.num` (`white-space: nowrap`). One value, "78 nt from forward primer, 19 nt from reverse primer; sequence matches the antisense strand", stretches that column to 459 px. At print width that leaves the Check column 67 px, about one word per line.
- **[V] Text is repeated.** The Check cell repeats the subject ("Forward primer HSV-1-gG1-FP GC content") under a group row that already names it. It then adds the full message, which is also printed in Part A's findings.
- **[V] Text is lost.** The table is 800 px wide on a 703 px page, so in print the "Rule applied" column is cut off ("preferred 54–70 °C" shows as "preferred / 54–70"; the heading prints as "Rule appl").

**Change [J]:**
- Use a matrix:
  - rows: the check (GC, Tm, 3′ G/C, runs, length, site in the reference amplicon…);
  - columns: Forward | Reverse | Probe, each cell holding the value and a chip;
  - a last column: the limit, written once.
- Pair and amplicon checks go in a short second block.
- Print the message only for rows outside the range, as a full-width line under the row.
- Let values wrap. Move the probe-position text into a note.
- Expected length: about 1 page. The "Oligo QC" sheet already has every check.
- Hairpins and dimers (about 1.5 pages): print the worst-case sequence only for flagged structures; the "Structures" sheet keeps the rest.

## 4. "Hits and alignments per oligo: is it relevant? Move to the Excel?" Agree, with two conditions.

- **[V] It is mostly a repeat.** The table has 51 rows (17 query variants × 3 tiers) over about 3 printed pages. What a reviewer needs from it is already in Part B:
  - "Searches": complete yes/no, with the incomplete oligos named;
  - "What the searches could report": 9 rows per tier and oligo, with ranges over the variants;
  - the Findings: the two queries cut at `max_sites_per_query`, background FP_v8 and P.
- **[V] Moving it needs a new sheet.** The workbook's "Searches" sheet holds only hits per query, as text. It has no relevant, assessed, cut or reported-down-to columns.
- **[V] The record contradicts itself.** Two tables use the header "Hit list full" with different meanings:
  - In "What the searches could report" it means `list_full`, the list merely reached its size limit. For exclusivity RP it says "yes" (RP_v8 has 6,837 hits over two searches).
  - In "Hits and alignments per oligo" it means `saturated`, full and with a weakest hit that is still relevant. For RP_v8 it says "no".
  - Meanwhile "Searches" reports exclusivity as complete.

**Change [J]:**
- Add a workbook sheet "Hits per query" with all the columns now in the HTML table.
- In Part C, keep only the queries that are incomplete (hit list full and still relevant, or cut by the cap; here 2 rows), plus one pointer sentence.
- Rename the two concepts: "List reached its size limit" and "Relevant hits possibly cut".

## 5. "Effective configuration to the Excel?" Partly agree: move the full listing, keep the limits.

- **[V] It takes three pages.** The YAML is 1.3 pages of content, but it prints over three: page 26 carries only the heading. The `pre` element has `break-inside: avoid` and does not fit after the heading.
- **[V] It mixes machine-specific values with the science.** It includes `cache_dir: /work/cache`, URLs and timeouts. `inputs_hash` deliberately leaves `ncbi` and `report` out because they "do not change the science".
- **[V] It is the only place for several limits.** The two-column listing splits nested keys across columns, yet it is the only place in the record that states:
  - the inclusivity limits (warn below 95 %, fail below 80 %), the minimum genomes and the maximum undetermined share;
  - the primer and probe site levels (critical: at most 3 mismatches, 0 gaps, at least 5 clean 3′ nt);
  - the severity mapping (`amplicon_likely_detected: FAIL`, and so on).
- **[V] Page 1 points to the wrong place.** Its legend says "Limits: Methods (appendix)", but Methods lists none of these limits.
- **[V] The full configuration already exists in machine form.** `results.json` stores it (`RunResult.config`), and the 64-character inputs hash identifies it. No workbook sheet holds it.
- **[J] What the filed record needs.** A filed quality record must let an auditor see which acceptance limits applied without running software. A hash proves the configuration is the same as another run's, but it does not show what the configuration was. The defaults are fixed by the tool version and code fingerprint, which the record already prints.

**Change [J]:**
- Replace the dump in Part C with:
  - **(a) "Limits applied"**, a compact table of about half a page:
    - the reaction conditions;
    - the inclusivity limits, status window, minimum per year and maximum undetermined;
    - the site-level definitions;
    - the severity mapping;
    - the search caps (`max_sites_per_query`, `max_amplicons`, `partner_scan_max_windows`).
    The oligo limits stay in the QC "Limit" column.
  - **(b) "Settings that differ from the defaults"**, as key, value, default and source (assay file or configuration file). It replaces "Settings from the assay file", which omits configuration-file overrides such as `config_annealing_55C.yaml`.
  - **(c)** One sentence: "The complete effective configuration is in results.json (`config`) and workbook sheet 'Configuration'; inputs hash …".
- Add that sheet (key path, value, default).
- Fix page 1 to say "Limits: Part C, Limits applied".

---

## Other things the HSV-1 record shows

1. **Part A runs to 3 pages [V].** "Findings that need a decision" lists 21 lines: 10 from oligo design and 11 from specificity. The specificity lines repeat Part B's Findings word for word, and the decision box ends up alone on page 3. **[J]** List the Exceeds-limit and Incomplete lines in full (6 here). Show the Review lines as one count per summary row, with the closest site. Leave the full list in Part B. This keeps the sign-off on 2 pages, decision box included.
2. **Wide tables are cut at the right edge in print [V].** The `.scroll` wrappers have `overflow-x: auto`. Measured at A4 print width:
   - the whole-fragment tables are 1,188–1,214 px wide on a 703 px page;
   - the per-oligo tables are 1,174–1,321 px;
   - "Closest off-target sites" is 1,190 px.

   The worst case: the reverse column of the fragment table loses its last 4 bases, so the T at -2 that makes one reverse site "tolerated" does not appear on paper. This is the 3′ end of a primer, the most important bases in the record. It needs a print layout that wraps or stacks instead of clipping, and a test that no table is wider than the A4 print width.
3. **Python representations in Methods [V].** "BLAST parameters" prints a Python dict (`{'program': 'blastn', …}`), and the RIDs print as tuples (`('FXNATUU1014', '2026-11-19')`). Write them as text.
4. **h4 headings and some summary lines print in the serif body font [V]** ("Needs attention (8 combinations)", "Of 614 records…"). `h4` is missing from the sans-serif rule.

**Estimated effect [J]:**

| Part | Pages now | Pages after |
|---|---|---|
| Sign-off | 3 | 2 |
| Oligo QC with structures | about 5 | about 2 |
| Variants per oligo | 1.6 | 0.4 |
| Hits per oligo | about 3 | 0.2 |
| Configuration (with its blank page) | 3 | 0.7 |

The record would go from 30 pages to about 20, without losing any content from what is filed. Everything that moves out of the HTML gets a workbook sheet first.

In silico analysis does not replace experimental validation, and the laboratory must verify the software within its own quality system. Nothing above changes that, and Part A must keep saying it.
