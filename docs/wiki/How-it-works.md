# How it works

A run takes an **assay file** (the oligos, the target, the regions and channels) and an optional
**configuration file** (reaction conditions, limits, search settings) and produces one
evaluation record. All sequence searching happens remotely at NCBI: there is no local BLAST
database to install or keep up to date.

```
 assay.yaml ─┐
 config.yaml ┴─► 1 Validate ─► 2 Oligo QC ────────────────────────────────────────┐
                    │                                                              │
                    ├─► 3 Resolve organism names to NCBI taxonomy IDs              │
                    │                                                              │
                    ├─► 4 Specificity: tiered remote BLAST of every oligo          │
                    │      └─ re-align every relevant hit, pair primer sites,      │
                    │         predict off-target products                          │
                    │                                                              │
                    └─► 5 Variant analysis: every genome of the target             │
                           ├─ list genomes (NCBI Datasets or Nucleotide)            │
                           ├─ download new ones, locate the assay region,           │
                           │  store only that region (incremental store)            │
                           ├─ align every oligo to every copy, grade each site      │
                           └─ judge each genome and each channel                    │
                                                                                   ▼
                                   6 Review status per section ─► 7 Report, JSON, Excel
```

## 1. Validate the assay

The assay file is checked before anything is sent anywhere: only IUPAC nucleotide codes, unique
oligo names, every primer and probe in exactly one region, one reporter dye per channel, a
reference fragment per region. `qpcr-assay-check validate` runs this step alone.

A **locus** is one amplified region: its primers, its probes, one or more *reference fragments*
(the sequence between and including both primers, as the laboratory expects it) and optionally a
*context accession*, a complete genome from which the sequence either side of the fragment is
taken (see [Finding the target in a genome](Finding-the-target-in-a-genome)).

A **channel** is one fluorescence readout: its probes (all with the same reporter dye) and the
taxon it is meant to detect. Old assay files without these sections are read as one locus with
all oligos and one channel per reporter dye.

## 2. Oligo quality control

Every primer and probe, and every pair, is checked with thermodynamic nearest-neighbour models
(primer3-py; SantaLucia parameters) at the reaction's salt, magnesium, dNTP and oligo
concentrations and annealing temperature: melting temperature, GC content, GC in the last
five bases, the longest single-base run, hairpins, self- and cross-dimers, the Tm difference of
the primers and between probe and primers, and the amplicon length. Each value is compared
with a preferred range (review) and a limit (exceeds limit). For an oligo with a declared
modification (a minor groove binder (MGB), locked or peptide nucleic acids, ZEN and the like)
the report warns that these models do not cover it and that vendor Tm values should be used.

## 3. Resolve organism names

The clinical organism list (a starter list per syndrome, to be reviewed by each laboratory, or
the assay's own `exclusivity_organisms`) is resolved to NCBI taxonomy IDs through E-utilities.
Exactly one match is a resolution; several matches are *ambiguous* and none is *unresolved*.
Neither is ever guessed: unresolved names are listed and left out of the search.

## 4. Specificity

Every oligo is searched with remote BLAST (blastn, core_nt) restricted by taxon in tiers: the
target itself, the near neighbours that must not be detected, taxa that are out of scope
(information only), the clinical organism list and the human background. Hits are re-aligned
over the full oligo length, primer sites that face each other are paired into predicted
products, and the probe decides whether a product would give signal. Details:
[Specificity search](Specificity-search).

## 5. Variant analysis (inclusivity)

This is the core of the tool and the part that uses every genome:

1. **List** every genome of the target: every current genome assembly in NCBI Datasets
   (bacteria), or every Nucleotide record, optionally narrowed by length (viruses). Newest
   release year first.
2. **Download and scan** the genomes not yet in the store, in batches. Each genome is searched
   for every copy of the assay region; only those regions, with their evidence, are kept. See
   [Finding the target in a genome](Finding-the-target-in-a-genome).
3. **Assess** every stored copy: each oligo is aligned end to end to its site and the site is
   given a graded mismatch class. A genome is judged by its best copy, because the PCR needs
   only one copy it can amplify. See [Judging primer and probe sites](Judging-primer-and-probe-sites).
4. **Count** per release year and per channel: detectable, at risk, likely failure,
   undetermined, and the genomes in which the region is missing, cut by a contig end or hidden
   by unknown bases (N).

A run processes at most a set number of new genomes (20,000 assemblies or 2,000 Nucleotide
records by default); the next run continues where it stopped, and the report says how far it
got.

## 6. Review status

Each section gets a status: **No flags**, **Review** (a review limit you configured was crossed),
**Exceeds limit** (a hard limit was crossed) or **Incomplete** (evidence is missing). The tool
does not pass or fail an assay: the reviewer decides, and the report ends with a box for that
decision. The inclusivity status uses the whole fragment (forward, probe and reverse together)
over the last three complete release years plus the current one: below 95% detectable is
Review, below 80% Exceeds limit (both configurable), and fewer than 100 genomes in that window
is Incomplete. Each channel is judged the same way on its own target, and the inclusivity status
is the worst of the whole-fragment and channel statuses.

## 7. Outputs

Each run writes a new folder `results/<assay>/<run id>/` that is never overwritten:

| File | Content |
|---|---|
| `report.html` | The self-contained report (no scripts, no external requests), for review and archiving |
| `results.json` | Every number and site in machine-readable form |
| `results.xlsx` | Every row the report condenses: sites, variants, products, genomes per outcome |
| `hits.tsv` | Every assessed off-target site |
