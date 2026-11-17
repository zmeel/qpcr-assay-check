# Whole-project evaluation: independent advisor (molecular diagnostics, scientific software)

Independent evaluation requested by the user on 2026-11-17 and carried out by a subagent of the
Claude Code session, which read the project's documentation, code and tests read-only (no NCBI
calls; the run reports themselves are not in the repository). Scope: scientific validity, honesty
of the reports, fitness for a clinical laboratory, dependence on NCBI, the example assays, the
knowledge bundle, priorities. The seven findings of the code review fixed the same day (commit
c9b5c05) were outside its brief.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon were
checked against the code first.

---

# Whole-project evaluation of qpcr-assay-check (read-only)

**What I checked:** the documents listed in the brief, the grading, specificity, inclusivity, summary, NCBI and pipeline code, and the test suite. The tests ran offline: 1,190 passed, and the working tree stayed clean. I made no NCBI calls. The run reports themselves are not in the repository, so I could only check the run pages against the code and the assay files.

**How to read it:** "Verified" means I read it in the code or files. "Judgement" is my opinion.

## 1. Summary verdict

This is careful, unusually honest work. Every grading rule names its source or says it has none. Missing evidence is mostly kept out of "No flags". The exhaustive per-genome analysis is a real advance over sampled BLAST hits.

It is not yet fit to produce filed evaluation records in a quality system, for three reasons:
- **The version stamp is wrong.** Reports made from unreleased code still say v2.1.0.
- **Some evidence gaps can still sit under a "No flags" headline.**
- **Specificity and inclusivity use two incompatible mismatch rule sets.** One of them can miss off-target products.

All three are fixable. None of them invalidates the science.

## 2. Strengths

- **Sources are traceable.** R1–R9 cite page numbers, and expert-judgement rules say so in the code notes (`oligo/grade.py:353-405`). The Otwell comparison is honestly called calibration, not validation (`MISMATCH_CLASSES.md` §11).
- **Missing evidence is handled conservatively.** Incomplete coverage holds back both Review and Exceeds limit (`variants/exhaustive.py:1422-1442`, `pipeline.py:226-255`). More than 25% undetermined gives Incomplete. The bracketing figures and the distinct-pattern counts stop over-reading of redundant public data.
- **N in a judged site makes the genome undetermined, never a match** (`exhaustive.py:568-570`).
- **NCBI etiquette is followed.** BLAST is contacted at most every 10 s and each RID polled at most once a minute (`default_config.yaml:79-80`). E-utilities stay below their limits (`ncbi/http.py:23-28`). Backoff honours Retry-After. Jobs are resumable and every state is saved before the next call. UNKNOWN and "READY but error page" are each retried a bounded number of times (`ncbi/runner.py:178-224`).
- **The provenance of the example assays is explicit and honest** (see E).
- **The in silico disclaimer and the quality-system statement are in every report** (`report.html.j2:725-731`), in the CLI and in the README.
- **The run pages separate samples from the population** (for example `runs/influenza-a-2026-10-07-complete.md`, "Two live samples, not the population").

## 3. Problems found (most serious first)

**P1. Reports do not identify the code that made them (verified).**
- The version comes from installed package metadata (`__init__.py:6`).
- `scripts/run_assay.sh:12,28` mounts `src/` over the image's installed package. The GUI runs the image's own code.
- So two runs on the NAS can use different code and still carry the same version string.
- No git commit or rules version is recorded (`pipeline.py:376-386`).
- The run pages say "v2.1.0" for runs that used unreleased grading rules: the R9 ladder, terminal G2, the MGB region and the hold-back (`runs/influenza-a-2026-10-21.md`, `runs/legionella-2026-10-07.md`).
- Consequence: a filed record cannot be traced to the rules that produced it, which is the first thing an audit asks.

**P2. "No flags" is still possible on missing evidence (verified).**
- A configured off-target tier that was not searched (near neighbours, or human background) adds only an INFO line (`specificity/findings.py:82-86`, `pipeline.py:348-352`).
- Its summary row reads "Not assessed" (`report/summary.py:153-163`), but the overall status is combined from section verdicts only (`verdict.py:67-80`). So the headline can read "No flags" above a "Not assessed" row.
- The influenza run had near neighbours unsearched; its headline was Review only because QC was flagged.
- Organism-list names that did not resolve are never searched, yet exclusivity can still be PASS (`taxonomy/exclusivity.py:166-176`).
- This breaks the report's own rule that missing evidence never counts as no flags (`report.html.j2:136`).

