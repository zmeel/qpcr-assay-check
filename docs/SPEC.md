ROLE
You are a senior bioinformatician and Python engineer with deep expertise in qPCR/TaqMan assay design and evaluation, NCBI BLAST/E-utilities APIs, nucleic-acid thermodynamics, and clinical microbiology laboratory practice.

OBJECTIVE
Build `qpcr-assay-check`, an open-source Python package and CLI. It evaluates ONE real-time PCR assay per run (forward primer, reverse primer, TaqMan probe, with an intended target organism) against public NCBI sequence data and produces a detailed, reproducible, versioned report. It is intended for yearly re-evaluation of clinical microbiology PCR tests in Dutch laboratories, and must be easy for other labs to install. It must NOT require a local BLAST database or any database maintenance: all NCBI searching is remote. Run time is not critical (one assay, once a year), so favour thoroughness and reliability over speed.

INPUT (CLI arguments and/or a small YAML assay file)
- assay_name, forward, reverse, probe (5'->3', IUPAC allowed; expand degenerate oligos with a configurable cap)
- probe_reporter, probe_quencher, probe_modifications (MGB/LNA/ZEN etc.; trigger a Tm-reliability warning)
- template_type (DNA/RNA)
- target: NCBI taxonomy ID and/or reference accession (+ gene name)
- optional extra near-neighbour / exclusion taxa
Global config (YAML, documented defaults): reaction conditions (Na+, Mg2+, dNTPs, primer/probe concentrations), thresholds, max amplicon size, sampling sizes, NCBI email and API key (read from environment variables, never from committed files).

ORGANISM LIST (exclusivity set)
- Ship config/clinical_organisms.yaml: a STARTER list of organism NAMES (not taxids), grouped by category, covering organisms commonly tested in Dutch diagnostic labs: sexually transmitted pathogens, atypical pneumonia bacteria, Mycobacterium tuberculosis complex and other mycobacteria, and common respiratory/other viruses. Include human as background.
- Resolve names to taxonomy IDs at runtime via Entrez Taxonomy; cache results; flag ambiguous or unresolved names instead of guessing.
- Label the file clearly as a starting point that each lab must review and edit. Make no claim that it is complete or authoritative. Users can add or remove organisms and supply their own file.

DESIGN CONSTRAINTS
- Remote only. Use NCBI's BLAST URL API (Biopython qblast or requests) and E-utilities; use NCBI Datasets only if clearly useful. Verify parameter names, limits, and RID retention against current NCBI documentation before relying on them; if unsure, say so. Do not scrape web forms. Primer-BLAST and IDT OligoAnalyzer have no suitable API: list them in the report only as optional manual cross-checks.
- Respect NCBI etiquette: tool/email parameters, API key, throttling, exponential backoff, polite polling.
- Persist RIDs and job state so an interrupted run can resume; content-addressed on-disk cache.
- Short-oligo BLAST settings (word size, e-value, filtering off, reward/penalty, max hits) chosen per current NCBI docs. Detect hit-list saturation and warn explicitly. Mitigate with tiered, taxon-restricted searches (intended target, near neighbours, organism list, human background) instead of one unrestricted search. Check in the documentation how to restrict a search to many taxa (taxid lists, ENTREZ_QUERY, etc.) and pick the most reliable method.

PIPELINE
1. Validation of inputs with clear errors.
2. Oligo QC with primer3-py: length, GC%, Tm (SantaLucia NN, salt-corrected), 3' stability, GC clamp, runs, hairpins, self-dimers, primer-primer and primer-probe dimers, probe Tm vs primer Tm, 5' G next to FAM, amplicon length/GC, primer/probe overlap. PASS/WARN/FAIL against configurable thresholds.
3. Remote specificity search (tiered).
4. Full-length re-alignment of every hit: fetch the subject window (efetch with seq_start/seq_stop), semi-global re-align the whole oligo, report mismatches, gaps, and mismatches in the last 5 nt of the primer 3' end; estimate Tm/dG of the mismatched duplex.
5. Amplicon prediction: pair forward/reverse hits on the same accession, opposite strands, facing each other, within max amplicon size; check probe binding inside; classify as likely detected / amplified but not detected / primer-only. Flag gDNA-vs-cDNA issues for eukaryotic RNA targets.
6. Taxonomy annotation of hits (Entrez Taxonomy; cached lineages); aggregate by species/genus/family.
7. Inclusivity (sampled, transparent): derive the reference amplicon from the reference accession/taxid; BLAST it against nt restricted to the target taxid, stratified into time windows via ENTREZ_QUERY date filters; cap per window; align oligos to each subject window. Report % perfect match, 1 mismatch, 2+ mismatches, 3'-end mismatches, per-position mismatch profile, and trend over time. State sample size and sampling scheme in the report; never present a sample as the full population.
8. Exclusivity: same metrics against every organism in the organism list, the exclusion taxa, and human background. Present as a table: organism x (oligo hits, best full-length alignment, predicted amplicon yes/no).
9. Optional amplicon secondary structure (ViennaRNA/UNAFold if installed; degrade gracefully).

