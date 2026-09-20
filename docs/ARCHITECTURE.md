# Architecture

Status: v0.1.0 implements steps 1, 2 and the offline part of 5 (see the roadmap). Everything else in
this document is the agreed design for later releases.

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
| 0.2.0 | Remote BLAST backend: batching, cache, resumable jobs, parser |
| 0.3.0 | Full-length re-alignment, mismatch Tm/ΔG, amplicon pairing |
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

### Not yet verified (checked by `scripts/smoke_test.py`, from v0.2.0)

Whether `ENTREZ_QUERY` is still honoured; the number of taxa an Entrez query can hold; the maximum
`HITLIST_SIZE` via the URL API; valid `GAPCOSTS` for reward/penalty 1,-3; the semantics of the `_S`
formats; the ESearch UID cap for nuccore; the behaviour of `[PDAT]` for nuccore.

The NCBI Taxonomy page announces that the legacy Taxonomy Browser will be replaced by the NCBI
Datasets Taxonomy Browser in Fall 2026. That concerns the web interface; whether the Entrez
Taxonomy E-utilities used in v0.4.0 are affected has not been checked and will be verified then.