**P3. Off-target sites use different rules from inclusivity, which errs both ways (verified).**
- Off-target sites are judged by counts (`default_config.yaml:119-124`). A site with no clean 3' bases left is "minor", and a minor site cannot prime (`pairing.py:75-77`).
- **Under-calling:** a single mismatch at -1 to -3 makes a site minor. Yet inclusivity grades terminal G3 and the -2/-3 G2/G3 mismatches as tolerated (`grade.py:39-43`). An off-target organism carrying exactly such a mismatch gets no predicted product.
- **Over-calling:**
  - A probe "binds" with up to 3 mismatches, including MGB probes, where R9 says one mismatch under the MGB is likely failure.
  - A critical primer site in a product is FAIL even when the probe does not detect the product (`default_config.yaml:126`).
  - The HSV-1, Entamoeba and Giardia "Exceeds limit" results rest partly on these rules. Human products with 4-5 mismatches per primer counted, although R3 would call such a primer likely failure.
- This is the open item `open/unified-off-target-rules.md`. I rank it higher than the bundle does, because of the under-calling.

**P4. R6 can hide a class change in primers and unmodified probes (verified).**
- Ambiguity codes are graded both ways only in the last 5 nt (`grade.py:184`, `356`). R3 and the probe rule count mismatches across 16 nt, or anywhere in the probe.
- Example: a code at -8 plus a real mismatch at -12 reads tolerated, but read as a mismatch it is at risk (R3).
- The same applies to one code plus one real mismatch in an unmodified probe.
- This is the same logic as the MGB fix of commit c9b5c05, not carried over. It matters for consensus records (influenza, HSV).

**P5. MGB probes are recognised for grading only by an exact "MGB" modification entry (verified).**
- `is_mgb()` checks the modifications list only (`grade.py:488-489`, `models.py:678`).
- The Tm-reliability warning also looks in the reporter and quencher names (`models.py:208-214`). So a quencher written "MGBNFQ" triggers the Tm warning but is graded as an unmodified probe, which is far more lenient.
- LNA probes are always graded as unmodified.

**P6. A deleted target region is invisible in a single-channel status (verified).**
- A genome without the region is left out of the whole-fragment denominator. It is only mentioned in the rationale (`exhaustive.py:2109-2122`).
- Only the per-channel figures count a complete genome without the region as not detected (`exhaustive.py:1759-1765`). Those enter the status only when channels are shown (`pipeline.py:212`), which is not the case for HSV, VZV, Giardia, Entamoeba or influenza.
- `rules/genome-outcome.md` states the channel behaviour as if it were general.
- Unavailable records count toward "complete", with no limit on their share (`variants/models.py:356`).

**P7. The report does not say what core_nt leaves out (verified in docs).**
- `ARCHITECTURE.md:204` records that core_nt holds no WGS draft assemblies, and `:237-244` that the newest records are not in it yet.
- The report's specificity limitations (`specificity/assess.py:39-61`) do not say this.
- For bacterial off-targets, whose genomes are mostly drafts, the exclusivity evidence is a subset, and the report does not tell the reader.

**P8. The status-window fix (commit c9b5c05, item 7) is only partly sound (verified).**
- Years are listed only when they hold records (`exhaustive.py:310`, `partitioned.py:118`). With no end year passed, the window ends at the latest of those rows (`inclusivity/models.py:161-162`).
- So on either axis, a target with nothing released this year is still judged on its last year with releases.
- The CHANGELOG's "(the current year)" and the rule page's "never the last year that has data" are true only while records are still being released.

**P9. RNA assays apply a DNA rule to the reverse primer (judgement, documented as R4).**
- In one-step RT-PCR the reverse primer's mismatch acts only in the RT step. Stadhouders found all 24 reverse-primer mismatches cost under 0.7 Ct with Taq + MMLV (`MISMATCH_CLASSES.md` R4).
- The 30.6% likely failure in the 2026-10-07 influenza run came entirely from one terminal G-A mismatch in the reverse primer.
- The caveat is printed, but the summary does not separate failures through the reverse primer alone.

