---
type: Grading Rule
title: LAB - laboratory evidence
description: An evidence entry in the assay file replaces the in silico class of one exact variant with the laboratory's result.
tags: [grading, evidence, LAB]
status: stable
verified: { by: human:zmeel, at: 2026-10-05T16:04:00Z }
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, LAB
---

# Rule

An `evidence:` entry in the assay file (oligo name, the site exactly as the report writes it,
outcome `detected` or `not_detected`, and the laboratory's reference) replaces the in silico
class of every site of that oligo with exactly that variant: detected is `tolerated`, not
detected is `likely_failure`; the in silico class stays in the note. Meant for single MGB probe
mismatches ([R9](r9-probes.md)) and homopolymer bulges ([R5b](r5b-homopolymer-length.md)), where
no published data exist. An entry that matches no site is flagged.[^mismatch-classes] None of the
example assays has entries yet (user, 2026-09-30, for Neisseria).

[^mismatch-classes]: docs/MISMATCH_CLASSES.md, LAB
