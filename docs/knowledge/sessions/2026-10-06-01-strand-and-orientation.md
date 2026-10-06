---
type: Session
title: "Strand and orientation of a record"
description: "Session log of 2026-10-06."
tags: [session]
session_date: 2026-10-06
session_label: "2026-10-06"
generated: { by: claude-code/agent, at: 2026-10-06T08:00:00Z }
---

# 2026-10-06: Strand and orientation of a record

- User asked whether the tool detects a sequence submitted as the reverse complement or in
  another orientation. Answer: yes. The chain locator seeds each record on both strands
  (`chain.py`, `for strand, s in (("+", contig), ("-", reverse_complement(contig)))`), every copy
  carries its strand and the sites are read in the fragment's sense; tests cover a minus-strand
  copy and a minus-strand record end to end, and the E. histolytica run is live evidence (its
  amplicon lies opposite the rRNA; X64142.1 carries it as a reverse complement).
- Written up as [components/strand-and-orientation](../components/strand-and-orientation.md),
  with the two cases orientation does not cover: a record that starts or ends inside the amplicon
  (cut, undetermined) and a circular genome whose start point falls inside it (two cut pieces,
  never joined). Linked from the chain locator page.

# Related

* [Strand and orientation of a record](../components/strand-and-orientation.md)