**P10. R8 is now almost inert (verified).**
- Since 3 mismatches within 16 nt already gives likely failure (`grade.py:267`), `pair_fails` (`:475`) can only change the outcome in the "4 adjacent mismatches" exception.
- The real gap, a 2+2 pair (median about 15 dCq), is unflagged.
- Yet the report explains R8 as a working rule (`report.html.j2:366`, `483`).

## 4. Answers A-F

**A. Scientific validity.**
- *Well sourced:* R1/R2 (Stadhouders, Lefever), terminal G2 (Kwok, Huang), the MGB region (Kutyavin), R5c (Otwell; one study, limits stated).
- *Expert judgement without a source:*
  - The "avoid" split by position.
  - Interpolation at -4.
  - The 4-adjacent exception.
  - R3b beyond 5 mismatches.
  - R5b homopolymer classes.
  - All of R6.
  - The unmodified-probe ladder: its "last 5 nt" borrows primer logic for a hydrolysis probe whose 3' end is blocked. I find that physically weak.
  - MGB probes with 2+ mismatches.
  - `judge_from_parts: detectable`.
  - The 95/80/100/25/30 status thresholds (labelled as starting points).
- *Code against documentation:* matches for R1-R3, R5-R9 and the genome outcome. Exceptions are P4, P5, P6, P8 and P10.
- *Stadhouders Table 1 check is unclear.* `MISMATCH_CLASSES.md:383` says it was "checked against the PDF"; `open/stadhouders-table-check.md` says it is unchecked and needs the PDF.
- *Fixes of c9b5c05:* items 1-6 are sound in principle. Item 5's "unavailable" needs a cap (P6). Item 7, see P8.

**B. Honesty of the reports.** Mostly exemplary: bracketing figures, distinct patterns, the hold-back, and "not the share of strains in circulation". Gaps are P2, P6 and P7. The disclaimer is present, but only at the end of the report. One line in the summary at the top would help, since reviewers read page 1.

**C. Fitness for a clinical laboratory.**
- *What a lab can conclude:* of the public NCBI records of the target taxon in the window, this share carries sites that the cited primer studies class as detectable, and no product was predicted in the searched tiers within core_nt.
- *What it cannot conclude:* clinical sensitivity, shifts in limit of detection, quantification accuracy, cross-reactivity outside the tiers or outside core_nt, or anything about probe behaviour under MGB/LNA beyond the rules.
- *What a quality system needs:*
  - Release tags, with a commit and rules version in every record (P1).
  - A single code path on the NAS.
  - A frozen offline verification pack with known answers per rule, run on each release. The 1,190 developer tests are not a lab verification.
  - The effective configuration archived per run. The runs used a NAS config (`status_axis: collection`) that is not in the repository.
  - A record of who ran it. The reviewer box exists; the GUI records no user identity.
- *Alarm fatigue:* primer3 Tm under the default 3 mM Mg put HSV-1's 20-year-old assay at Exceeds limit on oligo QC.

**D. Dependence on NCBI.**
- *Robust:* resume, backoff, cache, bounded resubmission, error pages detected. The 2026-10-20 hold was handled by resuming.
- *Weak points:*
  - Resubmitting after 90 minutes (`default_config.yaml:84`) may push a held search to the back of the queue (judgement).
  - The off-peak advice is only a log warning, and there is no count of searches per 24 h across runs.
  - Database version and BLAST version are recorded, but nothing flags a database change between yearly runs.
- *Unverified from the repository:* the URL API hit-list maximum, the per-search taxid limit, and the gap costs for 1/-3 scoring. All are labelled as such.

**E. Example assays.**
- *Provenance is honest in every file:*
  - HSV-1: checked against Ryncarz 1999.
  - CDC N1: checked against two papers and the genome record.
  - Influenza: from the Erasmus MC protocol, with the author's permission recorded.
  - Giardia: supplied with Verweij 2004 but explicitly not read out of the paper.
  - Entamoeba, Neisseria, enterovirus, HSV-2 and VZV: supplied by the user, unchecked.
  - Legionella: placeholders in the repository, while the runs used a file kept on the NAS, so those run pages cannot be reproduced from the repository.
