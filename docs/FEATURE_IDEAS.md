# Feature ideas after v1.1.1

Proposals for making qpcr-assay-check more useful in a clinical laboratory, written 2026-09-23
after v1.1.1. **None of these is planned or started**: each needs the user's go-ahead (see
`CLAUDE.md`, "Do not start the next phase without my go-ahead"). Items marked *verify first*
rest on NCBI behaviour or published data that must be checked before building on it; nothing
here is a verified fact about NCBI or about PCR chemistry yet.

Recommended order: 8 is done (v1.3.0), 1 is done (unreleased); next 4, then 2 and 3 after
their checks.

| # | Idea | Value | New NCBI traffic | Verify first |
|---|---|---|---|---|
| 1 | Panel-level escape detection | High | None | No |
| 2 | Collection date and country | High | Metadata only | Yes |
| 3 | Mismatch impact score | High | None | Yes (literature) |
| 4 | Scheduled runs with alerts | High | As today | No |
| 5 | Multi-assay overview | Medium | As today | No |
| 6 | Variant templates for wet-lab checks | Medium | None | No |
| 7 | Degenerate-base suggestion | Medium | None | No |
| 8 | Several oligos per role, named oligos, multi-copy targets | High | None | No |

## 1. Panel-level escape detection (multi-target assays) (done, `qpcr-assay-check panel`)

Many assays detect one organism with two targets, e.g. *C. trachomatis* on the cryptic plasmid
plus a chromosomal gene. The clinical risk is a strain that escapes **every** target at once;
the Swedish new-variant *C. trachomatis* (nvCT) was a problem because its plasmid deletion hit
the only target of the affected assays.

- Input: a panel file listing two or more assay files for the same target taxon.
- Per genome, combine the stored regions of each assay (the region store already holds them,
  keyed by accession) and classify: all targets fine / one target affected / **all targets
  affected** (not found, 3′-end mismatch or 2+ mismatches).
- Report the "all targets affected" genomes prominently, with accessions, per year.
- Only genomes processed by every assay are combined; the report states how many.
- No new NCBI requests: it reuses the per-assay stores.

## 2. Group by collection date and country (*verify first*)

Tables are now grouped by NCBI release year, which can lag the sample by years. BioSample
metadata usually carries a collection date and geographic location.

- Would allow "variants rising in Europe over the last two years", a stronger early-warning
  signal than release year.
- **Verify first:** which fields NCBI Datasets genome reports and E-utilities return for this
  (and their exact names), how often they are filled in for the targets we use, and the formats
  seen live (full dates, year only, "missing"). Records without a date or country must be shown
  as such, never guessed.

## 3. Mismatch impact score (*verify first*)

We report duplex Tm loss and the clean 3′ end. Published work shows that position and type of
mismatch matter: some terminal 3′ mismatches are tolerated, others block extension, and MGB/LNA
probes tolerate mismatches differently from plain probes.

- Add a per-variant "predicted impact: low / moderate / high" with the rule and its source.
- **Verify first:** build only on rules taken from specific cited publications; no thresholds
  of our own invention. The report keeps stating that in silico analysis does not replace
  experimental validation.

## 4. Scheduled runs with alerts

- A documented schedule (cron or Synology Task Scheduler) running each assay monthly.
- A notification (email; address and SMTP settings only from environment variables, never
  committed) only when the history diff finds something new and concerning: a new variant with
  a 3′-end mismatch or 2+ mismatches, a verdict change, or an inclusivity drop.
- A yearly per-assay summary built from the stored run history, as evidence of ongoing
  performance monitoring for the laboratory's quality system (ISO 15189 / IVDR post-market
  follow-up); wording to be agreed with the user.
- Keeps NCBI etiquette: the existing throttling, and large runs outside US peak hours.

## 5. Multi-assay overview

- One command runs every assay file in a folder (sequentially, sharing the cache).
- One overview page: assay, verdict, share of genomes/records assessed, new concerns since the
  previous run, link to each full report.

## 6. Variant templates for wet-lab checks

- For each concerning variant, export the variant amplicon with flanks (FASTA and a table),
  taken directly from the NCBI record it was found in (accession and coordinates included),
  ready to order as a synthetic template to test whether the assay still detects it.
- Sequences come only from NCBI records; nothing is constructed or edited.

## 7. Degenerate-base suggestion

- When a variant reaches a configurable share of genomes (e.g. 5%), show the IUPAC base that
  would cover it at that position, with the resulting Tm range.
- Labelled as a computed suggestion for the laboratory to evaluate, not a validated redesign;
  the assay definition is never changed by the tool.

## 8. Several oligos per role, named oligos, multi-copy targets (v1.3.0; done)

Some assays use more than one forward primer, reverse primer or probe for the same target, when
the differences between lineages are too big for a wobble base. Confirmed by the user
(2026-09-24): such oligos are always in the same reaction mix; probes with the same dye are
alternatives for mismatches, probes with different dyes detect different regions of the fragment.
Worked example: [examples/neisseria_gonorrhoeae_two_probes.yaml](examples/neisseria_gonorrhoeae_two_probes.yaml).

- **Assay file:** each role takes a plain sequence (as now; name defaults to the role), one named
  oligo, or a list of named oligos; probes may carry their own reporter and modifications. Names
  must be unique and are used in the report, workbook, `hits.tsv`, history and BLAST labels.
