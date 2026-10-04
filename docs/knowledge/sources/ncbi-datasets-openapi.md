---
type: Reference
title: NCBI Datasets v2 OpenAPI specification
description: NCBI's published OpenAPI spec for Datasets v2, the source of the endpoints and parameters the genome download uses.
resource: https://raw.githubusercontent.com/ncbi/datasets/master/datasets.openapi.yaml
tags: [ncbi, datasets, documentation]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: openapi
    resource: https://raw.githubusercontent.com/ncbi/datasets/master/datasets.openapi.yaml
    title: datasets.openapi.yaml (API v2)
    author: team:ncbi
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, v1.1.0 and store v2 sections
---

# What we use from it

Endpoints and parameters of Datasets v2 (`dataset_report`, `download`, `sequence_reports`),
read 2026-09-23;[^openapi] behaviour measured live on top of it is in
[Datasets v2 facts](../ncbi/datasets-v2.md).[^arch] The spec states no rate limit; the live
response header with an API key read `X-Ratelimit-Limit: 10`.

[^openapi]: datasets.openapi.yaml (API v2)
[^arch]: docs/ARCHITECTURE.md, v1.1.0 and store v2 sections
