---
type: Component
title: Strand and orientation of a record
description: Both strands are searched, so a record submitted as the reverse complement is found and judged like any other; only a record that starts or ends inside the amplicon is cut.
tags: [component, locator, strand]
status: draft
generated: { by: claude-code/agent, at: 2026-10-06T08:00:00Z }
sources:
  - id: chain
    resource: ../../../src/qpcr_assay_check/variants/chain.py
    title: variants/chain.py (candidates, both strands)
  - id: test-chain
    resource: ../../../tests/test_chain.py
    title: tests/test_chain.py (the minus strand is read in the fragment sense)
  - id: test-partitioned
    resource: ../../../tests/test_variants_partitioned.py
    title: tests/test_variants_partitioned.py (a minus-strand record is assessed)
  - id: run
    resource: ../runs/entamoeba-2026-10-05-complete.md
    title: "Entamoeba histolytica, 2026-10-05 12:49Z (complete)"
---

# The question

Does the tool find the target when a submitter deposited the sequence as the reverse complement,
or in another orientation? (User, 2026-10-06.)

# Yes: both strands are searched

The [chain locator](chain-locator.md) seeds each record twice, on the record as given and on its
reverse complement, and keeps a candidate from either:
`for strand, s in (("+", contig), ("-", reverse_complement(contig)))`.[^chain] Every copy carries
its strand, and the oligo sites are read in the fragment's own sense, so a reverse-complement
record is graded exactly like a forward one.[^test-chain] A minus-strand record goes through the
whole assessment unchanged.[^test-partitioned] The BLAST searches report both strands as well.

Live evidence: in the E. histolytica assay the amplicon lies on the strand opposite the rRNA, and
the reference record X64142.1 carries it as a reverse complement at 88-260. That record and the
other 80 with the region were found and judged.[^run]

# What orientation does not cover

- A nucleotide record has two orientations only, so beyond the reverse complement there is no
  third case to handle.
- A record that **starts or ends inside the amplicon** carries only part of it: that is "cut by a
  record end", counted as undetermined, whichever strand it is on
  ([genome outcome](../rules/genome-outcome.md)).
- A **circular** genome whose start point falls inside the amplicon splits it across the two ends
  of the record. The locator sees two cut pieces, not one whole copy; nothing joins them.

[^chain]: variants/chain.py (candidates, both strands)
[^test-chain]: tests/test_chain.py (the minus strand is read in the fragment sense)
[^test-partitioned]: tests/test_variants_partitioned.py (a minus-strand record is assessed)
[^run]: Entamoeba histolytica, 2026-10-05 12:49Z (complete)
