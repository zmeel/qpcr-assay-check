---
type: Session
title: "Giardia lamblia assay file, and a reference sequence that was not one"
description: "Session log of 2026-10-09."
tags: [session]
session_date: 2026-10-09
session_label: "2026-10-09"
generated: { by: claude-code/agent, at: 2026-10-09T09:00:00Z }
---

# 2026-10-09: Giardia lamblia

- User supplied the Giardia channel of the Verweij 2004 faecal multiplex (forward, reverse, a
  FAM/BHQ1 probe, a 56-nt "reference sequence") and asked for exclusion suggestions. Added as
  [docs/examples/giardia_lamblia_ssu.yaml](../../examples/giardia_lamblia_ssu.yaml).
- **The supplied reference sequence was the three oligos concatenated**, not an amplicon: the
  real template has a 6-nt spacer (GCACCC) between the forward primer and the probe and one C
  between the probe and the reverse site, so the product is 63 bp and not 56. Checked live: of 60
  G. duodenalis SSU rRNA records sampled, 55 carry the probe and 41 carry the whole 63-nt
  amplicon exactly (37 with G at the primer's degenerate R, 4 with A); none carries the 56-nt
  form. The file takes the real amplicon in both forms as its references, each named after a
  record that holds it, and the header records what was supplied and why it was not used. A
  stitched reference would have been worse than useless, because the region is located by exact
  16-base seeds and every seed across one of its two junctions matches nothing.
- Checked live as well: the gene is SSU (18S) rRNA, not beta-giardin/gdh/tpi; NCBI's scientific
  name is **Giardia duodenalis** (5741), with "lamblia" and "intestinalis" resolving only through
  the [All Names] fallback; 54,162 records for the taxon, 2,791 matching the rRNA query chosen
  for `blast_partitioned`; every exclusivity name resolves to exactly one taxon.
- Exclusivity suggested in four groups, worst risk first: the co-targets of the same tube
  (E. histolytica, C. parvum) with E. dispar and C. hominis; the rest of the genus, where the
  conserved SSU rRNA makes cross-reaction likeliest; the nearest intestinal flagellates
  (Spironucleus, Hexamita, Chilomastix, Retortamonas, Enteromonas, Pentatrichomonas,
  T. vaginalis); and the rest of the faecal differential. Gut bacteria went to the background
  tier instead (9606, 562, 816), since the oligos are in 18S rRNA and the flora is the largest
  mass of DNA in a stool.
- Oligo names had to lose their spaces, which the format forbids ("RealT G.lamblia F" ->
  RealT-G.lamblia-F). QC: Review, 0 outside the limit and 8 outside the preferred range, all of
  them the design - a GC-rich rRNA target and a short, hot amplicon.

# Related

* [Giardia lamblia, SSU rRNA (Verweij 2004 multiplex)](../assays/giardia-lamblia-ssu.md)
