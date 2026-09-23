# Architecture

Status: v0.3.0 implements steps 1, 2, 5, 6 (from v0.2.0) plus 7 and 8: full-length re-alignment of
every relevant hit and amplicon pairing, feeding a real specificity verdict. v0.4.0 (tagged
2026-09-22) adds steps 3, part of 4, and 9: organism names are resolved to taxonomy IDs (never
guessed) and searched as a real "exclusivity" tier reusing the same specificity machinery as the
other off-target tiers, with its own per-organism table and a species/genus/family rollup of every
off-target hit (step 6's aggregation, generalised beyond exclusivity alone; phase 4a); and
inclusivity (phase 4b): the target tier's own hits (already searched for every run) are bucketed
into years afterwards via ESummary, sampled, and re-aligned over the full oligo length, giving a
year-by-year trend rather than the BLAST+`[PDAT]` design SPEC.md step 7 originally proposed (ruled
out live; see "Design decisions" below). Both phase 4a's and 4b's remaining live-verification items
have now been checked (see "Verified" sections below). v1.0.0 (implemented, not yet tagged) adds
step 11: every run diffs itself against the most recent previous run for the same assay (found from
the existing `results/<slug>/<run_id>/` layout, no separate index), reusing the design already
sketched below ("History as files"). A Dockerfile is also new, built and run successfully by the
user (see "Verified for v1.0.0" below); the history/diff feature itself has not been checked
against a real multi-year dataset yet (see "Still unverified" below). An unreleased addition on
top of v1.0.0: a variant-summary report (`specificity/variants.py`) lumps the target tier's own
hits into unique sequence variants, per oligo and per whole fragment -- requested after comparing
this project against a lab's own pre-existing manual spreadsheet workflow, which had exactly this
report and nothing else this project didn't already improve on.

## Data flow

```
 assay.yaml ─┐
 config.yaml ─┼─► 1 Load & validate ──► 2 Oligo QC (primer3-py) ─────────────┐
 organisms.yaml ┘        │                                                    │
                         ▼                                                    │
            3 Resolve organism names → taxids (Entrez Taxonomy, cached)       │
                         ▼                                                    │
            4 Search planner: target │ near-neighbours │ organism list        │
                         │ (per category) │ human; + inclusivity windows      │
                         ▼                                                    │
  ┌──────────── 5 NCBI client layer ─────────────┐                            │
  │ throttle · backoff · job store (RIDs) · cache│                            │
  │  ├─ BLAST URL API (own requests client)      │                            │
  │  └─ E-utilities (esearch, efetch, taxonomy)  │                            │
  └───────────────────┬──────────────────────────┘                            │
                      ▼                                                       │
            6 Parse + saturation check                                        │
                      ▼                                                       │
            7 Fetch subject windows → semi-global re-alignment → Tm/dG        │
                      ▼                                                       │
   8 Amplicon pairing   9 Inclusivity   10 Exclusivity table                  │
                      └───────────────┬───────────────────────────────────────┘
                                      ▼
            11 Diff against the previous run (results/<slug>/*, by generated_at)
                                      ▼
            12 Verdict engine
                                      ▼
            13 Outputs: HTML · results.json · hits.tsv · xlsx
```

## Roadmap

| Version | Content |
|---|---|
| 0.1.0 | Skeleton, input parsing, oligo QC, report skeleton |
| 0.2.0 | Remote BLAST backend: batching, cache, resumable jobs, parser, smoke test |
| 0.3.0 | Full-length re-alignment, mismatch Tm/ΔG, amplicon pairing, specificity verdicts |
| 0.4.0 | Taxonomy resolution, organism list, exclusivity (phase 4a); inclusivity via target-tier reuse + ESummary date-bucketing (phase 4b) |
| **1.0.0** | Run history + yearly diff, Docker (implemented, not yet tagged); complete report/documentation polish (open) |

## Design decisions

- **Own `requests` client for BLAST, not `qblast`**: `qblast` blocks until results arrive, so a RID
  cannot be persisted and resumed.
- **Cache scoped by validity**: BLAST results only within a run/resume (short TTL), sequence
  windows by accession.version long-term, taxonomy with a moderate TTL. A naive content-hash cache
  would serve last year's results against this year's database.
- **Saturation is judged by relevance**: a full hit list only matters if its weakest hit is still
  biologically relevant; then the search is split further.
- **Inclusivity with honest denominators**: each year's `population_size` comes from an independent
  ESearch count, reported next to `sample_size` (never presented as the full population). The
  sample itself comes from whatever the target-tier BLAST search already returned for that year,
  not a dedicated per-year search (see the redesign note below), so it is not a controlled random
  sample and `limitations` says so explicitly on every result.
- **Missing evidence is never a PASS** (verdict INCOMPLETE).
- **History as files, no separate index** (v1.0.0, `history/store.py`): the previous run is found
  by scanning `results/<assay.slug>/*/results.json` (a directory every version already writes) and
  reading each record's own `generated_at` field; the most recent one is "the previous run". No
  database, no index file to keep in sync or go stale relative to the actual files on disk.
- **Sites and amplicons are matched across runs by a natural key, not by their run-local ID**
  (v1.0.0, `history/diff.py`): `(tier, role, accession, orientation, subject_start, subject_end)`
  for a site, `(tier, accession, start, end, roles)` for an amplicon. A site's run-local `id`
  (`S1`, `S2`, ...) is only stable within one run's output, so matching by it would make every site
  look "new" on every run.
- **The "history" section is required, and a first run is honestly INCOMPLETE** (v1.0.0): like
  every other section, missing evidence is never a PASS -- a first run for an assay has nothing to
  diff against, so it cannot be a full pass yet, only from the second run onward. Confirmed with the
  user before implementing, since it means a brand-new assay's very first run can never reach
  overall PASS by itself.
- **"History" only flags that something changed (WARN), never FAILs by itself** (v1.0.0): a
  regression bad enough to fail the run already fails the specific section it belongs to
  (specificity/exclusivity/inclusivity); duplicating that into history's own verdict would just be
  noise. History compares each *other* section's already-known verdict (computed earlier in the
  same `evaluate()` call) rather than the run's own combined overall verdict, deliberately: the
  overall verdict is combined from every section including history itself, so comparing against it
  would be circular.
