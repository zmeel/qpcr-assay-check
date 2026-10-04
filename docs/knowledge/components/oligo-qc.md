---
type: Component
title: "Oligo quality control"
description: "Length, GC, Tm, 3' end, runs, hairpins and dimers per oligo and across the mix, against PASS/WARN/FAIL bands."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/oligo/qc.py
    title: "src/qpcr_assay_check/oligo/qc.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/oligo/thermo.py
    title: "src/qpcr_assay_check/oligo/thermo.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/oligo/iupac.py
    title: "src/qpcr_assay_check/oligo/iupac.py"
  - id: code3
    resource: ../../../src/qpcr_assay_check/oligo/amplicon.py
    title: "src/qpcr_assay_check/oligo/amplicon.py"
---

# What it does

primer3-py (SantaLucia nearest-neighbour, salt-corrected) for Tm, hairpins and dimers;
every degenerate expansion is evaluated and the worst decides. The reference amplicon locates
the oligos and checks orientation, length, GC and probe position. Thresholds are starting
points ([thresholds](../settings/thresholds.md), [reaction](../settings/reaction.md)); the report
labels them within / outside preferred / outside limit.

# Code

[`oligo/qc.py`](../../../src/qpcr_assay_check/oligo/qc.py), [`oligo/thermo.py`](../../../src/qpcr_assay_check/oligo/thermo.py), [`oligo/iupac.py`](../../../src/qpcr_assay_check/oligo/iupac.py), [`oligo/amplicon.py`](../../../src/qpcr_assay_check/oligo/amplicon.py)[^code0][^code1][^code2][^code3]

[^code0]: src/qpcr_assay_check/oligo/qc.py
[^code1]: src/qpcr_assay_check/oligo/thermo.py
[^code2]: src/qpcr_assay_check/oligo/iupac.py
[^code3]: src/qpcr_assay_check/oligo/amplicon.py
