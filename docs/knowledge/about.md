---
type: Overview
title: About this bundle
description: What qpcr-assay-check is, how this knowledge bundle is organised and how far to trust it.
tags: [overview]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: okf
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    title: Open Knowledge Format v0.2 specification
  - id: spec
    resource: ../SPEC.md
    title: docs/SPEC.md (authoritative specification)
  - id: progress
    resource: sessions/index.md
    title: Session logs (formerly docs/PROGRESS.md)
---

# The tool

qpcr-assay-check re-evaluates a real-time PCR (TaqMan) assay in silico against public NCBI
data, once a year or whenever needed, and files the result as a versioned record: oligo quality
control, specificity by remote BLAST, and inclusivity from every genome assembly of the target
(the exhaustive variant analysis). The specification is authoritative.[^spec] In silico analysis
does not replace experimental validation, and the laboratory verifies the software within its
own quality system.

# This bundle

A knowledge bundle in the Open Knowledge Format v0.2:[^okf] markdown files with YAML
frontmatter, one concept per file, linked to each other and to the code and documents in this
repository. It gathers what the project knows and why: the grading rules and the papers they
rest on, the user's decisions, the example assays, the live runs, the NCBI behaviour the code
relies on, and what is still open.

- **Hand-written** concepts (`rules/`, `sources/`, `decisions/`, `assays/`, `runs/`, `ncbi/`,
  `components/`, `open/`, `status.md`) summarise and link; the documents they link to stay the full record.
  Each claim names its source; where a source was not checked, the concept says so.
- **Generated** concepts (`settings/`, `releases/`, every `index.md` and `log.md`) are written
  by `scripts/build_knowledge.py` from the configuration, `CHANGELOG.md` and the session pages; a
  test fails when they are out of date. Do not edit them by hand.
- **Sessions**: what each working session did, one page per session in `sessions/`, the former
  PROGRESS.md moved verbatim;[^progress] `log.md` lists them. [status.md](status.md) is the
  current state, read first. Before ending a session: update status.md and add a session page
  (`sessions/<date>-<nn>-<slug>.md`, `type: Session`, `session_date`, a "Related" list of the
  concepts it changed, and those concepts cite it in `sources`).

# Trust

Every hand-written concept starts as `status: draft` with no `verified` entry (OKF trust tier
"unverified"). When the user has read a concept and agrees with it, add
`verified: { by: human:zmeel, at: <date and time> }` and set `status: stable`. A concept that no
longer holds gets `status: deprecated` and a line saying what replaced it; it is not deleted.
Concepts about live data (`runs/`, `ncbi/`) carry `stale_after`: past that date, check again
before relying on them.

# Links

Links are relative, so they work on GitHub, in a checkout and in any markdown viewer. Links to
files outside the bundle (code, docs) point into this repository.

[^spec]: docs/SPEC.md (authoritative specification)
[^okf]: Open Knowledge Format v0.2 specification
[^progress]: Session logs (formerly docs/PROGRESS.md)
