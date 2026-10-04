---
type: Assay
title: Enterovirus (realT, in-house) RT-qPCR
description: In-house 5' UTR assay with two forward primers, a degenerate reverse primer and an MGB probe; human enteroviruses, not rhinoviruses.
resource: ../../examples/enterovirus_realt.yaml
tags: [assay, example, RNA, virus]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: assay-file
    resource: ../../examples/enterovirus_realt.yaml
    title: docs/examples/enterovirus_realt.yaml (provenance and checks in its header)
---

# Provenance

Sequences, names, dye and protocol supplied by the user on 2026-09-25; an in-house assay, not
checked against a publication or kit insert. The probe quencher was not given and is left
empty.[^assay-file]

# Design

| Role | Oligos |
|---|---|
| forward | realT-Entero-F1, realT-Entero-F2 (alternatives; F2 differs at positions 5-6) |
| reverse | realT-Entero-DHU-R (degenerate, 2 expansions) |
| probe | Entero-P, FAM, MGB (degenerate, 2 expansions) |

74-nt fragment in the 5' UTR; `template_type: RNA`; target genus Enterovirus (12059) without the
rhinoviruses (must not detect) and animal enteroviruses (out of scope), each excluded taxon with
a role and reason ([decision](../decisions/2026-09-25-human-enteroviruses-only.md)).
Context accession NC_001612.1 (RefSeq Enterovirus A), checked live 2026-09-30. Variant source:
partitioned remote BLAST over near-complete Nucleotide records (6,500-8,500 bases).

# What was checked

Oligo positions against the fragment, NCBI Taxonomy IDs for every excluded taxon, record counts
and that BLAST honours `NOT` in ENTREZ_QUERY, all live on 2026-09-25 (details in the file
header).[^assay-file] Latest complete run: [2026-09-30](../runs/enterovirus-2026-09-30.md).

[^assay-file]: docs/examples/enterovirus_realt.yaml (provenance and checks in its header)
