---
type: Assay
title: Legionella genus + L. pneumophila
description: One primer pair on the 23S-5S spacer with a genus probe (VIC) and an L. pneumophila probe (FAM); the example in the repository is a draft with placeholders.
resource: ../../examples/legionella_genus_pneumophila.yaml
tags: [assay, example, DNA, bacterium, multiplex]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: assay-file
    resource: ../../examples/legionella_genus_pneumophila.yaml
    title: docs/examples/legionella_genus_pneumophila.yaml (draft; provenance and checks in its header)
  - id: herpers
    resource: ../sources/herpers-2003.md
    title: Herpers et al. 2003
  - id: progress
    resource: ../sessions/2026-09-27-01-summary-instead-of-a-verdict-v1-5-0-released-legionella.md
    title: "Session 2026-09-27: Summary instead of a verdict; v1.5.0 released; Legionella draft"
---

# Provenance

The assay of Herpers et al. 2003 (23S-5S spacer).[^herpers] The user runs it with their own assay
file on the NAS (oligo names LEGgenus and LEGpneu in the run logs).[^progress] **The file in this
repository is a draft:** primer, probe and fragment sequences are placeholders, so `validate`
rejects it on purpose; nothing in it was invented.[^assay-file]

# Design

One locus (23S-5S spacer), context accession NC_002942.5 (L. pneumophila Philadelphia 1). Two
channels: the genus probe (VIC) for Legionellaceae (444, so that L. dumoffii and L. gormanii,
filed under Fluoribacter, are inside), the L. pneumophila probe (FAM) for taxid 446. Exclusivity:
Coxiella burnetii, Rickettsiella, Aquicella ([decision](../decisions/2026-09-29-generic-assay-model.md)).

# What was checked

NCBI Taxonomy IDs for the family, genera and exclusivity organisms (live, 2026-09-27); the
context accession (2026-09-29).[^assay-file] Runs: [2026-10-02](../runs/legionella-2026-10-02.md).
To do: put the real sequences into the example, or say why not
([open](../open/legionella-example-sequences.md)).

[^assay-file]: docs/examples/legionella_genus_pneumophila.yaml (draft; provenance and checks in its header)
[^herpers]: Herpers et al. 2003
[^progress]: Session 2026-09-27: Summary instead of a verdict; v1.5.0 released; Legionella draft
