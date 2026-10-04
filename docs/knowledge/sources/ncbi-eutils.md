---
type: Reference
title: NCBI E-utilities documentation
description: Entrez Programming Utilities - ESearch, ESummary, EFetch and their usage rules.
resource: https://www.ncbi.nlm.nih.gov/books/NBK25497/
tags: [ncbi, eutils, documentation]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: eutils
    resource: https://www.ncbi.nlm.nih.gov/books/NBK25497/
    title: Entrez Programming Utilities Help (NCBI Bookshelf NBK25497, the URL the code already cites)
    author: team:ncbi
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, NCBI facts
---

# What we use from it

Request limits (3 per second without an API key, 10 with one), the `tool` and `email`
parameters, and the ESearch, ESummary and EFetch calls.[^eutils] What the code relies on and what
was measured live: [E-utilities facts](../ncbi/eutils.md).[^arch]

[^eutils]: Entrez Programming Utilities Help (NCBI Bookshelf NBK25497, the URL the code already cites)
[^arch]: docs/ARCHITECTURE.md, NCBI facts
