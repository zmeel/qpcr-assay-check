---
type: Session
title: "Threshold hides divergent Legionella species; next: overhaul with advisor"
description: "Session log of 2026-09-28 (end)."
tags: [session]
session_date: 2026-09-28
session_label: "2026-09-28 (end)"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-28 (end): Threshold hides divergent Legionella species; next: overhaul with advisor

- Legionella rerun on #30 code: the copy-identity threshold (0.75 vs the L. pneumophila reference
  fragment) set aside real copies of other species as "related regions, not the target" (201
  genomes, e.g. L. longbeachae GCF_000176095.1, L. dumoffii GCF_000236165.1). The L. longbeachae
  (49) and L. dumoffii rows vanished from "Needs attention"; target detection read 95.6% "No
  flags": too optimistic, do not rely on it. Measured live (genomes deleted afterwards): real
  L. longbeachae copies identity 0.74 (9 exact seeds) and 0.63 (6), L. dumoffii 0.59-0.74
  (6 seeds), chance regions 0.57 (1 seed). Minimal fix (not built): a copy when identity >= 0.75
  OR >= 3 exact seeds.
- USER DECISION for the next session: consult the advisor on a total overhaul of the code to
  make the solutions built during development more robust. Deleting the cache and starting over
  (re-downloading every genome) is always allowed if that is best for the tool. Ideas to put to
  the advisor: find copies by homology (several chained seeds) instead of one exact seed; store
  per copy its true offset, contig edge / adjacent N-run and contig lengths, and all copies with
  their identity at scan time; build a reference fragment per species automatically for genus
  assays (e.g. Legionella) from complete genomes; then revisit "possibly unassembled", "detectable
  from parts", the identity threshold and the per-channel probes on that richer data.
- Also to discuss (user): every fix of the past week that could be done better with all data
  downloaded again, among them: region hidden by N (partly via N-tolerant seeds, wholly via the
  reference context, v1.1.1); target on a plasmid judged from FASTA descriptions; copies capped
  at 5 then 20 per genome and rescans (copies_capped, refs_checked, needs_rescan); cut by a contig
  end (contig_break) and its clamped offsets; failed downloads counted unavailable after 2 tries;
  best-binding copy per genome; homopolymer run-length variants and their per-level breakdown;
  "possibly unassembled" (inferred from copy counts, no gap data stored); "detectable from parts";
  the copy-identity threshold and the multi-reference fall-through; per-channel probe sites.
