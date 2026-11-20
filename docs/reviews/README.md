# Reviews

Independent reviews of the project, kept verbatim. They are reviewers' opinions, not project
decisions: this file records how they compare and what was taken up.

| File | Reviewer | Date |
|---|---|---|
| `2026-10-01-theory-review-molecular-biologist.md` | senior theoretical molecular biologist and bioinformatician | 2026-10-01 |
| `2026-10-01-theory-review-advisor.md` | methods advisor (diagnostic qPCR, quality systems) | 2026-10-01 |
| `2026-11-17-whole-project-advisor.md` | independent advisor (molecular diagnostics, scientific software), whole project | 2026-11-17 |
| `2026-11-20-report-advisor.md` | independent advisor (molecular diagnostics, quality systems, data visualisation, report design), the HTML report | 2026-11-20 |
| `2026-11-20-tiers-advisor.md` | independent advisor (molecular diagnostics, in silico qPCR evaluation, scientific software), the off-target search tiers | 2026-11-20 |

Both assessed the theoretical background of the tool at the same time, independently, from the
same documentation (SPEC, ARCHITECTURE, MISMATCH_CLASSES, the wiki pages, PROGRESS) and the code,
using the literature and GitHub. Neither saw the other's report.

## Where they agree

Both call the method sound and, in combination, without a published equivalent: exhaustive
genome-by-genome analysis, one documented outcome per genome, the chain locator, the computed
BLAST score floor, the partner scan, and the honest accounting of every genome that leaves the
denominator. Both rank the same four weaknesses highest:

1. **The probe rules are the weakest link**, although usable data exist (Kutyavin 2000 on
   MGB mismatch position, Süß 2009, Klungthong 2010 on clinical false negatives, and Otwell's own
   probe-deletion lengths).
2. **Terminal mismatch types rest on one source** (Stadhouders); Kwok 1990 and Huang 1992 should
   be weighed in.
