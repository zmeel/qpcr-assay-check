# User guide

The full reference for qpcr-assay-check: installation details, every command, the assay file,
configuration, NCBI access and the complete list of limitations. The [README](../README.md) gives
the overview; release history is in [CHANGELOG.md](../CHANGELOG.md), design decisions and the NCBI
facts they rest on in [ARCHITECTURE.md](ARCHITECTURE.md), the mismatch classes in
[MISMATCH_CLASSES.md](MISMATCH_CLASSES.md).

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

### Docker (v1.0.0)

No local BLAST database is built or shipped: the image is just the CLI and its Python
dependencies, so it is small and needs nothing beyond network access to NCBI at run time.

```bash
git clone https://github.com/zmeel/qpcr-assay-check.git
cd qpcr-assay-check
docker build -t qpcr-assay-check .

# write a starter assay/config into a host directory (bind-mounted as /work)
mkdir -p work
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/work:/work" qpcr-assay-check init my-assay --example

# a full run: give NCBI_EMAIL (required) and NCBI_API_KEY (optional); -y skips the confirmation
# prompt, which does not work in a non-interactive `docker run` without a TTY
docker run --rm --user "$(id -u):$(id -g)" -e NCBI_EMAIL="your.name@example.org" -v "$PWD/work:/work" \
  qpcr-assay-check run my-assay/assay.yaml -o results -y
```

Everything the container writes lands under the bind-mounted `/work` directory (`results/`,
and the NCBI cache if you point `ncbi.cache_dir` there too via `--config`); nothing persists
inside the container itself. The image's own default user is non-root (uid 1000, matching neither
root nor most host users), so a bind-mounted directory created or owned by a different user on the
host will not be writable from inside the container without one of: `--user "$(id -u):$(id -g)"`
(shown above -- runs the container as your own host user instead) or pre-creating the host
directory and `chown`-ing it to uid 1000 to match the image's default user. Pass `--qc-only` for a
network-free run, or omit `-y` and run with `-it` for an interactive confirmation prompt.

