# Components

What each part of the code does, with links to the source.

* [Assay model and configuration](assay-model.md) - The assay file (oligos, loci, channels, target taxa, evidence, settings) and the layered configuration.
* [Chain locator](chain-locator.md) - Finds every copy of a locus in a genome by chains of exact co-linear blocks, with context flanks.
* [Command line](cli.md) - The commands validate, run, init, search and gui (set-password, serve); exit codes are flag levels.
* [Exhaustive variant analysis and inclusivity](exhaustive-analysis.md) - Grades every genome's copies, decides each genome's outcome and builds the whole-fragment and channel statuses.
* [Genome store](genome-store.md) - Store v2 - every candidate copy of one locus per genome, incremental, with a schema/key header.
* [Site grading](grading.md) - Graded mismatch classes for one oligo site, rule by rule, with the rule and source in the note.
* [Browser interface](gui.md) - FastAPI app for one user - assays with live validation, confirmed runs in a queue, results, settings.
* [NCBI client](ncbi-client.md) - BLAST URL API and E-utilities with throttling, backoff, caching and resumable jobs.
* [Oligo quality control](oligo-qc.md) - Length, GC, Tm, 3' end, runs, hairpins and dimers per oligo and across the mix, against PASS/WARN/FAIL bands.
* [Report and records](report.md) - Self-contained HTML report, Excel workbook, results.json and hits.tsv per run.
* [Scripts](scripts.md) - Helper scripts for live checks, Docker runs, run summaries and this bundle.
* [Specificity search and assessment](specificity.md) - Plans remote BLAST tiers, re-aligns hits over the whole oligo, pairs products, scans for partners and rolls up by taxon.