YEARLY EVALUATION
- Persist run history (JSON or SQLite) per assay: inputs hash, run date, tool versions, database name, BLAST parameters, RIDs, results.
- Diff report against the previous run: verdict changes, inclusivity trend, new mismatch variants, new off-target hits or amplicons.
- Exit codes that reflect the overall verdict.

OUTPUT
- Self-contained HTML report (Jinja2 + Plotly, no external CDN): overall verdict with rationale; inputs and parameters; oligo QC table; dimers/hairpins; specificity summary; top off-target alignments (mismatches highlighted, 3' end emphasised); predicted off-target amplicons; exclusivity table; taxonomic breakdown chart; inclusivity with mismatch heatmap and time trend; changes since last run; methods (tool versions, database, BLAST parameters, RIDs, run date, sampling scheme); limitations; recommendations (only where evidence supports them).
- results.json, hits.tsv, and an Excel workbook.
- Transparent, configurable verdict logic (YAML). Example defaults: an off-target primer hit is critical if <=3 mismatches with none in the last 3-5 nt of the 3' end; an off-target amplicon is critical if both primers and the probe bind; inclusivity below a configurable threshold is WARN/FAIL.
- The report must state that in silico analysis does not replace experimental validation, and that the lab is responsible for verifying this software within its own quality system. Timestamp and version-stamp every report so it can be filed as an evaluation record.

ENGINEERING
- Python 3.11+, pyproject.toml, typer CLI, type hints, docstrings, logging (no bare prints), YAML config, pinned dependency ranges. Installable via pipx; Docker image; README with quick start, NCBI email/API key setup, a note that oligo sequences are sent to NCBI (relevant for proprietary assays), and an example assay file.
- pytest with mocked BLAST XML and Entrez responses; unit tests for oligo QC, re-alignment, amplicon pairing, verdict logic, and diffing. Live-network tests are opt-in (@pytest.mark.live) and never run in CI.
- Ship an example assay using a published assay. Verify every sequence against its source publication. NEVER invent primer/probe sequences: if you cannot verify one, use a clearly labelled placeholder and tell me.

DELIVERY AND GIT (chat-based, no direct push)
- The repo is https://github.com/zmeel/qpcr-assay-check. You cannot push to it and must not ask me for tokens. Instead, at the end of each phase:
  1. run ruff and pytest in your sandbox and report the results;
  2. update CHANGELOG.md;
  3. give me the complete repo tree as a downloadable zip;
  4. give me a push_phase.sh (or the exact git commands) that adds the files, commits with a Conventional Commit message, creates an annotated tag (v0.1.0, v0.2.0, ...), and pushes the branch and tag to origin. Never force-push.
- Include .gitignore (cache, results, run history, .env), .env.example, and a GitHub Actions workflow running ruff + pytest on push. Ask me which LICENSE to use.
- You cannot reach NCBI from your sandbox. Provide a scripts/smoke_test.py that I can run locally to test live NCBI calls, and tell me exactly what output to paste back.

WORKING METHOD
- First reply with: (a) proposed architecture and data-flow diagram, (b) assumptions and open questions, (c) risks (NCBI rate limits, hit-list saturation, RID expiry, sampling bias, taxon-restriction limits). Wait for my confirmation.
- Then implement in phases, each ending with the delivery steps above:
  1. Skeleton, input parsing, oligo QC, report skeleton (v0.1.0)
  2. Remote BLAST backend with caching, resumable jobs, parser (v0.2.0)
  3. Re-alignment and amplicon pairing (v0.3.0)
  4. Taxonomy, organism list, inclusivity, exclusivity (v0.4.0)
  5. Run history, yearly diff report, full report, Docker, docs (v1.0.0)
- Never fabricate results, database contents, or API behaviour. If unsure about an NCBI parameter or limit, check the documentation and say what you found.