- **Three site sources, most to least certain** (`specificity/sites.py`): `blast_full` when BLAST's
  own alignment already spans the whole oligo (nothing to fetch); `realigned` when a partial hit's
  subject window was fetched and the whole oligo re-aligned semi-globally; `blast_partial_worst_case`
  for a partial hit that was *not* re-aligned, either because it provably cannot reach a reportable
  level or because the fetch failed — its unaligned bases are assumed to match as well as BLAST's own
  scoring allows, the risk-conservative assumption for a diagnostic assay.
- **Pruning without fetching every hit**: BLAST reports a locally maximal alignment (extending it
  over a matching base would have raised the score). Two derived, paper-only bounds decide whether a
  partial hit can be skipped without an `efetch` call: a lower bound on its full-length mismatch count
  from the unaligned base counts, and a cap on clean 3' nucleotides from the fact that the first
  unaligned base must itself be a mismatch. `scripts/validate_assessment.py` checks both bounds
  against real hits before they are trusted (see "Still unverified" below).
- **A target tier without a perfect full-length hit is a WARN**, not silence: it is the assay's own
  positive control, so its absence is itself informative.
- **Saturation, site-cap truncation and failed fetches are never silently dropped**: they make the
  specificity verdict INCOMPLETE rather than a false PASS.
- **Exclusivity reuses the specificity tier machinery, not a parallel implementation** (phase 4a):
  once the organism list is resolved to taxonomy IDs, "exclusivity" is planned, searched and
  assessed exactly like `near_neighbours`/`background` (it is simply added to
  `specificity.off_target_tiers`). `taxonomy/exclusivity.py` only adds SPEC.md step 8's own view
  over that same evidence: one row per organism-list entry (including zero-hit organisms and names
  that did not resolve), plus its own tier-scoped verdict, rather than a second assessment.
- **Name resolution never guesses** (`taxonomy/resolve.py`): `[Scientific Name]` first, then (if
  configured) `[All Names]` for synonyms; exactly one UID is a resolution, more than one is flagged
  ambiguous, none is unresolved — never picked at random. A tier built from zero resolved names is
  simply not searched, and the run reports why rather than silently passing.
- **A tier that was never searched is INCOMPLETE, not a silent PASS**: if every organism-list name
  fails to resolve, the exclusivity section still renders, explains why, and does not count as
  evidence of exclusivity.
- **The assay's own target taxid is excluded from the exclusivity search** (found live, v1.0.0):
  the packaged organism list can legitimately include the assay's own target organism (e.g. a
  respiratory panel lists SARS-CoV-2 alongside the other pathogens a SARS-CoV-2 assay is checked
  against). Searching it under "exclusivity" would only ever find the assay's own perfect,
  intended match -- not evidence of cross-reactivity -- so `search/execute.py` filters
  `assay.target.taxid` out of the resolved taxids before they reach the exclusivity search. The
  organism-list row is still shown (never silently dropped), flagged via
  `ExclusivityRow.is_target`, with no site/amplicon evidence populated for it even defensively.
- **Exclusivity rows group hits by species when known, not only by exact taxid** (fixed live,
  2026-09-23, `taxonomy/exclusivity.py`): a BLAST hit's own `taxid` is whatever specific NCBI
  Taxonomy record the matched sequence is filed under, which can be a strain-level descendant of
  the (typically species-level) taxid an organism-list name resolves to. `build_exclusivity` now
  accepts `taxon_species` (taxid -> species name, from `taxonomy.resolve.fetch_lineages`, covering
  both the hit taxids and the organism list's own resolved taxids -- `cli.py` fetches this once,
  reusing the same lineage data the taxonomy breakdown already needs, so no new NCBI calls) and
  groups by species name when both a hit's and a row's taxid are in that map; a taxid missing from
  the map still falls back to exact-taxid matching exactly as before, so this never invents a
  match it didn't actually look up.
