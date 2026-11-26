---
type: Decision
title: "Oligo design can be carried over from an earlier record"
description: "A run can take its oligo design from the newest earlier record of the assay with the same oligos, reference amplicons, reaction conditions and limits; the status still counts, the record names its source, and with no match oligo design is evaluated."
tags: [decision, report, gui]
status: draft
decided_on: 2026-11-26
generated: { by: claude-code/agent, at: 2026-11-26T12:00:00Z }
sources:
  - id: code
    resource: ../../../src/qpcr_assay_check/pipeline.py
    title: "src/qpcr_assay_check/pipeline.py"
---

# Decision

The CLI option `--skip-oligo-design` and the GUI's **Evaluate oligo design** option (ticked by
default) make oligo design optional at the start of a run.

- **The source record.** The oligo design is taken from the newest earlier record of the assay,
  in the same results folder, whose oligos, reference amplicons, reaction conditions and oligo
  limits are the same. `oligo_design_hash` fingerprints these. It is computed from each
  record's own assay and configuration, so records made before this change can be used too.
- **It still counts.** The carried-over oligo design counts in the status, so HSV-1 keeps
  "Exceeds limit" for its primer Tm. The limits crossed stand in Part A, with the values and
  the limit.
- **The record names its source.**
  - `oligo_design_from` gives the run, date, version and commit.
  - The oligo-design row in Part A says where it came from.
  - Part B shows a notice in place of the QC tables.
  - The workbook (sheets "Oligo QC", "Structures") and results.json keep every check.
- **A chain of carry-overs** still names the record that evaluated it.
- **When oligo design is evaluated anyway:**
  - when no earlier record matches (the run log says so, and the GUI's plan page says it
    beforehand);
  - always with `--qc-only`, where the option is refused, because a QC-only run is the oligo
    design.

# Who and why

The user, 2026-11-26: "Make Oligo design optional at start (also in GUI). After the first run
oligo design is known and therefore not to be repeated in each run." Of three choices put to the
user, they chose this one: carry the earlier result over. The other two were to leave it out of
the status, or to compute it and show one line.
