# qpcr-assay-check

Yearly in silico re-evaluation of **one real-time PCR (TaqMan) assay per run** for clinical
microbiology laboratories: forward primer, reverse primer, probe and an intended target organism go
in; a detailed, reproducible, version-stamped evaluation record comes out (HTML, JSON, Excel).

> **Status: v0.1.0 (alpha).** This release checks **oligo quality only** (Tm, GC, dimers, hairpins,
> probe rules, optional amplicon geometry). Searching public sequence data (specificity,
> inclusivity, exclusivity) arrives in later releases, see the roadmap. **Until then a full run
> ends as `INCOMPLETE`, never as `PASS`.** Nothing is sent to NCBI in this version.

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

# a full run (INCOMPLETE in v0.1.0, because remote analyses do not exist yet)
qpcr-assay-check run my-assay/assay.yaml -o results
```

Each run writes `results/<assay>/<run-id>/` containing:

| File | Content |
|---|---|
| `report.html` | Self-contained evaluation record (no external requests) |
| `results.json` | Machine-readable results (`schema_version` 1) |
| `results.xlsx` | Workbook: summary, inputs, QC checks, structures, sections |

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
- `near_neighbour_taxids` and `exclusion_taxids` are accepted now and used from v0.4.0.

### The example assay

`examples/cdc_2019-nCoV_N1.yaml` is the CDC 2019-nCoV N1 assay. Its file header documents how the
sequences were checked: they were cross-checked against two open-access papers that quote the CDC
set, **not** against the CDC package insert, which was not accessible. Verify against your own
supplier documentation before relying on it. No reference amplicon is shipped because none was
verified against a sequence record.

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

## NCBI access (from v0.2.0)

Version 0.2.0 introduces the NCBI client. NCBI asks every user to identify themselves. Set these
environment variables (never commit them; `.env.example` shows the names):

```bash
export NCBI_EMAIL="your.name@example.org"   # required by NCBI
export NCBI_API_KEY="..."                   # optional; raises E-utilities from 3 to 10 requests/s
```

**Privacy note: from v0.2.0 the oligo sequences of the assay are sent to NCBI's servers** for BLAST
searches. This matters for proprietary assays. Version 0.1.0 sends nothing.

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
- Not yet implemented: everything that needs sequence data (see the roadmap).

## Roadmap

| Version | Content |
|---|---|
| **0.1.0** | Skeleton, input parsing, oligo QC, report skeleton |
| 0.2.0 | Remote BLAST backend: batching, cache, resumable jobs, parser |
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
