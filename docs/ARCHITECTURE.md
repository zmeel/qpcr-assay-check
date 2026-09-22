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
against a real multi-year dataset yet (see "Still unverified" below).

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
- **Not yet re-verified**: a fresh full run with the fix applied, to confirm the corrected verdict
  looks sane end to end (the fix was implemented and unit/CLI-tested against a constructed world
  reproducing the exact bug, but not re-run against live NCBI data after the fix).

### Still unverified for v1.0.0

- **The history/diff feature has not been checked against a real multi-year dataset**, only the
  constructed test world and hand-built unit fixtures (`tests/test_history.py`,
  `tests/test_run_full.py::test_history_diff_across_two_runs`). The natural-key matching logic
  (site/amplicon identity by accession and position) is straightforward and needs no live NCBI
  behaviour to verify -- it operates entirely on this tool's own already-verified output -- so no
  smoke-test step was added for it.
