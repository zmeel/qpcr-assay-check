---
type: Component
title: "Scripts"
description: "Helper scripts for live checks, Docker runs, run summaries and this bundle."
tags: [component]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: scripts
    resource: ../../../scripts/
    title: "scripts/"
---

# What it does

- `scripts/smoke_test.py` / `run_smoke.sh`: live NCBI checks the user runs locally and pastes
  back (e.g. the E-value sweep).
- `scripts/run_assay.sh`: a full run in Docker in the background, with the checkout's `src/`
  mounted; `scripts/run_summary.py`: a compact summary of a results.json to paste back.
- `scripts/check_blast_stats.py`, `measure_borderline.py`, `probe_variant_sources.py`,
  `validate_assessment.py`, `resolve_pathogen_panel_taxids.py`: one-off checks behind recorded
  facts.
- `scripts/build_knowledge.py`: writes the generated parts of this bundle.

# Code

[`scripts/`](../../../scripts/)[^scripts]

[^scripts]: scripts/
