# Reviews

Independent reviews of the project, kept verbatim. They are reviewers' opinions, not project
decisions: this file records how they compare and what was taken up.

| File | Reviewer | Date |
|---|---|---|
| `2026-10-01-theory-review-molecular-biologist.md` | senior theoretical molecular biologist and bioinformatician | 2026-10-01 |
| `2026-10-01-theory-review-advisor.md` | methods advisor (diagnostic qPCR, quality systems) | 2026-10-01 |

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