- **Alternatives:** per genome and role every oligo is assessed and the best-binding one counts
  (fewest mismatches/gaps, then clean 3' end, then highest duplex Tm). New per-oligo coverage
  table: covered by this oligo / only by this oligo / by none (escape list). An oligo that covers
  no assessed genome is an informational finding.
- **Probe channels:** probes are grouped by reporter. Same reporter: alternatives. Different
  reporters: separate channels, with coverage per channel plus "any channel" and "all channels";
  which one decides a positive is a setting (default: any channel).
- **Multi-copy targets:** the example target has several differing copies per genome (6-7
  forward primer sites in each of three genomes checked). A genome counts as detected when any
  copy gives a complete product bound by the primers and a probe; the copy is chosen by how well
  the assay binds, not by seed support as now, and the report shows copies per genome.
- **Several reference amplicons, one per lineage** (the example has one fragment per probe): the
  region search uses seeds from all of them, each genome's region is read against the reference
  it matches best, and the region store is keyed by the whole reference set. An oligo that fits
  no reference exactly is aligned over the window where its role binds.
- **QC and specificity:** Tm, hairpin and length per oligo; dimers across every pair in the mix;
  each oligo searched under its own name; off-target products from every forward/reverse pair.
- **Plan:** step 1 = assay format, names, QC and specificity; step 2 = best oligo per genome over
  all copies, coverage per oligo and channel, escape lists in the variant analysis.

## Advisor review (2026-09-25): proposals, not started

From the advisor subagent (senior molecular biologist, big-data analysis) after the NG and
enterovirus runs. Items marked *verify first* need the cited papers' full tables or NCBI field
checks before any rule is built; no thresholds of our own invention.

| # | Idea | Why | Verify first |
|---|---|---|---|
| 9 | Graded, role-specific mismatch classes (perfect / tolerated likely / at risk / likely failure / indeterminate); MGB probes stricter; primer-pair combinations; IUPAC codes in the genome shown as uncertain | The binary rule is too strict for primers and too lenient for MGB probes | Yes: Stadhouders 2010, Lefever 2013, Kwok 1990 full tables |
| 10 | Collapse identical amplicon-region haplotypes; study provenance (BioProject) per escape cluster; report per type/lineage | Single studies dominate raw counts (e.g. 262 Poliovirus 2 records of one series) | Yes: Datasets/ESummary fields |
| 11 | Stratify by assembly level and sequencing technology; check homopolymer variants in complete/long-read genomes | Homopolymer length is a sequencing-error hotspot | Yes: field availability |
| 12 | Copy-aware reporting: detectable copies per genome | Near the LoD fewer detectable copies matter | No |
| 13 | Panel: interpretation rule (either target positive vs both); 'region not found' informative in complete genomes only; one homopolymer rule per panel | Clinical meaning of "detected by some targets" depends on the lab's algorithm | No |

Idea 6 (variant templates for wet-lab checks) was ranked high by the advisor as the link to
experimental validation.

**#9, source checked (2026-09-25, full text supplied by the user, read by the advisor):**
Stadhouders R, Pas SD, Anber J, Voermans J, Mes THM, Schutten M. J Mol Diagn 2010;12(1):109-117,
doi:10.2353/jmoldx.2010.090035. Single template mismatches at primer positions 1, 2, 3 and 5
from the 3' end (not 4, not beyond 5), named primer-template; two TaqMan assays; three setups
(Taq on DNA; Taq + MMLV one-step RT-PCR; rTth one-step RT-PCR); delta Ct at one input, n = 4.
Its Table 1 groups mismatch classes (A-A/A-G/G-A/G-G/C-C; T-T/T-C/C-T; C-A/A-C/G-T/T-G) by
position (terminal / penultimate / 3-5) and setup into "acceptable" (< 2 Ct) or "avoid", and the
setups differ strongly (e.g. reverse-primer mismatches mattered little with Taq + MMLV but much
with rTth). Multiple mismatches in the last 3 nt: no amplification with Taq-based setups.
Usable for: a class x position x setup lookup for the last 5 nt, with the setup as a lab setting
(worst case when unknown). Not covered: position 4 (extrapolated by the authors), beyond 5,
probe/MGB mismatches, indels/bulges, spread or two-primer mismatches, degenerate primers, modern
mixes, efficiency/LoD. Those need Lefever 2013 (positions > 5, counts), Kutyavin 2000 (MGB);
no source yet for bulges. The PDF is not stored in the repository (copyright).

## Related tools (context, 2026-09-23)

A short web search (not a full literature review; maintenance status not checked) found no
public tool combining automatic NCBI collection for any organism, run-to-run variant history,
exclusivity and per-mismatch thermodynamics. Closest in purpose:

- **SCREENED** (Sciensano, Galaxy): inclusivity/exclusivity from user-supplied genomes, 10%
  mismatch rule, built for SARS-CoV-2.
  [IJMS 2020](https://www.mdpi.com/1422-0067/21/15/5585),
  [Genes 2021](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8069896/)
- **Simple Oligo Matching Tool** (Python, SARS-CoV-2).
  [Genes & Genomics 2025](https://link.springer.com/article/10.1007/s13258-025-01663-6)
- **GISAID PrimerChecker / CoVsurver, Nextclade, assayM**: SARS-CoV-2 only.
  [assayM](https://www.biorxiv.org/content/10.1101/2020.12.18.423467.full.pdf),
  [review](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9414863/)
- **virtualPCR**: general in silico PCR against genomes you supply.
  [GitHub](https://github.com/rkalendar/virtualPCR)
- **Primer-BLAST** (NCBI): no API; listed in our reports as an optional manual cross-check.

SCREENED's published SARS-CoV-2 results could serve as an external comparison for our N1
numbers.