- *Run conclusions* agree with the quoted figures, with three caveats:
  - The HSV-1 page's counts (8,964 HSV-2 sites; 31 human products) come from before the duplicate-per-variant fix and are probably inflated. The page does not say so.
  - Giardia's "the probe detects G. microti and G. psittaci" rests on the permissive ≤3-mismatch probe criterion (P3). The page gives no probe mismatch counts.
  - Entamoeba's Exceeds limit comes from products the probe is not expected to detect. That is a consequence of the severity setting, not of predicted detection.

**F. The knowledge bundle.** Usable and well linked, but these statements are stale or contradictory:
- `rules/inclusivity-status.md:43` says "Incomplete, unless already below the limit", which contradicts the hold-back in place since 2026-10-07.
- `README.md:209` says a single MGB mismatch has "no published outcome… undetermined"; since 2026-10-02 one under the MGB is likely failure.
- `MISMATCH_CLASSES.md`:
  - The §8 F2 example still says at risk (3 mismatches are now likely failure).
  - §7 says history is "not built yet" (history was dropped).
  - §9 item 4 is partly done.
  - §10 contradicts the Stadhouders open item.
- `default_config.yaml`:
  - Line 167: "0-1 mismatch, no 3' mismatch" is stale.
  - Line 256: "off = counted as an escape" contradicts line 250 and the code (undetermined).
  - Line 228: the comment stops mid-sentence.
- `rules/genome-outcome.md` overstates the deletion rule (P6).
- `status.md`:
  - The "Latest runs" table lacks the HSV-1 run.
  - "VZV first run under way" has no follow-up since 2026-10-23.
  - The frontmatter date is 2026-10-05.
- `CLAUDE.md:51` ("LICENSE not yet chosen") conflicts with the LICENSE file already in the repository.

## 5. Ranked priorities

1. **Make every record identify its code.**
   - What: put the git commit, a dirty flag and a rules version in `results.json` and the report header. Run the GUI and the script from the same code. Cut a release before anything is filed.
   - Why: without it no report is auditable (P1).
2. **Close the "No flags" gaps.**
   - What: a configured tier that was not searched, or an unresolved organism name, gives Incomplete or Not assessed at the overall level. Cap the share of unavailable records. Count complete genomes without the region as possible escapes in the main status.
   - Why: this is the report's own core honesty rule (P2, P6).
3. **Use one rule set for off-target and target sites.**
   - What: at minimum, any primer site that inclusivity calls tolerated or at risk can prime off-target, and probe binding follows R9, including MGB.
   - Why: it removes a possible blind spot for cross-reacting organisms and the spurious Exceeds limit results (P3).
4. **Extend R6 and MGB detection.**
   - What: grade ambiguity codes both ways across the 16-nt region and the whole unmodified probe. Recognise MGB from the quencher name, or refuse the ambiguity.
   - Why: small changes that prevent silent misgrading (P4, P5).
5. **State core_nt's composition in the report's limitations.**
   - What: no WGS drafts; the newest records lag. Consider a Datasets-based check of the near neighbours for bacterial targets.
   - Why: otherwise the exclusivity scope is overstated (P7).
6. **Build a lab verification pack.**
   - What: offline fixtures with planted variants per rule and the expected classes and summary, run per release. Add independent data (Knight 2025, GoPrime) as a validation set, separate from Otwell.
   - Why: this is what a quality system will ask for.
7. **RNA assays: show failures through the reverse primer alone separately in the summary.**
   - Why: this is where the DNA-only basis is weakest and most consequential (P9; influenza).
8. **Clean up the bundle (list in F) and annotate the HSV-1 run page as made before the fixes.**
   - Why: the bundle is the user's working memory; stale rules mislead.
9. **Rerun HSV-1 and enterovirus on the fixed code, and rethink oligo QC for assays already in use.**
   - What: make QC information only, or calibrate its thresholds to the laboratory's mix.
   - Why: it stops design-time limits from dominating the status of established assays.
10. **Replace R8 with a flag for 2+2 pairs.**
    - Why: R8 now explains outcomes it no longer decides (P10).
