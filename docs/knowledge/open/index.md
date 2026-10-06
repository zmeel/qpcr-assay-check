# Open

Open items: review suggestions not taken up, checks still to do.

* [Check N. meningitidis record CP171264.1](cp171264-record-check.md) - A perfect 76-bp product with NG-P1 is predicted on this N. meningitidis record; is the record what it says it is?
* [Rerun the enterovirus assay](enterovirus-rerun.md) - The enterovirus run predates the MGB region rule, which can change its probe's single-mismatch genomes.
* [Analyse every locus of a multi-locus assay](every-locus.md) - Only the first locus is analysed; a multi-locus assay would be judged on one region.
* [Independent validation of the classes](independent-validation.md) - The Otwell comparison is calibration; independent data such as Knight 2025 or the GoPrime templates are needed.
* [Legionella example still has placeholders](legionella-example-sequences.md) - The repository's Legionella example has TODO sequences, while the user runs a complete file on the NAS.
* [CLAUDE.md says the licence is not chosen](license-note.md) - pyproject.toml and the old progress log say Apache-2.0; CLAUDE.md still says to ask before adding a licence.
* [Exact Tm of the mismatched duplex](mismatched-duplex-dtm.md) - Compute ΔTm on the actual mismatched duplex instead of the current estimate; check primer3's documentation first.
* [The divergent Neisseria genomes: checked, an assembly artefact](neisseria-divergent-genomes.md) - Checked 2026-10-06: about 1,500 draft genomes whose only assembled copy is a single-copy opa paralogue every genome carries; the tool counts them undetermined, which is right. One lead left.
* [R7 note and the pair flag at 4+ mismatches](r7-pair-flag.md) - Degenerate primers are only a note, and pairs with 4 or more mismatches in total are not flagged yet.
* [The 3'-most 16 nt window](sixteen-nt-window.md) - R3/R8 count mismatches within the 3'-most 16 nt, which the biologist calls an artefact of Lefever's 20-mers.
* [Check the encoded Stadhouders Table 1](stadhouders-table-check.md) - Compare the Table 1 cells encoded in oligo/grade.py with the printed table; needs the PDF.
* [Süss 2009 for unmodified probes](suss-2009.md) - The one source on single mismatches in unmodified probes could not be obtained.
* [Split taxon lists per tier, not per search](taxid-split-per-tier.md) - max_taxids_per_search 1 split every tier into many searches; a per-tier split is the proper fix.
* [One rule set for off-target sites](unified-off-target-rules.md) - Specificity uses its own mismatch heuristics instead of the graded classes; a per-tier amplicon BLAST is not built.
* [Wet-lab tests the reviews propose](wet-lab-tests.md) - Test variants the tool cannot judge from literature, e.g. NG-R on an A8 template, and record results as evidence entries.
* [Publish docs/wiki to the GitHub wiki](wiki-publication.md) - The session cannot reach the wiki repository; the user publishes the pages.
