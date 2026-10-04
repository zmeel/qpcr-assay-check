---
type: Component
title: "Assay model and configuration"
description: "The assay file (oligos, loci, channels, target taxa, evidence, settings) and the layered configuration."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: code0
    resource: ../../../src/qpcr_assay_check/models.py
    title: "src/qpcr_assay_check/models.py"
  - id: code1
    resource: ../../../src/qpcr_assay_check/config.py
    title: "src/qpcr_assay_check/config.py"
  - id: code2
    resource: ../../../src/qpcr_assay_check/data/default_config.yaml
    title: "src/qpcr_assay_check/data/default_config.yaml"
  - id: code3
    resource: ../../../src/qpcr_assay_check/data/assay_template.yaml
    title: "src/qpcr_assay_check/data/assay_template.yaml"
---

# What it does

An assay is oligos (named, several per role, IUPAC codes, modifications such as MGB) ->
loci (primers, probes, reference fragments, optional context accession) -> channels (one per
reporter, each with its own target taxon). Older single-locus files load as one locus and one
channel per reporter. `target.taxa` lists excluded taxa with a role (must not detect, out of
scope) and a reason; `evidence:` holds laboratory results ([LAB](../rules/lab-evidence.md)).
Configuration: packaged defaults ([settings](../settings/index.md)), a `--config` file, then the
assay's own `settings:`. NCBI credentials never come from files
([decision](../decisions/2026-09-29-generic-assay-model.md)).

# Code

[`models.py`](../../../src/qpcr_assay_check/models.py), [`config.py`](../../../src/qpcr_assay_check/config.py), [`data/default_config.yaml`](../../../src/qpcr_assay_check/data/default_config.yaml), [`data/assay_template.yaml`](../../../src/qpcr_assay_check/data/assay_template.yaml)[^code0][^code1][^code2][^code3]

[^code0]: src/qpcr_assay_check/models.py
[^code1]: src/qpcr_assay_check/config.py
[^code2]: src/qpcr_assay_check/data/default_config.yaml
[^code3]: src/qpcr_assay_check/data/assay_template.yaml
