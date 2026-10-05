---
type: Assay
title: Entamoeba histolytica, SSU rRNA (one FAM-MGB probe)
description: One primer pair and an MGB probe in the 18S rRNA gene; variants from about 2,345 Nucleotide rRNA records because only 13 genome assemblies exist.
resource: ../../examples/entamoeba_histolytica_ssu.yaml
tags: [assay, example, DNA, parasite]
status: draft
generated: { by: claude-code/agent, at: 2026-10-05T08:30:00Z }
sources:
  - id: assay-file
    resource: ../../examples/entamoeba_histolytica_ssu.yaml
    title: docs/examples/entamoeba_histolytica_ssu.yaml (provenance and checks in its header)
  - id: session
    resource: ../sessions/2026-10-05-01-entamoeba-histolytica-assay.md
    title: "Session 2026-10-05: Entamoeba histolytica assay"
---

# Provenance

Sequences, probe label (FAM-...-MGB), fragment and exclusivity organisms supplied by the user on
2026-10-05; not checked against a publication or kit insert. Oligo names are placeholders; the
quencher was not given.[^assay-file]

# Design

| Role | Oligo | Position in the 173-nt fragment |
|---|---|---|
| forward | Eh-F (22 nt) | 1-22 |
| probe | Eh-P (22 nt, FAM, MGB) | 44-65, same strand |
| reverse | Eh-R (20 nt) | binds 154-173 |

Target E. histolytica (5759); reference record X64142.1 (SSU rRNA gene, HM-1:IMSS), which holds
the fragment exactly. Exclusivity, as supplied: E. dispar, E. coli, E. bangladeshi,
E. hartmanni, E. polecki, E. gingivalis (all checked in NCBI Taxonomy). Template DNA (not stated
by the user).

# Variant source (to confirm by the user)

Chosen in this session, not by the user: Nucleotide records (`blast_partitioned`) filtered to
rRNA records (2,345 on 2026-10-05), because NCBI has only 13 current assemblies (below the 100
genomes the [inclusivity status](../rules/inclusivity-status.md) needs) and the rRNA genes sit on
a multi-copy episome. Records whose title names none of the filter words are not
assessed.[^session]

# QC-only run (2026-10-05, no NCBI)

Review: the probe's model Tm is 4.8 C below the primers (expected for an MGB probe, whose
modification the model does not include), one more G than C in the probe, amplicon 173 bp and GC
34.1% outside the preferred ranges. The full run has not been made.

[^assay-file]: docs/examples/entamoeba_histolytica_ssu.yaml (provenance and checks in its header)
[^session]: Session 2026-10-05: Entamoeba histolytica assay
