# Advice: Part C "Methods, rules and limitations" shortened and at full width (2026-11-27)

Requested by the user on 2026-11-27 on the influenza A record of 2026-11-27 09:20Z ("There is a
lot of text in the Methods, rules and limitations section which also seems to be squeezed in 1
kolom. Ask advisor how to shorten this text (table?) and use the whole width of the page") and
given by a subagent of the Claude Code session, read-only.

This file holds that advisor's report as delivered, unedited. It is an opinion, not a project
decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and in
the knowledge bundle's session pages.

---

# Part C "Methods, rules and limitations": how to shorten it and use the page width

Advisor review, 2026-11-27. Material: the influenza A record of 2026-11-27 09:20Z (Part C as text, HTML, A4 pages 12–14, 1440 px screenshot), the template, `html.py`, `oligo/grade.py`, `specificity/assess.py`, `docs/MISMATCH_CLASSES.md`. Advice only: no repository file was changed.

[V] = I checked it in the record, code or docs. [J] = my judgement. All measurements come from rendering the original Part C and my mock-up with the same stylesheet in Chromium, at A4 print width.

---

## 1. Bottom line

- **On screen** the text really is "squeezed into one column". Every paragraph is capped at 46rem (about 780 px) inside a 1,536 px page, so the right half is empty. The Limitations list is the exception: it is not capped, so it runs the full width in a different (serif) font. [V `p { max-width: 46rem }`, screenshot]
- **On A4** the text already uses the full width. The problem there is density. The prose is set in 7.4 pt grey (`.meta`) at about 200 characters per line, with no breaks: "Mismatch classes" is a single paragraph of 744 words. Comfortable reading needs 60–90 characters per line. [V print CSS, pc-12.png]
- **Simply removing the width cap would make things worse.** Lines of 200 characters on screen are harder to read than the narrow column. The width should be used by **tables**, plus a few **short text blocks side by side**, not by stretching paragraphs. [J]
- **About tables:** turning the text into tables makes it much easier to read and to audit, and it shows where a rule has no stated basis. It does **not** save much paper by itself. The 744-word paragraph is already the most paper-efficient form; it is just unreadable. The real cuts come from removing the repeats (section 2). Measured on the mock-up: **2,533 → 2,188 words (−14 %)**, and **2.74 → 2.64 A4 pages**. That saves no whole page. Section 6 says what a whole page would cost.

**Recommendation (yes/no):** Rebuild Part C as seven numbered blocks, C1–C7, mostly tables, with every repeat removed and one type style. No rule, number or reference changes. Fix the wording points in section 5 at the same time, each of which you approve. The mock-up shows the result with this record's real content.

---

## 2. Why it reads as a wall: section by section

| Section (words) | What goes wrong | Repeats [V] |
|---|---|---|
| **Rules applied** (452) | Four run-in paragraphs that mix three kinds of content: definitions (amplicon, status window, percentages), a table legend (dot, letter, grey letter) and caveats. The first sentence holds a 60-word bracket. | The alignment legend is also under the whole-fragment table (Part B). The "Status window" text is almost the same as Part B's inclusivity note (template line 454). "Classes present published data… in silico does not replace…" appears again in the caveat and in C7. |
| **Mismatch classes** (744) | One paragraph with no breaks. It holds 5 class definitions, about 15 rules, 8 literature references, the RNA caveat, the mix caveat, ΔTm, "Tm ≤ annealing" and quantification. You cannot see which rule rests on which source, or which rule has no source. | The single-MGB-mismatch rule is stated twice. Stadhouders and Lefever are named three times. The ΔTm explanation of the 3′-terminal mismatch is repeated in Limitations. |
| **Queries with incomplete evidence** (278) | The answer ("None") is one line. Three more paragraphs follow, two of which explain the search and are not about this record's queries. | "Reported down to…" repeats Part B "What the searches could report". "What the search cannot find" repeats Limitations bullets 1–2. The opposite-primer sentence appears **three times** in Part C. |
| **Methods** (304) | Already a table, which is good. The BLAST row mixes parameters sent to NCBI with the tool's own settings. "Platform" and "Run mode" each take a full row for one value. | The RIDs are also in Part B "Searches". `blast_versions` repeats the database row. |
| **Limits applied** (198) | Already a table, which is good. One empty value: `tier_waivers` prints nothing. | The "Search" row repeats the BLAST parameters in Methods (database, expect, word_size, hitlist_size, background_taxids). |
| **Settings that differ** (77) | Fine. "The inputs hash above" points to Part A, not to anything above it in Part C. | – |
| **Limitations** (459) | One serif paragraph about oligo design, then 8 bullets about the search, in a different font and size. The bullets are mostly the same points as "What the search cannot find". | Word size and E-value (2×), opposite primer (3×), ΔTm and terminal mismatch (2×). |
| **Required statements** (70) | Fine. Keep the wording exactly. | Statement 1 also appears in "Rules applied"; once in C7 is enough (Part A keeps its short form). |

Across the whole of Part C:
- There are no section numbers, so Part B cannot point anywhere precisely. Part B already sends readers to "Mismatch classes under Inclusivity", which no longer exists, and to "Part C, 'What the search cannot find'". [V]
- Three type styles are mixed: 7.4 pt grey sans, 9.5 pt serif, and a full-width serif list. The grey reads as "unimportant", yet this is the audit text. [V]

---

## 3. Proposals

### P1. One layout rule for Part C (CSS only)
- Tables take the full width, on screen and on A4.
- The little prose that remains sits in short **cards**, two side by side (a CSS grid that falls back to one column on a phone). No line runs past about 90 characters.
- All of Part C uses one type style: sans, in ink colour (not grey), 7.6 pt in print like the other tables. No serif, no 7.4 pt grey paragraphs.
- Print uses a narrower cell padding (0.1 rem) in Part C only.

### P2. Number the blocks C1–C7, with a one-line contents list
C1 Terms and counting rules · C2 Mismatch classes · C3 What the search could and could not find · C4 Methods · C5 Limits and settings · C6 Other limitations · C7 Required statements. Part B then points to "Part C2" and so on.

### P3. C1 "Terms and counting rules": a two-column table (term, then the rule with a "→ where used" tag)
This replaces "Rules applied". The alignment legend stays only under the whole-fragment table in Part B, where the reader needs it; take its fuller wording ("an ambiguity code in the genome: a match, but not the same base") there.

| Term | Rule |
|---|---|
| Predicted amplicon | Two primer sites that can prime, facing each other on one record within 2000 bp; identical amplicons counted once. Can prime: perfect or tolerated always; at risk or undetermined at warning level or better; likely failure never. In the cautious tiers (near_neighbours) an at-risk or undetermined site, and a gapped probe site, acts at warning level. → Part B, Off-target |
| Status window | Outcome pooled over the last 3 complete collection years (inclusivity.status_axis) and the current one: the latest release year listed, never the last year with data… a single year in the window with at least 30 genomes below the FAIL limit gives Review… → Part A; Part B, Inclusivity |
| Distinct site patterns | Clonal outbreaks sequenced many times weigh heavily in the genome count and once in the pattern count; neither figure is the share of strains in circulation. → Part B, Inclusivity |

Part B then keeps only a one-line pointer instead of its own copy of the status-window text (this saves room in Part B as well).

### P4. C2 "Mismatch classes": two tables and four cards (the biggest gain in readability)

**Table 1: classes.** This settles the confusion between "indeterminate" and "undetermined" (see 5.2).

| Class | Meaning | Counted as |
|---|---|---|
| perfect / tolerated | no mismatch, no gap / expected to cost little | **detectable** (the inclusivity limits apply to it) |
| at risk | a measurable delay is expected, worse near the limit of detection | not detected |
| indeterminate | no published basis | R6, R9: **undetermined**, left out of the percentage; gaps (R5): not detected |

The class-to-count mapping is checked against `variants/exhaustive.py` (`undetermined()`: R6 and R9 only) and `oligo/grade.py` (`combination_outcome`: "an unexplained gap: not detected"). [V]

**Table 2: rules.** Columns: Rule, Site, Class, Basis. Group rows: Primers, MGB probes, Probes without MGB, Any oligo. Every row comes from the current record text, and the rule numbers from docs/MISMATCH_CLASSES.md. [V]

| Rule | Site | Class | Basis |
|---|---|---|---|
| R1 | single mismatch in the last 5 nt | by mismatch type and position | Stadhouders et al., J Mol Diagn 2010, Table 1 (Taq polymerase on DNA) |
| R9 | MGB probe: 1 mismatch in the 3′-most 7 nt (under the MGB) | likely failure | Kutyavin et al., Nucleic Acids Res 2000 |
| R9 | probe without MGB: 3 or more mismatches | likely failure | expert judgement, no published rule |
| R9 | probe without MGB: 1 mismatch outside the last 5 nt | tolerated | *not stated in the record* (see 5.3) |

The Basis column keeps each reference next to the rule it supports. It also shows openly where the record names no basis (two cells, both shown in the mock-up).

**Four cards** in two columns, in the record's own words, shortened:
- "What a class is": the master-mix caveat (`GRADE_CAVEAT`) plus "not a predicted Cq".
- "This assay detects RNA" (Christopherson 1997). This card is conditional, as it is now.
- "Detection, not quantification" (Bru 2008).
- "ΔTm and Tm ≤ annealing". The terminal-mismatch point moves here from Limitations.

### P5. C3 "What the search could and could not find": one table
This merges "Queries with incomplete evidence", "What the search cannot find" and the 8 search bullets of Limitations. Columns: Limit, then what it means, with a "→ where to check" tag.

| Limit | What it means for this record |
|---|---|
| Queries with incomplete evidence | **None**: every relevant alignment of every query was assessed. Sites found: 45 critical, 522 warning, 4645 minor; 5326 sequence windows used. → sheet "Hits per query" |
| E-value cut-off 1000.0 | Lower than Primer-BLAST's default of 30,000 for primers… the smallest reportable score depends on each search's size; **an absent hit is not proof of absent binding**. → Part B, "What the searches could report" |
| Database core_nt | No WGS draft assemblies; newest records arrive after a delay (seen live on 2026-09-23…); for organisms known mostly from draft genomes only complete genomes and other core_nt records are covered. |

Each point now appears once. The first row is shaded, because it is the only row specific to this record.

### P6. C4 Methods and C5 Limits: keep the tables, tighten them
- Merge Platform and Run mode into the Software row. Merge Melting temperature, Structures and 3′ end stability into one "Thermodynamics" row.
- Split the BLAST row into **"sent with each search"** (program, database, word_size, expect, filter, reward, penalty, gap costs, hitlist_size, result format) and **"tool settings"** (max_taxids_per_search, max_searches_warn, background_taxids, target_tier, relevance min_identical_bases). I checked this split against `ncbi/blast.py` `build_put_params` and the FORMAT_TYPE parameter of the Get request. [V]
- Make the taxon restriction check a small table: Tier | inside | set aside | not checkable | RID. This folds in the "Search and RIDs" row, so the RIDs appear once in Part C (they stay in Part B as well).
- Limits: drop the "Search" group (it is in C4). Print `tier_waivers none` instead of an empty value. Mark the one setting in the limits table that differs from its default with a small "≠ default" tag that ties it to the differing-settings table.
- "The inputs hash above" becomes "the inputs hash (Part A)".

### P7. C6 Other limitations: a five-row table
The five oligo-design limitations (defaults are not acceptance criteria; Tm and energies are estimates; structures only at the annealing temperature; modified probes; sequences only) become a table with short row labels. The search limitations have moved to C3.

### P8. C7 Required statements: unchanged
Keep it word for word, at full width. It no longer needs to appear a second time in C1.

### What moves to the workbook or docs, and what stays
- **Stays in the record** [J]: every rule that can decide a class or status, with its source; every limit and setting value; the search parameters, RIDs and software identity; all search limitations; both required statements. An auditor can rebuild every class and status from Part C without the repository.
- **Already in the workbook, so one pointer line is enough:** "Hits per query" (per-query floors and cut lists) and "Configuration" (the full effective configuration). Nothing new needs to move.
- **docs/MISMATCH_CLASSES.md** stays the long-form rationale. The record cites it once, in the C2 card, and does not depend on it. Note that an auditor without the repository cannot open it. If you want R2–R3 to be reproducible from the record alone, add three rows to the rules table from section 4 of that document (R2: single mismatch beyond the last 5 nt, tolerated; R3: 2, 3 or 4 mismatches within the 3′-most 16 nt; R3b: beyond −16). That adds about 0.1 page. This is optional, and the rows are not in the mock-up because the current record does not contain them.

---

## 4. Mock-up

`/tmp/claude-0/-home-user-qpcr-assay-check/11a8236c-4c6b-584c-a5b6-87a742a716a1/scratchpad/advisor5/mockup.html` holds this record's Part C, restructured as above, with the project stylesheet plus a short Part C block at its end.
- Open it in a browser for the screen view. Print it to A4 for paper; `mock.pdf` in the same folder is that print, 3 pages with page 3 half empty.
- Every number, reference and rule in it is copied from the record. The two "*not stated in the record*" cells mark gaps; they are not new content.
- What I did not do: run it through the real renderer. Conditional parts (RNA card, no-search records, incomplete queries) need the same `{% if %}` logic as now.

---

## 5. Points in the current text that look wrong or overstated (separate from the layout)

1. **Class definition contradicts R9.** "*indeterminate* (… a single mismatch in an MGB probe)". A single mismatch **under** the MGB (the 3′-most 7 nt) is *likely failure* (R9; the same paragraph says so later). The definition should read "a single mismatch in an MGB probe outside its 3′-most 7 nt". [V template, docs R9]
2. **Two words for one idea, and the gap case.** The class is "indeterminate"; the count outcome is "undetermined". A gapped site (R5) gets class *indeterminate* but is counted **not detected**: its outcome becomes "at risk" in `combination_outcome`. A reader of the whole-fragment table sees an "indeterminate" site in an "at risk" row and cannot tell why. The P4 classes table explains this. You may also want to add the words "(gap: counted not detected)" to the site note in Part B. [V code]
3. **Basis not stated, which reads as more certain than it is.** In the record's sentence, "MGB probe … with 2 or more [mismatches] a likely failure" follows the Kutyavin citation, and the unmodified-probe single-mismatch steps (tolerated outside the last 5 nt, at risk inside) follow nothing. docs/MISMATCH_CLASSES.md calls both **expert judgement** (R9: "position-free … expert judgement"; "Süß et al. 2009 … could not be obtained; the rule for a single mismatch in an unmodified probe stays expert judgement"). I suggest putting "expert judgement" in those two Basis cells. That changes the wording only, not the rule. You decide. [V docs]
4. **"Lefever's Fig. 6 puts near 15 dCq"**: the docs say this value was "read from the figure". Add those words. [V docs R3/R8]
5. **R8 wording**: "3 + ≥2 or 4 + 1". The code (`pair_fails`) uses "≥3 with ≥2, or ≥4 with ≥1". The current text can be read as "exactly 4 + exactly 1". Suggest "≥3 + ≥2, or ≥4 + ≥1". [V code]
6. **"Modified probes (MGB, LNA, ZEN and similar) are not modelled"** seems to contradict R9, which does grade MGB probes. What is not modelled is their Tm and structures. Suggest: "The Tm and structures of modified probes (MGB, LNA, ZEN and similar) are not modelled." [J; please confirm against what the oligo QC actually computes]
7. **Cross-references that lead nowhere:**
   - "flagged in the **Rationale**": the Rationale prints only when inclusivity is not "No flags" (template line 494), so in this record it does not exist.
   - "given per tier and oligo under **'search'**": the printed name is "What the searches could report" (Part B).
   - Part B's 'see "Mismatch classes" under **Inclusivity**': it is in Part C.
   - "The inputs hash **above**": it is in Part A.

   Section numbers (P2) fix all four. [V]
8. **`tier_waivers` prints an empty value** in Limits applied. [V pc-13]
9. **Not in Methods: the variant search by BLAST.** With `variants.source: blast_partitioned` (this record), records too long to scan directly are searched with their own BLAST parameters: word size 11, expect 10, hit list at least 500 (`variants/partitioned.py` line 201). Part C lists only the off-target parameters. It probably made no difference in this record (influenza segment-7 records are short), but other assays need it. Suggest a conditional Methods row, "Variant search (long records)". [V code]
10. **Not re-checked by me:** Ye et al. 2012 (≈0.5 % missed at word size 7; Primer-BLAST expect 30,000) and the Christopherson, Bru, Klungthong and Otwell figures. They match docs/MISMATCH_CLASSES.md where the docs cover them. I did not re-read the papers.

---

## 6. Effect and ranking

Measured: same stylesheet, A4, 186 mm content width, 1032 px per page of content.

| Section | Now (px / words) | Mock-up (px / words) |
|---|---|---|
| Rules applied → C1 | 328 / 452 | 293 / 322 |
| Mismatch classes → C2 | 451 / 744 | 922 / 722 (also takes the ΔTm limitation and the "Whole fragment" caveats) |
| Queries + Limitations (search bullets) → C3 | 235 + ≈380 / 278 + 347 | 396 / 420 |
| Methods → C4 | 477 / 304 | 332 / 269 |
| Limits + differing → C5 | 584 / 275 | 414 / 219 |
| Limitations (design paragraph) → C6 | ≈150 / 113 | 168 / 122 |
| Required statements → C7 | 143 / 70 | 99 / 71 |
| **Total** | **2,823 px = 2.74 pages / 2,533 words** | **2,723 px = 2.64 pages / 2,188 words** |

C2 grows on paper (a dense paragraph is cheaper than a table). C1, C3, C4 and C5 shrink because the repeats go.

Ranking (value against effort):

| # | Proposal | Value | Effort | Note |
|---|---|---|---|---|
| 1 | P1 layout rule + P2 numbering + 5.7 cross-references | high (screen width, one type style, working pointers) | low (CSS + headings) | Do this first. |
| 2 | P5 merge the search text into C3 | high (three copies become one) | low–medium | Template + `LIMITATIONS` list |
| 3 | P4 C2 tables + cards | highest for audit (basis per rule visible) | medium | Text is ready in the mock-up; needs your OK on 5.1–5.5 |
| 4 | P6 Methods/Limits tightening, P7, P3 | medium | low | – |
| 5 | Part B pointer instead of the copied status-window text | medium (Part B shorter, by about 0.1 page) | low | – |
| 6 | Optional R2–R3 rows | medium for self-containment | low | +0.1 page |

**What a whole page would cost** [J, not recommended]: about 1.7 of Part C's 2.7 pages is text that is identical in every record of v2.2.0 (C1, C2, most of C3, C6). Saving a whole page would mean moving it into a versioned "method description" that ships with the software, identified by the code fingerprint. Many quality systems work this way, with the method in the validation file and the record citing its version. But the record would then no longer stand alone for an auditor, which goes against your constraint. I would not do this now.

---

## 7. Decision for you (yes or no)

**Rebuild Part C as in the mock-up:**
- seven numbered blocks;
- tables at full width and short side-by-side cards on screen;
- one type style;
- every repeat removed;
- no rule, number or reference changed.

**Also approve corrections 5.1–5.8:**
- 5.1 MGB definition;
- 5.2 the gap case explained;
- 5.3 "expert judgement" in two Basis cells;
- 5.4 "read from the figure";
- 5.5 the R8 "≥" wording;
- 5.6 modified-probe wording;
- 5.7 cross-references;
- 5.8 `tier_waivers none`.

**And add 5.9**, a Methods row for the variant BLAST parameters, shown only when they were used.

**Expected result:** about 14 % fewer words, about the same paper (−0.1 page), Part C readable on screen at full width, and a rules table in which each rule sits next to its source or is marked as having none.
