# qpcr-assay-check

Yearly in silico re-evaluation of **one real-time PCR (TaqMan) assay per run** for clinical
microbiology laboratories: forward primer, reverse primer, probe and an intended target organism go
in; a detailed, reproducible, version-stamped evaluation record comes out (HTML, JSON, Excel).

> **Status: v0.2.0 (alpha).** `run` still checks **oligo quality only** (Tm, GC, dimers, hairpins,
> probe rules, optional amplicon geometry). New in this release: the `search` command runs tiered,
> taxon-restricted **remote BLAST searches** and writes the raw hits (`hits.tsv`, `search.json`).
> Those hits are **not yet assessed** (re-alignment and off-target verdicts arrive in v0.3.0), so a
> full `run` still ends as `INCOMPLETE`, never as `PASS`. The BLAST client was validated once
> against the live NCBI servers (2026-09-21); see `docs/ARCHITECTURE.md` for what was verified.

In silico analysis **does not replace experimental validation**, and **your laboratory is
responsible for verifying this software within its own quality system** before relying on it.

## Design goals

- No local BLAST database and no database maintenance: all NCBI searching will be remote.
- One assay, once a year: thoroughness and reliability over speed.
- Filed as a record: every report carries a timestamp, tool version and a SHA-256 hash of the inputs.
- Transparent, configurable verdict logic. Thresholds in this tool are **starting points**; each
  laboratory must review them.

## Install

Requires Python 3.11 or newer.

```bash
pipx install git+https://github.com/zmeel/qpcr-assay-check.git
qpcr-assay-check --version
```

From a clone (development):

```bash
git clone https://github.com/zmeel/qpcr-assay-check.git
cd qpcr-assay-check
pip install -e ".[dev]"
pytest
```

## Quick start

```bash
# write a worked example and a fully commented default configuration
qpcr-assay-check init my-assay --example

# check the input files without running anything
qpcr-assay-check validate my-assay/assay.yaml

# oligo QC only (verdict covers QC alone; exit code 10 = WARN)
qpcr-assay-check run my-assay/assay.yaml --qc-only -o results

# a full run (INCOMPLETE until the off-target assessment exists, v0.3.0)
qpcr-assay-check run my-assay/assay.yaml -o results
```

Each run writes `results/<assay>/<run-id>/` containing:

| File | Content |
|---|---|
| `report.html` | Self-contained evaluation record (no external requests) |
| `results.json` | Machine-readable results (`schema_version` 1) |
| `results.xlsx` | Workbook: summary, inputs, QC checks, structures, sections |

### Remote BLAST search (v0.2.0)

```bash
export NCBI_EMAIL="your.name@example.org"      # required by NCBI
qpcr-assay-check search my-assay/assay.yaml --dry-run   # show exactly what would be sent
qpcr-assay-check search my-assay/assay.yaml -o results   # asks before sending anything
```

`search` sends the oligos to NCBI in tiers (intended target, near neighbours and exclusion taxa,
background taxa such as human), each restricted to its taxa, with short-oligo BLAST settings
(word size 7, E-value 1000, filtering off, reward 1 / penalty -3, gap costs 5/2, database
`core_nt`). Output goes to `results/<assay>/search-<hash>/`:

| File | Content |
|---|---|
| `hits.tsv` | One row per alignment: tier, query oligo, subject, taxon, identical bases, positions |
| `search.json` | Parameters, BLAST version, RIDs, hit counts, hit-list saturation, restriction summary |
| `jobs.json` | Job state: the run resumes from here if it is interrupted |

Behaviour worth knowing:
- **Resumable**: if a run is interrupted (network, laptop closed, timeout), run the same command
  again. The request IDs (RIDs) are saved *before* polling starts; NCBI keeps results for about 36
  hours, after which a job is resubmitted automatically.
- **Polite**: at least 10 s between BLAST requests, at most one poll per RID per minute, your
  e-mail and the tool name on every request, and exponential backoff on errors.
- **Saturation is judged by relevance**: a full hit list only triggers a warning (exit code 10)
  if even its weakest hit still has at least `search.relevance.min_identical_bases` identical
  bases, meaning relevant hits may have been cut off.
- **Cached, but not for long**: BLAST results are reused only for `ncbi.blast_cache_ttl_days` (7),
  so next year's run never receives this year's answer.
- Exit codes: 0 done, 10 done with a saturated hit list, 64 invalid input, 70 NCBI problem (resumable).

You can also define an assay entirely on the command line:

```bash
qpcr-assay-check run --qc-only --name "My assay" \
  --forward GACCCCAAAATCAGCGAAAT --reverse TCTGGTTACTGCCAGTTGAATCTG \
  --probe ACCCCGCATTACGTTTGGTGGACC --probe-reporter FAM --probe-quencher BHQ1 \
  --template-type RNA --target-taxid 2697049
```

Command-line options override values in the assay file.

## Assay file

```yaml
assay_name: CDC 2019-nCoV N1
forward: GACCCCAAAATCAGCGAAAT      # 5'->3', DNA, IUPAC codes allowed
reverse: TCTGGTTACTGCCAGTTGAATCTG
probe: ACCCCGCATTACGTTTGGTGGACC    # sequence only; dye/quencher go below
probe_reporter: FAM
probe_quencher: BHQ1
probe_modifications: []            # e.g. [MGB]; any entry triggers a Tm-reliability warning
template_type: RNA                 # DNA | RNA
target:                            # a taxonomy ID and/or a reference accession
  taxid: 2697049
  accession: NC_045512.2
  gene: N
# reference_amplicon: ...          # optional; enables amplicon length/GC/overlap checks
```

