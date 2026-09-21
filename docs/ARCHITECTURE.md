# Architecture

Status: v0.3.0 implements steps 1, 2, 5, 6 (from v0.2.0) plus 7 and 8: full-length re-alignment of
every relevant hit and amplicon pairing, feeding a real specificity verdict. Steps 3, 4, 9 and 10
(taxonomy, the clinical organism list, inclusivity, exclusivity) and 11's history comparison are
still the agreed design for later releases, not implemented.

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
            11 Verdict engine ◄── previous run (history)
                                      ▼
            12 Outputs: HTML · results.json · hits.tsv · xlsx · diff
```

## Roadmap

| Version | Content |
|---|---|
| 0.1.0 | Skeleton, input parsing, oligo QC, report skeleton |
| 0.2.0 | Remote BLAST backend: batching, cache, resumable jobs, parser, smoke test |
| **0.3.0** | Full-length re-alignment, mismatch Tm/ΔG, amplicon pairing, specificity verdicts |
| 0.4.0 | Taxonomy, organism list, inclusivity, exclusivity |
| 1.0.0 | Run history, yearly diff, complete report, Docker, documentation |

## Design decisions

- **Own `requests` client for BLAST, not `qblast`**: `qblast` blocks until results arrive, so a RID
  cannot be persisted and resumed.
- **Cache scoped by validity**: BLAST results only within a run/resume (short TTL), sequence
  windows by accession.version long-term, taxonomy with a moderate TTL. A naive content-hash cache
  would serve last year's results against this year's database.
- **Saturation is judged by relevance**: a full hit list only matters if its weakest hit is still
  biologically relevant; then the search is split further.
- **Inclusivity with honest denominators**: ESearch counts per time window; complete enumeration
  where possible; truncated windows are labelled as upper bounds (BLAST ranks by similarity to the
  reference, so truncation biases towards reference-like sequences).
- **Missing evidence is never a PASS** (verdict INCOMPLETE).
- **History as files**: one directory per run plus a small index; easy to audit and diff.
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

### Still unverified (checked by the next smoke run, needed before v0.4.0)

How many taxa an Entrez query can hold (13, 40 and 100 are probed); whether `[PDAT]` date windows
restrict a BLAST search the way they restrict an ESearch; whether alternative databases
(`human_genomic`, `refseq_genomic`, `refseq_rna`) are accepted by the URL API and faster for the
human background.

The NCBI Taxonomy page announces that the legacy Taxonomy Browser will be replaced by the NCBI
Datasets Taxonomy Browser in Fall 2026. That concerns the web interface; whether the Entrez
Taxonomy E-utilities used in v0.4.0 are affected has not been checked and will be verified then.

### Still unverified for v0.3.0 (run `scripts/validate_assessment.py`, never yet run live)

The two pruning bounds described above (mismatch lower bound, clean-3'-nt cap) were derived on
paper from BLAST's documented scoring, not observed. The script re-aligns a sample of real partial
hits over their full oligo length — including hits the assessment would otherwise skip — and reports
every case where reality contradicts a bound; a contradiction means the pruning is unsafe and must
not be trusted until fixed. It also counts how many `efetch` calls a real run actually makes; an
earlier "about 1,500" figure mentioned in development chat was an unverified guess and should be
disregarded in favour of the script's own count.
