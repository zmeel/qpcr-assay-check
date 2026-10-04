---
type: NCBI Fact
title: NCBI Datasets v2 - what the code relies on
description: dataset_report paging, GCA/GCF duplicates, genome downloads, hydrated fetch, and sequence_reports with roles, one assembly per request.
tags: [ncbi, datasets]
status: draft
stale_after: 2027-04-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: openapi
    resource: ../sources/ncbi-datasets-openapi.md
    title: NCBI Datasets v2 OpenAPI specification
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, v1.1.0 design and store v2 sections
---

# From the OpenAPI spec, measured live (2026-09-23, API key set)

- `/genome/taxon/{name}/dataset_report` accepts scientific names; `page_size` up to 1000,
  `page_token`, `total_count`; `filters.assembly_version` defaults to current.[^openapi]
- Report keys used: `accession`, `paired_accession`, `assembly_info.release_date`,
  `assembly_info.assembly_level` (Chromosome, Complete Genome, Contig, Scaffold),
  `assembly_info.biosample.collection_date` (e.g. "missing"). GCA and GCF copies of one assembly
  are both listed: de-duplicate before counting.[^arch]
- `/genome/accession/{acc}/download?include_annotation_type=GENOME_FASTA`: a zip with the
  genomic FASTA; at most 100 accessions per request (the code uses 20).
- `hydrated=DATA_REPORT_ONLY` gives `fetch.txt` with direct URLs to plain FASTA.

# Store v2 (2026-09-29, no API key)

`/genome/accession/{acc}/sequence_reports` gives `role`, `assigned_molecule_location_type`
(Chromosome, Plasmid), `chr_name`, `length` and paging with `next_page_token`. One assembly per
request: a comma-separated pair returned an empty object.[^arch]

Genome downloads are allowed by the hard rules for the exhaustive analysis; only the extracted
target regions are kept, never a genome database.

[^openapi]: NCBI Datasets v2 OpenAPI specification
[^arch]: docs/ARCHITECTURE.md, v1.1.0 design and store v2 sections