Notes:
- Write oligos as DNA (T, not U), also for RNA targets. Dye and quencher names never belong in the
  sequence.
- Degenerate (IUPAC) oligos are expanded (cap: `oligo.max_degenerate_expansions`, default 64);
  every variant is evaluated and the worst one decides.
- `near_neighbour_taxids` and `exclusion_taxids` define the near-neighbour search tier of `search`.

### The example assay

`examples/cdc_2019-nCoV_N1.yaml` is the CDC 2019-nCoV N1 assay. Its file header documents the
verification: the oligos match two open-access papers that quote the CDC set, and a live check
showed that all three occur exactly in the SARS-CoV-2 reference genome NC_045512.2 (positions
28287-28358, a 72 bp product, which is also the shipped `reference_amplicon`). That shows the
sequences are real and consistent with the reference; it does not show they are what your
laboratory orders, so verify against your own supplier documentation.

## Configuration

`qpcr-assay-check init` writes `config.yaml` with every default and its meaning. Pass your own file
with `--config`; only the keys you set change, and unknown keys are rejected so a typo can never
silently fall back to a default. Reaction conditions (Na⁺, Mg²⁺, dNTP, primer and probe
concentration, annealing temperature), all QC thresholds and the structure limits live there.
`examples/config_annealing_55C.yaml` shows an override.

## Verdicts and exit codes

| Verdict | Exit code | Meaning |
|---|---|---|
| PASS | 0 | Every evaluated check passed **and** every required analysis was run |
| WARN | 10 | No failure, at least one warning |
| FAIL | 20 | At least one check failed |
| INCOMPLETE | 30 | A required analysis was not evaluated; not a pass |
| (invalid input) | 64 | The assay or configuration file is invalid |

Precedence: FAIL > INCOMPLETE > WARN > PASS. Missing evidence never counts as a PASS.

## NCBI access

NCBI asks every user to identify themselves. Set these environment variables (never commit them;
`.env.example` shows the names):

```bash
export NCBI_EMAIL="your.name@example.org"   # required for any network use
export NCBI_API_KEY="..."                   # optional; raises E-utilities from 3 to 10 requests/s
```

**Privacy note: the `search` command sends the oligo sequences of the assay to NCBI's public
servers** for BLAST searches. This matters for proprietary assays. It always shows the sequences
and the planned searches first and asks for confirmation (`--yes` skips the question; `--dry-run`
sends nothing and needs no credentials). `run` and `validate` never use the network.

### Live smoke test (please run once)

The BLAST client was written without access to NCBI, so several behaviours are still unverified
(see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). `scripts/smoke_test.py` checks them against the
real servers and writes `smoke_out/smoke_report.json` (without secrets, rewritten after every step):

```bash
pip install -e .
mkdir -p smoke_out
nohup python scripts/smoke_test.py > smoke_out/run.log 2>&1 &
tail -f smoke_out/run.log
```

| Option | Effect |
|---|---|
| `--quick` | Only the core searches (SARS-CoV-2 control and an influenza A restriction check) |
| `--max-wait-minutes N` | Give up on one search after N minutes (default 30); it stays resumable |
| `--human` | Also run the human-background search with the default settings (slow, see below) |
| `--probe-databases` | Try alternative databases for a faster human background search |

It sends only the published CDC N1 oligos. It also verifies those oligos against the SARS-CoV-2
reference genome record, which closes the verification gap noted in the example file.

**Timing to expect** (one measurement, 2026-09-21): a SARS-CoV-2-restricted search took about
one minute; a human-restricted search against `core_nt` took **61 minutes**. A `search` with the
default human background tier therefore takes roughly an hour or more. The default wait limit is
240 minutes and interrupted searches resume.

## Limitations

- Thresholds are common-practice defaults, not acceptance criteria.
- Tm and dimer values are nearest-neighbour estimates. MGB/LNA/ZEN-type modifications are not
  modelled (a warning is raised).
- Structures are searched at the annealing temperature; one that forms only at lower temperatures
  may not be reported, and the same oligo can be flagged at one annealing temperature and not at
  another.
- The HTML report embeds Plotly's JavaScript bundle (about 5 MB). That bundle contains URL strings
  for map tiles that are only used by map charts, which this tool does not produce; the report
  makes no external requests. A test checks that no HTML tag references another file or host.
- BLAST is a heuristic (exact 7-base seed): heavily mismatched binding sites can be missed, so "no
  hit" is not "no binding". Primer-BLAST and IDT OligoAnalyzer remain useful manual cross-checks.
- The remote client was validated against live NCBI once, for one assay; NCBI can change formats
  or behaviour, and a parse failure ends the run as an error rather than guessing.
- Hits are collected but not yet assessed: re-alignment, off-target amplicons and taxonomy come
  in later releases (see the roadmap).

## Roadmap

| Version | Content |
|---|---|
| 0.1.0 | Skeleton, input parsing, oligo QC, report skeleton |
| **0.2.0** | Remote BLAST backend: batching, cache, resumable jobs, parser, smoke test |
| 0.3.0 | Full-length re-alignment, mismatch Tm/ΔG, amplicon pairing |
| 0.4.0 | Taxonomy, organism list, inclusivity, exclusivity |
| 1.0.0 | Run history, yearly diff report, complete report, Docker, documentation |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and the NCBI facts it rests on.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest                # live NCBI tests are skipped unless --run-live is given; CI never runs them
```

## License

Apache License 2.0, see [LICENSE](LICENSE). The software is provided without warranty.