Built and run end to end (2026-09-22, on a Synology NAS, Docker running as root): correct version
string, `init`, `run --qc-only`, and a full network run against real NCBI all confirmed. That first
full run also found and led to fixing a real bug (the exclusivity tier had no exclusion for the
assay's own target taxid — see Limitations below and `docs/ARCHITECTURE.md`), then confirmed fixed
on a second live run.

## Quick start

```bash
# write a worked example and a fully commented default configuration
qpcr-assay-check init my-assay --example

# check the input files without running anything
qpcr-assay-check validate my-assay/assay.yaml

# oligo QC only, no network use (verdict covers QC alone; exit code 10 = WARN)
qpcr-assay-check run my-assay/assay.yaml --qc-only -o results

# a full run: sends the oligos to NCBI, asks first (still INCOMPLETE overall until
# yearly history exists, v1.0.0)
qpcr-assay-check run my-assay/assay.yaml -o results

# show exactly what a full run would send, without sending anything or needing credentials
qpcr-assay-check run my-assay/assay.yaml --dry-run
```

Each run writes `results/<assay>/<run-id>/` containing:

| File | Content |
|---|---|
| `report.html` | Self-contained evaluation record (no external requests) |
| `results.json` | Machine-readable results (`schema_version` 1) |
| `results.xlsx` | Workbook: summary, inputs, QC checks, off-target variants (grouped) and every off-target site, products, sections |
| `hits.tsv` | One row per assessed off-target site: alignment, mismatches, level, duplex Tm/ΔG (full `run` only, not `--qc-only`) |

### Specificity assessment (v0.3.0)

A full `run` sends the oligos to NCBI in tiers (intended target, near neighbours and exclusion
taxa, background taxa such as human), each restricted to its taxa, with short-oligo BLAST settings
(word size 7, E-value 1000, filtering off, reward 1 / penalty -3, gap costs 5/2, database
`core_nt`). For every hit that could plausibly reach a reportable level, it fetches the subject
window (`efetch`, padded for gaps) and semi-globally re-aligns the *whole* oligo, so mismatches
past BLAST's seed are not missed. Hits that provably cannot reach even a "warning" level (from
BLAST's own scoring bound) are not fetched, to keep a background-tier run to a practical number of
`efetch` calls; `scripts/validate_assessment.py` checks that bound against real NCBI hits.
To skip the human background search (it takes about an hour), set `search.background_taxids: []`
in a `--config` file. The search plan then warns, and the report's rationale states that
off-target binding to human DNA was not evaluated.
Forward/reverse hits on the same accession, facing each other within `specificity.max_amplicon_size`,
are paired into predicted products, and classified as likely detected / amplified but not detected /
primer-only depending on whether the probe also binds. Amplicon pairing only expands the *primary*
record of a BLAST hit group; sequences merged into one hit by core_nt (see below) are not.

Behaviour worth knowing:
- **Resumable**: if a run is interrupted (network, laptop closed, timeout), run the same command
  again. The request IDs (RIDs) are saved *before* polling starts; NCBI keeps results for about 36
  hours, after which a job is resubmitted automatically. A search NCBI has kept WAITING for 90
  minutes or more (`ncbi.resubmit_after_minutes`) is submitted anew, once per run;
  `--resubmit` does that at once for every unfinished search.
- **Polite**: at least 10 s between BLAST requests, at most one poll per RID per minute, your
  e-mail and the tool name on every request, and exponential backoff on errors.
- **Saturation is judged by relevance**: a full hit list only triggers a warning (exit code 10)
  if even its weakest hit still has at least `search.relevance.min_identical_bases` identical
  bases, meaning relevant hits may have been cut off.
- **Cached at different scopes**: BLAST results are reused only for `ncbi.blast_cache_ttl_days`
  (7), so next year's run never receives this year's answer. Fetched sequence windows are cached
  without expiry, keyed on accession and coordinates, because a published record's sequence does
  not change.
- Exit codes for `run`: 0 PASS, 10 WARN, 20 FAIL, 30 INCOMPLETE, 64 invalid input, 70 NCBI problem
  (resumable).

For just the raw BLAST hits without assessment (e.g. to inspect what a search alone returns), the
lower-level `search` command still exists and writes `results/<assay>/search-<hash>/hits.tsv` and
`search.json` (different columns from the `run` output above) plus `jobs.json`. Its own exit codes:
0 done, 10 done with a saturated hit list, 64 invalid input, 70 NCBI problem (resumable).

```bash
export NCBI_EMAIL="your.name@example.org"      # required by NCBI
qpcr-assay-check search my-assay/assay.yaml --dry-run   # show exactly what would be sent
qpcr-assay-check search my-assay/assay.yaml -o results   # asks before sending anything
```

### Variant summary: every genome assembly or Nucleotide record (v1.1.0)

The **variant summary** lumps the oligo sites on the intended target into unique sequence
variants, with a count, a percentage and the first and last release date of the assemblies that
carry each one: one table per oligo (forward/probe/reverse) and one for the whole fragment
(forward + probe + reverse on the same genome). Emerging variants show up as rows whose first
release date is recent.

By default (`variants.source: datasets`) it is built from **every genome assembly of the target
in NCBI Datasets**, complete and draft: current versions, atypical assemblies excluded, one copy
per GenBank/RefSeq pair. Each genome is downloaded, scanned for the reference amplicon (exact
16-base seeds along the amplicon, so a variant with mismatches in a primer is still found through
the unchanged stretches), and deleted; only the amplicon region and 50 bases of flank on each
side are kept. The oligos are then re-aligned end to end in that region. These are counts over all
assessed assemblies, not a sample. The report states per release year how many assemblies NCBI
lists and how many were assessed, how many had the region cut by a contig end, how many did not
contain the region at all (listed, to review), and how many carry more than one copy.

- **Budget:** at most `variants.max_assemblies_per_run` (default 20,000) new assemblies per run,
  newest release year first. A species with more assemblies (e.g. *E. coli*) is completed over
  several runs; the report says "incomplete" until then. Later runs only process new assemblies.
- **Keep the cache between runs.** The extracted regions live in the NCBI cache directory. In
  Docker, point it into the mounted folder, or every run starts again from zero:

  ```yaml
  ncbi:
    cache_dir: /work/cache
  ```

- **Needs the reference amplicon:** the assay's `reference_amplicon`, or a target `accession`
  in which both primers match exactly.
- **Genome assemblies only.** Sequences submitted without an assembly (single genes, amplicons)
  are not in this collection. For such targets use `variants.source: blast_partitioned`: every
  NCBI Nucleotide record of the target is listed (ESearch, newest year first, optionally narrowed
  with `variants.nucleotide_query`, e.g. `"25000:32000[SLEN]"` for near-complete SARS-CoV-2
  genomes). Records up to `variants.direct_scan_max_length` (200,000) bases are fetched and
  scanned directly, like the genome assemblies; longer ones are found by BLASTing the reference
  amplicon against lists of 100 records at a time, so no search can fill its hit list. At most
  `variants.blast_max_records_per_run` (2,000) records per run; a target with millions of records
  is covered newest first over many runs, and the report says how far it got.
  `variants.source: blast_hits` keeps the v1.0 behaviour (the target tier's own hits, biased
  toward perfect matches when the hit list is full, and the report says so).
- **Inclusivity** is built from the same assemblies, per release year, when this source is used.
- **Regions hidden by N** (low-coverage sequencing) are found with N-tolerant seeds and reported
  as masked, with examples; they are not counted as matches or variants. A region that is N from
  end to end (v1.1.1; live: SARS-CoV-2 records with 1,144 N over N1) is placed by the reference
  sequence on either side of the amplicon, taken once from the assay's `target.accession` and
  cached; without an accession it is still counted as not found.
- **Emerging variants:** the history section compares each run's variant tables with the
  previous run's and lists new variants, marked "emerging" when their first assembly was released
  after the previous run. A new variant with a primer 3'-end mismatch or 2+ mismatches makes the
  history section WARN.
- What is sent to NCBI: assembly listing requests and genome downloads (no oligo sequences).

### Exclusivity against a clinical organism list (v0.4.0)

A full `run` also resolves every organism name in a **clinical organism list** to an NCBI
taxonomy ID (Entrez Taxonomy, cached; never guessed — ambiguous or unresolved names are reported,
not silently dropped or picked at random) and searches it as its own **exclusivity** tier, exactly
like the near-neighbour and background tiers. The report gets a per-organism table (organism,
resolution, sites, best site, predicted product) and a species/genus/family breakdown of every
off-target hit across all tiers.

```bash
qpcr-assay-check init my-assay --example
# edit my-assay/config.yaml: organisms.list_file, or leave it null for the packaged starter list
qpcr-assay-check run my-assay/assay.yaml -o results
```

**Per-assay exclusivity panels.** A single global list applied to every assay is often the wrong
panel — an STI assay and a respiratory assay do not have the same near neighbours. Give an assay
its own panel with `exclusivity_organisms` in its `assay.yaml`:

```yaml
exclusivity_organisms:
  - Mycoplasma genitalium
  - Trichomonas vaginalis
  - Ureaplasma urealyticum
```

`organisms.source` in `config.yaml` decides which list a run actually uses:
- `assay` (the default): the assay's own `exclusivity_organisms` when it defines one; an assay
  that leaves it empty falls back to the global list below, so existing assays keep working
  unchanged until they opt in.
- `global`: always the list from `organisms.list_file` (or the packaged starter list), even for an
  assay that defines its own `exclusivity_organisms` — for a lab that wants one shared panel across
  every assay regardless of what individual assay files contain.

The report states which one a run actually used (an "Exclusivity list source" line in
`results.xlsx`'s Summary sheet, `exclusivity.source` in `results.json`, and a notice at the top of
the Exclusivity section in `report.html`), so this is never silently ambiguous after the fact.

For a broader reference when curating your own organism list, see
[`docs/clinical_pathogen_panels.md`](docs/clinical_pathogen_panels.md): human pathogens typically
detected by real-time PCR, grouped by syndromic panel (respiratory, GI, meningitis/encephalitis,
bloodstream infection, STI, and more). It is general reference material, not itself wired into the
tool — see its own disclaimer.

The packaged list (`organisms.list_file: null`) is `src/qpcr_assay_check/data/clinical_organisms.yaml`:
a small, hand-picked, **non-authoritative starting point** (sexually transmitted pathogens, atypical
pneumonia bacteria, *M. tuberculosis* complex and other mycobacteria, common respiratory/other
viruses, human background) that every laboratory must review and edit for its own assay panel —
give `organisms.list_file` your own file with the same `categories:`/`organisms:` structure to
replace it entirely.

Resolving organism names uses the network (Entrez Taxonomy) but never sends the oligo sequences, so
it runs automatically before the confirmation prompt without needing `--yes`; declining still sends
no sequences (see `--dry-run`, which shows the organism-list name count but resolves nothing, since
resolution needs `NCBI_EMAIL`).

If the organism list also happens to include the assay's own intended target — a respiratory panel
that lists SARS-CoV-2 alongside the other pathogens a SARS-CoV-2 assay is checked against, for
example — that entry is automatically excluded from the exclusivity search: searching for it there
could only ever find the assay's own perfect, intended match, not evidence of cross-reactivity. The
organism-list row is still shown (never silently dropped), marked as the assay's own target rather
than given a `0` sites / `none` result that would otherwise look identical to a genuinely clean
finding.

### Inclusivity across the intended target (v0.4.0)

A full `run` also gives a year-by-year trend of how well the oligos still match the intended
target: the "target" tier search every run already makes (perfect full-length hits or near enough)
is bucketed by each hit's own submission year afterwards (via ESummary), sampled deterministically
(evenly spread by accession, capped by `inclusivity.sample_per_window`, default 20/year over the
last `inclusivity.lookback_years`, default 10), and re-aligned over the full oligo length. The
report gets a per-oligo, per-year table (population size from an independent ESearch count, sample
size, perfect/1-mismatch/2+-mismatch/3'-mismatch counts, a per-position mismatch profile).

This is deliberately **not** a separate, date-restricted BLAST search: a live check found that
combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call does not
reliably restrict by date, so inclusivity reuses evidence the run already gathers instead (see
`docs/ARCHITECTURE.md`). One honest consequence: the yearly sample is whatever the target tier's own
BLAST hit list returned for that year, not a controlled random sample of everything sequenced that
year — `population_size` is always shown alongside `sample_size` so the two are never confused.
A target tier that was never searched, or a year with no dated hits, is INCOMPLETE for that scope
rather than a silent PASS.

### Run history and changes since the last run (v1.0.0)

Every full `run` looks for the most recently generated `results.json` under the same output
directory and assay name (`<outdir>/<assay-slug>/*/results.json`, sorted by the record's own
`generated_at`) and diffs the current evaluation against it: no separate index or database, just
the same per-run directories every version has already written. The report gets a "Changes since
the previous run" section: which section verdicts changed, which off-target sites or predicted
products are new or have disappeared, and how the inclusivity trend moved — matched across runs by
accession and position (not by the run-local site ID, which is only ever stable within one run).

The first run for a new assay has nothing to compare against, so this section is honestly
`INCOMPLETE` rather than silently skipped — the same "missing evidence is never a PASS" rule
applied everywhere else in this tool. From the second run onward it is a real `PASS` (nothing
concerning changed) or `WARN` (a section got worse, a new critical/warning site or predicted
product appeared, or inclusivity regressed for some oligo/year) — never `FAIL` by itself, since a
regression that is bad enough to fail the run already fails the specific section it belongs to
(specificity, exclusivity, inclusivity); "history" only flags that something changed and is worth a
human look.

```bash
# run the same assay again later; -o must point at the same output directory as before
qpcr-assay-check run my-assay/assay.yaml -o results
```

You can also define an assay entirely on the command line:

```bash
qpcr-assay-check run --qc-only --name "My assay" \
  --forward GACCCCAAAATCAGCGAAAT --reverse TCTGGTTACTGCCAGTTGAATCTG \
  --probe ACCCCGCATTACGTTTGGTGGACC --probe-reporter FAM --probe-quencher BHQ1 \
  --template-type RNA --target-taxid 2697049
```

Command-line options override values in the assay file.

## Assay file

**Template:** [`examples/assay_template.yaml`](examples/assay_template.yaml) (also written by
`qpcr-assay-check init`) is a compact assay file: one line per oligo and a short `settings:`
with only what differs from the defaults (see the N. gonorrhoeae example for a filled one). Below
it, a commented reference lists every other option with its default; copy a line into
`settings:` (same indentation) only when an assay needs another value. Tests check that the
reference's defaults are the real ones and that no option is missing.

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

### Several oligos per role, and oligo names (v1.3.0)

Some assays carry more than one forward primer, reverse primer or probe for the same target, when
lineages differ too much for a wobble base. Each role takes a plain sequence (as above; its name is
then the role), one named oligo, or a list of named oligos:

```yaml
forward: {name: NG-F, sequence: GTTGAAACACCGCCCGG}
reverse: {name: NG-R, sequence: CGGTTTGACCGGTTAAAAAAAGAT}
probe:
  - name: NG-P1
    sequence: CCCTTCAACATCAGTGAAA
    reporter: FAM          # optional per probe; else probe_reporter
    modifications: [MGB]   # optional per probe; else probe_modifications
  - name: NG-P2
    sequence: CTTTGAACCATCAGTGAAA
reference_amplicons:       # optional; one per lineage, or a single reference_amplicon
  - {name: lineage-1, sequence: ...}
  - {name: lineage-2, sequence: ...}
```

- Oligos of the same role are alternatives in the same reaction mix: for each record the
  best-binding one counts (fewest mismatches and gaps, then the cleanest 3' end). Probes with the
  same reporter are alternatives; probes with different reporters detect different regions.
- Names (letters, digits, `.`, `_`, `-`; unique; not ending in `_v` + a number, which labels
  degenerate variants) are used in the report, the workbook, `hits.tsv` and as BLAST query labels.
- QC checks every oligo, every dimer across the whole mix (including two alternatives), and the Tm
  spread of each role's alternatives. Each oligo is placed in the reference amplicon it fits best;
  an alternative that fits no reference is a warning when another oligo of its role fits.
- Specificity searches every oligo under its own name; predicted products pair any forward with
  any reverse primer. Variant tables name the alternative seen in each row.
- Multi-copy targets: every stored copy of the region is assessed with every oligo, and each
  genome is judged by the copy the assay binds best (a PCR needs one copy it can amplify). The
  report's "Copies, coverage per oligo, and escapes" table shows copies per genome, how many
  genomes each oligo covers (and covers alone), genomes no oligo of a role covers, probe channels
  (`variants.probe_channels: any | all`) and the escapes: genomes without any detectable copy
  (graded mismatch class perfect or tolerated; see below).
- **Graded mismatch classes** ([docs/MISMATCH_CLASSES.md](docs/MISMATCH_CLASSES.md)): every oligo
  site on the target is *perfect*, *tolerated*, *at risk*, *likely failure* or *indeterminate*.
  Primers follow two published studies read in full: single mismatches in the last 5 nt by type
  and position after Stadhouders et al. 2010 (Table 1, Taq polymerase on DNA), farther positions
  and the number of mismatches per primer and per primer pair after Lefever et al. 2013. Gaps and
  homopolymer bulges, ambiguity codes in the genome and mismatches in MGB probes are
  *indeterminate* (no published basis). Inclusivity counts perfect + tolerated as detectable. The
  size of a mismatch effect differs between master mixes; a wet-lab check decides.
- Homopolymer bulges (a site that differs only by the length of a single-base run, no mismatch)
  are **not** counted as detectable by default (strict). `variants.homopolymer_bulges_detectable:
  true` counts them; the report shows the genomes with a detectable copy under both rules either
  way, since only a wet-lab check can show whether such a site amplifies.
- Genomes stored before v1.3.0 kept at most 5 copies; they are downloaded and scanned again once
  (within the per-run maximum), so every copy (up to 20) is assessed.
- Further reference amplicons are tried when the first finds nothing (region store unchanged, so
  adding a lineage reference keeps the regions already stored).
- A site that differs only by the length of a single-base run (e.g. a poly-T of 9 instead of 7)
  is aligned as a bulge with the 3' end intact and labelled "homopolymer length variant", rather
  than shown as 3'-end mismatches. Homopolymer lengths are also a known sequencing-error hotspot.
- Worked example (user-supplied sequences):
  [`docs/examples/neisseria_gonorrhoeae_two_probes.yaml`](docs/examples/neisseria_gonorrhoeae_two_probes.yaml).

### Laboratory evidence per oligo variant

Where the tool has no published basis (a single mismatch in an MGB probe, a homopolymer length
difference in a primer site), a wet-lab test decides. Record the result in the assay file and
every genome with exactly that site variant takes it:

```yaml
evidence:
  - oligo: Entero-P
    variant: "........T........"   # copied from the report's "Variants per oligo" table
    outcome: detected               # detected | not_detected
    note: "RNA template, dilution series to the LoD, Ct +0.6; lab report QC-2026-014"
```

`detected` counts as tolerated, `not_detected` as likely failure (rule LAB); the in silico class
stays in the note. The report lists every entry with the number of records it was applied to,
and flags an entry that matched no site (usually a typo in the name or the variant).

### Taxa inside the target that are not the intended target

Some assays target a taxon but not all of it. An enterovirus assay for a human diagnostic lab must
not detect the rhinoviruses (which NCBI Taxonomy files inside the genus *Enterovirus*), and the
animal enteroviruses are simply not what it is for. List such taxa under `target.taxa`, each with
a role and a reason:

```yaml
target:
  taxid: 12059                                   # genus Enterovirus
  taxa:
    - {taxid: 3428501, role: must_not_detect, reason: "rhinovirus A"}
    - {taxid: 3428509, role: out_of_scope,    reason: "animal enterovirus (EV-G)"}
```

- Both roles are left out of the target search, inclusivity and the variant analysis (Entrez
  `NOT`), and **every oligo is still searched against them**.
- `must_not_detect`: searched as near neighbours; a predicted product there counts against the
  specificity verdict, as for any off-target organism.
- `out_of_scope`: searched in their own tier and listed as what the assay *also detects*,
  information only, not part of the verdict (e.g. a pan-enterovirus assay amplifying pig
  enteroviruses is expected, not a specificity failure for a human lab).
- `exclude_taxids: [..]` still works as the short form of `must_not_detect` taxa.
- Every such taxon must lie inside the target (checked against NCBI Taxonomy when the run
  starts): an ancestor would empty the target search and search the target as off-target.
- Give such taxa by ID. The name "rhinovirus" resolves to the genus *Enterovirus* itself in
  NCBI Taxonomy (the former genus name is a synonym), so it cannot be used as an organism name.
- Records of such organisms that NCBI files under another taxon (e.g. "unclassified
  Enterovirus") stay in the target; the report says so.
- Supported with `variants.source: blast_partitioned` (and `blast_hits`), not with `datasets`.
- Worked example (user-supplied sequences):
  [`docs/examples/enterovirus_realt.yaml`](docs/examples/enterovirus_realt.yaml).

### Panels: genomes that escape every target

Many laboratories detect one organism with two or more assays (e.g. *C. trachomatis* on the
cryptic plasmid and on a chromosomal gene). The clinical risk is a strain that escapes every
target at once. After each assay has run its variant analysis, combine them:

```yaml
# ct_panel.yaml (paths relative to this file)
panel_name: C. trachomatis two-target panel
assays:
  - ct_plasmid.yaml
  - ct_chromosome.yaml
```

```bash
qpcr-assay-check panel ct_panel.yaml -o results
```

- Reads the region stores the assays' runs already filled: nothing is sent to NCBI (except, once,
  to cut the amplicon out of a target accession for an assay without a reference amplicon).
- Each genome is judged per assay exactly as in that assay's report (best-binding copy, the
  inclusivity criterion, the assay's own homopolymer-bulge setting): detected, escape (region
  found but no detectable copy), region not found, or not assessable (hidden by N, cut by a
  contig end). Per genome: detected by every target, by some, by **no target** (no target
  detects it and at least one shows an escape), or undetermined (no target detects it, but no
  region is found or assessable: more often an incomplete assembly or a partial record). With
  Nucleotide records (`blast_partitioned`), "region not found" counts as not assessable, as a
  record is often another gene or a partial sequence.
- Only genomes processed by every assay are combined; the rest are counted. The assays must
  share the target taxon, its exclusions, the variant source and its record filters.
- Writes `panel.html` (genomes detected by no target first, per release year), `panel.xlsx`
  (every genome with its outcome per assay) and `panel.json`. Exit code 10 when at least one
  genome is detected by no target.

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

### Settings per assay (v1.3.0)

Everything specific to one assay belongs in the assay file itself, under `settings:`, with the same
structure as `config.yaml`; only what differs from the defaults needs writing:

```yaml
settings:
  reaction:
    annealing_temp_C: 60          # this assay's cycling protocol
  search:
    background_taxids: []         # skip the human background search
  variants:
    source: blast_partitioned     # a virus: Nucleotide records
    nucleotide_query: "25000:32000[SLEN]"
```

Order of precedence: built-in defaults, then a `--config` file (lab-wide), then the assay's
`settings:`. Allowed sections: `reaction`, `oligo`, `thresholds`, `search`, `specificity`,
`organisms`, `inclusivity`, `variants`. `ncbi` (servers, throttling, cache location) and `report`
stay lab-wide; the NCBI email and API key always come from environment variables. Unknown keys
are rejected, naming the assay file's settings. The report's Methods section lists the settings
that came from the assay file, and a change to them counts as an assay change in the run history
(run budgets such as `max_assemblies_per_run` excepted). So one file per assay:
`qpcr-assay-check run my_assay.yaml --yes`.

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

**Privacy note: `run` (unless given `--qc-only`) and `search` send the oligo sequences of the
assay to NCBI's public servers** for BLAST searches, and a full `run` also sends the resulting hit
accessions to NCBI's E-utilities to fetch sequence windows. This matters for proprietary assays.
Both commands always show the sequences and the planned searches first and ask for confirmation
(`--yes` skips the question; `--dry-run` sends nothing and needs no credentials). `run --qc-only`
and `validate` never use the network. A full `run` also sends the organism-list *names* (not the
oligo sequences) to Entrez Taxonomy to resolve them to taxonomy IDs; this runs automatically,
without its own confirmation, since it never sends anything proprietary (see
[Exclusivity](#exclusivity-against-a-clinical-organism-list-v040) above).

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

**Second live run (2026-09-22), v0.4.0 phase 4a additions:** entrez queries with 11, 40 and 100
taxids were all accepted (the true upper limit is still unknown, but 100 is a safe planning number);
taxonomy lineage parsing (species/genus/family) matched real output for all 5 sampled organisms; 38
of the 40 packaged organism-list names resolved through the real exclusivity-resolution path. One
important negative result: **combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter
in a single BLAST call does not reliably restrict by date** (4 of 20 checked hit accessions fell
outside the requested window) — this rules out this project's originally planned inclusivity
design; see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detail and the redesign it led to
(phase 4b, implemented: reuse the target tier's own search, bucket by date via ESummary afterwards).

**Third live run (2026-09-22), v0.4.0 phase 4b additions:** the renamed organism
`Mycoplasmoides pneumoniae` now resolves (39 of the 40 packaged organism-list names resolve; only
`Mycobacterium chelonae` remains unresolved). Inclusivity's own ESummary-based date lookup was
checked and works: `Eutils.esummary()`'s JSON shape matched a real response, the nuccore ESummary
docsum's date field is `createdate` (confirmed by extracting the correct year for two real
records), and NCBI does key the result by resolved UID rather than by the accession sent as input
(confirmed directly) — `fetch_years()` correctly recovers the right years despite this. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detail, including a smoke-test-script-only bug
this run uncovered and fixed (the shipped `inclusivity/dates.py` code was unaffected).

### Live validation of the specificity assessment (v0.3.0)

`scripts/validate_assessment.py` checks the pruning rules the specificity assessment relies on to
avoid fetching every hit (see [Specificity assessment](#specificity-assessment-v030) above) against
real NCBI hits, and reports how many `efetch` calls a real run makes:

```bash
export NCBI_EMAIL="your.name@example.org"
mkdir -p validation_out
nohup python scripts/validate_assessment.py > validation_out/run.log 2>&1 &
tail -f validation_out/run.log
```

Paste back `validation_out/validation_report.json` (no secrets). Exit code 0 means no rule was
contradicted in the sample; exit code 1 means at least one was, and the report lists the cases —
in that event the assessment's pruning must not be trusted until it is fixed. The default tier
(`--tier background`) reuses the same search as `run`, so it can take about an hour the first time
but is served from cache afterwards.

**First live run (2026-09-21, CDC N1 example, `--tier background`):** 905 relevant alignments, 244
ruled out without fetching, 661 needing a fetch (a real background-tier run for this assay makes
661 `efetch` calls — this replaces an earlier unmeasured "about 1,500" guess). Sample of 80 checked
(40 fetchable, 40 ruled out): **0 contradictions.** That covers one assay's background tier only —
re-run it (varying `--tier` and `--sample`) for other assays or tiers, and whenever the alignment or
pruning logic changes, rather than treating this one result as permanent proof.

## Limitations

- Thresholds are common-practice defaults, not acceptance criteria.
- Tm and dimer values are nearest-neighbour estimates. MGB/LNA/ZEN-type modifications are not
  modelled (a warning is raised).
- Structures are searched at the annealing temperature; one that forms only at lower temperatures
  may not be reported, and the same oligo can be flagged at one annealing temperature and not at
  another.
- The HTML report contains no JavaScript; its one chart (oligo Tm) is inline SVG, and the report
  makes no external requests. A test checks that no HTML tag loads another file or host; the only
  references are plain links from accessions and taxonomy IDs to their NCBI pages, opened on click.
- BLAST is a heuristic (exact 7-base seed): heavily mismatched binding sites can be missed, so "no
  hit" is not "no binding". Primer-BLAST and IDT OligoAnalyzer remain useful manual cross-checks.
- The remote client was validated against live NCBI once, for one assay; NCBI can change formats
  or behaviour, and a parse failure ends the run as an error rather than guessing.
- The re-alignment pruning rules (which hits can be skipped without fetching) follow from BLAST's
  documented scoring, and were checked live once (CDC N1, background tier, 0 contradictions in an
  80-hit sample; see [Live validation](#live-validation-of-the-specificity-assessment-v030) above) —
  one assay, one tier, a sample. Re-run `scripts/validate_assessment.py` for other assays or tiers
  before relying on a specificity verdict there.
- Amplicon pairing only expands the *primary* record of a BLAST hit group; core_nt merges identical
  sequences into one hit (observed: up to ~39 descriptions per hit), so a product on a merged
  record can be missed.
- Duplex Tm/ΔG for a mismatched site ignore a mismatch at the very 3' terminal base (treated as an
  unpaired overhang); priming risk is judged from the mismatch positions and clean-3'-nt count,
  never from Tm alone.
- Specificity covers only the tiers actually searched (intended target, near neighbours,
  background, exclusivity).
- `ENTREZ_QUERY` taxon restriction is effective, not airtight: one "synthetic construct" record
  leaked into 3,715 live human-restricted hits (it carries a human source feature).
- The clinical organism list ships as a small, hand-picked, non-authoritative starting point (see
  `src/qpcr_assay_check/data/clinical_organisms.yaml`'s own header); every laboratory must review
  and edit it, or supply its own file, before relying on the exclusivity report.
- Organism-name resolution never guesses: an ambiguous or unresolved name is reported and left out
  of the exclusivity search rather than picked at random. Review `results.json`'s
  `exclusivity.unresolved` (or the report's Exclusivity section) after every run. Checked live
  (2026-09-22): 39 of the 40 packaged organism-list names resolve; the `[All Names]` synonym
  fallback did not catch "Mycoplasma pneumoniae"'s scientific-name rename (fixed by renaming the
  entry directly to *Mycoplasmoides pneumoniae*, which itself now resolves live) — a name that
  stops resolving is a real possibility worth checking for after any NCBI Taxonomy update, not just
  a corner case. `Mycobacterium chelonae` remains unresolved (cause unknown).
- **Inclusivity's originally planned design does not work**: combining `ENTREZ_QUERY` taxon
  restriction with a `[PDAT]` date filter in one BLAST call does not reliably restrict by date
  (checked live, 2026-09-22: 4 of 20 checked hit accessions fell outside the requested window).
  Implemented instead: reuse the target tier's own search, bucket its hits into years afterwards
  via ESummary; this itself checked live for the common case (see `docs/ARCHITECTURE.md`).
- **Inclusivity's yearly sample is not a controlled random sample**: it comes from whatever the
  target-tier BLAST search's own hit list (capped) returned for that year, so a well-sequenced
  target can under- or over-represent some years depending on BLAST's own ranking. Reported
  honestly: `population_size` (an independent ESearch count) is always shown next to `sample_size`.
- **A first run for any assay always ends `INCOMPLETE` overall**, even when every other section
  passes: the new "history" section has no previous run to compare against yet, and missing
  evidence is never a PASS. From the second run onward for that same assay (same output directory,
  same assay name) it becomes a real comparison.
- **The previous run is found by assay slug, not by assay content**: renaming an assay (which
  changes its filesystem-safe slug) starts its history over with nothing to compare against, even
  if the oligos themselves did not change. Off-target sites and predicted products are matched
  across runs by accession and position, which is stable for the same physical binding site but
  will register as "new" if the *reference record itself* is revised to a new accession.version.
- **Docker's default user is non-root (uid 1000)**: a bind-mounted host directory not owned by
  that uid needs `--user "$(id -u):$(id -g)"` on `docker run` (or a `chown` to uid 1000
  beforehand), or `init`/`run` will fail with a permission error writing into it. Confirmed live
  (2026-09-22): the image builds, and `init`, `run --qc-only`, and a full network run against real
  NCBI all completed correctly through the container.
- **If the organism list also includes the assay's own target** (a respiratory panel listing
  SARS-CoV-2 alongside a SARS-CoV-2 assay's other targets, say), that entry is automatically
  excluded from the exclusivity search rather than reported as an off-target hit against itself —
  found and fixed from the user's first full live run, then confirmed fixed on a second live run
  (predicted off-target products dropped from 500 to 0). See "Exclusivity" above and
  `docs/ARCHITECTURE.md`.
