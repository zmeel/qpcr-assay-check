# Data storage and cache

The tool keeps **no local sequence database**. Everything it knows about a genome comes from NCBI
at run time. What it stores locally is small and falls into three groups: a **cache** of NCBI
answers, a **store** of the located regions, and the **evaluation records** of each run.

```
<cache_dir>/                         set with ncbi.cache_dir (default: the per-user cache folder)
├── blast/…            BLAST results                      kept 7 days
├── blast_rid/…        submitted BLAST searches (RIDs)    to resume an interrupted run
├── seqwindow/…        fetched pieces of records          kept indefinitely
├── taxonomy_name/…    organism name → taxonomy ID        kept 30 days
├── taxonomy_lineage/… taxonomy ID → lineage              kept 30 days
├── taxonomy_ancestors/…                                  kept 30 days
└── genomes/
    ├── 444-3f9c…e1.jsonl                  the region store of one locus (see below)
    ├── 444-3f9c…e1.jsonl.failures.json    genomes whose download failed, with the reason
    └── context-8a1b….json                 the flanks taken from the context accession

<results>/<assay>/<run id>/          one folder per run, never overwritten
├── report.html  results.json  results.xlsx  hits.tsv
```

## The cache of NCBI answers

Each answer is stored as a compressed JSON file named by a **SHA-256 hash of the question**
(the query, the parameters, the taxa): the same question gives the same file, and a different
question never reuses an answer by accident. Each kind has its own **lifetime**, chosen by how
fast the answer can change:

| Kind | Lifetime | Why |
|---|---|---|
| BLAST results | 7 days | the database grows every day; last year's answer must not be served this year |
| BLAST search IDs | until NCBI discards them (about 36 hours) | an interrupted run resumes the same search instead of submitting it again |
| sequence windows | indefinitely | a record `accession.version` never changes; a new version gets a new number |
| taxonomy | 30 days | names and lineages change occasionally (taxonomic renames) |

Files are written atomically (to a temporary file, then renamed), so a run that is stopped
halfway never leaves a damaged entry.

## The region store

The region store is what makes the tool **incremental**: a genome is downloaded and scanned
once, and later runs only process genomes that are new at NCBI.

It is one text file per locus, in *JSON Lines* format (one JSON object per line):

- **Line 1, the header**: the store's format version and its **key**: the reference fragments
  with their flanks, the scan settings (seed length, seed step, largest insertion or deletion,
  flank length, the threshold for the N-tolerant search, the seed length and block count of
  the fallback search), the taxon, the source (assemblies or
  Nucleotide records) and the excluded taxa. The file name contains a hash of this key.
- **Every further line: one genome.** Its accession, release date, organism, taxonomy ID,
  assembly level, number of sequences, total length, number of `N` and of assembly gaps (runs of
  10 or more `N`), the sequences recognised as plasmids, and **every candidate copy** found by
  the locator with all its evidence: anchors, anchored and flank bases, identity, signed
  coordinates, `N` inside and beside it, the molecule it lies on and the sequence of the region
  itself (the fragment with 50 bases either side). If an accession appears twice, the last line
  counts.

**Only these regions are kept, never the genomes.** A 3.4-million-base *Legionella* genome
becomes a few hundred bytes per copy of a 260-base region.

### When is a genome scanned again?

| Change | Effect |
|---|---|
| a new genome at NCBI | downloaded and scanned in the next run |
| a new version of an assembly | the latest version is used; the older one is ignored |
| a copy-rule threshold (`min_anchored_bases`, `min_context_bases`, `min_copy_identity`, `min_identity_anchored_bases`) | **no new scan**: every candidate was stored, the rule is applied again |
| a mismatch-class setting, a channel, an inclusivity limit | **no new scan**: only the assessment is repeated |
| a reference fragment, the context accession, a scan setting, the taxon or the source | a **new key**: a new file, every genome is scanned again |
| a new store format version of the tool | a new key as well |

A file whose header does not match its key (for example after editing it by hand) is set aside
as `.old` and every genome is scanned again: there is no migration code that could silently
mix two definitions. Deleting the cache is always safe; the next run rebuilds it.

### Failed downloads

A failed download batch is retried in halves down to single genomes, so one bad genome does not
fail the others. Failures are counted per genome with their reason. A genome is retried on every
run; after two failed runs it counts as *unavailable*: listed in the report, left out of the
counts, and not treated as work still to do.

## The evaluation record

Every run writes a new folder under the output directory, named by the assay and a run ID with
the date, time and the start of the inputs hash. It is never overwritten. The **inputs hash** is
a SHA-256 over the assay and the configuration that decides the result (NCBI connection
settings, report settings and the per-run genome budget are left out), so two records with the
same hash were made from the same inputs. `results.json` holds every number the report shows; the report states the tool version,
the NCBI databases and dates, and the search IDs, for traceability in a quality system.

## Privacy

What is sent to NCBI: the oligo sequences (BLAST), the reference fragment (only for Nucleotide
records longer than 200,000 bases), organism names, accessions and taxonomy IDs. No patient data
is involved. The NCBI e-mail address and API key are read from environment variables
(`NCBI_EMAIL`, `NCBI_API_KEY`) and are never written to the cache, the logs or the reports.
