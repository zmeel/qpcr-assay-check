---
type: Session
title: "Visualisation examples (not built)"
description: "Session log of 2026-10-02."
tags: [session]
session_date: 2026-10-02
session_label: "2026-10-02"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-02: Visualisation examples (not built)

- Mock-ups published as artifacts (data from the reports, nothing built in the tool): variant
  landscape views (Legionella), site pattern maps (PCoA of oligo-site combinations; Legionella and
  Neisseria). Assessment given to the user: the site map is exploratory only (every position
  weighs the same, few points); the whole-amplicon map is the meaningful version.
- scripts/export_amplicons.py: reads one genome store read-only, judges every genome with the
  package's own functions (no NCBI request) and writes the distinct best-copy amplicons with
  genome counts, outcomes, organisms, levels and collection years, for the whole-amplicon map.
  tests/test_export_amplicons.py (the store stays byte-identical, no file added).
- Whole-amplicon map for Neisseria made from the export (51,545 genomes, 167 distinct 76 bp
  amplicons): T8-T10 runs occur on all three common backgrounds (recurrent, not one lineage);
  27 divergent amplicons in 1,496 genomes, mostly possibly unassembled (worth checking).
- User, 2026-10-03: "For now no graph of the variants. Remove code": export_amplicons.py and its
  test removed (they were merged in PR #69). The artifacts stay as examples only.

# Related

* [No graph of the variants for now](../decisions/2026-10-03-no-variant-graph.md)
* [Check the 1,496 divergent Neisseria genomes](../open/neisseria-divergent-genomes.md)