- **The exclusivity list can be per-assay, and defaults to preferring that over the global one**
  (unreleased, `Assay.exclusivity_organisms`, `organisms.source`): a single global panel applied
  to every assay doesn't reflect that different assays have different real near neighbours (an STI
  assay and a respiratory assay share almost none). `taxonomy/organisms.organism_list_source(cfg,
  assay)` is the single place that decides: `"assay"` only when `organisms.source` is `"assay"`
  (the packaged default) *and* the assay's own `exclusivity_organisms` is non-empty; `"global"`
  otherwise -- deliberately including the default-config case where an assay simply hasn't been
  given its own list yet, so every existing assay keeps its current (global-list) behaviour
  unchanged until it opts in, rather than this being a breaking change. `organisms.source:
  "global"` overrides an assay's own list entirely, for a lab that wants one shared panel
  regardless of what individual assay files contain. The resolved source is carried onto
  `OrganismListResolution`/`ExclusivityResult` and stated in the report, never left for the reader
  to infer from which fields happen to be populated.
- **The variant summary carries no verdict of its own** (unreleased, `specificity/variants.py`):
  like `taxonomy/rollup.py`, it needs no new `SectionResult` and does not affect `combine()`. It
  renders `SiteResult.q_aln`/`s_aln` through the existing `aln_html` filter.
- **Target-tier sites are built separately, for the variant summary only**
  (`assess_target_sites`): `assess_specificity` only builds sites for `off_target_tiers`, so the
  first version of the variant summary, which filtered `specificity.sites` for `tier ==
  "target"`, was always empty on a real run (found in the first live report, 2026-09-23; its unit
  tests had constructed target sites by hand). Every target-tier HSP with at least
  `min_identical_bases` identical bases is assessed; partial hits are always fetched and re-aligned
  (inclusivity's `assess_candidates`, no `can_reach_warning` pruning, since a variant table needs
  observed bases). The closest site per record and oligo is kept. These sites are passed to
  `evaluate()` separately and never enter the off-target counts, verdict, hits.tsv or
  results.json; only the lumped `VariantSummary` is stored. Cost: one cached `efetch` per partial
  target hit, at most `hitlist_size` per oligo.
  **Measured live (CDC N1, 2026-09-23):** 5000 / 5000 / 5002 target sites for forward /
  reverse / probe, 0 partial, so 0 extra fetches; every site a perfect match except one `N` in a
  reverse site. That is the hit-list bias, not the absence of variants: SARS-CoV-2 has about 9
  million records and BLAST ranks by score, so a full list holds only the best matches. Only 2,106
  records carried all three oligos among the hits (5,862 excluded), because each oligo's top 5000
  is a separate selection among millions of tied perfect matches. The report now says so whenever
  the target list is full; real variant frequencies for such targets need a different sample
  (not yet designed, see PROGRESS.md).
- **Exhaustive variant analysis from NCBI Datasets genome assemblies** (v1.1.0,
  `variants/`): the target tier's BLAST hits are BLAST's best matches, so for any target with more
  records than `hitlist_size` they are biased toward perfect matches (seen live: 5000/5000 perfect
  for CDC N1). Most bacterial genomes are draft (WGS) assemblies, which `core_nt` does not contain
  at all. `variants/datasets.py` lists the target's assemblies (`exclude_paired_reports`,
  `assembly_version=current`, `exclude_atypical`) by release-year window, newest first (the
  documented `first/last_release_date` filters; `sort.field` values are not documented),
  downloads genome FASTA in batches (`datasets_batch_size`, max 100), and `variants/locate.py`
  finds the amplicon by exact k-mer seeds along the whole amplicon on both strands (so primer-site
  variants are found through the unchanged stretches between the oligos); seeds that agree
  within 20 bases form one locus. Only the region plus `flank_nt` is stored
  (`variants/store.py`, one JSON line per assembly, keyed by taxon + amplicon + flank), which
  makes runs resumable and later runs incremental; genomes are never kept (project rule). Each
  oligo is re-aligned in its expected window (+-15 bases) of the best complete copy; alignments
  are memoised by window, since most assemblies share the same sequence. Not found, contig-break
  and multi-copy assemblies are counted and reported, never dropped. Superseded assembly versions
  in the store are ignored (highest version per accession wins). Inclusivity becomes exhaustive
  per release year from the same sites. Throttle: 4 requests/s with an API key (the live limit
  header said 10), 2/s without (the keyless limit was not measured). The API key is sent as the
  documented `api-key` header; no tool/email query parameters are sent to Datasets.
- **Only fully re-aligned sites count as a measured variant**: a `blast_partial_worst_case` site's
  unaligned flanks are an assumed-conservative estimate, not an observed base, so counting it as a
  variant would misrepresent an estimate as a measurement (the same reasoning as inclusivity's
  `n_fetch_failed`). Excluded counts are reported, never silently dropped.
- **A whole fragment is the forward, probe and reverse site on the same record**, each fully
  re-aligned; records missing one of the three are excluded and counted. It deliberately does not
  require a predicted product: product prediction drops primers that cannot prime (a 3'-end
  mismatch), which are exactly the variants the table must show, and is capped at
  `max_amplicons`.
