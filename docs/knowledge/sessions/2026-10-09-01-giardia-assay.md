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
- The user's first live Giardia run then failed: NCBI called an exclusivity RID READY and
  answered the JSON2_S request with "SYSTEM CAN'T PROCESS YOUR REQUEST, PLEASE CONTACT
  blasthelp" (RID CHAN7C89016). Two things were wrong on our side: the runner cached whatever
  the fetch returned **before** the caller parsed it, so the page became the stored result and
  every later run was served it from the cache and failed identically until the TTL expired; and
  there was no retry, so one formatter hiccup stopped a run outright. Fixed: the fetch is
  retried three times and the search submitted anew once if it was resumed, only a body that can
  be a report is cached, and a page cached by an older run is ignored. Written up in
  [ncbi/blast-url-api](../ncbi/blast-url-api.md) as measured NCBI behaviour: READY is not a
  promise that the formatter will deliver.
- The rerun on the fixed code refused the poisoned entry and searched again; the log the user
  pasted ended at "attempt 1/3" for the new RID, and I concluded from that the failure was
  deterministic and the background tier I had suggested was at fault, so I took E. coli and
  Bacteroides out of the file. **That was wrong, and corrected the same day**: the finished run
  shows the background search is RID CHCC1S18014, the very one whose first fetch failed, so a
  later attempt of the retry delivered its report. The tier is restored, and the BLAST API page
  now says that a repeat failure for one RID still says nothing about the next.
- The run itself finished: [runs/giardia-2026-10-09](../runs/giardia-2026-10-09.md). Exceeds
  limit, because the probe is predicted to detect G. microti (8 records, perfect primer pair) and
  G. psittaci - group 2 of the suggested panel, the rest of the genus, which was the right worry.
  The background tier predicted 31 products and none probe-detectable, so the flora earns its
  place in that tier after all. 96.0% detectable of 202 records collected 2023-2026, but
  Incomplete because 67.7% of the records have no usable collection year; for Giardia
  `status_axis: release` would suit the records better.

# Related

* [Giardia lamblia, SSU rRNA (Verweij 2004 multiplex)](../assays/giardia-lamblia-ssu.md)
* [BLAST URL API - what the code relies on](../ncbi/blast-url-api.md)
* [Giardia lamblia, 2026-10-09 (09:45Z, complete)](../runs/giardia-2026-10-09.md)
