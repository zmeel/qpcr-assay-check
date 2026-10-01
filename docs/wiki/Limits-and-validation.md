# Limits and validation

## What the tool does not tell you

- **No Ct values, no analytical sensitivity.** The mismatch classes present published
  primer-mismatch data (Stadhouders et al. 2010; Lefever et al. 2013). The size of a mismatch
  effect depends on the master mix, the polymerase and, for RNA targets, the reverse
  transcription step; the classes use one basis (Taq polymerase on DNA) for every laboratory.
- **Probes have no published quantitative basis.** The probe classes are expert judgement and are
  labelled as such; a single mismatch in an MGB probe is *undetermined*.
- **Public data are not a random sample of what circulates.** NCBI holds what was sequenced and
  submitted: outbreak studies, reference collections, surveillance programmes. A lineage that is
  over-sequenced weighs heavily; one that is never sequenced is invisible. Percentages are exact
  counts over the public genomes, not estimates of prevalence.
- **Draft assemblies hide repeats.** Short-read assemblies often leave near-identical repeat
  copies (rRNA operons, opa genes) unassembled, collapsed or cut at contig ends. The tool reports
  these genomes separately (*cut by a contig end*, *detectable from parts*, *possibly
  unassembled*) instead of counting them as escapes, which can also hide a real loss of copies;
  the lists are in the workbook. Cut genomes count as undetermined, so many of them can make a
  result INCOMPLETE; genomes detectable from parts count as detected by default.
- **Sequencing errors look like variants.** Homopolymer length differences in particular are a
  known error of some sequencing platforms; the report shows where the copies of one genome
  disagree and how the variants spread over assembly levels.
- **Genome assemblies only, for the `datasets` source.** Sequences submitted without an assembly
  (single genes, amplicons) are not part of NCBI Datasets' genome collection. The Nucleotide source
  covers them, but for large taxa only the newest records per run.
- **Multiplex assays with several regions**: the assay model, the specificity search and the oligo
  QC cover every region; the genome scan currently covers only the first region (locus) of the
  assay, and the run log warns when there are more.
- **Specificity covers only what was searched**: the tiers, taxa and database of the run.
  Organisms outside them are not evaluated.

> In silico analysis does not replace experimental validation. The laboratory must verify the
> software within its own quality system before relying on its output.

## What was measured to set the rules

The locator and the copy rule were measured on real genomes before the defaults were chosen
(September 2026):

| Measurement | Result | Consequence |
|---|---|---|
| chains built from shuffled reference sequences (decoys) | at most **18** anchored bases | a copy needs **32** (rule a) |
| 134 *Legionella* genomes (species chosen to include divergent and cut copies) | 191 of 283 copies differ in length from the reference by more than 20 bases | chains allow up to 150 bases of insertion or deletion |
| same genomes, oligo placement | the former single-offset placement judged 518 of 1,132 sites at a worse position | each oligo is placed through its nearest exact block |
| *Legionella* borderline candidates | look-alike regions: identity 0.60–0.66, **0** flank bases; real divergent copies: identity 0.66–0.73, **40–792** flank bases | rule (b): 32 flank bases; identity alone cannot separate them |
| *N. gonorrhoeae* divergent opa copies | identity 0.79–0.80 with 16–23 anchored bases | rule (c): identity ≥ 0.75 with ≥ 16 anchored bases |
| seed step on *N. gonorrhoeae* | step 2 found what step 1 found; step 4 missed divergent copies | seeds every 2 bases |

Full-scale runs with these rules (September 2026): *N. gonorrhoeae*, 20,000 of 51,583 assemblies
in one run; *Legionellaceae*, all 11,911 assemblies in one run of about 10.5 hours on a small
NAS. With the new locator, the *L. longbeachae* complete genomes that the earlier locator reported
as likely failures are detectable with perfect genus-probe sites, most likely because the earlier
single-offset placement judged their sites at the wrong position.

## NCBI behaviour relied on

Facts about NCBI's services that the tool depends on were checked live, and are listed with the
date in `docs/ARCHITECTURE.md`. Among them: the BLAST URL API accepts the short-oligo parameters
and returns JSON; `ENTREZ_QUERY` restricts by taxon but not airtight (hits are filtered again
locally); a date filter combined with a taxon restriction in one BLAST search is **not**
reliable (so the tool does not use one); NCBI Datasets pages its listings and returns a sequence
report that tells chromosomes from plasmids; ESummary is keyed by NCBI's own record ID, not by
the accession sent.

The tool follows NCBI's usage rules: it identifies itself with a tool name and e-mail address,
throttles its requests (faster with an API key), backs off on errors, polls BLAST searches
politely and warns when a run would submit many searches outside NCBI's quiet hours.

## Tests

The code is tested with `pytest` on synthetic genomes and recorded NCBI responses (no network in
the tests), and checked with `ruff`. Live checks against NCBI are run separately
(`scripts/smoke_test.py`) and their results recorded.