- **Species/genus/family aggregation is generic, not exclusivity-specific** (`taxonomy/rollup.py`):
  it runs over every off-target site regardless of tier, because SPEC.md step 6 ("taxonomy
  annotation of hits") is not scoped to exclusivity alone. A lineage-fetch failure degrades this
  aggregation to empty rather than failing the whole evaluation: it is informational, not a
  required section.
- **Taxonomy resolution runs before the send-oligos confirmation, without its own gate**: it sends
  only organism names (from the reviewable, packaged or lab-supplied list), never the assay's own
  oligo sequences, so it does not need the same confirm/decline protection that oligo sequences do.
- **Inclusivity cannot combine `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one
  BLAST call** — confirmed unreliable live (see "Verified in a third live run" below: 4 of 20
  checked hit accessions fell outside the requested window). This rules out the design in SPEC.md
  step 7 ("BLAST the reference amplicon against nt restricted to the target taxid, stratified into
  time windows via `ENTREZ_QUERY` date filters") for BLAST calls specifically. **Phase 4b's actual
  design (implemented)**: reuse the "target" tier search every run already makes (taxon-restricted
  only, no date filter — the same search the specificity/exclusivity assessment already needs), and
  bucket its hits into years *afterwards* via ESummary (`inclusivity/dates.py`), which reads each
  hit's own accession's submission date rather than asking BLAST to filter by date at all. This
  means inclusivity adds no new, unverified BLAST behaviour — only one new-but-standard E-utility
  (ESummary, flagged for live verification below) on top of already-verified primitives (BLAST
  taxon-only restriction, ESearch `[PDAT]` counts). The trade-off, stated honestly in every
  `InclusivityResult.limitations`: the yearly sample is whatever the target-tier search's hit list
  (capped at `hitlist_size`) happened to return for that year, not a dedicated per-year search, so a
  well-sequenced target can under- or over-represent some years depending on BLAST's own ranking.

## NCBI facts checked against current documentation (2026-09-20)

- The Common URL API page states that parameters not in its table are unsupported. The table
  includes `WORD_SIZE`, `NUCL_REWARD`/`NUCL_PENALTY`, `EXPECT`, `FILTER`, `HITLIST_SIZE`,
  `SHORT_QUERY_ADJUST`, but no `ENTREZ_QUERY` or taxid-list parameter. Taxon restriction through
  `ENTREZ_QUERY` (as Biopython's `qblast` does) is widely used but outside the documented surface.
- Listed report formats: HTML, Text, XML2, XML2_S, JSONSA, JSON2, JSON2_S, SAM (legacy `XML` is
  not listed).
- `nt` requests are switched to `core_nt`.
- Etiquette: at least 10 s between contacts, at most one poll per RID per minute, `email` and
  `tool` parameters; more than 100 searches per 24 h go to a slower queue; more than 50 searches
  should run off-peak (weekends or 9 pm–5 am US Eastern); merge short queries into one search of up
  to 1,000 bases.
- RIDs are stable for 36 hours (NCBI training material, not the API page).
- E-utilities: 3 requests/s without an API key, 10 with one.

### Implemented in v0.2.0 on the basis of the above

- Short-oligo parameters: word size 7, E-value 1000, `FILTER=F`, reward 1 / penalty -3, `core_nt`.
  Gap costs 5/2 are assumed to be valid for reward 1 / penalty -3; that is unverified, and the
  smoke test checks that the server accepts them.
- One multi-FASTA submission per tier and batch (at most 1,000 bases), as NCBI recommends.
- Taxon restriction through `ENTREZ_QUERY` with `txid<ID>[ORGN]` terms joined by `OR`; chunked to
  `search.max_taxids_per_search` because the real limit is unknown.
- Result format `JSON2_S`, parsed defensively; the layout is taken from the documented BLAST
  JSON2 format and has not been validated against real output.

### Verified in the first live smoke run (2026-09-21, one lab network, BLASTN 2.17.0+)

Accepted by the BLAST URL API: `WORD_SIZE` 7, `EXPECT` 1000, `FILTER` F, reward 1 / penalty -3,
`GAPCOSTS` "5 2", `HITLIST_SIZE` 5000, `ENTREZ_QUERY` with `txid<ID>[ORGN]`, `DATABASE` core_nt.

Report format:
- `JSON2_S` is one JSON document: `BlastOutput2` is a list with one `report` per query.
  `JSON2` and `XML2` (without `_S`) return ZIP archives; `XML2_S`, legacy `XML` and `Text` also work.
- Query ids are global counters (`Query_1830923`); the FASTA label is echoed in `query_title` and is
  the only reliable way to map a report back to an oligo.
- Every checked hit description has `id` (like `gi|2438938980|emb|OX417460.1|`), `accession`
  (**without** version), `title`, `taxid` and `sciname`; the version must be read from `id`.
  core_nt merges identical sequences: one hit can carry up to ~39 descriptions.
- HSPs carry `identity`, `align_len`, `gaps`, `evalue`, `bit_score`, `qseq`, `hseq`, `midline`,
  `hit_strand` ("Plus"/"Minus"). `HITLIST_SIZE` counts hits (merged groups): 5000 requested,
  exactly 5000 returned.

Behaviour:
- Taxon restriction through `ENTREZ_QUERY` is effective: SARS-CoV-2 search 16,992 of 16,992
  descriptions SARS-CoV-2; human search 3,714 of 3,715 *Homo sapiens*, plus one "synthetic
  construct" record (the filter uses the record's organism index, which includes secondary source
  features). It is effective, not airtight.
- Timing: the SARS-CoV-2 search took ~49 s from submission to a parsed result; the human-restricted
  core_nt search took 61 minutes (RTOE said 30 s). Plan for hours, not minutes, when a human tier
  is included. A DNS failure during polling was recovered by the retry logic.
- Human off-target hits with these settings: forward 1,482 hits (best 17 of 20 identical bases),
  reverse 1,976 (best 19 of 24), probe 219 (best 16 of 24); no list was full.
- The SARS-CoV-2 target search returned full lists (5,000 hits) for all three oligos, so target
  tier saturation is expected; inclusivity needs time windows.

E-utilities:
- ESearch `[PDAT]` date filters work (SARS-CoV-2 in nuccore: 9,217,970 records in total,
  3,571,941 in 2022, 33 in January 2020). `retstart` up to 100,000 still returned identifiers.
- `efetch` with `seq_start`/`seq_stop` is 1-based inclusive; `strand=2` returns the reverse
  complement. The CDC N1 oligos match NC_045512.2 exactly at 28287-28358 (72 bp).
- Entrez Taxonomy: 12 of 13 names resolved uniquely with `[Scientific Name]`; "Mycoplasma
  pneumoniae" returned nothing, most likely because the scientific name changed. The organism list
  must be resolved with synonyms and every non-exact resolution flagged (v0.4.0).
- Requests spaced exactly at 3/s still drew HTTP 429 twice.

### Verified in a second live run (2026-09-21), used to build v0.3.0

For a Minus-strand hit, `hit_from > hit_to`, `query_strand` is always `Plus`, and `hseq` is written
in the oligo's own orientation (not the subject's forward strand) — confirmed on a real SARS-CoV-2
reverse-primer hit, kept verbatim in `tests/fixtures/real_hits_strands.json`. Duplex Tm/ΔG for a
mismatch at the very 3' terminal base, computed by treating it as an unpaired overhang, was checked
against primer3 directly (61.6 vs 61.2 °C) rather than against a BLAST hit.

### Verified for the v1.1.0 design (2026-09-23, `scripts/probe_variant_sources.py`, API key set)

NCBI Datasets v2 (endpoints from the published OpenAPI spec, behaviour measured live):
- `/genome/taxon/{name}/dataset_report` accepts scientific names; `total_count` (all assembly
  versions / current and not atypical): C. trachomatis 750 / 713, N. gonorrhoeae 53,535 / 53,386,
  S. pneumoniae 98,633 / 96,853, M. tuberculosis 16,705 / 16,451, E. coli 518,826 / 492,216.
- `page_size=1000` returned all 750 C. trachomatis reports in one page (2.76 MB, 0.54 s, complete
  reports). Report keys include `accession`, `paired_accession`, `assembly_info.release_date`,
  `assembly_info.assembly_level` (Chromosome, Complete Genome, Contig, Scaffold),
  `assembly_stats.total_sequence_length`, `checkm_info`. GCA and GCF copies of the same assembly
  are both listed (e.g. GCA_000008725.1 and GCF_000008725.1): de-duplicate before counting.
- Response headers with the API key: `X-Ratelimit-Limit: 10`. 13 requests at 2/s drew no 429.
- `/genome/accession/{acc}/download?include_annotation_type=GENOME_FASTA`: a zip with
  `ncbi_dataset/data/<acc>/<acc>_<name>_genomic.fna` (plus README, jsonl report, catalog,
  md5sum). A 1.03 Mb draft genome (3 WGS contigs): 311,652 bytes zipped, 0.57 s.
- `hydrated=DATA_REPORT_ONLY` gives `ncbi_dataset/fetch.txt`: one line per file, tab-separated
  `URL  0  data/<acc>/<file>.fna`; the URL (`api.ncbi.nlm.nih.gov/datasets/fetch_h/...`) returned
  the plain, uncompressed FASTA (1,055,612 bytes, `text/plain`, 0.61 s).

E-utilities and BLAST:
- ESearch `retstart` at 1,034,331 / 1,228,716 / 1,448,773 / 3,571,940 (the last record of
  SARS-CoV-2 2022, 3,571,941 records) each returned exactly one UID.
- EFetch `rettype=acc` (POST, 100 UIDs) returned exactly one accession.version per UID.
- BLAST of the 72 bp N1 amplicon with an ENTREZ_QUERY of 100 `[ACCN]` terms (1,998 characters) was
  accepted and finished in 43 s: all 100 requested accessions were hit, plus 43 accessions outside
  the list. The restriction is not exact, so partitioned searches must filter hits back to their
  own list; coverage of the list was complete.
- Not yet answered: BLAST against `DATABASE=wgs` with a species ENTREZ_QUERY (the probe's query
  region was outside the 7,500 bp record ESearch returned first, a plasmid; fixed, needs a rerun).

### First live run of the exhaustive variant analysis (2026-09-23, C. trachomatis, v1.1.0 dev)

User's own cryptic-plasmid assay (87 bp reference amplicon). NCBI Datasets listed 357 assemblies
(current, not atypical, one per GenBank/RefSeq pair; 713 without that de-duplication), all 357
downloaded and scanned in one run, 0 failed downloads. Region found (all three sites complete)
in 76, not found in 281, contig break 0, more than one copy 3. Variants among the 76: forward
69.7% perfect, 27.6% one mismatch at position 12 (2005-2023), 2.6% two mismatches; probe 98.7%
perfect; reverse 100% perfect; no variant touches a primer's 3' end. The 281 "not found" included
GCF_000008725.1 (D/UW-3/CX), which is most likely a chromosome-only assembly (the plasmid is not
part of every assembly) -- not verified from here. That motivated the plasmid split: the rule
"a FASTA description containing 'plasmid' marks a plasmid sequence" is itself unverified until
the report's "Recognised as plasmid" examples are checked on a live run.

### Verified in a third live run (2026-09-22)

- **Entrez queries with 11, 40 and 100 taxids were all accepted** by the BLAST URL API (no
  rejection). The 11-taxid search was let run to completion (5000 hits per oligo, taxon
  restriction still effective by lineage check); the 40- and 100-taxid searches were only checked
  for acceptance (RID issued, `Status=READY`/`WAITING` on the first poll), not full correctness.
  The true upper limit is still unknown, but 100 is a safe planning number, well above the
  conservative default (`max_taxids_per_search: 20`).
- `retstart` up to 100,000 still returns identifiers (reconfirmed).
- **`[PDAT]` date windows do NOT reliably restrict a BLAST search the way they restrict an ESearch.**
  A BLAST search of the 72 bp N1 amplicon with `ENTREZ_QUERY = "txid2697049[ORGN] AND
  2020/01/01:2020/01/31[PDAT]"` returned 15 hits; of the first 20 hit accessions, only 16 actually
  fell inside that window when checked independently via ESearch with the same date filter (4
  leaked out). **This rules out the inclusivity design this project had assumed** (SPEC.md step 7:
  "BLAST [the reference amplicon] against nt restricted to the target taxid, stratified into time
  windows via `ENTREZ_QUERY` date filters") for BLAST calls specifically; ESearch's own `[PDAT]`
  filtering is independently confirmed reliable (see the `01_esearch_counts` findings below), so
  phase 4b's design must get its per-window accession lists from ESearch and not lean on BLAST to
  do the date filtering — see the design note under "Design decisions".

The NCBI Taxonomy page announces that the legacy Taxonomy Browser will be replaced by the NCBI
Datasets Taxonomy Browser in Fall 2026. That concerns the web interface; whether the Entrez
Taxonomy E-utilities used here are affected has not been checked. Alternative databases
(`human_genomic`, `refseq_genomic`, `refseq_rna`) remain unchecked (`--probe-databases` was not
used in the runs so far).

### Verified for v0.3.0 (`scripts/validate_assessment.py`, live, 2026-09-21)

The two pruning bounds described above (mismatch lower bound, clean-3'-nt cap) were derived on
paper from BLAST's documented scoring, not observed; the script re-aligns a sample of real partial
hits over their full oligo length — including hits the assessment would otherwise skip — and
reports every case where reality contradicts a bound. First live run: CDC N1 example assay,
background tier, 905 relevant alignments, 244 ruled out without fetching, 661 needing a fetch, an
80-hit sample (40 fetchable, 40 ruled out) checked, **0 contradictions**. That 661 figure replaces
an earlier "about 1,500" guess from development chat, which was never measured and should be
disregarded.

This is one sample of one tier of one assay, not a proof for every assay or tier: re-run the script
(varying `--tier` and `--sample`) whenever the alignment or pruning logic changes, and periodically
otherwise, before trusting a specificity verdict on a different assay.

### Verified for v0.4.0 phase 4a (`scripts/smoke_test.py` steps `03b`/`03c`, live, 2026-09-22)

- **Lineage parsing works.** `taxonomy/resolve.py`'s `Rank`/`LineageEx` parsing was checked against
  5 real Taxonomy EFetch responses (Homo sapiens, Mus musculus, SARS-CoV-2, Escherichia coli,
  Staphylococcus aureus): every one returned a populated genus and family. One real subtlety: a
  taxon's own `Rank` is not always `species` — SARS-CoV-2's is `"no rank"`, with `species` itself
  coming from its `LineageEx` ancestor (`Betacoronavirus pandemicum`, its formal ICTV/NCBI species).
  `Lineage.species` correctly reports the ancestor in that case, not the taxon's own name.
- **The `Mycoplasma pneumoniae` `[All Names]` synonym fallback does NOT resolve it** (`status:
  "unresolved"`, both `[Scientific Name]` and `[All Names]` returned zero hits). The hypothesis in
  the previous note — that a 2018 genus rename to *Mycoplasmoides* would be caught by `[All Names]`
  — was wrong: NCBI's `[All Names]` index apparently does not carry the old genus as a synonym for
  this species. **Fixed by editing the organism list** to use the current name directly
  (`Mycoplasmoides pneumoniae`) rather than relying on synonym resolution; this itself needs a live
  re-check (not yet done) to confirm the new name resolves.
- **The packaged organism list resolved 38 of 40 names in this run** through the real
  `taxonomy.plan.resolve_organism_list` path. Unresolved (this run): `Mycoplasma pneumoniae` (see
  above, now renamed in the list) and `Mycobacterium chelonae` (cause unknown — a plausible,
  well-established species name; needs investigation, not assumed to be a rename). Both are exactly
  what the "flag, never guess" design is for: they are left out of the exclusivity search and
  reported, not silently dropped. **Update (2026-09-22, next live run): the renamed entry,
  `Mycoplasmoides pneumoniae`, now resolves** — 39 of 40 packaged names resolved, only
  `Mycobacterium chelonae` remained unresolved. See "Verified for v0.4.0 phase 4b" below.

### Verified for v0.4.0 phase 4b (`scripts/smoke_test.py` step `08b`, live, 2026-09-22)

- **The renamed organism-list entry `Mycoplasmoides pneumoniae` resolves live.** The organism-list
  resolution carried over from phase 4a went from 38/40 to 39/40 in this run; only
  `Mycobacterium chelonae` remains unresolved (cause still unknown).
- **`Eutils.esummary()`'s JSON shape is correct against a real response**: `result.uids` is a list
  of UID strings, and `result[uid]` is one document summary object per UID, exactly as the client
  assumes.
- **The nuccore ESummary docsum's date field is `createdate`** (format `"YYYY/MM/DD"`, e.g.
  `"2020/01/13"` for `NC_045512.2`), the first candidate `year_from_docsum()` tries — confirmed by
  extracting the correct year for two real records (`NC_045512.2` → 2020, `NC_000007.14` → 2002,
  both matching the real `createdate` values in the response). The other candidate field names
  (`CreateDate`, `updatedate`, `UpdateDate`, `sortpubdate`, `PubDate`) remain unverified but are no
  longer needed for the common case.
- **NCBI keys the ESummary result by its own resolved UID, not by the accession string sent as
  input**, confirmed directly (the response for `id=NC_045512.2,NC_000007.14` came back keyed
  `"1798174254"`/`"568815591"`, not by either accession). `fetch_years()`'s re-indexing by each
  docsum's own `accessionversion` field (`inclusivity/dates.py`) correctly recovered both years
  despite this. **A bug was found and fixed in the smoke-test script itself** (not in the shipped
  `inclusivity/dates.py`, which was already correct): step `08b`'s own findings computation had
  naively indexed the UID-keyed response by accession, which silently produced empty findings
  (`esummary_docsum_keys: {}`) even though `fetch_years_result` was correct throughout. Fixed by
  re-indexing the same way `fetch_years()` does, and the constructed test fakes
  (`tests/world.py`, `tests/test_smoke_script.py`) were tightened to use a UID that deliberately
  differs from the accession, so this class of bug is now caught by the test suite too, not only
  by a live run.
- Inclusivity's ESummary-based date lookup can now be considered verified for the common case
  (`createdate` present, `accessionversion` present). Still open: a record where `createdate` is
  absent and one of the fallback field names is needed instead has not been observed live.

### Verified for v1.0.0 (Docker, live, 2026-09-22)

The Docker image could not be built in the sandbox this was developed in (no route to Docker Hub
through its outbound proxy -- both `docker pull python:3.12-slim` and `docker build` failed
identically with an HTTP 403 from Docker's own CDN, even after installing the proxy's CA bundle
system-wide and passing `HTTPS_PROXY`/`HTTP_PROXY` to the daemon as the environment's own guidance
for `docker build` describes; concluded to be a genuine restriction on reaching that particular CDN
through this proxy, not a fixable misconfiguration, and not worked around further). The user built
and ran it themselves (Synology NAS, Docker running as root):

- `docker build` succeeds; `--version` and `--help` produce the expected output.
- **The image's default non-root user (uid 1000) cannot write to a bind-mounted host directory it
  does not own** -- hit as a real `PermissionError` on first try (`docker run -v "$PWD/work:/work"
  ... init ...` with the host `work/` directory owned by root). Documented in the README:
  `--user "$(id -u):$(id -g)"` on `docker run` (what the user used successfully) or `chown`-ing the
  host directory to uid 1000 beforehand.
- With that fixed, `init` and `run --qc-only` both produced output identical to the plain-virtualenv
  install this was first checked against (same verdict, same rationale message, correct files).
- A full network run against real NCBI, through the container, also completed successfully (see
  next section for what it found).

### Verified for v1.0.0 (first full live `run`, through Docker, 2026-09-22)

The user's first full `run` (CDC N1 example, packaged organism list, background tier included)
completed end to end through the container and surfaced a real, significant bug, not a config or
environment issue:

- **The exclusivity tier had no exclusion for the assay's own target taxid.** The packaged
  organism list includes "Severe acute respiratory syndrome coronavirus 2" (a respiratory panel
  reasonably tests for it alongside other pathogens) — which is also the CDC N1 example's own
  target (`taxid 2697049`). Without an exclusion, the exclusivity tier's search restricted to that
  taxid (among ~39 others) could only ever find the assay's own perfect, intended match, and every
  one of those matches was reported as a critical off-target site or a "likely detected" predicted
  product — dominating the run: 4025 critical primer sites, 2000 critical probe sites, 343
  "likely detected" predicted products, all with 0 mismatches (`+0.0 °C vs perfect`) against
  records explicitly titled "Severe acute respiratory syndrome coronavirus 2". This alone flipped
  the overall verdict from what should have been closer to a real (background-tier) `WARN` into a
  dramatic, misleading `FAIL`.
- **Fixed**: `search/execute.py` now filters `assay.target.taxid` out of the resolved exclusivity
  taxids before they reach the search planner, so this tier is never asked to find the assay's own
  target. The organism-list row for it is still shown (never silently dropped, per the project's
  own "never present a sample as the full population" rule) — `ExclusivityRow.is_target` flags it,
  and no site/amplicon evidence is populated for it, defensively, even if some were somehow present.
- Everything else in that first full run looked as expected and not itself concerning: real
  human-background hits (24 critical, 71 warning primer sites — the CDC N1 forward/reverse primers
  do have some homology to the human genome, a known, documented finding for this published assay,
  not new), the hit-list saturating for the (now-smaller, ~38-organism) exclusivity tier at the
  configured `max_sites_per_query` per search chunk, and `Mycobacterium chelonae` still the one
  unresolved organism-list name (consistent with earlier live runs).
### Verified for v1.0.0 (retry of the full live `run`, with the fix applied, 2026-09-22)

The user rebuilt the image with the fix and re-ran the same full `run` (same cached BLAST results,
so no new NCBI calls were needed for the unaffected tiers). Confirms both the fix and the
history/diff feature against real data in one pass:

- **The fix works.** Predicted off-target products dropped from 500 to 0 (that section is now
  `PASS`), and the "Changes since the previous run" section correctly shows 6028 off-target sites
  and 500 predicted products "no longer found" — exactly the bogus SARS-CoV-2-self-match evidence
  disappearing. The exclusivity table's row for it now reads "assay's own intended target —
  excluded from this search", as designed.
- **The remaining `FAIL` is a genuine finding, not a bug**: real homology between the CDC N1
  primers and the human genome (24 critical + 71 warning primer sites in `background`; a similar
  picture in `exclusivity`, since "Homo sapiens" is *also* separately listed in the packaged
  organism list — the same organism searched by two different tiers for two different reasons,
  redundant but not wrong). This is a known, documented characteristic of this published assay.
- **43 "new" sites in the diff are expected, not concerning**: removing SARS-CoV-2 from the
  exclusivity tier's taxid list shifted which of the remaining ~38 organisms share a
  `max_taxids_per_search` chunk, which shifted which hits rank within that chunk's own
  `max_sites_per_query` cap — surfacing a handful of previously-crowded-out, minor-severity
  Influenza A warning sites. A real, if minor, side effect of the fix's own correctness, not a
  new problem.
- This is also the first live confirmation that history/diff (this same phase's other new feature)
  correctly attributes a change to its real cause across two runs of real NCBI data, not only the
  constructed test world.

### Still unverified for v1.0.0

- **History/diff's natural-key matching has now been checked against one real two-run pair**
  (immediately above), which is a stronger check than the constructed test world alone, though
  still only one assay and one pair of runs.

### Verified in a fourth live smoke run (2026-09-23) -- and a real bug found

Ran with `NCBI_API_KEY` set for the first time (10 req/s instead of 3). Step `06` was changed from
the earlier runs' ad-hoc human-background check to an Influenza A virus restriction check (the
human check is now behind `--human`), which surfaced something none of the SARS-CoV-2/human
checks ever would have:

- **`ENTREZ_QUERY` taxon restriction (`txid11320[ORGN]`) is genuinely effective** -- a rigorous
  ancestry-based check (`lineage_check`) found **100% of a 300-hit sample** genuinely within the
  Influenza A subtree.
- **But only 89.5% (5530/6180) of hit descriptions carry the exact species-level taxid (11320)
  itself.** The other ~10.5% are filed under distinct, more specific strain-level taxa (e.g.
  "Influenza A virus (A/Michigan/272/2017(H1N1))"), each its own NCBI taxid, children of 11320.
  Restriction is not the problem; a naive "does this hit's own taxid literally equal the
  requested one" check would have looked like ~10% leakage that isn't real.
- **This exposed a genuine bug**, not just a smoke-test artifact: `taxonomy/exclusivity.py`
  grouped hits by exactly this kind of naive taxid equality against each organism-list entry's
  own resolved taxid, so any hit filed under a more specific descendant taxid than the
  organism-list name resolved to was silently missing from that organism's row and count --
  roughly a 10% real undercount for a finely-split taxon like influenza. The overall exclusivity
  tier verdict was never affected (it sums every exclusivity-tier hit directly, not grouped by
  row) -- only the per-organism breakdown table undercounted. Fixed same-day: see "Design
  decisions" below and the `[Unreleased]` CHANGELOG entry. Not yet independently re-verified live
  (the constructed test world's taxonomy EFetch fake always returns an empty `TaxaSet`, so this
  fix's species-matching branch is only unit-tested so far, not exercised end-to-end against real
  lineage data).
- Also reconfirmed, consistent with prior runs: SARS-CoV-2 positive control, reference-position
  check, `[PDAT]` date-window unreliability for BLAST, ESummary UID-vs-accession re-indexing,
  multi-taxid list acceptance (11/40/100), and organism-list resolution (39/40, only
  *Mycobacterium chelonae* still unresolved).