3. **Duplex Tm** should carry more weight: the advisor wants it as a documented test against the
   annealing temperature (the FDA's first stage), the biologist wants it computed on the
   mismatched duplex and withheld for modified probes.
4. **Database redundancy** (outbreak clusters, repeat submissions) inflates the detectable
   percentage; a deduplicated figure should sit beside the raw one.

They also agree that RNA assays are graded on DNA-only evidence, and that the strict/lenient
homopolymer spread should be reported as an interval.

## Where they differ

- Only the advisor treats **section 11 of MISMATCH_CLASSES as calibration, not validation** (the
  rules were changed after seeing the Otwell outcomes), and asks for independent validation data.
- Only the advisor asks for the **collection date to become the status axis**, for a refusal to
  state a status when too many genomes are undetermined, and for specificity to reuse the graded
  classes instead of its own mismatch heuristics.
- Only the biologist points out that the classes concern **detection, not quantification**
  (Bru 2008: up to 1000-fold copy-number error from one internal mismatch), and that the
  3'-most-16-nt window is an artefact of Lefever's 20-mers.

## Taken up for v2 (the smaller, non-behavioural items)

- A flag where a site's predicted duplex Tm falls at or below the configured annealing
  temperature, next to the class, never replacing it (FDA 2023 stage 1).
- ΔTm marked as not applicable for MGB/LNA-modified oligos.
- Probe deletions graded by length from Otwell's measurements instead of always
  `indeterminate`.
- Section 11 relabelled as a calibration set, in the document and the wiki.
- A caveat that the classes concern detection, not quantification.
- The bracketing percentages (all undetermined detected versus all escapes) next to the headline
  figure, and INCOMPLETE when the undetermined share exceeds a configurable limit.

## Deferred (they change results or need new evidence; the user decides)

Position-aware MGB probe rule; a third source for terminal mismatch types; a deduplicated or
diversity-weighted inclusivity figure; collection date as the status axis; scanning every locus
of a multi-locus assay; one mismatch rule set for off-target sites plus a per-tier amplicon BLAST;
independent validation on Knight 2025 or the GoPrime templates; and the wet-lab tests both
reviewers propose.

## Checked afterwards

- The bioRxiv DOI prefix `10.64898` (Johnston et al. 2026) looked unusual but resolves; bioRxiv
  now uses it.
- The advisor's claim that only the first locus of a multi-locus assay is scanned is correct
  (`variants/exhaustive.py` warns about it). All three example assays have one locus, so no
  result so far is affected.
- Neither reviewer obtained the Stadhouders or Lefever PDFs, so whether `oligo/grade.py` matches
  their tables is still unchecked (open item 1 in MISMATCH_CLASSES).

## Checked against the papers (2026-10-02)

The user supplied Kutyavin 2000, Klungthong 2010, Kwok 1990 and Huang 1992 (Süß 2009 could not be
obtained). Two claims in the molecular-biologist review do not hold:
- **Klungthong 2010** reports reduced sensitivity, not clinical false negatives (every sample was
  detected, swH1 Ct up to 38.53), and its probe is an unmodified 30-mer with an internal
  quencher, not an MGB probe. It bears on the unmodified-probe rule, which it is consistent with.
- **Terminal G3 (C-A, A-C, G-T, T-G)**: Kwok 1990 amplified all four as well as a perfect match
  (Table III), so it does not contradict Stadhouders; only Huang 1992's single-step kinetics do,
  and Huang notes the difference from Kwok's PCR himself. G3 stays `tolerated`.

Taken up (user decisions 2026-10-02, MISMATCH_CLASSES R1 and R9): terminal G2 (T-T, T-C, C-T)
`at_risk` instead of `likely_failure`; one mismatch in the 3'-most 7 nt of an MGB probe
`likely_failure` (Kutyavin 2000), further toward the 5' end still undetermined.

Taken up on 2026-10-03 (user: "Start with 8, 6 and 9"): the report states what the specificity
search cannot find (word size 7 and the E-value against Primer-BLAST's default, Ye et al. 2012),
an RNA note for one-step RT-PCR assays (Christopherson et al. 1997, abstract checked in PubMed),
and the status figure under the other homopolymer setting. Both sources were checked against
their text (Ye 2012 full text in Europe PMC, PMC3412702).

## Whole-project evaluation (2026-11-17)

The advisor's ten problems were checked against the code before acting. Taken up the same day
(user: "fix 1, 2, 4, 5"):

- **P1** every record names its code: a fingerprint of the installed package and the git commit.
- **P2** a configured off-target tier that was not searched, or an organism name that did not
  resolve, no longer reads as No flags. The other part of the advisor's priority 2 (a cap on the
  share of unavailable records; complete genomes without the region in the main status, P6) was
  not taken up.
- **P4** R6 over a primer's 3'-most 16 nt and the whole probe.
- **P5** MGB recognised from the dye names; LNA probes graded as unmodified, and said so.

The rest was taken up the same day (user: "fix the remaining issues"): P3 (off-target sites graded
by R1-R9 together with the levels), P6 (possible deletions in the status, a cap on unavailable
records), P7 (core_nt in the limitations), P8 (the window ends at the run's year), P9 (RNA:
failures through the reverse primer alone), P10 (2 + 2 pairs flagged, class unchanged), and the
stale statements under F.

Not done, as they are not code defects: a laboratory verification pack (priority 6), oligo QC as
information only for assays in use (priority 9), a count of searches per 24 h across runs, the
LICENSE / CLAUDE.md question, and the release (tag) before records are filed: the user's.


## Review of the search tiers (2026-11-20)

Nine findings (F1-F9) and eight corrections to the knowledge bundle's search-tiers page. Checked
against the code the same day: F1 (a tier left out of `specificity.off_target_tiers` is still
searched, not assessed, and its summary row reads No flags), F2 (near-neighbour and exclusivity
taxa are not checked against the target's lineage; *Homo sapiens* is both in the packaged starter
list and the background tier), F3 (partner windows and probe re-alignment share one fetch budget,
partner windows first; a tier cut at `max_amplicons` is not partner-scanned), F5 (the taxon
restriction check and the exclusivity table compare exact IDs) and F7 (a missing tier or an
unresolved name gives Incomplete only when the run or tier would otherwise read No flags) hold as
described. The search-tiers page was corrected.

Taken up the same day (user: "Fix all. You can decide the order yourself"), in the order F1, F7,
F2, F6, F5, F3 with F8, F4, F9: every searched tier assessed and tier waivers with a reason (F1);
missing tiers and unresolved names Incomplete above Review (F7); tier taxa checked against the
target's lineage and each other, a taxon in two tiers searched once (F2); balanced searches and
the floor per search (F6); lineage in the exclusivity table and the restriction check (F5); a
probe budget of its own and a "not detected (bounded)" computed in code (F3); near neighbours
read cautiously, at risk and gapped sites acting at warning level (F8); a bounded cut at
`max_amplicons` and distinct product patterns (F4); the eukaryote note by lineage (F9). The
cautious rule was narrowed to warning level after a test showed a minor site of random sequence
(a run of N) graded at risk.

Not built: the exhaustive analysis of a near neighbour's own records (F4, the advisor's "stronger
answer", a feature of its own), specimen panels and taxonomy-derived near-neighbour suggestions
(F9, judgement; the NCBI Taxonomy query would need checking first). The 2759 = Eukaryota default
was confirmed by the user on 2026-11-20.

## Review of the HTML report (2026-11-20)

Diagnosis (24-31 A4 pages printed, about 60% prose, more than half of it the same in every
report, one chart, inside a closed section), six visual proposals (P1 page-1 status table with
small figures, P2 detection per year as stacked bars, P3 oligo-site mismatch maps, P4 tier
overview with a closest-site glyph, P5 score-floor matrix, P6 a compressed organism table), a
two-page sign-off part, prose cuts and implementation notes. Checked the same day: closed
`<details>` sections are left out of the printed PDF (reproduced with a minimal page in
Chromium: the print rule `details:not([open]) > *:not(summary)` has no effect), so the printed
HSV-1 record lacked the oligo QC tables behind its one Exceeds-limit row; the page-1 line counts
an Exceeds-limit row as "flagged for review". Nothing taken up yet: the user decides, and P3 needs
the user's word on the decision of 2026-10-03 (no variant graph).
